"""Optical-printer and traveling-matte artifacts."""

from __future__ import annotations

import cv2
import numpy as np

from ...engine import color
from ...engine.graph import Context, Effect, Param, register


def _shift_x(channel: np.ndarray, px: float) -> np.ndarray:
    if abs(px) < 1e-3:
        return channel
    h, w = channel.shape
    matrix = np.array([[1.0, 0.0, px], [0.0, 1.0, 0.0]], np.float32)
    return cv2.warpAffine(channel, matrix, (w, h), flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_REPLICATE)


@register
class OpticalComposite(Effect):
    eid = "optical_composite"
    label = "Optical Composite"
    kind = "frame"
    desc = ("Optical-printer generation softness, traveling-matte edge lines, color-layer "
            "misregistration, printer haze and slow density breathing.")
    PARAMS = (
        Param("softness", "Generation Softness", "float", 0.0, 0.0, 1.0,
              group="Printer", iscale=True,
              desc="Detail lost while a composited shot is rephotographed through the optical printer."),
        Param("matte_line", "Matte Lines", "float", 0.0, 0.0, 1.0,
              group="Matte", iscale=True,
              desc="Thin dark and pale seams around strong traveling-matte boundaries."),
        Param("registration", "Layer Registration", "float", 0.0, 0.0, 3.0, unit="px",
              group="Matte", iscale=True,
              desc="Red and blue composite layers landing slightly apart at matte edges."),
        Param("layer_haze", "Printer Haze", "float", 0.0, 0.0, 1.0,
              group="Printer", iscale=True,
              desc="Scattered printer light lifting blacks and softening the composited layer."),
        Param("density_breath", "Density Breathing", "float", 0.0, 0.0, 1.0,
              group="Printer", iscale=True,
              desc="Slow shot-density drift from exposure variation in the optical pass."),
    )

    def prepare(self, ctx: Context) -> None:
        self._density = ctx.noise.smooth(f"{self.key}:density", 0.22)

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        softness = self.v["softness"]
        matte = self.v["matte_line"]
        registration = self.v["registration"]
        haze = self.v["layer_haze"]
        breath = self.v["density_breath"]
        if softness <= 0 and matte <= 0 and registration <= 0 and haze <= 0 and breath <= 0:
            return frame

        h, w = frame.shape[:2]
        hscale = max(h / 1080.0, 0.35)
        out = frame

        if softness > 0:
            blur = cv2.GaussianBlur(out, (0, 0), (0.45 + 1.55 * softness) * hscale)
            out = cv2.addWeighted(out, 1.0 - 0.52 * softness,
                                  blur, 0.52 * softness, 0.0)

        edge = None
        if matte > 0 or registration > 0:
            y = color.luma(out)
            gx = cv2.Sobel(y, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(y, cv2.CV_32F, 0, 1, ksize=3)
            mag = cv2.magnitude(gx, gy)
            edge = np.clip((mag - 0.12) / 0.55, 0.0, 1.0)
            edge = cv2.GaussianBlur(edge, (0, 0), 0.45 * hscale + 0.25)

        if registration > 0 and edge is not None:
            px = registration * max(w / 1920.0, 0.35)
            shifted_r = _shift_x(out[..., 0], px)
            shifted_b = _shift_x(out[..., 2], -px)
            mix = edge * min(registration / 2.0, 1.0) * 0.65
            out = out.copy()
            out[..., 0] += (shifted_r - out[..., 0]) * mix
            out[..., 2] += (shifted_b - out[..., 2]) * mix

        if matte > 0 and edge is not None:
            dark = _shift_x(edge, 0.55 * hscale)
            pale = _shift_x(edge, -0.65 * hscale)
            out *= (1.0 - dark[..., None] * (0.085 * matte))
            out += pale[..., None] * (0.035 * matte) * (1.0 - out)

        if haze > 0:
            small = cv2.resize(out, (max(w // 6, 8), max(h // 6, 8)),
                               interpolation=cv2.INTER_AREA)
            small = cv2.GaussianBlur(small, (0, 0), 2.0 + 3.0 * haze)
            veil = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
            out = out * (1.0 - 0.09 * haze) + veil * (0.055 * haze)
            out += np.array((0.010, 0.009, 0.008), np.float32) * haze

        if breath > 0:
            fi = min(ctx.fi_out, len(self._density) - 1)
            drift = float(self._density[fi]) * breath
            gain = 1.0 + 0.026 * drift
            lift = max(drift, 0.0) * 0.008
            out = out * gain + np.array((lift, lift * 0.95, lift * 0.90), np.float32)

        return np.clip(out, 0.0, 1.0).astype(np.float32)
