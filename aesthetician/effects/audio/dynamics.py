"""Era dynamics: broadcast AGC, glue compression, and clippers."""

from __future__ import annotations

import numpy as np

from ...engine.graph import Context, Effect, Param, register
from . import _util as U


@register
class AAgc(Effect):
    eid = "a_agc"
    label = "Vintage AGC"
    kind = "audio"
    desc = "Broadcast automatic gain control: slowly breathes gain toward a target level, pumping audibly on program peaks."
    PARAMS = (
        Param("target_db", "Target", "float", -16.0, -36.0, -6.0, unit="dB",
              desc="Program level the AGC rides toward.", group="Dynamics"),
        Param("max_gain_db", "Max Gain", "float", 12.0, 0.0, 24.0, unit="dB",
              desc="Gain ceiling when the program is quiet.", group="Dynamics"),
        Param("attack_ms", "Attack", "float", 40.0, 1.0, 500.0, unit="ms",
              desc="How fast gain ducks on peaks.", group="Dynamics"),
        Param("release_ms", "Release", "float", 900.0, 50.0, 4000.0, unit="ms",
              desc="How slowly gain breathes back up.", group="Dynamics"),
        Param("amount", "Amount", "float", 1.0, 0.0, 1.0,
              desc="Dry/wet on the gain ride.", group="Dynamics", iscale=True),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        amt = self.v["amount"]
        if amt <= 0:
            return audio
        env = U.envelope(audio, ctx.sr, attack_ms=15.0, release_ms=80.0, mode="rms")
        target = U.db_to_lin(self.v["target_db"])
        desired = target / np.maximum(env, 1e-5)
        desired = np.clip(desired, U.db_to_lin(-24.0), U.db_to_lin(self.v["max_gain_db"]))
        gain = U.smooth_gain(desired.astype(np.float32), ctx.sr,
                             self.v["attack_ms"], self.v["release_ms"])
        if amt < 1.0:
            gain = gain ** amt
        return U.peak_guard((audio * gain[:, None]).astype(np.float32))


@register
class ACompressor(Effect):
    eid = "a_compressor"
    label = "Compressor"
    kind = "audio"
    desc = "General era glue compressor with soft knee and peak/RMS detection."
    PARAMS = (
        Param("threshold_db", "Threshold", "float", -20.0, -50.0, 0.0, unit="dB", group="Dynamics",
              desc="Level where gain reduction begins."),
        Param("ratio", "Ratio", "float", 3.0, 1.0, 20.0, group="Dynamics",
              desc="Compression ratio above threshold."),
        Param("attack_ms", "Attack", "float", 8.0, 0.2, 200.0, unit="ms", group="Dynamics",
              desc="Gain-reduction onset time."),
        Param("release_ms", "Release", "float", 200.0, 20.0, 2000.0, unit="ms", group="Dynamics",
              desc="Gain-reduction recovery time."),
        Param("knee_db", "Knee", "float", 6.0, 0.0, 18.0, unit="dB", group="Dynamics",
              desc="Soft-knee width around the threshold."),
        Param("makeup_db", "Makeup", "float", 0.0, 0.0, 24.0, unit="dB", group="Dynamics",
              desc="Output makeup gain."),
        Param("detector", "Detector", "enum", "rms", choices=("rms", "peak"), group="Dynamics",
              desc="Envelope detector law."),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        sr = ctx.sr
        env = U.envelope(audio, sr, attack_ms=0.5, release_ms=30.0, mode=self.v["detector"])
        level_db = 20.0 * np.log10(np.maximum(env, 1e-6))
        thr, knee, ratio = self.v["threshold_db"], self.v["knee_db"], self.v["ratio"]
        over = level_db - thr
        slope = 1.0 - 1.0 / ratio
        if knee > 0:
            # quadratic soft knee
            below = over <= -knee / 2
            inside = (~below) & (over < knee / 2)
            gr = np.where(below, 0.0, slope * over)
            gr = np.where(inside, slope * (over + knee / 2) ** 2 / (2 * knee), gr)
        else:
            gr = np.maximum(over, 0.0) * slope
        gain = np.power(10.0, -gr / 20.0).astype(np.float32)
        gain = U.smooth_gain(gain, sr, self.v["attack_ms"], self.v["release_ms"])
        out = audio * gain[:, None] * U.db_to_lin(self.v["makeup_db"])
        return U.peak_guard(out.astype(np.float32))


@register
class ADistortion(Effect):
    eid = "a_distortion"
    label = "Distortion"
    kind = "audio"
    desc = "General clipper: soft tanh, hard clip, gated fuzz, or asymmetric — with post tone tilt and automatic level compensation."
    PARAMS = (
        Param("type", "Type", "enum", "soft", choices=("soft", "hard", "fuzz", "asym"),
              desc="Clipping law.", group="Dynamics"),
        Param("drive", "Drive", "float", 3.0, 1.0, 12.0,
              desc="Input gain into the clipper.", group="Dynamics"),
        Param("tone", "Tone", "float", 0.0, -1.0, 1.0,
              desc="Post tilt: −1 dark to +1 bright.", group="Bandwidth"),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        d = self.v["drive"]
        peak = float(np.max(np.abs(audio))) + 1e-9
        x = audio / peak
        t = self.v["type"]
        if t == "soft":
            y = np.tanh(d * x)
        elif t == "hard":
            y = np.clip(d * x, -1.0, 1.0)
        elif t == "fuzz":
            # biased, heavily saturated, with a crude crossover gate notch
            y = np.tanh(2.0 * d * (x + 0.08))
            y = y - np.tanh(2.0 * d * 0.08)
            y = y - 0.3 * np.tanh(30.0 * y) / 30.0 * d
        else:  # asym: gentle on top, harder underneath
            y = np.where(x >= 0, np.tanh(d * x), np.tanh(2.2 * d * x) / 1.4)
        y = (y * peak).astype(np.float32)
        tone = self.v["tone"]
        if abs(tone) > 0.01:
            y = U.tilt(y, ctx.sr, 6.0 * tone, pivot_hz=1200.0)
        y = U.match_rms(y, audio, max_db=12.0)
        return U.peak_guard(y)
