"""Film-medium effects: grain, halation, gate weave, flicker, dust, scratches,
transport damage, cadence, vignette, light leaks and projection feel.

These model the *print/transport* layer of the film look. Print-level
artifacts (grain, dust, weave, flicker, scratches) key their randomness on
ctx.fi_out so they stay alive on every output frame even while a cadence
effect holds a source frame; content-level looks (light leaks) key on
ctx.fi_src.
"""

from __future__ import annotations

import numpy as np
import cv2

from ...engine import color
from ...engine.graph import Context, Effect, Param, register


# ── shared helpers ─────────────────────────────────────────────────────


def _screen(base: np.ndarray, glow: np.ndarray) -> np.ndarray:
    return 1.0 - (1.0 - base) * (1.0 - glow)


def _wide_blur(img: np.ndarray, sigma: float) -> np.ndarray:
    """Large-radius gaussian via downsample → blur → upsample (fast, soft)."""
    if sigma <= 2.5:
        return cv2.GaussianBlur(img, (0, 0), max(sigma, 0.3))
    h, w = img.shape[:2]
    ds = int(np.clip(sigma / 2.5, 1, 10))
    small = cv2.resize(img, (max(w // ds, 8), max(h // ds, 8)), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), sigma / ds)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)


def _coarse_kf(ctx: Context, key: str, k: int, gh: int, gw: int, sigma: float = 0.9) -> np.ndarray:
    """Deterministic coarse noise keyframe `k` for slowly-evolving spatial fields."""
    g = ctx.rng(f"{key}#{k}")
    f = g.standard_normal((gh, gw)).astype(np.float32)
    if sigma > 0:
        f = cv2.GaussianBlur(f, (0, 0), sigma)
    return f


class _EvolvingField:
    """Very-low-frequency spatial field that slowly crossfades between noise
    keyframes - the engine behind grain boiling, density mottle and decay
    animation. Bounded cache, bilinear upsample to frame size on demand."""

    def __init__(self, key: str, gh: int, gw: int, rate_hz: float, sigma: float = 0.9):
        self.key = key
        self.gh, self.gw = gh, gw
        self.rate = rate_hz
        self.sigma = sigma
        self._kf: dict[int, np.ndarray] = {}

    def _frame_kf(self, ctx: Context, k: int) -> np.ndarray:
        f = self._kf.get(k)
        if f is None:
            f = _coarse_kf(ctx, self.key, k, self.gh, self.gw, self.sigma)
            if len(self._kf) > 6:
                self._kf.clear()
            self._kf[k] = f
        return f

    def coarse(self, ctx: Context, t_s: float) -> np.ndarray:
        """Coarse (gh×gw) field at time t, ~N(0,1) per cell."""
        ph = t_s * self.rate
        k = int(np.floor(ph))
        fr = np.float32(ph - k)
        fr = fr * fr * (3.0 - 2.0 * fr)  # eased crossfade
        a, b = self._frame_kf(ctx, k), self._frame_kf(ctx, k + 1)
        # equal-power-ish mix keeps variance steady through the fade
        m = a * np.float32(np.sqrt(1.0 - fr)) + b * np.float32(np.sqrt(fr))
        return m

    def sample(self, ctx: Context, t_s: float, w: int, h: int) -> np.ndarray:
        return cv2.resize(self.coarse(ctx, t_s), (w, h), interpolation=cv2.INTER_LINEAR)


# ── grain ──────────────────────────────────────────────────────────────


@register
class Grain(Effect):
    eid = "grain"
    label = "Film Grain"
    kind = "frame"
    desc = "Multi-scale silver/dye grain with midtone-weighted response, per-stock character and optional color decorrelation."
    PARAMS = (
        Param("amount", "Amount", "float", 0.35, 0.0, 1.5, iscale=True, group="Grain",
              desc="Overall grain strength (noise level at midtones)."),
        Param("size", "Grain Size", "float", 2.0, 0.8, 6.0, unit="px", group="Grain",
              desc="Grain clump diameter in pixels, measured at whichever resolution Size Reference selects."),
        Param("size_ref", "Size Reference", "enum", "processing",
              choices=("processing", "output"), group="Grain",
              desc="Whether Grain Size means pixels at the era simulation resolution (processing) or in the "
                   "delivered file (output). Presets that simulate at a low era resolution magnify their grain "
                   "on the final upscale; 'output' compensates so the clumps stay the size you asked for."),
        Param("roughness", "Roughness", "float", 0.5, 0.0, 1.0, group="Grain",
              desc="Mix of a finer, sharper grain octave over the soft clumps."),
        Param("chroma_grain", "Color Grain", "float", 0.25, 0.0, 1.0, group="Grain",
              desc="Decorrelated per-channel grain (color negative) versus pure luma grain (prints, b&w)."),
        Param("stock", "Stock", "enum", "fine_35",
              choices=("fine_35", "newsreel_35", "doc_16", "super8", "push_process", "print_dupe"),
              group="Grain",
              desc="Film stock character: multiplies size/amount/color/clumping (explicit params still apply on top)."),
        Param("layers", "Layer Structure", "enum", "mono",
              choices=("mono", "color_neg", "reversal", "print_from_neg"), group="Grain",
              desc="Emulsion layer model: mono = single-layer (classic behavior); color_neg gives each channel its "
                   "own grain size (blue layer coarsest, red finest); reversal is tighter overall; print_from_neg "
                   "adds a second softer achromatic dupe-grain octave printed through from the negative."),
        Param("shadow_boost", "Shadow Boost", "float", 0.0, 0.0, 1.0, iscale=True, group="Response",
              desc="Pushes grain energy down into the shadows - the push-processed / underexposed look where "
                   "blacks crawl while highlights stay clean."),
        Param("intermittent", "Boiling", "float", 0.0, 0.0, 1.0, iscale=True, group="Response",
              desc="Grain 'boiling': a slowly evolving low-frequency unevenness of grain amplitude across the "
                   "frame, as real scans show - grain energy is never perfectly uniform."),
        Param("mottle", "Density Mottle", "float", 0.0, 0.0, 1.0, iscale=True, group="Response",
              desc="Very-low-frequency emulsion coating mottle: large soft ±1–2% density blotches drifting "
                   "slowly. Subliminal, but it is what makes a still frame read as a film scan."),
    )

    #            size  amount chroma rough  clump
    _STOCK = {
        "fine_35":      (1.00, 1.00, 1.00, 1.00, 0.7),
        "newsreel_35":  (1.20, 1.45, 0.40, 1.15, 1.1),
        "doc_16":       (1.60, 1.75, 0.55, 1.20, 1.2),
        "super8":       (2.30, 2.30, 0.90, 1.00, 1.4),
        "push_process": (1.35, 2.05, 0.70, 1.35, 1.8),
        "print_dupe":   (1.30, 1.50, 0.15, 0.75, 0.9),
    }

    # per-channel grain size ratios (R, G, B), overall size trim, dupe octave gain
    _LAYERS = {
        "color_neg":      ((0.85, 1.00, 1.35), 1.00, 0.0),
        "reversal":       ((0.88, 0.92, 1.08), 0.85, 0.0),
        "print_from_neg": ((0.95, 1.00, 1.12), 1.00, 0.62),
    }

    def prepare(self, ctx: Context) -> None:
        self._norm: dict = {}
        self._boil: _EvolvingField | None = None
        self._mot: _EvolvingField | None = None
        ar = ctx.width / max(ctx.height, 1)
        if self.v["intermittent"] > 0:
            self._boil = _EvolvingField(f"{self.key}:boil", 9, max(int(round(9 * ar)), 4), 1.35, sigma=0.75)
        if self.v["mottle"] > 0:
            self._mot = _EvolvingField(f"{self.key}:mottle", 6, max(int(round(6 * ar)), 3), 0.42, sigma=0.85)

    def _measured_norm(self, key: tuple, field: np.ndarray) -> float:
        n = self._norm.get(key)
        if n is None:
            n = 1.0 / (float(field.std()) + 1e-6)
            self._norm[key] = n
        return n

    def _response(self, frame: np.ndarray, amount: float, chroma: float, rough: float,
                  H: int, W: int, ctx: Context) -> np.ndarray:
        """Luminance response: peaks in midtones, falls off in deep shadow/highlight,
        reshaped by shadow_boost and modulated by the boiling field."""
        y = color.luma(frame)
        resp = 0.32 + 1.30 * np.sqrt(np.clip(y - y * y, 0.0, None))
        resp *= 0.30 + 0.70 * np.clip(y * 11.1, 0.0, 1.0)             # fade in from true black
        resp *= 1.0 - 0.55 * np.clip((y - 0.87) * 7.7, 0.0, 1.0)      # clear film = no grain in whites
        sb = self.v["shadow_boost"]
        if sb > 0:
            # push-processed: density (and grain) keeps building down into the toe
            lift = (1.0 - color.smoothstep(0.02, 0.55, y)) * (0.25 + 0.75 * np.clip(y * 16.0, 0.0, 1.0))
            resp += sb * 1.05 * lift
        c = chroma
        var = (1 - c) ** 2 + c * c + 1.155 * c * (1 - c) + (0.65 * rough) ** 2
        resp *= amount * 0.085 / np.sqrt(var)
        if self._boil is not None:
            it = self.v["intermittent"]
            mod = self._boil.sample(ctx, ctx.fi_out / max(ctx.fps, 1.0), W, H)
            resp *= np.clip(1.0 + it * 0.5 * mod, 0.12, 2.2)
        return resp

    def _grain_mono(self, frame: np.ndarray, amount: float, size: float, rough: float,
                    chroma: float, clm: float, H: int, W: int, ctx: Context) -> None:
        """Classic single-layer path - kept exactly as the original implementation."""
        g = ctx.frame_rng(f"{self.key}:grain")

        # coarse octave: soft organic clumps at the grain size
        sh, sw = max(int(round(H / size)), 8), max(int(round(W / size)), 8)
        field = g.standard_normal((sh, sw, 3), dtype=np.float32)
        field = cv2.GaussianBlur(field, (0, 0), 0.62)
        field = cv2.resize(field, (W, H), interpolation=cv2.INTER_LINEAR)
        norm = self._measured_norm(("c", sh, sw, H, W), field)
        # correlated (luma) component of the field, ~unit std
        shared = field @ np.full(3, 0.5773 * norm, np.float32)

        fine = None
        fnorm = 1.0
        if rough > 0:
            size2 = size * 0.45
            if size2 <= 1.05:
                fine = g.standard_normal((H, W), dtype=np.float32)
            else:
                fh, fw = max(int(round(H / size2)), 8), max(int(round(W / size2)), 8)
                fine = g.standard_normal((fh, fw), dtype=np.float32)
                fine = cv2.resize(fine, (W, H), interpolation=cv2.INTER_LINEAR)
                fnorm = self._measured_norm(("f", fh, fw, H, W), fine)

        resp = self._response(frame, amount, chroma, rough, H, W, ctx)

        base = shared * (1.0 - chroma)
        if fine is not None:
            base += fine * (0.65 * rough * fnorm)
        cnorm = chroma * norm
        if cnorm <= 0:
            base *= resp
            for ci in range(3):
                fc = frame[..., ci]
                fc += base
                np.clip(fc, 0.0, 1.0, out=fc)
        else:
            for ci in range(3):
                gc = field[..., ci] * cnorm
                gc += base
                gc *= resp
                fc = frame[..., ci]
                fc += gc
                np.clip(fc, 0.0, 1.0, out=fc)

        # occasional soft silver clumps at high amounts
        cl = max(0.0, amount - 0.42) * clm
        if cl > 0:
            k = max(int(size * 5), 5)
            tiny = g.standard_normal((H // k + 2, W // k + 2), dtype=np.float32)
            tiny = cv2.GaussianBlur(tiny, (0, 0), 1.0)
            tiny = cv2.resize(tiny, (W, H), interpolation=cv2.INTER_LINEAR)
            tiny *= self._measured_norm(("t", k, H, W), tiny)
            clumps = np.clip((tiny - 1.55) * 1.33, 0.0, 1.0)
            clumps *= clumps
            clumps *= resp * (cl * 0.11 / max(amount * 0.085, 1e-6))
            for ci in range(3):
                fc = frame[..., ci]
                fc -= clumps
                np.clip(fc, 0.0, 1.0, out=fc)

    def _layer_field(self, g: np.random.Generator, size: float, H: int, W: int,
                     tag: str, sigma: float = 0.62) -> np.ndarray:
        """One ~unit-std grain octave at `size` px, normalized by measured std."""
        if size <= 1.05:
            return g.standard_normal((H, W), dtype=np.float32)
        sh, sw = max(int(round(H / size)), 8), max(int(round(W / size)), 8)
        f = g.standard_normal((sh, sw), dtype=np.float32)
        f = cv2.GaussianBlur(f, (0, 0), sigma)
        f = cv2.resize(f, (W, H), interpolation=cv2.INTER_LINEAR)
        f *= self._measured_norm((tag, sh, sw, H, W), f)
        return f

    def _grain_layered(self, frame: np.ndarray, amount: float, size: float, rough: float,
                       chroma: float, clm: float, H: int, W: int, ctx: Context) -> None:
        """Per-layer path: each dye layer carries grain at its own scale.

        Real color negative resolves finest in the red-sensitive bottom layer
        and coarsest in the blue top layer; reversal is tighter throughout;
        prints from negative add an achromatic dupe-grain octave on top."""
        ratios, trim, dupe = self._LAYERS[self.v["layers"]]
        size = float(np.clip(size * trim, 0.8, 9.0))
        g = ctx.frame_rng(f"{self.key}:lgrain")

        # exposure-correlated component shared by all layers
        shared = self._layer_field(g, size, H, W, "ls")
        chans = [self._layer_field(g, float(np.clip(size * ratios[ci], 0.8, 12.0)), H, W, f"l{ci}")
                 for ci in range(3)]
        fine = None
        if rough > 0:
            fine = self._layer_field(g, max(size * 0.45, 0.8), H, W, "lf")
        dup = None
        if dupe > 0:
            # dupe grain: printed through from the negative - softer, larger, achromatic
            dup = self._layer_field(g, size * 1.9, H, W, "ld", sigma=0.9)

        resp = self._response(frame, amount, chroma, rough, H, W, ctx)

        cw, sw_ = chroma, 1.0 - chroma
        fw = 0.65 * rough
        dw = 0.7 * dupe
        # keep perceived level consistent with the mono path (fields independent here)
        var = sw_ * sw_ + cw * cw + fw * fw + dw * dw
        resp *= np.float32(np.sqrt(((1 - chroma) ** 2 + chroma ** 2 + 1.155 * chroma * (1 - chroma)
                                    + (0.65 * rough) ** 2) / max(var, 1e-6)))
        base = shared * sw_
        if fine is not None:
            base += fine * fw
        if dup is not None:
            base += dup * dw
        for ci in range(3):
            gc = chans[ci] * cw
            gc += base
            gc *= resp
            fc = frame[..., ci]
            fc += gc
            np.clip(fc, 0.0, 1.0, out=fc)

        # silver clump octave (as mono path, keyed off the shared stream)
        cl = max(0.0, amount - 0.42) * clm
        if cl > 0:
            k = max(int(size * 5), 5)
            tiny = g.standard_normal((H // k + 2, W // k + 2), dtype=np.float32)
            tiny = cv2.GaussianBlur(tiny, (0, 0), 1.0)
            tiny = cv2.resize(tiny, (W, H), interpolation=cv2.INTER_LINEAR)
            tiny *= self._measured_norm(("t", k, H, W), tiny)
            clumps = np.clip((tiny - 1.55) * 1.33, 0.0, 1.0)
            clumps *= clumps
            clumps *= resp * (cl * 0.11 / max(amount * 0.085, 1e-6))
            for ci in range(3):
                fc = frame[..., ci]
                fc -= clumps
                np.clip(fc, 0.0, 1.0, out=fc)

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        szm, am, chm, rgm, clm = self._STOCK[self.v["stock"]]
        amount = self.v["amount"] * am
        mot = self.v["mottle"]
        if amount <= 0 and mot <= 0:
            return frame
        H, W = frame.shape[:2]
        if amount > 0:
            size = self.v["size"] * szm
            if self.v["size_ref"] == "output":
                # generated here, but magnified by the final upscale - pre-shrink
                size /= max(ctx.upscale, 1e-3)
            size = float(np.clip(size, 0.8, 9.0))
            rough = float(np.clip(self.v["roughness"] * rgm, 0.0, 1.0))
            chroma = float(np.clip(self.v["chroma_grain"] * chm, 0.0, 1.0))
            if self.v["layers"] == "mono":
                self._grain_mono(frame, amount, size, rough, chroma, clm, H, W, ctx)
            else:
                self._grain_layered(frame, amount, size, rough, chroma, clm, H, W, ctx)
        if mot > 0 and self._mot is not None:
            # emulsion coating mottle: gentle density blotches, slowly drifting
            m = self._mot.sample(ctx, ctx.fi_out / max(ctx.fps, 1.0), W, H)
            gain = 1.0 + mot * np.float32(0.016) * m
            for ci in range(3):
                fc = frame[..., ci]
                fc *= gain
                np.clip(fc, 0.0, 1.0, out=fc)
        return frame


# ── halation ───────────────────────────────────────────────────────────


@register
class Halation(Effect):
    eid = "halation"
    label = "Halation"
    kind = "frame"
    desc = "Warm halo bleeding around highlights: light punching through the emulsion and reflecting off the film base."
    PARAMS = (
        Param("strength", "Strength", "float", 0.35, 0.0, 1.0, iscale=True, group="Glow",
              desc="How strongly highlights bloom outward."),
        Param("threshold", "Threshold", "float", 0.72, 0.4, 0.95, group="Glow",
              desc="Luma level where highlights start to bleed."),
        Param("radius", "Radius", "float", 0.055, 0.01, 0.25, unit="×H", group="Glow",
              desc="Halo radius as a fraction of frame height (resolution independent)."),
        Param("tint", "Tint", "enum", "red_orange",
              choices=("red", "red_orange", "orange", "warm_white", "neutral"), group="Glow",
              desc="Halo color; neutral suits black & white glow."),
        Param("double_pass", "Long Tails", "float", 0.0, 0.0, 1.0, iscale=True, group="Glow",
              desc="Second, much wider and fainter halo pass - real base reflections trail off far beyond a "
                   "single gaussian falloff."),
        Param("edge_only", "Edge Emphasis", "float", 0.0, 0.0, 1.0, group="Glow",
              desc="Suppresses the halo inside flat bright fields so it reads at dark–bright boundaries, where "
                   "halation is actually visible on a print."),
    )

    _TINT = {
        "red": (1.0, 0.24, 0.10),
        "red_orange": (1.0, 0.38, 0.12),
        "orange": (1.0, 0.52, 0.16),
        "warm_white": (1.0, 0.86, 0.62),
        "neutral": (0.93, 0.93, 0.93),
    }

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        s = self.v["strength"]
        if s <= 0:
            return frame
        H, W = frame.shape[:2]
        y = color.luma(frame)
        mask = color.smoothstep(self.v["threshold"], 1.0, y)
        if float(mask.max()) < 1e-3:
            return frame
        sigma = self.v["radius"] * H
        ds = int(np.clip(sigma / 3.0, 1, 10))
        small = np.ascontiguousarray(mask[::ds, ::ds])  # about to be blurred hard anyway
        small = cv2.GaussianBlur(small, (0, 0), 1.0)
        b1 = cv2.GaussianBlur(small, (0, 0), max(sigma / ds, 0.4))
        b2 = cv2.GaussianBlur(small, (0, 0), max(sigma * 0.32 / ds, 0.4))
        combo = 0.62 * b1 + 0.5 * b2
        dp = self.v["double_pass"]
        if dp > 0:
            # long tail: a third pass at ~2.6× radius, faint, mostly visible off dark surrounds
            b3 = cv2.GaussianBlur(small, (0, 0), max(sigma * 2.6 / ds, 0.5))
            combo = combo + dp * 0.42 * b3
        glow = cv2.resize(combo, (W, H), interpolation=cv2.INTER_LINEAR)
        eo = self.v["edge_only"]
        if eo > 0:
            # knock the halo back out of the bright field itself: what remains
            # hugs the dark side of dark–bright boundaries
            core = cv2.GaussianBlur(mask, (0, 0), max(sigma * 0.12, 0.8))
            glow *= 1.0 - eo * 0.9 * np.clip(core, 0.0, 1.0)
        tint = self._TINT[self.v["tint"]]
        for ci in range(3):
            k = tint[ci] * s * 1.6
            gc = glow * k
            if k > 1.0:
                np.clip(gc, 0.0, 1.0, out=gc)
            fc = frame[..., ci]
            gc *= 1.0 - fc  # screen blend
            fc += gc
        return frame


# ── release-print character ────────────────────────────────────────────


@register
class PrintChar(Effect):
    eid = "print_char"
    label = "Release Print Character"
    kind = "frame"
    desc = ("What generations of photochemical printing and a projector loop do to an image: development edge "
            "effects, dupe-contrast buildup, breathing blacks, an intruding frameline and rare perf light flashes.")
    PARAMS = (
        Param("acutance", "Edge Effect", "float", 0.0, 0.0, 1.0, iscale=True, group="Print",
              desc="Development adjacency effect: a faint dark line just inside the bright side of edges. "
                   "Unlike digital sharpening there is no bright halo - only the exhausted-developer line."),
        Param("dmax_breath", "Breathing Blacks", "float", 0.0, 0.0, 1.0, iscale=True, group="Print",
              desc="Projector flare lifts the blacks in step with overall scene brightness - Dmax breathes "
                   "as the picture cuts between bright and dark."),
        Param("contrast_buildup", "Dupe Generations", "int", 0, 0, 4, group="Print",
              desc="Each duplication generation adds S-curve contrast and loses a little detail. Pairs with "
                   "grain layers=print_from_neg."),
        Param("frameline", "Frameline", "float", 0.0, 0.0, 1.0, iscale=True, group="Gate",
              desc="Misframed projection: the dark frameline intrudes at the very top or bottom edge and "
                   "bounces slowly with the transport."),
        Param("perf_flash", "Perf Flashes", "float", 0.0, 0.0, 1.0, iscale=True, group="Gate",
              desc="Rare one-frame warm flashes hugging the left edge - light striking through the "
                   "perforation area when a splice lifts the film off the gate."),
    )

    def prepare(self, ctx: Context) -> None:
        self._ema: float | None = None
        self._lut: np.ndarray | None = None
        self._fl_track = None
        self._fl_side = 0
        if self.v["frameline"] > 0:
            self._fl_track = ctx.noise.smooth(f"{self.key}:fl", 0.45)
            self._fl_side = 0 if ctx.rng(f"{self.key}:flside").random() < 0.62 else 1  # top favored
        self._perf: dict[int, dict] = {}
        pf = self.v["perf_flash"]
        if pf > 0:
            ev = ctx.noise.events(f"{self.key}:perf", pf * 4.5 / 60.0, min_gap_s=2.0)
            g = ctx.rng(f"{self.key}:perfinit")
            for i in np.nonzero(ev)[0]:
                self._perf[int(i)] = dict(
                    inten=float(g.uniform(0.55, 1.0)), phase=float(g.uniform(0.0, 1.0)),
                    n=int(g.integers(3, 5)), tail=bool(g.random() < 0.45),
                )
                if self._perf[int(i)]["tail"]:
                    self._perf[int(i) + 1] = dict(self._perf[int(i)], inten=self._perf[int(i)]["inten"] * 0.35,
                                                  tail=False)

    def _dupe_lut(self, gens: int) -> np.ndarray:
        if self._lut is None:
            x = np.linspace(0.0, 1.0, 1024, dtype=np.float32)
            yv = x.copy()
            for _ in range(gens):
                s = yv * yv * (3.0 - 2.0 * yv)
                yv = yv + 0.17 * (s - yv)          # S-curve pivoting around mid
                yv = 0.010 + yv * (0.995 - 0.010)  # tiny fog + shoulder loss per generation
            self._lut = yv.astype(np.float32)
        return self._lut

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        H, W = frame.shape[:2]
        hscale = H / 1080.0

        gens = self.v["contrast_buildup"]
        if gens > 0:
            lut = self._dupe_lut(gens)
            idx = np.clip(frame * 1023.0, 0.0, 1023.0)
            lo = idx.astype(np.int32)
            fr = idx - lo
            hi = np.minimum(lo + 1, 1023)
            frame = (lut[lo] * (1.0 - fr) + lut[hi] * fr).astype(np.float32)
            frame = cv2.GaussianBlur(frame, (0, 0), (0.28 + 0.16 * gens) * max(hscale, 0.4))

        ac = self.v["acutance"]
        if ac > 0:
            y = color.luma(frame)
            blur = cv2.GaussianBlur(y, (0, 0), 1.7 * max(hscale, 0.4))
            hp = y - blur                       # positive just inside the bright side
            line = np.clip(hp, 0.0, None)
            line = cv2.GaussianBlur(line, (0, 0), 0.65 * max(hscale, 0.4))
            line *= ac * 2.0
            np.clip(line, 0.0, 0.30, out=line)
            for ci in range(3):
                frame[..., ci] *= 1.0 - line

        db = self.v["dmax_breath"]
        if db > 0:
            m = float(color.luma(frame[::8, ::8]).mean())
            a = 1.0 - float(np.exp(-1.0 / (max(ctx.fps, 1.0) * 0.35)))
            self._ema = m if self._ema is None else self._ema + a * (m - self._ema)
            lift = db * 0.055 * float(np.clip(self._ema * 1.8, 0.0, 1.2))
            if lift > 1e-4:
                lc = (lift, lift * 0.94, lift * 0.85)  # lamp-warm flare
                for ci in range(3):
                    fc = frame[..., ci]
                    fc *= 1.0 - lc[ci]
                    fc += lc[ci]

        flv = self.v["frameline"]
        if flv > 0 and self._fl_track is not None:
            b = float(self._fl_track[min(ctx.fi_out, len(self._fl_track) - 1)])
            intr = flv * H * (0.011 + 0.011 * (0.5 + 0.5 * b))
            if intr > 0.75:
                n = int(min(intr * 2.2, H * 0.08))
                yy = np.arange(n, dtype=np.float32)
                prof = 1.0 - color.smoothstep(intr * 0.55, intr * 1.15, yy)
                # thin printed-through light line right at the frame edge
                glint = np.exp(-0.5 * ((yy - intr) / max(intr * 0.14, 0.6)) ** 2) * 0.05 * flv
                mult = (1.0 - 0.92 * prof + glint)[:, None, None].astype(np.float32)
                if self._fl_side == 0:
                    frame[:n] *= mult
                    np.clip(frame[:n], 0.0, 1.0, out=frame[:n])
                else:
                    frame[H - n:] *= mult[::-1]
                    np.clip(frame[H - n:], 0.0, 1.0, out=frame[H - n:])

        pev = self._perf.get(ctx.fi_out)
        if pev is not None:
            hs, ws = max(H // 8, 8), max(W // 8, 8)
            yy = (np.arange(hs, dtype=np.float32) + 0.5) / hs
            xx = (np.arange(ws, dtype=np.float32) + 0.5) / ws
            edge = np.exp(-xx / 0.055)[None, :]
            cy = (np.arange(pev["n"], dtype=np.float32) + 0.5 + pev["phase"]) / pev["n"]
            bumps = np.zeros(hs, np.float32)
            for c in cy:
                bumps += np.exp(-0.5 * (((yy - (c % 1.0)) * pev["n"]) / 0.30) ** 2)
            m = (0.25 + 0.75 * np.clip(bumps, 0.0, 1.0))[:, None] * edge
            m *= pev["inten"] * self.v["perf_flash"] * 1.15
            leak = cv2.resize(m.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
            col = (1.0, 0.80, 0.52)
            for ci in range(3):
                fc = frame[..., ci]
                fc += leak * col[ci] * (1.0 - fc)
            np.clip(frame, 0.0, 1.0, out=frame)
        return frame


# ── gate weave ─────────────────────────────────────────────────────────


@register
class GateWeave(Effect):
    eid = "gate_weave"
    label = "Gate Weave"
    kind = "frame"
    desc = "The gate never holds film perfectly still: slow subpixel drift, vertical jitter, micro-rotation and splice bumps."
    PARAMS = (
        Param("amount", "Amount", "float", 1.5, 0.0, 8.0, unit="px", iscale=True, group="Movement",
              desc="Weave amplitude in pixels (subpixel capable)."),
        Param("hz", "Weave Speed", "float", 0.6, 0.1, 3.0, unit="Hz", group="Movement",
              desc="How fast the frame wanders in the gate."),
        Param("rotation", "Rotation", "float", 0.05, 0.0, 0.3, unit="°", group="Movement",
              desc="Micro-rotation component of the weave."),
        Param("splice_bump", "Splice Bumps", "float", 1.0, 0.0, 12.0, unit="/min", group="Movement",
              desc="Rate of sudden vertical jumps as bad splices pass the gate."),
    )

    def prepare(self, ctx: Context) -> None:
        hz = self.v["hz"]
        self._tx = ctx.noise.smooth(f"{self.key}:x", hz)
        self._ty = ctx.noise.smooth(f"{self.key}:y", hz * 1.17)
        self._tj = ctx.noise.smooth(f"{self.key}:jit", min(hz * 5.0, 6.0))
        self._tr = ctx.noise.smooth(f"{self.key}:rot", hz * 0.6)
        n = ctx.n_frames
        bump = np.zeros(n + 8, np.float32)
        if self.v["splice_bump"] > 0:
            ev = ctx.noise.events(f"{self.key}:splice", self.v["splice_bump"] / 60.0, min_gap_s=1.0)
            g = ctx.rng(f"{self.key}:bumps")
            kern = np.array([1.0, 0.52, 0.27, 0.13, 0.05], np.float32)
            for i in np.nonzero(ev)[0]:
                amp = g.uniform(2.0, 6.0) * (1.0 if g.random() < 0.7 else -1.0)
                bump[i : i + 5] += amp * kern
        self._bump = bump

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        fi = min(ctx.fi_out, len(self._tx) - 1)
        a = self.v["amount"]
        dx = float(self._tx[fi]) * a
        dy = float(self._ty[fi]) * a * 0.85 + float(self._tj[fi]) * a * 0.30 + float(self._bump[fi])
        ang = float(self._tr[fi]) * self.v["rotation"]
        if abs(dx) < 1e-3 and abs(dy) < 1e-3 and abs(ang) < 1e-4:
            return frame
        H, W = frame.shape[:2]
        M = cv2.getRotationMatrix2D((W / 2.0, H / 2.0), ang, 1.0)
        M[0, 2] += dx
        M[1, 2] += dy
        return cv2.warpAffine(frame, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


# ── flicker ────────────────────────────────────────────────────────────


@register
class Flicker(Effect):
    eid = "flicker"
    label = "Exposure Flicker"
    kind = "frame"
    desc = "Frame-to-frame exposure instability: lamp drift, shutter beat or hand-cranked wobble, optionally uneven across the frame."
    PARAMS = (
        Param("amount", "Amount", "float", 0.25, 0.0, 1.0, iscale=True, group="Exposure",
              desc="Depth of the brightness fluctuation."),
        Param("character", "Character", "enum", "slow_drift",
              choices=("slow_drift", "projector", "hand_cranked"), group="Exposure",
              desc="Frequency content: lamp drift, projector shutter beat, or strong fast hand-crank wobble."),
        Param("color_flicker", "Color Flicker", "float", 0.1, 0.0, 1.0, group="Exposure",
              desc="Small independent RGB gain wobble (early color processes)."),
        Param("spatial", "Spatial Unevenness", "float", 0.2, 0.0, 1.0, group="Exposure",
              desc="Makes the flicker slightly uneven across the frame with a drifting orientation."),
    )

    def prepare(self, ctx: Context) -> None:
        a = self.v["amount"]
        ch = self.v["character"]
        if ch == "slow_drift":
            t = ctx.noise.onef(f"{self.key}:g", 1.7)
            amp = 0.10
        elif ch == "projector":
            t = 0.7 * ctx.noise.smooth(f"{self.key}:g", 6.5) + 0.5 * ctx.noise.smooth(f"{self.key}:g2", 1.0)
            amp = 0.09
        else:  # hand_cranked
            t = 0.85 * ctx.noise.smooth(f"{self.key}:g", 2.6) + 0.6 * ctx.noise.smooth(f"{self.key}:g2", 0.45)
            amp = 0.20
        self._gain = np.clip(1.0 + a * amp * t, 0.3, 1.9).astype(np.float32)
        cf = self.v["color_flicker"]
        self._rgb = None
        if cf > 0:
            chans = [ctx.noise.smooth(f"{self.key}:c{c}", 1.8) for c in "rgb"]
            self._rgb = np.clip(1.0 + cf * 0.05 * np.stack(chans, axis=-1), 0.7, 1.3).astype(np.float32)
        self._theta = ctx.noise.smooth(f"{self.key}:th", 0.15) * np.pi
        self._grids: tuple | None = None

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        fi = min(ctx.fi_out, len(self._gain) - 1)
        gains = [float(self._gain[fi])] * 3
        if self._rgb is not None:
            gains = [gains[c] * float(self._rgb[fi][c]) for c in range(3)]
        sp = self.v["spatial"] * self.v["amount"]
        ramp = None
        if sp > 0:
            H, W = frame.shape[:2]
            if self._grids is None or self._grids[0].shape != (H, W):
                yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
                self._grids = (xx / max(W - 1, 1) * 2 - 1, yy / max(H - 1, 1) * 2 - 1)
            xx, yy = self._grids
            th = float(self._theta[fi])
            ramp = xx * np.float32(np.cos(th)) + yy * np.float32(np.sin(th))
            ramp *= np.float32(sp * 0.30)
            ramp += 1.0
        may_exceed = max(gains) * (1.0 + sp * 0.30 * 1.4143) > 1.0  # ramp peaks at sqrt(2) on diagonals
        for ci in range(3):
            fc = frame[..., ci]
            if ramp is not None:
                fc *= ramp
            fc *= gains[ci]
            if may_exceed:
                np.clip(fc, 0.0, 1.0, out=fc)
        return frame


# ── dust ───────────────────────────────────────────────────────────────


@register
class Dust(Effect):
    eid = "dust"
    label = "Dust & Dirt"
    kind = "frame"
    desc = "Transient print dirt: dark and bright specks, irregular smudges and thin curved hairs caught in the gate."
    PARAMS = (
        Param("density", "Density", "float", 0.35, 0.0, 1.0, iscale=True, group="Damage",
              desc="How much dirt appears per frame (area-scaled), with occasional dirty-frame bursts."),
        Param("size", "Size", "float", 1.0, 0.4, 3.0, group="Damage",
              desc="Multiplier on speck sizes (log-distributed 1–6 px)."),
        Param("polarity", "Polarity", "enum", "print",
              choices=("print", "negative", "both"), group="Damage",
              desc="print = mostly dark dirt, negative = mostly white (dirt printed from the negative), both = mixed."),
        Param("hairs", "Hairs", "float", 0.25, 0.0, 1.0, group="Damage",
              desc="Probability of thin curved hairs, occasionally lingering a few frames."),
    )

    def prepare(self, ctx: Context) -> None:
        self._lingering: list[dict] = []

    def _dark_frac(self) -> float:
        return {"print": 0.85, "negative": 0.15, "both": 0.5}[self.v["polarity"]]

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        den = self.v["density"]
        if den <= 0 and not self._lingering:
            return frame
        H, W = frame.shape[:2]
        g = ctx.frame_rng(f"{self.key}:d")
        area = (H * W) / 9.2e5
        mean = den * 11.0 * area
        if g.random() < den * 0.045:  # dirty-frame burst
            mean *= g.uniform(4.0, 9.0)
        n = int(g.poisson(mean)) if mean > 0 else 0

        dark = None
        light = None
        bbox = [W, H, 0, 0]  # x0, y0, x1, y1 of everything drawn

        def _grow(x0: float, y0: float, x1: float, y1: float) -> None:
            bbox[0] = min(bbox[0], int(x0))
            bbox[1] = min(bbox[1], int(y0))
            bbox[2] = max(bbox[2], int(x1) + 1)
            bbox[3] = max(bbox[3], int(y1) + 1)

        def _mask(is_dark: bool):
            nonlocal dark, light
            if is_dark:
                if dark is None:
                    dark = np.zeros((H, W), np.float32)
                return dark
            if light is None:
                light = np.zeros((H, W), np.float32)
            return light

        dfrac = self._dark_frac()
        size_m = self.v["size"]
        if n > 0:
            xs = g.uniform(0, W, n)
            ys = g.uniform(0, H, n)
            rads = np.clip(np.exp(g.normal(0.22, 0.55, n)) * size_m, 0.5, 6.5)
            vals = g.uniform(0.35, 0.9, n)
            darks = g.random(n) < dfrac
            for i in range(n):
                m = _mask(bool(darks[i]))
                r = float(rads[i])
                c = (int(xs[i]), int(ys[i]))
                if r > 2.4 and g.random() < 0.5:  # elongated speck
                    ax = (int(r * g.uniform(1.2, 2.2)), max(int(r * 0.6), 1))
                    cv2.ellipse(m, c, ax, float(g.uniform(0, 180)), 0, 360, float(vals[i]), -1, cv2.LINE_AA)
                    r *= 2.3
                else:
                    cv2.circle(m, c, max(int(round(r)), 1), float(vals[i]), -1, cv2.LINE_AA)
                _grow(c[0] - r, c[1] - r, c[0] + r, c[1] + r)

        # larger irregular smudge blobs
        if den > 0 and g.random() < den * 0.22:
            for _ in range(1 + int(g.random() < 0.3)):
                cx, cy = g.uniform(0, W), g.uniform(0, H)
                base_r = g.uniform(3.0, 11.0) * size_m
                npts = int(g.integers(3, 7))
                angs = np.sort(g.uniform(0, 2 * np.pi, npts))
                rr = base_r * g.uniform(0.55, 1.4, npts)
                pts = np.stack([cx + rr * np.cos(angs), cy + rr * np.sin(angs)], axis=-1).astype(np.int32)
                m = _mask(g.random() < dfrac)
                cv2.fillPoly(m, [pts], float(g.uniform(0.25, 0.6)), cv2.LINE_AA)
                _grow(pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max())

        # hairs: thin curved polylines, sometimes lingering
        if self.v["hairs"] > 0 and g.random() < self.v["hairs"] * 0.13:
            x0, y0 = g.uniform(0, W), g.uniform(0, H)
            ang = g.uniform(0, 2 * np.pi)
            npts = int(g.integers(3, 6))
            step = g.uniform(8, 25)
            pts = [(x0, y0)]
            for _ in range(npts - 1):
                ang += g.uniform(-0.55, 0.55)
                x0, y0 = x0 + np.cos(ang) * step, y0 + np.sin(ang) * step
                pts.append((x0, y0))
            life = 1 + (int(g.integers(1, 4)) if g.random() < 0.35 else 0)
            self._lingering.append(dict(
                pts=np.asarray(pts, np.float32), life=life,
                dark=bool(g.random() < 0.75), val=float(g.uniform(0.35, 0.6)),
            ))

        still = []
        for hair in self._lingering:
            wob = g.normal(0.0, 0.7, 2).astype(np.float32)
            p = (hair["pts"] + wob).astype(np.int32)
            cv2.polylines(_mask(hair["dark"]), [p], False, hair["val"], 1, cv2.LINE_AA)
            _grow(p[:, 0].min(), p[:, 1].min(), p[:, 0].max(), p[:, 1].max())
            hair["life"] -= 1
            if hair["life"] > 0:
                still.append(hair)
        self._lingering = still

        if dark is None and light is None:
            return frame
        # apply only inside the padded bounding box of what was drawn
        x0, y0 = max(bbox[0] - 4, 0), max(bbox[1] - 4, 0)
        x1, y1 = min(bbox[2] + 4, W), min(bbox[3] + 4, H)
        if x1 <= x0 or y1 <= y0:
            return frame
        region = frame[y0:y1, x0:x1]
        if dark is not None:
            d = cv2.GaussianBlur(dark[y0:y1, x0:x1], (0, 0), 0.65)
            np.clip(d, 0.0, 1.0, out=d)
            region *= 1.0 - d[..., None] * 0.95
        if light is not None:
            l = cv2.GaussianBlur(light[y0:y1, x0:x1], (0, 0), 0.65)
            np.clip(l, 0.0, 1.0, out=l)
            region += np.clip(0.93 - region, 0.0, None) * l[..., None]
        return frame


# ── scratches ──────────────────────────────────────────────────────────


@register
class Scratches(Effect):
    eid = "scratches"
    label = "Tramline Scratches"
    kind = "frame"
    desc = "Vertical tramline scratches that wander, flicker and break into dashes, plus one-frame transient scratches."
    PARAMS = (
        Param("strength", "Strength", "float", 0.5, 0.0, 1.0, iscale=True, group="Damage",
              desc="Opacity of the scratch lines."),
        Param("count", "Persistent Lines", "int", 2, 0, 8, group="Damage",
              desc="Number of long-lived scratch slots (each cycles alive/dead over time)."),
        Param("wander", "Wander", "float", 0.5, 0.0, 3.0, unit="px/frame", group="Damage",
              desc="How far a scratch random-walks sideways per frame."),
        Param("transient_rate", "Transients", "float", 4.0, 0.0, 30.0, unit="/min", group="Damage",
              desc="Rate of scratches that appear for a single frame."),
        Param("emulsion_side", "Emulsion Scratches", "float", 0.0, 0.0, 1.0, group="Damage",
              desc="Fraction of persistent scratches that gouge the emulsion instead of the base - dye layers "
                   "torn away refract green/orange with a complementary fringe, instead of a neutral line."),
        Param("gouge_rate", "Gouges", "float", 0.0, 0.0, 10.0, unit="/min", group="Damage",
              desc="Rare deep gouges: a wide ragged dark gash with torn bright edges, lasting one to three frames."),
    )

    def prepare(self, ctx: Context) -> None:
        n, fps = ctx.n_frames, ctx.fps
        rng = ctx.rng(f"{self.key}:init")
        self._segs: list[dict] = []
        for _slot in range(self.v["count"]):
            t = int(rng.uniform(0.0, 4.0) * fps) if rng.random() < 0.6 else 0
            while t < n:
                dur = max(int(rng.uniform(1.2, 9.0) * fps), 2)
                seed = int(rng.integers(1 << 30))
                self._segs.append(dict(
                    f0=t, f1=min(t + dur, n),
                    x0=rng.uniform(0.04, 0.96),
                    walk=np.cumsum(rng.uniform(-self.v["wander"], self.v["wander"], dur)).astype(np.float32),
                    bright=bool(rng.random() < 0.55),
                    w=float(rng.uniform(0.55, 1.3)),
                    inten=float(rng.uniform(0.28, 0.75)),
                    yspan=(0.0, 1.0) if rng.random() < 0.6 else tuple(sorted((rng.uniform(0, 0.55), rng.uniform(0.45, 1.0)))),
                    dashy=bool(rng.random() < 0.45),
                    seed=seed,
                ))
                t += dur + int(rng.uniform(0.8, 7.0) * fps)
        # per-segment temporal tracks
        self._fl = {s["seed"]: ctx.noise.smooth(f"{self.key}:fl{s['seed']}", 3.0) for s in self._segs}
        self._da = {s["seed"]: ctx.noise.smooth(f"{self.key}:da{s['seed']}", 0.5) for s in self._segs}
        self._tev = ctx.noise.events(f"{self.key}:trans", self.v["transient_rate"] / 60.0, min_gap_s=0.3)
        self._vp_cache: dict = {}
        emu = self.v["emulsion_side"]
        if emu > 0:  # separate stream: never disturbs the classic init draws
            ge = ctx.rng(f"{self.key}:emul")
            for seg in self._segs:
                if ge.random() < emu:
                    seg["emul"] = float(ge.random())  # 0 → green, 1 → orange
        self._gouges: list[dict] = []
        if self.v["gouge_rate"] > 0:
            gg = ctx.rng(f"{self.key}:gougeinit")
            ev = ctx.noise.events(f"{self.key}:gouge", self.v["gouge_rate"] / 60.0, min_gap_s=2.5)
            for i in np.nonzero(ev)[0]:
                self._gouges.append(dict(
                    f0=int(i), dur=int(gg.integers(1, 4)), x=float(gg.uniform(0.06, 0.94)),
                    w=float(gg.uniform(2.2, 5.5)), inten=float(gg.uniform(0.55, 0.95)),
                    seed=int(gg.integers(1 << 30)),
                ))

    def _vprofile(self, seg: dict, H: int) -> np.ndarray:
        key = (seg["seed"], H)
        vp = self._vp_cache.get(key)
        if vp is None:
            y = np.linspace(0.0, 1.0, H, dtype=np.float32)
            y0, y1 = seg["yspan"]
            if (y0, y1) == (0.0, 1.0):
                vp = np.ones(H, np.float32)
            else:
                vp = color.smoothstep(y0, y0 + 0.08, y) * (1.0 - color.smoothstep(y1 - 0.08, y1, y))
            self._vp_cache[key] = vp
        return vp

    def _draw_line(self, frame: np.ndarray, xc: float, w: float, inten: float,
                   bright: bool, vmod: np.ndarray, emul: float | None = None) -> None:
        H, W = frame.shape[:2]
        half = max(int(3 * w + 1), 2)
        c0, c1 = int(np.clip(xc - half, 0, W - 1)), int(np.clip(xc + half + 1, 1, W))
        if c1 <= c0:
            return
        xg = np.arange(c0, c1, dtype=np.float32) - xc
        prof = np.exp(-0.5 * (xg / max(w, 0.3)) ** 2) * inten
        sign = 0.55 if bright else -0.40
        if emul is None:
            frame[:, c0:c1] += (vmod[:, None] * prof[None, :] * sign)[..., None]
            return
        # emulsion-side scratch: torn dye layers refract color - a green↔orange
        # core with a fainter complementary fringe hugging one flank
        t = emul
        colw = (np.asarray((0.30, 1.00, 0.42), np.float32) * (1.0 - t)
                + np.asarray((1.00, 0.58, 0.18), np.float32) * t)
        comp = np.clip(np.float32(1.15) - colw, 0.0, 1.0)
        prof2 = np.exp(-0.5 * ((xg - 1.5 * max(w, 0.5)) / max(w * 0.8, 0.3)) ** 2) * inten
        base = vmod[:, None] * prof[None, :] * (sign * 1.15)
        fringe = vmod[:, None] * prof2[None, :] * (-sign * 0.55)
        for ci in range(3):
            frame[:, c0:c1, ci] += base * colw[ci] + fringe * comp[ci]

    def _draw_gouge(self, frame: np.ndarray, gg: dict, fi: int, s: float, ctx: Context) -> None:
        H, W = frame.shape[:2]
        gr = ctx.frame_rng(f"{self.key}:gg{gg['seed']}")
        age = fi - gg["f0"]
        fade = (1.0, 0.62, 0.38)[min(age, 2)] * (0.82 + 0.36 * float(gr.random()))
        wpx = gg["w"] * max(H / 720.0, 0.6)
        # ragged per-row center: the gouge tears, it doesn't rule a line
        v = np.repeat(gr.standard_normal(H // 16 + 2).astype(np.float32), 16)[:H]
        v = np.convolve(v, np.ones(13, np.float32) / 13.0, mode="same")
        xc_row = gg["x"] * W + v * (1.6 * wpx)
        half = int(4.5 * wpx + 3)
        c0 = int(np.clip(gg["x"] * W - half, 0, W - 1))
        c1 = int(np.clip(gg["x"] * W + half + 1, 1, W))
        if c1 <= c0:
            return
        xs = np.arange(c0, c1, dtype=np.float32)[None, :]
        d = xs - xc_row[:, None]
        core = np.exp(-0.5 * (d / max(wpx, 0.5)) ** 2)
        edge = np.exp(-0.5 * ((np.abs(d) - 2.1 * wpx) / max(wpx * 0.55, 0.4)) ** 2)
        inten = gg["inten"] * s * fade
        # depth varies down the gash; occasionally it skips
        depth = np.clip(0.55 + 0.45 * v, 0.15, 1.1)[:, None]
        region = frame[:, c0:c1]
        region *= 1.0 - np.clip(core * depth * (inten * 0.9), 0.0, 0.95)[..., None]
        region += (edge * depth * (inten * 0.35))[..., None]

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        s = self.v["strength"]
        if s <= 0:
            return frame
        H, W = frame.shape[:2]
        fi = ctx.fi_out
        drew = False
        for seg in self._segs:
            if not (seg["f0"] <= fi < seg["f1"]):
                continue
            xc = seg["x0"] * W + float(seg["walk"][fi - seg["f0"]])
            if xc < 1 or xc > W - 2:
                continue
            fl = self._fl[seg["seed"]]
            flick = 0.75 + 0.25 * float(fl[min(fi, len(fl) - 1)])
            # per-frame vertical intensity variation (broken dashes at times)
            gv = ctx.frame_rng(f"{self.key}:v{seg['seed']}")
            coarse = gv.standard_normal(H // 24 + 2).astype(np.float32)
            v = np.repeat(coarse, 24)[:H]
            v = np.convolve(v, np.ones(9, np.float32) / 9.0, mode="same")
            vmod = self._vprofile(seg, H) * (0.72 + 0.28 * np.clip(v, -1.5, 1.5))
            da = self._da[seg["seed"]]
            if seg["dashy"] and float(da[min(fi, len(da) - 1)]) > 0.35:
                vmod = vmod * color.smoothstep(-0.25, 0.35, v)
            self._draw_line(frame, xc, seg["w"], seg["inten"] * s * flick, seg["bright"], vmod,
                            emul=seg.get("emul"))
            drew = True
        if fi < len(self._tev) and self._tev[fi] > 0:
            gt = ctx.frame_rng(f"{self.key}:t")
            for _ in range(int(gt.integers(1, 4))):
                v = np.repeat(gt.standard_normal(H // 24 + 2).astype(np.float32), 24)[:H]
                v = np.convolve(v, np.ones(9, np.float32) / 9.0, mode="same")
                vmod = np.clip(0.7 + 0.3 * v, 0.0, 1.2).astype(np.float32)
                self._draw_line(frame, gt.uniform(2, W - 2), gt.uniform(0.5, 0.9),
                                gt.uniform(0.2, 0.5) * s, bool(gt.random() < 0.5), vmod)
            drew = True
        for gg in self._gouges:
            if gg["f0"] <= fi < gg["f0"] + gg["dur"]:
                self._draw_gouge(frame, gg, fi, s, ctx)
                drew = True
        if drew:
            np.clip(frame, 0.0, 1.0, out=frame)
        return frame


# ── frame damage / transport events ────────────────────────────────────


@register
class FrameDamage(Effect):
    eid = "frame_damage"
    label = "Frame Damage"
    kind = "frame"
    desc = "Physical transport events: splice skips with a visible splice bar, vertical slips, evolving chemical blotches and an optional film burn."
    PARAMS = (
        Param("splice_skip_rate", "Splice Skips", "float", 2.0, 0.0, 20.0, unit="/min", group="Damage",
              desc="Bad splices: a few source frames skip and a splice bar crosses the frame."),
        Param("slip_rate", "Frame Slips", "float", 1.5, 0.0, 20.0, unit="/min", group="Damage",
              desc="One-frame vertical rolls exposing the frameline."),
        Param("blotch_rate", "Blotches", "float", 4.0, 0.0, 40.0, unit="/min", group="Damage",
              desc="Chemical blotches that grow over a few frames then vanish."),
        Param("burn", "Film Burn", "bool", False, group="Damage",
              desc="Dramatic burn-through: a growing orange→brown→white hole."),
        Param("burn_at_s", "Burn Time", "float", 2.0, 0.0, 600.0, unit="s", group="Damage",
              desc="When the burn starts."),
        Param("static_flash", "Static Flashes", "float", 0.0, 0.0, 20.0, unit="/min", group="Damage",
              desc="Static discharge marks: one-frame branching bright streaks jumping in from a frame edge "
                   "(dry rewind sparks exposing the stock), most visible on dark scenes."),
        Param("mold_edge", "Edge Mold", "float", 0.0, 0.0, 1.0, iscale=True, group="Damage",
              desc="Constant faint organic mottled darkening creeping in from the frame edges - mildew "
                   "blooming between the reel wraps."),
    )

    def prepare(self, ctx: Context) -> None:
        n, fps = ctx.n_frames, ctx.fps
        g = ctx.rng(f"{self.key}:events")
        self._splice: dict[int, dict] = {}
        for i in np.nonzero(ctx.noise.events(f"{self.key}:splice", self.v["splice_skip_rate"] / 60.0, min_gap_s=2.0))[0]:
            self._splice[int(i)] = dict(
                skip=int(g.integers(2, 6)), bar_y=g.uniform(0.30, 0.70),
                roll=g.uniform(0.10, 0.20) * (1 if g.random() < 0.5 else -1),
                seed=int(g.integers(1 << 30)),
            )
        self._slip: dict[int, dict] = {}
        for i in np.nonzero(ctx.noise.events(f"{self.key}:slip", self.v["slip_rate"] / 60.0, min_gap_s=2.0))[0]:
            if int(i) in self._splice:
                continue
            self._slip[int(i)] = dict(shift=g.uniform(0.12, 0.42) * (1 if g.random() < 0.5 else -1))
        self._blotches: list[dict] = []
        for i in np.nonzero(ctx.noise.events(f"{self.key}:blotch", self.v["blotch_rate"] / 60.0, min_gap_s=0.2))[0]:
            for _ in range(1 + int(g.random() < 0.3)):
                self._blotches.append(dict(
                    birth=int(i), life=int(g.integers(3, 9)),
                    cx=g.uniform(0.08, 0.92), cy=g.uniform(0.08, 0.92),
                    r=g.uniform(0.05, 0.16),
                    a1=g.uniform(0.12, 0.35), a2=g.uniform(0.08, 0.25),
                    p1=g.uniform(0, 2 * np.pi), p2=g.uniform(0, 2 * np.pi),
                    sepia=bool(g.random() < 0.5), inten=g.uniform(0.5, 0.95),
                ))
        self._burn_f0 = ctx.frame_of(self.v["burn_at_s"])
        self._burn_dur = max(int(1.1 * fps), 4)
        self._burn_noise: np.ndarray | None = None
        self._burn_grid: tuple | None = None
        self._flash: dict[int, int] = {}
        if self.v["static_flash"] > 0:
            gs = ctx.rng(f"{self.key}:staticseed")
            for i in np.nonzero(ctx.noise.events(f"{self.key}:static",
                                                 self.v["static_flash"] / 60.0, min_gap_s=1.0))[0]:
                self._flash[int(i)] = int(gs.integers(1 << 30))
        self._mold_mask: np.ndarray | None = None
        self._mold_breath = ctx.noise.smooth(f"{self.key}:moldb", 0.07) if self.v["mold_edge"] > 0 else None

    def remap(self, ctx: Context) -> np.ndarray | None:
        if not self._splice:
            return None
        n = ctx.n_frames
        delta = np.zeros(n, np.int64)
        for fi, sp in self._splice.items():
            if fi < n:
                delta[fi:] += sp["skip"]
        return np.arange(n, dtype=np.int64) + delta

    # ── drawing helpers ────────────────────────────────────────────────

    def _frameline(self, frame: np.ndarray, seam: float, width_frac: float = 0.035) -> None:
        H = frame.shape[0]
        yy = np.arange(H, dtype=np.float32)
        band = np.clip(1.0 - np.abs(yy - seam) / max(width_frac * H, 2.0), 0.0, 1.0) ** 1.5
        frame *= (1.0 - 0.92 * band)[:, None, None]

    def _draw_splice(self, frame: np.ndarray, sp: dict, ctx: Context) -> np.ndarray:
        H, W = frame.shape[:2]
        roll = int(sp["roll"] * H)
        frame = np.roll(frame, roll, axis=0)
        seam = float(roll % H)
        self._frameline(frame, seam)
        # scuffed white splice bar with ragged edges + dark cement line
        g = ctx.frame_rng(f"{self.key}:bar{sp['seed']}")
        ybar = sp["bar_y"] * H
        hb = 0.045 * H
        edge = g.standard_normal(W).astype(np.float32)
        edge = np.convolve(edge, np.ones(31, np.float32) / 31.0, mode="same") * (0.35 * hb)
        y0, y1 = int(max(ybar - hb * 1.6, 0)), int(min(ybar + hb * 1.6, H))
        if y1 > y0:
            yy = np.arange(y0, y1, dtype=np.float32)[:, None]
            top = ybar - hb * 0.5 + edge[None, :]
            bot = ybar + hb * 0.5 + edge[None, :] * 0.6
            m = np.clip((yy - top) / 2.0, 0, 1) * np.clip((bot - yy) / 2.0, 0, 1)
            region = frame[y0:y1]
            white = np.asarray((0.88, 0.86, 0.80), np.float32)
            region[...] = region * (1.0 - (m * 0.82)[..., None]) + white * (m * 0.82)[..., None]
            cy = int(np.clip(ybar - y0, 1, y1 - y0 - 2))
            region[cy : cy + 2] *= 0.18
        return frame

    def _draw_slip(self, frame: np.ndarray, sl: dict) -> np.ndarray:
        H = frame.shape[0]
        shift = int(sl["shift"] * H)
        frame = np.roll(frame, shift, axis=0)
        self._frameline(frame, float(shift % H), 0.05)
        frame *= 0.92
        return frame

    def _draw_blotch(self, frame: np.ndarray, b: dict, fi: int) -> None:
        H, W = frame.shape[:2]
        t = (fi - b["birth"] + 1.0) / b["life"]
        grow = float(color.smoothstep(0.0, 0.55, np.float32(t)))
        fade = 1.0 - float(color.smoothstep(0.72, 1.0, np.float32(t)))
        alpha = b["inten"] * fade
        if alpha <= 0.01:
            return
        R = b["r"] * H * (0.35 + 0.65 * grow)
        cx, cy = b["cx"] * W, b["cy"] * H
        pad = R * 1.6
        x0, x1 = int(max(cx - pad, 0)), int(min(cx + pad + 1, W))
        y0, y1 = int(max(cy - pad, 0)), int(min(cy + pad + 1, H))
        if x1 <= x0 or y1 <= y0:
            return
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        dx, dy = xx - cx, yy - cy
        d = np.sqrt(dx * dx + dy * dy) + 1e-6
        th = np.arctan2(dy, dx)
        rwob = 1.0 + b["a1"] * np.sin(3 * th + b["p1"]) + b["a2"] * np.sin(5 * th + b["p2"])
        dn = d / (R * rwob + 1e-6)
        m = 1.0 - color.smoothstep(0.55, 1.0, dn)
        region = frame[y0:y1, x0:x1]
        if b["sepia"]:
            sepia = np.asarray((0.42, 0.30, 0.16), np.float32)
            a = (m * alpha * 0.8)[..., None]
            region[...] = region * (1.0 - a * 0.8) + sepia * a * 0.55
        else:
            region *= 1.0 - (m * alpha * 0.9)[..., None]
            ring = color.smoothstep(0.55, 0.85, dn) * (1.0 - color.smoothstep(0.85, 1.15, dn))
            region += (ring * alpha * 0.10)[..., None] * np.asarray((0.35, 0.20, 0.05), np.float32)

    def _draw_static(self, frame: np.ndarray, seed: int, ctx: Context) -> None:
        """One-frame static discharge: branching lightning polylines with glow."""
        H, W = frame.shape[:2]
        g = ctx.rng(f"{self.key}:static{seed}")
        mask = np.zeros((H, W), np.float32)

        def bolt(x: float, y: float, ang: float, nseg: int, step: float, val: float) -> list[tuple]:
            pts = [(x, y)]
            mids = []
            for _ in range(nseg):
                ang += g.uniform(-0.55, 0.55)
                x, y = x + np.cos(ang) * step, y + np.sin(ang) * step
                pts.append((x, y))
                mids.append((x, y, ang))
            cv2.polylines(mask, [np.asarray(pts, np.float32).astype(np.int32)], False, val, 1, cv2.LINE_AA)
            return mids

        for _ in range(1 + int(g.random() < 0.35)):
            side = int(g.integers(0, 4))
            u = g.uniform(0.15, 0.85)
            if side == 0:
                x0, y0, ang = 0.0, u * H, g.uniform(-0.5, 0.5)
            elif side == 1:
                x0, y0, ang = float(W - 1), u * H, np.pi + g.uniform(-0.5, 0.5)
            elif side == 2:
                x0, y0, ang = u * W, 0.0, np.pi / 2 + g.uniform(-0.5, 0.5)
            else:
                x0, y0, ang = u * W, float(H - 1), -np.pi / 2 + g.uniform(-0.5, 0.5)
            step = g.uniform(0.045, 0.10) * H
            mids = bolt(x0, y0, ang, int(g.integers(3, 6)), step, 1.0)
            for bx, by, ba in mids[: max(len(mids) - 1, 1)]:
                if g.random() < 0.55:
                    bolt(bx, by, ba + g.uniform(0.5, 1.1) * (1 if g.random() < 0.5 else -1),
                         int(g.integers(2, 4)), step * 0.55, 0.75)

        glow = cv2.GaussianBlur(mask, (0, 0), 2.4)
        comp = np.clip(mask + glow * 0.9, 0.0, 1.0)
        ym = float(color.luma(frame[::8, ::8]).mean())
        k = (0.40 + 0.60 * (1.0 - min(ym * 1.4, 1.0))) * float(g.uniform(0.8, 1.0))
        col = (0.86, 0.90, 1.0)  # discharge exposes blue-sensitive layers hardest
        for ci in range(3):
            fc = frame[..., ci]
            fc += comp * (col[ci] * k) * (1.0 - fc)

    def _mold(self, H: int, W: int, ctx: Context) -> np.ndarray:
        if self._mold_mask is None or self._mold_mask.shape != (H, W):
            g = ctx.rng(f"{self.key}:mold")
            o1 = g.standard_normal((9, max(int(9 * W / H), 5))).astype(np.float32)
            o1 = cv2.resize(cv2.GaussianBlur(o1, (0, 0), 1.0), (W, H), interpolation=cv2.INTER_LINEAR)
            o2 = g.standard_normal((26, max(int(26 * W / H), 12))).astype(np.float32)
            o2 = cv2.resize(cv2.GaussianBlur(o2, (0, 0), 0.9), (W, H), interpolation=cv2.INTER_LINEAR)
            field = o1 + 0.6 * o2
            nx = np.minimum(np.arange(W, dtype=np.float32), np.arange(W - 1, -1, -1, dtype=np.float32)) / W
            ny = np.minimum(np.arange(H, dtype=np.float32), np.arange(H - 1, -1, -1, dtype=np.float32)) / H
            d = np.minimum(nx[None, :] * (W / H), ny[:, None])  # distance from nearest edge, ~H units
            reach = 1.0 - color.smoothstep(0.02, 0.24, d)
            m = color.smoothstep(-0.1, 1.4, field + 1.8 * reach - 0.9) * reach
            self._mold_mask = np.clip(m, 0.0, 1.0).astype(np.float32)
        return self._mold_mask

    def _draw_burn(self, frame: np.ndarray, fi: int, ctx: Context) -> np.ndarray:
        H, W = frame.shape[:2]
        t = (fi - self._burn_f0) / self._burn_dur
        white = np.asarray((0.99, 0.975, 0.93), np.float32)
        if t > 1.35:
            frame[:] = white
            return frame
        if self._burn_noise is None or self._burn_noise.shape != (H, W):
            g = ctx.rng(f"{self.key}:burnnz")
            nz = g.standard_normal((H // 16 + 2, W // 16 + 2)).astype(np.float32)
            nz = cv2.GaussianBlur(nz, (0, 0), 1.5)
            nz = cv2.resize(nz, (W, H), interpolation=cv2.INTER_LINEAR)
            self._burn_noise = nz / (np.abs(nz).max() + 1e-6)
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            g2 = ctx.rng(f"{self.key}:burnc")
            cx, cy = W * g2.uniform(0.3, 0.7), H * g2.uniform(0.3, 0.7)
            self._burn_grid = (np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2),)
        d = self._burn_grid[0]
        R = H * (0.03 + 2.1 * max(t, 0.0) ** 1.6) + 1e-3
        s = (d * (1.0 + 0.4 * self._burn_noise)) / R
        m_heat = 1.0 - color.smoothstep(1.05, 1.45, s)
        m_char = 1.0 - color.smoothstep(0.96, 1.14, s)
        m_white = 1.0 - color.smoothstep(0.74, 0.97, s)
        heat = np.asarray((1.08, 0.62, 0.28), np.float32)
        char = np.asarray((0.13, 0.06, 0.02), np.float32)
        frame *= 1.0 - m_heat[..., None] * (1.0 - heat)
        frame = frame * (1.0 - m_char[..., None]) + char * m_char[..., None]
        frame = frame * (1.0 - m_white[..., None]) + white * m_white[..., None]
        return np.clip(frame, 0.0, 1.0).astype(np.float32)

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        fi = ctx.fi_out
        sp = self._splice.get(fi)
        if sp is not None:
            frame = self._draw_splice(frame, sp, ctx)
        sl = self._slip.get(fi)
        if sl is not None:
            frame = self._draw_slip(frame, sl)
        for b in self._blotches:
            if b["birth"] <= fi < b["birth"] + b["life"]:
                self._draw_blotch(frame, b, fi)
        mold = self.v["mold_edge"]
        if mold > 0 and self._mold_breath is not None:
            H, W = frame.shape[:2]
            mask = self._mold(H, W, ctx)
            breath = 0.85 + 0.15 * float(self._mold_breath[min(fi, len(self._mold_breath) - 1)])
            mv = mold * 0.38 * breath
            for ci, wc in enumerate((0.95, 0.72, 1.0)):  # kills red/blue first → drab green-brown
                frame[..., ci] *= 1.0 - mask * (mv * wc)
        seed = self._flash.get(fi)
        if seed is not None:
            self._draw_static(frame, seed, ctx)
        if self.v["burn"] and fi >= self._burn_f0:
            frame = self._draw_burn(frame, fi, ctx)
        return np.clip(frame, 0.0, 1.0, out=frame)


# ── cadence ────────────────────────────────────────────────────────────


@register
class Cadence(Effect):
    eid = "cadence"
    label = "Frame Cadence"
    kind = "frame"
    desc = "Time-remap feel of period frame rates: held frames, hand-crank irregularity, telecine judder or projector flutter."
    PARAMS = (
        Param("pattern", "Pattern", "enum", "none",
              choices=("none", "twos", "threes", "silent_irregular", "pulldown_judder", "projector_flutter"),
              group="Timing",
              desc="twos/threes hold frames animation-style; silent_irregular is ~16 fps hand-crank; pulldown_judder is 3:2-style TV cadence; projector_flutter double-prints ~2% of frames."),
        Param("field_blend", "Field Blend", "float", 0.5, 0.0, 1.0, group="Timing",
              desc="For pulldown judder: soft telecine blend of the straddled frame with its neighbor."),
        Param("speed", "Shot Speed", "enum", "native", choices=("native", "silent_16fps_in_24"),
              group="Timing",
              desc="silent_16fps_in_24 resamples the source as if shot at ~16 fps and shown at 24: motion "
                   "runs 1.5× fast inside a 2:1 hold pattern while total duration is preserved - the "
                   "authentic comedy fast-walk feel."),
    )

    def prepare(self, ctx: Context) -> None:
        n, fps = ctx.n_frames, ctx.fps
        pat = self.v["pattern"]
        speed = self.v["speed"]
        self._marks = np.zeros(n, bool)
        self._prev: np.ndarray | None = None
        if pat == "none" and speed == "native":
            self._src = None
            return
        idx = np.arange(n, dtype=np.int64)
        if pat == "none":
            src = idx
        elif pat == "twos":
            src = (idx // 2) * 2
        elif pat == "threes":
            src = (idx // 3) * 3
        elif pat == "silent_irregular":
            g = ctx.rng(f"{self.key}:cad")
            src = np.empty(n, np.int64)
            cur, err, fi = 0, 0.0, 0
            ratio = fps / 16.0
            while fi < n:
                err += ratio + g.uniform(-0.25, 0.25)
                hold = max(int(err), 1)
                err -= hold
                adv = hold + (1 if g.random() < 0.05 else 0)  # crank hiccup skips a frame
                for _ in range(hold):
                    if fi < n:
                        src[fi] = cur
                        fi += 1
                cur += adv
        elif pat == "pulldown_judder":
            off = np.array([0, 0, 1, 2, 3], np.int64)
            src = (idx // 5) * 5 + off[idx % 5]
            self._marks = (idx % 5) == 2  # frame straddling the duplicate boundary
        else:  # projector_flutter
            g = ctx.rng(f"{self.key}:cad")
            src = idx.copy()
            flut = g.random(n) < 0.02
            for i in range(1, n):
                if flut[i]:
                    src[i] = src[i - 1]  # double-print previous frame, drop this one
        if speed == "silent_16fps_in_24":
            # shot at 16, shown at 24: advance the source 1.5× with periodic
            # holds (2,1,2,1…) so the clip keeps its duration but motion runs fast
            adv = (idx * 2 // 3) * 3 // 2
            src = adv[np.minimum(src, n - 1)]
        self._src = np.minimum(src, n - 1)

    def remap(self, ctx: Context) -> np.ndarray | None:
        return self._src

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        if self.v["pattern"] != "pulldown_judder" or self.v["field_blend"] <= 0:
            return frame
        fi = ctx.fi_out
        out = frame
        if fi < len(self._marks) and self._marks[fi] and self._prev is not None:
            a = 0.5 * self.v["field_blend"]
            out = cv2.addWeighted(frame, 1.0 - a, self._prev, a, 0.0)
        self._prev = frame.copy()
        return out


# ── vignette ───────────────────────────────────────────────────────────


@register
class Vignette(Effect):
    eid = "vignette"
    label = "Vignette"
    kind = "frame"
    desc = "Photographic corner falloff with adjustable shape, or a projection hotspot brightening the center."
    PARAMS = (
        Param("amount", "Amount", "float", 0.35, 0.0, 1.0, iscale=True, group="Glow",
              desc="Darkening of the falloff."),
        Param("radius", "Radius", "float", 0.85, 0.3, 1.5, group="Glow",
              desc="Where the falloff begins (1 ≈ frame edge)."),
        Param("softness", "Softness", "float", 0.5, 0.05, 1.0, group="Glow",
              desc="Feather of the falloff edge."),
        Param("roundness", "Roundness", "float", 1.0, 0.4, 1.0, group="Glow",
              desc="1 = round; lower = squarer / anamorphic oval."),
        Param("center_y", "Center Offset", "float", 0.0, -0.4, 0.4, group="Glow",
              desc="Vertical offset of the vignette center."),
        Param("hot_center", "Hotspot", "float", 0.0, 0.0, 1.0, group="Glow",
              desc="Projection hotspot: brightens the center instead."),
    )

    def prepare(self, ctx: Context) -> None:
        self._mask: np.ndarray | None = None
        self._shape: tuple | None = None

    def _build(self, H: int, W: int) -> np.ndarray:
        p = 2.0 / max(self.v["roundness"], 0.35)
        nx = np.abs(np.linspace(-1.0, 1.0, W, dtype=np.float32))[None, :] ** p
        ny = np.abs(np.linspace(-1.0, 1.0, H, dtype=np.float32) - self.v["center_y"] * 2.0)[:, None] ** p
        d = (nx + ny) ** (1.0 / p)
        r = self.v["radius"]
        soft = self.v["softness"]
        fall = color.smoothstep(r * (1.0 - soft * 0.9), r * (1.0 + soft * 1.1) + 1e-3, d)
        mask = 1.0 - self.v["amount"] * 0.85 * fall
        hot = self.v["hot_center"]
        if hot > 0:
            mask = mask * (1.0 + hot * 0.22 * (1.0 - color.smoothstep(0.0, r * 0.85, d)))
        return mask.astype(np.float32)[..., None]

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        if self.v["amount"] <= 0 and self.v["hot_center"] <= 0:
            return frame
        H, W = frame.shape[:2]
        if self._mask is None or self._shape != (H, W):
            self._mask = self._build(H, W)[..., 0]
            self._shape = (H, W)
        hot = self.v["hot_center"] > 0
        for ci in range(3):
            fc = frame[..., ci]
            fc *= self._mask
            if hot:
                np.clip(fc, 0.0, 1.0, out=fc)
        return frame


# ── light leak ─────────────────────────────────────────────────────────


@register
class LightLeak(Effect):
    eid = "light_leak"
    label = "Light Leak"
    kind = "frame"
    desc = "Warm procedural light leaks breathing in from the frame edges, with occasional blooming bursts."
    PARAMS = (
        Param("amount", "Amount", "float", 0.5, 0.0, 1.0, iscale=True, group="Glow",
              desc="Overall leak brightness."),
        Param("hue", "Palette", "enum", "warm", choices=("warm", "red", "rainbow"), group="Glow",
              desc="Leak color family."),
        Param("frequency", "Bursts", "float", 2.0, 0.0, 20.0, unit="/min", group="Glow",
              desc="Rate of bloom-up-then-fade leak bursts."),
        Param("constant", "Constant Glow", "float", 0.15, 0.0, 1.0, group="Glow",
              desc="Always-on edge glow floor."),
        Param("sprocket_side", "Sprocket Fog", "float", 0.0, 0.0, 1.0, iscale=True, group="Glow",
              desc="Fog hugging one edge in a repeating vertical rhythm - light seeping through the "
                   "sprocket area between the perforations, breathing with the transport."),
    )

    _HUES = {
        "warm": ((1.0, 0.45, 0.12), (1.0, 0.62, 0.20), (1.0, 0.30, 0.15), (1.0, 0.75, 0.40)),
        "red": ((1.0, 0.15, 0.08), (0.95, 0.10, 0.20), (1.0, 0.25, 0.05), (0.9, 0.12, 0.12)),
        "rainbow": ((1.0, 0.2, 0.1), (1.0, 0.7, 0.15), (0.3, 0.9, 0.5), (0.3, 0.5, 1.0), (0.8, 0.3, 1.0)),
    }

    def prepare(self, ctx: Context) -> None:
        g = ctx.rng(f"{self.key}:init")
        hues = self._HUES[self.v["hue"]]
        nb = 2 + int(g.random() < 0.5)
        sides = ["left", "right", "top", "bottom"]
        self._blobs = []
        for b in range(nb):
            side = sides[int(g.integers(0, 4))]
            u = g.uniform(0.1, 0.9)
            if side == "left":
                cx, cy, ang = -0.12, u, 0.0
            elif side == "right":
                cx, cy, ang = 1.12, u, np.pi
            elif side == "top":
                cx, cy, ang = u, -0.12, np.pi / 2
            else:
                cx, cy, ang = u, 1.12, -np.pi / 2
            self._blobs.append(dict(
                cx=cx, cy=cy,
                r0=g.uniform(0.28, 0.60),
                elong=g.uniform(1.6, 3.4),
                ang=ang + g.uniform(-0.5, 0.5),
                col=np.asarray(hues[int(g.integers(0, len(hues)))], np.float32),
                tx=ctx.noise.smooth(f"{self.key}:b{b}x", 0.07 + 0.05 * g.random()),
                ty=ctx.noise.smooth(f"{self.key}:b{b}y", 0.07 + 0.05 * g.random()),
                tr=ctx.noise.smooth(f"{self.key}:b{b}r", 0.11),
                ti=ctx.noise.smooth(f"{self.key}:b{b}i", 0.13),
            ))
        n, fps = ctx.n_frames, ctx.fps
        env = np.zeros(n, np.float32)
        if self.v["frequency"] > 0:
            ev = ctx.noise.events(f"{self.key}:burst", self.v["frequency"] / 60.0, min_gap_s=1.8)
            na, tau = max(int(0.3 * fps), 1), max(1.0 * fps, 1.0)
            kern = np.concatenate([np.linspace(0, 1, na, dtype=np.float32),
                                   np.exp(-np.arange(int(3 * tau)) / tau).astype(np.float32)])
            env = np.convolve(ev, kern)[:n].astype(np.float32)
        self._env = np.clip(env, 0.0, 1.5)
        self._grids: tuple | None = None
        self._spr: dict | None = None
        if self.v["sprocket_side"] > 0:
            gs = ctx.rng(f"{self.key}:spr")
            self._spr = dict(
                left=bool(gs.random() < 0.5),
                period=float(gs.uniform(0.17, 0.25)),   # perf pitch as a fraction of H
                phase=float(gs.uniform(0.0, 1.0)),
                depth=float(gs.uniform(0.055, 0.095)),  # horizontal reach as a fraction of W
                col=np.asarray(hues[int(gs.integers(0, len(hues)))], np.float32),
                tb=ctx.noise.smooth(f"{self.key}:sprb", 0.10),
                tp=ctx.noise.smooth(f"{self.key}:sprp", 0.045),
            )

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        a = self.v["amount"]
        if a <= 0:
            return frame
        fi = min(ctx.fi_src, len(self._env) - 1)
        H, W = frame.shape[:2]
        hs, ws = max(H // 8, 8), max(W // 8, 8)
        if self._grids is None or self._grids[0].shape != (hs, ws):
            yy, xx = np.mgrid[0:hs, 0:ws].astype(np.float32)
            self._grids = (xx * (W / ws), yy * (H / hs))
        xg, yg = self._grids
        acc = None
        env = float(self._env[fi])
        for blob in self._blobs:
            breath = 0.5 + 0.5 * float(blob["ti"][fi])
            inten = self.v["constant"] * (0.35 + 0.65 * breath) + env * (0.55 + 0.45 * breath)
            if inten < 0.02:
                continue
            cx = (blob["cx"] + float(blob["tx"][fi]) * 0.10) * W
            cy = (blob["cy"] + float(blob["ty"][fi]) * 0.10) * H
            r = blob["r0"] * H * (0.75 + 0.30 * float(blob["tr"][fi]))
            ca, sa = np.cos(blob["ang"]), np.sin(blob["ang"])
            u = (xg - cx) * ca + (yg - cy) * sa
            v = -(xg - cx) * sa + (yg - cy) * ca
            m = np.exp(-0.5 * ((u / (r * blob["elong"])) ** 2 + (v / (r * 0.9)) ** 2))
            core = np.exp(-0.5 * ((u / (r * blob["elong"] * 0.45)) ** 2 + (v / (r * 0.42)) ** 2))
            layer = (m * 0.8 + core * 0.6)[..., None] * (blob["col"] * (inten * a))
            acc = layer if acc is None else acc + layer
        if self._spr is not None:
            sp = self._spr
            breath = 0.5 + 0.5 * float(sp["tb"][fi])
            inten = self.v["sprocket_side"] * (0.30 + 0.50 * breath + 0.35 * env)
            if inten >= 0.02:
                t = xg / W if sp["left"] else 1.0 - xg / W
                horiz = np.exp(-t / sp["depth"])
                yph = (yg / H) / sp["period"] + sp["phase"] + float(sp["tp"][fi]) * 0.2
                bump = (0.5 + 0.5 * np.cos(2 * np.pi * yph)) ** 2.4
                layer = (horiz * (0.30 + 0.80 * bump))[..., None] * (sp["col"] * (inten * a))
                acc = layer if acc is None else acc + layer
        if acc is None:
            return frame
        acc = acc / (1.0 + acc * 0.35)  # soft-saturate toward white
        np.clip(acc, 0.0, 1.0, out=acc)
        leak = cv2.resize(acc.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
        for ci in range(3):
            fc = frame[..., ci]
            lc = leak[..., ci]
            lc *= 1.0 - fc  # screen blend
            fc += lc
        return frame


# ── projection ─────────────────────────────────────────────────────────


@register
class Projection(Effect):
    eid = "projection"
    label = "Projected In A Room"
    kind = "frame"
    desc = "Being projected on a screen: shutter-beat flicker, slight keystone, ambient light lifting the blacks, screen edge falloff."
    PARAMS = (
        Param("shutter_flicker", "Shutter Flicker", "float", 0.2, 0.0, 1.0, iscale=True, group="Exposure",
              desc="48/72 Hz shutter beat aliasing as gentle fast luma flicker."),
        Param("keystone", "Keystone", "float", 0.03, -0.2, 0.2, group="Geometry",
              desc="Trapezoid warp from off-axis projection (+ pinches the top)."),
        Param("ambient_lift", "Ambient Lift", "float", 0.06, 0.0, 0.3, group="Exposure",
              desc="Room light spilling on the screen: lifted, slightly warm blacks."),
        Param("screen_gain_falloff", "Edge Falloff", "float", 0.25, 0.0, 1.0, group="Exposure",
              desc="Screen gain: edges dimmer than the center."),
    )

    def prepare(self, ctx: Context) -> None:
        n, fps = ctx.n_frames, ctx.fps
        hz = 9.0 + 3.0 * ctx.noise.smooth(f"{self.key}:hz", 0.05)
        phase = np.cumsum(2 * np.pi * hz / max(fps, 1.0))
        sf = self.v["shutter_flicker"]
        w = ctx.noise.white(f"{self.key}:w")
        self._gain = (1.0 - sf * 0.035 * (0.5 + 0.5 * np.sin(phase)) - sf * 0.012 * np.abs(w)).astype(np.float32)
        self._mask: np.ndarray | None = None
        self._M: np.ndarray | None = None
        self._shape: tuple | None = None

    def _geom(self, H: int, W: int) -> None:
        k = self.v["keystone"]
        self._M = None
        if abs(k) > 1e-4:
            dx = abs(k) * W * 0.5
            src = np.float32([(0, 0), (W, 0), (W, H), (0, H)])
            if k > 0:
                dst = np.float32([(dx, 0), (W - dx, 0), (W, H), (0, H)])
            else:
                dst = np.float32([(0, 0), (W, 0), (W - dx, H), (dx, H)])
            self._M = cv2.getPerspectiveTransform(src, dst)
        f = self.v["screen_gain_falloff"]
        self._mask = None
        if f > 0:
            nx = np.linspace(-1, 1, W, dtype=np.float32)[None, :] ** 2
            ny = np.linspace(-1, 1, H, dtype=np.float32)[:, None] ** 2
            d = np.sqrt(nx + ny)
            self._mask = (1.0 - f * 0.35 * color.smoothstep(0.35, 1.35, d)).astype(np.float32)
        self._shape = (H, W)

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        H, W = frame.shape[:2]
        if self._shape != (H, W):
            self._geom(H, W)
        fi = min(ctx.fi_out, len(self._gain) - 1)
        frame *= np.float32(self._gain[fi])
        if self._M is not None:
            frame = cv2.warpPerspective(frame, self._M, (W, H), flags=cv2.INTER_LINEAR,
                                        borderMode=cv2.BORDER_CONSTANT, borderValue=(0.01, 0.01, 0.01))
        al = self.v["ambient_lift"]
        spill = (0.30 * al, 0.26 * al, 0.20 * al)
        for ci in range(3):
            fc = frame[..., ci]
            if self._mask is not None:
                fc *= self._mask
            if al > 0:
                fc *= 1.0 - al * 0.25 - spill[ci]
                fc += spill[ci]
        return np.clip(frame, 0.0, 1.0, out=frame) if al > 0 else frame
