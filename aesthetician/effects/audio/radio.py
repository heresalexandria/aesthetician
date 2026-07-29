"""Broadcast receivers: AM, FM, and analog TV intercarrier sound."""

from __future__ import annotations

import numpy as np

from ...engine.graph import Context, Effect, Param, register
from ...engine.rng import stream
from . import _util as U


@register
class AAmRadio(Effect):
    eid = "a_am_radio"
    label = "AM Radio"
    kind = "audio"
    desc = "AM broadcast receiver: narrow band, pumping program compression, atmospheric static, ionospheric fading, heterodyne whistle and tuning drift."
    PARAMS = (
        Param("hi_hz", "Bandwidth Top", "float", 4800.0, 2500.0, 7000.0, unit="Hz",
              desc="Receiver IF bandwidth top edge.", group="Bandwidth"),
        Param("pump", "Compression Pump", "float", 0.6, 0.0, 1.0,
              desc="How audible the fast AGC pumping is.", group="Dynamics", iscale=True),
        Param("static_db", "Static Level", "float", -48.0, -80.0, -25.0, unit="dB",
              desc="Atmospheric crackle and hiss bed.", group="Noise"),
        Param("fade", "Ionospheric Fade", "float", 0.0, 0.0, 1.0,
              desc="Slow 0.05–0.2 Hz level and treble fading (skywave).", group="Damage", iscale=True),
        Param("whistle_db", "Heterodyne", "float", -66.0, -80.0, -35.0, unit="dB",
              desc="Faint drifting 1–3 kHz carrier-beat whistle.", group="Noise"),
        Param("tune_drift", "Tuning Drift", "float", 0.0, 0.0, 10.0, unit="/min",
              desc="Brief detune dips per minute (muffled, distorted, quieter).", group="Damage", iscale=True),
        Param("adjacent_channel", "Adjacent Channel", "float", 0.0, 0.0, 1.0,
              desc="Adjacent-station interference: the 10 kHz carrier-spacing heterodyne whistle plus a ghostly band-limited other-program murmur that fades in and out.", group="Noise", iscale=True),
        Param("power_line", "Power Line", "float", 0.0, 0.0, 1.0,
              desc="Buzzy 120 Hz mains-harmonic bed the receiver picks up from house wiring.", group="Noise", iscale=True),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        sr = ctx.sr
        x = U.highpass(audio, 150.0, sr, order=2)
        x = U.lowpass(x, self.v["hi_hz"], sr, order=5)

        # fast AGC program compression (the AM 'pump')
        pump = self.v["pump"]
        if pump > 0:
            env = U.envelope(x, sr, attack_ms=4.0, release_ms=220.0 - 120.0 * pump, mode="rms")
            ref = np.percentile(env, 90) + 1e-9
            lev = np.maximum(env / ref, 1e-4)
            ratio = 5.0
            gain = lev ** -(1.0 - 1.0 / ratio)  # toward constant loudness
            gain = np.clip(gain, U.db_to_lin(-18.0), U.db_to_lin(12.0 * pump))
            gain = U.smooth_gain(gain, sr, attack_ms=4.0, release_ms=180.0)
            depth = 0.35 + 0.65 * pump
            g_eff = gain ** depth
            x = (x * g_eff[:, None]).astype(np.float32)
            x = U.match_rms(x, audio, max_db=9.0)

        fadeamt = self.v["fade"]
        if fadeamt > 0:
            g = stream(ctx.seed, f"{self.key}:fade")
            f = U.control_noise(g, n, sr, 0.05, 0.2, ctrl_sr=50.0)
            w = np.clip(0.5 + 0.5 * f, 0.0, 1.0) * fadeamt  # 0 = clear, 1 = deep fade
            lvl = U.db_to_lin(-14.0) ** w  # up to −14 dB dips
            dull = U.lowpass(x, 1800.0, sr, order=2)
            m = (w * 0.9)[:, None].astype(np.float32)
            x = ((1.0 - m) * x + m * dull) * lvl[:, None].astype(np.float32)

        drift_rate = self.v["tune_drift"]
        if drift_rate > 0:
            g = stream(ctx.seed, f"{self.key}:drift")
            times = U.event_times(g, drift_rate, n / sr, min_gap_s=2.0)
            if len(times):
                w = np.zeros(n, np.float32)
                for t0 in times:
                    L = int(g.uniform(0.4, 1.2) * sr)
                    s = int(t0 * sr)
                    e = min(s + L, n)
                    if e > s:
                        env = 0.5 - 0.5 * np.cos(np.linspace(0, 2 * np.pi, e - s))
                        w[s:e] = np.maximum(w[s:e], (env * g.uniform(0.6, 1.0)).astype(np.float32))
                mistuned = U.lowpass(np.tanh(3.0 * x) / 3.0, 1200.0, sr, order=2) * U.db_to_lin(-4.0)
                m = w[:, None]
                x = (1.0 - m) * x + m * mistuned * 3.0  # undo tanh /3 level drop

        bed = np.zeros((n, ch), np.float32)
        st_lvl = U.db_to_lin(self.v["static_db"])
        if st_lvl > 1e-6:
            g = stream(ctx.seed, f"{self.key}:static")
            k = int(g.poisson(60.0 * n / sr))
            imp = np.zeros(n, np.float32)
            if k > 0:
                idx = g.integers(0, n, k)
                amp = (g.random(k) ** 2.5) * np.where(g.random(k) < 0.5, -1, 1)
                np.add.at(imp, idx, amp.astype(np.float32))
            crk = U.bandpass(imp[:, None], 1000.0, 6000.0, sr, order=2)[:, 0]
            hiss = g.standard_normal(n).astype(np.float32)
            hiss = U.bandpass(hiss[:, None], 300.0, self.v["hi_hz"], sr, order=2)[:, 0] * 0.25
            static = crk * 2.0 + hiss
            static *= st_lvl / (U.rms(static) + 1e-12)
            bed += static[:, None]

        wh_lvl = U.db_to_lin(self.v["whistle_db"])
        if wh_lvl > 1e-6:
            g = stream(ctx.seed, f"{self.key}:whistle")
            f0 = g.uniform(1000.0, 3000.0)
            drift = 1.0 + 0.12 * U.control_noise(g, n, sr, 0.02, 0.15, ctrl_sr=50.0)
            phase = 2 * np.pi * np.cumsum(f0 * drift) / sr
            bed += (wh_lvl * np.sqrt(2.0) * np.sin(phase)).astype(np.float32)[:, None]

        adj = self.v["adjacent_channel"]
        if adj > 0.001:
            g = stream(ctx.seed, f"{self.key}:adj")
            # 10 kHz channel-spacing het: thin, slightly unstable, near the edge
            f10 = min(10000.0, sr * 0.45)
            wob = 1.0 + 0.0004 * U.control_noise(g, n, sr, 0.05, 0.3, ctrl_sr=50.0)
            het = np.sin(2 * np.pi * np.cumsum(f10 * wob) / sr).astype(np.float32)
            het *= U.db_to_lin(-52.0 + 10.0 * adj) * np.sqrt(2.0)
            # the other program: speech-shaped murmur under its own skywave fade
            mur = U.speech_murmur(g, n, sr)
            mur = U.bandpass(mur[:, None], 250.0, 2800.0, sr, order=2)[:, 0]
            f2 = 0.5 + 0.5 * U.control_noise(g, n, sr, 0.05, 0.22, ctrl_sr=50.0)
            mur *= np.clip(f2, 0.0, 1.0).astype(np.float32) ** 1.5
            mur *= U.db_to_lin(-47.0 + 12.0 * adj) / (U.rms(mur) + 1e-12)
            bed += (het + mur)[:, None]

        pl = self.v["power_line"]
        if pl > 0.001:
            g = stream(ctx.seed, f"{self.key}:pline")
            wand = 1.0 + 0.0008 * U.control_noise(g, n, sr, 0.02, 0.1, ctrl_sr=50.0)
            phb = 2 * np.pi * np.cumsum(120.0 * wand) / sr
            buzz = np.zeros(n, np.float64)
            for k in range(1, 14):  # gritty rectified-supply stack up to ~1.6 kHz
                a = 1.0 / (k ** 1.15)
                buzz += a * np.sin(k * phb + g.uniform(0, 2 * np.pi) * (0 if k == 1 else 1))
            b = U.highpass(buzz.astype(np.float32)[:, None], 70.0, sr, order=1)[:, 0]
            b *= (1.0 + 0.12 * U.control_noise(g, n, sr, 0.2, 1.2, ctrl_sr=100.0)).astype(np.float32)
            b *= U.db_to_lin(-52.0 + 14.0 * pl) / (U.rms(b) + 1e-12)
            bed += b[:, None]

        return U.peak_guard(x + bed)


@register
class AFmRadio(Effect):
    eid = "a_fm_radio"
    label = "FM Radio"
    kind = "audio"
    desc = "FM receiver: 15 kHz cap, high-tilted hiss that breathes up in quiet parts, broadcast compression and multipath flutter events."
    PARAMS = (
        Param("hiss_db", "Hiss Floor", "float", -58.0, -80.0, -35.0, unit="dB",
              desc="FM detector hiss (rises when the program is quiet).", group="Noise"),
        Param("comp", "Broadcast Comp", "float", 0.5, 0.0, 1.0,
              desc="Gentle station-processor compression amount.", group="Dynamics"),
        Param("multipath", "Multipath", "float", 0.0, 0.0, 12.0, unit="/min",
              desc="Picket-fence flutter events per minute (driving under a bridge).", group="Damage", iscale=True),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        sr = ctx.sr
        x = U.lowpass(audio, 15000.0, sr, order=6)
        x = U.highpass(x, 30.0, sr, order=1)

        comp = self.v["comp"]
        if comp > 0:
            env = U.envelope(x, sr, attack_ms=8.0, release_ms=300.0, mode="rms")
            ref = np.percentile(env, 90) + 1e-9
            lev = np.maximum(env / ref, 1e-4)
            gain = lev ** -(1.0 - 1.0 / 3.0)
            gain = np.clip(gain, U.db_to_lin(-12.0), U.db_to_lin(6.0))
            gain = U.smooth_gain(gain, sr, 8.0, 300.0) ** (0.3 + 0.7 * comp)
            x = U.match_rms((x * gain[:, None]).astype(np.float32), audio, max_db=6.0)

        mp = self.v["multipath"]
        if mp > 0:
            g = stream(ctx.seed, f"{self.key}:mp")
            times = U.event_times(g, mp, n / sr, min_gap_s=1.0)
            for t0 in times:
                L = int(g.uniform(0.1, 0.4) * sr)
                s = int(t0 * sr)
                e = min(s + L, n)
                if e - s < 64:
                    continue
                seg = x[s:e]
                m = e - s
                env = (0.5 - 0.5 * np.cos(np.linspace(0, 2 * np.pi, m))).astype(np.float32)
                flut_hz = g.uniform(8.0, 25.0)
                tau = (0.001 + 0.0009 * np.sin(2 * np.pi * flut_hz * np.arange(m) / sr
                                               + g.uniform(0, 2 * np.pi))) * sr
                mixd = np.empty_like(seg)
                for c in range(ch):
                    mixd[:, c] = U.fractional_delay(seg[:, c], tau)
                d = 0.9 * env[:, None]
                dip = (1.0 - 0.5 * env)[:, None]
                x[s:e] = ((1.0 - 0.5 * d) * seg - 0.5 * d * mixd) * dip  # comb + level dip

        hiss_lvl = U.db_to_lin(self.v["hiss_db"])
        if hiss_lvl > 1e-6:
            env = U.envelope(x, sr, 20.0, 400.0, mode="rms")
            ref = np.percentile(env, 90) + 1e-9
            quiet = np.clip(1.0 - env / ref, 0.0, 1.0)
            cols = [stream(ctx.seed, f"{self.key}:hiss{c}").standard_normal(n).astype(np.float32)
                    for c in range(ch)]
            hiss = np.stack(cols, axis=1)
            hiss = U.tilt(hiss, sr, 9.0, pivot_hz=3000.0)  # triangular-ish FM noise
            hiss = U.lowpass(hiss, 15000.0, sr, order=3)
            hiss *= hiss_lvl / (U.rms(hiss) + 1e-12)
            hiss *= (1.0 + 1.5 * quiet)[:, None]
            x = x + hiss
        return U.peak_guard(x)


@register
class ATvSound(Effect):
    eid = "a_tv_sound"
    label = "TV Intercarrier"
    kind = "audio"
    desc = "Analog TV sound: bandwidth cap, harsh video buzz at mains-related harmonics, soft hum, mild compression. Chain before a speaker sim."
    PARAMS = (
        Param("hz", "Mains", "enum", "60", choices=("60", "50"),
              desc="Mains frequency (NTSC 60 / PAL 50).", group="Noise"),
        Param("buzz_db", "Video Buzz", "float", -52.0, -80.0, -30.0, unit="dB",
              desc="Sawtooth-like buzz with strong odd harmonics (sync buzz).", group="Noise"),
        Param("hum_db", "Hum", "float", -58.0, -80.0, -35.0, unit="dB",
              desc="Softer sine hum under the buzz.", group="Noise"),
        Param("comp", "Compression", "float", 0.4, 0.0, 1.0,
              desc="Mild intercarrier limiter squash.", group="Dynamics"),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        sr = ctx.sr
        x = U.highpass(audio, 50.0, sr, order=2)
        x = U.lowpass(x, 10000.0, sr, order=4)
        comp = self.v["comp"]
        if comp > 0:
            env = U.envelope(x, sr, 6.0, 250.0, mode="rms")
            ref = np.percentile(env, 90) + 1e-9
            gain = np.clip(np.maximum(env / ref, 1e-4) ** -(1.0 - 1.0 / 2.5),
                           U.db_to_lin(-9.0), U.db_to_lin(4.0))
            gain = U.smooth_gain(gain, sr, 6.0, 250.0) ** comp
            x = U.match_rms((x * gain[:, None]).astype(np.float32), audio, max_db=6.0)

        f0 = float(self.v["hz"])
        g = stream(ctx.seed, f"{self.key}:buzz")
        t = np.arange(n) / sr
        wander = 1.0 + 0.0015 * U.control_noise(g, n, sr, 0.03, 0.2, ctrl_sr=50.0)
        phase = 2 * np.pi * np.cumsum(f0 * wander) / sr
        buzz_lvl = U.db_to_lin(self.v["buzz_db"])
        if buzz_lvl > 1e-6:
            buzz = np.zeros(n, np.float64)
            for k in range(1, 26):
                a = (1.0 / k) * (1.0 if k % 2 else 0.35)  # sawtooth-ish, odd-forward
                buzz += a * np.sin(k * phase)
            buzz = U.highpass(buzz.astype(np.float32)[:, None], 40.0, sr, 1)[:, 0]
            buzz *= buzz_lvl / (U.rms(buzz) + 1e-12)
            x = x + buzz[:, None]
        hum_lvl = U.db_to_lin(self.v["hum_db"])
        if hum_lvl > 1e-6:
            hum = (np.sin(phase) + 0.4 * np.sin(2 * phase)).astype(np.float32)
            hum *= hum_lvl / (U.rms(hum) + 1e-12)
            x = x + hum[:, None]
        return U.peak_guard(x)
