"""Playback-device coloration and mains hum."""

from __future__ import annotations

import numpy as np

from ...engine.graph import Context, Effect, Param, register
from ...engine.rng import stream
from . import _util as U


@register
class ASpeaker(Effect):
    eid = "a_speaker"
    label = "Speaker Sim"
    kind = "audio"
    desc = "Playback-device coloration via biquad cascades: boxy TVs, honky horns, tinny pockets. Strength morphs the recipe back toward flat."
    # recipe: hp (hz, order), lp (hz, order), stages [(kind, hz, dB, q)]
    # kind: 'pk' peaking, 'ls'/'hs' shelves. Gains scale with strength; HP/LP
    # corners log-morph toward 20 Hz / 20 kHz so strength 0 is truly flat
    # (chosen over dry/wet mixing, whose phase offsets comb the midrange).
    _DEVICES = {
        "tv_mono_1965": ((120, 2), (7000, 3), [("pk", 800, 4.0, 1.2), ("pk", 3000, 3.0, 2.0), ("pk", 180, -3.0, 1.0)]),
        "tv_mono_1985": ((90, 2), (10000, 3), [("pk", 650, 3.0, 1.2), ("pk", 2500, 2.5, 1.8), ("hs", 7000, -2.0, 0)]),
        "portable_radio_1975": ((200, 2), (6500, 3), [("pk", 1100, 5.0, 1.4), ("pk", 400, 2.0, 1.2), ("pk", 4500, -2.0, 2.0)]),
        "transistor_pocket_1965": ((350, 3), (4800, 3), [("pk", 1500, 7.0, 1.6), ("pk", 2400, 4.0, 2.2), ("pk", 500, -3.0, 1.2)]),
        "clock_radio_1988": ((250, 2), (5500, 3), [("pk", 900, 5.0, 1.5), ("pk", 2200, 2.0, 1.8)]),
        "laptop_2006": ((300, 3), (14000, 2), [("pk", 1200, 3.0, 1.4), ("pk", 4500, 4.0, 2.0), ("pk", 700, -3.0, 1.5)]),
        "cellphone_2008": ((600, 3), (8000, 2), [("pk", 1800, 6.0, 1.8), ("pk", 3300, 4.0, 2.0)]),
        "gramophone_horn_1915": ((250, 3), (3200, 4), [("pk", 800, 8.0, 1.2), ("pk", 1800, 5.0, 3.0), ("pk", 500, -3.0, 1.5)]),
        "jukebox_1955": ((70, 2), (9000, 3), [("pk", 120, 4.0, 1.0), ("pk", 2500, 3.0, 1.5), ("pk", 5000, -2.0, 2.0)]),
        "car_dash_1978": ((120, 2), (7500, 3), [("pk", 250, 3.0, 1.0), ("pk", 1400, 4.0, 1.5), ("pk", 4500, -3.0, 2.0)]),
        "studio_monitor": ((None, 0), (None, 0), []),
    }
    PARAMS = (
        Param("device", "Device", "enum", "tv_mono_1985", choices=tuple(_DEVICES),
              desc="Playback device recipe.", group="Bandwidth"),
        Param("strength", "Strength", "float", 1.0, 0.0, 1.0,
              desc="Morphs from flat (0) to the full device curve (1).", group="Bandwidth"),
        Param("cabinet_knock", "Cabinet Knock", "float", 0.0, 0.0, 1.0,
              desc="Resonant low-mid box knock (peaking boost near 180 Hz).", group="Bandwidth", iscale=True),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        sr = ctx.sr
        s = self.v["strength"]
        (hp_hz, hp_o), (lp_hz, lp_o), stages = self._DEVICES[self.v["device"]]
        if s <= 0.001:
            hp_hz = lp_hz = None
        x = audio
        if hp_hz:
            f = np.exp(np.log(20.0) * (1 - s) + np.log(hp_hz) * s)  # log-morph from 20 Hz
            x = U.highpass(x, f, sr, order=hp_o)
        if lp_hz:
            f = np.exp(np.log(20000.0) * (1 - s) + np.log(lp_hz) * s)
            x = U.lowpass(x, min(f, sr * 0.49), sr, order=lp_o)
        rows = []
        for kind, f, gdb, q in stages:
            gdb = gdb * s
            if abs(gdb) < 0.05:
                continue
            if kind == "pk":
                rows.append(U.peaking(sr, f, gdb, q))
            else:
                rows.append(U.shelf(sr, f, gdb, high=(kind == "hs")))
        knock = self.v["cabinet_knock"]
        if knock > 0:
            rows.append(U.peaking(sr, 180.0, 6.0 * knock * s if s > 0 else 6.0 * knock, q=4.0))
        if rows:
            x = U.apply_sos(x, U.sos_cascade(*rows))
        x = U.match_rms(x, audio, max_db=9.0)
        return U.peak_guard(x)


@register
class AHum(Effect):
    eid = "a_hum"
    label = "Mains Hum"
    kind = "audio"
    desc = "50/60 Hz mains hum with a harmonic stack; buzz pushes energy into higher harmonics for an angrier tone."
    PARAMS = (
        Param("hz", "Mains", "enum", "60", choices=("60", "50"),
              desc="Mains frequency.", group="Noise"),
        Param("level_db", "Level", "float", -46.0, -80.0, -25.0, unit="dB",
              desc="Hum RMS level.", group="Noise"),
        Param("buzz", "Buzz", "float", 0.2, 0.0, 1.0,
              desc="0 = pure hum, 1 = harsh rectifier buzz.", group="Noise", iscale=True),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        sr = ctx.sr
        lvl = U.db_to_lin(self.v["level_db"])
        if lvl <= 1e-6:
            return audio
        g = stream(ctx.seed, f"{self.key}:hum")
        f0 = float(self.v["hz"])
        buzz = self.v["buzz"]
        wander = f0 + 0.1 * U.control_noise(g, n, sr, 0.02, 0.1, ctrl_sr=50.0)
        phase = 2 * np.pi * np.cumsum(wander) / sr
        p = 3.0 - 2.2 * buzz  # harmonic rolloff exponent
        hum = np.zeros(n, np.float64)
        for k in range(1, 20):
            a = 1.0 / (k ** p)
            if k % 2 == 0:
                a *= 0.5 + 0.5 * buzz  # rectifier evens grow with buzz
            hum += a * np.sin(k * phase + g.uniform(0, 2 * np.pi) * (0 if k == 1 else 1))
        h = hum.astype(np.float32)
        h *= lvl / (U.rms(h) + 1e-12)
        return (audio + h[:, None]).astype(np.float32)  # stereo-coherent
