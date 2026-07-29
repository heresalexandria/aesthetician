"""Vinyl & shellac: surface noise, off-center wow, needle-drop events."""

from __future__ import annotations

import numpy as np

from ...engine.graph import Context, Effect, Param, register
from ...engine.rng import stream
from . import _util as U


def _impulse_train(rng: np.random.Generator, n: int, per_second: float, sr: int,
                   amp_pow: float = 1.6, amp: float = 1.0) -> np.ndarray:
    """Sparse random impulses with power-law amplitudes and random polarity."""
    k = int(rng.poisson(max(per_second, 0.0) * n / sr))
    out = np.zeros(n, np.float32)
    if k <= 0:
        return out
    idx = rng.integers(0, n, k)
    a = amp * rng.random(k) ** amp_pow  # many small, few big
    a *= np.where(rng.random(k) < 0.5, -1.0, 1.0)
    np.add.at(out, idx, a.astype(np.float32))
    return out


def _pan_spread(rng: np.random.Generator, imp: np.ndarray, ch: int, width: float) -> np.ndarray:
    """Place each impulse at a random equal-power pan position (±width).

    Gains are scaled so a center impulse matches the coherent mono path
    exactly (1.0 in both channels)."""
    out = np.zeros((len(imp), ch), np.float32)
    nz = np.nonzero(imp)[0]
    if len(nz) == 0:
        return out
    a = (rng.uniform(-width, width, len(nz)) + 1.0) * (np.pi / 4.0)
    out[nz, 0] = imp[nz] * (np.sqrt(2.0) * np.cos(a))
    if ch >= 2:
        out[nz, 1] = imp[nz] * (np.sqrt(2.0) * np.sin(a))
    for c in range(2, ch):
        out[:, c] = out[:, c % 2]
    return out


def _groove_noise(rng: np.random.Generator, n: int, sr: int, heavy: float = 1.0) -> np.ndarray:
    """A short bed of 'needle in the groove' noise: crackle + frying + hiss."""
    bed = _impulse_train(rng, n, 30.0 * heavy, sr, amp=0.8)
    bed = U.bandpass(bed[:, None], 800.0, 7000.0, sr, order=2)[:, 0]
    fry = _impulse_train(rng, n, 400.0 * heavy, sr, amp=0.12)
    fry = U.bandpass(fry[:, None], 2000.0, 9000.0, sr, order=2)[:, 0]
    hiss = rng.standard_normal(n).astype(np.float32) * 0.02
    hiss = U.bandpass(hiss[:, None], 500.0, 8000.0, sr, order=2)[:, 0]
    return (bed + fry + hiss).astype(np.float32)


