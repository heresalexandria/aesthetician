#!/usr/bin/env python3
"""Turn the source artwork into the app icons.

    .venv/bin/python scripts/package/make_icon.py [source.png]

The artwork (`icon.png` at the repo root by default) is a rounded plate painted
on a white page, so the corners arrive as opaque white pixels. This cuts that
page away: the white background is flood-filled from the edges, the remaining
plate is eroded by a hair so no white fringe survives on the curve, and the
result is written with a real alpha channel.

Two outputs, both committed, regenerated only when the artwork changes:

  app/build/icon.png     1024 px, artwork inset to 824 px on the macOS icon
                         grid, which is what electron-builder turns into .icns
                         and .ico. Full-bleed art in that slot renders larger
                         than every other icon in the Dock.
  app/renderer/icon.png  512 px, full bleed, the mark the app shows in its own
                         title bar and on the drop screen.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "icon.png"
OUT_BUILD = ROOT / "app" / "build" / "icon.png"
OUT_RENDERER = ROOT / "app" / "renderer" / "icon.png"

ICNS_CANVAS = 1024          # what electron-builder wants
ICNS_ART = 824              # macOS icon grid: 100 px of air on every side
RENDERER_SIZE = 512


def cut_background(img: np.ndarray) -> np.ndarray:
    """RGB artwork on a white page -> BGRA with the page removed."""
    h, w = img.shape[:2]
    bgr = img[..., :3]

    # Near-white, and reachable from the border: interior whites (eye
    # highlights, paper textures) are never touched.
    white = (bgr.min(axis=2) >= 232).astype(np.uint8)
    flood = np.zeros((h + 2, w + 2), np.uint8)
    seeded = white.copy()
    for y, x in ((0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)):
        if seeded[y, x]:
            cv2.floodFill(seeded, flood, (x, y), 2)
    page = seeded == 2
    if not page.any():
        page = np.zeros((h, w), bool)   # already cut out: keep everything

    art = (~page).astype(np.uint8)
    # Fill any speck the flood left behind inside the plate.
    n, labels, stats, _ = cv2.connectedComponentsWithStats(art, 8)
    if n > 1:
        keep = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        art = (labels == keep).astype(np.uint8)

    # The plate's edge is antialiased against white, so the last two pixels of
    # the curve are pale. Pull the alpha in past them, then feather what is
    # left so the corners stay smooth rather than stair-stepped.
    inset = max(2.0, min(h, w) * 0.0022)
    feather = max(1.2, min(h, w) * 0.0012)
    dist = cv2.distanceTransform(art, cv2.DIST_L2, 5)
    alpha = np.clip((dist - inset) / feather, 0.0, 1.0)

    out = np.dstack([bgr.astype(np.float32), alpha[..., None] * 255.0])
    return out.astype(np.uint8)


def resize_rgba(rgba: np.ndarray, size: int) -> np.ndarray:
    """Area-resample in premultiplied space so edges do not halo."""
    a = rgba[..., 3:4].astype(np.float32) / 255.0
    pm = rgba[..., :3].astype(np.float32) * a
    interp = cv2.INTER_AREA if size < rgba.shape[0] else cv2.INTER_CUBIC
    pm = cv2.resize(pm, (size, size), interpolation=interp)
    a = cv2.resize(a, (size, size), interpolation=interp)[..., None]
    rgb = np.where(a > 1e-4, pm / np.maximum(a, 1e-4), 0.0)
    return np.dstack([np.clip(rgb, 0, 255), np.clip(a * 255.0, 0, 255)]).astype(np.uint8)


def square(rgba: np.ndarray) -> np.ndarray:
    """Crop to the artwork's own bounds, padded out to a square."""
    ys, xs = np.where(rgba[..., 3] > 4)
    if not len(ys):
        return rgba
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    crop = rgba[y0:y1, x0:x1]
    side = max(crop.shape[0], crop.shape[1])
    pad = np.zeros((side, side, 4), np.uint8)
    oy, ox = (side - crop.shape[0]) // 2, (side - crop.shape[1]) // 2
    pad[oy:oy + crop.shape[0], ox:ox + crop.shape[1]] = crop
    return pad


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC
    if not src.exists():
        print(f"source artwork not found: {src}", file=sys.stderr)
        return 1
    img = cv2.imread(str(src), cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"could not read {src}", file=sys.stderr)
        return 1
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if img.shape[2] == 4:
        # Honour an alpha channel that is already there, then re-cut anyway:
        # the artwork may be opaque white *and* carry a useless full alpha.
        img[..., :3][img[..., 3] < 8] = 255
    art = square(cut_background(img))

    canvas = np.zeros((ICNS_CANVAS, ICNS_CANVAS, 4), np.uint8)
    inner = resize_rgba(art, ICNS_ART)
    o = (ICNS_CANVAS - ICNS_ART) // 2
    canvas[o:o + ICNS_ART, o:o + ICNS_ART] = inner

    for path, data in ((OUT_BUILD, canvas), (OUT_RENDERER, resize_rgba(art, RENDERER_SIZE))):
        path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(path), data)
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
