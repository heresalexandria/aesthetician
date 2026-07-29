"""Runtime asset store: loads overlay plates with caching and graceful fallback."""

from __future__ import annotations

import os

import cv2
import numpy as np

from .manifest import pack_files

_CACHE: dict[tuple[str, int, int, int], np.ndarray] = {}


def plate(pack: str, index: int, width: int, height: int) -> np.ndarray | None:
    """Load plate `index % available` from a pack, resized (cover-crop) to WxH.

    Returns float32 HxWx3 in [0,1], or None when the pack has no files.
    """
    files = pack_files(pack)
    if not files:
        return None
    path = files[index % len(files)]
    key = (path, width, height, 0)
    if key in _CACHE:
        return _CACHE[key]
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        return None
    x = img.astype(np.float32) / 255.0
    x = x[..., ::-1]  # BGR→RGB
    h, w = x.shape[:2]
    scale = max(width / w, height / h)
    nw, nh = int(round(w * scale)), int(round(h * scale))
    x = cv2.resize(x, (nw, nh), interpolation=cv2.INTER_AREA)
    y0 = (nh - height) // 2
    x0 = (nw - width) // 2
    x = np.ascontiguousarray(x[y0 : y0 + height, x0 : x0 + width])
    if len(_CACHE) > 64:
        _CACHE.clear()
    _CACHE[key] = x
    return x


def n_plates(pack: str) -> int:
    return len(pack_files(pack))
