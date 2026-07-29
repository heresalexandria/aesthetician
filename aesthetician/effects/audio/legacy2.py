"""Deeper period devices: wire recorder, transcription disc, 8-track cartridge,
microcassette memo recorder, and tube amplifier electronics."""

from __future__ import annotations

import numpy as np

from ...engine.graph import Context, Effect, Param, register
from ...engine.rng import stream
from . import _util as U


def _mono_fold(audio: np.ndarray) -> np.ndarray:
    """Collapse to mono, keeping the channel count."""
    return audio.mean(axis=1, keepdims=True) * np.ones((1, audio.shape[1]), np.float32)


def _knock(rng: np.random.Generator, sr: int, f_lo: float = 60.0, f_hi: float = 120.0,
           decay_s: float = 0.04, click: float = 0.4) -> np.ndarray:
    """Damped mechanical knock: low thud + broadband contact click."""
    L = int(sr * max(decay_s * 4.0, 0.05))
    t = np.arange(L) / sr
    f0 = rng.uniform(f_lo, f_hi)
    body = np.sin(2 * np.pi * f0 * t + rng.uniform(0, 2 * np.pi)) * np.exp(-t / decay_s)
    body += 0.5 * np.sin(2 * np.pi * 2.3 * f0 * t) * np.exp(-t / (decay_s * 0.4))
    snap = rng.standard_normal(L).astype(np.float64) * np.exp(-t / 0.004) * click
    k = U.bandpass((body + snap)[:, None].astype(np.float32), 35.0, 2500.0, sr, order=2)[:, 0]
    return (k / (np.max(np.abs(k)) + 1e-9)).astype(np.float32)


