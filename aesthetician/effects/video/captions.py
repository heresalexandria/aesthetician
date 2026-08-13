"""Burned-in timed captions: subtitle and closed-caption text as a picture layer.

Unlike the damage effects, captions have no procedural schedule: every cue is
user-authored, arriving purely through event edits (docs/events.md). The effect
turns those cues into styled text blocks via engine/text.py, composites the
active ones per frame, and reports each cue back from events() with the
normalized on-screen bbox so a front end can draw exact drag handles.

With no cues the frame passes through untouched, byte for byte.
"""

from __future__ import annotations

import bisect

import numpy as np

from ...engine import text as textmod
from ...engine.graph import Context, Effect, Event, Param, register
from .overlay import StrParam

_ALIGNS = ("left", "center", "right")
_MIN_SIZE, _MAX_SIZE = 0.014, 0.2


def _unit(d: dict, key: str) -> float | None:
    """Optional 0..1 detail value; JSON null hands the cue back to the preset."""
    v = d.get(key)
    return None if v is None else float(np.clip(float(v), 0.0, 1.0))


def _opt_size(d: dict, key: str = "size") -> float | None:
    v = d.get(key)
    return None if v is None else float(np.clip(float(v), _MIN_SIZE, _MAX_SIZE))


def _opt_align(d: dict, key: str = "align") -> str | None:
    v = d.get(key)
    return str(v) if v in _ALIGNS else None


def _opt_color(d: dict, key: str = "color") -> str | None:
    v = d.get(key)
    return None if v in (None, "") else str(v)


