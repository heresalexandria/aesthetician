"""Deterministic random streams and band-limited temporal noise.

Every stochastic element in a render (grain, weave, flicker, dropouts…) draws
from a stream keyed by (render seed, string key). The same seed always
reproduces the same render exactly.
"""

from __future__ import annotations

import hashlib

import numpy as np
from scipy import signal as sps


def _entropy(seed: int, key: str) -> np.random.SeedSequence:
    digest = hashlib.sha256(f"{seed}:{key}".encode()).digest()
    words = np.frombuffer(digest[:16], dtype=np.uint32)
    return np.random.SeedSequence(words.tolist())


def stream(seed: int, key: str) -> np.random.Generator:
    """A dedicated PCG64 generator for `key`, decorrelated from all other keys."""
    return np.random.Generator(np.random.PCG64(_entropy(seed, key)))


class TemporalNoise:
    """Precomputed per-frame noise tracks, cached per (key) for one render.

    Tracks are sampled once per output frame. Helpers shape them into the
    slow drifts and twitchy jitters that analog media exhibit.
    """

    def __init__(self, seed: int, fps: float, n_frames: int):
        self.seed = seed
        self.fps = max(fps, 1.0)
        self.n = max(n_frames, 1)
        self._cache: dict[str, np.ndarray] = {}

    def white(self, key: str) -> np.ndarray:
        """Uniform white noise in [-1, 1], one sample per frame."""
        if key not in self._cache:
            g = stream(self.seed, f"tn:{key}")
            self._cache[key] = g.uniform(-1.0, 1.0, self.n).astype(np.float32)
        return self._cache[key]

    def smooth(self, key: str, hz: float = 0.5) -> np.ndarray:
        """Band-limited noise (lowpassed white), normalized to roughly [-1, 1]."""
        ck = f"{key}|s{hz:.4f}"
        if ck not in self._cache:
            g = stream(self.seed, f"tn:{key}")
            w = g.standard_normal(self.n + 64).astype(np.float32)
            nyq = self.fps / 2.0
            cut = min(max(hz, 0.01), nyq * 0.95) / nyq
            b, a = sps.butter(2, cut)
            x = sps.filtfilt(b, a, w)[64 // 2 : 64 // 2 + self.n]
            p95 = np.percentile(np.abs(x), 95) + 1e-9
            self._cache[ck] = (x / p95).astype(np.float32)
        return self._cache[ck]

    def drift(self, key: str, hz: float = 0.15) -> np.ndarray:
        """Very slow wander, e.g. gate weave or tape transport drift."""
        return self.smooth(key, hz)

    def onef(self, key: str, alpha: float = 1.0) -> np.ndarray:
        """1/f^alpha 'pink-ish' noise track, normalized to roughly [-1, 1]."""
        ck = f"{key}|f{alpha:.2f}"
        if ck not in self._cache:
            g = stream(self.seed, f"tn:{key}")
            n = self.n
            spec = np.fft.rfft(g.standard_normal(n * 2))
            f = np.fft.rfftfreq(n * 2)
            f[0] = f[1] if len(f) > 1 else 1.0
            spec = spec / (f ** (alpha / 2.0))
            x = np.fft.irfft(spec)[:n]
            p95 = np.percentile(np.abs(x), 95) + 1e-9
            self._cache[ck] = (x / p95).astype(np.float32)
        return self._cache[ck]

    def events(self, key: str, per_second: float, min_gap_s: float = 0.0) -> np.ndarray:
        """Sparse random event mask (1.0 on event frames), Poisson-ish."""
        ck = f"{key}|e{per_second:.4f}|{min_gap_s:.3f}"
        if ck not in self._cache:
            g = stream(self.seed, f"tn:{key}")
            p = min(per_second / self.fps, 1.0)
            mask = (g.random(self.n) < p).astype(np.float32)
            if min_gap_s > 0:
                gap = int(min_gap_s * self.fps)
                last = -gap - 1
                for i in range(self.n):
                    if mask[i]:
                        if i - last <= gap:
                            mask[i] = 0.0
                        else:
                            last = i
            self._cache[ck] = mask
        return self._cache[ck]
