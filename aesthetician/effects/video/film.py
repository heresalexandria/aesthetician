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
              desc="Grain clump diameter in pixels at processing resolution."),
        Param("roughness", "Roughness", "float", 0.5, 0.0, 1.0, group="Grain",
              desc="Mix of a finer, sharper grain octave over the soft clumps."),
        Param("chroma_grain", "Color Grain", "float", 0.25, 0.0, 1.0, group="Grain",
              desc="Decorrelated per-channel grain (color negative) versus pure luma grain (prints, b&w)."),
        Param("stock", "Stock", "enum", "fine_35",
              choices=("fine_35", "newsreel_35", "doc_16", "super8", "push_process", "print_dupe"),
              group="Grain",
              desc="Film stock character: multiplies size/amount/color/clumping (explicit params still apply on top)."),
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

    def prepare(self, ctx: Context) -> None:
        self._norm: dict = {}

    def _measured_norm(self, key: tuple, field: np.ndarray) -> float:
        n = self._norm.get(key)
        if n is None:
            n = 1.0 / (float(field.std()) + 1e-6)
            self._norm[key] = n
        return n

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        szm, am, chm, rgm, clm = self._STOCK[self.v["stock"]]
        amount = self.v["amount"] * am
        if amount <= 0:
            return frame
        size = float(np.clip(self.v["size"] * szm, 0.8, 9.0))
        rough = float(np.clip(self.v["roughness"] * rgm, 0.0, 1.0))
        chroma = float(np.clip(self.v["chroma_grain"] * chm, 0.0, 1.0))
        H, W = frame.shape[:2]
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

        # luminance response: peaks in midtones, falls off in deep shadow/highlight
        y = color.luma(frame)
        resp = 0.32 + 1.30 * np.sqrt(np.clip(y - y * y, 0.0, None))
        resp *= 0.30 + 0.70 * np.clip(y * 11.1, 0.0, 1.0)             # fade in from true black
        resp *= 1.0 - 0.55 * np.clip((y - 0.87) * 7.7, 0.0, 1.0)      # clear film = no grain in whites
        c = chroma
        var = (1 - c) ** 2 + c * c + 1.155 * c * (1 - c) + (0.65 * rough) ** 2
        resp *= amount * 0.085 / np.sqrt(var)

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
        glow = cv2.resize(0.62 * b1 + 0.5 * b2, (W, H), interpolation=cv2.INTER_LINEAR)
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
                   bright: bool, vmod: np.ndarray) -> None:
        H, W = frame.shape[:2]
        half = max(int(3 * w + 1), 2)
        c0, c1 = int(np.clip(xc - half, 0, W - 1)), int(np.clip(xc + half + 1, 1, W))
        if c1 <= c0:
            return
        xg = np.arange(c0, c1, dtype=np.float32) - xc
        prof = np.exp(-0.5 * (xg / max(w, 0.3)) ** 2) * inten
        sign = 0.55 if bright else -0.40
        frame[:, c0:c1] += (vmod[:, None] * prof[None, :] * sign)[..., None]

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
            self._draw_line(frame, xc, seg["w"], seg["inten"] * s * flick, seg["bright"], vmod)
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
        self._burn_f0 = int(self.v["burn_at_s"] * fps)
        self._burn_dur = max(int(1.1 * fps), 4)
        self._burn_noise: np.ndarray | None = None
        self._burn_grid: tuple | None = None

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
    )

    def prepare(self, ctx: Context) -> None:
        n, fps = ctx.n_frames, ctx.fps
        pat = self.v["pattern"]
        self._marks = np.zeros(n, bool)
        self._prev: np.ndarray | None = None
        if pat == "none":
            self._src = None
            return
        idx = np.arange(n, dtype=np.int64)
        if pat == "twos":
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