@register
class AVinylNoise(Effect):
    eid = "a_vinyl_noise"
    label = "Vinyl Surface"
    kind = "audio"
    desc = "Record surface noise: crackle clicks, big ringing pops, frying micro-crackle, turntable rumble, and groove wear."
    PARAMS = (
        Param("crackle", "Crackle Density", "float", 8.0, 0.0, 60.0, unit="/s",
              desc="Average crackle clicks per second.", group="Noise", iscale=True),
        Param("crackle_db", "Crackle Level", "float", -32.0, -70.0, -12.0, unit="dB",
              desc="Peak level of typical crackle clicks.", group="Noise"),
        Param("pops", "Pop Rate", "float", 5.0, 0.0, 60.0, unit="/min",
              desc="Big scratch pops per minute (with low ringing).", group="Damage", iscale=True),
        Param("pops_db", "Pop Level", "float", -18.0, -50.0, -6.0, unit="dB",
              desc="Peak level of big pops.", group="Damage"),
        Param("frying_db", "Frying Level", "float", -58.0, -80.0, -30.0, unit="dB",
              desc="Dense micro-crackle 'frying bacon' bed.", group="Noise"),
        Param("rumble_db", "Rumble Level", "float", -50.0, -80.0, -24.0, unit="dB",
              desc="Turntable bearing rumble below 35 Hz.", group="Noise"),
        Param("wear", "Groove Wear", "float", 0.2, 0.0, 1.0,
              desc="Master wear: raises all noise and adds 3–8 kHz worn-groove hiss.", group="Damage", iscale=True),
        Param("stereo_width", "Stereo Width", "float", 0.0, 0.0, 1.0,
              desc="Spreads crackle, pops and frying across the stereo field; 0 keeps them coherent in the center like a mono cartridge (original behavior).", group="Noise"),
        Param("warp_thump", "Warp Thump", "float", 0.0, 0.0, 1.0,
              desc="Warped record: soft once-per-revolution low thump with a slight level dip as the stylus rides the warp.", group="Damage", iscale=True),
        Param("warp_rpm", "Warp Speed", "enum", "33", choices=("33", "45", "78"),
              desc="Rotation speed setting the warp-thump rate (same convention as a_vinyl_wow).", group="Damage"),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        sr = ctx.sr
        wear = self.v["wear"]
        wear_gain = U.db_to_lin(8.0 * wear)  # up to +8 dB with wear
        width = self.v["stereo_width"] if ch >= 2 else 0.0
        bed = np.zeros((n, ch), np.float32)

        if self.v["crackle"] > 0:
            g = stream(ctx.seed, f"{self.key}:crackle")
            lvl = U.db_to_lin(self.v["crackle_db"]) * wear_gain
            # two click flavors: short/bright and mid/duller
            i1 = _impulse_train(g, n, self.v["crackle"] * 0.6, sr, amp=lvl)
            i2 = _impulse_train(g, n, self.v["crackle"] * 0.4, sr, amp=lvl * 1.3)
            if width <= 0:
                t1 = U.bandpass(i1[:, None], 2500.0, 9000.0, sr, order=2)[:, 0]
                t2 = U.bandpass(i2[:, None], 900.0, 4000.0, sr, order=2)[:, 0]
                c = (t1 + t2) * 3.0  # bandpass eats impulse energy; restore
                bed += c[:, None]
            else:
                gp = stream(ctx.seed, f"{self.key}:cpan")
                t1 = U.bandpass(_pan_spread(gp, i1, ch, width), 2500.0, 9000.0, sr, order=2)
                t2 = U.bandpass(_pan_spread(gp, i2, ch, width), 900.0, 4000.0, sr, order=2)
                bed += (t1 + t2) * 3.0

        if self.v["pops"] > 0:
            g = stream(ctx.seed, f"{self.key}:pops")
            gp = stream(ctx.seed, f"{self.key}:poppan") if width > 0 else None
            lvl = U.db_to_lin(self.v["pops_db"]) * wear_gain
            times = U.event_times(g, self.v["pops"], n / sr, min_gap_s=0.4)
            for t0 in times:
                f0 = g.uniform(200.0, 900.0)
                length = int(sr * g.uniform(0.015, 0.05))
                t = np.arange(length) / sr
                ring = np.sin(2 * np.pi * f0 * t) * np.exp(-t / g.uniform(0.004, 0.012))
                click = np.zeros(length)
                click[: max(int(sr * 0.0006), 4)] = g.uniform(0.7, 1.0)
                pop = (click + 0.8 * ring) * lvl * g.uniform(0.5, 1.0)
                if gp is None:
                    U.add_at(bed, pop.astype(np.float32), int(t0 * sr))
                else:
                    a = (gp.uniform(-width, width) + 1.0) * (np.pi / 4.0)
                    w2 = np.sqrt(2.0) * np.array([np.cos(a), np.sin(a)], np.float32)[:ch]
                    U.add_at(bed, pop.astype(np.float32)[:, None] * w2[None, :], int(t0 * sr))

        fry_lvl = U.db_to_lin(self.v["frying_db"]) * wear_gain
        if fry_lvl > 1e-6:
            g = stream(ctx.seed, f"{self.key}:fry")
            fry_imp = _impulse_train(g, n, 500.0, sr, amp=1.0)
            if width <= 0:
                fry = U.bandpass(fry_imp[:, None], 2000.0, 10000.0, sr, order=2)[:, 0]
                fry *= fry_lvl / (U.rms(fry) + 1e-12) * 0.15
                bed += fry[:, None]
            else:
                gp = stream(ctx.seed, f"{self.key}:frypan")
                fry = U.bandpass(_pan_spread(gp, fry_imp, ch, width), 2000.0, 10000.0, sr, order=2)
                fry *= fry_lvl / (U.rms(fry) + 1e-12) * 0.15
                bed += fry

        rum_lvl = U.db_to_lin(self.v["rumble_db"]) * wear_gain
        if rum_lvl > 1e-6:
            g = stream(ctx.seed, f"{self.key}:rumble")
            r = g.standard_normal(n).astype(np.float32)
            r = U.lowpass(r[:, None], 35.0, sr, order=4)[:, 0]
            r *= rum_lvl / (U.rms(r) + 1e-12)
            bed += r[:, None]

        if wear > 0:
            g = stream(ctx.seed, f"{self.key}:wearhiss")
            cols = [g.standard_normal(n).astype(np.float32) for _ in range(ch)]
            h = np.stack(cols, axis=1)
            h = U.bandpass(h, 3000.0, 8000.0, sr, order=2)
            h *= U.db_to_lin(-58.0 + 14.0 * wear) / (U.rms(h) + 1e-12)
            bed += h

        out = audio + bed

        warp = self.v["warp_thump"]
        if warp > 0 and n > 16:
            g = stream(ctx.seed, f"{self.key}:warp")
            f0 = {"33": 0.555, "45": 0.75, "78": 1.3}[self.v["warp_rpm"]]
            period = 1.0 / f0
            off = g.uniform(0.0, period)
            t = np.arange(n) / sr
            # slight level dip once per rev as the stylus climbs the warp
            ph = ((t + off) * f0) % 1.0
            dip_w = 0.10 + 0.06 * g.uniform()
            dip = np.exp(-0.5 * ((ph - 0.5) / dip_w) ** 2)
            out = out * (1.0 - 0.20 * warp * dip)[:, None].astype(np.float32)
            # soft low 'whomp' at the crest of each revolution
            k = 0
            while True:
                tk = (k + 0.5) * period - off
                k += 1
                if tk >= n / sr:
                    break
                L = int(0.11 * sr)
                tt = np.arange(L) / sr
                fk = g.uniform(38.0, 55.0)
                th = np.sin(2 * np.pi * fk * tt + g.uniform(0, 2 * np.pi)) * np.exp(-tt / 0.045)
                th += 0.4 * np.sin(2 * np.pi * 2.1 * fk * tt) * np.exp(-tt / 0.02)
                th = U.lowpass(th[:, None].astype(np.float32), 150.0, sr, order=2)[:, 0]
                amp = warp * U.db_to_lin(-22.0) * g.uniform(0.8, 1.15)
                if tk >= 0:
                    U.add_at(out, (th * amp / (np.max(np.abs(th)) + 1e-9)).astype(np.float32),
                             int(tk * sr))

        return U.peak_guard(out)


@register
class AVinylWow(Effect):
    eid = "a_vinyl_wow"
    label = "Vinyl Wow"
    kind = "audio"
    desc = "Off-center pressing: once-per-revolution pitch wow at the rotation rate plus slow drift."
    _RPM_HZ = {"33": 0.555, "45": 0.75, "78": 1.3}
    PARAMS = (
        Param("rpm", "Speed", "enum", "33", choices=("33", "45", "78"),
              desc="Record speed; sets the once-per-rev wow rate.", group="Pitch"),
        Param("depth_cents", "Depth", "float", 8.0, 0.0, 60.0, unit="cents",
              desc="Peak pitch deviation from the off-center hole.", group="Pitch", iscale=True),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n = audio.shape[0]
        if n < 16 or self.v["depth_cents"] <= 0:
            return audio
        sr = ctx.sr
        f0 = self._RPM_HZ[self.v["rpm"]]
        g = stream(ctx.seed, f"{self.key}:phase")
        t = np.arange(n) / sr
        ph = g.uniform(0, 2 * np.pi)
        cents = self.v["depth_cents"] * (
            np.sin(2 * np.pi * f0 * t + ph) + 0.3 * np.sin(2 * np.pi * 2 * f0 * t + 2.1 * ph)
        )
        cents += 0.15 * self.v["depth_cents"] * U.control_noise(
            stream(ctx.seed, f"{self.key}:drift"), n, sr, 0.03, 0.12, ctrl_sr=50.0)
        return U.variable_speed(audio, np.exp2(cents / 1200.0))


@register
class ANeedle(Effect):
    eid = "a_needle"
    label = "Needle Events"
    kind = "audio"
    desc = "Needle drops, lifts, and the classic skipping-record repeat."
    PARAMS = (
        Param("drop_at_start", "Drop at Start", "bool", False,
              desc="Thump and ~0.4 s of groove noise before the music fades in.", group="Damage"),
        Param("lift_at_end", "Lift at End", "bool", False,
              desc="Music fades to groove noise and a lift click at the end.", group="Damage"),
        Param("skip_rate", "Skip Rate", "float", 0.0, 0.0, 12.0, unit="/min",
              desc="Skipping-record events per minute (a chunk repeats 1–2 times).", group="Damage", iscale=True),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        sr = ctx.sr
        x = audio.astype(np.float32).copy()

        if self.v["skip_rate"] > 0 and n > sr:
            g = stream(ctx.seed, f"{self.key}:skips")
            times = U.event_times(g, self.v["skip_rate"], n / sr, min_gap_s=2.0)
            if len(times):
                pieces = []
                cursor = 0
                fade = max(int(sr * 0.002), 16)
                for t0 in times:
                    s = int(t0 * sr)
                    L = int(g.uniform(0.2, 0.9) * sr)
                    reps = int(g.integers(1, 3))  # 1–2 extra plays
                    if s <= cursor or s + L >= n:
                        continue
                    pieces.append(x[cursor : s + L])
                    for _ in range(reps):
                        pieces.append(x[s : s + L])
                    cursor = s + L
                pieces.append(x[cursor:])
                if len(pieces) > 1:
                    y = np.concatenate(pieces, axis=0)
                    # crossfade + tick at every splice boundary
                    offs = np.cumsum([p.shape[0] for p in pieces])[:-1]
                    ramp = np.linspace(0, 1, fade, dtype=np.float32)[:, None]
                    for o in offs:
                        if fade < o < y.shape[0] - fade:
                            y[o - fade : o] *= ramp[::-1]
                            y[o : o + fade] *= ramp
                            tick = (g.uniform(0.1, 0.25) * np.array([1, -0.6, 0.3], np.float32))
                            U.add_at(y, tick, int(o))
                    x = y[:n] if y.shape[0] >= n else np.vstack(
                        [y, np.zeros((n - y.shape[0], ch), np.float32)])

        def thump(gen: np.random.Generator) -> np.ndarray:
            f0 = gen.uniform(60.0, 120.0)
            L = int(sr * 0.12)
            t = np.arange(L) / sr
            body = np.sin(2 * np.pi * f0 * t) * np.exp(-t / 0.03)
            scuff = gen.standard_normal(L).astype(np.float64) * np.exp(-t / 0.008) * 0.4
            k = U.bandpass((body + scuff)[:, None].astype(np.float32), 40.0, 900.0, sr, order=2)[:, 0]
            return (k * 0.5 / (np.max(np.abs(k)) + 1e-9)).astype(np.float32)

        if self.v["drop_at_start"] and n > sr:
            g = stream(ctx.seed, f"{self.key}:drop")
            head = int(0.6 * sr)
            env = np.ones(n, np.float32)
            env[: int(0.25 * sr)] = 0.0
            ramp = np.linspace(0, 1, int(0.3 * sr), dtype=np.float32)
            env[int(0.25 * sr) : int(0.25 * sr) + len(ramp)] = ramp
            x *= env[:, None]
            groove = _groove_noise(g, head, sr, heavy=1.2) * 0.5
            fadeout = np.linspace(1, 0, head, dtype=np.float32) ** 0.6
            U.add_at(x, (groove * fadeout).astype(np.float32), 0)
            U.add_at(x, thump(g), int(0.04 * sr))

        if self.v["lift_at_end"] and n > sr:
            g = stream(ctx.seed, f"{self.key}:lift")
            tail = int(0.5 * sr)
            env = np.ones(n, np.float32)
            env[-tail:] = np.linspace(1, 0, tail, dtype=np.float32)
            x *= env[:, None]
            groove = _groove_noise(g, tail, sr, heavy=0.8) * 0.35
            U.add_at(x, (groove * np.linspace(0.2, 1, tail, dtype=np.float32)).astype(np.float32), n - tail)
            U.add_at(x, thump(g) * 0.6, n - int(0.09 * sr))

        return U.peak_guard(x)
