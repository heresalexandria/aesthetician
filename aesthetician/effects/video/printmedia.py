"""Print and reprographic looks: halftone screening (newspaper, comic CMYK,
fine magazine), photocopier generations, microfilm readers and risograph
spot-color — stylized, but physically modeled.

Halftoning is done properly: real rotated periodic dot screens (C 15°, M 75°,
Y 0°, K 45°) thresholded at 2–3x supersample and area-downscaled, so fine
settings produce genuine rosettes instead of moiré soup. Ink is composed
multiplicatively (each ink is a transmissive layer over paper), which is what
makes overlaps and rosette centers print dark the way ink actually does.

Registration, screens, paper and roller state are all static per render
(plates don't move between frames); anything per-frame draws from ctx streams
so renders reproduce exactly from their seed.
"""

from __future__ import annotations

import cv2
import numpy as np

from ...engine.color import smoothstep
from ...engine.graph import Context, Effect, Param, register

_LUMA_W = np.array([0.299, 0.587, 0.114], dtype=np.float32)


def _resize(img: np.ndarray, w: int, h: int, interp: int) -> np.ndarray:
    return cv2.resize(img, (w, h), interpolation=interp)


# ═══════════════════════════════════════════════════════════════════════
# 1. Halftone
# ═══════════════════════════════════════════════════════════════════════
_INK_RGB = {
    "c": np.array([0.04, 0.60, 0.90], np.float32),
    "m": np.array([0.90, 0.07, 0.48], np.float32),
    "y": np.array([0.98, 0.90, 0.06], np.float32),
    "k": np.array([0.10, 0.095, 0.10], np.float32),
}
_INK_ANGLE = {"c": 15.0, "m": 75.0, "y": 0.0, "k": 45.0}

# process → (inks, lpi multiplier, dot-gain factor, paper color at paper=1)
_PROCESSES = {
    "newspaper_bw": (("k",), 0.70, 1.00, (0.870, 0.845, 0.780)),
    "comic_cmyk": (("c", "m", "y", "k"), 1.00, 0.55, (0.965, 0.940, 0.870)),
    "magazine_fine": (("c", "m", "y", "k"), 1.60, 0.25, (0.985, 0.978, 0.960)),
}


