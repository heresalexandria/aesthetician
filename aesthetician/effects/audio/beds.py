"""Baked ambience beds: pre-rendered environment loops (projector rooms, CRT
whine, HVAC halls…) mixed under the program with ducking and de-looped seams.

Beds are synthesized offline by scripts/bake_audio_beds.py into
assets/audio-beds/*.wav (48 kHz stereo, loop-ready, peak ≤ −12 dBFS).
"""

from __future__ import annotations

import os

import numpy as np
from scipy import signal as sps
from scipy.io import wavfile

from ...engine.graph import Context, Effect, Param, register
from ...engine.rng import stream
from . import _util as U

BED_NAMES = (
    "projector_16mm_run",
    "projector_8mm_run",
    "projector_35mm_booth",
    "tv_shop_wall",
    "fluorescent_office",
    "vcr_transport",
    "record_surface_loop",
    "tape_deck_room",
    "crt_whine",
    "air_handler_hall",
)


def _beds_dir(ctx: Context) -> str:
    root = ctx.asset_root
    if not root:
        from ...engine.render import default_asset_root
        root = default_asset_root()
    return os.path.join(root, "audio-beds")


def _load_bed(path: str) -> tuple[int, np.ndarray]:
    sr, data = wavfile.read(path)
    if data.dtype == np.int16:
        x = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        x = data.astype(np.float32) / 2147483648.0
    elif data.dtype == np.uint8:
        x = (data.astype(np.float32) - 128.0) / 128.0
    else:
        x = data.astype(np.float32)
    if x.ndim == 1:
        x = x[:, None]
    return int(sr), x


@register
class ABed(Effect):
    eid = "a_bed"
    label = "Ambience Bed"
    kind = "audio"
    desc = "Mixes a baked environment bed (running projector, shop of TVs, HVAC hall…) under the program, with gentle ducking and randomized loop points so long clips never read as loops."
    PARAMS = (
        Param("bed", "Bed", "enum", "projector_16mm_run", choices=BED_NAMES,
              desc="Which baked bed to lay under the program (bake with scripts/bake_audio_beds.py).", group="Noise"),
        Param("level_db", "Bed Level", "float", -32.0, -60.0, -12.0, unit="dB",
              desc="RMS level of the bed in the mix.", group="Noise"),
        Param("duck", "Ducking", "float", 0.3, 0.0, 1.0,
              desc="Gently lowers the bed (up to −8 dB) while the program is loud, like ears adapting to the room.", group="Dynamics", iscale=True),
        Param("loop_jitter", "Loop Jitter", "float", 0.5, 0.0, 1.0,
              desc="Reassembles the bed from randomized crossfaded slices so repeats never line up; 0 = plain seamless loop.", group="Noise"),
    )

    def prepare(self, ctx: Context) -> None:
        d = _beds_dir(ctx)
        path = os.path.join(d, f"{self.v['bed']}.wav")
        if not os.path.isfile(path):
            have = []
            if os.path.isdir(d):
                have = sorted(os.path.splitext(f)[0] for f in os.listdir(d)
                              if f.lower().endswith(".wav"))
            raise RuntimeError(
                f"a_bed: bed '{self.v['bed']}' not found at {path}. "
                f"Available baked beds: {', '.join(have) if have else 'none'}. "
                f"Run `.venv/bin/python scripts/bake_audio_beds.py` to bake them."
            )
        self._bed_sr, self._bed = _load_bed(path)

    def _looped(self, n: int, ch: int, sr: int, ctx: Context) -> np.ndarray:
        bed = self._bed
        if self._bed_sr != sr:
            bed = sps.resample_poly(bed, sr, self._bed_sr, axis=0).astype(np.float32)
        # channel match
        if bed.shape[1] >= ch:
            bed = bed[:, :ch]
        else:
            bed = np.repeat(bed, ch, axis=1)[:, :ch]
        m = bed.shape[0]
        if m < sr // 2:  # degenerate file; just tile it
            reps = int(np.ceil(n / max(m, 1)))
            return np.tile(bed, (reps, 1))[:n]

        jit = self.v["loop_jitter"]
        if jit <= 0.001 or m < int(2.5 * sr):
            if m >= n:
                return bed[:n].copy()
            reps = int(np.ceil(n / m))
            return np.tile(bed, (reps, 1))[:n]  # ends are baked loop-ready

        # reassemble from random slices, equal-power crossfaded, so the seam
        # position and content order never repeat
        g = stream(ctx.seed, f"{self.key}:loop")
        xf = int(min(0.35 * sr, m // 8))
        lo_s = 2.5 + 2.5 * (1.0 - jit)   # higher jitter = shorter, choppier slices
        hi_s = 6.0 + 6.0 * (1.0 - jit)
        pieces = []
        total = 0
        while total < n + xf:
            s = int(g.uniform(0, max(m - 2 * xf, 1)))
            L = min(int(g.uniform(lo_s, hi_s) * sr), m - s)
            if L < 2 * xf:
                L = m - s  # slice runs to the end of the bed; still >= 2*xf by s range
            pieces.append(bed[s : s + L])
            total += L - xf
        ramp_out = np.sqrt(np.linspace(1.0, 0.0, xf, dtype=np.float32))[:, None]
        ramp_in = np.sqrt(np.linspace(0.0, 1.0, xf, dtype=np.float32))[:, None]
        out = np.zeros((total + xf, ch), np.float32)
        pos = 0
        for i, seg in enumerate(pieces):
            segc = seg.copy()
            if i > 0:
                segc[:xf] *= ramp_in
                out[pos : pos + xf] *= ramp_out
            out[pos : pos + segc.shape[0]] += segc
            pos += segc.shape[0] - xf
        return out[:n]

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        sr = ctx.sr
        if not hasattr(self, "_bed"):
            self.prepare(ctx)
        bed = self._looped(n, ch, sr, ctx)
        bed = bed * (U.db_to_lin(self.v["level_db"]) / (U.rms(bed) + 1e-12))

        duck = self.v["duck"]
        if duck > 0:
            env = U.envelope(audio, sr, attack_ms=30.0, release_ms=700.0, mode="rms")
            ref = np.percentile(env, 90) + 1e-9
            loud = np.clip(env / ref, 0.0, 1.2)
            gain_db = -8.0 * duck * loud
            bed = bed * np.power(10.0, gain_db / 20.0)[:, None].astype(np.float32)

        return U.peak_guard((audio + bed).astype(np.float32))
