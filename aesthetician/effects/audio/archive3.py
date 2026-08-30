"""Archival audio capture, carrier, duplication and transfer artifacts.

These effects alter the supplied program and its physical noise floor. They do
not generate music, dialogue or other editorial content.
"""

from __future__ import annotations

import numpy as np

from ...engine.graph import Context, Effect, Param, register
from ...engine.rng import stream
from . import _util as U


def _mono_mix(audio: np.ndarray, amount: float) -> np.ndarray:
    if audio.shape[1] < 2 or amount <= 0.0:
        return audio.astype(np.float32)
    mid = audio.mean(axis=1, keepdims=True)
    return (audio * (1.0 - amount) + mid * amount).astype(np.float32)


@register
class AHistoricalMicrophone(Effect):
    eid = "a_historical_mic"
    label = "Historical Microphone"
    kind = "audio"
    desc = "Period microphone capture: capsule response, resonant presence, proximity rise, overload, self-noise and optional handling thumps."

    # low cut, high cut, response peaks, top shelf, inherent mono amount
    _PROFILES = {
        "carbon_1925": (180.0, 3200.0, ((950.0, 3.5, 1.0), (2200.0, 5.0, 1.8)), -2.0, 1.0),
        "ribbon_1938": (45.0, 10500.0, ((180.0, 2.2, 0.8), (3200.0, -1.5, 1.0)), -2.0, 1.0),
        "broadcast_dynamic_1955": (60.0, 12000.0, ((130.0, 1.4, 0.9), (2300.0, 3.0, 1.2)), -0.8, 1.0),
        "crystal_1940": (150.0, 7200.0, ((850.0, -1.5, 1.0), (2600.0, 4.8, 1.5)), -1.5, 1.0),
        "lavalier_1972": (90.0, 12000.0, ((260.0, 2.5, 1.0), (3900.0, 2.2, 1.1)), -0.5, 0.85),
        "shotgun_1975": (70.0, 14000.0, ((350.0, -1.5, 0.8), (2800.0, 3.2, 1.0)), 0.0, 0.65),
        "electret_1985": (100.0, 15000.0, ((500.0, -1.0, 0.9), (5200.0, 2.4, 1.3)), 0.8, 0.65),
        "camcorder_1994": (120.0, 12000.0, ((650.0, -1.2, 0.9), (3300.0, 3.0, 1.2)), -1.0, 0.75),
    }
    PARAMS = (
        Param("profile", "Microphone", "enum", "broadcast_dynamic_1955",
              choices=tuple(_PROFILES), desc="Capsule and enclosure response.", group="Capture"),
        Param("amount", "Capture Amount", "float", 1.0, 0.0, 1.0,
              desc="Morphs from the source microphone to the selected period microphone.", group="Capture", iscale=True),
        Param("proximity", "Proximity Rise", "float", 0.0, 0.0, 1.0,
              desc="Close-mic bass rise around 180 Hz.", group="Capture", iscale=True),
        Param("overload", "Capsule Overload", "float", 0.15, 0.0, 1.0,
              desc="Level-compensated capsule and preamp saturation.", group="Dynamics", iscale=True),
        Param("self_noise_db", "Self Noise", "float", -62.0, -80.0, -30.0, unit="dB",
              desc="Microphone electronics and capsule noise floor.", group="Noise"),
        Param("handling", "Handling Thumps", "float", 0.0, 0.0, 1.0,
              desc="Random low-frequency knocks transmitted through the stand or camera body.", group="Damage", iscale=True),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        amount = self.v["amount"]
        if amount <= 0.0 or not len(audio):
            return audio.astype(np.float32)
        n, ch = audio.shape
        sr = ctx.sr
        lo, hi, peaks, top, mono = self._PROFILES[self.v["profile"]]
        y = U.highpass(audio, lo, sr, order=2)
        y = U.lowpass(y, hi, sr, order=4)
        rows = [U.peaking(sr, hz, db, q=q) for hz, db, q in peaks]
        if abs(top) > 0.01:
            rows.append(U.shelf(sr, min(4200.0, hi * 0.7), top, high=True, s=0.7))
        y = U.apply_sos(y, U.sos_cascade(*rows))
        if self.v["proximity"] > 0:
            y = U.apply_sos(y, U.shelf(sr, 180.0, 7.0 * self.v["proximity"], high=False, s=0.7))
        overload = self.v["overload"]
        if overload > 0:
            drive = 1.0 + 5.0 * overload
            clipped = np.tanh(drive * y) / drive
            y = U.match_rms(clipped.astype(np.float32), y, max_db=8.0)
        y = _mono_mix(y, mono)
        x = (audio * (1.0 - amount) + y * amount).astype(np.float32)

        if self.v["self_noise_db"] > -79.5:
            cols = []
            for c in range(ch):
                g = stream(ctx.seed, f"{self.key}:self{c}")
                cols.append(g.standard_normal(n).astype(np.float32))
            noise = np.stack(cols, axis=1)
            noise = U.highpass(U.lowpass(noise, hi, sr, order=3), max(lo * 0.5, 30.0), sr, order=1)
            noise *= U.db_to_lin(self.v["self_noise_db"]) / (U.rms(noise) + 1e-12)
            x += noise * amount

        handling = self.v["handling"]
        if handling > 0:
            g = stream(ctx.seed, f"{self.key}:handling")
            for t0 in U.event_times(g, 18.0 * handling, n / sr, min_gap_s=0.4):
                length = int(g.uniform(0.04, 0.16) * sr)
                t = np.arange(length) / sr
                hz = g.uniform(38.0, 95.0)
                thump = np.sin(2 * np.pi * hz * t + g.uniform(0, 2 * np.pi))
                thump *= np.exp(-t / g.uniform(0.018, 0.055))
                thump = U.lowpass(thump[:, None].astype(np.float32), 240.0, sr, order=2)[:, 0]
                U.add_at(x, thump * (0.08 + 0.18 * handling) * amount, int(t0 * sr))
        return U.peak_guard(x)


@register
class ADiscMedium(Effect):
    eid = "a_disc_medium"
    label = "Early Disc and Cylinder"
    kind = "audio"
    desc = "Wax cylinder, aluminum disc, home acetate and dictation-belt recording with format response, rotational wow, surface wash and wear impacts."

    # low, high, rotation rate, response peaks, noise low/high
    _MEDIA = {
        "wax_cylinder_1905": (250.0, 2800.0, 2.67, ((700.0, 3.0, 1.0), (1800.0, 4.5, 1.5)), 300.0, 3500.0),
        "wax_dictation_1922": (180.0, 3500.0, 1.33, ((900.0, 2.5, 1.0), (2400.0, 3.0, 1.8)), 250.0, 4200.0),
        "aluminum_disc_1934": (140.0, 4800.0, 1.30, ((1600.0, 2.8, 1.2), (3400.0, 2.0, 1.8)), 500.0, 6500.0),
        "acetate_home_1947": (90.0, 6500.0, 1.30, ((120.0, 1.5, 0.8), (3200.0, 1.8, 1.4)), 700.0, 8000.0),
        "dictation_belt_1964": (240.0, 4300.0, 0.42, ((1100.0, 2.0, 1.0), (2800.0, 3.0, 1.5)), 350.0, 5200.0),
    }
    PARAMS = (
        Param("medium", "Medium", "enum", "wax_cylinder_1905", choices=tuple(_MEDIA),
              desc="Physical recording format and its native response.", group="Medium"),
        Param("wear", "Wear", "float", 0.45, 0.0, 1.0,
              desc="Dulls the recorded edge and raises irregular surface modulation.", group="Damage", iscale=True),
        Param("surface_db", "Surface Wash", "float", -45.0, -80.0, -28.0, unit="dB",
              desc="Continuous stylus and surface noise floor.", group="Noise"),
        Param("impacts", "Surface Impacts", "float", 10.0, 0.0, 80.0, unit="/min",
              desc="Larger pits, seams and recording defects per minute.", group="Damage", iscale=True),
        Param("wow_cents", "Rotational Wow", "float", 12.0, 0.0, 45.0, unit="cents",
              desc="Pitch variation at the medium's rotation rate.", group="Pitch", iscale=True),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        if n < 16:
            return audio.astype(np.float32)
        sr = ctx.sr
        lo, hi, rev_hz, peaks, nlo, nhi = self._MEDIA[self.v["medium"]]
        wear = self.v["wear"]
        x = _mono_mix(audio, 1.0)
        wow = self.v["wow_cents"]
        if wow > 0:
            g = stream(ctx.seed, f"{self.key}:wow")
            t = np.arange(n) / sr + ctx.t0
            cents = wow * (0.72 * np.sin(2 * np.pi * rev_hz * t + g.uniform(0, 2 * np.pi))
                           + 0.28 * U.control_noise(g, n, sr, 0.08, 0.5, ctrl_sr=80.0))
            x = U.variable_speed(x, np.exp2(cents / 1200.0))
        top = hi * (0.62 ** wear)
        x = U.highpass(U.lowpass(x, top, sr, order=5), lo, sr, order=3)
        x = U.apply_sos(x, U.sos_cascade(*(U.peaking(sr, hz, db, q=q) for hz, db, q in peaks)))
        y = np.tanh((1.5 + 1.4 * wear) * x) / (1.5 + 1.4 * wear)
        x = U.match_rms(y.astype(np.float32), x, max_db=8.0)

        if self.v["surface_db"] > -79.5:
            g = stream(ctx.seed, f"{self.key}:surface")
            wash = g.standard_normal(n).astype(np.float32)
            wash = U.bandpass(wash[:, None], nlo, min(nhi, sr * 0.47), sr, order=2)[:, 0]
            t = np.arange(n) / sr + ctx.t0
            turn = 0.65 + (0.22 + 0.3 * wear) * (0.5 + 0.5 * np.sin(2 * np.pi * rev_hz * t))
            wash *= turn.astype(np.float32)
            wash *= U.db_to_lin(self.v["surface_db"] + 5.0 * wear) / (U.rms(wash) + 1e-12)
            x += wash[:, None]

        impacts = self.v["impacts"]
        if impacts > 0:
            g = stream(ctx.seed, f"{self.key}:impacts")
            for t0 in U.event_times(g, impacts, n / sr, min_gap_s=0.08):
                length = int(g.uniform(0.005, 0.035) * sr)
                t = np.arange(length) / sr
                click = g.standard_normal(length).astype(np.float32) * np.exp(-t / g.uniform(0.002, 0.012))
                click = U.bandpass(click[:, None], 500.0, min(6500.0, sr * 0.47), sr, order=2)[:, 0]
                click /= np.max(np.abs(click)) + 1e-9
                U.add_at(x, click * g.uniform(0.06, 0.22), int(t0 * sr))
        return U.peak_guard(x)


@register
class AAnalogDub(Effect):
    eid = "a_analog_dub"
    label = "Analog Dub Generations"
    kind = "audio"
    desc = "Repeat analog generations with speed-specific head response, saturation, alignment smear and cumulative tape hiss."

    # low, high, head bump, hiss tilt
    _FORMATS = {
        "reel_15ips": (28.0, 18000.0, 55.0, 2.0),
        "reel_75ips": (38.0, 15000.0, 75.0, 3.0),
        "reel_375ips": (55.0, 9500.0, 105.0, 4.5),
        "broadcast_cart": (70.0, 10500.0, 115.0, 4.0),
        "cassette": (42.0, 12500.0, 95.0, 6.0),
        "microcassette": (240.0, 4500.0, 150.0, 3.0),
    }
    PARAMS = (
        Param("format", "Tape Format", "enum", "reel_75ips", choices=tuple(_FORMATS),
              desc="Transport speed and head geometry for every generation.", group="Medium"),
        Param("generations", "Generations", "int", 1, 0, 8,
              desc="Number of analog record-play cycles. Zero passes the source untouched.", group="Medium"),
        Param("alignment", "Alignment Error", "float", 0.15, 0.0, 1.0,
              desc="Cumulative head azimuth error and drifting high-frequency smear.", group="Damage", iscale=True),
        Param("compression", "Generation Compression", "float", 0.25, 0.0, 1.0,
              desc="Saturation and level loss accumulated on each copy.", group="Dynamics", iscale=True),
        Param("hiss_db", "Per-Generation Hiss", "float", -58.0, -80.0, -32.0, unit="dB",
              desc="Noise contributed by each record-play cycle.", group="Noise"),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        generations = self.v["generations"]
        if generations <= 0 or not len(audio):
            return audio.astype(np.float32)
        n, ch = audio.shape
        sr = ctx.sr
        lo, hi, bump, hiss_tilt = self._FORMATS[self.v["format"]]
        alignment = self.v["alignment"]
        compression = self.v["compression"]
        x = audio.astype(np.float32)
        for gen in range(generations):
            this_hi = hi * (0.95 ** gen) * (1.0 - 0.16 * alignment)
            x = U.highpass(U.lowpass(x, this_hi, sr, order=3), lo, sr, order=2)
            x = U.apply_sos(x, U.peaking(sr, bump, 0.8 + 0.45 * gen, q=0.85))
            if alignment > 0:
                g = stream(ctx.seed, f"{self.key}:align{gen}")
                drift = np.clip(0.45 + 0.55 * U.control_noise(g, n, sr, 0.04, 0.28, ctrl_sr=80.0), 0.0, 1.0)
                mix = (alignment * (0.18 + 0.08 * gen) * drift)[:, None].astype(np.float32)
                dull = U.lowpass(x, max(2600.0, this_hi * 0.42), sr, order=2)
                x = x * (1.0 - mix) + dull * mix
                if ch >= 2:
                    delay = np.maximum(0.0, alignment * (4.0 + 2.5 * gen) * drift)
                    x[:, 1] = U.fractional_delay(x[:, 1], delay)
            if compression > 0:
                drive = 1.0 + compression * (0.9 + 0.22 * gen)
                y = np.tanh(drive * x) / drive
                x = U.match_rms(y.astype(np.float32), x, max_db=5.0)

        if self.v["hiss_db"] > -79.5:
            cols = []
            for c in range(ch):
                g = stream(ctx.seed, f"{self.key}:hiss{c}")
                cols.append(g.standard_normal(n).astype(np.float32))
            hiss = np.stack(cols, axis=1)
            hiss = U.tilt(hiss, sr, hiss_tilt, pivot_hz=2500.0)
            hiss = U.highpass(U.lowpass(hiss, min(hi, sr * 0.47), sr, order=3), 30.0, sr, order=1)
            combined_db = self.v["hiss_db"] + 10.0 * np.log10(max(generations, 1))
            hiss *= U.db_to_lin(combined_db) / (U.rms(hiss) + 1e-12)
            x += hiss
        return U.peak_guard(x)


@register
class APrintThrough(Effect):
    eid = "a_print_through"
    label = "Tape Print-Through"
    kind = "audio"
    desc = "Magnetic layer-to-layer print-through: dull pre-echo and post-echo from adjacent tape winds, with optional multiple layers."
    PARAMS = (
        Param("delay_s", "Layer Delay", "float", 1.1, 0.15, 3.0, unit="s",
              desc="Time between adjacent tape winds at the pack diameter.", group="Medium"),
        Param("pre_echo_db", "Pre-Echo", "float", -48.0, -80.0, -24.0, unit="dB",
              desc="Future program magnetically printed onto the preceding tape layer.", group="Damage"),
        Param("post_echo_db", "Post-Echo", "float", -54.0, -80.0, -24.0, unit="dB",
              desc="Past program magnetically printed onto the following tape layer.", group="Damage"),
        Param("layers", "Printed Layers", "int", 1, 1, 3,
              desc="Number of progressively quieter adjacent winds.", group="Damage"),
        Param("softness", "Ghost Softness", "float", 0.55, 0.0, 1.0,
              desc="High-frequency loss and magnetic blur in the transferred ghost.", group="Bandwidth", iscale=True),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n = len(audio)
        if n < 2:
            return audio.astype(np.float32)
        delay = max(int(self.v["delay_s"] * ctx.sr), 1)
        cutoff = 12000.0 * (3500.0 / 12000.0) ** self.v["softness"]
        ghost = U.lowpass(audio, cutoff, ctx.sr, order=2)
        x = audio.astype(np.float32).copy()
        for layer in range(1, self.v["layers"] + 1):
            d = delay * layer
            if d >= n:
                break
            falloff = 4.5 * (layer - 1)
            pre = U.db_to_lin(self.v["pre_echo_db"] - falloff)
            post = U.db_to_lin(self.v["post_echo_db"] - falloff)
            if self.v["pre_echo_db"] > -79.5:
                x[:-d] += ghost[d:] * pre
            if self.v["post_echo_db"] > -79.5:
                x[d:] += ghost[:-d] * post
        return U.peak_guard(x)


@register
class ANoiseReduction(Effect):
    eid = "a_noise_reduction"
    label = "Noise-Reduction Mistracking"
    kind = "audio"
    desc = "Dolby, dbx and telcom replay mismatch with level-dependent brightness loss or excess, noise-floor breathing and compander pumping."

    # crossover, maximum tracking shift, broadband share
    _SYSTEMS = {
        "dolby_b": (1800.0, 8.0, 0.05),
        "dolby_c": (900.0, 14.0, 0.12),
        "dbx": (120.0, 12.0, 0.75),
        "telcom": (350.0, 9.0, 0.45),
    }
    PARAMS = (
        Param("system", "System", "enum", "dolby_b", choices=tuple(_SYSTEMS),
              desc="Compander family and the band it controls.", group="Medium"),
        Param("decode_error", "Decode Error", "float", -0.35, -1.0, 1.0,
              desc="Negative is under-decoded and bright in quiet passages; positive is over-decoded and dull.", group="Dynamics"),
        Param("threshold_db", "Tracking Threshold", "float", -34.0, -60.0, -18.0, unit="dB",
              desc="Program level below which the replay curve moves most.", group="Dynamics"),
        Param("pumping", "Compander Pump", "float", 0.25, 0.0, 1.0,
              desc="Broadband gain breathing caused by level-tracking lag.", group="Dynamics", iscale=True),
        Param("hiss_db", "Residual Hiss", "float", -58.0, -80.0, -32.0, unit="dB",
              desc="Tape noise remaining after the mismatched replay system.", group="Noise"),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        if not len(audio):
            return audio.astype(np.float32)
        n, ch = audio.shape
        sr = ctx.sr
        crossover, max_shift, broad = self._SYSTEMS[self.v["system"]]
        low = U.lowpass(audio, crossover, sr, order=2)
        controlled = (audio - low).astype(np.float32)
        detector = audio if broad > 0.5 else controlled
        env = U.envelope(detector, sr, attack_ms=8.0, release_ms=180.0, mode="rms")
        env_db = 20.0 * np.log10(np.maximum(env, 1e-7))
        quiet = np.clip((self.v["threshold_db"] - env_db) / 28.0, 0.0, 1.0)
        shift_db = -self.v["decode_error"] * max_shift * quiet
        tracked = controlled * np.power(10.0, shift_db / 20.0)[:, None].astype(np.float32)
        x = low + tracked
        if broad > 0:
            x = audio * (1.0 - broad) + x * broad

        pumping = self.v["pumping"]
        if pumping > 0:
            ref = np.percentile(env, 90) + 1e-9
            loud = np.clip(env / ref, 0.0, 1.5)
            desired = np.power(10.0, (-2.8 * pumping * loud) / 20.0).astype(np.float32)
            gain = U.smooth_gain(desired, sr, attack_ms=12.0, release_ms=320.0)
            x *= gain[:, None]
            x = U.match_rms(x, audio, max_db=5.0)

        if self.v["hiss_db"] > -79.5:
            cols = []
            for c in range(ch):
                g = stream(ctx.seed, f"{self.key}:hiss{c}")
                cols.append(g.standard_normal(n).astype(np.float32))
            hiss = np.stack(cols, axis=1)
            hiss = U.highpass(U.lowpass(hiss, 15000.0, sr, order=3), max(700.0, crossover * 0.5), sr, order=1)
            breathe = 0.65 + (0.4 + 0.8 * pumping) * quiet
            hiss *= breathe[:, None].astype(np.float32)
            hiss *= U.db_to_lin(self.v["hiss_db"]) / (U.rms(hiss) + 1e-12)
            x += hiss
        return U.peak_guard(x)


@register
class AVideoTapeAudio(Effect):
    eid = "a_video_tape_audio"
    label = "Videotape Audio Track"
    kind = "audio"
    desc = "U-matic, Betamax, VHS and 8 mm video audio tracks with native carrier response, companding, tracking roughness, head-switch ticks and dropouts."

    # low, high, mono amount, compression, noise tilt
    _FORMATS = {
        "umatic_linear": (80.0, 9000.0, 1.0, 0.45, 4.0),
        "betamax_linear": (100.0, 8200.0, 1.0, 0.55, 5.0),
        "vhs_linear": (120.0, 7200.0, 1.0, 0.65, 5.5),
        "betahifi": (28.0, 18000.0, 0.0, 0.35, 2.0),
        "vhs_hifi": (30.0, 17500.0, 0.0, 0.4, 2.5),
        "video8_afm": (55.0, 14000.0, 0.8, 0.45, 3.5),
        "hi8_afm": (42.0, 15500.0, 0.0, 0.38, 3.0),
    }
    PARAMS = (
        Param("format", "Track Format", "enum", "vhs_linear", choices=tuple(_FORMATS),
              desc="Native linear or frequency-modulated video audio format.", group="Medium"),
        Param("tracking", "Audio Tracking", "float", 0.2, 0.0, 1.0,
              desc="Slow carrier-level roughness and high-frequency instability.", group="Damage", iscale=True),
        Param("dropout_rate", "Audio Dropouts", "float", 4.0, 0.0, 90.0, unit="/min",
              desc="Brief carrier or longitudinal-track losses per minute.", group="Damage", iscale=True),
        Param("noise_db", "Track Noise", "float", -52.0, -80.0, -30.0, unit="dB",
              desc="Format-shaped track or demodulation noise floor.", group="Noise"),
        Param("head_switch_db", "Head-Switch Ticks", "float", -62.0, -80.0, -34.0, unit="dB",
              desc="Frame-rate switching residue from the rotating video heads.", group="Noise"),
        Param("compander_error", "Compander Error", "float", 0.0, -1.0, 1.0,
              desc="Hi-Fi and AFM level-tracking error: negative brightens quiet material, positive dulls it.", group="Dynamics"),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        if n < 16:
            return audio.astype(np.float32)
        sr = ctx.sr
        lo, hi, mono, comp, noise_tilt = self._FORMATS[self.v["format"]]
        x = _mono_mix(audio, mono)
        x = U.highpass(U.lowpass(x, hi, sr, order=4), lo, sr, order=2)
        if comp > 0:
            drive = 1.0 + 1.8 * comp
            y = np.tanh(drive * x) / drive
            x = U.match_rms(y.astype(np.float32), x, max_db=5.0)

        err = self.v["compander_error"]
        if abs(err) > 0.001:
            low = U.lowpass(x, 1800.0, sr, order=2)
            high = (x - low).astype(np.float32)
            env = U.envelope(x, sr, 8.0, 180.0, mode="rms")
            ref = np.percentile(env, 88) + 1e-9
            quiet = np.clip(1.0 - env / ref, 0.0, 1.0)
            gain = np.power(10.0, (-err * 7.0 * quiet) / 20.0).astype(np.float32)
            x = low + high * gain[:, None]

        tracking = self.v["tracking"]
        if tracking > 0:
            g = stream(ctx.seed, f"{self.key}:tracking")
            rough = U.control_noise(g, n, sr, 0.8, 18.0, ctrl_sr=300.0)
            gain = np.clip(1.0 + 0.08 * tracking * rough, 0.68, 1.12)
            dull = U.lowpass(x, min(5200.0, hi * 0.55), sr, order=2)
            loss = np.clip(tracking * np.maximum(-rough, 0.0), 0.0, 1.0)[:, None]
            x = (x * (1.0 - loss) + dull * loss) * gain[:, None]
            if ch >= 2 and mono < 1.0:
                delay = np.maximum(0.0, tracking * 18.0 * (0.5 + 0.5 * rough))
                x[:, 1] = U.fractional_delay(x[:, 1], delay)

        rate = self.v["dropout_rate"]
        if rate > 0:
            g = stream(ctx.seed, f"{self.key}:dropouts")
            gain = np.ones(n, np.float32)
            for t0 in U.event_times(g, rate, n / sr, min_gap_s=0.18):
                length = max(int(g.uniform(0.006, 0.055) * sr), 8)
                start = int(t0 * sr)
                end = min(start + length, n)
                if end <= start:
                    continue
                env = 0.5 - 0.5 * np.cos(np.linspace(0, 2 * np.pi, end - start))
                depth = U.db_to_lin(-g.uniform(8.0, 30.0))
                gain[start:end] *= (1.0 - env * (1.0 - depth)).astype(np.float32)
            x *= gain[:, None]

        if self.v["noise_db"] > -79.5:
            cols = []
            for c in range(ch):
                g = stream(ctx.seed, f"{self.key}:noise{c}")
                cols.append(g.standard_normal(n).astype(np.float32))
            noise = np.stack(cols, axis=1)
            noise = U.tilt(noise, sr, noise_tilt, pivot_hz=2400.0)
            noise = U.highpass(U.lowpass(noise, hi, sr, order=3), max(30.0, lo * 0.5), sr, order=1)
            noise *= U.db_to_lin(self.v["noise_db"]) / (U.rms(noise) + 1e-12)
            x += noise

        if self.v["head_switch_db"] > -79.5:
            g = stream(ctx.seed, f"{self.key}:switch")
            ticks = np.zeros(n, np.float32)
            frame_samples = sr / max(ctx.fps, 1.0)
            first = int((np.ceil(ctx.t0 * ctx.fps) / ctx.fps - ctx.t0) * sr)
            for i in np.arange(first, n, frame_samples).astype(int):
                length = min(int(0.0018 * sr), n - i)
                if length <= 0:
                    continue
                t = np.arange(length) / sr
                ticks[i:i + length] += (g.uniform(0.6, 1.0) * np.exp(-t / 0.00035)
                                        * np.sin(2 * np.pi * g.uniform(900.0, 2800.0) * t)).astype(np.float32)
            if U.rms(ticks) > 1e-9:
                ticks *= U.db_to_lin(self.v["head_switch_db"]) / U.rms(ticks)
                x += ticks[:, None]
        return U.peak_guard(x)


@register
class AChannelAging(Effect):
    eid = "a_channel_aging"
    label = "Stereo Channel Aging"
    kind = "audio"
    desc = "Aging stereo and dual-system alignment: width change, channel imbalance, crosstalk, time skew, phase wander and mono bass."
    PARAMS = (
        Param("width", "Stereo Width", "float", 0.8, 0.0, 1.8,
              desc="Zero is mono, one preserves the source, and values above one widen the side channel.", group="Image"),
        Param("imbalance_db", "Right Imbalance", "float", -0.5, -8.0, 8.0, unit="dB",
              desc="Gain offset of the right channel relative to the left.", group="Image"),
        Param("crosstalk_db", "Crosstalk", "float", -42.0, -80.0, -6.0, unit="dB",
              desc="Opposite-channel leakage through heads, wiring or transfer electronics.", group="Image"),
        Param("skew_us", "Channel Skew", "float", 40.0, -1500.0, 1500.0, unit="us",
              desc="Fixed timing error between left and right channels.", group="Image"),
        Param("phase_wander", "Phase Wander", "float", 0.1, 0.0, 1.0,
              desc="Slow drifting inter-channel delay from mechanical alignment.", group="Damage", iscale=True),
        Param("mono_bass_hz", "Mono Bass Below", "float", 120.0, 20.0, 600.0, unit="Hz",
              desc="Folds low frequencies toward mono below this point. Set to 20 Hz for effectively off.", group="Image"),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        if audio.shape[1] < 2 or not len(audio):
            return audio.astype(np.float32)
        n = len(audio)
        sr = ctx.sr
        x = audio.astype(np.float32).copy()
        skew = self.v["skew_us"] * sr / 1_000_000.0
        wander = self.v["phase_wander"]
        if wander > 0:
            g = stream(ctx.seed, f"{self.key}:phase")
            drift = U.control_noise(g, n, sr, 0.03, 0.35, ctrl_sr=80.0)
        else:
            drift = np.zeros(n, np.float32)
        delay = np.abs(skew) + 28.0 * wander * (0.5 + 0.5 * drift)
        if skew >= 0:
            x[:, 1] = U.fractional_delay(x[:, 1], delay)
        else:
            x[:, 0] = U.fractional_delay(x[:, 0], delay)

        leak = U.db_to_lin(self.v["crosstalk_db"])
        if self.v["crosstalk_db"] > -79.5:
            left, right = x[:, 0].copy(), x[:, 1].copy()
            x[:, 0] = (left + leak * right) / (1.0 + leak)
            x[:, 1] = (right + leak * left) / (1.0 + leak)

        mid = 0.5 * (x[:, 0] + x[:, 1])
        side = 0.5 * (x[:, 0] - x[:, 1]) * self.v["width"]
        x[:, 0], x[:, 1] = mid + side, mid - side
        x[:, 1] *= U.db_to_lin(self.v["imbalance_db"])

        bass_hz = self.v["mono_bass_hz"]
        if bass_hz > 22.0:
            low = U.lowpass(x[:, :2], bass_hz, sr, order=2)
            low_mid = low.mean(axis=1, keepdims=True)
            x[:, :2] = x[:, :2] - low + low_mid
        return U.peak_guard(U.match_rms(x, audio, max_db=4.0))
