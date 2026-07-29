"""Film sound: optical soundtrack coloration and projector-in-the-room beds."""

from __future__ import annotations

import numpy as np

from ...engine.graph import Context, Effect, Param, register
from ...engine.rng import stream
from . import _util as U


@register
class AOpticalTrack(Effect):
    eid = "a_optical_track"
    label = "Optical Soundtrack"
    kind = "audio"
    desc = "Variable-area film soundtrack: steep band limit, cell-grain noise floor, 96 Hz sprocket flutter and slight photographic distortion."
    # academy presets: (low_hz, high_hz, extra top shelf dB @3k)
    _ACADEMY = {
        "newsreel_1930s": (150.0, 3800.0, -6.0),
        "feature_1940s": (100.0, 5200.0, -3.0),
        "classroom_16mm": (150.0, 4500.0, -5.0),
        "none": (None, None, 0.0),
    }
    PARAMS = (
        Param("low_hz", "Low Cut", "float", 100.0, 40.0, 400.0, unit="Hz",
              desc="Bottom of the optical track band.", group="Bandwidth"),
        Param("high_hz", "High Cut", "float", 6500.0, 2000.0, 9000.0, unit="Hz",
              desc="Top of the optical track band.", group="Bandwidth"),
        Param("academy_rolloff", "Academy Curve", "enum", "none", choices=tuple(_ACADEMY),
              desc="Era playback-curve preset; overrides the band edges when set.", group="Bandwidth"),
        Param("cell_noise", "Cell Noise", "float", -48.0, -75.0, -28.0, unit="dB",
              desc="Granular photo-cell crackle-hiss floor.", group="Noise"),
        Param("flutter", "Sprocket Flutter", "float", 0.5, 0.0, 1.0,
              desc="96 Hz sprocket amplitude wobble and pitch micro-flutter.", group="Pitch", iscale=True),
        Param("drive", "Track Drive", "float", 1.3, 1.0, 4.0,
              desc="Photographic overmodulation distortion (slight).", group="Dynamics"),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        sr = ctx.sr
        lo, hi, extra_shelf = self._ACADEMY[self.v["academy_rolloff"]]
        if lo is None:
            lo, hi = self.v["low_hz"], self.v["high_hz"]
        x = audio

        fl = self.v["flutter"]
        if fl > 0 and n > 16:
            g = stream(ctx.seed, f"{self.key}:sprocket")
            t = np.arange(n) / sr
            ph = g.uniform(0, 2 * np.pi)
            wob = np.sin(2 * np.pi * 96.0 * t + ph)
            wob += 0.4 * U.control_noise(g, n, sr, 60.0, 130.0, ctrl_sr=400.0)
            cents = 1.5 * fl * wob
            x = U.variable_speed(x, np.exp2(cents / 1200.0))
            am = (1.0 + 0.03 * fl * wob).astype(np.float32)
            x = x * am[:, None]

        d = self.v["drive"]
        if d > 1.01:
            y = np.tanh(d * x) / d
            x = U.match_rms(y, x, max_db=6.0)

        x = U.highpass(x, lo, sr, order=3)
        x = U.lowpass(x, hi, sr, order=5)
        if extra_shelf < 0:
            x = U.apply_sos(x, U.shelf(sr, 3000.0, extra_shelf, high=True, s=0.7))

        lvl = U.db_to_lin(self.v["cell_noise"])
        if lvl > 1e-6:
            g = stream(ctx.seed, f"{self.key}:cell")
            k = int(g.poisson(900.0 * n / sr))  # dense granular floor
            grain = np.zeros(n, np.float32)
            if k > 0:
                idx = g.integers(0, n, k)
                amp = (g.random(k) ** 2.0) * np.where(g.random(k) < 0.5, -1.0, 1.0)
                np.add.at(grain, idx, amp.astype(np.float32))
            hiss = g.standard_normal(n).astype(np.float32) * 0.35
            bed = U.bandpass((grain + hiss)[:, None], 300.0, min(hi, 5500.0), sr, order=2)
            bed *= lvl / (U.rms(bed) + 1e-12)
            x = x + bed
        return U.peak_guard(x)


@register
class AProjector(Effect):
    eid = "a_projector"
    label = "Projector Bed"
    kind = "audio"
    desc = "Synthesized running projector: shutter-rate claw clatter, wandering motor tone and air whoosh, mixed under the signal."
    # machine: (pulse_hz, clatter band, clatter gain, motor_hz, motor gain, whoosh gain, extra LP)
    _MACHINES = {
        "proj_16mm": (24.0, (700.0, 3200.0), 1.0, 55.0, 0.5, 0.4, None),
        "proj_8mm": (18.0, (500.0, 2800.0), 1.1, 50.0, 0.8, 0.5, None),
        "proj_35mm_booth": (24.0, (300.0, 1200.0), 0.35, 40.0, 1.0, 0.9, 1400.0),
    }
    PARAMS = (
        Param("machine", "Machine", "enum", "proj_16mm", choices=tuple(_MACHINES),
              desc="Projector type; 35 mm booth is distant and muffled.", group="Noise"),
        Param("level_db", "Bed Level", "float", -34.0, -60.0, -15.0, unit="dB",
              desc="Overall projector bed level.", group="Noise"),
        Param("distance", "Distance", "float", 0.2, 0.0, 1.0,
              desc="Moves the machine away: darker and quieter.", group="Noise"),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        sr = ctx.sr
        pulse_hz, (b_lo, b_hi), cg, motor_hz, mg, wg, extra_lp = self._MACHINES[self.v["machine"]]
        g = stream(ctx.seed, f"{self.key}:bed")
        t = np.arange(n) / sr

        # claw clatter: main pulse + weaker offset sub-pulse each frame period
        period = sr / pulse_hz
        n_pulses = int(n / period) + 2
        starts = (np.arange(n_pulses) * period).astype(np.float64)
        starts += g.uniform(-0.001, 0.001, n_pulses) * sr  # ±1 ms timing jitter
        train = np.zeros(n, np.float32)
        amps = (1.0 + g.uniform(-0.3, 0.3, n_pulses)).astype(np.float32)
        sub_amps = amps * g.uniform(0.35, 0.6, n_pulses).astype(np.float32)
        idx = starts.astype(np.int64)
        sub_idx = (starts + 0.42 * period).astype(np.int64)
        ok = (idx >= 0) & (idx < n)
        np.add.at(train, idx[ok], amps[ok])
        ok = (sub_idx >= 0) & (sub_idx < n)
        np.add.at(train, sub_idx[ok], -sub_amps[ok])
        clatter = U.bandpass(train[:, None], b_lo, b_hi, sr, order=2)[:, 0]
        clatter *= cg / (np.max(np.abs(clatter)) + 1e-9)

        # motor tone with slight wander
        wander = 1.0 + 0.015 * U.control_noise(g, n, sr, 0.1, 0.6, ctrl_sr=100.0)
        phase = 2 * np.pi * np.cumsum(motor_hz * wander) / sr
        motor = np.zeros(n, np.float64)
        for k, a in ((1, 1.0), (2, 0.55), (3, 0.3), (4, 0.15), (6, 0.08)):
            motor += a * np.sin(k * phase + g.uniform(0, 2 * np.pi))
        motor *= mg * 0.25 * (1.0 + 0.15 * U.control_noise(g, n, sr, 0.2, 1.0, ctrl_sr=100.0))

        # air / fan whoosh, shutter-modulated a touch
        cols = []
        for c in range(max(ch, 1)):
            w = stream(ctx.seed, f"{self.key}:whoosh{c}").standard_normal(n).astype(np.float32)
            cols.append(w)
        whoosh = np.stack(cols, axis=1)
        whoosh = U.lowpass(U.highpass(whoosh, 80.0, sr, 1), 900.0, sr, order=2)
        whoosh *= wg / (U.rms(whoosh) + 1e-12) * 0.28
        shutter_am = (1.0 + 0.10 * np.sin(2 * np.pi * pulse_hz * t)).astype(np.float32)
        whoosh *= shutter_am[:, None]

        bed = whoosh * 0.5
        mono = clatter + motor.astype(np.float32)
        if ch >= 2:
            # slight width: tiny inter-channel delay on the mechanical part
            d = int(sr * 0.0004)
            mech = np.stack([mono, np.concatenate([np.zeros(d, np.float32), mono[:-d] if d else mono])], axis=1)
            mech = mech[:, :ch]
        else:
            mech = mono[:, None]
        bed = bed + mech * np.array([[1.0, 0.92]], np.float32)[:, :ch]

        dist = self.v["distance"]
        lp = 8000.0 * (800.0 / 8000.0) ** dist
        if extra_lp:
            lp = min(lp, extra_lp)
        bed = U.lowpass(bed, lp, sr, order=2)
        bed = U.highpass(bed, 30.0, sr, order=1)
        lvl = U.db_to_lin(self.v["level_db"] - 9.0 * dist)
        bed *= lvl / (U.rms(bed) + 1e-12)
        return U.peak_guard(audio + bed)
