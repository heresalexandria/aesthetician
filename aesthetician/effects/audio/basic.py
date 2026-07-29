"""Basic audio utility effects (also the reference pattern for audio DSP)."""

from __future__ import annotations

import numpy as np
from scipy import signal as sps

from ...engine.graph import Context, Effect, Param, register


@register
class AGain(Effect):
    eid = "a_gain"
    label = "Gain"
    kind = "audio"
    desc = "Output gain in dB."
    PARAMS = (Param("db", "Gain", "float", 0.0, -60.0, 24.0, unit="dB", desc="−60 is effectively mute."),)

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        return audio * (10.0 ** (self.v["db"] / 20.0))


@register
class ABandlimit(Effect):
    eid = "a_bandlimit"
    label = "Bandwidth"
    kind = "audio"
    desc = "High/low frequency limits of the medium (butterworth)."
    PARAMS = (
        Param("low_hz", "Low Cut", "float", 20.0, 10.0, 2000.0, unit="Hz"),
        Param("high_hz", "High Cut", "float", 20000.0, 500.0, 22000.0, unit="Hz"),
        Param("order", "Slope", "int", 4, 1, 8, desc="Filter order (steepness)."),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        nyq = ctx.sr / 2.0
        x = audio
        lo = self.v["low_hz"] / nyq
        hi = min(self.v["high_hz"] / nyq, 0.99)
        if lo > 0.001:
            sos = sps.butter(self.v["order"], lo, btype="high", output="sos")
            x = sps.sosfiltfilt(sos, x, axis=0)
        if hi < 0.99:
            sos = sps.butter(self.v["order"], hi, btype="low", output="sos")
            x = sps.sosfiltfilt(sos, x, axis=0)
        return x.astype(np.float32)


@register
class AMonoize(Effect):
    eid = "a_mono"
    label = "Mono Fold"
    kind = "audio"
    desc = "Collapse to mono (single mic / single speaker era), optionally narrow instead."
    PARAMS = (
        Param("amount", "Amount", "float", 1.0, 0.0, 1.0, desc="1 = full mono."),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        if audio.shape[1] < 2 or self.v["amount"] <= 0:
            return audio
        mid = audio.mean(axis=1, keepdims=True)
        return (audio * (1.0 - self.v["amount"]) + mid * self.v["amount"]).astype(np.float32)