@register
class Halftone(Effect):
    eid = "halftone"
    label = "Halftone Print"
    kind = "frame"
    desc = (
        "Printed reproduction with real rotated dot screens: single 45° "
        "newspaper screen, four-color comic CMYK with genuine rosettes, or a "
        "fine magazine screen — with paper tint, dot gain and CMYK plate "
        "misregistration."
    )
    PARAMS = (
        Param("process", "Process", "enum", "comic_cmyk",
              choices=("newspaper_bw", "comic_cmyk", "magazine_fine"), group="Screen",
              desc="newspaper_bw = coarse single black screen on gray stock; "
                   "comic_cmyk = 4 rotated screens, rosettes and all; "
                   "magazine_fine = tighter screen on coated stock."),
        Param("lpi", "Screen Ruling", "float", 45.0, 20.0, 120.0, unit="lpi", group="Screen",
              desc="Relative screen frequency (frame ≈ a 6-inch-tall page). "
                   "Low = chunky pop-art dots, high = tight magazine rosettes."),
        Param("paper", "Paper & Bleed", "float", 0.35, 0.0, 1.0, group="Paper",
              desc="Paper tint plus ink bleed (dot gain): dots swell and soften "
                   "into the stock the way ink spreads on newsprint."),
        Param("misregister", "Misregistration", "float", 0.5, 0.0, 2.0, unit="px", group="Screen",
              desc="CMYK plate offset. Black stays pinned; the colors drift, "
                   "fringing edges the way a rushed press run does."),
        Param("ink_tone", "Ink Tone", "float", 1.0, 0.5, 1.5, group="Paper",
              desc="Tone-transfer gamma into the screens: <1 opens shadows, "
                   ">1 inks up."),
    )

    def prepare(self, ctx: Context) -> None:
        self._built_for: tuple[int, int] | None = None
        self._offsets: dict[str, tuple[float, float]] = {}
        inks = _PROCESSES[self.v["process"]][0]
        g = ctx.rng(f"{self.key}:plates")
        mis = float(self.v["misregister"])
        for ink in inks:
            if ink == "k" or mis <= 0:
                self._offsets[ink] = (0.0, 0.0)
            else:
                r = mis * (0.45 + 0.55 * float(g.random()))
                th = float(g.uniform(0.0, 2.0 * np.pi))
                self._offsets[ink] = (r * float(np.cos(th)), r * float(np.sin(th)))

    def _build(self, W: int, H: int) -> None:
        if self._built_for == (W, H):
            return
        self._built_for = (W, H)
        inks, lpi_mult, gain, _paper = _PROCESSES[self.v["process"]]
        lpi_eff = float(self.v["lpi"]) * lpi_mult
        period = max(H / (6.0 * lpi_eff), 2.0)            # output px per screen line
        # 2x supersample suffices at the clamped minimum period (verified
        # against 3x side by side: identical rosettes, no moiré) and keeps the
        # fine screens inside the perf budget
        S = 2
        self._S = S
        Ws, Hs = W * S, H * S
        p = period * S                                     # supersampled period
        self._aa_inv = np.float32(p / 2.4)                 # AA slope for the threshold
        self._gain_sigma = gain * float(self.v["paper"]) * p * 0.16
        self._screens: dict[str, np.ndarray] = {}
        for ink in inks:
            # yellow is composed at output resolution — its dots are nearly
            # invisible against paper, so it doesn't need the supersample
            sw, sh, sp = (W, H, period) if ink == "y" else (Ws, Hs, p)
            yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
            k = np.float32(2.0 * np.pi / sp)
            th = np.deg2rad(_INK_ANGLE[ink])
            u = (xx * np.float32(np.cos(th)) + yy * np.float32(np.sin(th))) * k
            v = (yy * np.float32(np.cos(th)) - xx * np.float32(np.sin(th))) * k
            # round-dot spot function in [0,1]. The SUM form keeps the dot
            # lattice on the rotated grid at every angle — the product form
            # cos(u)cos(v) degenerates at 45° into an axis-aligned screen.
            self._screens[ink] = (0.5 + 0.25 * (np.cos(u) + np.cos(v))).astype(np.float32)
        self._half = {(Hs, Ws): np.full((Hs, Ws), 0.5, np.float32)}
        if "y" in self._screens:
            self._half[(H, W)] = np.full((H, W), 0.5, np.float32)
        self._ones_s = np.ones((Hs, Ws), np.float32)
        self._out = [np.empty((Hs, Ws), np.float32) for _ in range(3)]

    def _coverage(self, ch: np.ndarray, ink: str) -> np.ndarray:
        """Threshold one separation against its rotated screen (AA'd)."""
        T = self._screens[ink]
        sh, sw = T.shape
        scale = sw // ch.shape[1] if sw > ch.shape[1] else 1
        up = ch if scale == 1 else cv2.resize(ch, (sw, sh), interpolation=cv2.INTER_LINEAR)
        a = cv2.subtract(up, T)
        slope = float(self._aa_inv) * (1.0 if ink != "y" else 1.0 / self._S)
        a = cv2.scaleAdd(a, slope, self._half[(sh, sw)])   # (c-T)*slope + 0.5
        cv2.max(a, 0.0, dst=a)
        cv2.min(a, 1.0, dst=a)
        if self._gain_sigma > 0.25:                        # ink bleed / dot gain
            sig = float(min(self._gain_sigma, 4.0)) / (1.0 if ink != "y" else self._S)
            if sig > 0.25:
                a = cv2.GaussianBlur(a, (0, 0), sig)
        dx, dy = self._offsets.get(ink, (0.0, 0.0))
        if abs(dx) + abs(dy) > 0.05:
            s = self._S if ink != "y" else 1
            M = np.array([[1.0, 0.0, dx * s], [0.0, 1.0, dy * s]], np.float32)
            a = cv2.warpAffine(a, M, (sw, sh), flags=cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_REPLICATE)
        return a

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        H, W = frame.shape[:2]
        self._build(W, H)
        inks, _lm, _gain, paper_full = _PROCESSES[self.v["process"]]
        S = self._S
        Ws, Hs = W * S, H * S
        tone = float(self.v["ink_tone"])

        # separations at working resolution
        seps: dict[str, np.ndarray] = {}
        if inks == ("k",):
            y = frame @ _LUMA_W
            k = 1.0 - y
            k = np.clip((k - 0.04) * 1.12, 0.0, 1.0)       # keep paper clean
            seps["k"] = k
        else:
            cmy = 1.0 - frame
            k = cmy.min(axis=2)
            kk = k ** 1.35                                  # skeleton black (GCR)
            denom = 1.0 - kk * 0.92 + 1e-4
            for i, ink in enumerate(("c", "m", "y")):
                seps[ink] = np.clip((cmy[..., i] - kk * 0.92) / denom, 0.0, 1.0)
            seps["k"] = np.clip(kk * 1.04 - 0.02, 0.0, 1.0)
        if tone != 1.0:
            for ink in seps:
                np.power(np.clip(seps[ink], 0.0, 1.0), tone, out=seps[ink])

        out = self._out
        for ch in range(3):
            out[ch][:] = 1.0
        for ink in inks:
            if ink == "y":
                continue                                   # composed after downscale
            a = self._coverage(seps[ink], ink)
            w = 1.0 - _INK_RGB[ink]
            for ch in range(3):
                if w[ch] < 0.02:
                    continue
                t = cv2.scaleAdd(a, -float(w[ch]), self._ones_s)
                out[ch] = cv2.multiply(out[ch], t, dst=out[ch])

        printed = cv2.merge(out)
        printed = cv2.resize(printed, (W, H), interpolation=cv2.INTER_AREA)
        if "y" in inks:
            ay = self._coverage(seps["y"], "y")
            w = 1.0 - _INK_RGB["y"]
            for ch in range(3):
                if w[ch] < 0.02:
                    continue
                printed[..., ch] *= 1.0 - ay * float(w[ch])
        pa = float(self.v["paper"])
        if pa > 0:
            pc = 1.0 - pa * (1.0 - np.asarray(paper_full, np.float32))
            printed *= pc[None, None, :]
        return np.clip(printed, 0.0, 1.0).astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════
