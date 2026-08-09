"""Spaces: small algorithmic room reverb (with era chamber/plate/spring modes)
and slap echo."""

from __future__ import annotations

import numpy as np

from ...engine.graph import Context, Effect, Param, register
from ...engine.rng import stream
from . import _util as U


@register
class ARoom(Effect):
    eid = "a_room"
    label = "Small Room"
    kind = "audio"
    desc = "Algorithmic space: Schroeder small room (default), dense bright 1960s studio plate, springy amp-tank reverb, or a dark echo chamber."
    # classic Schroeder tunings (ms); per-channel prime-ish offsets for width
    _COMBS_L = (29.7, 37.1, 41.1, 43.7)
    _COMBS_R = (30.1, 36.7, 41.9, 44.3)
    # plate: many short combs = fast dense diffusion; kept bright
    _PLATE_L = (11.3, 13.9, 16.7, 19.3, 23.1, 27.7)
    _PLATE_R = (11.9, 14.3, 16.3, 19.9, 22.7, 28.1)
    # chamber: long sparse combs, heavy damping applied on top
    _CHAMBER_L = (47.9, 53.3, 61.1, 67.9)
    _CHAMBER_R = (48.7, 52.7, 61.9, 68.3)
    PARAMS = (
        # The original range was scaled to the Schroeder small room this started
        # as. The chamber and plate modes arrived later wanting numbers well past
        # it, and presets were already written that way - a cathedral asking for
        # size 2.2 and a 4.2 s decay was quietly getting 1.6 and 1.5. The dial
        # now reaches where those presets were pointing, and further: down to a
        # broom cupboard and out to a hall.
        Param("size", "Room Size", "float", 1.0, 0.2, 4.0,
              desc="Scales the reflection delays: under 1 is a cupboard, past 2 is a hall.",
              group="Damage"),
        Param("decay_s", "Decay", "float", 0.35, 0.05, 8.0, unit="s",
              desc="RT60-style decay time. The chamber mode runs 1.6x this.", group="Damage"),
        Param("damp", "Damping", "float", 0.55, 0.0, 0.95,
              desc="High-frequency absorption in the tail.", group="Damage"),
        Param("predelay_ms", "Predelay", "float", 8.0, 0.0, 60.0, unit="ms",
              desc="Gap before the reverb starts.", group="Damage"),
        Param("mix", "Mix", "float", 0.25, 0.0, 1.0,
              desc="Wet amount.", group="Damage", iscale=True),
        Param("mode", "Mode", "enum", "room", choices=("room", "plate1960", "spring_amp", "chamber"),
              desc="Reverb character: room = original Schroeder; plate1960 = dense fast bright diffusion; spring_amp = boingy modulated tank with a 2–3 kHz resonance; chamber = darker and longer.", group="Damage"),
    )

    def _spring_wet(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        """Spring tank: mono drive into modulated feedback combs, band-limited
        with a resonant 2–3 kHz 'boing' peak and wobbling short delays."""
        n, ch = audio.shape
        sr = ctx.sr
        size = self.v["size"]
        decay = self.v["decay_s"]
        mono = audio.mean(axis=1)
        comb_ms = tuple(m * size for m in (33.1, 41.3, 51.9))
        fb = tuple(10.0 ** (-3.0 * (m / 1000.0) / max(decay, 0.05)) for m in comb_ms)
        wet = U.schroeder(mono, sr, comb_ms, fb, ap_ms=(3.1, 1.3),
                          ap_g=0.6, damp=min(0.4, self.v["damp"]))
        wet = U.bandpass(wet[:, None], 250.0, 4500.0, sr, order=2)[:, 0]
        wet = U.apply_sos(wet[:, None], U.sos_cascade(
            U.peaking(sr, 2500.0, 8.0, q=2.0), U.peaking(sr, 600.0, 3.0, q=1.1)))[:, 0]
        # the characteristic flutter: short delays wobbling a few ms
        g = stream(ctx.seed, f"{self.key}:spring")
        t = np.arange(n) / sr
        cols = []
        for c in range(ch):
            ph = g.uniform(0, 2 * np.pi)
            rate = g.uniform(3.6, 5.8)
            dmod = (0.0009 + 0.0006 * np.sin(2 * np.pi * rate * t + ph)
                    + 0.0004 * U.control_noise(g, n, sr, 1.0, 6.0, ctrl_sr=200.0)) * sr
            cols.append(U.fractional_delay(wet, np.maximum(dmod, 0.0)))
        return np.stack(cols, axis=1)

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        mix = self.v["mix"]
        if mix <= 0.001:
            return audio
        n, ch = audio.shape
        sr = ctx.sr
        size = self.v["size"]
        decay = self.v["decay_s"]
        mode = self.v["mode"]
        if mode == "spring_amp":
            wet = self._spring_wet(audio, ctx)
        else:
            if mode == "plate1960":
                tun_l, tun_r = self._PLATE_L, self._PLATE_R
                damp = 0.35 * self.v["damp"]  # plates stay bright to the end
                dec = decay * 0.9
                ap = (7.9, 3.1, 1.3)
            elif mode == "chamber":
                tun_l, tun_r = self._CHAMBER_L, self._CHAMBER_R
                damp = min(0.5 + 0.5 * self.v["damp"], 0.95)
                dec = decay * 1.6
                ap = (6.1, 2.3)
            else:  # room - original path
                tun_l, tun_r = self._COMBS_L, self._COMBS_R
                damp = self.v["damp"]
                dec = decay
                ap = (5.0, 1.7)
            wet_cols = []
            for c in range(ch):
                combs = tun_r if (c % 2) else tun_l
                comb_ms = tuple(m * size for m in combs)
                fb = tuple(10.0 ** (-3.0 * (m / 1000.0) / dec) for m in comb_ms)
                wet_cols.append(U.schroeder(audio[:, c], sr, comb_ms, fb,
                                            ap_ms=ap, ap_g=0.7, damp=damp))
            wet = np.stack(wet_cols, axis=1)
            if mode == "chamber":
                wet = U.lowpass(wet, 5000.0, sr, order=2)  # dark distant walls
            elif mode == "plate1960":
                wet = U.tilt(wet, sr, 1.5, pivot_hz=2500.0)  # airy sheen
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
    desc = "Single or multi-tap slapback echo with progressive damping - gym PA and hallway flavor."
    PARAMS = (
        Param("delay_ms", "Delay", "float", 110.0, 20.0, 600.0, unit="ms",
              desc="Slap delay time.", group="Damage"),
        Param("gain_db", "Echo Level", "float", -8.0, -30.0, 0.0, unit="dB",
              desc="Level of the first repeat.", group="Damage"),
        Param("repeats", "Repeats", "int", 1, 1, 12,
              desc="Number of echoes. Repeats past the end of the clip stop early.",
              group="Damage"),
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
