"""Color-space transforms and tone helpers (float32 RGB in [0, 1])."""

from __future__ import annotations

import numpy as np

# ITU-R BT.601 luma weights — the analog-era standard, used across the engine.
_RGB2YIQ = np.array(
    [
        [0.299, 0.587, 0.114],
        [0.5959, -0.2746, -0.3213],
        [0.2115, -0.5227, 0.3112],
    ],
    dtype=np.float32,
)
_YIQ2RGB = np.linalg.inv(_RGB2YIQ).astype(np.float32)


def rgb_to_yiq(rgb: np.ndarray) -> np.ndarray:
    return rgb @ _RGB2YIQ.T


def yiq_to_rgb(yiq: np.ndarray) -> np.ndarray:
    return yiq @ _YIQ2RGB.T


def luma(rgb: np.ndarray) -> np.ndarray:
    return rgb @ _RGB2YIQ[0]


def saturate(rgb: np.ndarray, amount: float) -> np.ndarray:
    """amount 1.0 = unchanged, 0 = grayscale, >1 boosts."""
    y = luma(rgb)[..., None]
    return y + (rgb - y) * amount


def lift_gamma_gain(
    rgb: np.ndarray,
    lift: tuple[float, float, float] | float = 0.0,
    gamma: tuple[float, float, float] | float = 1.0,
    gain: tuple[float, float, float] | float = 1.0,
) -> np.ndarray:
    lift = np.asarray(lift, dtype=np.float32)
    gamma = np.asarray(gamma, dtype=np.float32)
    gain = np.asarray(gain, dtype=np.float32)
    x = np.clip(rgb, 0.0, 1.0)
    x = x * gain + lift * (1.0 - x)
    x = np.clip(x, 0.0, 1.0) ** (1.0 / np.maximum(gamma, 1e-3))
    return x.astype(np.float32)


def apply_matrix(rgb: np.ndarray, m: np.ndarray) -> np.ndarray:
    return rgb @ m.T.astype(np.float32)


def soft_clip_highlights(rgb: np.ndarray, knee: float = 0.85) -> np.ndarray:
    """Gentle shoulder above `knee` instead of a hard clip."""
    x = rgb.copy()
    over = x > knee
    span = 1.0 - knee
    x[over] = knee + span * np.tanh((x[over] - knee) / max(span, 1e-6)) * 1.0
    return x


def temperature_shift(rgb: np.ndarray, warmth: float, tint: float = 0.0) -> np.ndarray:
    """warmth >0 warms (red/yellow), <0 cools. tint >0 shifts magenta, <0 green."""
    gains = np.array(
        [1.0 + 0.20 * warmth + 0.05 * tint, 1.0 - 0.05 * tint * 2.0, 1.0 - 0.20 * warmth + 0.05 * tint],
        dtype=np.float32,
    )
    return rgb * gains


def smoothstep(e0: float, e1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - e0) / max(e1 - e0, 1e-9), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)
