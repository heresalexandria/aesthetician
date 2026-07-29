"""CRT display effects: interlaced fields, the tube itself (scanlines, phosphor
mask, bloom, curvature, misconvergence) and phosphor persistence trails.

Frames are float32 RGB in [0, 1]. Raster geometry is computed from the
processing height so scan structure always follows the rendered line count.
"""

from __future__ import annotations

import cv2
import numpy as np

from ...engine.graph import Context, Effect, Param, register
from .analog import _luma


def _blur_down(img: np.ndarray, sigma: float, factor: int = 4) -> np.ndarray:
    """Large-radius gaussian via downscale → blur → upscale (fast, soft)."""
    h, w = img.shape[:2]
    dw, dh = max(w // factor, 4), max(h // factor, 4)
    small = cv2.resize(img, (dw, dh), interpolation=cv2.INTER_AREA)
    s = max(sigma / factor, 0.6)
    small = cv2.GaussianBlur(small, (0, 0), s)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)


# ═══════════════════════════════════════════════════════════════════════
# 6. Interlace
# ═══════════════════════════════════════════════════════════════════════
@register
class Interlace(Effect):
    eid = "interlace"
    label = "Interlace"
    kind = "frame"
    desc = ("Field-based rendering: alternate scanlines come from the previous frame, so motion "
            "combs into mice teeth; optional line twitter on fine horizontal detail.")
    PARAMS = (
        Param("field_order", "Field Order", "enum", "tff", choices=("tff", "bff"), group="Fields",
              desc="Which field is newer: top-field-first (most tape formats) or bottom-field-first (DV)."),
        Param("combing", "Combing", "float", 1.0, 0.0, 1.0, group="Fields", iscale=True,
              desc="How fully the stale field shows through — the serrated edges on anything moving."),
        Param("twitter", "Line Twitter", "float", 0.25, 0.0, 1.0, group="Fields", iscale=True,
              desc="Interlace flicker on sharp horizontal edges: one-line shimmer alternating every frame."),
    )

    def prepare(self, ctx: Context) -> None:
        self._prev: np.ndarray | None = None

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        cur = frame.copy()          # clean input becomes next frame's stale field
        if self._prev is None:
            self._prev = cur
        c = self.v["combing"]
        if c > 0.0:
            # stale field: with tff the top field is current → even rows fresh,
            # odd rows late; bff swaps parity
            start = 1 if self.v["field_order"] == "tff" else 0
            rows = frame[start::2]
            prev_rows = self._prev[start::2]
            if prev_rows.shape == rows.shape:
                if c >= 0.999:
                    rows[:] = prev_rows
                else:
                    rows *= (1.0 - c)
                    rows += prev_rows * c

        tw = self.v["twitter"]
        if tw > 0.0:
            y = _luma(frame)
            blur = cv2.filter2D(y, -1, np.array([[0.25], [0.5], [0.25]], np.float32),
                                borderType=cv2.BORDER_REFLECT)
            hf = np.abs(y - blur)
            m = np.clip(hf * 6.0, 0.0, 1.0) * (tw * 0.75)
            parity = ctx.fi_out & 1
            sh = np.roll(frame, 1 if parity else -1, axis=0)
            frame += (sh - frame) * m[..., None]

        self._prev = cur
        return np.clip(frame, 0.0, 1.0, out=frame)


