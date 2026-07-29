"""Telephony and public-address: era telephones, PA systems, bullhorns."""

from __future__ import annotations

import numpy as np
from scipy import signal as sps

from ...engine.graph import Context, Effect, Param, register
from ...engine.rng import stream
from . import _util as U


@register
class ATelephone(Effect):
    eid = "a_telephone"
    label = "Telephone"
    kind = "audio"
    desc = "Era telephone line and handset: band limit, real 8-bit mu-law companding, carbon-mic grit, line noise, and switch clicks. Pair cell_2003 with a_codec_speech."
    _ERAS = ("candlestick_1915", "rotary_1955", "touchtone_1985",
             "cordless_1992", "cell_2003", "speakerphone_1995")
    PARAMS = (
        Param("era", "Era", "enum", "rotary_1955", choices=_ERAS,
              desc="Telephone technology era preset.", group="Bandwidth"),
        Param("line_noise_db", "Line Noise", "float", -54.0, -80.0, -30.0, unit="dB",
              desc="Hum + hiss of the line.", group="Noise"),
        Param("sidetone_click", "Switch Clicks", "bool", False,
              desc="Tiny connect/disconnect clicks at start and end.", group="Damage"),
        Param("exchange_noise", "Exchange Noise", "float", 0.0, 0.0, 1.0,
              desc="Central-office bed: distant switching clicks and a faint crosstalk murmur of other calls bleeding onto the line.", group="Noise", iscale=True),
    )

    def _mulaw_8k(self, x: np.ndarray, sr: int) -> np.ndarray:
        """Downsample to 8 kHz, 8-bit mu-law companding round-trip, back up."""
        y = sps.resample_poly(x, 8000, sr, axis=0).astype(np.float32)
        peak = float(np.max(np.abs(y))) + 1e-9
        y = U.mulaw_roundtrip(y / peak) * peak
        return sps.resample_poly(y, sr, 8000, axis=0).astype(np.float32)

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        sr = ctx.sr
        era = self.v["era"]
        x = audio.mean(axis=1, keepdims=True) * np.ones((1, ch), np.float32)  # phones are mono

        if era == "candlestick_1915":
            x = U.highpass(x, 300.0, sr, order=3)
            x = U.lowpass(x, 2500.0, sr, order=4)
            x = U.apply_sos(x, U.peaking(sr, 1000.0, 7.0, q=1.4))  # horn receiver honk
            # carbon-button grit: strong odd-harmonic distortion...
            y = np.tanh(4.0 * x) / 4.0
            y = y + 0.15 * y * y  # slight asymmetry (button rectification)
            y = y - float(np.mean(y))  # remove rectification DC
            x = U.match_rms(y, x, max_db=9.0)
            # ...plus signal-envelope-modulated carbon frying noise
            env = U.envelope(x, sr, 5.0, 60.0, mode="rms")
            g = stream(ctx.seed, f"{self.key}:carbon")
            fry = g.standard_normal(n).astype(np.float32)
            fry = U.bandpass(fry[:, None], 400.0, 2500.0, sr, order=2)[:, 0]
            fry *= env / (np.percentile(env, 95) + 1e-9)
            fry *= U.db_to_lin(-26.0) / (U.rms(fry) + 1e-12) * 0.5
            x = x + fry[:, None]
            x = U.highpass(U.lowpass(x, 2500.0, sr, 3), 300.0, sr, 2)
        elif era == "cell_2003":
            x = U.highpass(x, 200.0, sr, order=3)
            x = U.lowpass(x, 3400.0, sr, order=5)
            # GSM-ish softness placeholder; real artifacts come from a_codec_speech
            x = self._mulaw_8k(x, sr)
        else:
            x = U.highpass(x, 300.0, sr, order=4)
            x = U.lowpass(x, 3400.0, sr, order=5)
            x = self._mulaw_8k(x, sr)
            if era == "rotary_1955":
                x = U.apply_sos(x, U.peaking(sr, 1700.0, 3.5, q=1.2))  # handset resonance
                x = U.apply_sos(x, U.peaking(sr, 700.0, 2.0, q=1.0))
                y = np.tanh(1.8 * x) / 1.8
                x = U.match_rms(y, x, max_db=6.0)
                x = U.lowpass(x, 3600.0, sr, order=4)  # earpiece can't emit the harmonics
            elif era == "cordless_1992":
                g = stream(ctx.seed, f"{self.key}:fmhiss")
                hiss = g.standard_normal((n, ch)).astype(np.float32)
                hiss = U.tilt(hiss, sr, 8.0, pivot_hz=2000.0)
                hiss = U.bandpass(hiss, 300.0, 3400.0, sr, 2)
                hiss *= U.db_to_lin(-46.0) / (U.rms(hiss) + 1e-12)
                x = x + hiss
                times = U.event_times(g, 3.0, n / sr, min_gap_s=1.5)
                for t0 in times:
                    L = int(g.uniform(0.03, 0.15) * sr)
                    s = int(t0 * sr)
                    e = min(s + L, n)
                    if e <= s:
                        continue
                    burst = g.standard_normal(e - s).astype(np.float32)
                    burst = U.bandpass(burst[:, None], 500.0, 3400.0, sr, 2)[:, 0]
                    env = np.sin(np.linspace(0, np.pi, e - s)) ** 0.5
                    x[s:e] += (burst * env * U.db_to_lin(-22.0) / (U.rms(burst) + 1e-9) * 0.3)[:, None]
            elif era == "speakerphone_1995":
                # hollow comb (mic-to-case reflection) + small-room tail
                dcomb = int(sr * 0.0045)
                x = x - 0.55 * np.vstack([np.zeros((dcomb, ch), np.float32), x[:-dcomb]])
                wet = np.stack(
                    [U.schroeder(x[:, c], sr, (23.0, 31.3, 35.9), (0.55, 0.5, 0.45),
                                 ap_ms=(5.0, 1.7), damp=0.6) for c in range(ch)], axis=1)
                x = (0.8 * x + 0.35 * wet).astype(np.float32)
                x = U.highpass(U.lowpass(x, 3400.0, sr, 4), 300.0, sr, 3)
                x = U.match_rms(x, audio, max_db=6.0)

        lvl = U.db_to_lin(self.v["line_noise_db"])
        if lvl > 1e-6:
            g = stream(ctx.seed, f"{self.key}:line")
            t = np.arange(n) / sr
            hum = np.sin(2 * np.pi * 60.0 * t) + 0.5 * np.sin(2 * np.pi * 180.0 * t + 1.0)
            hiss = g.standard_normal(n).astype(np.float32)
            hiss = U.bandpass(hiss[:, None], 300.0, 3400.0, sr, 2)[:, 0]
            noise = 0.4 * hum.astype(np.float32) + hiss / (U.rms(hiss) + 1e-12) * 0.6
            noise *= lvl / (U.rms(noise) + 1e-12)
            x = x + noise[:, None]

        ex = self.v["exchange_noise"]
        if ex > 0.001:
            g = stream(ctx.seed, f"{self.key}:exchange")
            bed = np.zeros(n, np.float32)
            # crosstalk murmur of other conversations, band-limited to the line
            mur = U.speech_murmur(g, n, sr)
            mur = U.bandpass(mur[:, None], 300.0, 3000.0, sr, order=2)[:, 0]
            mur *= U.db_to_lin(-54.0 + 12.0 * ex) / (U.rms(mur) + 1e-12)
            bed += mur
            # distant relay/switch clicks somewhere in the office
            for t0 in U.event_times(g, 6.0 + 10.0 * ex, n / sr, min_gap_s=0.5):
                L = max(int(0.004 * sr), 16)
                ck = g.standard_normal(L).astype(np.float32) * np.exp(-np.arange(L) / (L / 5.0))
                ck = U.bandpass(ck[:, None], 600.0, 2800.0, sr, order=2)[:, 0]
                amp = U.db_to_lin(-36.0 + 8.0 * ex) * g.uniform(0.4, 1.0)
                U.add_at(bed, (ck * amp / (np.max(np.abs(ck)) + 1e-9)).astype(np.float32),
                         int(t0 * sr))
            x = x + bed[:, None]

        if self.v["sidetone_click"]:
            g = stream(ctx.seed, f"{self.key}:click")
            for pos, amp in ((int(0.01 * sr), 0.25), (n - int(0.02 * sr), 0.2)):
                L = int(0.004 * sr)
                click = g.standard_normal(L).astype(np.float32) * np.exp(-np.arange(L) / (L / 6))
                click = U.bandpass(click[:, None], 400.0, 3000.0, sr, 2)[:, 0]
                U.add_at(x, click * amp / (np.max(np.abs(click)) + 1e-9), pos)
        return U.peak_guard(x)


