"""Display-referred finishing tools for modern cinema and photochemical looks.

These are creative transforms of decoded RGB, not camera IDTs, HDR recovery,
or measured emulations of proprietary film stocks.
"""

from __future__ import annotations

import cv2
import numpy as np

from ...engine import color
from ...engine.graph import Context, Effect, Param, register


@register
class CinemaFinish(Effect):
    eid = "cinema_finish"
    label = "Cinema Finish"
    desc = "Shape highlight color, subtractive dye density, silver retention and local contrast in the existing picture. Creative SDR finishing; does not recover clipped highlights."
    PARAMS = (
        Param("highlight_desat", "Highlight Desaturation", "float", 0.0, 0.0, 1.0,
              desc="Gradually neutralize bright colors, keeping midtone color intact."),
        Param("density", "Color Density", "float", 0.0, 0.0, 1.0,
              desc="Darken saturated colors like subtractive print dyes; neutrals stay neutral."),
        Param("silver", "Silver Retention", "float", 0.0, 0.0, 1.0,
              desc="Add a contrasting monochrome silver image for a bleach-bypass character."),
        Param("local_contrast", "Local Contrast", "float", 0.0, -1.0, 1.0,
              desc="Positive gives broad detail separation; negative gently softens tonal transitions."),
        Param("radius", "Detail Radius", "float", 0.025, 0.005, 0.15,
              desc="Blur radius as a fraction of frame height; active when Local Contrast is nonzero."),
        Param("mix", "Mix", "float", 1.0, 0.0, 1.0,
              desc="Blend with the incoming picture. Zero is an exact bypass."),
    )

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        v = self.v
        if v["mix"] == 0 or not any(v[k] for k in ("highlight_desat", "density", "silver", "local_contrast")):
            return frame
        x = frame.copy()
        y = color.luma(x)[..., None]
        if v["highlight_desat"]:
            weight = color.smoothstep(0.55, 1.0, y) * v["highlight_desat"]
            x = x * (1 - weight) + y * weight
        if v["density"]:
            chroma = x.max(axis=2, keepdims=True) - x.min(axis=2, keepdims=True)
            x *= 1.0 - chroma * v["density"] * 0.45
        if v["silver"]:
            silver = np.clip((color.luma(x)[..., None] - 0.45) * 1.45 + 0.45, 0, 1)
            x = x * (1 - 0.7 * v["silver"]) + silver * (0.7 * v["silver"])
        if v["local_contrast"]:
            lum = color.luma(x)
            blur = cv2.GaussianBlur(lum, (0, 0), max(0.5, frame.shape[0] * v["radius"]))
            x += ((lum - blur) * v["local_contrast"] * 0.7)[..., None]
        return np.clip(frame * (1 - v["mix"]) + x * v["mix"], 0, 1).astype(np.float32)
