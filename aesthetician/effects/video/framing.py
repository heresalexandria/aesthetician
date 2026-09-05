"""Framing: era aspect ratios, letterbox/pillarbox, overscan, corner masks."""

from __future__ import annotations

import cv2
import numpy as np

from ...engine.graph import Context, Effect, Param, register


@register
class Framing(Effect):
    eid = "framing"
    label = "Framing / Aspect"
    kind = "frame"
    desc = "Fit the image into an era aspect ratio inside the canvas (letterbox/pillarbox or crop), with CRT-style rounded corners and overscan."
    PARAMS = (
        Param("aspect", "Target Aspect", "enum", "source",
              choices=("source", "none", "4:3", "16:9", "1.37", "1.85", "2.35", "1:1", "9:16"),
              desc="Match source video by default. Choose a ratio to frame inside the source canvas; output dimensions stay the same."),
        Param("mode", "Fit Mode", "enum", "box",
              choices=("box", "crop"), desc="box = fit the entire image inside the aperture; crop = fill the aperture with a center-cut. Neither stretches the picture."),
        Param("zoom", "Overscan Zoom", "float", 0.0, 0.0, 0.25, desc="CRT overscan: pushes edges out of frame."),
        Param("corner_radius", "Corner Rounding", "float", 0.0, 0.0, 0.25, desc="CRT tube corner mask."),
        Param("edge_soft", "Edge Softness", "float", 0.004, 0.0, 0.05, desc="Feather of the mask edge."),
        Param("matte_gray", "Matte Brightness", "float", 0.0, 0.0, 0.25, desc="Bar color (0 = black)."),
    )

    _ASPECTS = {"4:3": 4 / 3, "16:9": 16 / 9, "1.37": 1.37, "1.85": 1.85, "2.35": 2.35, "1:1": 1.0, "9:16": 9 / 16}

    def prepare(self, ctx: Context) -> None:
        self._mask_cache: np.ndarray | None = None

    def _content_rect(self, W: int, H: int) -> tuple[int, int, int, int]:
        """(x, y, w, h) of the content region inside the canvas."""
        a = self._ASPECTS.get(self.v["aspect"])
        if a is None:
            return 0, 0, W, H
        canvas_a = W / H
        if a >= canvas_a:  # content wider than canvas → bars top/bottom
            w = W
            h = max(1, int(round(W / a)))
            return 0, (H - h) // 2, w, h
        else:
            h = H
            w = max(1, int(round(H * a)))
            return (W - w) // 2, 0, w, h

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        H, W = frame.shape[:2]
        x0, y0, w, h = self._content_rect(W, H)
        zoom = 1.0 + self.v["zoom"]

        if (x0, y0, w, h) == (0, 0, W, H) and zoom == 1.0 and self.v["corner_radius"] <= 0:
            return frame

        src = frame
        if zoom > 1.0:
            zw, zh = max(1, int(W / zoom)), max(1, int(H / zoom))
            src = frame[(H - zh) // 2 : (H - zh) // 2 + zh, (W - zw) // 2 : (W - zw) // 2 + zw]
        sh, sw = src.shape[:2]
        if self.v["mode"] == "crop":
            if sw / sh > w / h:
                cw = max(1, round(sh * w / h))
                src = src[:, (sw - cw) // 2 : (sw - cw) // 2 + cw]
            else:
                ch = max(1, round(sw * h / w))
                src = src[(sh - ch) // 2 : (sh - ch) // 2 + ch]
            content = cv2.resize(src, (w, h), interpolation=cv2.INTER_AREA)
        else:
            scale = min(w / sw, h / sh)
            fw, fh = max(1, round(sw * scale)), max(1, round(sh * scale))
            content = np.full((h, w, 3), self.v["matte_gray"], np.float32)
            ox, oy = (w - fw) // 2, (h - fh) // 2
            content[oy:oy + fh, ox:ox + fw] = cv2.resize(src, (fw, fh), interpolation=cv2.INTER_AREA)

        canvas = np.full_like(frame, self.v["matte_gray"], dtype=np.float32)
        canvas[y0 : y0 + h, x0 : x0 + w] = content

        r = self.v["corner_radius"]
        if r > 0:
            if self._mask_cache is None:
                mask = _rounded_mask(w, h, r, self.v["edge_soft"])
                self._mask_cache = mask
            m = self._mask_cache[..., None]
            region = canvas[y0 : y0 + h, x0 : x0 + w]
            canvas[y0 : y0 + h, x0 : x0 + w] = region * m + self.v["matte_gray"] * (1.0 - m)
        return canvas


def _rounded_mask(w: int, h: int, radius_frac: float, soft: float) -> np.ndarray:
    r = radius_frac * min(w, h)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx = np.clip(xx, r, w - 1 - r)
    cy = np.clip(yy, r, h - 1 - r)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    s = max(soft * min(w, h), 1.0)
    return np.clip((r - d) / s + 1.0, 0.0, 1.0).astype(np.float32)
