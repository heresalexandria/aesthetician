"""Burned-in OSD overlays: camcorder/security timestamps and VCR UI chrome.

All text is rendered from a 5x7 dot-matrix bitmap font defined in code, scaled
with chunky nearest-neighbor blocks and a slight soft edge — the way real
character generators looked once recorded to tape.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import cv2

from ...engine.graph import Context, Effect, Param, register


class StrParam(Param):
    """Free-text parameter (start times, channel labels…)."""

    def coerce(self, value):  # type: ignore[override]
        return str(value)


# ── 5x7 dot-matrix font ────────────────────────────────────────────────

_GLYPHS = {
    "0": ".XXX.|X...X|X..XX|X.X.X|XX..X|X...X|.XXX.",
    "1": "..X..|.XX..|..X..|..X..|..X..|..X..|.XXX.",
    "2": ".XXX.|X...X|....X|...X.|..X..|.X...|XXXXX",
    "3": "XXXXX|....X|...X.|..XX.|....X|X...X|.XXX.",
    "4": "...X.|..XX.|.X.X.|X..X.|XXXXX|...X.|...X.",
    "5": "XXXXX|X....|XXXX.|....X|....X|X...X|.XXX.",
    "6": "..XX.|.X...|X....|XXXX.|X...X|X...X|.XXX.",
    "7": "XXXXX|....X|...X.|..X..|.X...|.X...|.X...",
    "8": ".XXX.|X...X|X...X|.XXX.|X...X|X...X|.XXX.",
    "9": ".XXX.|X...X|X...X|.XXXX|....X|...X.|.XX..",
    "A": ".XXX.|X...X|X...X|XXXXX|X...X|X...X|X...X",
    "B": "XXXX.|X...X|X...X|XXXX.|X...X|X...X|XXXX.",
    "C": ".XXX.|X...X|X....|X....|X....|X...X|.XXX.",
    "D": "XXXX.|X...X|X...X|X...X|X...X|X...X|XXXX.",
    "E": "XXXXX|X....|X....|XXXX.|X....|X....|XXXXX",
    "F": "XXXXX|X....|X....|XXXX.|X....|X....|X....",
    "G": ".XXX.|X...X|X....|X.XXX|X...X|X...X|.XXXX",
    "H": "X...X|X...X|X...X|XXXXX|X...X|X...X|X...X",
    "I": ".XXX.|..X..|..X..|..X..|..X..|..X..|.XXX.",
    "J": "..XXX|...X.|...X.|...X.|...X.|X..X.|.XX..",
    "K": "X...X|X..X.|X.X..|XX...|X.X..|X..X.|X...X",
    "L": "X....|X....|X....|X....|X....|X....|XXXXX",
    "M": "X...X|XX.XX|X.X.X|X.X.X|X...X|X...X|X...X",
    "N": "X...X|X...X|XX..X|X.X.X|X..XX|X...X|X...X",
    "O": ".XXX.|X...X|X...X|X...X|X...X|X...X|.XXX.",
    "P": "XXXX.|X...X|X...X|XXXX.|X....|X....|X....",
    "Q": ".XXX.|X...X|X...X|X...X|X.X.X|X..X.|.XX.X",
    "R": "XXXX.|X...X|X...X|XXXX.|X.X..|X..X.|X...X",
    "S": ".XXXX|X....|X....|.XXX.|....X|....X|XXXX.",
    "T": "XXXXX|..X..|..X..|..X..|..X..|..X..|..X..",
    "U": "X...X|X...X|X...X|X...X|X...X|X...X|.XXX.",
    "V": "X...X|X...X|X...X|X...X|X...X|.X.X.|..X..",
    "W": "X...X|X...X|X...X|X.X.X|X.X.X|XX.XX|X...X",
    "X": "X...X|X...X|.X.X.|..X..|.X.X.|X...X|X...X",
    "Y": "X...X|X...X|.X.X.|..X..|..X..|..X..|..X..",
    "Z": "XXXXX|....X|...X.|..X..|.X...|X....|XXXXX",
    ":": ".....|..XX.|..XX.|.....|..XX.|..XX.|.....",
    "/": "....X|....X|...X.|..X..|.X...|X....|X....",
    "-": ".....|.....|.....|XXXXX|.....|.....|.....",
    ".": ".....|.....|.....|.....|.....|.XX..|.XX..",
    " ": ".....|.....|.....|.....|.....|.....|.....",
}

_FONT = {
    ch: np.array([[c == "X" for c in row] for row in rows.split("|")], np.float32)
    for ch, rows in _GLYPHS.items()
}

_GW, _GH = 5, 7          # glyph cell
_ADV, _LINE = 6, 9       # advance / line height in dots

_MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
_DOW = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")


def _text_grid(lines: list[str], align: str = "left") -> np.ndarray:
    """Dot-resolution (1 px per dot) mask for multi-line text."""
    widths = [max(len(s), 1) * _ADV - 1 for s in lines]
    W = max(widths)
    H = len(lines) * _LINE - (_LINE - _GH)
    grid = np.zeros((H, W), np.float32)
    for li, line in enumerate(lines):
        x = W - widths[li] if align == "right" else 0
        y = li * _LINE
        for ch in line.upper():
            glyph = _FONT.get(ch)
            if glyph is not None:
                grid[y : y + _GH, x : x + _GW] = np.maximum(grid[y : y + _GH, x : x + _GW], glyph)
            x += _ADV
    return grid


def _scale_mask(grid: np.ndarray, scale: int) -> np.ndarray:
    """Chunky nearest-neighbor scale + 0.5 px soft edge."""
    big = np.kron(grid, np.ones((scale, scale), np.float32))
    if scale > 1:
        big = cv2.GaussianBlur(big, (0, 0), 0.55)
    return big


# style: color, glow multiplier, outline, box
_STYLES = {
    "camcorder_orange": dict(col=(1.00, 0.58, 0.10), glow=1.0, outline=False, box=False),
    "vcr_white":        dict(col=(0.97, 0.97, 0.97), glow=0.25, outline=True, box=False),
    "security_white":   dict(col=(0.95, 0.95, 0.95), glow=0.15, outline=False, box=True),
    "security_green":   dict(col=(0.30, 1.00, 0.42), glow=0.85, outline=False, box=False),
    "lcd_gray":         dict(col=(0.80, 0.83, 0.80), glow=0.10, outline=True, box=False),
    # short names used by the osd effect
    "white":  dict(col=(0.97, 0.97, 0.97), glow=0.25, outline=True, box=False),
    "green":  dict(col=(0.30, 1.00, 0.42), glow=0.85, outline=False, box=False),
    "orange": dict(col=(1.00, 0.58, 0.10), glow=1.0, outline=False, box=False),
}


def _blend_osd(frame: np.ndarray, mask: np.ndarray, x0: int, y0: int, col: tuple,
               opacity: float, style: dict, glow_amt: float, scale: int,
               brightness: float = 1.0) -> None:
    """Composite a text/shape mask into the frame at (x0, y0) with style dressing."""
    H, W = frame.shape[:2]
    g = glow_amt * style.get("glow", 0.0)
    pad = int(round(3.2 * scale)) if g > 0 else 0
    if pad:
        mask = np.pad(mask, pad)  # room for the glow to fall off naturally
        x0, y0 = x0 - pad, y0 - pad
    mh, mw = mask.shape
    fx0, fy0 = max(x0, 0), max(y0, 0)
    fx1, fy1 = min(x0 + mw, W), min(y0 + mh, H)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    if style.get("box"):
        bp = scale * 2
        bx0, by0 = max(fx0 + pad - bp, 0), max(fy0 + pad - bp, 0)
        bx1, by1 = min(fx1 - pad + bp, W), min(fy1 - pad + bp, H)
        if bx1 > bx0 and by1 > by0:
            frame[by0:by1, bx0:bx1] *= 0.42
    m = mask[fy0 - y0 : fy1 - y0, fx0 - x0 : fx1 - x0]
    region = frame[fy0:fy1, fx0:fx1]
    c = np.asarray(col, np.float32) * brightness

    if style.get("outline"):
        it = max(scale // 3, 1)
        outline = cv2.dilate(m, np.ones((3, 3), np.float32), iterations=it) - m
        a = np.clip(outline, 0, 1)[..., None] * (opacity * 0.85)
        region *= 1.0 - a
    a = np.clip(m, 0.0, 1.0)[..., None] * opacity
    region[...] = region * (1.0 - a) + c * a
    if g > 0:
        gm = cv2.GaussianBlur(m, (0, 0), max(scale * 0.9, 0.8)) * (g * 0.6 * opacity)
        region += c * gm[..., None] * (1.05 - region)
    np.clip(region, 0.0, 1.0, out=region)


def _auto_scale(H: int, size: int) -> int:
    return size if size > 0 else max(1, int(round(H / 170.0)))


def _margins(H: int, W: int, scale: int) -> tuple[int, int]:
    return max(int(W * 0.055), 2 * scale), max(int(H * 0.045), 2 * scale)


# ── timestamp ──────────────────────────────────────────────────────────


@register
class Timestamp(Effect):
    eid = "timestamp"
    label = "Timestamp OSD"
    kind = "frame"
    desc = "Camcorder/security date-time burned into the image with a period dot-matrix character generator; the clock advances with playback."
    PARAMS = (
        Param("style", "Style", "enum", "camcorder_orange",
              choices=("camcorder_orange", "vcr_white", "security_white", "security_green", "lcd_gray"),
              group="OSD", desc="Character generator look: glowing amber, chunky outlined white, boxed security text…"),
        Param("corner", "Corner", "enum", "br", choices=("tl", "tr", "bl", "br"), group="OSD",
              desc="Which corner the timestamp sits in."),
        Param("date_format", "Format", "enum", "mon_d_yyyy",
              choices=("mon_d_yyyy", "dd-mm-yyyy", "yyyy-mm-dd", "mdy_time", "dow_dmy_hms", "hms"),
              group="OSD",
              desc="mon_d_yyyy = 'JAN 1 1990' + time line; mdy_time = '01/01/1990 12:00 AM'; dow_dmy_hms = 'MON 01-01-90 00:00:00'."),
        StrParam("start", "Start Time", "str", "1990-01-01 18:34:12",  # type: ignore[arg-type]
                 group="OSD", desc="Clock value at the first frame, 'YYYY-MM-DD HH:MM:SS'."),
        Param("size", "Pixel Scale", "int", 0, 0, 14, group="OSD",
              desc="Dot size in pixels; 0 picks a period-correct size for the resolution."),
        Param("opacity", "Opacity", "float", 1.0, 0.0, 1.0, group="OSD"),
        Param("glow", "Glow", "float", 0.6, 0.0, 1.0, group="OSD",
              desc="Phosphor-style bloom around the characters."),
        Param("flicker", "Flicker", "float", 0.3, 0.0, 1.0, group="OSD",
              desc="Slight per-frame brightness jitter plus rare one-frame dropouts."),
    )

    def prepare(self, ctx: Context) -> None:
        raw = self.v["start"].strip()
        self._t0 = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                self._t0 = datetime.strptime(raw, fmt)
                break
            except ValueError:
                continue
        if self._t0 is None:
            raise ValueError(f"timestamp: cannot parse start {raw!r} (want 'YYYY-MM-DD HH:MM:SS')")
        self._jit = ctx.noise.white(f"{self.key}:jit")
        self._drop = ctx.noise.white(f"{self.key}:drop")
        self._cache_key: tuple | None = None
        self._cache_mask: np.ndarray | None = None

    def _lines(self, t: datetime) -> list[str]:
        f = self.v["date_format"]
        if f == "mon_d_yyyy":
            h12 = t.hour % 12 or 12
            return [f"{_MONTHS[t.month - 1]} {t.day} {t.year}", f"{h12}:{t.minute:02d} {'AM' if t.hour < 12 else 'PM'}"]
        if f == "dd-mm-yyyy":
            return [f"{t.day:02d}-{t.month:02d}-{t.year}"]
        if f == "yyyy-mm-dd":
            return [f"{t.year}-{t.month:02d}-{t.day:02d}"]
        if f == "mdy_time":
            h12 = t.hour % 12 or 12
            return [f"{t.month:02d}/{t.day:02d}/{t.year} {h12}:{t.minute:02d} {'AM' if t.hour < 12 else 'PM'}"]
        if f == "dow_dmy_hms":
            return [f"{_DOW[t.weekday()]} {t.day:02d}-{t.month:02d}-{t.year % 100:02d} "
                    f"{t.hour:02d}:{t.minute:02d}:{t.second:02d}"]
        return [f"{t.hour:02d}:{t.minute:02d}:{t.second:02d}"]

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        op = self.v["opacity"]
        if op <= 0:
            return frame
        fi = ctx.fi_out
        fl = self.v["flicker"]
        if fl > 0 and float(self._drop[min(fi, len(self._drop) - 1)]) > 1.0 - 0.006 * fl:
            return frame  # rare one-frame OSD dropout
        H, W = frame.shape[:2]
        scale = _auto_scale(H, self.v["size"])
        t = self._t0 + timedelta(seconds=fi / max(ctx.fps, 1.0))
        lines = self._lines(t)
        corner = self.v["corner"]
        align = "right" if corner in ("tr", "br") else "left"
        key = (tuple(lines), scale, align)
        if key != self._cache_key:
            self._cache_mask = _scale_mask(_text_grid(lines, align), scale)
            self._cache_key = key
        mask = self._cache_mask
        mh, mw = mask.shape
        mx, my = _margins(H, W, scale)
        x0 = mx if corner in ("tl", "bl") else W - mx - mw
        y0 = my if corner in ("tl", "tr") else H - my - mh
        b = 1.0 + fl * 0.12 * float(self._jit[min(fi, len(self._jit) - 1)])
        style = _STYLES[self.v["style"]]
        _blend_osd(frame, mask, x0, y0, style["col"], op, style, self.v["glow"], scale, brightness=b)
        return frame


# ── VCR / camcorder UI ─────────────────────────────────────────────────


@register
class OSD(Effect):
    eid = "osd"
    label = "VCR / Camcorder UI"
    kind = "frame"
    desc = "Tape-deck UI chrome: PLAY with its triangle, blinking REC dot, tape speed, an advancing counter and a channel label."
    PARAMS = (
        Param("style", "Style", "enum", "white", choices=("white", "green", "orange"), group="OSD",
              desc="Shared character style for all elements."),
        Param("size", "Pixel Scale", "int", 0, 0, 14, group="OSD",
              desc="Dot size in pixels; 0 picks a period-correct size."),
        Param("opacity", "Opacity", "float", 1.0, 0.0, 1.0, group="OSD"),
        Param("show_play", "PLAY", "bool", True, group="OSD", desc="PLAY label with a solid triangle."),
        Param("play_pos", "PLAY Corner", "enum", "tl", choices=("tl", "tr", "bl", "br"), group="OSD"),
        Param("show_rec", "REC", "bool", False, group="OSD", desc="REC label with a blinking red dot."),
        Param("rec_pos", "REC Corner", "enum", "tr", choices=("tl", "tr", "bl", "br"), group="OSD"),
        Param("blink_hz", "Blink Rate", "float", 1.0, 0.2, 4.0, unit="Hz", group="OSD",
              desc="REC dot blink frequency."),
        Param("show_sp", "Tape Speed", "bool", True, group="OSD", desc="Show the SP/LP/EP speed tag."),
        Param("speed", "Speed Tag", "enum", "sp", choices=("sp", "lp", "ep"), group="OSD"),
        Param("sp_pos", "Speed Corner", "enum", "tr", choices=("tl", "tr", "bl", "br"), group="OSD"),
        Param("show_counter", "Counter", "bool", True, group="OSD",
              desc="Advancing tape counter with occasional digit flicker."),
        StrParam("counter_start", "Counter Start", "str", "0:00:00",  # type: ignore[arg-type]
                 group="OSD", desc="Counter value at the first frame, 'H:MM:SS'."),
        Param("counter_pos", "Counter Corner", "enum", "tl", choices=("tl", "tr", "bl", "br"), group="OSD"),
        Param("show_ch", "Channel", "bool", False, group="OSD", desc="Channel/input label."),
        StrParam("channel", "Channel Text", "str", "CH 03",  # type: ignore[arg-type]
                 group="OSD", desc="Label text, e.g. 'CH 03' or 'AV'."),
        Param("ch_pos", "Channel Corner", "enum", "br", choices=("tl", "tr", "bl", "br"), group="OSD"),
    )

    def prepare(self, ctx: Context) -> None:
        parts = self.v["counter_start"].strip().split(":")
        try:
            nums = [int(p) for p in parts]
        except ValueError:
            raise ValueError(f"osd: cannot parse counter_start {self.v['counter_start']!r} (want 'H:MM:SS')")
        while len(nums) < 3:
            nums.insert(0, 0)
        self._counter0 = nums[0] * 3600 + nums[1] * 60 + nums[2]
        self._flick = ctx.noise.white(f"{self.key}:flick")
        self._mask_cache: dict = {}

    # ── element masks (cached until their text changes) ────────────────

    def _cached(self, key: tuple, builder) -> np.ndarray:
        m = self._mask_cache.get(key)
        if m is None:
            m = builder()
            self._mask_cache = {k: v for k, v in self._mask_cache.items() if k[0] != key[0]}
            self._mask_cache[key] = m
        return m

    def _play_mask(self, scale: int) -> np.ndarray:
        def build():
            text = _scale_mask(_text_grid(["PLAY"]), scale)
            th, tw = text.shape
            tri_w = 6 * scale
            tri = np.zeros((th, tri_w + 3 * scale), np.float32)
            pts = np.array([[0, 0], [tri_w - 1, th // 2], [0, th - 1]], np.int32)
            cv2.fillConvexPoly(tri, pts, 1.0, cv2.LINE_AA)
            return np.concatenate([tri, text], axis=1)
        return self._cached(("play", scale), build)

    def _rec_masks(self, scale: int) -> tuple[np.ndarray, np.ndarray]:
        def build():
            text = _scale_mask(_text_grid(["REC"]), scale)
            th, tw = text.shape
            r = max(int(2.2 * scale), 2)
            dot = np.zeros((th, 2 * r + 3 * scale), np.float32)
            cv2.circle(dot, (r, th // 2), r, 1.0, -1, cv2.LINE_AA)
            pad = np.zeros((th, dot.shape[1]), np.float32)
            return (np.concatenate([dot, np.zeros_like(text)], axis=1),
                    np.concatenate([pad, text], axis=1))
        return self._cached(("rec", scale), build)

    def _counter_text(self, fi: int, fps: float) -> str:
        s = int(self._counter0 + fi / max(fps, 1.0))
        return f"{s // 3600}:{(s // 60) % 60:02d}:{s % 60:02d}"

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        op = self.v["opacity"]
        if op <= 0:
            return frame
        H, W = frame.shape[:2]
        fi = ctx.fi_out
        scale = _auto_scale(H, self.v["size"])
        style = _STYLES[self.v["style"]]
        mx, my = _margins(H, W, scale)
        gap = 4 * scale
        cursors = {c: [0, 0] for c in ("tl", "tr", "bl", "br")}  # [used height, count]

        def place(mask: np.ndarray, corner: str, col: tuple, brightness: float = 1.0) -> None:
            mh, mw = mask.shape
            used = cursors[corner][0]
            x0 = mx if corner in ("tl", "bl") else W - mx - mw
            if corner in ("tl", "tr"):
                y0 = my + used
            else:
                y0 = H - my - used - mh
            _blend_osd(frame, mask, x0, y0, col, op, style, 0.5, scale, brightness=brightness)
            cursors[corner][0] = used + mh + gap

        t = fi / max(ctx.fps, 1.0)
        if self.v["show_play"]:
            place(self._play_mask(scale), self.v["play_pos"], style["col"])
        if self.v["show_rec"]:
            dot, text = self._rec_masks(scale)
            corner = self.v["rec_pos"]
            mh, mw = text.shape
            used = cursors[corner][0]
            x0 = mx if corner in ("tl", "bl") else W - mx - mw
            y0 = my + used if corner in ("tl", "tr") else H - my - used - mh
            _blend_osd(frame, text, x0, y0, style["col"], op, style, 0.5, scale)
            if (t * self.v["blink_hz"]) % 1.0 < 0.6:
                _blend_osd(frame, dot, x0, y0, (0.95, 0.12, 0.10), op, style, 0.7, scale)
            cursors[corner][0] = used + mh + gap
        if self.v["show_sp"]:
            mask = self._cached(("sp", self.v["speed"], scale),
                                lambda: _scale_mask(_text_grid([self.v["speed"].upper()]), scale))
            place(mask, self.v["sp_pos"], style["col"])
        if self.v["show_counter"]:
            text = self._counter_text(fi, ctx.fps)
            mask = self._cached(("cnt", text, scale), lambda: _scale_mask(_text_grid([text]), scale))
            b = 1.0
            flick = float(self._flick[min(fi, len(self._flick) - 1)])
            if flick > 0.96:  # occasional digit flicker
                mask = mask.copy()
                g = ctx.frame_rng(f"{self.key}:dig")
                di = int(g.integers(0, len(text)))
                x0 = di * _ADV * scale
                mask[:, x0 : x0 + _GW * scale] *= float(g.uniform(0.1, 0.5))
                b = 0.92
            place(mask, self.v["counter_pos"], style["col"], brightness=b)
        if self.v["show_ch"]:
            txt = self.v["channel"].upper()
            mask = self._cached(("ch", txt, scale), lambda: _scale_mask(_text_grid([txt]), scale))
            place(mask, self.v["ch_pos"], style["col"])
        return frame
