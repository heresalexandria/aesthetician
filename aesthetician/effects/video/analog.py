"""Analog video-signal effects: composite NTSC/PAL color encoding, the VHS
record/playback stack, VCR transport events, RF/antenna reception and the
rainbow tape-junk static between recordings.

Signal model
------------
Horizontal frequencies are expressed in MHz against an effective sampling
rate of ~13.4 MHz for a 704-sample active line (BT.601-ish), scaled by the
actual frame width so bandwidths keep their physical meaning at any
resolution. The color subcarrier sits on the same scale (3.58 / 4.43 MHz),
which puts the NTSC subcarrier dot pitch at ~3.7 px on a 704-wide frame.
Vertical (line-count) quantities are specified against a 480-line active
frame and scaled by the actual height.

Everything stochastic draws from ctx.noise temporal tracks or per-frame
ctx.frame_rng streams so a render is exactly reproducible from its seed.
"""

from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np
from scipy import signal as sps

from ...engine.color import luma, rgb_to_yiq, yiq_to_rgb
from ...engine.graph import Context, Effect, Event, Param, register
from ...engine.rng import stream

# ── horizontal-frequency model ─────────────────────────────────────────
BASE_FS_MHZ = 13.4      # effective sample rate of a 704-sample active line
BASE_W = 704.0
BASE_H = 480.0
FSC_MHZ = {"ntsc": 3.579545, "pal": 4.43361875}


def _cut(bw_mhz: float, width: int) -> float:
    """Normalized cutoff (fraction of Nyquist) for a horizontal FIR."""
    fs = BASE_FS_MHZ * (width / BASE_W)
    return float(np.clip(bw_mhz / (fs * 0.5), 0.008, 0.985))


# (H,W,3) @ (3,3) matmuls hit numpy's slow stacked path; one flat BLAS call
# per conversion is ~15x faster on full frames.
def _to_yiq(rgb: np.ndarray) -> np.ndarray:
    h, w = rgb.shape[:2]
    return rgb_to_yiq(rgb.reshape(-1, 3)).reshape(h, w, 3)


def _to_rgb(yiq: np.ndarray) -> np.ndarray:
    h, w = yiq.shape[:2]
    return yiq_to_rgb(yiq.reshape(-1, 3)).reshape(h, w, 3)


def _luma(rgb: np.ndarray) -> np.ndarray:
    h, w = rgb.shape[:2]
    return luma(rgb.reshape(-1, 3)).reshape(h, w)


@lru_cache(maxsize=256)
def _lp_kernel_c(cut: float) -> np.ndarray:
    taps = int(np.clip(round(3.6 / max(cut, 0.008)), 13, 129)) | 1
    return sps.firwin(taps, cut).astype(np.float32).reshape(1, -1)


def _lp_kernel(cut: float) -> np.ndarray:
    return _lp_kernel_c(round(float(cut), 4))


@lru_cache(maxsize=64)
def _bp_kernel_c(f1: float, f2: float) -> np.ndarray:
    taps = int(np.clip(round(5.0 / max(f2 - f1, 0.02)), 21, 129)) | 1
    return sps.firwin(taps, [f1, f2], pass_zero=False).astype(np.float32).reshape(1, -1)


def _bp_kernel(f1: float, f2: float) -> np.ndarray:
    f1 = max(round(float(f1), 4), 0.005)
    f2 = min(round(float(f2), 4), 0.99)
    return _bp_kernel_c(f1, f2)


@lru_cache(maxsize=32)
def _ring_kernel_c(cut: float, taps: int) -> np.ndarray:
    # Truncated (boxcar-windowed) lowpass: the Gibbs ripple is exactly the
    # ringing a cheap analog aperture-corrector produces.
    return sps.firwin(taps, cut, window="boxcar").astype(np.float32).reshape(1, -1)


def _filt_x(img: np.ndarray, k: np.ndarray) -> np.ndarray:
    """FIR along width; k is a (1, N) kernel. Works on HxW or HxWxC."""
    return cv2.filter2D(img, -1, k, borderType=cv2.BORDER_REFLECT)