# 2. Photocopy
# ═══════════════════════════════════════════════════════════════════════
@register
class Photocopy(Effect):
    eid = "photocopy"
    label = "Photocopy"
    kind = "frame"
    desc = (
        "Copy-of-a-copy xerography: contrast collapsing toward pure black and "
        "white, detail clogging, edge halos, streaky toner starvation, "
        "periodic roller bands and a slightly skewed page with a lid shadow. "
        "Color mode does the washed, misregistered CMY of an early color "
        "copier."
    )
    PARAMS = (
        Param("generations", "Generations", "int", 2, 1, 6, group="Copy",
              desc="How many times it went back under the glass. 5–6 is zine-"
                   "master territory: pure bilevel crunch."),
        Param("toner", "Toner Wear", "float", 0.35, 0.0, 1.0, iscale=True, group="Copy",
              desc="Starved-cartridge streaks and toner speckle."),
        Param("roller_marks", "Roller Marks", "float", 0.2, 0.0, 1.0, iscale=True, group="Copy",
              desc="Periodic faint vertical gray bands from the fuser roller."),
        Param("skew", "Page Skew", "float", 0.2, 0.0, 1.0, iscale=True, group="Page",
              desc="The page sat crooked on the platen: slight rotation plus a "
                   "soft lid/spine shadow along one edge."),
        Param("mono", "Monochrome", "bool", True, group="Copy",
              desc="Off = a period color copier: washed CMY, misregistered."),
    )

    def prepare(self, ctx: Context) -> None:
        H, W = ctx.height, ctx.width
        g = ctx.rng(f"{self.key}:page")
        sk = float(self.v["skew"])
        self._angle = float(g.uniform(0.3, 1.0)) * 1.4 * sk * (1.0 if g.random() < 0.5 else -1.0)
        self._shadow_edge = int(g.integers(0, 4))
        self._shadow_w = float(g.uniform(0.06, 0.16))
        self._shadow_d = float(g.uniform(0.35, 0.8)) * sk

        rm = float(self.v["roller_marks"])
        self._roller: np.ndarray | None = None
        if rm > 0:
            period = W * float(g.uniform(0.15, 0.26))
            ph = float(g.uniform(0.0, 2.0 * np.pi))
            x = np.arange(W, dtype=np.float32)
            band = 0.5 + 0.5 * np.cos(x * (2.0 * np.pi / period) + ph)
            band = band ** 5                                # narrow-ish gray bands
            band += 0.5 * (0.5 + 0.5 * np.cos(x * (4.0 * np.pi / period) + ph * 1.7)) ** 7
            self._roller = (1.0 - band * 0.085 * rm)[None, :].astype(np.float32)

        tn = float(self.v["toner"])
        self._toner_band: np.ndarray | None = None
        if tn > 0:
            gt = ctx.rng(f"{self.key}:toner")
            n = gt.random(max(W // 28, 8), dtype=np.float32)
            n = cv2.GaussianBlur(n.reshape(1, -1), (0, 0), 1.4)
            band = _resize(n.reshape(1, -1), W, 1, cv2.INTER_LINEAR).reshape(-1)
            band -= band.min()
            band /= max(float(band.max()), 1e-6)
            self._toner_band = smoothstep(0.62, 0.95, band)[None, :].astype(np.float32)
            self._toner_drift = ctx.noise.smooth(f"{self.key}:tdrift", 0.10) * (W * 0.02)

        if not self.v["mono"]:
            gc = ctx.rng(f"{self.key}:cmy")
            self._cmy_off = [(float(gc.uniform(-1.6, 1.6)), float(gc.uniform(-1.1, 1.1)))
                             for _ in range(3)]

    def _edge_shadow(self, H: int, W: int) -> np.ndarray | None:
        if self._shadow_d <= 0.01:
            return None
        w = self._shadow_w
        if self._shadow_edge in (0, 1):
            r = np.linspace(0.0, 1.0, W, dtype=np.float32)
            r = r if self._shadow_edge == 0 else r[::-1]
            prof = np.clip(1.0 - r / w, 0.0, 1.0) ** 1.8
            return prof[None, :]
        r = np.linspace(0.0, 1.0, H, dtype=np.float32)
        r = r if self._shadow_edge == 2 else r[::-1]
        prof = np.clip(1.0 - r / w, 0.0, 1.0) ** 1.8
        return prof[:, None]

    def _tone(self, y: np.ndarray, gens: int, sharp: float = 1.0) -> np.ndarray:
        """The per-generation xerographic transfer curve + clogging + halo."""
        for gi in range(gens):
            y = cv2.GaussianBlur(y, (0, 0), 0.55)          # optics soften
            slope = (5.5 + 3.4 * gi) * sharp
            t = (y - 0.55) * slope
            y = 1.0 / (1.0 + np.exp(-t, dtype=np.float32))
        # edge halo: copiers over-corrected edges — white ring around blacks
        blur = cv2.GaussianBlur(y, (0, 0), 2.4)
        y = y + (y - blur) * (0.22 * gens * sharp)
        return y

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        H, W = frame.shape[:2]
        gens = int(self.v["generations"])
        mono = bool(self.v["mono"])
        x = frame

        if abs(self._angle) > 1e-3:
            M = cv2.getRotationMatrix2D((W / 2.0, H / 2.0), self._angle, 1.0)
            x = cv2.warpAffine(x, M, (W, H), flags=cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_CONSTANT, borderValue=(1.0, 1.0, 1.0))

        if mono:
            y = x @ _LUMA_W
            y = self._tone(y, gens)
        else:
            chans = []
            for c in range(3):
                yc = self._tone(np.ascontiguousarray(x[..., c]), max(gens - 1, 1), sharp=0.55)
                dx, dy = self._cmy_off[c]
                M = np.array([[1.0, 0.0, dx], [0.0, 1.0, dy]], np.float32)
                yc = cv2.warpAffine(yc, M, (W, H), flags=cv2.INTER_LINEAR,
                                    borderMode=cv2.BORDER_REPLICATE)
                chans.append(yc)
            col = cv2.merge(chans)
            col = col + (col.mean(axis=2, keepdims=True) - col) * 0.35   # washed
            y = None

        tn = float(self.v["toner"])
        speck: np.ndarray | None = None
        if tn > 0:
            g = ctx.frame_rng(f"{self.key}:speckle")
            u = g.random((H // 2, W // 2), dtype=np.float32)
            speck = _resize(u, W, H, cv2.INTER_NEAREST)

        def finish_plane(y: np.ndarray) -> np.ndarray:
            tri = y.ndim == 3
            if tn > 0 and self._toner_band is not None:
                fi = min(ctx.fi_out, len(self._toner_drift) - 1)
                band = self._toner_band
                shift = float(self._toner_drift[fi])
                if abs(shift) > 0.5:
                    M = np.array([[1.0, 0.0, shift], [0.0, 1.0, 0.0]], np.float32)
                    band = cv2.warpAffine(band, M, (W, 1), flags=cv2.INTER_LINEAR,
                                          borderMode=cv2.BORDER_REPLICATE)
                b = band[..., None] if tri else band
                y = y + (1.0 - y) * (b * (0.5 * tn))        # starved = lighter print
            if speck is not None:
                sp = speck[..., None] if tri else speck
                mid = 4.0 * y * (1.0 - y)                   # speckle lives in the mids
                y = y - (sp < 0.006 * tn).astype(np.float32) * (0.5 * mid)
                y = y + (sp > 1.0 - 0.004 * tn).astype(np.float32) * (0.5 * mid)
            if self._roller is not None:
                y = y * (self._roller[..., None] if tri else self._roller)
            return y

        if mono:
            y = finish_plane(y)
            sh = self._edge_shadow(H, W)
            if sh is not None:
                y = y * (1.0 - sh * (0.30 * self._shadow_d))
            paper = np.asarray([1.0, 0.995, 0.975], np.float32)
            ink = np.asarray([0.055, 0.055, 0.065], np.float32)
            out = ink + (paper - ink) * np.clip(y, 0.0, 1.0)[..., None]
        else:
            col = finish_plane(col)
            sh = self._edge_shadow(H, W)
            if sh is not None:
                col = col * (1.0 - (sh * (0.30 * self._shadow_d))[..., None])
            out = 0.06 + col * 0.92
        return np.clip(out, 0.0, 1.0).astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════
# 3. Microfilm
# ═══════════════════════════════════════════════════════════════════════
@register
class Microfilm(Effect):
    eid = "microfilm"
    label = "Microfilm Reader"
    kind = "frame"
    desc = (
        "A reel on the library reader: harsh orthochromatic black-and-white "
        "(reds print dark), a wandering lens glare blob, fine horizontal "
        "transport scratches, and the dark film-frame border with soft "
        "edge-of-lens blur."
    )
    PARAMS = (
        Param("contrast", "Ortho Contrast", "float", 0.55, 0.0, 1.0, group="Film",
              desc="Document-film gamma: mids vanish, blacks crush, whites blow. "
                   "Red-blind emulsion — warm tones go dark."),
        Param("reader_glare", "Reader Glare", "float", 0.25, 0.0, 1.0, iscale=True,
              group="Reader",
              desc="The projection lamp's glare blob drifting around the screen."),
        Param("scratches_scan", "Transport Scratches", "float", 0.3, 0.0, 1.0, iscale=True,
              group="Reader",
              desc="Fine horizontal scratches from the reader's rollers, riding "
                   "the film with a faint shimmer."),
        Param("frame_border", "Frame Border", "float", 0.4, 0.0, 1.0, iscale=True,
              group="Film",
              desc="Dark film edge closing in, with the reader lens going soft "
                   "toward the border."),
    )

    _ORTHO_W = np.array([0.09, 0.44, 0.47], dtype=np.float32)   # red-blind

    def prepare(self, ctx: Context) -> None:
        H, W = ctx.height, ctx.width
        self._gx = ctx.noise.smooth(f"{self.key}:gx", 0.07)
        self._gy = ctx.noise.smooth(f"{self.key}:gy", 0.055)
        self._ga = 0.6 + 0.4 * ctx.noise.smooth(f"{self.key}:ga", 0.15)

        sc = float(self.v["scratches_scan"])
        self._scratch: np.ndarray | None = None
        if sc > 0:
            g = ctx.rng(f"{self.key}:scratch")
            ov = np.zeros((H, W), np.float32)
            for _ in range(int(3 + 9 * sc)):
                r = int(g.integers(0, H))
                x0 = int(g.uniform(0.0, 0.5) * W)
                x1 = int(x0 + g.uniform(0.3, 1.0) * (W - x0))
                val = float(g.uniform(0.4, 1.0)) * (1.0 if g.random() < 0.6 else -0.8)
                ov[r, x0:x1] = val
            self._scratch = cv2.GaussianBlur(ov, (0, 0), 0.55)
            self._sflick = 0.55 + 0.45 * ctx.noise.smooth(f"{self.key}:sfl", 1.8)
            self._sjit = ctx.noise.white(f"{self.key}:sjit")

        fb = float(self.v["frame_border"])
        self._border: np.ndarray | None = None
        self._edge_m: np.ndarray | None = None
        if fb > 0:
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            dx = np.minimum(xx, W - 1 - xx) / W
            dy = np.minimum(yy, H - 1 - yy) / H
            d = np.minimum(dx, dy)
            self._border = 1.0 - (1.0 - smoothstep(0.004, 0.030 + 0.030 * fb, d)) * (0.92 * fb)
            self._edge_m = (1.0 - smoothstep(0.02, 0.16, d)) * np.float32(min(1.0, 0.4 + 0.8 * fb))

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        H, W = frame.shape[:2]
        fi = min(ctx.fi_out, ctx.noise.n - 1)
        y = frame @ self._ORTHO_W

        c = float(self.v["contrast"])
        if c > 0:
            slope = 4.0 + 9.0 * c
            t = 1.0 / (1.0 + np.exp(-(y - 0.5) * slope, dtype=np.float32))
            lo = 1.0 / (1.0 + np.exp(0.5 * slope))
            y = y + ((t - lo) / max(1.0 - 2.0 * lo, 1e-4) - y) * (0.55 + 0.45 * c)

        sc = float(self.v["scratches_scan"])
        if sc > 0 and self._scratch is not None:
            ov = np.roll(self._scratch, int(round(float(self._sjit[fi]) * 1.5)), axis=0)
            y = y + ov * (0.16 * sc * float(self._sflick[fi]))

        if self._edge_m is not None:
            yb = cv2.GaussianBlur(y, (0, 0), 2.2)
            y = y + (yb - y) * self._edge_m
        if self._border is not None:
            y = y * self._border

        gl = float(self.v["reader_glare"])
        if gl > 0:
            cx = (0.5 + 0.30 * float(self._gx[fi])) * W
            cy = (0.5 + 0.26 * float(self._gy[fi])) * H
            sig = 0.36 * min(H, W)
            xs = (np.arange(W, dtype=np.float32) - cx) / sig
            ys = (np.arange(H, dtype=np.float32) - cy) / sig
            blob = np.exp(-0.5 * ys * ys)[:, None] * np.exp(-0.5 * xs * xs)[None, :]
            y = 1.0 - (1.0 - y) * (1.0 - blob * (0.32 * gl * float(self._ga[fi])))

        y = np.clip(y, 0.0, 1.0)
        tint = np.asarray([0.90, 0.97, 1.02], np.float32)   # cool reader lamp
        out = y[..., None] * tint[None, None, :] + np.asarray(
            [0.015, 0.017, 0.020], np.float32)
        return np.clip(out, 0.0, 1.0).astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════
# 4. Risograph
# ═══════════════════════════════════════════════════════════════════════
_RISO_INKS = {
    "blue_red": ((0.12, 0.24, 0.62), (0.88, 0.17, 0.14)),
    "black_fluor_pink": ((0.11, 0.10, 0.12), (0.99, 0.36, 0.62)),
    "teal_orange": ((0.05, 0.43, 0.45), (0.95, 0.46, 0.10)),
}


@register
class RisoPrint(Effect):
    eid = "riso_print"
    label = "Risograph"
    kind = "frame"
    desc = (
        "Two-ink risograph duplicator: the image splits into a dark drawing "
        "layer and a warm spot-color layer (luma threshold + hue split), laid "
        "down with the riso's trademark loose registration, grainy ink "
        "coverage in the midtones and soft paper white."
    )
    PARAMS = (
        Param("inks", "Ink Pair", "enum", "blue_red",
              choices=("blue_red", "black_fluor_pink", "teal_orange"), group="Ink",
              desc="The two drums loaded: classic blue/red, zine black/fluor "
                   "pink, or teal/orange."),
        Param("misregister", "Misregistration", "float", 1.5, 0.0, 4.0, unit="px", group="Ink",
              desc="How far the second drum landed from the first. Fixed for the "
                   "whole run (with a hair of wobble), like a real pass."),
        Param("grain_ink", "Ink Grain", "float", 0.4, 0.0, 1.0, iscale=True, group="Ink",
              desc="Speckly ink coverage in the midtones — the riso's stencil "
                   "grain."),
        Param("paper", "Paper", "float", 0.6, 0.0, 1.0, group="Paper",
              desc="Warm uncoated-stock tint under the inks."),
    )

    def prepare(self, ctx: Context) -> None:
        H, W = ctx.height, ctx.width
        g = ctx.rng(f"{self.key}:reg")
        mis = float(self.v["misregister"])
        th = float(g.uniform(0.0, 2.0 * np.pi))
        r = mis * (0.55 + 0.45 * float(g.random()))
        self._off = (r * float(np.cos(th)), r * float(np.sin(th)))
        self._wob_x = ctx.noise.smooth(f"{self.key}:wx", 0.4) * 0.3
        self._wob_y = ctx.noise.smooth(f"{self.key}:wy", 0.33) * 0.3

        gt = ctx.rng(f"{self.key}:grain")
        t = gt.standard_normal((max(H // 2, 4), max(W // 2, 4))).astype(np.float32)
        t = cv2.GaussianBlur(t, (0, 0), 0.6)
        t = _resize(t, W, H, cv2.INTER_LINEAR)
        t /= float(np.percentile(np.abs(t), 95)) + 1e-6
        self._grain = np.clip(t, -2.2, 2.2)

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        H, W = frame.shape[:2]
        fi = min(ctx.fi_out, ctx.noise.n - 1)
        inkA, inkB = (np.asarray(c, np.float32) for c in _RISO_INKS[self.v["inks"]])

        y = frame @ _LUMA_W
        d = 1.0 - y
        # dark drawing layer: shadows and lines, with a toe so paper stays clean
        aA = smoothstep(0.25, 0.78, d)
        # warm spot layer: warm/saturated areas plus a light midtone fill
        warm = frame[..., 0] - frame[..., 2]
        sat = frame.max(axis=2) - frame.min(axis=2)
        aB = smoothstep(0.03, 0.30, warm) * smoothstep(0.06, 0.30, sat)
        aB = np.clip(aB + 0.35 * (4.0 * d * (1.0 - d)) * (1.0 - aB), 0.0, 1.0)
        aB = aB * (1.0 - 0.55 * aA)                       # the dark ink owns the lines

        gr = float(self.v["grain_ink"])
        if gr > 0:
            for a in (aA, aB):
                mid = a * (1.0 - a) * 4.0
                a += self._grain * (0.22 * gr) * mid
                np.clip(a, 0.0, 1.0, out=a)

        dx = self._off[0] + float(self._wob_x[fi])
        dy = self._off[1] + float(self._wob_y[fi])
        if abs(dx) + abs(dy) > 0.03:
            M = np.array([[1.0, 0.0, dx], [0.0, 1.0, dy]], np.float32)
            aB = cv2.warpAffine(aB, M, (W, H), flags=cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_REPLICATE)

        pa = float(self.v["paper"])
        paper = 1.0 - pa * (1.0 - np.asarray([0.975, 0.950, 0.905], np.float32))
        out = np.empty_like(frame)
        for ch in range(3):
            out[..., ch] = paper[ch] * (1.0 - aA * (1.0 - inkA[ch])) \
                                     * (1.0 - aB * (1.0 - inkB[ch]))
        return np.clip(out, 0.0, 1.0).astype(np.float32)