@register
class AWireRecorder(Effect):
    eid = "a_wire_recorder"
    label = "Wire Recorder"
    kind = "audio"
    desc = "1945 steel-wire recorder: violent flutter, 200–4500 band, watery HF instability, the wire 'twang' resonance near 2.8 kHz, rough hiss and heavy dropouts."
    PARAMS = (
        Param("flutter", "Flutter", "float", 0.7, 0.0, 1.0,
              desc="Transport instability of the spinning wire spool (wow + fast flutter).", group="Pitch", iscale=True),
        Param("watery", "Watery Highs", "float", 0.6, 0.0, 1.0,
              desc="Rapid micro-detune of the top band via a short modulated delay — the characteristic underwater sheen.", group="Pitch", iscale=True),
        Param("twang", "Wire Twang", "float", 0.5, 0.0, 1.0,
              desc="Resonance of the taut steel wire around 2.8 kHz.", group="Bandwidth", iscale=True),
        Param("dropout_rate", "Dropouts", "float", 25.0, 0.0, 150.0, unit="/min",
              desc="Kinks and bad wire spots per minute (deep, fast level holes).", group="Damage", iscale=True),
        Param("hiss_db", "Hiss Level", "float", -42.0, -70.0, -25.0, unit="dB",
              desc="Rough wire noise floor.", group="Noise"),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        sr = ctx.sr
        x = _mono_fold(audio)  # wire recorders are single-track

        fl = self.v["flutter"]
        if fl > 0 and n > 16:
            cents = 15.0 * fl * U.control_noise(
                stream(ctx.seed, f"{self.key}:wow"), n, sr, 0.5, 2.5, ctrl_sr=200.0)
            cents += 22.0 * fl * U.control_noise(
                stream(ctx.seed, f"{self.key}:flut"), n, sr, 7.0, 28.0, ctrl_sr=400.0)
            x = U.variable_speed(x, np.exp2(cents / 1200.0))

        x = U.highpass(x, 200.0, sr, order=3)
        x = U.lowpass(x, 4500.0, sr, order=5)

        tw = self.v["twang"]
        if tw > 0:
            x = U.apply_sos(x, U.sos_cascade(
                U.peaking(sr, 2800.0, 8.0 * tw, q=4.0),
                U.peaking(sr, 1400.0, 2.5 * tw, q=2.0)))

        wat = self.v["watery"]
        if wat > 0 and n > 64:
            g = stream(ctx.seed, f"{self.key}:water")
            low = U.lowpass(x, 1200.0, sr, order=2)
            hf = (x - low).astype(np.float32)
            t = np.arange(n) / sr
            rate = g.uniform(8.0, 13.0)
            dmod = (0.0005 + 0.00045 * np.sin(2 * np.pi * rate * t + g.uniform(0, 2 * np.pi))
                    + 0.00035 * U.control_noise(g, n, sr, 3.0, 16.0, ctrl_sr=400.0)) * sr
            wob = np.stack([U.fractional_delay(hf[:, c], np.maximum(dmod, 0.0))
                            for c in range(ch)], axis=1)
            x = (low + (1.0 - wat) * hf + wat * wob).astype(np.float32)

        # mild magnetic squash — wire saturates early
        y = np.tanh(2.2 * x) / 2.2
        x = U.match_rms(y, x, max_db=6.0)

        rate = self.v["dropout_rate"]
        if rate > 0:
            g = stream(ctx.seed, f"{self.key}:drop")
            gain = np.ones(n, np.float32)
            dull = np.zeros(n, np.float32)
            for t0 in U.event_times(g, rate, n / sr, min_gap_s=0.12):
                L = int(np.exp(g.uniform(np.log(0.003), np.log(0.050))) * sr)
                s = int(t0 * sr)
                e = min(s + max(L, 8), n)
                if e <= s:
                    continue
                env = 0.5 - 0.5 * np.cos(np.linspace(0, 2 * np.pi, e - s))
                depth = g.uniform(12.0, 35.0)
                gain[s:e] = np.minimum(gain[s:e],
                                       (1.0 - env * (1.0 - U.db_to_lin(-depth))).astype(np.float32))
                dull[s:e] = np.maximum(dull[s:e], (env * g.uniform(0.5, 1.0)).astype(np.float32))
            muf = U.lowpass(x, 1500.0, sr, order=2)
            m = dull[:, None]
            x = ((1.0 - m) * x + m * muf) * gain[:, None]

        lvl = U.db_to_lin(self.v["hiss_db"])
        if lvl > 1e-6:
            g = stream(ctx.seed, f"{self.key}:hiss")
            h = g.standard_normal(n).astype(np.float32)
            h = U.bandpass(h[:, None], 250.0, 5000.0, sr, order=2)[:, 0]
            h += 0.4 * np.abs(h) * U.control_noise(g, n, sr, 20.0, 120.0, ctrl_sr=1000.0)  # grainy
            h *= lvl / (U.rms(h) + 1e-12)
            x = x + h[:, None]
        return U.peak_guard(x)


@register
class ATranscriptionDisc(Effect):
    eid = "a_transcription_disc"
    label = "Transcription Disc"
    kind = "audio"
    desc = "1930s–40s 16-inch lacquer transcription at 33⅓: wider than a 78 (50–8000), once-per-revolution surface swish, occasional lacquer crackle, playback wear."
    _REV_HZ = 0.555  # 33⅓ rpm
    PARAMS = (
        Param("band", "Band Limit", "float", 1.0, 0.0, 1.0,
              desc="Morphs from a flat modern transfer (0) to the full 50–8000 Hz lacquer band (1).", group="Bandwidth"),
        Param("swish", "Surface Swish", "float", 0.6, 0.0, 1.0,
              desc="Once-per-revolution breathing surface noise as the needle rides the lacquer.", group="Noise", iscale=True),
        Param("crackle", "Lacquer Crackle", "float", 3.0, 0.0, 30.0, unit="/s",
              desc="Crazing crackle clusters per second (softer and duller than vinyl).", group="Noise", iscale=True),
        Param("wear", "Wear", "float", 0.3, 0.0, 1.0,
              desc="Plays raise noise, dull the top edge and add groove hiss.", group="Damage", iscale=True),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        sr = ctx.sr
        wear = self.v["wear"]
        x = _mono_fold(audio)

        b = self.v["band"]
        if b > 0.001:
            lo = np.exp(np.log(20.0) * (1 - b) + np.log(50.0) * b)
            hi_top = 8000.0 * (5500.0 / 8000.0) ** wear  # wear shaves the top
            hi = np.exp(np.log(16000.0) * (1 - b) + np.log(hi_top) * b)
            x = U.highpass(x, lo, sr, order=2)
            x = U.lowpass(x, hi, sr, order=4)
            # lacquer cutter head resonance, gentle
            x = U.apply_sos(x, U.peaking(sr, 3400.0, 1.5 * b, q=1.8))

        bed = np.zeros((n, ch), np.float32)
        dur = n / sr

        sw = self.v["swish"]
        if sw > 0:
            g = stream(ctx.seed, f"{self.key}:swish")
            base = g.standard_normal(n).astype(np.float32)
            base = U.bandpass(base[:, None], 800.0, 5200.0, sr, order=2)[:, 0]
            t = np.arange(n) / sr
            ph = ((t + g.uniform(0, 1.8)) * self._REV_HZ) % 1.0
            # asymmetric once-per-rev bump (worn sector of the disc)
            bump = np.exp(-0.5 * ((ph - 0.5) / 0.16) ** 2)
            per_rev = 1.0 + 0.25 * U.control_noise(g, n, sr, 0.05, 0.3, ctrl_sr=50.0)
            am = (0.45 + 1.1 * bump * per_rev).astype(np.float32)
            swish = base * am
            lvl = U.db_to_lin(-52.0 + 10.0 * sw + 6.0 * wear)
            swish *= lvl / (U.rms(swish) + 1e-12)
            bed += swish[:, None]

        cr = self.v["crackle"]
        if cr > 0:
            g = stream(ctx.seed, f"{self.key}:crackle")
            imp = np.zeros(n, np.float32)
            k = int(g.poisson(cr * dur))
            if k > 0:
                idx = g.integers(0, n, k)
                amp = (g.random(k) ** 1.8) * np.where(g.random(k) < 0.5, -1.0, 1.0)
                np.add.at(imp, idx, amp.astype(np.float32))
                # crazing: some clicks arrive as tight clusters
                nclu = max(int(k * 0.15), 0)
                if nclu:
                    ci = g.integers(0, n, nclu)
                    for c0 in ci:
                        for _ in range(int(g.integers(1, 4))):
                            j = c0 + int(g.uniform(0.002, 0.06) * sr)
                            if j < n:
                                imp[j] += g.uniform(0.2, 0.7) * (1 if g.random() < 0.5 else -1)
            c = U.bandpass(imp[:, None], 1000.0, 5500.0, sr, order=2)[:, 0]
            lvl = U.db_to_lin(-34.0 + 6.0 * wear)
            bed += (c * 3.0 * lvl)[:, None]

        if wear > 0:
            g = stream(ctx.seed, f"{self.key}:wearhiss")
            h = np.stack([g.standard_normal(n).astype(np.float32) for _ in range(ch)], axis=1)
            h = U.bandpass(h, 2000.0, 6500.0, sr, order=2)
            h *= U.db_to_lin(-60.0 + 16.0 * wear) / (U.rms(h) + 1e-12)
            bed += h
            g2 = stream(ctx.seed, f"{self.key}:rumble")
            r = g2.standard_normal(n).astype(np.float32)
            r = U.lowpass(r[:, None], 45.0, sr, order=3)[:, 0]
            r *= U.db_to_lin(-52.0 + 8.0 * wear) / (U.rms(r) + 1e-12)
            bed += r[:, None]

        return U.peak_guard(x + bed)


@register
class A8Track(Effect):
    eid = "a_8track"
    label = "8-Track Cartridge"
    kind = "audio"
    desc = "1974 Stereo 8 cartridge: syrupy wow, crosstalk bleed from the adjacent program, baked tape hiss, and the iconic ker-CHUNK program change."
    PARAMS = (
        Param("wow", "Wow", "float", 0.5, 0.0, 1.0,
              desc="Cartridge transport wow/flutter (the endless-loop platter drags).", group="Pitch", iscale=True),
        Param("crosstalk_db", "Crosstalk", "float", -28.0, -60.0, -20.0, unit="dB",
              desc="Bleed of the adjacent program — the same tape a few seconds shifted, muffled, under everything.", group="Noise"),
        Param("program_clunk", "Program Clunk", "bool", False,
              desc="Insert the program-change ker-CHUNK: fade, dual solenoid thump, resume.", group="Damage"),
        Param("clunk_at_s", "Clunk Time", "float", 4.0, 0.0, 600.0, unit="s",
              desc="Where the program change lands.", group="Damage"),
        Param("hiss_db", "Hiss Level", "float", -44.0, -70.0, -28.0, unit="dB",
              desc="Cartridge tape hiss (baked into every 8-track).", group="Noise"),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        sr = ctx.sr
        x = audio.astype(np.float32)

        wow = self.v["wow"]
        if wow > 0 and n > 16:
            cents = 9.0 * wow * U.control_noise(
                stream(ctx.seed, f"{self.key}:wow"), n, sr, 0.3, 1.2, ctrl_sr=200.0)
            cents += 4.0 * wow * U.control_noise(
                stream(ctx.seed, f"{self.key}:flut"), n, sr, 5.0, 18.0, ctrl_sr=400.0)
            x = U.variable_speed(x, np.exp2(cents / 1200.0))

        x = U.highpass(x, 50.0, sr, order=2)
        x = U.lowpass(x, 9000.0, sr, order=3)
        x = U.apply_sos(x, U.peaking(sr, 110.0, 2.0, q=0.9))  # cart head bump

        ct = U.db_to_lin(self.v["crosstalk_db"])
        if ct > U.db_to_lin(-59.0) and n > sr:
            g = stream(ctx.seed, f"{self.key}:xtalk")
            off = int(g.uniform(8.0, 12.0) * sr) % n
            ghost = np.roll(x, off, axis=0)  # same tape, other program position
            ghost = U.lowpass(ghost, 2000.0, sr, order=3)  # adjacent-track azimuth muffle
            ghost = U.highpass(ghost, 150.0, sr, order=2)
            x = x + (ghost * ct).astype(np.float32)

        if self.v["program_clunk"]:
            t0 = self.v["clunk_at_s"]
            if 0.3 < t0 < n / sr - 0.5:
                g = stream(ctx.seed, f"{self.key}:clunk")
                env = np.ones(n, np.float32)
                s = int(t0 * sr)
                fade = int(0.15 * sr)
                gap = int(0.35 * sr)
                a0, a1 = max(s - fade, 0), s
                b0, b1 = min(s + gap, n), min(s + gap + fade, n)
                env[a0:a1] = np.linspace(1.0, 0.05, a1 - a0)
                env[a1:b0] = 0.05  # transport still rolling, program gone
                if b1 > b0:
                    env[b0:b1] = np.linspace(0.05, 1.0, b1 - b0)
                x = x * env[:, None]
                # dual-solenoid ker-CHUNK: lighter latch then the hard head shift
                k1 = _knock(g, sr, 70.0, 110.0, decay_s=0.03, click=0.5) * 0.5
                k2 = _knock(g, sr, 55.0, 90.0, decay_s=0.055, click=0.8) * 0.95
                U.add_at(x, k1 * 0.35, s + int(0.06 * sr))
                U.add_at(x, k2 * 0.42, s + int(0.20 * sr))

        lvl = U.db_to_lin(self.v["hiss_db"])
        if lvl > 1e-6:
            cols = []
            for c in range(ch):
                g = stream(ctx.seed, f"{self.key}:hiss{c}")
                cols.append(g.standard_normal(n).astype(np.float32))
            h = np.stack(cols, axis=1)
            h = U.tilt(h, sr, 5.0, pivot_hz=2500.0)
            h = U.lowpass(h, 9000.0, sr, order=4)
            h = U.highpass(h, 40.0, sr, order=1)
            h *= lvl / (U.rms(h) + 1e-12)
            x = x + h
        return U.peak_guard(x)


@register
class AMicrocassette(Effect):
    eid = "a_microcassette"
    label = "Microcassette"
    kind = "audio"
    desc = "1980s memo recorder at 2.4 cm/s: 300–4000 band, heavy flutter, hard AGC pumping and loud hiss — the dictation-tape sound."
    PARAMS = (
        Param("flutter", "Flutter", "float", 0.7, 0.0, 1.0,
              desc="Tiny-capstan transport instability (severe at 2.4 cm/s).", group="Pitch", iscale=True),
        Param("agc", "AGC Pump", "float", 0.8, 0.0, 1.0,
              desc="The recorder's automatic level control breathing hard between words.", group="Dynamics", iscale=True),
        Param("hiss_db", "Hiss Level", "float", -38.0, -60.0, -22.0, unit="dB",
              desc="Loud narrow tape hiss.", group="Noise"),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        sr = ctx.sr
        x = _mono_fold(audio)  # one tiny mic, one tiny speaker

        fl = self.v["flutter"]
        if fl > 0 and n > 16:
            cents = 12.0 * fl * U.control_noise(
                stream(ctx.seed, f"{self.key}:wow"), n, sr, 0.6, 2.5, ctrl_sr=200.0)
            cents += 20.0 * fl * U.control_noise(
                stream(ctx.seed, f"{self.key}:flut"), n, sr, 8.0, 30.0, ctrl_sr=400.0)
            cents += 4.0 * fl * U.control_noise(
                stream(ctx.seed, f"{self.key}:scrape"), n, sr, 50.0, 160.0, ctrl_sr=1000.0)
            x = U.variable_speed(x, np.exp2(cents / 1200.0))

        x = U.highpass(x, 300.0, sr, order=3)
        x = U.lowpass(x, 4000.0, sr, order=5)
        x = U.apply_sos(x, U.peaking(sr, 1400.0, 3.0, q=1.3))  # condenser-capsule honk
        y = np.tanh(2.8 * x) / 2.8  # cheap electronics clip early
        x = U.match_rms(y, x, max_db=6.0)

        agc = self.v["agc"]
        if agc > 0:
            env = U.envelope(x, sr, attack_ms=4.0, release_ms=260.0, mode="rms")
            ref = np.percentile(env, 90) + 1e-9
            desired = np.clip((ref * 0.7) / np.maximum(env, 1e-5),
                              U.db_to_lin(-10.0), U.db_to_lin(16.0))
            gain = U.smooth_gain(desired.astype(np.float32), sr, 4.0, 260.0)
            x = (x * (gain ** (0.4 + 0.6 * agc))[:, None]).astype(np.float32)
            x = U.match_rms(x, audio, max_db=9.0)

        lvl = U.db_to_lin(self.v["hiss_db"])
        if lvl > 1e-6:
            g = stream(ctx.seed, f"{self.key}:hiss")
            h = g.standard_normal(n).astype(np.float32)
            h = U.bandpass(h[:, None], 250.0, 4300.0, sr, order=2)[:, 0]
            h *= lvl / (U.rms(h) + 1e-12)
            x = x + h[:, None]
        return U.peak_guard(x)


@register
class ATubeAmp(Effect):
    eid = "a_tube_amp"
    label = "Tube Amplifier"
    kind = "audio"
    desc = "Tube console electronics: even-harmonic warmth, output-transformer sag that softens loud lows, faint microphonic ring on transients, and supply hum."
    PARAMS = (
        Param("drive", "Drive", "float", 1.8, 1.0, 6.0,
              desc="How hard the output stage is pushed.", group="Dynamics"),
        Param("sag", "Transformer Sag", "float", 0.4, 0.0, 1.0,
              desc="Dynamic low-end give: loud passages lose bass weight and compress as the iron saturates.", group="Dynamics", iscale=True),
        Param("microphonics", "Microphonics", "float", 0.0, 0.0, 1.0,
              desc="A slightly loose tube rings faintly (1–2 kHz) when transients shake it.", group="Damage", iscale=True),
        Param("hum_db", "Hum", "float", -60.0, -80.0, -35.0, unit="dB",
              desc="Heater/supply hum with a warm harmonic stack.", group="Noise"),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        sr = ctx.sr
        x = U.highpass(U.lowpass(audio, 14000.0, sr, order=2), 25.0, sr, order=1)

        # asymmetric soft clip: grid bias offsets the curve = even harmonics
        d = self.v["drive"]
        c = 0.35
        y = (np.tanh(d * x + c) - np.tanh(c)) / d
        y = y - float(np.mean(y))
        x = U.match_rms(y.astype(np.float32), x, max_db=9.0)

        sag = self.v["sag"]
        if sag > 0:
            env = U.envelope(x, sr, attack_ms=25.0, release_ms=280.0, mode="rms")
            ref = np.percentile(env, 90) + 1e-9
            loud = np.clip(env / ref - 0.35, 0.0, 1.0)
            low = U.lowpass(x, 200.0, sr, order=2)
            lg = (1.0 - 0.45 * sag * loud)[:, None].astype(np.float32)   # lows give first
            gg = (1.0 - 0.18 * sag * loud)[:, None].astype(np.float32)   # whole rail droops
            x = ((low * lg + (x - low)) * gg).astype(np.float32)
            x = U.match_rms(x, audio, max_db=6.0)

        mic = self.v["microphonics"]
        if mic > 0:
            g = stream(ctx.seed, f"{self.key}:mic")
            fast = U.envelope(x, sr, attack_ms=1.0, release_ms=40.0, mode="peak")
            onset = np.diff(fast, prepend=fast[:1])
            thr = np.percentile(onset, 99.2) + 1e-9
            hits = np.nonzero(onset > thr)[0]
            f0 = g.uniform(1100.0, 2000.0)
            last = -sr
            ring_lvl = U.db_to_lin(-40.0 + 10.0 * mic)
            for i in hits:
                if i - last < int(0.15 * sr):
                    continue
                last = i
                L = int(0.22 * sr)
                t = np.arange(L) / sr
                ring = np.sin(2 * np.pi * f0 * (1.0 + g.uniform(-0.004, 0.004)) * t)
                ring *= np.exp(-t / 0.07) * ring_lvl * g.uniform(0.5, 1.0)
                ring *= min(float(onset[i] / thr), 3.0) / 3.0
                U.add_at(x, ring.astype(np.float32), int(i))

        lvl = U.db_to_lin(self.v["hum_db"])
        if lvl > 1e-6 and self.v["hum_db"] > -79.5:
            g = stream(ctx.seed, f"{self.key}:hum")
            wander = 60.0 + 0.05 * U.control_noise(g, n, sr, 0.02, 0.1, ctrl_sr=50.0)
            ph = 2 * np.pi * np.cumsum(wander) / sr
            hum = np.zeros(n, np.float64)
            for k, a in ((1, 1.0), (2, 0.6), (3, 0.25), (4, 0.1), (5, 0.05)):
                hum += a * np.sin(k * ph + g.uniform(0, 2 * np.pi) * (0 if k == 1 else 1))
            h = hum.astype(np.float32)
            h *= lvl / (U.rms(h) + 1e-12)
            x = x + h[:, None]
        return U.peak_guard(x)