# ═══════════════════════════════════════════════════════════════════════
# 7. CRT display
# ═══════════════════════════════════════════════════════════════════════
@register
class CRT(Effect):
    eid = "crt"
    label = "CRT Display"
    kind = "frame"
    desc = ("The picture tube: scanline gaps, phosphor mask, bloom and glass glow, barrel "
            "curvature with dark rounded corners, beam misconvergence and tube-edge vignette.")
    PARAMS = (
        Param("scan_strength", "Scanlines", "float", 0.0, 0.0, 1.0, group="Raster", iscale=True,
              desc="Darkened gaps between scan rows; strength of the visible line structure."),
        Param("phosphor_mask", "Phosphor Mask", "enum", "none", choices=("none", "grille", "dots"),
              group="Raster",
              desc="RGB substructure of the tube face: aperture-grille stripes or shadow-mask dots."),
        Param("mask_scale", "Mask Pitch", "float", 2.0, 1.0, 8.0, unit="px", group="Raster",
              desc="Width of one phosphor stripe; keep small and subtle to avoid moiré."),
        Param("mask_strength", "Mask Strength", "float", 0.25, 0.0, 1.0, group="Raster",
              desc="Visibility of the phosphor triads."),
        Param("bloom", "Bloom", "float", 0.15, 0.0, 1.0, group="Glass", iscale=True,
              desc="Bright areas blowing past their outlines and bleeding into neighbors."),
        Param("bloom_radius", "Bloom Radius", "float", 10.0, 2.0, 40.0, unit="px", group="Glass",
              desc="How far the highlight bleed spreads."),
        Param("glass_glow", "Glass Glow", "float", 0.0, 0.0, 1.0, group="Glass", iscale=True,
              desc="Soft overall halation, as if the whole faceplate is lit from within."),
        Param("curvature", "Curvature", "float", 0.0, 0.0, 0.35, group="Geometry",
              desc="Barrel bulge of the tube; edges bow and the corners round off dark."),
        Param("misconvergence", "Misconvergence", "float", 0.0, 0.0, 6.0, unit="px", group="Geometry",
              iscale=True,
              desc="Red and blue beams landing apart, worsening toward the edges of the tube."),
        Param("vignette_crt", "Tube Vignette", "float", 0.0, 0.0, 1.0, group="Glass", iscale=True,
              desc="Gentle darkening toward the edges of the glass."),
    )

    def prepare(self, ctx: Context) -> None:
        self._W = -1
        self._H = -1
        self._build(ctx.width, ctx.height)

    def _build(self, W: int, H: int) -> None:
        if (W, H) == (self._W, self._H):
            return
        self._W, self._H = W, H
        v = self.v

        # scanline profile: every other raster row darkened, softly
        rows = np.arange(H, dtype=np.float32)
        s = v["scan_strength"]
        alt = 0.5 - 0.5 * np.cos(np.pi * rows)          # 0,1,0,1…
        self._scan = (1.0 - s * (0.12 + 0.78 * alt))[:, None, None].astype(np.float32) if s > 0 else None

        # phosphor mask
        self._mask = None
        if v["phosphor_mask"] != "none" and v["mask_strength"] > 0.0:
            p = max(int(round(v["mask_scale"])), 1)
            m = v["mask_strength"]
            xch = (np.arange(W) // p) % 3
            gain = np.full((1, W, 3), 1.0 - 0.55 * m, np.float32)
            for cch in range(3):
                gain[0, xch == cch, cch] = 1.0 + 0.9 * m
            if v["phosphor_mask"] == "grille":
                self._mask = np.broadcast_to(gain, (H, W, 3))
            else:  # dots: brick-offset the triads every p rows
                gain2 = np.roll(gain, p + p // 2, axis=1)
                tile = np.empty((2 * p, W, 3), np.float32)
                tile[:p] = gain
                tile[p:] = gain2
                reps = H // (2 * p) + 1
                self._mask = np.tile(tile, (reps, 1, 1))[:H]

        # curvature remap
        self._curve_maps = None
        k = v["curvature"]
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        cx, cy = (W - 1) / 2.0, (H - 1) / 2.0
        nx, ny = (xx - cx) / cx, (yy - cy) / cy
        if k > 0.0:
            r2 = nx * nx + ny * ny
            f = (1.0 + k * r2) / (1.0 + k)
            self._curve_maps = (cx + nx * f * cx, cy + ny * f * cy)

        # misconvergence: radial R/B split growing toward the edges
        self._conv_maps = None
        mc = v["misconvergence"]
        if mc > 0.0:
            amp = mc * (W / 704.0) * 0.5
            r2 = nx * nx + ny * ny
            dx = nx * r2 * amp
            dy = ny * r2 * amp * (H / W)
            self._conv_maps = (xx + dx, yy + dy, xx - dx, yy - dy)

        # tube vignette
        self._vig = None
        if v["vignette_crt"] > 0.0:
            r = np.sqrt(np.clip((nx * nx + ny * ny) / 2.0, 0.0, 1.0))
            t = np.clip((r - 0.55) / 0.45, 0.0, 1.0)
            fall = t * t * (3.0 - 2.0 * t)
            self._vig = (1.0 - v["vignette_crt"] * 0.5 * fall)[..., None].astype(np.float32)

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        v = self.v
        H, W = frame.shape[:2]
        self._build(W, H)

        if self._conv_maps is not None:
            xr, yr, xb, yb = self._conv_maps
            frame[..., 0] = cv2.remap(np.ascontiguousarray(frame[..., 0]), xr, yr,
                                      cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            frame[..., 2] = cv2.remap(np.ascontiguousarray(frame[..., 2]), xb, yb,
                                      cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

        if self._curve_maps is not None:
            frame = cv2.remap(frame, self._curve_maps[0], self._curve_maps[1],
                              cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)

        if self._scan is not None:
            frame *= self._scan
            frame *= 1.0 + 0.25 * v["scan_strength"]     # tubes ran bright

        if self._mask is not None:
            frame = frame * self._mask

        b = v["bloom"]
        if b > 0.0:
            y = _luma(np.ascontiguousarray(frame))
            t = np.clip((y - 0.68) / 0.32, 0.0, 1.0)
            t = t * t * (3.0 - 2.0 * t)
            glow = _blur_down(frame * t[..., None], v["bloom_radius"])
            frame = 1.0 - (1.0 - np.clip(frame, 0.0, 1.0)) * (1.0 - np.clip(glow * b, 0.0, 1.0))

        gg = v["glass_glow"]
        if gg > 0.0:
            halo = _blur_down(frame, max(v["bloom_radius"] * 2.5, 18.0), factor=8)
            frame = 1.0 - (1.0 - np.clip(frame, 0.0, 1.0)) * (1.0 - np.clip(halo * gg * 0.5, 0.0, 1.0))

        if self._vig is not None:
            frame = frame * self._vig

        return np.clip(frame, 0.0, 1.0).astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════
# 8. Phosphor decay
# ═══════════════════════════════════════════════════════════════════════
@register
class PhosphorDecay(Effect):
    eid = "phosphor_decay"
    label = "Phosphor Decay"
    kind = "frame"
    desc = ("Slow phosphor persistence: bright things drag glowing trails behind motion, green "
            "lingering longest — the security-camera and old-terminal look.")
    _TINT = {
        "green_mono": (0.10, 1.0, 0.22),
        "amber_mono": (1.0, 0.66, 0.08),
    }

    PARAMS = (
        Param("decay", "Persistence", "float", 0.45, 0.0, 1.0, group="Phosphor", iscale=True,
              desc="How long the phosphor keeps glowing after the beam moves on; 0 is a modern panel."),
        Param("mode", "Phosphor Type", "enum", "p22", choices=("p22", "green_mono", "amber_mono"),
              group="Phosphor",
              desc="Standard color P22 phosphors, or single-phosphor green/amber monitor glass."),
    )

    def prepare(self, ctx: Context) -> None:
        self._prev: np.ndarray | None = None

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        mode = self.v["mode"]
        if mode != "p22":
            y = _luma(frame)
            tint = np.asarray(self._TINT[mode], np.float32)
            frame = y[..., None] * tint

        d = self.v["decay"]
        if d <= 0.0:
            self._prev = None
            return np.clip(frame, 0.0, 1.0).astype(np.float32)

        base = 0.35 + 0.62 * d
        # green phosphor persists longest, blue a touch more than red
        ret = np.asarray([base * 0.90, base, base * 0.94], np.float32)
        np.clip(ret, 0.0, 0.985, out=ret)
        if self._prev is not None and self._prev.shape == frame.shape:
            frame = np.maximum(frame, self._prev * ret)
        self._prev = frame.copy()
        return np.clip(frame, 0.0, 1.0).astype(np.float32)