@register
class APaBullhorn(Effect):
    eid = "a_pa_bullhorn"
    label = "PA / Bullhorn"
    kind = "audio"
    desc = "Horn-loaded public address: narrow band, horn resonances, clipping, hall slap echo and optional feedback squeal."
    # device: (lo, hi, res list [(hz, dB, q)], clip 'hard'|'soft', slap_ms, slap_gain_db, repeats)
    _DEVICES = {
        "pa_hall": (200.0, 6000.0, [(1400.0, 6.0, 1.4)], "soft", 180.0, -10.0, 2),
        "pa_stadium": (250.0, 5000.0, [(1800.0, 7.0, 1.6)], "soft", 340.0, -8.0, 3),
        "bullhorn": (450.0, 3800.0, [(2200.0, 9.0, 1.8), (1200.0, 5.0, 1.4)], "hard", 0.0, -12.0, 1),
        "drive_thru": (350.0, 3000.0, [(1600.0, 8.0, 1.6)], "hard", 0.0, -12.0, 1),
        "intercom": (300.0, 4000.0, [(1200.0, 6.0, 1.3)], "soft", 60.0, -14.0, 1),
    }
    PARAMS = (
        Param("device", "Device", "enum", "bullhorn", choices=tuple(_DEVICES),
              desc="Horn/PA type; sets band, resonances and default slap.", group="Bandwidth"),
        Param("drive", "Drive", "float", 2.5, 1.0, 10.0,
              desc="Amplifier overdrive into the horn.", group="Dynamics"),
        Param("slap_ms", "Slap Delay", "float", -1.0, -1.0, 800.0, unit="ms",
              desc="Echo delay; -1 uses the device default.", group="Damage"),
        Param("slap_gain_db", "Slap Level", "float", -10.0, -30.0, 0.0, unit="dB",
              desc="Level of the first echo repeat.", group="Damage"),
        Param("slap_repeats", "Slap Repeats", "int", 0, 0, 3,
              desc="Echo repeats; 0 uses the device default.", group="Damage"),
        Param("feedback_squeal", "Squeal Rate", "float", 0.0, 0.0, 6.0, unit="/min",
              desc="Brief 1.5–3 kHz feedback swells per minute.", group="Damage", iscale=True),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        sr = ctx.sr
        lo, hi, res, clip, d_slap, d_gain, d_reps = self._DEVICES[self.v["device"]]
        x = audio.mean(axis=1, keepdims=True) * np.ones((1, ch), np.float32)
        x = U.highpass(x, lo, sr, order=3)
        x = U.lowpass(x, hi, sr, order=4)
        rows = [U.peaking(sr, f, g_, q) for f, g_, q in res]
        x = U.apply_sos(x, U.sos_cascade(*rows))
        d = self.v["drive"]
        peak = float(np.max(np.abs(x))) + 1e-9
        xn = x / peak
        if clip == "hard":
            y = np.clip(d * xn, -1.0, 1.0) / d
            y = U.lowpass(y, hi, sr, 2)  # tame clip edge
        else:
            y = np.tanh(d * xn) / d
        x = U.match_rms((y * peak).astype(np.float32), x, max_db=9.0)

        slap_ms = self.v["slap_ms"] if self.v["slap_ms"] >= 0 else d_slap
        reps = self.v["slap_repeats"] or d_reps
        if slap_ms > 5 and reps > 0:
            gain = U.db_to_lin(self.v["slap_gain_db"] if self.v["slap_ms"] >= 0 else d_gain)
            D = int(slap_ms * sr / 1000.0)
            out = x.copy()
            tap = x
            for r in range(1, reps + 1):
                tap = U.lowpass(tap, 3500.0, sr, 1) * gain
                if r * D >= n:
                    break
                out[r * D :] += tap[: n - r * D]
            x = out

        rate = self.v["feedback_squeal"]
        if rate > 0:
            g = stream(ctx.seed, f"{self.key}:squeal")
            for t0 in U.event_times(g, rate, n / sr, min_gap_s=3.0):
                L = int(g.uniform(0.5, 1.4) * sr)
                s = int(t0 * sr)
                e = min(s + L, n)
                if e - s < sr // 10:
                    continue
                m = e - s
                f0 = g.uniform(1500.0, 3000.0)
                t = np.arange(m) / sr
                swell = (np.sin(np.linspace(0, np.pi, m)) ** 2).astype(np.float32)
                sq = np.sin(2 * np.pi * f0 * (1.0 + 0.01 * t) * t).astype(np.float32)
                x[s:e] += (sq * swell * U.db_to_lin(-16.0))[:, None]
        return U.peak_guard(x)