def _filt_x_narrow(img: np.ndarray, cut: float) -> np.ndarray:
    """Very low cutoffs (long kernels) via downsample → short FIR → upsample.

    A fraction of the cost of the direct FIR, and physically the right model
    for color-under chroma, which really was subsampled on tape.
    """
    if cut >= 0.12:
        return _filt_x(img, _lp_kernel(cut))
    h, w = img.shape[:2]
    ds = int(np.clip(round(0.3 / cut), 2, 6))
    small = cv2.resize(img, (max(w // ds, 8), h), interpolation=cv2.INTER_AREA)
    small = _filt_x(small, _lp_kernel(min(cut * ds, 0.5)))
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)


def _filt_y(img: np.ndarray, k: np.ndarray) -> np.ndarray:
    return cv2.filter2D(img, -1, k.reshape(-1, 1), borderType=cv2.BORDER_REFLECT)


_VKERN_CHROMA = np.array([[0.27], [0.46], [0.27]], np.float32)  # ~2-line color-under smear


@lru_cache(maxsize=8)
def _xgrid(h: int, w: int) -> np.ndarray:
    return np.broadcast_to(np.arange(w, dtype=np.float32), (h, w)).copy()


@lru_cache(maxsize=8)
def _ygrid(h: int, w: int) -> np.ndarray:
    return np.broadcast_to(np.arange(h, dtype=np.float32)[:, None], (h, w)).copy()


def _shift_int_x(img: np.ndarray, s: int) -> np.ndarray:
    """Shift along width by whole pixels, replicating edges (no wrap)."""
    if s == 0:
        return img
    w = img.shape[1]
    s = int(np.clip(s, -w + 1, w - 1))
    out = np.empty_like(img)
    if s > 0:
        out[:, s:] = img[:, : w - s]
        out[:, :s] = img[:, :1]
    else:
        out[:, :s] = img[:, -s:]
        out[:, s:] = img[:, -1:]
    return out


def _shift_x(img: np.ndarray, px: float) -> np.ndarray:
    """Subpixel horizontal shift (positive = right), edge-replicated."""
    if abs(px) < 1e-3:
        return img
    i0 = int(np.floor(px))
    f = px - i0
    a = _shift_int_x(img, i0)
    if f < 1e-3:
        return a if a is not img else img.copy()
    return a * (1.0 - f) + _shift_int_x(img, i0 + 1) * f


def _remap_x(frame: np.ndarray, off: np.ndarray) -> np.ndarray:
    """Per-row horizontal displacement via one cv2.remap call."""
    h, w = frame.shape[:2]
    map_x = _xgrid(h, w) + off[:, None]
    return cv2.remap(frame, map_x, _ygrid(h, w), cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_REPLICATE)


def _resize(img: np.ndarray, w: int, h: int, interp: int) -> np.ndarray:
    return cv2.resize(img, (w, h), interpolation=interp)


def _streak_noise(g: np.random.Generator, h: int, w: int, coarse_x: int = 3) -> np.ndarray:
    """Horizontally smeared uniform noise in [0,1] - the tracking-band fill."""
    gw = max(w // coarse_x, 8)
    nz = g.random((h, gw), dtype=np.float32)
    nz = _resize(nz, w, h, cv2.INTER_LINEAR)
    rowg = 0.55 + 0.9 * g.random((h, 1), dtype=np.float32)  # per-line gain streaks
    return np.clip(nz * rowg, 0.0, 1.0)


def _tracking_storm(frame: np.ndarray, g: np.random.Generator, amount: float) -> np.ndarray:
    """Full-frame mistracking: shredded lines, noise bands, desaturation.

    Shared by vcr_transport (start/pause/random glitches). amount in 0..1.
    """
    h, w = frame.shape[:2]
    a = float(np.clip(amount, 0.0, 1.0))
    if a <= 0.0:
        return frame
    # per-row shred: every row jitters a little, random runs of rows a lot
    off = g.standard_normal(h).astype(np.float32) * (2.0 + 10.0 * a) * (w / BASE_W)
    runsel = g.random(h).astype(np.float32)
    runsel = _resize(runsel.reshape(-1, 1), 1, h, cv2.INTER_LINEAR)[:, 0]  # correlate rows
    shred_rows = runsel < (0.12 + 0.45 * a)
    big = g.standard_normal(h).astype(np.float32) * (0.16 * w * a)
    off = np.where(shred_rows, off + big, off)
    frame = _remap_x(frame, off)
    # noise wash on the shredded rows plus a rolling heavy band
    m = np.where(shred_rows, np.clip(0.25 + 0.75 * g.random(h).astype(np.float32), 0, 1) * 0.75 * a, 0.15 * a)
    nz = _streak_noise(g, h, w)
    y = _luma(frame)[..., None]
    frame += (y - frame) * (0.6 * a)                     # chroma dies under mistracking
    mm = m.astype(np.float32)[:, None, None]
    frame = frame * (1.0 - mm) + nz[..., None] * mm
    return frame


# ═══════════════════════════════════════════════════════════════════════
# 1. Composite NTSC / PAL
# ═══════════════════════════════════════════════════════════════════════
@register
class CompositeColor(Effect):
    eid = "ntsc"
    label = "Composite NTSC/PAL"
    kind = "frame"
    desc = ("Composite color encoding and receiver decode: bandlimited luma/chroma, "
            "cross-color rainbows on fine detail, crawling subcarrier dots and hue instability.")
    PARAMS = (
        Param("system", "System", "enum", "ntsc", choices=("ntsc", "pal"), group="System",
              desc="NTSC (never-twice-same-color hue jitter) or PAL (Hanover-bar line averaging)."),
        Param("luma_bw", "Luma Bandwidth", "float", 4.2, 1.5, 6.6, unit="MHz", group="Bandwidth",
              desc="Brightness detail the channel keeps; 4.2 is broadcast NTSC, lower is softer."),
        Param("chroma_bw", "Chroma Bandwidth", "float", 1.3, 0.3, 2.2, unit="MHz", group="Bandwidth",
              desc="Color detail bandwidth; color always smears wider than brightness."),
        Param("comb", "Comb Filter", "float", 0.2, 0.0, 1.0, group="Decoder",
              desc="0 = notch decoder (rainbow swirls on detail), 1 = 1-line comb (dot crawl at color edges)."),
        Param("rainbow", "Cross-Color", "float", 0.35, 0.0, 1.0, group="Decoder", iscale=True,
              desc="Fine luma detail leaking into the color decoder as shimmering rainbow swirls."),
        Param("dot_crawl", "Dot Crawl", "float", 0.25, 0.0, 1.0, group="Decoder", iscale=True,
              desc="Residual subcarrier dots on colored areas that crawl upward frame by frame."),
        Param("phase_error", "Hue Error", "float", 0.0, -45.0, 45.0, unit="°", group="Phase",
              desc="Static hue rotation, as from a mis-set tint knob or phase drift."),
        Param("phase_noise", "Hue Instability", "float", 0.8, 0.0, 12.0, unit="°", group="Phase", iscale=True,
              desc="Random per-scanline hue wobble - the classic NTSC tint shimmer (ignored for PAL)."),
        Param("fringing", "Chroma Fringing", "float", 1.0, -8.0, 8.0, unit="px", group="Phase",
              desc="Color delayed against brightness so hues smear off edges to the right (negative = left)."),
        Param("comb_mode", "Comb Mode", "enum", "legacy_notch",
              choices=("legacy_notch", "comb_1line", "comb_2d_adaptive"), group="Decoder",
              desc="Y/C separator model: the legacy notch/comb blend (driven by the Comb Filter slider), "
                   "a forced 1-line comb, or a late-80s 2D adaptive comb that combs only where adjacent "
                   "lines agree - far fewer hanging dots."),
        Param("diff_phase", "Differential Phase", "float", 0.0, 0.0, 8.0, unit="°", group="Phase", iscale=True,
              desc="Hue tied to brightness: highlights rotate the subcarrier so bright faces drift "
                   "orange-red, the classic overdriven-transmitter error."),
        Param("chroma_agc", "Chroma AGC Breathing", "float", 0.0, 0.0, 1.0, group="Decoder", iscale=True,
              desc="The receiver's color AGC hunting: saturation slowly pumps up and down over seconds."),
        Param("setup_level", "Setup Pedestal", "float", 0.0, 0.0, 0.1, group="Levels",
              desc="NTSC 7.5-IRE setup: black rides a gray pedestal and everything above compresses to fit."),
        Param("cc_line", "Line-21 Captions", "bool", False, group="Levels",
              desc="Line-21 closed-caption data on the top visible line: a run-in burst and two white "
                   "dash clusters flickering with the data, as overscan would reveal."),
        Param("sync_jitter", "Sync Jitter", "float", 0.0, 0.0, 1.0, group="Timing", iscale=True,
              desc="Sync separator pulled by picture content: lines under bright content trigger late, "
                   "so bright pictures bend to the right."),
        Param("strength", "Strength", "float", 1.0, 0.0, 1.0, group="Mix", iscale=True,
              desc="Master blend of the composite look against the clean image."),
    )

    def prepare(self, ctx: Context) -> None:
        self._W = -1
        self._H = -1
        self._build(max(ctx.width, int(BASE_W)), ctx.height)

    def _build(self, W: int, H: int) -> None:
        if W == self._W and H == self._H:
            return
        self._W, self._H = W, H
        system = self.v["system"]
        fsc_n = _cut(FSC_MHZ[system], W)              # fraction of Nyquist
        cyc_per_px = 0.5 * fsc_n
        ph = 2.0 * np.pi * cyc_per_px * np.arange(W, dtype=np.float32)
        self._cosx = np.cos(ph)[None, :].astype(np.float32)
        self._sinx = np.sin(ph)[None, :].astype(np.float32)
        self._fsc_n = fsc_n
        yy = np.arange(H)
        if system == "ntsc":
            # 227.5 cycles/line → 180° per line; 525 lines → 180° per frame
            self._step_l, self._step_f = np.pi, np.pi
        else:
            # 283.75 cycles/line → 270° per line; 625 lines → 270° per frame
            self._step_l, self._step_f = 1.5 * np.pi, 1.5 * np.pi
        self._rows = yy.astype(np.float32)
        self._svec = np.where(yy % 2 == 0, 1.0, -1.0).astype(np.float32)[:, None]  # PAL V-switch

    def _carrier(self, fi: int) -> tuple[np.ndarray, np.ndarray]:
        rowph = self._step_l * self._rows + self._step_f * fi
        if self.v["system"] == "ntsc":
            s = np.where((self._rows.astype(np.int64) + fi) % 2 == 0, 1.0, -1.0).astype(np.float32)[:, None]
            return self._cosx * s, self._sinx * s
        co = np.cos(rowph).astype(np.float32)[:, None]
        so = np.sin(rowph).astype(np.float32)[:, None]
        return (self._cosx * co - self._sinx * so,
                self._sinx * co + self._cosx * so)

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        v = self.v
        if v["strength"] <= 0.0:
            return frame
        H, W0 = frame.shape[:2]
        # the composite trip needs the subcarrier below Nyquist: narrow frames
        # (previews) are resampled up to a full 704-sample active line
        W = max(W0, int(BASE_W))
        work = frame if W == W0 else cv2.resize(frame, (W, H), interpolation=cv2.INTER_LINEAR)
        self._build(W, H)
        fi = ctx.fi_out
        pal = v["system"] == "pal"

        yiq = _to_yiq(work)
        y = np.ascontiguousarray(yiq[..., 0])
        i_ = np.ascontiguousarray(yiq[..., 1])
        q = np.ascontiguousarray(yiq[..., 2])

        # ── transmitter: bandlimit and modulate onto the subcarrier ────
        y = _filt_x(y, _lp_kernel(_cut(v["luma_bw"], W)))
        i_ = _filt_x_narrow(i_, _cut(v["chroma_bw"], W))
        q = _filt_x_narrow(q, _cut(v["chroma_bw"] * 0.46, W))
        cos_c, sin_c = self._carrier(fi)
        q_enc = q * self._svec[:, :1] if pal else q
        chroma_sig = i_ * cos_c + q_enc * sin_c
        comp = y + chroma_sig

        # ── receiver: luma/chroma separation ───────────────────────────
        cbw_n = _cut(max(v["chroma_bw"], 0.5) * 1.15, W)
        k_bp = _bp_kernel(self._fsc_n - cbw_n, self._fsc_n + cbw_n)
        c = float(v["comb"])

        bp = _filt_x(comp, k_bp)
        y_notch = comp - bp
        # rainbow: the bandpassed composite still contains HF luma → feeding
        # more of it to the demodulator turns fine detail into false color
        din = chroma_sig + v["rainbow"] * (bp - chroma_sig)
        mode = v["comb_mode"]
        if mode == "comb_1line" or (mode == "legacy_notch" and c > 0.0):
            if mode == "comb_1line":
                c = 1.0
            prev = np.empty_like(comp)
            prev[1:] = comp[:-1]
            prev[0] = comp[1]
            din_comb = 0.5 * (comp - prev)          # phase flips line-to-line
            y_comb = comp - _filt_x(din_comb, k_bp)  # hanging dots at color edges
            y_dec = y_notch * (1.0 - c) + y_comb * c
            din = din * (1.0 - c) + din_comb * c
        elif mode == "comb_2d_adaptive":
            # 2-line comb where the picture is vertically correlated, notch
            # elsewhere - the late-80s "digital comb" that killed hanging dots
            prev = np.empty_like(comp)
            prev[1:] = comp[:-1]
            prev[0] = comp[1]
            nxt = np.empty_like(comp)
            nxt[:-1] = comp[1:]
            nxt[-1] = comp[-2]
            din_2d = 0.5 * comp - 0.25 * (prev + nxt)
            y_comb = comp - _filt_x(din_2d, k_bp)
            # lines one above/below share subcarrier phase, so their difference
            # is pure vertical picture change: comb only where it is small
            verr = _filt_x(np.abs(prev - nxt), _lp_kernel(0.10))
            wmap = 1.0 - np.clip((verr - 0.035) / 0.11, 0.0, 1.0)
            wmap *= wmap
            y_dec = y_notch * (1.0 - wmap) + y_comb * wmap
            din = din * (1.0 - wmap) + din_2d * wmap
        else:
            y_dec = y_notch
        if v["dot_crawl"] > 0.0:
            y_dec = y_dec + (0.55 * v["dot_crawl"]) * chroma_sig
        if v["setup_level"] > 0.0:
            # pedestal: black lifted to setup, white pinned - headroom compresses
            y_dec = v["setup_level"] + y_dec * (1.0 - v["setup_level"])

        # ── chroma demodulation ────────────────────────────────────────
        dem = np.empty((H, W, 2), np.float32)
        dem[..., 0] = din * cos_c
        dem[..., 1] = din * sin_c
        dem = _filt_x(dem, _lp_kernel(_cut(max(v["chroma_bw"] * 0.5, 0.35), W))) * 2.0
        i_r = dem[..., 0]
        q_r = dem[..., 1] * self._svec if pal else dem[..., 1]

        # ── phase errors ───────────────────────────────────────────────
        th0 = np.deg2rad(v["phase_error"])
        if pal:
            if abs(th0) > 1e-4:
                # V-switch turns a static phase error into ±θ on alternating
                # lines; the delay line mostly averages it away (Hanover bars)
                th = th0 * self._svec
                ci, si = np.cos(th), np.sin(th)
                i_r, q_r = i_r * ci - q_r * si, i_r * si + q_r * ci
            pr_i = np.empty_like(i_r); pr_i[1:] = i_r[:-1]; pr_i[0] = i_r[1]
            pr_q = np.empty_like(q_r); pr_q[1:] = q_r[:-1]; pr_q[0] = q_r[1]
            i_r = 0.55 * i_r + 0.45 * pr_i           # imperfect delay line →
            q_r = 0.55 * q_r + 0.45 * pr_q           # faint Hanover banding
        elif abs(th0) > 1e-4 or v["phase_noise"] > 0.0:
            th = np.full(H, th0, np.float32)
            if v["phase_noise"] > 0.0:
                g = ctx.frame_rng(f"{self.key}:hue")
                th = th + np.deg2rad(v["phase_noise"]) * g.standard_normal(H).astype(np.float32)
            ci, si = np.cos(th)[:, None], np.sin(th)[:, None]
            i_r, q_r = i_r * ci - q_r * si, i_r * si + q_r * ci

        if v["diff_phase"] > 0.0:
            # differential phase: subcarrier phase advances with beam current,
            # so the hue of a color depends on how bright it sits
            ylv = np.clip(_filt_x_narrow(y_dec, _cut(0.6, W)), 0.0, 1.0)
            th_dp = np.deg2rad(v["diff_phase"] * 3.2) * ylv * ylv
            ci, si = np.cos(th_dp), np.sin(th_dp)
            i_r, q_r = i_r * ci - q_r * si, i_r * si + q_r * ci

        if v["chroma_agc"] > 0.0:
            fi_n = min(fi, ctx.noise.n - 1)
            pump = 1.0 + 0.32 * v["chroma_agc"] * ctx.noise.smooth(f"{self.key}:cagc", 0.3)[fi_n]
            i_r = i_r * pump
            q_r = q_r * pump

        if v["cc_line"]:
            self._draw_cc_line(y_dec, i_r, q_r, ctx)

        if abs(v["fringing"]) > 1e-3:
            px = v["fringing"] * (W / BASE_W)
            i_r = _shift_x(i_r, px)
            q_r = _shift_x(q_r, px)

        out = np.empty_like(yiq)
        out[..., 0] = y_dec
        out[..., 1] = i_r
        out[..., 2] = q_r
        rgb = _to_rgb(out)

        if v["sync_jitter"] > 0.0:
            # the sync separator's slice level rides on line energy: a bright
            # line delays the next H-sync, pulling that line to the right
            rowy = y_dec.mean(axis=1)
            drive = np.empty_like(rowy)
            drive[1:] = rowy[:-1]
            drive[0] = rowy[0]
            drive = np.convolve(drive, np.array([0.5, 0.3, 0.2], np.float32), mode="same")
            pull = np.clip(drive - 0.18, 0.0, None) ** 1.4
            g = ctx.frame_rng(f"{self.key}:sync")
            wob = np.abs(g.standard_normal(H).astype(np.float32))
            offj = v["sync_jitter"] * (W / BASE_W) * pull * (6.5 + 1.2 * wob)
            if float(np.max(offj)) > 0.05:
                rgb = _remap_x(rgb, offj)

        if W != W0:
            rgb = cv2.resize(rgb, (W0, H), interpolation=cv2.INTER_AREA)
        s = v["strength"]
        if s < 1.0:
            rgb = frame * (1.0 - s) + rgb * s
        return np.clip(rgb, 0.0, 1.0, out=rgb)

    def _draw_cc_line(self, y_dec: np.ndarray, i_r: np.ndarray, q_r: np.ndarray,
                      ctx: Context) -> None:
        """Line-21 caption data on the first visible line: run-in clock burst
        plus two data-byte dash clusters whose bits flicker frame to frame."""
        H, W = y_dec.shape
        sy = H / BASE_H
        r0 = max(int(round(1.0 * sy)), 1)
        hh = max(int(round(1.3 * sy)), 1)
        r1 = min(r0 + hh, H)
        g = ctx.frame_rng(f"{self.key}:cc21")
        row = np.full(W, 0.03, np.float32)

        def dash(c0: float, c1: float, val: float) -> None:
            row[int(c0 * W):max(int(c1 * W), int(c0 * W) + 1)] = val

        for k in range(7):                     # run-in clock burst
            x = 0.085 + 0.047 * k
            dash(x, x + 0.020, 0.66)
        bits = g.random(16) < 0.5              # two data bytes, live bits
        for k in range(8):
            if bits[k]:
                dash(0.455 + 0.0295 * k, 0.455 + 0.0295 * k + 0.018, 0.78)
        for k in range(8):
            if bits[8 + k]:
                dash(0.715 + 0.0295 * k, 0.715 + 0.0295 * k + 0.018, 0.78)
        row = np.convolve(row, np.array([0.18, 0.64, 0.18], np.float32), mode="same")
        y_dec[r0:r1] = y_dec[r0:r1] * 0.10 + row[None, :] * 0.90
        i_r[r0:r1] *= 0.12                     # data line carries no chroma
        q_r[r0:r1] *= 0.12


# ═══════════════════════════════════════════════════════════════════════
# 2. VHS record/playback stack
# ═══════════════════════════════════════════════════════════════════════
@register
class VHS(Effect):
    eid = "vhs"
    label = "VHS"
    kind = "frame"
    desc = ("The full VHS record/playback chain: color-under bandwidth loss, VCR edge "
            "enhancement, tape noise, dropouts, head switching, time-base wobble and tracking errors.")
    _MODE = {"sp": (1.00, 1.0, 1.0), "lp": (0.82, 1.7, 1.5), "ep": (0.65, 2.6, 2.3)}

    PARAMS = (
        Param("mode", "Tape Speed", "enum", "sp", choices=("sp", "lp", "ep"), group="Bandwidth",
              desc="SP is the cleanest; LP and EP squeeze more hours onto the tape at the cost of detail and noise."),
        Param("luma_bw", "Luma Bandwidth", "float", 3.0, 1.2, 5.2, unit="MHz", group="Bandwidth",
              desc="Brightness detail surviving the tape - 3 MHz is standard VHS softness."),
        Param("chroma_bw", "Chroma Bandwidth", "float", 0.4, 0.1, 1.2, unit="MHz", group="Bandwidth",
              desc="Color-under bandwidth; VHS color is drastically softer than brightness and smears down 2 lines."),
        Param("chroma_delay", "Chroma Delay", "float", 1.2, -6.0, 8.0, unit="px", group="Bandwidth",
              desc="Color arriving late so hues hang off the right side of edges."),
        Param("sharpen", "Edge Enhance", "float", 0.35, 0.0, 1.5, group="Playback", iscale=True,
              desc="The VCR's aperture correction: crisp overshoot halos and faint ringing after vertical edges."),
        Param("luma_noise", "Luma Noise", "float", 0.35, 0.0, 1.0, group="Noise", iscale=True,
              desc="Streaky horizontal tape noise shimmering over the brightness channel."),
        Param("chroma_noise", "Chroma Noise", "float", 0.35, 0.0, 1.0, group="Noise", iscale=True,
              desc="Coarse drifting color blotches from the noisy color-under channel."),
        Param("head_switch", "Head Switching", "float", 0.7, 0.0, 1.0, group="Playback", iscale=True,
              desc="The bent lines and noise strip at the very bottom of the frame where the video heads swap."),
        Param("dropouts", "Dropouts", "float", 1.5, 0.0, 60.0, unit="events/s", group="Damage", iscale=True,
              desc="Bright comet-tailed streaks where oxide flaked off the tape."),
        Param("dropout_burst", "Dropout Bursting", "float", 0.3, 0.0, 1.0, group="Damage",
              desc="Clusters dropouts into angry bursts, as on a creased or worn stretch of tape."),
        Param("time_base_error", "Time-Base Error", "float", 0.35, 0.0, 1.0, group="Timing", iscale=True,
              desc="Per-line horizontal wobble - edges swim and breathe without a TBC."),
        Param("flagging", "Flagging", "float", 0.25, 0.0, 1.0, group="Timing", iscale=True,
              desc="The top of the picture skewing and waving - classic bent-top playback."),
        Param("jitter_v", "Vertical Jitter", "float", 0.15, 0.0, 1.0, group="Timing", iscale=True,
              desc="Occasional one-or-two line vertical bounce of the whole frame."),
        Param("tracking_error", "Tracking Error", "float", 0.1, 0.0, 1.0, group="Tracking", iscale=True,
              desc="Rolling bands of shredded, noisy lines; 0 is a locked tape, 1 a constant storm."),
        Param("generation", "Generation", "int", 1, 1, 5, group="Tape",
              desc="Copy-of-a-copy count; each dub adds softness, noise and level drift."),
        Param("azimuth_error", "Azimuth Error", "float", 0.0, 0.0, 1.0, group="Tracking", iscale=True,
              desc="Head tilted against the recording: HF detail dies and a faint woven herringbone "
                   "shimmer rides wherever the picture is detailed."),
        Param("head_beat", "Head Beat", "float", 0.0, 0.0, 1.0, group="Playback", iscale=True,
              desc="The two video heads disagreeing on chroma phase: color saturation and hue pulse "
                   "on a ~2-frame beat, most visible on flat saturated areas."),
        Param("fm_sparkle", "FM Sparkle", "float", 0.0, 0.0, 1.0, group="Noise", iscale=True,
              desc="FM demodulator click noise: tiny bright/dark ticks clustered on hard bright edges "
                   "instead of spread evenly over the frame."),
        Param("white_clip", "White Clip", "float", 1.0, 0.85, 1.0, group="Levels",
              desc="VHS record white clip: highlights shoulder off softly into a ceiling below full white."),
        Param("black_crush", "Black Crush", "float", 0.0, 0.0, 0.1, group="Levels", iscale=True,
              desc="Record black level set low: shadow detail crushes into the floor with a soft knee."),
        Param("skew_tear", "Skew Tear", "float", 0.0, 0.0, 1.0, group="Timing", iscale=True,
              desc="Worn transport tension: occasional tear bands near the top where a handful of "
                   "lines shear hard sideways for a frame or two."),
        Param("interchange", "Interchange Error", "float", 0.0, 0.0, 1.0, group="Tracking", iscale=True,
              desc="Recorded on someone else's deck: chroma sits a couple of lines low, the head-switch "
                   "point rides up into the picture and the whole frame carries a slight static skew."),
    )

    def prepare(self, ctx: Context) -> None:
        self._schedule_dropouts(ctx)
        self._schedule_storms(ctx)
        self._schedule_tears(ctx)
        W = ctx.width
        self._k_gen = _lp_kernel(_cut(2.6, W))
        self._genc_cut = _cut(0.5, W)
        # aperture corrector: truncated FIR → overshoot + trailing ripple
        self._k_sharp = _ring_kernel_c(round(_cut(1.7, W), 4), 15)

    # ── damage helpers ─────────────────────────────────────────────────
    def _schedule_dropouts(self, ctx: Context) -> None:
        """Work out every dropout before the first frame is touched.

        The same draws in the same order from the same per-frame generator, so
        the picture does not move by a level - the only thing that changes is
        that the list now exists somewhere you can read it. Deciding this a
        frame at a time inside `process` meant nobody could ask where the
        dropouts were, count them, or move one.
        """
        self._dropouts: dict[int, list[tuple]] = {}
        v = self.v
        rate = v["dropouts"] * self._MODE[v["mode"]][2]
        if rate <= 0.0:
            return
        W, H = ctx.width, ctx.height
        sx = W / BASE_W
        # The burst multiplier rides the clip's own track: a bursty stretch of
        # tape is bursty in every window that shows it.
        burst_track = ctx.clip_noise.onef(f"{self.key}:doburst", 1.2)
        af0 = ctx.abs_frame(0)
        for fi in range(ctx.n_frames):
            bi = min(af0 + fi, ctx.clip_noise.n - 1)
            burst = 1.0 + v["dropout_burst"] * 7.0 * max(0.0, burst_track[bi]) ** 2
            g = ctx.frame_rng(f"{self.key}:dropouts", fi)
            n = int(g.poisson(rate / max(ctx.fps, 1.0) * burst))
            if n <= 0:
                continue
            evs = []
            for i in range(min(n, 40)):
                L = int((20.0 + 280.0 * g.random() ** 2) * sx)
                L = max(min(L, W - 2), 6)
                x0 = int(g.integers(0, W - L))
                r = int(g.integers(0, H))
                dark = bool(g.random() < 0.12)
                rows = 1 if g.random() < 0.65 else 2
                # The id is minted on the base schedule, before any edit, and it
                # travels with the instance from then on. Editing one dropout
                # must not renumber its neighbours, or every edit after the
                # first would land on the wrong instance.
                evs.append({"id": f"{self.key}:dropout:{ctx.abs_frame(fi)}:{i}",
                            "x": x0, "row": r, "L": L, "dark": dark, "rows": rows})
            self._dropouts[fi] = evs
        self._apply_event_edits(ctx)

    def _schedule_storms(self, ctx: Context) -> None:
        """Tracking storms as instances: the runs the gate track produces.

        The render used to compute activation per frame - a slow gate crossing a
        threshold the knob sets, times a per-frame flicker - which made storms
        real but unaddressable: episodes with a start, a length and a peak that
        existed nowhere as a list. The same arithmetic over the whole track at
        once yields the same numbers frame for frame, segmented into runs. Each
        run is an instance with an id; edits move, scale, stretch, remove or add
        segments; and the per-frame activation the render reads is rasterised
        from the final list. Untouched, it reproduces the old values exactly.
        """
        n = ctx.n_frames
        v = self.v
        self._storms: list[dict] = []
        # Not vectorised, and that is the point. The per-frame original mixed
        # widths mid-expression - float32 track scalars, a float() promotion at
        # the clip, the power in float64, the flicker multiply back in whatever
        # the running numpy promotes to - and both a float32 and a float64
        # vectorisation of it land a last-bit away often enough to move single
        # pixels. Running the literal expressions per frame IS the original
        # computation, whatever numpy's promotion rules are this year; a python
        # loop over the frame count costs microseconds per frame in prepare.
        self._track_act = np.zeros(n, np.float64)
        tr = v["tracking_error"]
        if tr > 0.0:
            # Planned over the WHOLE clip, on the clip's own noise, whatever
            # window this render covers. A schedule drawn on the window's tracks
            # normalises to the window: a three-second preview then plans a
            # different tape than the export, and an edit naming an exported
            # storm's id does nothing on screen - which is exactly the bug this
            # replaces. `f0` is a clip frame from here on.
            N = ctx.clip_frames
            gate_track = ctx.clip_noise.smooth(f"{self.key}:trgate", 0.35)
            flick_track = ctx.clip_noise.white(f"{self.key}:trflick")
            acts = np.zeros(N, np.float64)
            for fi in range(min(N, ctx.clip_noise.n)):
                gate = 0.5 + 0.5 * gate_track[fi]
                act = float(np.clip((gate - (0.92 - tr)) / 0.30, 0.0, 1.0)) ** 1.3
                act *= 0.55 + 0.45 * abs(flick_track[fi])
                if act > 0.02:
                    acts[fi] = float(act)
            f = 0
            while f < N:
                if acts[f] <= 0.0:
                    f += 1
                    continue
                f1 = f
                while f1 < N and acts[f1] > 0.0:
                    f1 += 1
                self._storms.append({
                    "id": f"{self.key}:tracking_storm:{f}:0",
                    "f0": f, "seg": acts[f:f1].copy(),
                })
                f = f1
        fps = max(ctx.fps, 1.0)
        for e in ctx.event_edits:
            if e.get("effect", self.key) != self.key or e.get("kind") != "tracking_storm":
                continue
            op = e.get("op")
            if op == "add":
                f0 = int(round(float(e.get("t", 0.0)) * fps))     # clip frame
                d = e.get("detail") or {}
                length = max(int(round(float(d.get("dur_s", 0.6)) * fps)), 2)
                peak = float(np.clip(float(d.get("intensity", 0.8)), 0.05, 1.0))
                # The flicker comes from the op, not the seed, so an added storm
                # keeps its exact character across a reseed.
                g = stream(0, f"edit:{e.get('id') or f0}")
                u = np.linspace(-1.0, 1.0, length)
                env = (0.5 + 0.5 * np.cos(np.pi * u)) * peak
                env *= (0.55 + 0.45 * g.random(length))
                if 0 <= f0 < ctx.clip_frames:
                    self._storms.append({"id": e.get("id") or f"edit:add:{f0}",
                                         "f0": f0, "seg": env})
                continue
            hit = next((x for x in self._storms if x["id"] == e.get("id")), None)
            if hit is None:
                continue
            if op == "remove":
                self._storms.remove(hit)
            elif op == "move":
                nf0 = int(round(float(e.get("t", hit["f0"] / fps)) * fps))
                if 0 <= nf0 < ctx.clip_frames:
                    hit["f0"] = nf0
                else:
                    self._storms.remove(hit)
            elif op == "tune":
                d = e.get("detail") or {}
                if "intensity" in d:
                    peak = float(hit["seg"].max()) or 1.0
                    hit["seg"] = np.clip(hit["seg"] * (float(d["intensity"]) / peak), 0.0, 1.0)
                if "dur_s" in d:
                    length = max(int(round(float(d["dur_s"]) * fps)), 2)
                    old = hit["seg"]
                    xs = np.linspace(0, len(old) - 1, length)
                    hit["seg"] = np.interp(xs, np.arange(len(old)), old)
        # Rasterise only the slice of each storm that falls inside this render's
        # window; the instance itself stays whole and clip-timed.
        af0 = ctx.abs_frame(0)
        for st in self._storms:
            lo = st["f0"] - af0
            hi = lo + len(st["seg"])
            a, b = max(lo, 0), min(hi, n)
            if b > a:
                self._track_act[a:b] = np.maximum(self._track_act[a:b],
                                                  st["seg"][a - lo: b - lo])

    def _schedule_tears(self, ctx: Context) -> None:
        """Skew tears as instances. Already events at heart - a Poisson mask
        with a hard shear drawn per hit - so this only lifts the mask into a
        list. The geometry generator stays keyed to the frame the tear was
        minted on, which is what lets a moved tear keep its own shape.
        """
        n = ctx.n_frames
        self._tears: list[dict] = []
        st = self.v["skew_tear"]
        if st > 0.0:
            # Clip-wide, like the storms: `fi` is a clip frame, and every window
            # of the same clip agrees about where the tears are.
            ev = ctx.clip_noise.events(f"{self.key}:skewev", per_second=0.12 + 0.55 * st, min_gap_s=1.2)
            for idx in np.nonzero(ev[: ctx.clip_frames] > 0.0)[0]:
                self._tears.append({"id": f"{self.key}:skew_tear:{int(idx)}:0",
                                    "fi": int(idx), "key_fi": int(idx), "e": 1.0})
        fps = max(ctx.fps, 1.0)
        for e in ctx.event_edits:
            if e.get("effect", self.key) != self.key or e.get("kind") != "skew_tear":
                continue
            op = e.get("op")
            if op == "add":
                fi = int(round(float(e.get("t", 0.0)) * fps))      # clip frame
                if 0 <= fi < ctx.clip_frames:
                    d = e.get("detail") or {}
                    self._tears.append({"id": e.get("id") or f"edit:add:{fi}", "fi": fi,
                                        "key_fi": fi,
                                        "e": float(np.clip(float(d.get("intensity", 1.0)), 0.05, 2.0))})
                continue
            hit = next((x for x in self._tears if x["id"] == e.get("id")), None)
            if hit is None:
                continue
            if op == "remove":
                self._tears.remove(hit)
            elif op == "move":
                nfi = int(round(float(e.get("t", hit["fi"] / fps)) * fps))
                if 0 <= nfi < ctx.clip_frames:
                    hit["fi"] = nfi          # key_fi stays: the tear keeps its shape
                else:
                    self._tears.remove(hit)
            elif op == "tune":
                d = e.get("detail") or {}
                if "intensity" in d:
                    hit["e"] = float(np.clip(float(d["intensity"]), 0.05, 2.0))
        # frame -> (strength, geometry key): the tear frame at full strength and
        # the frame after it relaxing back at half, exactly as the render did.
        # Window-local render map. The geometry key is the clip frame the tear
        # was minted on, translated to a window-relative index so frame_rng's
        # absolute keying lands back on the mint frame from any window.
        af0 = ctx.abs_frame(0)
        self._tear_map: dict[int, tuple[float, int]] = {}
        occupied = {x["fi"] for x in self._tears}
        for t in self._tears:
            lf = t["fi"] - af0
            if 0 <= lf < n:
                self._tear_map[lf] = (t["e"], t["key_fi"] - af0)
            if 0 <= lf + 1 < n and (t["fi"] + 1) not in occupied:
                self._tear_map.setdefault(lf + 1, (0.5 * t["e"], t["key_fi"] - af0))

    def _apply_event_edits(self, ctx: Context) -> None:
        """The user's diff on top of the seeded schedule.

        Ops address instances by the id minted at draw time, so they survive
        each other; an op whose id no longer exists (the seed changed under it)
        is skipped rather than grabbed at, because silently editing a different
        dropout would be worse than editing none.
        """
        edits = [e for e in ctx.event_edits
                 if e.get("effect", self.key) == self.key and e.get("kind", "dropout") == "dropout"]
        if not edits:
            return
        fps = max(ctx.fps, 1.0)
        by_id = {ev["id"]: (fi, ev) for fi, evs in self._dropouts.items() for ev in evs}
        n_add = 0
        for e in edits:
            op = e.get("op")
            if op == "add":
                fi = ctx.frame_of(float(e.get("t", 0.0)))
                if not (0 <= fi < ctx.n_frames):
                    continue
                d = e.get("detail") or {}
                W, H = ctx.width, ctx.height
                # Anything unspecified is derived from the op itself, not from
                # the render seed, so an added dropout stays put when the seed
                # changes - it is yours, not the tape's.
                g = stream(0, f"edit:{e.get('id') or n_add}:{e.get('t')}")
                L = int(d.get("length_px", 20 + 280 * g.random() ** 2 * (W / BASE_W)))
                L = max(min(int(L), W - 2), 6)
                x0 = int(d.get("x", g.integers(0, max(W - L, 1))))
                row = int(d.get("row", g.integers(0, H)))
                self._dropouts.setdefault(fi, []).append({
                    "id": e.get("id") or f"edit:add:{n_add}",
                    "x": min(max(x0, 0), W - L), "row": min(max(row, 0), H - 1), "L": L,
                    "dark": d.get("polarity", "bright") == "dark",
                    "rows": int(d.get("rows", 1))})
                n_add += 1
                continue
            hit = by_id.get(e.get("id"))
            if hit is None:
                continue
            fi, ev = hit
            if op == "remove":
                self._dropouts[fi].remove(ev)
                if not self._dropouts[fi]:
                    del self._dropouts[fi]
            elif op == "move":
                nfi = ctx.frame_of(float(e.get("t", fi / fps)))
                self._dropouts[fi].remove(ev)
                if not self._dropouts[fi]:
                    del self._dropouts[fi]
                if 0 <= nfi < ctx.n_frames:
                    self._dropouts.setdefault(nfi, []).append(ev)
            elif op == "tune":
                d = e.get("detail") or {}
                if "row" in d: ev["row"] = min(max(int(d["row"]), 0), ctx.height - 1)
                if "x" in d: ev["x"] = min(max(int(d["x"]), 0), ctx.width - 2)
                if "length_px" in d: ev["L"] = max(min(int(d["length_px"]), ctx.width - ev["x"]), 6)
                if "rows" in d: ev["rows"] = 1 if int(d["rows"]) <= 1 else 2
                if "polarity" in d: ev["dark"] = d["polarity"] == "dark"

    def _apply_dropouts(self, y: np.ndarray, ctx: Context) -> None:
        evs = getattr(self, "_dropouts", {}).get(min(ctx.fi_out, ctx.noise.n - 1))
        if not evs:
            return
        H, W = y.shape
        for ev in evs:
            x0, r, L, dark, rows = ev["x"], ev["row"], ev["L"], ev["dark"], ev["rows"]
            tail = np.exp(-np.arange(L, dtype=np.float32) / (L * 0.38))
            tail[:2] *= (0.55, 0.9)[: min(2, L)]
            for dr in range(rows):
                rr = min(r + dr, H - 1)
                wgt = tail if dr == 0 else tail * 0.5
                seg = y[rr, x0:x0 + L]
                if dark:
                    # oxide gone, no compensator: the FM carrier just dies
                    seg -= seg * (0.92 * wgt)
                else:
                    # dropout compensator: holds the LINE ABOVE for the span,
                    # with a hot switch fringe at the leading edge - so the
                    # streak is a displaced copy of the picture, not flat white
                    above = y[rr - 1, x0:x0 + L] if rr > 0 else np.full(L, 0.82, np.float32)
                    fill = above + (0.20 + 0.42 * tail) * (1.0 - above)
                    seg += (fill - seg) * wgt
                    if dr == 0:
                        hp = min(max(2, L // 24), L)
                        seg[:hp] = np.maximum(seg[:hp], 0.94)

    def events(self, ctx: Context) -> list[Event]:
        fps = max(ctx.fps, 1.0)
        out: list[Event] = []
        for fi, evs in sorted(getattr(self, "_dropouts", {}).items()):
            for ev in evs:
                out.append(Event(
                    t=ctx.t0 + fi / fps,
                    dur=1.0 / fps,          # a dropout is one frame's streak
                    kind="dropout",
                    detail={"id": ev["id"], "row": ev["row"], "x": ev["x"],
                            "length_px": ev["L"], "rows": ev["rows"],
                            "polarity": "dark" if ev["dark"] else "bright"},
                ))
        # Instances are clip-timed, but a render reports only what it will
        # actually produce: the ones its window can see. The whole-clip list is
        # what you get by asking with whole-clip options, which is what the
        # timeline does.
        w0 = ctx.t0
        w1 = ctx.t0 + ctx.n_frames / fps
        for st in getattr(self, "_storms", []):
            t, dur = st["f0"] / fps, len(st["seg"]) / fps
            if t < w1 and t + dur > w0:
                out.append(Event(
                    t=t, dur=dur, kind="tracking_storm",
                    detail={"id": st["id"], "intensity": round(float(st["seg"].max()), 3)},
                ))
        for tr in getattr(self, "_tears", []):
            t = tr["fi"] / fps
            if w0 <= t < w1:
                out.append(Event(
                    t=t, dur=2.0 / fps,     # the tear and its relaxing frame
                    kind="skew_tear",
                    detail={"id": tr["id"], "intensity": round(tr["e"], 3)},
                ))
        return sorted(out, key=lambda e: e.t)

    def _geometry_offsets(self, H: int, W: int, ctx: Context) -> tuple[np.ndarray, tuple]:
        """Per-row x displacement for TBE + flagging + head switch + tracking."""
        v = self.v
        fi = min(ctx.fi_out, ctx.noise.n - 1)
        sx, sy = W / BASE_W, H / BASE_H
        off = np.zeros(H, np.float32)
        rows = np.arange(H, dtype=np.float32)

        ic = v["interchange"]
        if ic > 0.0:
            # someone else's deck: a constant mild skew across the whole frame
            off += ic * 4.0 * sx * (rows / max(H - 1, 1) - 0.5)

        tbe = v["time_base_error"]
        if tbe > 0.0:
            g = ctx.frame_rng(f"{self.key}:tbe")
            ph = ctx.noise.drift(f"{self.key}:tbe_ph", 0.15)[fi] * 2.0 + fi * 0.013
            amp_d = 0.6 + 0.4 * ctx.noise.smooth(f"{self.key}:tbe_amp", 0.4)[fi]
            wave = np.sin(rows * (2.0 * np.pi * 2.3 / H) + ph * 2.0 * np.pi)
            rnd = g.standard_normal(H).astype(np.float32)
            rnd = np.convolve(rnd, np.ones(7, np.float32) / 7.0, mode="same")
            off += tbe * sx * (1.5 * amp_d * wave + 1.1 * rnd)

        flag = v["flagging"]
        if flag > 0.0:
            n_fl = max(int(40 * sy), 8)
            wob = 0.55 + 0.45 * ctx.noise.smooth(f"{self.key}:flag", 0.3)[fi]
            prof = np.clip(1.0 - rows[:n_fl] / n_fl, 0.0, 1.0) ** 2.1
            off[:n_fl] += flag * 16.0 * sx * wob * prof

        st = v["skew_tear"]
        if st > 0.0:
            # The schedule owns the when and the how-hard; the geometry is drawn
            # from the frame the tear was minted on, so a moved tear tears the
            # same way in its new home.
            e, fe = getattr(self, "_tear_map", {}).get(fi, (0.0, fi))
            if e > 0.0:
                ge = ctx.frame_rng(f"{self.key}:skew", fe)   # tear keeps its place
                y0 = int(H * (0.03 + 0.11 * ge.random()))
                bh = max(int((5.0 + 12.0 * ge.random()) * sy), 3)
                y1 = min(y0 + bh, H)
                u = (rows[y0:y1] - y0) / max(y1 - y0 - 1, 1)
                dirn = 1.0 if ge.random() < 0.72 else -1.0
                amp = (0.045 + 0.05 * ge.random()) * W
                gj = ctx.frame_rng(f"{self.key}:skewjit")
                jag = gj.standard_normal(y1 - y0).astype(np.float32)
                # hard shear at the top edge of the band, decaying downward
                off[y0:y1] += e * st * dirn * amp * (1.0 - u) ** 1.35
                off[y0:y1] += e * st * 1.6 * sx * jag

        hs_strip = None
        hs = v["head_switch"]
        if hs > 0.0:
            jit = int(round(1.4 * ctx.noise.white(f"{self.key}:hsjit")[fi]))
            bend = max(int(round(9 * sy)), 4)
            sw = int(np.clip(H - bend + jit, H - int(H * 0.06) - 1, H - 2))
            rise = 0
            if ic > 0.0:
                # interchange: the switch point lands inside the picture
                rise = int(ic * 0.030 * H)
                sw = max(sw - rise, 2)
            ramp = (rows[sw:] - sw) / max(H - sw - 1, 1)
            wob = 0.75 + 0.25 * ctx.noise.smooth(f"{self.key}:hswob", 0.8)[fi]
            off[sw:] += hs * 30.0 * sx * wob * (0.2 + 0.8 * ramp ** 1.7)
            hs_strip = (sw, max(int(round(1.6 * sy)), 2), rise)

        band = None
        tr = v["tracking_error"]
        if tr > 0.0 or len(getattr(self, "_storms", [])):
            # The per-frame activation now comes off the rasterised schedule -
            # identical numbers when nobody has edited, and the edited truth
            # when someone has. `tr` alone no longer gates it: an added storm
            # must land even on a preset whose dial sits at zero.
            act = float(self._track_act[fi]) if fi < len(self._track_act) else 0.0
            if act > 0.02:
                g = ctx.frame_rng(f"{self.key}:track")
                # Clip-indexed for the same reason as the schedule: the band a
                # preview shows at 5.2s must be the band the export has there.
                af = min(ctx.abs_frame(fi), ctx.clip_noise.n - 1)
                bh = (36.0 + 84.0 * (0.5 + 0.5 * ctx.clip_noise.smooth(f"{self.key}:trh", 0.2)[af])) * sy
                speed = H * (0.011 + 0.007 * ctx.clip_noise.smooth(f"{self.key}:trv", 0.1)[af])
                wander = ctx.clip_noise.smooth(f"{self.key}:trpos", 0.5)[af] * 30.0 * sy
                p = (0.31 * H + speed * af + wander) % (H + 2.0 * bh) - bh
                y0, y1 = int(max(0.0, p - bh / 2)), int(min(H, p + bh / 2))
                if y1 - y0 > 2:
                    d = (rows[y0:y1] - p) / (bh * 0.5)
                    prof = (0.5 + 0.5 * np.cos(np.pi * np.clip(d, -1.0, 1.0))).astype(np.float32)
                    shred = g.standard_normal(y1 - y0).astype(np.float32)
                    off[y0:y1] += prof * act * (0.10 * W) * np.clip(shred, -2.2, 2.2)
                    off[y0:y1] += prof * act * 20.0 * sx * ctx.clip_noise.smooth(f"{self.key}:trskew", 0.6)[af]
                    band = (y0, y1, prof, act)
        return off, (hs_strip, band)

    def _paint_head_strip(self, frame: np.ndarray, ctx: Context, sw: int, strip_h: int,
                          rise: int = 0) -> None:
        H, W = frame.shape[:2]
        hs = self.v["head_switch"]
        g = ctx.frame_rng(f"{self.key}:hstrip")
        y0 = max(H - strip_h - rise, 0)
        y1 = min(y0 + strip_h, H)
        nz = _streak_noise(g, strip_h, W, coarse_x=10)
        dash = _resize(g.random((strip_h, max(W // 64, 6)), dtype=np.float32),
                       W, strip_h, cv2.INTER_NEAREST)
        val = 0.12 + 0.55 * nz
        val = np.where(dash > 0.72, 0.85 + 0.15 * nz, val).astype(np.float32)
        a = float(np.clip(hs * 1.3, 0.0, 1.0)) * 0.9
        frame[y0:y1] = frame[y0:y1] * (1.0 - a) + val[: y1 - y0, ..., None] * a
        # thin darker disturbance right above the noise line
        if sw < y0:
            frame[sw:y0] *= (1.0 - 0.22 * hs)

    def _paint_tracking_band(self, frame: np.ndarray, ctx: Context, band: tuple) -> None:
        y0, y1, prof, act = band
        W = frame.shape[1]
        g = ctx.frame_rng(f"{self.key}:tracknz")
        sub = frame[y0:y1]
        m = (prof * act * 0.85).astype(np.float32)[:, None, None]
        gray = _luma(np.ascontiguousarray(sub))[..., None]
        sub += (gray - sub) * (0.7 * m)                    # color drops out
        nz = _streak_noise(g, y1 - y0, W)[..., None]
        frame[y0:y1] = sub * (1.0 - m) + nz * m

    # ── core degradation (one tape pass over Y/IQ planes) ──────────────
    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        v = self.v
        H, W = frame.shape[:2]
        fi = min(ctx.fi_out, ctx.noise.n - 1)
        sx = W / BASE_W
        bw_m, nz_m, _ = self._MODE[v["mode"]]

        yiq = _to_yiq(frame)
        y = np.ascontiguousarray(yiq[..., 0])
        iq = np.ascontiguousarray(yiq[..., 1:])

        # record-side bandwidth (luma FM + color-under)
        y = _filt_x(y, _lp_kernel(_cut(v["luma_bw"] * bw_m, W)))
        iq = _filt_x_narrow(iq, _cut(v["chroma_bw"] * bw_m, W))
        iq = _filt_y(iq, _VKERN_CHROMA[:, 0])              # ~2-line vertical chroma smear
        if abs(v["chroma_delay"]) > 1e-3:
            iq = _shift_x(iq, v["chroma_delay"] * sx)

        # record levels: soft-knee white clip and black crush
        wc = v["white_clip"]
        if wc < 0.9995:
            knee = 0.10
            t = y - (wc - knee)
            y = np.where(t > 0.0, (wc - knee) + knee * np.tanh(t / knee), y)
        bc = v["black_crush"]
        if bc > 0.0:
            kb = max(bc * 0.6, 0.015)
            yb = y - bc
            y = 0.5 * (yb + np.sqrt(yb * yb + kb * kb)) - 0.5 * kb

        # mistracked azimuth: the FM carrier reads back low, so HF luma dies;
        # keep the detail map - the crosstalk pattern lives where detail was
        az = v["azimuth_error"]
        az_detail = None
        if az > 0.0:
            y_soft = _filt_x(y, _lp_kernel(_cut(1.5, W)))
            az_detail = np.abs(y - y_soft)
            y += (y_soft - y) * (0.85 * min(az, 1.0))
            iq *= 1.0 - 0.18 * az

        ic = v["interchange"]
        if ic > 0.0:
            # different deck's chroma timing: color rides a couple lines low
            dvy = max(int(round((1.0 + 3.0 * ic) * (H / BASE_H))), 1)
            iq = np.roll(iq, dvy, axis=0)
            iq[:dvy] = iq[dvy:dvy + 1]

        # dubbing generations: each extra copy re-degrades mildly
        for gen in range(v["generation"] - 1):
            g = ctx.frame_rng(f"{self.key}:gen{gen}")
            y = _filt_x(y, self._k_gen) * 0.985 + 0.006
            gn = g.standard_normal((max(H // 2, 4), max(W // 4, 4)), dtype=np.float32)
            y += _resize(gn, W, H, cv2.INTER_LINEAR) * 0.012
            iq = _filt_x_narrow(iq, self._genc_cut) * 0.955
            iq = _filt_y(iq, _VKERN_CHROMA[:, 0])

        # playback electronics: edge enhancement with overshoot + ringing
        if v["sharpen"] > 0.0:
            y += (v["sharpen"] * 1.7) * (y - _filt_x(y, self._k_sharp))

        # tape noise: streaky horizontal luma noise, blotchy chroma noise
        if v["luma_noise"] > 0.0:
            g = ctx.frame_rng(f"{self.key}:ynoise")
            nz = g.standard_normal((H, max(W // 2, 8)), dtype=np.float32)
            nz = _resize(nz, W, H, cv2.INTER_LINEAR)
            nz = _filt_x(nz, _lp_kernel(0.34))
            rowg = 1.0 + 0.55 * g.standard_normal((H, 1), dtype=np.float32)
            y += nz * np.abs(rowg) * (v["luma_noise"] * 0.155 * nz_m)
        if v["chroma_noise"] > 0.0:
            g = ctx.frame_rng(f"{self.key}:cnoise")
            cn = g.standard_normal((max(H // 8, 4), max(W // 8, 4), 2), dtype=np.float32)
            cn = _resize(cn, W, H, cv2.INTER_LINEAR)
            iq += cn * (v["chroma_noise"] * 0.055 * nz_m)

        # azimuth crosstalk: a fine woven herringbone riding on detailed areas
        if az > 0.0 and az_detail is not None:
            dwgt = np.clip(_filt_x(az_detail, _lp_kernel(0.09)) * 9.0, 0.0, 1.0)
            lam = 4.2 * sx
            rr = np.arange(H, dtype=np.float32)
            zig = np.abs((rr * 0.5) % 2.0 - 1.0)          # slope flips every 2 lines
            dr_t = ctx.noise.drift(f"{self.key}:azph", 0.25)[fi] * 2.4 + fi * 0.61
            ph = (2.0 * np.pi / lam) * _xgrid(H, W) + (2.9 * zig + dr_t)[:, None]
            y += np.sin(ph) * dwgt * (az * 0.075)

        # FM sparkle: demodulator ticks pile up on hard, hot transitions
        fs = v["fm_sparkle"]
        if fs > 0.0:
            g = ctx.frame_rng(f"{self.key}:sparkle")
            gx = np.abs(np.diff(y, axis=1, prepend=y[:, :1]))
            # threshold well above the tape-noise gradient floor: only real
            # picture transitions collect ticks, not the grain
            edge = np.clip((gx - 0.10) * 9.0, 0.0, 1.0)
            hot = np.clip((y - 0.42) * 1.9, 0.0, 1.0)
            hot += np.clip((np.abs(iq[..., 0]) + np.abs(iq[..., 1])) * 2.2 - 0.25, 0.0, 1.0)
            w8 = edge * np.clip(hot, 0.0, 1.0)
            u = g.random((H, W), dtype=np.float32)
            p = fs * 0.30 * w8
            m = u < p
            if np.any(m):
                tick = np.where(u < p * 0.62, np.float32(0.55), np.float32(-0.45))
                tick = np.where(m, tick, np.float32(0.0))
                y += tick + 0.55 * _shift_int_x(tick, 1)

        # 2-head chroma beat: saturation and hue pulse on a ~2-frame period
        hb = v["head_beat"]
        if hb > 0.0:
            phb = np.pi * ctx.fi_out / 1.024 + 2.1 * ctx.noise.drift(f"{self.key}:hbph", 0.07)[fi]
            satm = 1.0 + hb * 0.16 * np.cos(phb)
            hue = hb * np.deg2rad(5.0) * np.sin(phb)
            chb, shb = np.cos(hue) * satm, np.sin(hue) * satm
            i2 = iq[..., 0] * chb - iq[..., 1] * shb
            iq[..., 1] = iq[..., 0] * shb + iq[..., 1] * chb
            iq[..., 0] = i2

        # oxide dropouts (on the FM luma signal, so they ride the geometry)
        self._apply_dropouts(y, ctx)

        out = np.empty_like(yiq)
        out[..., 0] = y
        out[..., 1:] = iq
        frame = _to_rgb(out)

        # timing geometry: TBE + flagging + head-switch bend + tracking shred
        off, (hs_strip, band) = self._geometry_offsets(H, W, ctx)
        if np.any(np.abs(off) > 0.02):
            frame = _remap_x(frame, off)
        if band is not None:
            self._paint_tracking_band(frame, ctx, band)
        if hs_strip is not None:
            self._paint_head_strip(frame, ctx, hs_strip[0], hs_strip[1], hs_strip[2])

        if v["jitter_v"] > 0.0:
            ev = ctx.noise.events(f"{self.key}:vjit", per_second=2.5 * v["jitter_v"])[fi]
            if ev > 0.0:
                w = ctx.noise.white(f"{self.key}:vjitmag")[fi]
                frame = np.roll(frame, (1 if w >= 0 else -1) * (1 + int(abs(w) > 0.6)), axis=0)

        return np.clip(frame, 0.0, 1.0, out=frame)


# ═══════════════════════════════════════════════════════════════════════
# 3. VCR transport events
# ═══════════════════════════════════════════════════════════════════════
@register
class VCRTransport(Effect):
    eid = "vcr_transport"
    label = "VCR Transport"
    kind = "frame"
    desc = ("Deck mechanics on the output timeline: the tracking storm and vertical roll as the "
            "VCR locks up, pause-bar freeze frames and random mid-play glitches.")
    PARAMS = (
        Param("start_glitch", "Start Glitch", "bool", False, group="Events",
              desc="Open with the tracking storm and vertical roll of a VCR still locking onto the tape."),
        Param("start_glitch_s", "Start Glitch Length", "float", 1.2, 0.2, 5.0, unit="s", group="Events",
              desc="How long the deck fights for lock before the picture settles."),
        Param("random_glitch_rate", "Random Glitches", "float", 0.0, 0.0, 12.0, unit="events/min",
              group="Events", iscale=True,
              desc="Momentary tracking storms erupting at random through playback."),
        Param("pause_bar", "Pause Bar", "bool", False, group="Pause",
              desc="The stationary band of shredded noise a paused VCR parks across the picture."),
        Param("freeze", "Freeze Frame", "bool", False, group="Pause",
              desc="Hold the first frame like a paused tape (combine with the pause bar)."),
    )

    def prepare(self, ctx: Context) -> None:
        self._frozen: np.ndarray | None = None
        n, fps = ctx.n_frames, max(ctx.fps, 1.0)
        # Draw the glitch list first, edit it second, and only then rasterise
        # the envelope - so a moved or removed glitch never leaves its old
        # shadow in the curve the frames actually read.
        glitches: list[dict] = []
        rate = self.v["random_glitch_rate"]
        if rate > 0.0:
            # Clip-wide: the deck coughs where the deck coughs, whichever three
            # seconds of it you happen to be looking at.
            ev = ctx.clip_noise.events(f"{self.key}:glitch", rate / 60.0, min_gap_s=1.5)
            g = ctx.rng(f"{self.key}:glitchdur")
            for idx in np.nonzero(ev[: ctx.clip_frames])[0]:
                dur = max(int(g.uniform(0.2, 0.8) * fps), 2)
                glitches.append({"id": f"{self.key}:transport_glitch:{int(idx)}:0",
                                 "fi": int(idx), "dur": dur, "amp": 1.0})
        for e in ctx.event_edits:
            if e.get("effect", self.key) != self.key or e.get("kind", "transport_glitch") != "transport_glitch":
                continue
            op = e.get("op")
            if op == "add":
                fi = int(round(float(e.get("t", 0.0)) * fps))      # clip frame
                if 0 <= fi < ctx.clip_frames:
                    d = e.get("detail") or {}
                    dur = max(int(float(d.get("dur_s", 0.5)) * fps), 2)
                    glitches.append({"id": e.get("id") or f"edit:add:{fi}", "fi": fi, "dur": dur,
                                     "amp": float(np.clip(float(d.get("intensity", 1.0)), 0.05, 1.0))})
                continue
            hit = next((x for x in glitches if x["id"] == e.get("id")), None)
            if hit is None:
                continue
            if op == "remove":
                glitches.remove(hit)
            elif op == "move":
                nfi = int(round(float(e.get("t", hit["fi"] / fps)) * fps))
                if 0 <= nfi < ctx.clip_frames:
                    hit["fi"] = nfi
                else:
                    glitches.remove(hit)
            elif op == "tune":
                d = e.get("detail") or {}
                if "dur_s" in d:
                    hit["dur"] = max(int(float(d["dur_s"]) * fps), 2)
                if "intensity" in d:
                    hit["amp"] = float(np.clip(float(d["intensity"]), 0.05, 1.0))
        self._glitches = glitches
        # The envelope is window-local; each glitch contributes the slice of
        # itself that this render can see.
        af0 = ctx.abs_frame(0)
        env = np.zeros(n, np.float32)
        for gl in glitches:
            idx, dur = gl["fi"] - af0, gl["dur"]
            prof = np.full(dur, gl.get("amp", 1.0), np.float32)
            edge = max(min(3, dur // 2), 1)
            amp = gl.get("amp", 1.0)
            prof[:edge] = np.linspace(0.3 * amp, amp, edge)
            prof[-edge:] = np.linspace(amp, 0.25 * amp, edge)
            lo, hi = max(idx, 0), min(idx + dur, n)
            if hi > lo:
                env[lo:hi] = np.maximum(env[lo:hi], prof[lo - idx: hi - idx])
        self._glitch_env = env
        # Against the clip, not against this render: a preview taken from the
        # middle of a tape should not re-enact the deck locking on.
        self._start_n = ctx.frame_of(self.v["start_glitch_s"]) if self.v["start_glitch"] else 0

    def events(self, ctx: Context) -> list[Event]:
        fps = max(ctx.fps, 1.0)
        w0, w1 = ctx.t0, ctx.t0 + ctx.n_frames / fps
        out = [Event(t=gl["fi"] / fps, dur=gl["dur"] / fps, kind="transport_glitch",
                     detail={"id": gl["id"], "frames": gl["dur"],
                             "intensity": round(gl.get("amp", 1.0), 3)})
               for gl in getattr(self, "_glitches", [])
               if gl["fi"] / fps < w1 and (gl["fi"] + gl["dur"]) / fps > w0]
        # The lock-up only belongs to a render whose window actually contains it.
        if self.v["start_glitch"] and 0 <= self._start_n < ctx.n_frames:
            out.append(Event(t=ctx.t0 + self._start_n / fps, dur=0.5,
                             kind="transport_lock", detail={"frames": int(0.5 * fps)}))
        return sorted(out, key=lambda e: e.t)

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        v = self.v
        H, W = frame.shape[:2]
        fi = min(ctx.fi_out, ctx.noise.n - 1)

        if v["freeze"]:
            if self._frozen is None:
                self._frozen = frame.copy()
            frame = self._frozen.copy()
            # a paused tape never sits perfectly still
            jit = ctx.noise.white(f"{self.key}:pausejit")[fi]
            if abs(jit) > 0.55:
                frame = np.roll(frame, 1 if jit > 0 else -1, axis=0)

        a = 0.0
        if self._start_n > 0 and ctx.fi_out < self._start_n:
            u = ctx.fi_out / max(self._start_n, 1)
            a = (1.0 - u) ** 1.4
            a *= 0.7 + 0.3 * abs(ctx.noise.white(f"{self.key}:stflick")[fi])
            # vertical roll while the servo hunts, decaying to lock
            roll = int(H * 0.42 * a * ctx.noise.smooth(f"{self.key}:roll", 1.2)[fi])
            if roll:
                frame = np.roll(frame, roll, axis=0)
        a = max(a, float(self._glitch_env[min(fi, len(self._glitch_env) - 1)]))
        if a > 0.01:
            g = ctx.frame_rng(f"{self.key}:storm")
            frame = _tracking_storm(frame, g, a)

        if v["pause_bar"]:
            g = ctx.frame_rng(f"{self.key}:pausebar")
            wob = ctx.noise.smooth(f"{self.key}:barwob", 0.7)[fi]
            y0 = int(H * 0.70 + 3.0 * wob)
            bh = max(int(H * 0.075), 6)
            y1 = min(y0 + bh, H)
            n = y1 - y0
            edge = (0.5 - 0.5 * np.cos(np.linspace(0, 2 * np.pi, n, dtype=np.float32))) ** 0.6
            # the frozen picture shreds sideways inside the bar…
            off = np.zeros(H, np.float32)
            off[y0:y1] = g.standard_normal(n).astype(np.float32) * (0.12 * W) * edge
            frame = _remap_x(frame, off)
            # …and long streaky noise dashes ride on top
            nz = _resize(g.random((n, max(W // 14, 6)), dtype=np.float32), W, n, cv2.INTER_LINEAR)
            val = (0.12 + 0.78 * nz ** 1.6).astype(np.float32)
            m = (0.8 * edge)[:, None, None]
            frame[y0:y1] = frame[y0:y1] * (1.0 - m) + val[..., None] * m
            dash = _resize(g.random((max(n // 3, 2), max(W // 20, 6)), dtype=np.float32),
                           W, n, cv2.INTER_LINEAR)
            hot = (dash > 0.82) & (edge[:, None] > 0.3)
            frame[y0:y1][hot] = 0.94

        return np.clip(frame, 0.0, 1.0, out=frame)


# ═══════════════════════════════════════════════════════════════════════
# 4. RF / antenna reception
# ═══════════════════════════════════════════════════════════════════════
@register
class SignalRF(Effect):
    eid = "signal_rf"
    label = "RF Reception"
    kind = "frame"
    desc = ("Antenna trouble on top of any signal: snow, multipath ghosting, a crawling "
            "AC hum bar, ignition interference dashes and an overall weak-signal wash.")
    PARAMS = (
        Param("snow", "Snow", "float", 0.12, 0.0, 1.0, group="Noise", iscale=True,
              desc="The fizzing per-pixel static of a marginal antenna, denser in the shadows."),
        Param("sparkle", "Snow Sparkle Size", "float", 2.0, 1.0, 8.0, unit="px", group="Noise",
              desc="Grain size of the snow - bigger sparkles read as a worse, lower-band signal."),
        Param("ghost_n", "Ghost Copies", "int", 1, 0, 4, group="Ghosting",
              desc="Number of multipath reflections layered over the picture."),
        Param("ghost_px", "Ghost Offset", "float", 14.0, -60.0, 60.0, unit="px", group="Ghosting",
              desc="Displacement of the first ghost; negative leads the image (pre-ghost)."),
        Param("ghost_alpha", "Ghost Visibility", "float", 0.25, 0.0, 0.8, group="Ghosting", iscale=True,
              desc="Opacity of the reflections; each further ghost is fainter."),
        Param("hum_bar", "Hum Bar", "float", 0.0, 0.0, 1.0, group="Interference", iscale=True,
              desc="A wide dark mains-hum band crawling slowly up the picture."),
        Param("hum_speed", "Hum Bar Speed", "float", 0.12, 0.01, 1.0, unit="bars/s", group="Interference",
              desc="Crawl rate of the hum bar - the beat between mains and vertical sync."),
        Param("impulse_noise", "Impulse Noise", "float", 0.0, 0.0, 30.0, unit="events/s",
              group="Interference", iscale=True,
              desc="Sparse bright one-line dashes from ignition or motor interference."),
        Param("weak_signal", "Weak Signal", "float", 0.0, 0.0, 1.0, group="Reception", iscale=True,
              desc="Master fade toward the noise floor: washed-out color, lifted snow, gray haze."),
    )

    def prepare(self, ctx: Context) -> None:
        pass

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        v = self.v
        H, W = frame.shape[:2]
        fi = min(ctx.fi_out, ctx.noise.n - 1)
        w = v["weak_signal"]

        # multipath ghosts of the clean signal
        n_g = v["ghost_n"]
        if n_g > 0 and v["ghost_alpha"] > 0.0:
            acc = frame.copy()
            asum = 1.0
            for i in range(n_g):
                drift = ctx.noise.smooth(f"{self.key}:ghost{i}", 0.12)[fi] * 3.0
                offset = v["ghost_px"] * (i + 1) * (W / BASE_W) + drift
                alpha = v["ghost_alpha"] * (0.62 ** i)
                acc += _shift_x(frame, offset) * alpha
                asum += alpha
            frame = acc / asum

        if w > 0.0:
            y = _luma(frame)[..., None]
            frame += (y - frame) * (0.55 * w)               # desaturate
            frame = (frame - 0.5) * (1.0 - 0.28 * w) + 0.5 + 0.02 * w

        snow = v["snow"] + 0.5 * w
        if snow > 0.0:
            g = ctx.frame_rng(f"{self.key}:snow")
            sp = max(1, int(round(v["sparkle"] * W / BASE_W)))
            gh, gw = max(H // sp, 8), max(W // sp, 8)
            n = g.standard_normal((gh, gw), dtype=np.float32)
            if sp > 1:
                n = _resize(n, W, H, cv2.INTER_NEAREST)
            amp = snow * 0.16
            vis = (1.0 - 0.45 * _luma(frame))[..., None]     # snow shows more in darks
            frame += (n * amp)[..., None] * vis
            spark = np.clip(n - 2.1, 0.0, None) * (snow * 0.9)  # hot white sparkles
            if np.any(spark > 0.0):
                frame += spark[..., None]

        if v["hum_bar"] > 0.0:
            ph = (fi / max(ctx.fps, 1.0)) * v["hum_speed"]
            center = (1.0 - (ph % 1.0)) * (H * 1.3) - 0.15 * H   # crawls upward
            rows = np.arange(H, dtype=np.float32)
            prof = np.exp(-0.5 * ((rows - center) / (0.10 * H)) ** 2)
            frame *= (1.0 - v["hum_bar"] * 0.45 * prof)[:, None, None]

        if v["impulse_noise"] > 0.0:
            g = ctx.frame_rng(f"{self.key}:impulse")
            n = int(g.poisson(v["impulse_noise"] / max(ctx.fps, 1.0) * 3.0))
            for _ in range(min(n, 30)):
                r = int(g.integers(0, H))
                L = int((10 + 70 * g.random()) * W / BASE_W)
                x0 = int(g.integers(0, max(W - L, 1)))
                val = 0.95 if g.random() > 0.15 else 0.03
                frame[r, x0:x0 + L] += (val - frame[r, x0:x0 + L]) * 0.85

        return np.clip(frame, 0.0, 1.0, out=frame)


# ═══════════════════════════════════════════════════════════════════════
# 5. Tape junk (between-recordings static)
# ═══════════════════════════════════════════════════════════════════════
@register
class TapeJunk(Effect):
    eid = "tape_junk"
    label = "Tape Junk"
    kind = "frame"
    desc = ("The unlocked garbage between recordings: shredded rainbow static, gray snow or "
            "VCR blue screen at the head or tail of the clip, with a half-locked transition.")
    PARAMS = (
        Param("at_start_s", "At Start", "float", 0.0, 0.0, 30.0, unit="s", group="Timing",
              desc="Seconds of junk before the recording snaps in."),
        Param("at_end_s", "At End", "float", 0.0, 0.0, 30.0, unit="s", group="Timing",
              desc="Seconds of junk after the recording cuts out."),
        Param("style", "Style", "enum", "rainbow_smear",
              choices=("rainbow_smear", "gray_snow", "blue_screen"), group="Style",
              desc="Shredded rainbow smears, plain gray snow, or the VCR's solid blue mute screen."),
    )

    _TRANS_S = 0.18   # half-locked transition length

    def prepare(self, ctx: Context) -> None:
        pass

    def _junk_frame(self, H: int, W: int, ctx: Context) -> np.ndarray:
        g = ctx.frame_rng(f"{self.key}:junk")
        fi = ctx.fi_out
        style = self.v["style"]

        if style == "blue_screen":
            out = np.empty((H, W, 3), np.float32)
            out[..., 0], out[..., 1], out[..., 2] = 0.02, 0.05, 0.72
            nz = g.standard_normal((H, max(W // 2, 8)), dtype=np.float32)
            out += _resize(nz, W, H, cv2.INTER_LINEAR)[..., None] * 0.015
            return np.clip(out, 0.0, 1.0, out=out)

        if style == "gray_snow":
            n = g.standard_normal((H, W), dtype=np.float32)
            y = 0.42 + 0.30 * n
            rowg = 1.0 + 0.3 * g.standard_normal((H, 1), dtype=np.float32)
            y *= np.abs(rowg) ** 0.5
            return np.clip(np.repeat(y[..., None], 3, axis=2), 0.0, 1.0)

        # rainbow_smear: a handful of big posterized color fields with torn
        # edges, chroma confetti speckle, all rolling vertically
        bs = max(H // 9, 8)
        rows_c = H // bs + 2
        field = g.random((rows_c, 4), dtype=np.float32)
        field = _resize(field, W, H, cv2.INTER_NEAREST)
        field = np.floor(field * 6.0) / 5.0                     # posterized bands
        y = _filt_x(field, _lp_kernel(0.05)) * 0.72 + 0.14      # smeared block edges

        cn = g.uniform(-0.62, 0.62, (rows_c, 4, 2)).astype(np.float32)
        iq = _resize(cn, W, H, cv2.INTER_NEAREST)
        iq = _filt_x(iq, _lp_kernel(0.05))

        # tearing: ragged per-line jitter over a mild coherent wander, plus a
        # few wildly thrown lines
        off = g.standard_normal(H).astype(np.float32)
        off = np.convolve(off, np.ones(5, np.float32) / 5.0, mode="same") * (0.04 * W)
        off += g.standard_normal(H).astype(np.float32) * (0.012 * W)
        wild = g.random(H) < 0.14
        off[wild] += g.standard_normal(int(wild.sum())).astype(np.float32) * (0.30 * W)
        idx = ((_xgrid(H, W) + off[:, None]).astype(np.int64)) % W
        y = np.take_along_axis(y, idx, axis=1)
        iq = np.take_along_axis(iq, idx[..., None].repeat(2, axis=2), axis=1)

        roll = int((fi * H * 0.055)) % H
        y = np.roll(y, roll, axis=0)
        iq = np.roll(iq, roll, axis=0)

        # chroma confetti + luma grain, and a couple of hot sync rows
        iq += g.standard_normal((H, W, 2), dtype=np.float32) * 0.085
        y += g.standard_normal((H, W), dtype=np.float32) * 0.075
        for _ in range(int(g.integers(1, 4))):
            r = int(g.integers(0, H))
            y[r:min(r + 2, H)] = 0.85 + 0.15 * g.random()

        # the bottom of the field collapses into gray noise
        gb = max(int(H * 0.10), 4)
        u = (np.linspace(0.0, 1.0, gb, dtype=np.float32) ** 1.5)[:, None]
        y[-gb:] = y[-gb:] * (1.0 - u) + (0.30 + 0.45 * g.random((gb, W), dtype=np.float32)) * u
        iq[-gb:] *= (1.0 - 0.85 * u)[..., None]

        out = np.empty((H, W, 3), np.float32)
        out[..., 0] = y
        out[..., 1:] = iq
        out = _to_rgb(out)
        return np.clip(out, 0.0, 1.0, out=out)

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        v = self.v
        if v["at_start_s"] <= 0.0 and v["at_end_s"] <= 0.0:
            return frame
        fps = max(ctx.fps, 1.0)
        t = ctx.fi_out / fps
        t_end = ctx.n_frames / fps - t

        blend = 0.0   # 1 = full junk
        if v["at_start_s"] > 0.0 and t < v["at_start_s"] + self._TRANS_S:
            blend = 1.0 if t < v["at_start_s"] else 1.0 - (t - v["at_start_s"]) / self._TRANS_S
        if v["at_end_s"] > 0.0 and t_end < v["at_end_s"] + self._TRANS_S:
            b = 1.0 if t_end < v["at_end_s"] else 1.0 - (t_end - v["at_end_s"]) / self._TRANS_S
            blend = max(blend, b)
        if blend <= 0.0:
            return frame

        H, W = frame.shape[:2]
        junk = self._junk_frame(H, W, ctx)
        if blend >= 1.0:
            return junk
        # half-locked: bands of lines flip between picture and junk, and the
        # picture rows that do show through are torn sideways
        g = ctx.frame_rng(f"{self.key}:lock")
        blocks = g.random(max(H // 24, 6), dtype=np.float32)
        runs = _resize(blocks.reshape(-1, 1), 1, H, cv2.INTER_LINEAR)[:, 0]
        rowsel = (runs < blend).astype(np.float32)
        rowsel = np.convolve(rowsel, np.ones(3, np.float32) / 3.0, mode="same")
        tear = g.standard_normal(H).astype(np.float32) * 14.0 * blend * (W / BASE_W)
        frame = _remap_x(frame, tear)
        m = rowsel[:, None, None]
        out = frame * (1.0 - m) + junk * m
        return np.clip(out, 0.0, 1.0, out=out)