@register
class Captions(Effect):
    eid = "captions"
    label = "Captions"
    kind = "frame"
    desc = ("Timed caption text burned into the picture. Cues (the words, when they show, where "
            "they sit) live on the timeline; this effect styles how every cue is drawn.")

    PARAMS = (
        Param("font", "Font", "enum", "sans", choices=textmod.FONT_CHOICES, group="Type",
              desc="Typeface for every cue. cc_mono and dotmatrix read as decoder text, "
                   "teletext as UK service pages, the rest as print or broadcast faces."),
        Param("size", "Text Size", "float", 0.045, lo=0.02, hi=0.13, group="Type",
              desc="Line height as a fraction of frame height."),
        Param("text_case", "Case", "enum", "as_typed", choices=("as_typed", "upper"), group="Type",
              desc="Force uppercase the way Line-21 decoders and many house styles did."),
        Param("line_chars", "Wrap Width", "int", 32, lo=12, hi=64, group="Type",
              desc="Characters per line before the text wraps."),
        Param("max_lines", "Rows", "int", 2, lo=1, hi=4, group="Type",
              desc="Rows the roll-up window scrolls through, and the row target "
                   "for auto-splitting pasted scripts."),
        Param("line_spacing", "Line Spacing", "float", 1.12, lo=0.95, hi=1.6, group="Type",
              desc="Baseline-to-baseline distance in line heights."),
        Param("align", "Alignment", "enum", "center", choices=_ALIGNS, group="Type",
              desc="How lines sit within the caption block."),
        StrParam("color", "Text Color", "str", "FFFFFF", group="Look",
                 desc="Hex color of the text, like FFFFFF or FFD24A."),
        Param("opacity", "Opacity", "float", 1.0, lo=0.2, hi=1.0, group="Look",
              desc="Overall caption opacity."),
        Param("edge", "Edge", "enum", "outline",
              choices=("none", "outline", "shadow", "outline_shadow", "glow", "etch"), group="Look",
              desc="Edge treatment: outline and drop shadow for legibility, glow for CRT "
                   "character generators, etch for optically printed film subtitles."),
        Param("edge_strength", "Edge Strength", "float", 0.5, lo=0.0, hi=1.0, group="Look",
              desc="How heavy the chosen edge treatment is."),
        StrParam("edge_color", "Edge Color", "str", "000000", group="Look",
                 desc="Hex color of the outline and drop shadow. Near-black is what every "
                      "decoder and subtitling house used; lift it for a softer rim."),
        Param("box", "Background", "enum", "none",
              choices=("none", "cells", "block", "band", "card"), group="Look",
              desc="Backing behind the text: cells for per-row decoder bars, block for one "
                   "rectangle, band for a full-width strap, card for a full-frame title card."),
        StrParam("box_color", "Background Color", "str", "000000", group="Look",
                 desc="Hex color of the backing."),
        Param("box_opacity", "Background Opacity", "float", 0.75, lo=0.0, hi=1.0, group="Look",
              desc="Opacity of the backing."),
        Param("pos_x", "Position X", "float", 0.5, lo=0.0, hi=1.0, group="Placement",
              desc="Horizontal center of the caption block. Cues can override their own spot."),
        Param("pos_y", "Position Y", "float", 0.88, lo=0.0, hi=1.0, group="Placement",
              desc="Vertical center of the caption block. 0.88 is the classic lower third."),
        Param("safe_margin", "Safe Margin", "float", 0.04, lo=0.0, hi=0.12, group="Placement",
              desc="Minimum distance from the frame edge, as a fraction of frame size."),
        Param("appear", "Appearance", "enum", "cut",
              choices=("cut", "fade", "paint_on", "typewriter", "roll_up", "karaoke"),
              group="Motion",
              desc="How a cue arrives: cut pops on whole, paint_on sweeps in fast, typewriter "
                   "spells with a cursor, roll_up scrolls rows like live CC, karaoke fills "
                   "across the held line."),
        Param("appear_speed", "Motion Speed", "float", 1.0, lo=0.25, hi=3.0, group="Motion",
              desc="Speed multiplier for fades, reveals, and rolls."),
        StrParam("karaoke_color", "Karaoke Fill", "str", "FFD24A", group="Motion",
                 desc="Hex color the karaoke sweep fills toward."),
        Param("jitter", "Unsteadiness", "float", 0.0, lo=0.0, hi=1.0, group="Motion", iscale=True,
              desc="Analog wobble: tiny position and brightness drift, the way overlaid "
                   "text sat on tape."),
    )

    # ── cue bookkeeping ────────────────────────────────────────────────

    def prepare(self, ctx: Context) -> None:
        fps = max(ctx.fps, 1.0)
        cues: list[dict] = []
        for e in ctx.event_edits:
            if e.get("effect", self.key) != self.key or e.get("kind", "caption") != "caption":
                continue
            op = e.get("op")
            if op == "add":
                fi = int(round(float(e.get("t", 0.0)) * fps))
                if 0 <= fi < ctx.clip_frames:
                    d = e.get("detail") or {}
                    cues.append({
                        "id": e.get("id") or f"edit:add:{fi}:{len(cues)}",
                        "fi": fi,
                        "dur": max(int(round(float(d.get("dur_s", 2.5)) * fps)), 1),
                        "text": str(d.get("text", "") or ""),
                        "pos_x": _unit(d, "pos_x"), "pos_y": _unit(d, "pos_y"),
                        "align": _opt_align(d), "color": _opt_color(d),
                        "size": _opt_size(d), "italic": bool(d.get("italic", False)),
                    })
                continue
            hit = next((c for c in cues if c["id"] == e.get("id")), None)
            if hit is None:
                continue                      # an id this spec never made: skip, never guess
            if op == "remove":
                cues.remove(hit)
            elif op == "move":
                nfi = int(round(float(e.get("t", hit["fi"] / fps)) * fps))
                if 0 <= nfi < ctx.clip_frames:
                    hit["fi"] = nfi
                else:
                    cues.remove(hit)
            elif op == "tune":
                d = e.get("detail") or {}
                if "text" in d:
                    hit["text"] = str(d.get("text") or "")
                if "dur_s" in d:
                    hit["dur"] = max(int(round(float(d["dur_s"]) * fps)), 1)
                for k in ("pos_x", "pos_y"):
                    if k in d:
                        hit[k] = _unit(d, k)
                if "align" in d:
                    hit["align"] = _opt_align(d)
                if "color" in d:
                    hit["color"] = _opt_color(d)
                if "size" in d:
                    hit["size"] = _opt_size(d)
                if "italic" in d:
                    hit["italic"] = bool(d["italic"])
        self._cues = sorted(cues, key=lambda c: (c["fi"], c["id"]))
        self._blocks: dict[tuple, textmod.TextBlock] = {}
        self._reveals: dict[tuple, np.ndarray] = {}
        # For the per-frame active-cue window: start frames in order, and the
        # longest hold, so a frame only ever looks at cues that could touch it.
        self._fis = [c["fi"] for c in self._cues]
        self._max_dur = max((c["dur"] for c in self._cues), default=1)
        self._seed = ctx.seed

    def _block(self, cue: dict, W: int, H: int, which: str = "base") -> textmod.TextBlock:
        v = self.v
        key = (cue["id"], which)
        blk = self._blocks.get(key)
        if blk is None:
            color = textmod.hex_rgb(v["karaoke_color"] if which == "karaoke" else
                                    (cue["color"] or v["color"]))
            size = cue["size"] if cue["size"] is not None else v["size"]
            box = v["box"] if v["box"] in ("cells", "block") else "none"
            line_h = max(int(round(float(size) * H)), 7)
            kw = dict(
                font=v["font"], italic=cue["italic"],
                line_chars=int(v["line_chars"]), spacing=float(v["line_spacing"]),
                align=cue["align"] or v["align"], color=color,
                edge=v["edge"], edge_strength=float(v["edge_strength"]),
                edge_color=textmod.hex_rgb(v["edge_color"], (0.0, 0.0, 0.0)),
                box=box if which == "base" else "none",
                box_color=textmod.hex_rgb(v["box_color"], (0.0, 0.0, 0.0)),
                box_opacity=float(v["box_opacity"]),
                upper=v["text_case"] == "upper", etch_seed=getattr(self, "_seed", 0),
            )
            blk = textmod.render_block(cue["text"], line_h=line_h, **kw)
            # A wrap width tuned for television can overrun a narrow portrait
            # frame; a caption that leaves the picture is never right, so the
            # block shrinks to fit the safe width. Metrics do not scale exactly
            # linearly, so give the correction a couple of passes to land.
            avail = W * max(1.0 - 2.0 * float(v["safe_margin"]), 0.5)
            for _ in range(3):
                tx0, _y0, tx1, _y1 = _text_rect(blk)
                if not (tx1 - tx0 > avail > 0) or line_h <= 7:
                    break
                line_h = max(int(line_h * avail / (tx1 - tx0)), 7)
                blk = textmod.render_block(cue["text"], line_h=line_h, **kw)
            self._blocks[key] = blk
        return blk

    def _place(self, cue: dict, blk: textmod.TextBlock, W: int, H: int) -> tuple[int, int]:
        """Top-left of the block so the TEXT rect centers on the cue's position,
        clamped into the safe area."""
        v = self.v
        px = cue["pos_x"] if cue["pos_x"] is not None else v["pos_x"]
        py = cue["pos_y"] if cue["pos_y"] is not None else v["pos_y"]
        tx0, ty0, tx1, ty1 = _text_rect(blk)
        tw, th = tx1 - tx0, ty1 - ty0
        mx, my = int(round(v["safe_margin"] * W)), int(round(v["safe_margin"] * H))
        want_x = float(px) * W - (tx0 + tw / 2.0)
        want_y = float(py) * H - (ty0 + th / 2.0)
        lo_x, hi_x = mx - tx0, W - mx - tw - tx0
        lo_y, hi_y = my - ty0, H - my - th - ty0
        x0 = int(round(want_x if hi_x < lo_x else float(np.clip(want_x, lo_x, hi_x))))
        y0 = int(round(want_y if hi_y < lo_y else float(np.clip(want_y, lo_y, hi_y))))
        return x0, y0

    # ── plan ───────────────────────────────────────────────────────────

    def _reveal(self, cue: dict, key: tuple, build) -> np.ndarray:
        """One remembered reveal mask per cue. Frames arrive in order, so the
        previous frame's mask is the only one worth keeping; an animated mode
        that holds its step for several frames pays for it once."""
        cached = self._reveals.get(cue["id"])
        if cached is not None and cached[0] == key:
            return cached[1]
        mask = build()
        self._reveals[cue["id"]] = (key, mask)
        return mask

    def events(self, ctx: Context) -> list[Event]:
        fps = max(ctx.fps, 1.0)
        w0, w1 = ctx.t0, ctx.t0 + ctx.n_frames / fps
        out: list[Event] = []
        for cue in getattr(self, "_cues", []):
            t, dur = cue["fi"] / fps, cue["dur"] / fps
            if not (t < w1 and t + dur > w0):
                continue
            blk = self._block(cue, ctx.width, ctx.height)
            x0, y0 = self._place(cue, blk, ctx.width, ctx.height)
            tx0, ty0, tx1, ty1 = _text_rect(blk)
            bbox = [round((x0 + tx0) / ctx.width, 4), round((y0 + ty0) / ctx.height, 4),
                    round((x0 + tx1) / ctx.width, 4), round((y0 + ty1) / ctx.height, 4)]
            out.append(Event(t=t, dur=dur, kind="caption", detail={
                "id": cue["id"], "text": cue["text"], "dur_s": round(dur, 3),
                "pos_x": cue["pos_x"], "pos_y": cue["pos_y"],
                "align": cue["align"], "color": cue["color"], "size": cue["size"],
                "italic": cue["italic"], "bbox": bbox,
                "lines": len(blk.line_boxes),
            }))
        return out

    # ── drawing ────────────────────────────────────────────────────────

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        cues = getattr(self, "_cues", None)
        if not cues:
            return frame
        v = self.v
        H, W = frame.shape[:2]
        fps = max(ctx.fps, 1.0)
        af = ctx.abs_frame(ctx.fi_out)
        # Only cues starting inside (af - longest hold, af] can be on screen.
        lo = bisect.bisect_left(self._fis, af - self._max_dur + 1)
        hi = bisect.bisect_right(self._fis, af)
        for cue in cues[lo:hi]:
            k = af - cue["fi"]
            if not (0 <= k < cue["dur"]):
                continue
            blk = self._block(cue, W, H)
            x0, y0 = self._place(cue, blk, W, H)
            t_in = k / fps
            t_out = (cue["dur"] - 1 - k) / fps
            speed = max(float(v["appear_speed"]), 0.05)
            gain = float(v["opacity"])
            reveal: np.ndarray | None = None
            shift_y = 0
            mode = v["appear"]
            if mode == "fade":
                ramp = 0.18 / speed
                gain *= float(np.clip(t_in / ramp, 0.0, 1.0)) * float(np.clip(t_out / ramp, 0.0, 1.0))
            cursor_rect = None
            if mode in ("paint_on", "typewriter"):
                cps = (28.0 if mode == "paint_on" else 11.0) * speed
                n = int(t_in * cps) + 1
                if n < blk.n_chars:
                    reveal = self._reveal(cue, ("chars", n),
                                          lambda: textmod.reveal_chars(blk, n))
                    if mode == "typewriter" and not ((af // 8) % 2):
                        cursor_rect = _cursor_rect(blk, n)
            elif mode == "roll_up":
                rows = max(int(v["max_lines"]), 1)
                row_t = 0.30 / speed
                n_rows = len(blk.line_boxes)
                k_line = min(int(t_in / row_t), n_rows - 1)
                frac = float(np.clip((t_in - k_line * row_t) / row_t, 0.0, 1.0))
                reveal = self._reveal(cue, ("rows", k_line, rows),
                                      lambda: _row_mask(blk, k_line, rows))
                if frac < 1.0:
                    if n_rows > 1:
                        step = blk.line_boxes[1][1] - blk.line_boxes[0][1]
                    else:
                        step = blk.line_boxes[0][3] - blk.line_boxes[0][1]
                    shift_y = int(round((1.0 - frac) * max(step, 0)))
            if gain <= 0.0:
                continue
            alpha = blk.alpha if reveal is None else blk.alpha * reveal
            rgb = blk.rgb
            if cursor_rect is not None:
                # The cursor is new ink in the gap past the last typed glyph,
                # so it has to be painted, not merely unmasked. Both arrays are
                # written, so neither can be the cached block's own.
                cy0, cy1, cx0, cx1 = cursor_rect
                rgb = rgb.copy()
                alpha[cy0:cy1, cx0:cx1] = 1.0
                rgb[cy0:cy1, cx0:cx1] = np.asarray(
                    textmod.hex_rgb(cue["color"] or v["color"]), np.float32)
            if mode == "karaoke" and blk.n_chars:
                fill = self._block(cue, W, H, "karaoke")
                # Same text, same geometry, different ink: inside the sweep the
                # fill's pixels simply replace the base's.
                if fill.alpha.shape == alpha.shape:
                    sweep = textmod.reveal_sweep(blk, t_in / max(cue["dur"] / fps, 1e-6))
                    m = (sweep > 0.0) & (fill.alpha > 0.02)
                    rgb = np.where(m[..., None], fill.rgb, rgb)
                    alpha = np.where(m, np.maximum(alpha, fill.alpha), alpha)
            jx = jy = 0
            bright = 1.0
            jr = float(v["jitter"])
            if jr > 0.0:
                g = ctx.frame_rng(f"{self.key}:jit:{cue['id']}", fi=af)
                jx = int(round(g.normal() * jr * W * 0.0022))
                jy = int(round(g.normal() * jr * H * 0.004))
                bright = 1.0 + float(g.normal()) * 0.05 * jr
            box_mode = v["box"]
            if box_mode in ("band", "card"):
                _frame_fill(frame, blk, x0, y0 + shift_y + jy, W, H, box_mode,
                            textmod.hex_rgb(v["box_color"], (0.0, 0.0, 0.0)),
                            float(v["box_opacity"]) * min(gain / max(float(v["opacity"]), 1e-6), 1.0))
            _composite(frame, rgb, alpha, x0 + jx, y0 + shift_y + jy, gain, bright)
        return frame


def _text_rect(blk: textmod.TextBlock) -> tuple[int, int, int, int]:
    """The ink: what a viewer sees, and so what a cue is placed and dragged by."""
    return blk.ink


def _layout_rect(blk: textmod.TextBlock) -> tuple[int, int, int, int]:
    """The em box the lines were set on - ascender to descender, full advance
    widths. Backings are sized from this, so a strap keeps the same height
    whether its line happens to carry a descender or not."""
    xs0 = [b[0] for b in blk.line_boxes] or [0]
    ys0 = [b[1] for b in blk.line_boxes] or [0]
    xs1 = [b[2] for b in blk.line_boxes] or [blk.w]
    ys1 = [b[3] for b in blk.line_boxes] or [blk.h]
    return min(xs0), min(ys0), max(xs1), max(ys1)


def _row_mask(blk: textmod.TextBlock, k_line: int, rows: int) -> np.ndarray:
    """Roll-up window: rows (k_line - rows, k_line] visible."""
    out = np.zeros((blk.h, blk.w), np.float32)
    first = max(k_line - rows + 1, 0)
    for i in range(first, k_line + 1):
        x0, y0, x1, y1 = blk.line_boxes[i]
        pad = max((y1 - y0) // 4, 2)
        out[max(y0 - pad, 0) : y1 + pad, :] = 1.0
    return out


def _cursor_rect(blk: textmod.TextBlock, n: int) -> tuple[int, int, int, int] | None:
    """Where a block cursor sits after the n-th typed character."""
    left = n
    for (x0, y0, _x1, y1), cols in zip(blk.line_boxes, blk.char_cols):
        if left < len(cols):
            cw = max(int(np.mean([b - a for a, b in cols])) if cols else 6, 4)
            cx = cols[left - 1][1] if left > 0 else x0
            cx0 = int(np.clip(cx + 1, 0, blk.w - 1))
            cx1 = int(np.clip(cx + 1 + cw, cx0 + 1, blk.w))
            return (max(y0, 0), min(y1, blk.h), cx0, cx1)
        left -= len(cols)
    return None


def _frame_fill(frame: np.ndarray, blk: textmod.TextBlock, x0: int, y0: int, W: int, H: int,
                mode: str, color: tuple, opacity: float) -> None:
    a = float(np.clip(opacity, 0.0, 1.0))
    if a <= 0.0:
        return
    c = np.asarray(color, np.float32)
    if mode == "card":
        frame *= 1.0 - a
        frame += c * a
        return
    # The strap keeps the height it takes from the em box, but sits centered on
    # the ink: a line of capitals carries no descender, and hanging the type in
    # the upper half of its own band is the tell of a caption drawn by geometry
    # rather than by eye.
    _lx0, ly0, _lx1, ly1 = _layout_rect(blk)
    _tx0, ty0, _tx1, ty1 = _text_rect(blk)
    vp = max(int(round((ly1 - ly0) * 0.22 / max(len(blk.line_boxes), 1))), 3)
    half = (ly1 - ly0) / 2.0 + vp
    mid = y0 + (ty0 + ty1) / 2.0
    r0 = int(np.clip(round(mid - half), 0, H))
    r1 = int(np.clip(round(mid + half), 0, H))
    if r1 > r0:
        frame[r0:r1] *= 1.0 - a
        frame[r0:r1] += c * a


def _composite(frame: np.ndarray, rgb: np.ndarray, alpha: np.ndarray,
               x0: int, y0: int, gain: float, bright: float) -> None:
    H, W = frame.shape[:2]
    bh, bw = alpha.shape
    fx0, fy0 = max(x0, 0), max(y0, 0)
    fx1, fy1 = min(x0 + bw, W), min(y0 + bh, H)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    a = alpha[fy0 - y0 : fy1 - y0, fx0 - x0 : fx1 - x0, None] * float(np.clip(gain, 0.0, 1.0))
    c = np.clip(rgb[fy0 - y0 : fy1 - y0, fx0 - x0 : fx1 - x0] * float(bright), 0.0, 1.0)
    region = frame[fy0:fy1, fx0:fx1]
    region[...] = region * (1.0 - a) + c * a
