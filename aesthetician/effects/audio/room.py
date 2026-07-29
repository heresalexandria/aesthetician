"""Spaces: small algorithmic room reverb and slap echo."""

from __future__ import annotations

import numpy as np

from ...engine.graph import Context, Effect, Param, register
from . import _util as U


@register
class ARoom(Effect):
    eid = "a_room"
    label = "Small Room"
    kind = "audio"
    desc = "Schroeder small-room reverb (4 damped combs + 2 allpasses) for the 'recorded in a room / off the TV' feel."
    # classic Schroeder tunings (ms); per-channel prime-ish offsets for width
    _COMBS_L = (29.7, 37.1, 41.1, 43.7)
    _COMBS_R = (30.1, 36.7, 41.9, 44.3)
    PARAMS = (
        Param("size", "Room Size", "float", 1.0, 0.5, 1.6,
              desc="Scales the reflection delays.", group="Damage"),
        Param("decay_s", "Decay", "float", 0.35, 0.1, 1.5, unit="s",
              desc="RT60-style decay time.", group="Damage"),
        Param("damp", "Damping", "float", 0.55, 0.0, 0.95,
              desc="High-frequency absorption in the tail.", group="Damage"),
        Param("predelay_ms", "Predelay", "float", 8.0, 0.0, 60.0, unit="ms",
              desc="Gap before the reverb starts.", group="Damage"),
        Param("mix", "Mix", "float", 0.25, 0.0, 1.0,
              desc="Wet amount.", group="Damage", iscale=True),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        mix = self.v["mix"]
        if mix <= 0.001:
            return audio
        n, ch = audio.shape
        sr = ctx.sr
        size = self.v["size"]
        decay = self.v["decay_s"]
        wet_cols = []
        for c in range(ch):
            combs = self._COMBS_R if (c % 2) else self._COMBS_L
            comb_ms = tuple(m * size for m in combs)
            fb = tuple(10.0 ** (-3.0 * (m / 1000.0) / decay) for m in comb_ms)
            wet_cols.append(U.schroeder(audio[:, c], sr, comb_ms, fb,
                                        ap_ms=(5.0, 1.7), ap_g=0.7, damp=self.v["damp"]))
        wet = np.stack(wet_cols, axis=1)
        pre = int(self.v["predelay_ms"] * sr / 1000.0)
        if pre > 0:
            wet = np.vstack([np.zeros((pre, ch), np.float32), wet[: n - pre]])
        wet = U.highpass(wet, 90.0, sr, order=1)  # keep mud out of the tail
        wet = U.match_rms(wet, audio, max_db=12.0)
        out = audio * (1.0 - 0.3 * mix) + wet * mix
        return U.peak_guard(out.astype(np.float32))


@register
class ASlap(Effect):
    eid = "a_slap"
    label = "Slap Echo"
    kind = "audio"
    desc = "Single or multi-tap slapback echo with progressive damping — gym PA and hallway flavor."
    PARAMS = (
        Param("delay_ms", "Delay", "float", 110.0, 20.0, 600.0, unit="ms",
              desc="Slap delay time.", group="Damage"),
        Param("gain_db", "Echo Level", "float", -8.0, -30.0, 0.0, unit="dB",
              desc="Level of the first repeat.", group="Damage"),
        Param("repeats", "Repeats", "int", 1, 1, 3,
              desc="Number of echoes.", group="Damage"),
        Param("damp", "Damping", "float", 0.5, 0.0, 1.0,
              desc="Progressive treble loss on each repeat.", group="Damage"),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        sr = ctx.sr
        D = int(self.v["delay_ms"] * sr / 1000.0)
        if D <= 0 or D >= n:
            return audio
        g = U.db_to_lin(self.v["gain_db"])
        lp_hz = 12000.0 * (2500.0 / 12000.0) ** self.v["damp"]
        out = audio.copy()
        tap = audio
        for r in range(1, self.v["repeats"] + 1):
            tap = U.lowpass(tap, lp_hz, sr, order=1) * g
            if r * D >= n:
                break
            out[r * D :] += tap[: n - r * D]
        return U.peak_guard(out)
