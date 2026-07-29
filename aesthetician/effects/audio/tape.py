"""Magnetic tape: wow/flutter transport instability, bias hiss, saturation,
oxide dropouts and azimuth error."""

from __future__ import annotations

import numpy as np
from scipy import signal as sps

from ...engine.graph import Context, Effect, Param, register
from ...engine.rng import stream
from . import _util as U


@register
class AWowFlutter(Effect):
    eid = "a_wow_flutter"
    label = "Wow & Flutter"
    kind = "audio"
    desc = "Tape-transport speed instability: slow wow, fast flutter, scrape roughness, constant speed error and start-up wobble."
    PARAMS = (
        Param("wow_depth", "Wow Depth", "float", 6.0, 0.0, 60.0, unit="cents",
              desc="Slow (0.4–2 Hz) pitch wander depth.", group="Pitch", iscale=True),
        Param("flutter_depth", "Flutter Depth", "float", 3.0, 0.0, 30.0, unit="cents",
              desc="Fast (6–30 Hz) pitch jitter depth.", group="Pitch", iscale=True),
        Param("scrape", "Scrape Flutter", "float", 0.0, 0.0, 1.0,
              desc="50–200 Hz micro-roughness from tape scraping the heads.", group="Pitch", iscale=True),
        Param("speed_pct", "Speed Error", "float", 0.0, -3.0, 3.0, unit="%",
              desc="Constant transport speed error (positive = fast and high).", group="Pitch"),
        Param("start_wobble", "Start-up Wobble", "bool", False,
              desc="First ~0.7 s starts about 4% slow and rises as the motor gets up to speed.", group="Pitch"),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n = audio.shape[0]
        if n < 16:
            return audio
        sr = ctx.sr
        cents = np.zeros(n, np.float64)
        if self.v["wow_depth"] > 0:
            cents += self.v["wow_depth"] * U.control_noise(
                stream(ctx.seed, f"{self.key}:wow"), n, sr, 0.4, 2.0, ctrl_sr=200.0)
        if self.v["flutter_depth"] > 0:
            cents += self.v["flutter_depth"] * U.control_noise(
                stream(ctx.seed, f"{self.key}:flutter"), n, sr, 6.0, 30.0, ctrl_sr=400.0)
        if self.v["scrape"] > 0:
            cents += 2.5 * self.v["scrape"] * U.control_noise(
                stream(ctx.seed, f"{self.key}:scrape"), n, sr, 50.0, 200.0, ctrl_sr=1000.0)
        speed = (1.0 + self.v["speed_pct"] / 100.0) * np.exp2(cents / 1200.0)
        if self.v["start_wobble"]:
            t = np.arange(n) / sr
            settle = 1.0 - 0.04 * np.exp(-t / 0.22) + 0.006 * np.exp(-t / 0.35) * np.sin(2 * np.pi * 2.2 * t)
            speed = speed * settle
        return U.variable_speed(audio, speed)


@register
class ATapeHiss(Effect):
    eid = "a_tape_hiss"
    label = "Tape Hiss"
    kind = "audio"
    desc = "Bias hiss of the tape formulation: pre-emphasized noise floor, decorrelated per channel."
    # (top-tilt dB, lowpass Hz, level offset dB)
    _TYPES = {
        "cassette": (6.0, 12000.0, 0.0),
        "reel_15ips": (3.0, 17000.0, -7.0),
        "reel_375ips": (5.0, 9500.0, 2.0),
        "dictaphone": (2.0, 5200.0, 6.0),
    }
    PARAMS = (
        Param("level_db", "Hiss Level", "float", -46.0, -70.0, -25.0, unit="dB",
              desc="RMS level of the hiss floor.", group="Noise"),
        Param("type", "Tape Type", "enum", "cassette", choices=tuple(_TYPES),
              desc="Formulation/speed preset shaping tilt and bandwidth.", group="Noise"),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        tilt_db, lp_hz, off_db = self._TYPES[self.v["type"]]
        cols = []
        for c in range(ch):
            g = stream(ctx.seed, f"{self.key}:hiss{c}")
            w = g.standard_normal(n).astype(np.float32)
            cols.append(w)
        hiss = np.stack(cols, axis=1)
        hiss = U.tilt(hiss, ctx.sr, tilt_db, pivot_hz=2500.0)
        hiss = U.lowpass(hiss, lp_hz, ctx.sr, order=3)
        hiss = U.highpass(hiss, 35.0, ctx.sr, order=1)
        target = U.db_to_lin(self.v["level_db"] + off_db)
        hiss *= target / U.rms(hiss)
        return (audio + hiss).astype(np.float32)


@register
class ATapeSat(Effect):
    eid = "a_tape_sat"
    label = "Tape Saturation"
    kind = "audio"
    desc = "Magnetic saturation: pre-emphasized tanh compression with head-bump low end and drive-dependent self-erasure of highs."
    PARAMS = (
        Param("drive", "Drive", "float", 2.0, 1.0, 8.0,
              desc="How hard the tape is hit; higher = more squash and grit.", group="Dynamics"),
        Param("bump_db", "Head Bump", "float", 2.5, 0.0, 8.0, unit="dB",
              desc="Low-frequency head-bump resonance around 90 Hz.", group="Bandwidth"),
        Param("hf_loss", "HF Loss", "float", 0.4, 0.0, 1.0,
              desc="Self-erasure top-end rolloff, scaled further by drive.", group="Bandwidth", iscale=True),
    )

    _EMPH_DB = 8.0
    _EMPH_HZ = 1800.0

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        sr = ctx.sr
        d = self.v["drive"]
        x = U.apply_sos(audio, U.shelf(sr, self._EMPH_HZ, self._EMPH_DB, high=True, s=0.6))
        x = np.tanh(d * x) / d  # unity small-signal gain, soft peak squash
        x = U.apply_sos(x, U.shelf(sr, self._EMPH_HZ, -self._EMPH_DB, high=True, s=0.6))
        if self.v["bump_db"] > 0:
            x = U.apply_sos(x, U.peaking(sr, 90.0, self.v["bump_db"], q=0.8))
        loss = np.clip(self.v["hf_loss"] * (0.4 + 0.2 * d), 0.0, 1.0)
        if loss > 0.01:
            cutoff = 18000.0 * (6500.0 / 18000.0) ** loss
            x = U.lowpass(x, cutoff, sr, order=2)
        x = U.match_rms(x, audio, max_db=9.0)
        return U.peak_guard(x)


@register
class ATapeDropouts(Effect):
    eid = "a_tape_dropouts"
    label = "Tape Dropouts"
    kind = "audio"
    desc = "Oxide-shedding level dropouts with momentary HF loss, plus azimuth error (drifting HF smear and inter-channel micro-delay)."
    PARAMS = (
        Param("rate", "Dropout Rate", "float", 6.0, 0.0, 120.0, unit="/min",
              desc="Average dropout events per minute.", group="Damage", iscale=True),
        Param("depth_db", "Max Depth", "float", 30.0, 6.0, 40.0, unit="dB",
              desc="Deepest possible dropout attenuation.", group="Damage"),
        Param("azimuth", "Azimuth Error", "float", 0.0, 0.0, 1.0,
              desc="Head misalignment: slow HF smear and drifting inter-channel delay.", group="Damage", iscale=True),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        sr = ctx.sr
        dur = n / sr
        x = audio.copy()

        az = self.v["azimuth"]
        if az > 0:
            # slowly varying HF loss (crossfade against a 4 kHz lowpass)
            g = stream(ctx.seed, f"{self.key}:az")
            drift = 0.5 + 0.5 * U.control_noise(g, n, sr, 0.05, 0.35, ctrl_sr=100.0)
            w = np.clip(az * drift, 0.0, 1.0)[:, None].astype(np.float32)
            dull = U.lowpass(x, 4000.0, sr, order=2)
            x = (1.0 - w) * x + w * dull
            if ch >= 2:
                d = stream(ctx.seed, f"{self.key}:azdelay")
                delay = az * 25.0 * (0.5 + 0.5 * U.control_noise(d, n, sr, 0.03, 0.25, ctrl_sr=100.0))
                x[:, 1] = U.fractional_delay(x[:, 1], np.maximum(delay, 0.0))

        rate = self.v["rate"]
        if rate > 0:
            g = stream(ctx.seed, f"{self.key}:events")
            times = U.event_times(g, rate, dur, min_gap_s=0.3)
            if len(times):
                gain = np.ones(n, np.float32)
                hfmix = np.zeros(n, np.float32)
                for t0 in times:
                    length = int(np.exp(g.uniform(np.log(0.005), np.log(0.080))) * sr)
                    depth_db = g.uniform(6.0, self.v["depth_db"])
                    s = int(t0 * sr)
                    e = min(s + max(length, 8), n)
                    if e <= s:
                        continue
                    env = 0.5 - 0.5 * np.cos(np.linspace(0, 2 * np.pi, e - s))  # smooth dip
                    dip = (1.0 - env * (1.0 - U.db_to_lin(-depth_db))).astype(np.float32)
                    gain[s:e] = np.minimum(gain[s:e], dip)
                    hfmix[s:e] = np.maximum(hfmix[s:e], (env * g.uniform(0.3, 1.0)).astype(np.float32))
                dull = U.lowpass(x, 2500.0, sr, order=2)
                m = hfmix[:, None]
                x = ((1.0 - m) * x + m * dull) * gain[:, None]
        return x.astype(np.float32)
