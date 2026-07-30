"""Transmission-path interference: long-distance (DX/skip) reception where the
whole signal breathes, heterodyne interference gratings, jamming bars and
studio-transmitter-link hits.

These sit between the studio and the set - they corrupt whatever signal is
already on the frame, so they stack naturally under `ntsc`, `vhs` and `crt`.
Horizontal quantities follow the same 704-sample active-line model as
`analog.py`; everything stochastic draws from ctx.noise tracks or per-frame
ctx.frame_rng streams so renders reproduce exactly from their seed.
"""

from __future__ import annotations

import cv2
import numpy as np

from ...engine.graph import Context, Effect, Param, register
from .analog import (
    BASE_H,
    BASE_W,
    _luma,
    _remap_x,
    _resize,
    _shift_int_x,
    _xgrid,
    _ygrid,
)


# ═══════════════════════════════════════════════════════════════════════
# 1. DX / skip reception
# ═══════════════════════════════════════════════════════════════════════
@register
class RFDX(Effect):
    eid = "rf_dx"
    label = "DX Reception"
    kind = "frame"
    desc = ("A station from much too far away: the signal fades in and out of the noise "
            "floor, a co-channel ghost of the program drifts and rolls underneath, and "
            "venetian-blind carrier-beat bars breathe with the fading.")
    PARAMS = (
        Param("fade_depth", "Fade Depth", "float", 0.45, 0.0, 1.0, group="Fading", iscale=True,
              desc="How deep the slow signal fades dip; at the bottom of a fade the picture "
                   "washes toward gray and the snow floor rises to meet it."),
        Param("fade_rate", "Fade Rate", "float", 0.08, 0.01, 0.6, unit="Hz", group="Fading",
              desc="How quickly the propagation breathes; skip fades are slow, aircraft "
                   "flutter is fast."),
        Param("noise_floor", "Noise Floor", "float", 0.5, 0.0, 1.0, group="Fading", iscale=True,
              desc="Strength of the ever-present snow that surfaces whenever the signal drops."),
        Param("co_channel", "Co-Channel Ghost", "float", 0.3, 0.0, 1.0, group="Co-Channel", iscale=True,
              desc="A second transmitter on the same channel: a delayed ghost of the program "
                   "drifting over the picture, rolling vertically when its sync wins."),
        Param("co_delay_s", "Ghost Delay", "float", 1.2, 0.4, 6.0, unit="s", group="Co-Channel",
              desc="How far behind the program the co-channel ghost runs."),
        Param("venetian", "Venetian Bars", "float", 0.25, 0.0, 1.0, group="Interference", iscale=True,
              desc="Fine horizontal venetian-blind bars from the two carriers beating, "
                   "drifting vertically and swelling as the fade deepens."),
    )

    def prepare(self, ctx: Context) -> None:
        self._buf: np.ndarray | None = None
        self._filled = 0
        self._fps = max(ctx.fps, 1.0)
        # ghost vertical roll: when the interfering sync loses lock, integrate
        # a roll velocity so the ghost picture rolls smoothly across frames
        gate = ctx.noise.smooth(f"{self.key}:roll", 0.08)
        vel = np.clip(gate - 0.25, 0.0, None) * 1.6              # rolls/s
        self._gvel = vel.astype(np.float32)
        self._groll = np.cumsum(vel) / self._fps                 # in frames of H

    def _push(self, frame: np.ndarray) -> None:
        H, W = frame.shape[:2]
        bh, bw = max(H // 4, 8), max(W // 4, 8)
        if self._buf is None:
            cap = max(int(round(self.v["co_delay_s"] * self._fps)) + 4, 8)
            self._buf = np.empty((cap, bh, bw, 3), np.uint8)
            self._filled = 0
        small = cv2.resize(frame, (self._buf.shape[2], self._buf.shape[1]),
                           interpolation=cv2.INTER_AREA)
        self._buf[self._filled % self._buf.shape[0]] = np.clip(small * 255.0, 0, 255).astype(np.uint8)
        self._filled += 1

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        v = self.v
        H, W = frame.shape[:2]
        fi = min(ctx.fi_out, ctx.noise.n - 1)
        t = ctx.fi_out / max(ctx.fps, 1.0)

        co = v["co_channel"]
        if co > 0.0:
            self._push(frame)

        # ── propagation fading ─────────────────────────────────────────
        f1 = ctx.noise.smooth(f"{self.key}:fade", v["fade_rate"])[fi]
        f2 = ctx.noise.smooth(f"{self.key}:fade2", v["fade_rate"] * 2.6)[fi]
        u = float(np.clip(0.5 + 0.5 * (0.75 * f1 + 0.45 * f2), 0.0, 1.0))
        deep = (1.0 - u) ** 2.0
        fade = v["fade_depth"] * deep

        # ── co-channel ghost (it is RF too: it rides under the noise) ──
        if co > 0.0 and self._buf is not None and self._filled > 1:
            cap = self._buf.shape[0]
            delay = min(int(round(v["co_delay_s"] * max(ctx.fps, 1.0))), self._filled - 1, cap - 1)
            idx = (self._filled - 1 - delay) % cap
            ghost = self._buf[idx].astype(np.float32) * (1.0 / 255.0)
            # the interferer fades on its own path
            gf = ctx.noise.smooth(f"{self.key}:gfade", v["fade_rate"] * 0.8)[fi]
            ga = co * (0.10 + 0.42 * float(np.clip(0.5 + 0.5 * gf, 0.0, 1.0)) ** 1.6)
            ga = min(ga + 0.25 * co * deep, 0.5)          # our fade lets it through
            if ga > 0.01:
                roll = int((self._groll[fi] % 1.0) * self._buf.shape[1])
                if roll:
                    ghost = np.roll(ghost, roll, axis=0)
                    # while its sync is lost the ghost's h-hold slips too:
                    # lines shear sideways and wrap around
                    vel = float(self._gvel[fi])
                    if vel > 0.05:
                        bh_, bw_ = ghost.shape[:2]
                        slip = (np.arange(bh_, dtype=np.float32)
                                * (vel * 0.9 * bw_ / bh_)).astype(np.int64) % bw_
                        cols = (np.arange(bw_, dtype=np.int64)[None, :] + slip[:, None]) % bw_
                        ghost = ghost[np.arange(bh_)[:, None], cols]
                ghost = cv2.resize(ghost, (W, H), interpolation=cv2.INTER_LINEAR)
                dx = ctx.noise.smooth(f"{self.key}:gdrift", 0.05)[fi] * 0.06 * W
                ghost = _shift_int_x(ghost, int(round(dx)))
                frame = frame * (1.0 - ga) + ghost * ga

        # ── the fade itself: gain drops toward the AGC'd gray haze ─────
        if fade > 0.0:
            y = _luma(np.ascontiguousarray(frame))[..., None]
            frame += (y - frame) * (0.65 * fade)          # chroma dies first
            frame = (frame - 0.5) * (1.0 - 0.52 * fade) + 0.5 + 0.02 * fade

        # ── noise floor surfaces as the signal drops ───────────────────
        nf = v["noise_floor"]
        if nf > 0.0:
            amp = nf * (0.05 + 0.85 * fade) * 0.17
            if amp > 0.004:
                g = ctx.frame_rng(f"{self.key}:snow")
                nz = g.standard_normal((H, max(W // 2, 8)), dtype=np.float32)
                frame += _resize(nz, W, H, cv2.INTER_LINEAR)[..., None] * amp

        # ── venetian-blind carrier beat ────────────────────────────────
        vb = v["venetian"]
        if vb > 0.0:
            per = 11.0 * H / BASE_H
            vph = ctx.noise.drift(f"{self.key}:vph", 0.1)[fi] * 2.0
            rows = np.arange(H, dtype=np.float32)
            bars = np.sin(2.0 * np.pi * (rows / per + 0.7 * t + vph))
            vamp = vb * (0.05 + 0.16 * deep)
            frame *= (1.0 + vamp * bars)[:, None, None]

        return np.clip(frame, 0.0, 1.0, out=frame)


# ═══════════════════════════════════════════════════════════════════════
# 2. Heterodyne interference gratings
# ═══════════════════════════════════════════════════════════════════════
@register
class Herringbone(Effect):
    eid = "herringbone"
    label = "RF Herringbone"
    kind = "frame"
    desc = ("Heterodyne beat between the picture carrier and an interfering signal: fine "
            "drifting gratings - the classic herringbone weave, plain diagonal bars, or "
            "broad rolling hum bands with a slow sideways wiggle.")
    PARAMS = (
        Param("amount", "Amount", "float", 0.35, 0.0, 1.0, group="Pattern", iscale=True,
              desc="Visibility of the interference pattern over the picture."),
        Param("pattern", "Pattern", "enum", "herringbone",
              choices=("herringbone", "diagonal_bars", "rolling_hum"), group="Pattern",
              desc="Herringbone chevron weave (adjacent-channel beat), straight diagonal "
                   "bars (CW carrier), or broad rolling hum bands (power-line beat)."),
        Param("wavelength", "Wavelength", "float", 7.0, 3.0, 40.0, unit="px", group="Pattern",
              desc="Stripe pitch of the beat pattern; hum bands run about ten times wider."),
        Param("drift", "Drift", "float", 0.6, 0.0, 4.0, unit="Hz", group="Motion",
              desc="How fast the pattern crawls - an unlocked beat never sits still."),
    )

    def prepare(self, ctx: Context) -> None:
        pass

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        v = self.v
        a = v["amount"]
        if a <= 0.0:
            return frame
        H, W = frame.shape[:2]
        fi = min(ctx.fi_out, ctx.noise.n - 1)
        t = ctx.fi_out / max(ctx.fps, 1.0)
        sx, sy = W / BASE_W, H / BASE_H
        lam = max(v["wavelength"] * sx, 2.5)
        wob = ctx.noise.drift(f"{self.key}:wob", 0.2)[fi]
        tph = 2.0 * np.pi * v["drift"] * t + 1.2 * wob
        pat = v["pattern"]

        if pat == "rolling_hum":
            per = lam * 10.0 * (sy / max(sx, 1e-6))
            rows = np.arange(H, dtype=np.float32)
            base = 2.0 * np.pi * (rows / max(per, 8.0)) - tph
            # heterodyne wiggle: the band edges lean left and right as they roll
            lean = 0.55 * np.sin(2.0 * np.pi * _xgrid(H, W) / (W * 0.55) + 1.7 * t)
            ph = base[:, None] + lean
            depth = a * 0.10
        elif pat == "diagonal_bars":
            ph = (2.0 * np.pi / lam) * (_xgrid(H, W) + 0.6 * _ygrid(H, W)) + tph
            depth = a * 0.065
        else:  # herringbone: stripe slope flips every couple of lines - a weave
            rows = np.arange(H, dtype=np.float32)
            zig = np.abs((rows * 0.5) % 2.0 - 1.0)
            ph = (2.0 * np.pi / lam) * _xgrid(H, W) + (3.1 * zig)[:, None] + tph
            depth = a * 0.075

        p = np.sin(ph).astype(np.float32, copy=False)
        frame += depth * p[..., None]
        return np.clip(frame, 0.0, 1.0, out=frame)


# ═══════════════════════════════════════════════════════════════════════
# 3. Jamming bars
# ═══════════════════════════════════════════════════════════════════════
@register
class JamBars(Effect):
    eid = "jam_bars"
    label = "Jamming Bars"
    kind = "frame"
    desc = ("Deliberate interference stomping on the channel: broad dark bars roll through "
            "the picture, colors smear inside them and the sync tears sideways where a bar "
            "sits - the pirate-TV / jammed-broadcast look.")
    PARAMS = (
        Param("amount", "Amount", "float", 0.35, 0.0, 1.0, group="Bars", iscale=True,
              desc="Strength of the rolling bars; low values read as a nuisance, high as denial."),
        Param("bar_size", "Bar Size", "float", 0.45, 0.12, 1.0, group="Bars",
              desc="Bar period as a fraction of the picture height."),
        Param("roll_speed", "Roll Speed", "float", 0.35, -2.0, 2.0, unit="bars/s", group="Bars",
              desc="How fast the bars roll; negative rolls them downward."),
        Param("tear", "Sync Tear", "float", 0.3, 0.0, 1.0, group="Tearing", iscale=True,
              desc="Horizontal shear where a bar crosses - the jammer wrestling the sync."),
    )

    def prepare(self, ctx: Context) -> None:
        pass

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        v = self.v
        a = v["amount"]
        if a <= 0.0:
            return frame
        H, W = frame.shape[:2]
        fi = min(ctx.fi_out, ctx.noise.n - 1)
        t = ctx.fi_out / max(ctx.fps, 1.0)
        rows = np.arange(H, dtype=np.float32)
        wob = ctx.noise.smooth(f"{self.key}:wob", 0.3)[fi]
        ph = rows / (v["bar_size"] * H) - (v["roll_speed"] + 0.06 * wob) * t
        prof = (0.5 - 0.5 * np.cos(2.0 * np.pi * ph)).astype(np.float32)

        # darken and color-corrupt inside the bar
        chug = np.sin(2.0 * np.pi * 0.9 * t + 1.7)
        gains = np.empty((H, 3), np.float32)
        dark = 1.0 - a * 0.55 * prof ** 1.5
        gains[:, 0] = dark * (1.0 - 0.20 * a * prof * max(chug, 0.0))
        gains[:, 1] = dark
        gains[:, 2] = dark * (1.0 - 0.20 * a * prof * max(-chug, 0.0))
        frame *= gains[:, None, :]

        tear = v["tear"]
        if tear > 0.0:
            edge = np.clip(prof - 0.60, 0.0, None) * 2.5
            if float(edge.max()) > 0.02:
                g = ctx.frame_rng(f"{self.key}:tear")
                jag = g.standard_normal(H).astype(np.float32)
                jag = np.convolve(jag, np.ones(3, np.float32) / 3.0, mode="same")
                coh = np.sin(2.0 * np.pi * (rows / (0.3 * H) + 1.3 * t))
                off = tear * edge ** 1.5 * (0.035 * W * coh + 0.028 * W * jag)
                frame = _remap_x(frame, off.astype(np.float32))

        return np.clip(frame, 0.0, 1.0, out=frame)


# ═══════════════════════════════════════════════════════════════════════
# 4. Microwave-link hits
# ═══════════════════════════════════════════════════════════════════════
@register
class MicrowaveHit(Effect):
    eid = "microwave_hit"
    label = "Microwave Hit"
    kind = "frame"
    desc = ("The studio-transmitter link taking a hit: for a frame or four the picture "
            "shatters into displaced strips of analog hash, then snaps back like nothing "
            "happened - the mark of remote trucks and rain fade.")
    PARAMS = (
        Param("rate", "Hit Rate", "float", 2.0, 0.0, 30.0, unit="/min", group="Events", iscale=True,
              desc="How often the link takes a hit; each one lasts one to four frames."),
        Param("strength", "Strength", "float", 0.85, 0.0, 1.0, group="Events",
              desc="How completely a hit shreds the picture."),
    )

    def prepare(self, ctx: Context) -> None:
        n, fps = ctx.n_frames, max(ctx.fps, 1.0)
        env = np.zeros(n, np.float32)
        rate = self.v["rate"]
        if rate > 0.0:
            ev = ctx.noise.events(f"{self.key}:hit", rate / 60.0, min_gap_s=1.5)
            g = ctx.rng(f"{self.key}:dur")
            steps = np.array([1.0, 0.95, 0.65, 0.4], np.float32)
            for idx in np.nonzero(ev)[0]:
                dur = int(g.integers(1, 5))
                amp = 0.65 + 0.35 * g.random()
                hi = min(idx + dur, n)
                env[idx:hi] = np.maximum(env[idx:hi], amp * steps[: hi - idx])
        self._env = env

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        v = self.v
        fi = min(ctx.fi_out, len(self._env) - 1)
        e = float(self._env[fi]) * v["strength"]
        if e <= 0.02:
            return frame
        H, W = frame.shape[:2]
        sy = H / BASE_H
        g = ctx.frame_rng(f"{self.key}:mw")

        # strips shear apart: coarse per-band displacement, most bands hit
        bh = max(int((8.0 + 26.0 * g.random()) * sy), 4)
        nb = H // bh + 1
        boff = g.standard_normal(nb).astype(np.float32) * (0.22 * W * e)
        boff *= (g.random(nb) < 0.72).astype(np.float32)
        off = np.repeat(boff, bh)[:H]
        off += g.standard_normal(H).astype(np.float32) * (1.5 * e)
        frame = _remap_x(frame, off)

        # blocky analog hash floods the displaced strips
        hz = g.random((max(H // 16, 8), max(W // 14, 8)), dtype=np.float32)
        hash_y = _resize(hz, W, H, cv2.INTER_NEAREST)
        hash_y = (0.18 + 0.64 * np.floor(hash_y * 5.0) / 4.0).astype(np.float32)
        fine = g.standard_normal((H, max(W // 3, 8)), dtype=np.float32)
        hash_y += _resize(fine, W, H, cv2.INTER_LINEAR) * 0.10
        m = np.clip(np.abs(np.repeat(boff, bh)[:H]) / (0.10 * W), 0.0, 0.85) * e
        m = m.astype(np.float32)[:, None, None]
        frame = frame * (1.0 - m) + hash_y[..., None] * m

        # sync loses its grip entirely on the hardest hits
        if e > 0.5:
            frame = np.roll(frame, int(H * 0.10 * g.random() * e), axis=0)

        return np.clip(frame, 0.0, 1.0, out=frame)
