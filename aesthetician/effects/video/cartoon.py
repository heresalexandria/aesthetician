"""Cel-animation production chain: paint flattening, limited-animation
cadence, peg-bar registration wobble, cel dirt, board texture, ink lines and
cartoon color rendering.

These are the CEL-STAGE artifacts - what the artwork itself and the rostrum
camera contribute before the film stages (grain, gate weave, telecine live in
other modules and get stacked by presets). Everything that lives ON a drawing
is keyed on ctx.fi_src, so it holds perfectly still while a drawing is held
and changes only when the animation advances: the authentic look of cels
being swapped under the camera.
"""

from __future__ import annotations

import cv2
import numpy as np

from ...engine import color
from ...engine.graph import Context, Effect, Param, register

# BT.601 YIQ matrices (same values as engine.color); cv2.transform applies
# 3x3/3x4 color matrices ~30x faster than numpy broadcasting on frames.
_RGB2YIQ = np.array(
    [[0.299, 0.587, 0.114], [0.5959, -0.2746, -0.3213], [0.2115, -0.5227, 0.3112]],
    dtype=np.float32,
)
_YIQ2RGB = np.linalg.inv(_RGB2YIQ).astype(np.float32)


@register
class CelFlatten(Effect):
    eid = "cel_flatten"
    label = "Cel Flatten"
    kind = "frame"
    desc = (
        "Pushes gradient-heavy modern renders toward flat cel paint: "
        "edge-preserving smoothing plus soft luminance posterization, with a "
        "gradient-aware guard so painted-background skies don't band."
    )
    PARAMS = (
        Param("smooth", "Paint Smoothing", "float", 0.5, 0.0, 1.0, group="Paint",
              desc="Edge-preserving (bilateral) flattening of shading inside regions."),
        Param("levels", "Paint Levels", "int", 12, 6, 24, group="Paint",
              desc="Luminance posterization steps - fewer = posterier."),
        Param("flatness", "Flatness", "float", 0.55, 0.0, 1.0, iscale=True, group="Paint",
              desc="Mix of the posterized luminance against the original."),
        Param("protect_gradients", "Protect Gradients", "bool", True, group="Paint",
              desc="Reduce quantization in smooth sky-like areas - cel backgrounds "
                   "WERE painted gradients, so this stays on by default."),
        Param("sat_snap", "Poster Sat Snap", "float", 0.25, 0.0, 1.0, group="Paint",
              desc="Slight chroma quantization for a poster-paint feel."),
        Param("line_gap_fill", "Paint Overshoot", "float", 0.0, 0.0, 1.0, iscale=True,
              group="Paint",
              desc="Hand-coloring slop: neighboring cel paint overshoots 1–2 px "
                   "into the ink lines in irregular patches, thinning strokes "
                   "where the brush strayed. Locked to the drawing."),
    )

    def prepare(self, ctx: Context) -> None:
        self._gap_cache: tuple[int, np.ndarray] | None = None
        self._k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

    def _gap_patches(self, shape: tuple[int, int], ctx: Context) -> np.ndarray:
        """Patchy 0..1 mask of where the painter overshot, per drawing."""
        if self._gap_cache is None or self._gap_cache[0] != ctx.fi_src:
            g = ctx.frame_rng(f"{self.key}:gap", fi=ctx.fi_src)
            h, w = shape
            n = g.random((max(2, h // 4), max(2, w // 4)), dtype=np.float32)
            n = cv2.GaussianBlur(n, (0, 0), 1.6)
            n = cv2.resize(n, (w, h), interpolation=cv2.INTER_LINEAR)
            n -= n.min()
            n /= max(float(n.max()), 1e-6)
            self._gap_cache = (ctx.fi_src, color.smoothstep(0.42, 0.72, n))
        return self._gap_cache[1]

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        x = frame
        H, W = frame.shape[:2]
        s = float(self.v["smooth"])
        if s > 0:
            # bilateral on a half-res proxy; the correction it produces is
            # low-frequency, so upsampling the delta keeps lines pixel-crisp
            sc = 0.06 + 0.22 * s
            sp = 2.0 + 3.0 * s
            half = cv2.resize(x, (max(2, W // 2), max(2, H // 2)), interpolation=cv2.INTER_AREA)
            sm = cv2.bilateralFilter(half, 5, sc, sp)
            if s > 0.55:
                sm = cv2.bilateralFilter(sm, 5, sc * 0.8, sp)
            x = x + cv2.resize(sm - half, (W, H), interpolation=cv2.INTER_LINEAR)

        flat = float(self.v["flatness"])
        if flat > 0:
            y = x @ np.asarray((0.299, 0.587, 0.114), np.float32)
            levels = float(self.v["levels"])
            t = y * levels
            f = t - np.floor(t)
            k = 1.5 + 5.0 * flat  # edge sharpness of each paint step (soft, no hard bands)
            fq = np.clip((f - 0.5) * k + 0.5, 0.0, 1.0)
            yq = (np.floor(t) + fq) / levels
            delta = (yq - y) * flat
            if self.v["protect_gradients"]:
                yb = cv2.GaussianBlur(y, (0, 0), 2.0)
                gx = cv2.Sobel(yb, cv2.CV_32F, 1, 0, ksize=3)
                gy = cv2.Sobel(yb, cv2.CV_32F, 0, 1, ksize=3)
                grad = np.sqrt(gx * gx + gy * gy)
                m = color.smoothstep(0.015, 0.09, grad)  # ~0 in smooth washes
                delta = delta * (0.12 + 0.88 * m)
            x = x + delta[..., None]

        snap = float(self.v["sat_snap"])
        if snap > 0:
            yiq = cv2.transform(np.ascontiguousarray(x), _RGB2YIQ)
            iq = yiq[..., 1:]
            tmp = iq * 12.0
            np.rint(tmp, out=tmp)
            tmp *= 1.0 / 12.0
            tmp -= iq
            tmp *= snap
            iq += tmp
            x = cv2.transform(yiq, _YIQ2RGB)

        gapf = float(self.v["line_gap_fill"])
        if gapf > 0:
            xc = np.clip(x, 0.0, 1.0).astype(np.float32)
            y = xc @ np.asarray((0.299, 0.587, 0.114), np.float32)
            # only genuinely dark ink takes overshoot; paint boundaries don't
            line = 1.0 - color.smoothstep(0.16, 0.40, y)
            if float(line.max()) > 0.02:
                it = 2 if gapf > 0.55 else 1
                paint = cv2.dilate(xc, self._k3, iterations=it)
                a = line * self._gap_patches(y.shape, ctx) * min(gapf * 1.5, 1.0)
                x = xc + (paint - xc) * a[..., None]
        return np.clip(x, 0.0, 1.0).astype(np.float32)


@register
class AnimateOn(Effect):
    eid = "animate_on"
    label = "Animate On..."
    kind = "frame"
    desc = (
        "Limited-animation cadence: hold each drawing for 1/2/3 frames (shot "
        "'on ones/twos/threes'), the Hanna-Barbera mix of mostly twos with "
        "scattered ones and threes, the Filmation syndication economy of "
        "4–8-frame holds, or straight shot-on-video (no held drawings)."
    )
    PARAMS = (
        Param("pattern", "Cadence", "enum", "hb_mixed",
              choices=("ones", "twos", "threes", "hb_mixed", "filmation", "shot_on_video"),
              group="Timing",
              desc="hb_mixed = mostly twos, occasional ones/threes, seed-stable. "
                   "filmation = very long 4–8 frame holds with a rare single - "
                   "the 1975 syndication budget. shot_on_video = every frame "
                   "fresh, the 59.94i videotape cadence (pair with interlace)."),
    )

    def prepare(self, ctx: Context) -> None:
        n = ctx.n_frames
        pat = self.v["pattern"]
        if pat in ("ones", "shot_on_video"):
            # shot_on_video: no held drawings at all - the cadence 'feel' comes
            # from pairing with interlace, which this leaves free to comb
            self._map = np.arange(n, dtype=np.int64)
            return
        if pat in ("twos", "threes"):
            h = 2 if pat == "twos" else 3
            self._map = (np.arange(n, dtype=np.int64) // h) * h
            return
        g = ctx.rng(f"{self.key}:holds")
        idx = np.empty(n, dtype=np.int64)
        pos = 0
        while pos < n:
            r = g.random()
            if pat == "filmation":
                h = 1 if r < 0.07 else 4 + int(g.integers(0, 5))
            else:
                h = 1 if r < 0.12 else (2 if r < 0.82 else 3)
            idx[pos : pos + h] = pos
            pos += h
        self._map = idx

    def remap(self, ctx: Context) -> np.ndarray:
        return self._map[: ctx.n_frames]


@register
class CelWobble(Effect):
    eid = "cel_wobble"
    label = "Cel Wobble"
    kind = "frame"
    desc = (
        "Peg-bar registration error: a tiny sub-pixel shift (and rare micro "
        "rotation) that stays LOCKED while a drawing is held and re-registers "
        "only when the drawing changes - the authentic cel-swap jitter."
    )
    PARAMS = (
        Param("amount", "Wobble", "float", 0.9, 0.0, 4.0, unit="px", iscale=True,
              group="Registration", desc="Maximum re-registration offset per new drawing."),
        Param("rot", "Micro Rotation", "float", 0.06, 0.0, 0.5, unit="°", group="Registration",
              desc="Size of the rare rotational slip."),
        Param("rot_p", "Rotation Chance", "float", 0.12, 0.0, 1.0, group="Registration",
              desc="Probability a new drawing lands slightly rotated."),
        Param("layers", "Cel Layers", "int", 1, 1, 3, group="Registration",
              desc="Stacked-cel depth: 2 separates ink/character from the painted "
                   "background (which sits pegged, drifting only slightly); 3 adds "
                   "an independent midtone cel. Split by luminance bands, kept "
                   "subtle so nothing halos."),
    )

    def prepare(self, ctx: Context) -> None:
        n = max(ctx.n_frames, 1)
        g = ctx.rng(f"{self.key}:table")
        a = float(self.v["amount"])
        self._dx = np.clip(g.normal(0.0, 0.55, n) * a, -a, a).astype(np.float32)
        self._dy = np.clip(g.normal(0.0, 0.55, n) * a, -a, a).astype(np.float32)
        r = float(self.v["rot"])
        hit = g.random(n) < float(self.v["rot_p"])
        self._rot = np.where(hit, np.clip(g.normal(0.0, r, n), -2.5 * r, 2.5 * r), 0.0).astype(np.float32)
        self._active = a > 1e-4 or (r > 1e-5 and self.v["rot_p"] > 0)
        self._layers = int(self.v["layers"])
        if self._layers > 1:
            g3 = ctx.rng(f"{self.key}:table3")            # midtone cel, per drawing
            a3 = a * 0.85
            self._dx3 = np.clip(g3.normal(0.0, 0.55, n) * a3, -a3, a3).astype(np.float32)
            self._dy3 = np.clip(g3.normal(0.0, 0.55, n) * a3, -a3, a3).astype(np.float32)
            gb = ctx.rng(f"{self.key}:bg")                # background painting: pegged
            self._bg_dx0 = float(gb.uniform(-0.3, 0.3)) * a
            self._bg_dy0 = float(gb.uniform(-0.3, 0.3)) * a
            self._bg_tx = ctx.noise.smooth(f"{self.key}:bgx", 0.15) * (0.22 * a)
            self._bg_ty = ctx.noise.smooth(f"{self.key}:bgy", 0.12) * (0.22 * a)
            self._mask_cache: tuple[int, list[np.ndarray]] | None = None

    def _layer_masks(self, frame: np.ndarray, ctx: Context) -> list[np.ndarray]:
        """Soft luminance-band masks (sum to 1), cached per drawing.

        Computed on a half-res proxy - the masks are low-frequency by design
        (soft blurred bands), so the upsample is lossless in practice."""
        if self._mask_cache is not None and self._mask_cache[0] == ctx.fi_src:
            return self._mask_cache[1]
        H, W = frame.shape[:2]
        hw, hh = max(2, W // 2), max(2, H // 2)
        y = cv2.resize(frame, (hw, hh), interpolation=cv2.INTER_AREA) \
            @ np.asarray((0.299, 0.587, 0.114), np.float32)
        y = cv2.GaussianBlur(y, (0, 0), 1.5)
        light = color.smoothstep(0.60, 0.80, y)           # background paint
        if self._layers == 2:
            masks = [1.0 - light, light]
        else:
            dark = 1.0 - color.smoothstep(0.30, 0.48, y)  # ink/shadow cel
            mid = np.clip(1.0 - dark - light, 0.0, 1.0)
            masks = [dark, mid, light]
        masks = [cv2.GaussianBlur(m, (0, 0), 1.0) for m in masks]
        s = masks[0].copy()
        for m in masks[1:]:
            s += m
        s = np.maximum(s, 1e-4)
        masks = [cv2.resize(m / s, (W, H), interpolation=cv2.INTER_LINEAR) for m in masks]
        self._mask_cache = (ctx.fi_src, masks)
        return masks

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        if not self._active:
            return frame
        i = min(ctx.fi_src, len(self._dx) - 1)
        dx, dy, rot = float(self._dx[i]), float(self._dy[i]), float(self._rot[i])
        H, W = frame.shape[:2]
        if self._layers == 1:
            if abs(dx) < 0.01 and abs(dy) < 0.01 and abs(rot) < 1e-4:
                return frame
            M = cv2.getRotationMatrix2D((W / 2.0, H / 2.0), rot, 1.0)
            M[0, 2] += dx
            M[1, 2] += dy
            return cv2.warpAffine(
                frame, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE
            )

        io = min(ctx.fi_out, len(self._bg_tx) - 1)
        moves: list[tuple[float, float, float]] = [(dx, dy, rot)]   # top cel
        if self._layers == 3:
            moves.append((float(self._dx3[i]), float(self._dy3[i]), 0.0))
        moves.append((self._bg_dx0 + float(self._bg_tx[io]),        # background
                      self._bg_dy0 + float(self._bg_ty[io]), 0.0))
        masks = self._layer_masks(frame, ctx)

        acc = np.zeros_like(frame)
        wsum = np.zeros(frame.shape[:2], np.float32)
        pack = np.empty((H, W, 4), np.float32)
        for (ldx, ldy, lrot), m in zip(moves, masks):
            pack[..., :3] = frame * m[..., None]
            pack[..., 3] = m
            if abs(ldx) < 0.01 and abs(ldy) < 0.01 and abs(lrot) < 1e-4:
                warped = pack
            else:
                M = cv2.getRotationMatrix2D((W / 2.0, H / 2.0), lrot, 1.0)
                M[0, 2] += ldx
                M[1, 2] += ldy
                warped = cv2.warpAffine(pack, M, (W, H), flags=cv2.INTER_LINEAR,
                                        borderMode=cv2.BORDER_REPLICATE)
            acc += warped[..., :3]
            wsum += warped[..., 3]
        acc /= np.maximum(wsum, 1e-4)[..., None]
        return np.clip(acc, 0.0, 1.0).astype(np.float32)


@register
class CelDirt(Effect):
    eid = "cel_dirt"
    label = "Cel Dirt"
    kind = "frame"
    desc = (
        "Dirt on the cels and camera glass: faint smudges, fingerprint arcs, "
        "eraser shadows and stray pencil flecks that persist while a drawing "
        "is held and change with it, plus big ultra-soft glass shadows near "
        "the corners. Reads subliminally at the default visibility."
    )
    PARAMS = (
        Param("density", "Density", "float", 0.5, 0.0, 1.0, group="Cel",
              desc="How much handling dirt each drawing carries."),
        Param("smudge_size", "Smudge Size", "float", 0.5, 0.0, 1.0, group="Cel",
              desc="Scale of smudges and wipe marks."),
        Param("visibility", "Visibility", "float", 0.07, 0.0, 0.5, iscale=True, group="Cel",
              desc="Opacity of the marks - keep low; these should read subliminally."),
        Param("glass_shadows", "Glass Shadows", "float", 0.35, 0.0, 1.0, group="Camera",
              desc="Ultra-soft dark patches near frame corners (platen glass / "
                   "rostrum shadows), static per shot with a tiny breathe."),
        Param("hair_in_gate_rate", "Hair in Gate", "float", 0.0, 0.0, 6.0, unit="events/min",
              iscale=True, group="Camera",
              desc="A dark hair caught at the frame edge, wiggling for a second "
                   "or three before it clears - the classic rostrum-camera gate "
                   "artifact."),
        Param("tape_splice", "Cel Tape", "float", 0.0, 0.0, 1.0, iscale=True, group="Cel",
              desc="Rare faint horizontal cel-tape edge: a hairline seam with a "
                   "subtle refraction band and sheen, stuck to the drawing it "
                   "was taped to."),
    )

    def prepare(self, ctx: Context) -> None:
        H, W = ctx.height, ctx.width
        self._cache: tuple[int, np.ndarray, np.ndarray] | None = None
        self._prepare_hairs(ctx)
        self._tape_cache: tuple[int, tuple | None] | None = None
        g = ctx.rng(f"{self.key}:glass")
        gh, gw = max(2, H // 16), max(2, W // 16)
        m = np.zeros((gh, gw), dtype=np.float32)
        yy, xx = np.mgrid[0:gh, 0:gw].astype(np.float32)
        corners = [(0.0, 0.0), (0.0, 1.0), (1.0, 0.0), (1.0, 1.0)]
        g.shuffle(corners)
        for cy, cx in corners[: 1 + int(g.integers(0, 2))]:
            jy = (cy + g.uniform(-0.10, 0.10)) * (gh - 1)
            jx = (cx + g.uniform(-0.10, 0.10)) * (gw - 1)
            sig = g.uniform(0.30, 0.55) * min(gh, gw)
            m += g.uniform(0.55, 1.0) * np.exp(-((yy - jy) ** 2 + (xx - jx) ** 2) / (2 * sig**2))
        m /= max(float(m.max()), 1e-6)
        self._glass = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)
        self._breath = 1.0 + 0.12 * ctx.noise.smooth(f"{self.key}:breath", 0.3)

    # ── hair in gate ───────────────────────────────────────────────────
    def _prepare_hairs(self, ctx: Context) -> None:
        self._hairs: list[dict] = []
        rate = float(self.v["hair_in_gate_rate"])
        if rate <= 0:
            return
        fps = max(ctx.fps, 1.0)
        ev = ctx.noise.events(f"{self.key}:hair", rate / 60.0, min_gap_s=3.5)
        g = ctx.rng(f"{self.key}:hairshape")
        for i in np.nonzero(ev)[0]:
            self._hairs.append(dict(
                f0=int(i),
                f1=int(i) + int((1.0 + 2.0 * g.random()) * fps),      # 1–3 s
                edge=int(g.integers(0, 4)),                           # 0 L,1 R,2 B,3 T
                u=float(g.uniform(0.12, 0.88)),                       # along the edge
                length=float(g.uniform(0.05, 0.13)),                  # of min dim
                curl=float(g.uniform(2.0, 5.5)),
                curl_ph=float(g.uniform(0.0, 2 * np.pi)),
                amp=float(g.uniform(0.5, 1.0)),
                wig=ctx.noise.smooth(f"{self.key}:hairw{len(self._hairs)}", 2.8),
                wig2=ctx.noise.smooth(f"{self.key}:hairw2{len(self._hairs)}", 4.5),
            ))

    def _hair_overlay(self, H: int, W: int, ctx: Context) -> np.ndarray | None:
        fi = ctx.fi_out
        active = [h for h in self._hairs if h["f0"] <= fi < h["f1"]]
        if not active:
            return None
        ov = np.zeros((H, W), np.float32)
        mind = min(H, W)
        for h in active:
            # ease in/out - the hair slides into the gate and clears
            u_in = np.clip((fi - h["f0"]) / 4.0, 0.0, 1.0)
            u_out = np.clip((h["f1"] - fi) / 4.0, 0.0, 1.0)
            vis = float(min(u_in, u_out))
            L = h["length"] * mind
            t = np.linspace(0.0, 1.0, 24, dtype=np.float32)
            w1 = float(h["wig"][min(fi, len(h["wig"]) - 1)])
            w2 = float(h["wig2"][min(fi, len(h["wig2"]) - 1)])
            # root pinned at the gate edge, tip waves: lateral offset grows with t
            lat = (np.sin(t * h["curl"] + h["curl_ph"] + w1 * 1.2) * 0.16
                   + w1 * 0.30 * t + w2 * 0.12) * h["amp"] * L * t ** 1.4
            ax = t * L
            if h["edge"] == 0:      # left
                xs, ys = ax, h["u"] * H + lat
            elif h["edge"] == 1:    # right
                xs, ys = W - 1 - ax, h["u"] * H + lat
            elif h["edge"] == 2:    # bottom
                xs, ys = h["u"] * W + lat, H - 1 - ax
            else:                   # top
                xs, ys = h["u"] * W + lat, ax
            pts = np.stack([xs, ys], axis=-1).astype(np.int32).reshape(-1, 1, 2)
            cv2.polylines(ov, [pts], False, float(0.8 * vis),
                          max(1, int(round(mind / 480.0))), lineType=cv2.LINE_AA)
        if float(ov.max()) <= 0.0:
            return None
        return cv2.GaussianBlur(ov, (0, 0), 0.7)

    # ── cel tape ───────────────────────────────────────────────────────
    def _tape_for_drawing(self, ctx: Context, H: int) -> tuple | None:
        """(y0, y1, shift_px, sheen) for the current drawing, or None."""
        if self._tape_cache is not None and self._tape_cache[0] == ctx.fi_src:
            return self._tape_cache[1]
        ts = float(self.v["tape_splice"])
        g = ctx.frame_rng(f"{self.key}:tape", fi=ctx.fi_src)
        tape = None
        if g.random() < 0.035 + 0.09 * ts:                # rare, per drawing
            y0 = int(g.uniform(0.12, 0.85) * H)
            bh = max(int(H * g.uniform(0.010, 0.028)), 3)
            tape = (y0, min(y0 + bh, H - 1),
                    float(g.uniform(0.5, 1.1)) * (1.0 if g.random() < 0.5 else -1.0),
                    float(g.uniform(0.5, 1.0)))
        self._tape_cache = (ctx.fi_src, tape)
        return tape

    def _apply_tape(self, x: np.ndarray, tape: tuple, ts: float) -> np.ndarray:
        y0, y1, shift, sheen = tape
        H, W = x.shape[:2]
        band = x[y0:y1]
        # refraction: the band samples slightly displaced rows (subpixel)
        s = abs(shift)
        src0 = x[max(y0 - 1, 0):y1 - 1] if shift > 0 else x[y0 + 1:min(y1 + 1, H)]
        if src0.shape == band.shape:
            x[y0:y1] = band * (1.0 - s * 0.55) + src0 * (s * 0.55)
        # hairline edges + faint sheen inside
        edge_a = 0.10 * ts
        x[y0] *= 1.0 - edge_a
        x[y1 - 1] *= 1.0 - edge_a * 0.7
        inner = x[y0 + 1:y1 - 1]
        if inner.size:
            inner += (0.028 * ts * sheen) * (1.0 - inner)
        return x

    def _draw_overlays(self, ctx: Context, W: int, H: int) -> tuple[np.ndarray, np.ndarray]:
        """Dark & light mark layers for the current drawing, at half res."""
        hw, hh = max(2, W // 2), max(2, H // 2)
        dark_soft = np.zeros((hh, hw), dtype=np.float32)
        dark_fine = np.zeros((hh, hw), dtype=np.float32)
        light = np.zeros((hh, hw), dtype=np.float32)
        g = ctx.frame_rng(f"{self.key}:cel", fi=ctx.fi_src)
        dens = float(self.v["density"])
        size = float(self.v["smudge_size"])
        mind = min(hw, hh)

        def _pt() -> tuple[int, int]:
            return int(g.uniform(0, hw)), int(g.uniform(0, hh))

        # soft smudges
        for _ in range(int(round(g.uniform(0.6, 1.5) * dens * 4))):
            ax = int(mind * (0.02 + 0.10 * size) * g.uniform(0.5, 1.7)) + 1
            ay = max(1, int(ax * g.uniform(0.35, 1.0)))
            cv2.ellipse(dark_soft, _pt(), (ax, ay), float(g.uniform(0, 180)),
                        0, 360, float(g.uniform(0.35, 0.8)), -1)
        # eraser shadow - one broad faint patch
        if g.random() < 0.35 * dens:
            ax = int(mind * g.uniform(0.10, 0.22)) + 2
            cv2.ellipse(dark_soft, _pt(), (ax, int(ax * g.uniform(0.4, 0.9))),
                        float(g.uniform(0, 180)), 0, 360, 0.16, -1)
        # fingerprint arcs - concentric partial ellipses
        if g.random() < 0.4 * dens:
            c = _pt()
            r0 = mind * g.uniform(0.02, 0.045) * (1.0 + size)
            a0 = g.uniform(0, 360)
            for j in range(int(g.integers(3, 7))):
                r = int(r0 * (1.0 + 0.22 * j)) + 1
                start = a0 + g.uniform(-20, 20)
                cv2.ellipse(dark_fine, c, (r, int(r * g.uniform(0.8, 1.0))),
                            float(g.uniform(0, 180)), start,
                            start + g.uniform(60, 200), 0.45, int(1 + (g.random() < 0.3)))
        # stray pencil flecks / dots
        for _ in range(int(round(g.uniform(2, 9) * dens))):
            x0, y0 = _pt()
            if g.random() < 0.4:
                cv2.circle(dark_fine, (x0, y0), int(g.random() < 0.2) + 1, float(g.uniform(0.4, 0.8)), -1)
            else:
                ln = g.uniform(3, 10)
                th = g.uniform(0, np.pi)
                x1 = int(x0 + ln * np.cos(th))
                y1 = int(y0 + ln * np.sin(th))
                cv2.line(dark_fine, (x0, y0), (x1, y1), float(g.uniform(0.4, 0.9)), 1)
        # rare light marks (paint skips / eraser shine)
        if g.random() < 0.22 * dens:
            ax = int(mind * (0.015 + 0.06 * size) * g.uniform(0.6, 1.4)) + 1
            cv2.ellipse(light, _pt(), (ax, max(1, int(ax * 0.6))),
                        float(g.uniform(0, 180)), 0, 360, float(g.uniform(0.2, 0.45)), -1)

        sig = 2.0 + 5.0 * size
        dark_soft = cv2.GaussianBlur(dark_soft, (0, 0), sig)
        dark_fine = cv2.GaussianBlur(dark_fine, (0, 0), 0.6)
        light = cv2.GaussianBlur(light, (0, 0), sig * 0.7)
        dark = np.clip(dark_soft * 0.85 + dark_fine, 0.0, 1.4)
        return (
            cv2.resize(dark, (W, H), interpolation=cv2.INTER_LINEAR),
            cv2.resize(light, (W, H), interpolation=cv2.INTER_LINEAR),
        )

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        H, W = frame.shape[:2]
        vis = float(self.v["visibility"])
        x = frame
        if vis > 0 and self.v["density"] > 0:
            if self._cache is None or self._cache[0] != ctx.fi_src:
                dark, light = self._draw_overlays(ctx, W, H)
                self._cache = (ctx.fi_src, dark, light)
            _, dark, light = self._cache
            x = x * (1.0 - dark[..., None] * vis)
            x = x + light[..., None] * (vis * 0.8) * (1.0 - x)
        ts = float(self.v["tape_splice"])
        if ts > 0:
            tape = self._tape_for_drawing(ctx, H)
            if tape is not None:
                if x is frame:
                    x = x.copy()
                x = self._apply_tape(x, tape, ts)
        if self._hairs:
            hair = self._hair_overlay(H, W, ctx)
            if hair is not None:
                x = x * (1.0 - np.clip(hair, 0.0, 1.0)[..., None] * 0.82)
        gs = float(self.v["glass_shadows"])
        if gs > 0:
            b = float(self._breath[min(ctx.fi_out, len(self._breath) - 1)])
            x = x * (1.0 - self._glass[..., None] * (0.16 * gs * b))
        return np.clip(x, 0.0, 1.0).astype(np.float32)


@register
class PaperTexture(Effect):
    eid = "paper_texture"
    label = "Paper Texture"
    kind = "frame"
    desc = (
        "Illustration-board / paint texture multiplied into flat areas: fine "
        "blurred grain with slight horizontal brush anisotropy, masked away "
        "from ink lines and deep blacks, static per shot with a sub-pixel "
        "breathe so it feels photographed rather than pasted on."
    )
    PARAMS = (
        Param("scale", "Texture Scale", "float", 1.0, 0.5, 3.0, group="Texture",
              desc="Feature size of the tooth/brush texture."),
        Param("amount", "Amount", "float", 0.05, 0.0, 0.5, iscale=True, group="Texture",
              desc="Multiply-blend strength - subtle by default (film grain is a "
                   "separate print-stage effect and stacks on top)."),
    )

    def prepare(self, ctx: Context) -> None:
        H, W = ctx.height, ctx.width
        g = ctx.rng(f"{self.key}:tex")
        sc = float(self.v["scale"])
        hs, ws = max(2, int(H / sc)), max(2, int(W / sc))
        t = g.standard_normal((hs, ws)).astype(np.float32)
        t = cv2.GaussianBlur(t, (0, 0), 0.55)
        t = cv2.blur(t, (5, 1))  # horizontal brush anisotropy
        t = cv2.resize(t, (W, H), interpolation=cv2.INTER_LINEAR)
        t /= float(np.percentile(np.abs(t), 95)) + 1e-6
        self._tex = np.clip(t, -2.5, 2.5)
        self._dx = ctx.noise.smooth(f"{self.key}:dx", 0.4) * 0.8
        self._dy = ctx.noise.smooth(f"{self.key}:dy", 0.33) * 0.5

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        amt = float(self.v["amount"])
        if amt <= 0:
            return frame
        H, W = frame.shape[:2]
        y = frame @ np.asarray((0.299, 0.587, 0.114), np.float32)
        yb = cv2.GaussianBlur(y, (0, 0), 1.0)
        gx = cv2.Sobel(yb, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(yb, cv2.CV_32F, 0, 1, ksize=3)
        edge = np.sqrt(gx * gx + gy * gy)
        # keep lines crisp, keep ink blacks clean, favor paint mids
        m = (1.0 - color.smoothstep(0.05, 0.22, edge)) * color.smoothstep(0.05, 0.22, y)
        i = min(ctx.fi_out, len(self._dx) - 1)
        M = np.array([[1.0, 0.0, float(self._dx[i])], [0.0, 1.0, float(self._dy[i])]], np.float32)
        t = cv2.warpAffine(self._tex, M, (W, H), flags=cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_REFLECT)
        out = frame * (1.0 + (t * amt * m)[..., None])
        return np.clip(out, 0.0, 1.0).astype(np.float32)


@register
class InkLine(Effect):
    eid = "ink_line"
    label = "Ink Line"
    kind = "frame"
    desc = (
        "Line treatment for cartoon sources: darkens and slightly thickens the "
        "existing dark drawn lines, with optional xerographic grit that makes "
        "line edges microscopically ragged (the post-1960 photocopied-pencil "
        "look). Enhances lines already present - meant for animation, not "
        "photographic content."
    )
    PARAMS = (
        Param("weight", "Line Weight", "float", 0.45, 0.0, 1.0, iscale=True, group="Line",
              desc="How much existing dark lines are darkened and thickened."),
        Param("xerox_grit", "Xerox Grit", "float", 0.35, 0.0, 1.0, group="Line",
              desc="Ragged line-edge modulation - the xerography era's broken line."),
        Param("line_color", "Line Color", "enum", "black",
              choices=("black", "sepia", "blue_pencil", "warm_brown"), group="Line",
              desc="Tint of the line boost: inked black, sepia print, the "
                   "blue-pencil trace look, or the warm-brown color-ink era."),
        Param("line_wobble", "Line Wobble", "float", 0.0, 0.0, 1.0, iscale=True, group="Line",
              desc="Hand-inked weight variation: line darkness and thickness swell "
                   "and thin slowly along the stroke, locked to the drawing so it "
                   "holds while the cel holds."),
    )

    _COLORS = {
        "black": (0.030, 0.028, 0.032),
        "sepia": (0.165, 0.105, 0.055),
        "blue_pencil": (0.115, 0.140, 0.300),
        "warm_brown": (0.130, 0.072, 0.042),
    }

    def prepare(self, ctx: Context) -> None:
        self._grit_cache: tuple[int, np.ndarray] | None = None
        self._wob_cache: tuple[int, np.ndarray] | None = None
        self._k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        w = float(self.v["weight"])
        if w <= 0:
            return frame
        y = frame @ np.asarray((0.299, 0.587, 0.114), np.float32)
        yb = cv2.GaussianBlur(y, (0, 0), 0.8)
        gx = cv2.Sobel(yb, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(yb, cv2.CV_32F, 0, 1, ksize=3)
        mag = cv2.magnitude(gx, gy) * 0.25
        m = color.smoothstep(0.10, 0.34, mag)
        # only boost near genuinely dark ink strokes - don't invent edges on
        # paint-to-paint boundaries
        ymin = cv2.erode(y, self._k3)
        m = m * (1.0 - color.smoothstep(0.18, 0.45, ymin))
        # xerox raggedness eats into the CORE mask first (clumpy, band-limited
        # noise - single-pixel salt reads as dots, not a broken line)
        grit = float(self.v["xerox_grit"])
        if grit > 0:
            if self._grit_cache is None or self._grit_cache[0] != ctx.fi_src:
                g = ctx.frame_rng(f"{self.key}:grit", fi=ctx.fi_src)
                noise = g.random(y.shape, dtype=np.float32)
                noise = cv2.GaussianBlur(noise, (0, 0), 0.7)
                noise -= noise.min()
                noise /= max(float(noise.max()), 1e-6)
                self._grit_cache = (ctx.fi_src, noise)
            noise = self._grit_cache[1]
            m = m * np.clip(1.0 - grit * (noise * 1.4 - 0.35), 0.0, 1.2)
        # hand-inked weight variation: slow per-position swell/thin of the
        # stroke, keyed to the drawing so it holds with the cel
        lw = float(self.v["line_wobble"])
        if lw > 0:
            if self._wob_cache is None or self._wob_cache[0] != ctx.fi_src:
                g = ctx.frame_rng(f"{self.key}:wobble", fi=ctx.fi_src)
                h2, w2 = max(2, y.shape[0] // 8), max(2, y.shape[1] // 8)
                wn = g.random((h2, w2), dtype=np.float32)
                wn = cv2.GaussianBlur(wn, (0, 0), 2.2)
                wn = cv2.resize(wn, (y.shape[1], y.shape[0]), interpolation=cv2.INTER_LINEAR)
                wn -= wn.min()
                wn /= max(float(wn.max()), 1e-6)
                self._wob_cache = (ctx.fi_src, wn)
            wn = self._wob_cache[1]
            m = m * np.clip(1.0 + lw * (wn * 1.7 - 0.85), 0.15, 2.0)
        # thicken: pull the ragged mask outward by ~1px, scaled with weight
        dil = cv2.dilate(m, self._k3)
        m = np.maximum(m, dil * (0.30 + 0.55 * w))
        a = np.clip(m * w, 0.0, 1.0)[..., None]
        col = np.asarray(self._COLORS[self.v["line_color"]], np.float32)
        out = frame * (1.0 - a) + col * a
        return np.clip(out, 0.0, 1.0).astype(np.float32)


@register
class ColorEra(Effect):
    eid = "color_era"
    label = "Cartoon Color Era"
    kind = "frame"
    desc = (
        "Cartoon-specific color rendering: Hanna-Barbera 1960s TV paint (warm "
        "paper whites, teal-leaning blues, gently muted primaries), brighter "
        "70s Saturday-morning, 1930s rubber-hose duotone, saturated 40s "
        "Technicolor cartoon, a dye-faded 16mm classroom print, flat olive "
        "Filmation syndication, bright 90s Nick punch, or grungy 1994 MTV "
        "bleach."
    )
    PARAMS = (
        Param("profile", "Profile", "enum", "hb_1960s_tv",
              choices=("hb_1960s_tv", "hb_1970s", "rubber_hose_1930s",
                       "technicolor_cartoon_1940s", "tv_print_faded",
                       "filmation_1975", "nick_90s", "mtv_1994"),
              group="Color", desc="Era rendering profile."),
        Param("strength", "Strength", "float", 1.0, 0.0, 1.0, group="Color"),
    )

    # matrix, saturation, gain, lift amount, lift color, highlight tint (amt, rgb)
    _P = {
        "hb_1960s_tv": dict(
            m=np.array([[1.02, 0.05, -0.07], [0.01, 1.00, -0.01], [-0.03, 0.08, 0.92]]),
            sat=0.88, gain=0.985, lift=0.045, lift_col=(1.25, 1.06, 0.82),
            high=(0.045, (0.9, 0.75, 0.25)),
        ),
        "hb_1970s": dict(
            m=np.array([[1.09, -0.02, -0.02], [-0.02, 1.03, -0.01], [0.01, -0.03, 1.05]]),
            sat=1.10, gain=1.045, lift=0.028, lift_col=(1.18, 0.92, 1.05),
            high=(0.02, (1.0, 0.85, 0.9)),
        ),
        "rubber_hose_1930s": dict(duotone=((0.105, 0.088, 0.070), (0.925, 0.895, 0.825))),
        "technicolor_cartoon_1940s": dict(
            m=np.array([[1.22, -0.12, -0.08], [-0.06, 1.14, -0.06], [-0.04, -0.10, 1.16]]),
            sat=1.28, gain=1.02, lift=-0.012, lift_col=(1.0, 1.0, 1.0),
            high=(0.03, (1.0, 0.93, 0.72)),
        ),
        "tv_print_faded": dict(
            m=np.array([[1.07, 0.03, -0.02], [0.01, 0.97, 0.01], [-0.05, 0.00, 0.87]]),
            sat=0.70, gain=0.885, lift=0.105, lift_col=(1.22, 1.02, 0.94),
            high=(0.0, (1.0, 1.0, 1.0)),
        ),
        # 1975 syndication economy: flat, dull, everything drifting olive
        "filmation_1975": dict(
            m=np.array([[1.00, 0.08, -0.05], [0.02, 0.99, -0.03], [-0.02, 0.07, 0.85]]),
            sat=0.80, gain=0.950, lift=0.060, lift_col=(1.02, 1.05, 0.80),
            high=(0.035, (0.92, 0.90, 0.55)),
        ),
        # 90s cable: bright SVHS-hot saturation, clean-ish whites
        "nick_90s": dict(
            m=np.array([[1.12, -0.05, -0.02], [-0.03, 1.07, -0.02], [-0.02, -0.04, 1.10]]),
            sat=1.30, gain=1.050, lift=0.022, lift_col=(1.06, 0.94, 1.08),
            high=(0.025, (1.0, 0.90, 0.96)),
        ),
        # 1994 alt-animation grunge: desaturated, contrasty, faintly bleached
        "mtv_1994": dict(
            m=np.array([[1.06, 0.03, -0.04], [0.00, 1.02, -0.02], [-0.01, 0.03, 0.96]]),
            sat=0.76, gain=1.065, lift=0.070, lift_col=(0.97, 1.00, 0.95),
            high=(0.020, (0.90, 0.92, 0.84)),
        ),
    }

    def prepare(self, ctx: Context) -> None:
        p = self._P[self.v["profile"]]
        s = float(self.v["strength"])
        self._duo = "duotone" in p
        if self._duo:
            return
        # Fold matrix · gain · lift · saturation · strength-mix into a single
        # affine transform x@A.T + b (all linear), leaving only the luma-masked
        # highlight tint as a per-frame nonlinearity. Exactly equivalent to the
        # sequential pipeline, ~3x faster.
        L = np.array([0.299, 0.587, 0.114], np.float32)
        M = p["m"].astype(np.float32) * p["gain"]
        lift = p["lift"]
        if lift > 0:
            A = M * (1.0 - lift)
            b = np.asarray(p["lift_col"], np.float32) * lift
        elif lift < 0:
            A = M * (1.0 - lift)
            b = np.full(3, lift, np.float32)
        else:
            A, b = M, np.zeros(3, np.float32)
        sat = p["sat"]
        S = sat * np.eye(3, dtype=np.float32) + (1.0 - sat) * np.outer(np.ones(3, np.float32), L)
        A, b = S @ A, S @ b
        hc = S @ np.asarray(p["high"][1], np.float32)  # tint rides through the sat op
        eye = np.eye(3, dtype=np.float32)
        A = (1.0 - s) * eye + s * A
        b = s * b
        self._M34 = np.hstack([A, b[:, None]]).astype(np.float32)
        self._high = (float(p["high"][0]) * s, hc.astype(np.float32))

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        s = float(self.v["strength"])
        if s <= 0:
            return frame
        if self._duo:
            p = self._P[self.v["profile"]]
            dark, paper = (np.asarray(c, np.float32) for c in p["duotone"])
            y = color.luma(frame)
            y = np.clip((y - 0.45) * 1.18 + 0.47, 0.0, 1.0)
            x = np.empty_like(frame)
            for c in range(3):
                x[..., c] = dark[c] + (paper[c] - dark[c]) * y
            if s < 1.0:
                x = frame * (1.0 - s) + x * s
            return np.clip(x, 0.0, 1.0).astype(np.float32)
        x = cv2.transform(np.ascontiguousarray(frame), self._M34)
        ha, hc = self._high
        if ha > 0:
            yl = np.clip(x @ self._LUMA, 0.0, 1.0)
            w = color.smoothstep(0.62, 0.95, yl)
            w *= ha
            for c in range(3):
                x[..., c] += hc[c] * w
        return np.clip(x, 0.0, 1.0).astype(np.float32)

    _LUMA = np.array([0.299, 0.587, 0.114], dtype=np.float32)
