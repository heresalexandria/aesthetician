#!/usr/bin/env python3
"""Generate app/build/icon.png - the source icon electron-builder converts to
.icns and .ico.

Committed output, regenerated only when the artwork changes:

    .venv/bin/python scripts/package/make_icon.py

The motif is the app's own subject matter: a dark plate lit by an amber film
leak with magenta chroma bleed, a scanline comb, and three bright tape-dropout
dashes (the one element that stays legible at 32 px).
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

OUT = Path(__file__).resolve().parents[2] / "app" / "build" / "icon.png"
S = 1024


def render() -> np.ndarray:
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    u, v = xx / S, yy / S

    img = np.zeros((S, S, 3), np.float32)
    img[..., 0] = 0.045 + 0.015 * v
    img[..., 1] = 0.048 + 0.018 * v
    img[..., 2] = 0.062 + 0.028 * v

    def glow(cx: float, cy: float, r: float, rgb: tuple, amp: float) -> None:
        d = np.sqrt((u - cx) ** 2 + (v - cy) ** 2)
        g = np.exp(-((d / r) ** 2)) * amp
        for i in range(3):
            img[..., i] += g * rgb[i]

    glow(0.12, 0.10, 0.44, (1.00, 0.48, 0.14), 1.05)   # amber film leak
    glow(0.92, 0.94, 0.38, (0.72, 0.20, 0.95), 0.60)   # magenta chroma bleed
    glow(0.52, 0.52, 0.55, (0.10, 0.12, 0.22), 0.35)   # centre lift

    comb = 0.5 + 0.5 * np.cos(yy * (2 * np.pi / 8.0))
    img *= 1.0 - 0.22 * comb[..., None]

    out = img
    rng = np.random.default_rng(11)
    for y0, x0, x1, h, amp in ((0.375, 0.16, 0.74, 0.030, 1.15),
                               (0.520, 0.34, 0.88, 0.022, 0.95),
                               (0.645, 0.22, 0.55, 0.016, 0.75)):
        band = np.exp(-0.5 * ((v - y0) / (h * 0.5)) ** 2)
        span = np.clip((u - x0) * 26, 0, 1) * np.clip((x1 - u) * 26, 0, 1)
        ragged = 0.78 + 0.22 * (0.5 + 0.5 * np.cos(xx * 0.19 + y0 * 40))
        hit = (band * span * ragged * amp)[..., None]
        out = out * (1 - 0.85 * hit) + hit * np.array([0.98, 0.96, 0.92], np.float32)
    out = out + rng.normal(0.0, 0.014, (S, S, 1)).astype(np.float32)

    # Squircle aperture.
    m = np.zeros((S, S), np.uint8)
    pad, rad = int(S * 0.06), int(S * 0.235)
    cv2.rectangle(m, (pad + rad, pad), (S - pad - rad, S - pad), 255, -1)
    cv2.rectangle(m, (pad, pad + rad), (S - pad, S - pad - rad), 255, -1)
    for cx, cy in ((pad + rad, pad + rad), (S - pad - rad, pad + rad),
                   (pad + rad, S - pad - rad), (S - pad - rad, S - pad - rad)):
        cv2.circle(m, (cx, cy), rad, 255, -1)
    alpha = cv2.GaussianBlur(m, (0, 0), S * 0.003).astype(np.float32) / 255.0

    inner = cv2.GaussianBlur(m, (0, 0), S * 0.016).astype(np.float32) / 255.0
    rim = np.clip(alpha - inner, 0, 1)
    out = out + rim[..., None] * (0.30 + 0.45 * (1.0 - v) ** 2)[..., None]

    out = np.clip(out, 0, 1) * alpha[..., None]     # nothing outside the plate
    return np.dstack([out[..., ::-1] * 255.0, alpha * 255.0]).astype(np.uint8)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT), render())
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
