"""Long-haul radio communications: shortwave listening and CB radio."""

from __future__ import annotations

import numpy as np

from ...engine.graph import Context, Effect, Param, register
from ...engine.rng import stream
from . import _util as U


@register
class AShortwave(Effect):
    eid = "a_shortwave"
    label = "Shortwave"
    kind = "audio"
    desc = "Distant shortwave broadcast: narrow band, deep fast multipath fading, drifting heterodyne carriers, RTTY utility interference and atmospheric crashes."
    PARAMS = (
        Param("hi_hz", "Bandwidth Top", "float", 3200.0, 2000.0, 5000.0, unit="Hz",
              desc="Receiver IF top edge (shortwave is narrower than AM broadcast).", group="Bandwidth"),
        Param("fade", "Multipath Fade", "float", 0.7, 0.0, 1.0,
              desc="Deep selective fading, faster than AM skywave - the signal breathes away and back in seconds.", group="Damage", iscale=True),
        Param("het_db", "Heterodynes", "float", -46.0, -80.0, -28.0, unit="dB",
              desc="One to three drifting carrier whistles from stations nearby on the dial.", group="Noise"),
        Param("utility_qrm", "RTTY Interference", "float", 0.0, 0.0, 1.0,
              desc="FSK/RTTY utility-station warble: two tones 85 Hz apart keying at 45 baud.", group="Noise", iscale=True),
        Param("sferics", "Atmospherics", "float", 0.5, 0.0, 1.0,
              desc="Lightning static: band-limited impulse crashes and whooshes from distant storms.", group="Noise", iscale=True),
        Param("static_db", "Static Bed", "float", -44.0, -80.0, -25.0, unit="dB",
              desc="Continuous atmospheric hiss-crackle floor.", group="Noise"),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        sr = ctx.sr
        dur = n / sr
        hi = self.v["hi_hz"]
        x = audio.mean(axis=1, keepdims=True) * np.ones((1, ch), np.float32)
        x = U.highpass(x, 120.0, sr, order=2)
        x = U.lowpass(x, hi, sr, order=5)

        # receiver AGC keeps the program pinned, exaggerating the fades
        env = U.envelope(x, sr, attack_ms=6.0, release_ms=350.0, mode="rms")
        ref = np.percentile(env, 90) + 1e-9
        gain = np.clip(np.maximum(env / ref, 1e-4) ** -(1.0 - 1.0 / 4.0),
                       U.db_to_lin(-12.0), U.db_to_lin(9.0))
        gain = U.smooth_gain(gain.astype(np.float32), sr, 6.0, 350.0)
        x = U.match_rms((x * gain[:, None]).astype(np.float32), audio, max_db=9.0)

        fade = self.v["fade"]
        if fade > 0:
            g = stream(ctx.seed, f"{self.key}:fade")
            f = U.control_noise(g, n, sr, 0.15, 0.9, ctrl_sr=100.0)  # faster than AM
            w = np.clip(0.5 + 0.5 * f, 0.0, 1.0) * fade
            lvl = U.db_to_lin(-26.0) ** w  # very deep dips
            dull = U.lowpass(x, 1300.0, sr, order=2)
            m = (w * 0.95)[:, None].astype(np.float32)
            x = ((1.0 - m) * x + m * dull) * lvl[:, None].astype(np.float32)

        bed = np.zeros((n, ch), np.float32)

        st_lvl = U.db_to_lin(self.v["static_db"])
        if st_lvl > 1e-6:
            g = stream(ctx.seed, f"{self.key}:static")
            k = int(g.poisson(90.0 * dur))
            imp = np.zeros(n, np.float32)
            if k > 0:
                idx = g.integers(0, n, k)
                amp = (g.random(k) ** 2.2) * np.where(g.random(k) < 0.5, -1, 1)
                np.add.at(imp, idx, amp.astype(np.float32))
            crk = U.bandpass(imp[:, None], 800.0, hi, sr, order=2)[:, 0]
            hiss = g.standard_normal(n).astype(np.float32)
            hiss = U.bandpass(hiss[:, None], 200.0, hi, sr, order=2)[:, 0] * 0.35
            static = crk * 2.0 + hiss
            static *= st_lvl / (U.rms(static) + 1e-12)
            bed += static[:, None]

        het_lvl = U.db_to_lin(self.v["het_db"])
        if het_lvl > 1e-6:
            g = stream(ctx.seed, f"{self.key}:het")
            n_car = int(g.integers(1, 4))  # 1–3 carriers
            hets = np.zeros(n, np.float32)
            for i in range(n_car):
                f0 = g.uniform(350.0, hi - 400.0)
                drift = f0 + g.uniform(-40.0, 40.0) * np.linspace(0, 1, n) \
                    + 25.0 * U.control_noise(g, n, sr, 0.02, 0.2, ctrl_sr=50.0)
                ph = 2 * np.pi * np.cumsum(np.clip(drift, 60.0, hi)) / sr
                am = 1.0 + 0.3 * U.control_noise(g, n, sr, 0.1, 0.5, ctrl_sr=50.0)
                hets += (np.sin(ph + g.uniform(0, 2 * np.pi)) * am).astype(np.float32) \
                    * g.uniform(0.4, 1.0)
            hets *= het_lvl * np.sqrt(2.0) / max(n_car, 1)
            bed += hets[:, None]

        qrm = self.v["utility_qrm"]
        if qrm > 0.001:
            g = stream(ctx.seed, f"{self.key}:rtty")
            baud = 45.45
            bit_len = sr / baud
            n_bits = int(np.ceil(n / bit_len)) + 1
            bits = g.integers(0, 2, n_bits)
            f_mark = g.uniform(900.0, 2200.0)
            f_space = f_mark + 85.0  # 85 Hz narrow FSK shift
            idx = np.minimum((np.arange(n) / bit_len).astype(np.int64), n_bits - 1)
            fi = np.where(bits[idx] > 0, f_space, f_mark).astype(np.float64)
            fi *= 1.0 + 0.0003 * U.control_noise(g, n, sr, 0.03, 0.2, ctrl_sr=50.0)
            ph = 2 * np.pi * np.cumsum(fi) / sr  # phase-continuous FSK
            rt = np.sin(ph + g.uniform(0, 2 * np.pi)).astype(np.float32)
            # idle gaps: utilities key on and off
            gate = np.clip(0.75 + 0.5 * U.control_noise(g, n, sr, 0.05, 0.2, ctrl_sr=50.0), 0.0, 1.0)
            rt *= gate.astype(np.float32) ** 0.5
            rt *= U.db_to_lin(-46.0 + 14.0 * qrm) * np.sqrt(2.0)
            bed += rt[:, None]

        sf = self.v["sferics"]
        if sf > 0:
            g = stream(ctx.seed, f"{self.key}:sferics")
            for t0 in U.event_times(g, 4.0 + 30.0 * sf, dur, min_gap_s=0.4):
                L = int(g.uniform(0.05, 0.3) * sr)
                s0 = int(t0 * sr)
                if s0 + 32 >= n:
                    continue
                L = min(L, n - s0)
                t = np.arange(L) / sr
                burst = g.standard_normal(L).astype(np.float32)
                # bright snap decaying into a darker whoosh tail
                snap = burst * np.exp(-t / g.uniform(0.004, 0.012))
                whoosh = burst * np.exp(-t / g.uniform(0.05, 0.15)) * 0.5
                b = U.bandpass(snap[:, None], 1200.0, hi, sr, order=2)[:, 0] \
                    + U.bandpass(whoosh[:, None], 250.0, 1800.0, sr, order=2)[:, 0]
                amp = sf * U.db_to_lin(-24.0) * g.uniform(0.3, 1.0) / (np.max(np.abs(b)) + 1e-9)
                U.add_at(bed, (b * amp).astype(np.float32), s0)

        return U.peak_guard(x + bed)


@register
class ACbRadio(Effect):
    eid = "a_cb_radio"
    label = "CB Radio"
    kind = "audio"
    desc = "1977 citizens-band rig: 300–3000 band, crushed and clipped modulation, squelch tails at the ends, heterodyne and other-station bleed."
    PARAMS = (
        Param("drive", "Drive", "float", 4.0, 1.0, 10.0,
              desc="Mic gain wound up - compression into clipping.", group="Dynamics"),
        Param("squelch_tails", "Squelch Tails", "bool", True,
              desc="The kshhh-chk of the squelch opening at the start and closing at the end.", group="Damage"),
        Param("bleed", "Station Bleed", "float", 0.3, 0.0, 1.0,
              desc="Another conversation bleeding over from the next channel (unintelligible murmur).", group="Noise", iscale=True),
        Param("het_db", "Heterodyne", "float", -52.0, -80.0, -30.0, unit="dB",
              desc="Carrier beat whistle from a nearby transmitter.", group="Noise"),
        Param("hiss_db", "Noise Floor", "float", -42.0, -70.0, -25.0, unit="dB",
              desc="Receiver hiss (quiets when the carrier is strong).", group="Noise"),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        sr = ctx.sr
        x = audio.mean(axis=1, keepdims=True) * np.ones((1, ch), np.float32)
        x = U.highpass(x, 300.0, sr, order=3)
        x = U.lowpass(x, 3000.0, sr, order=5)

        # speech processor: hard fast compression, then clipping
        env = U.envelope(x, sr, attack_ms=2.0, release_ms=120.0, mode="rms")
        ref = np.percentile(env, 90) + 1e-9
        gain = np.clip(np.maximum(env / ref, 1e-4) ** -(1.0 - 1.0 / 8.0),
                       U.db_to_lin(-10.0), U.db_to_lin(14.0))
        gain = U.smooth_gain(gain.astype(np.float32), sr, 2.0, 120.0)
        x = (x * gain[:, None]).astype(np.float32)
        d = self.v["drive"]
        peak = float(np.max(np.abs(x))) + 1e-9
        y = np.clip(np.tanh(1.5 * d * x / peak) * 1.15, -1.0, 1.0) * peak / d
        x = U.lowpass(y.astype(np.float32), 3000.0, sr, order=3)  # tame clip edges
        x = U.match_rms(x, audio, max_db=9.0)

        bed = np.zeros((n, ch), np.float32)
        prog_env = U.envelope(x, sr, 10.0, 200.0, mode="rms")
        quiet = np.clip(1.0 - prog_env / (np.percentile(prog_env, 90) + 1e-9), 0.0, 1.0)

        hiss_lvl = U.db_to_lin(self.v["hiss_db"])
        if hiss_lvl > 1e-6:
            g = stream(ctx.seed, f"{self.key}:hiss")
            h = g.standard_normal(n).astype(np.float32)
            h = U.bandpass(h[:, None], 300.0, 3000.0, sr, order=2)[:, 0]
            h *= hiss_lvl / (U.rms(h) + 1e-12)
            h *= (0.4 + 0.6 * quiet).astype(np.float32)  # carrier quieting
            bed += h[:, None]

        het_lvl = U.db_to_lin(self.v["het_db"])
        if het_lvl > 1e-6:
            g = stream(ctx.seed, f"{self.key}:het")
            f0 = g.uniform(800.0, 2200.0)
            drift = 1.0 + 0.05 * U.control_noise(g, n, sr, 0.05, 0.3, ctrl_sr=50.0)
            ph = 2 * np.pi * np.cumsum(f0 * drift) / sr
            bed += (het_lvl * np.sqrt(2.0) * np.sin(ph)).astype(np.float32)[:, None]

        bl = self.v["bleed"]
        if bl > 0.001:
            g = stream(ctx.seed, f"{self.key}:bleed")
            mur = U.speech_murmur(g, n, sr, syllable_hz=(3.0, 6.0))
            mur = U.bandpass(mur[:, None], 350.0, 2500.0, sr, order=2)[:, 0]
            mur *= U.db_to_lin(-50.0 + 14.0 * bl) / (U.rms(mur) + 1e-12)
            bed += mur[:, None]

        x = x + bed

        if self.v["squelch_tails"] and n > sr:
            g = stream(ctx.seed, f"{self.key}:squelch")

            def _burst(length: int, fade_out: bool) -> np.ndarray:
                b = g.standard_normal(length).astype(np.float32)
                b = U.bandpass(b[:, None], 400.0, 3400.0, sr, order=2)[:, 0]
                envl = np.linspace(1.0, 0.0, length) ** 1.5 if fade_out \
                    else np.linspace(0.0, 1.0, length) ** 0.7
                return (b * envl * U.db_to_lin(-16.0) / (U.rms(b) + 1e-12) * 0.25).astype(np.float32)

            def _chk(amp: float) -> np.ndarray:
                L = max(int(0.006 * sr), 32)
                k = g.standard_normal(L).astype(np.float32) * np.exp(-np.arange(L) / (L / 7.0))
                k = U.bandpass(k[:, None], 700.0, 3200.0, sr, order=2)[:, 0]
                return (k * amp / (np.max(np.abs(k)) + 1e-9)).astype(np.float32)

            open_len = int(0.13 * sr)
            x[:open_len] *= np.linspace(0.0, 1.0, open_len)[:, None].astype(np.float32) ** 0.5
            U.add_at(x, _burst(open_len, fade_out=True), 0)   # kshhh...
            U.add_at(x, _chk(0.30), open_len)                 # ...chk
            close_len = int(0.10 * sr)
            x[n - close_len:] *= np.linspace(1.0, 0.1, close_len)[:, None].astype(np.float32)
            U.add_at(x, _chk(0.26), n - close_len)
            U.add_at(x, _burst(close_len, fade_out=False), n - close_len + int(0.008 * sr))

        return U.peak_guard(x)
