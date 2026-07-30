"""Digital-transport failures: DAT error concealment and CD anti-shock
buffer skipping. Purely digital artifacts - hard edges, perfect repeats."""

from __future__ import annotations

import numpy as np

from ...engine.graph import Context, Effect, Param, register
from ...engine.rng import stream
from . import _util as U


@register
class ADatError(Effect):
    eid = "a_dat_error"
    label = "DAT Errors"
    kind = "audio"
    desc = "Digital tape error concealment: brief sample-and-hold interpolation holds (a frozen buzz, not an analog dip) and occasional hard full mutes."
    PARAMS = (
        Param("error_rate", "Hold Rate", "float", 12.0, 0.0, 120.0, unit="/min",
              desc="Concealment events per minute - the player freezes 2–10 ms of samples.", group="Damage", iscale=True),
        Param("mute_rate", "Mute Rate", "float", 1.5, 0.0, 30.0, unit="/min",
              desc="Uncorrectable blocks per minute: 50–200 ms of hard digital silence.", group="Damage", iscale=True),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        sr = ctx.sr
        x = audio.copy()
        dur = n / sr

        if self.v["error_rate"] > 0:
            g = stream(ctx.seed, f"{self.key}:hold")
            for t0 in U.event_times(g, self.v["error_rate"], dur, min_gap_s=0.08):
                L = int(g.uniform(0.002, 0.010) * sr)
                s = int(t0 * sr)
                e = min(s + max(L, 4), n)
                if e <= s or s < 1:
                    continue
                x[s:e] = x[s - 1]  # sample-and-hold: dead-flat, hard edges

        if self.v["mute_rate"] > 0:
            g = stream(ctx.seed, f"{self.key}:mute")
            for t0 in U.event_times(g, self.v["mute_rate"], dur, min_gap_s=0.5):
                L = int(g.uniform(0.050, 0.200) * sr)
                s = int(t0 * sr)
                e = min(s + L, n)
                if e > s:
                    x[s:e] = 0.0  # no fade - the edge click is authentic
        return x.astype(np.float32)


@register
class ACdSkip(Effect):
    eid = "a_cd_skip"
    label = "CD Skip"
    kind = "audio"
    desc = "Skipping CD player: the anti-shock buffer loops a 40–120 ms chunk 2–6 times with perfect digital edges, then the laser lands further on."
    PARAMS = (
        Param("rate", "Skip Rate", "float", 3.0, 0.0, 30.0, unit="/min",
              desc="Skip events per minute.", group="Damage", iscale=True),
    )

    @staticmethod
    def _zero_cross_near(mono: np.ndarray, i: int, sr: int) -> int:
        """Snap an index to the nearest rising zero crossing within ±5 ms."""
        n = len(mono)
        w0 = max(i - int(0.005 * sr), 1)
        w1 = min(i + int(0.005 * sr), n - 1)
        if w1 <= w0:
            return i
        seg = mono[w0:w1]
        prev = mono[w0 - 1 : w1 - 1]
        idx = np.nonzero((prev <= 0) & (seg > 0))[0]
        if len(idx) == 0:
            return i
        return int(w0 + idx[np.argmin(np.abs(idx + w0 - i))])

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        sr = ctx.sr
        rate = self.v["rate"]
        if rate <= 0 or n < sr // 2:
            return audio
        x = audio.copy()
        mono = x.mean(axis=1)
        g = stream(ctx.seed, f"{self.key}:skips")
        for t0 in U.event_times(g, rate, n / sr, min_gap_s=1.2):
            s = self._zero_cross_near(mono, int(t0 * sr), sr)
            L0 = int(g.uniform(0.040, 0.120) * sr)
            e = self._zero_cross_near(mono, s + L0, sr)
            L = e - s
            reps = int(g.integers(2, 7))
            if L < int(0.020 * sr) or s + L >= n:
                continue
            chunk = x[s:e].copy()
            # overwrite forward: duration is preserved and the program resumes
            # exactly where it would have been - i.e. it 'jumps forward' past
            # everything the loop papered over.
            for r in range(1, reps + 1):
                a = s + r * L
                if a >= n:
                    break
                b = min(a + L, n)
                x[a:b] = chunk[: b - a]
        return x.astype(np.float32)
