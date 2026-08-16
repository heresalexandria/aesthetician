"""Shared audio DSP helpers (no effects registered here).

Conventions: audio is float32 (n_samples, channels); all helpers keep that
shape and dtype. Every stochastic helper takes an explicit np.random.Generator
so effects stay deterministic per (seed, effect key).
"""

from __future__ import annotations

import numpy as np
from scipy import signal as sps


def db_to_lin(db: float) -> float:
    return float(10.0 ** (db / 20.0))


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(x), dtype=np.float64)) + 1e-12)


def match_rms(processed: np.ndarray, reference: np.ndarray, max_db: float = 12.0) -> np.ndarray:
    """Gain `processed` so its RMS matches `reference`, capped at ±max_db."""
    g = rms(reference) / rms(processed)
    lim = db_to_lin(max_db)
    g = float(np.clip(g, 1.0 / lim, lim))
    return (processed * g).astype(np.float32)


def peak_guard(x: np.ndarray, ceiling: float = 0.98) -> np.ndarray:
    """Scale down (never up) if the buffer exceeds a soft ceiling."""
    p = float(np.max(np.abs(x))) if x.size else 0.0
    if p > ceiling:
        x = x * (ceiling / p)
    return x.astype(np.float32)


def fit_len(x: np.ndarray, n: int) -> np.ndarray:
    """Trim or zero-pad a buffer to exactly n samples.

    Resampling rounds up on both legs, so a rate round-trip hands back a
    sample or two more than it was given whenever the length isn't a whole
    multiple of the ratio. Anything built against the original n - a noise
    bed, a hum, an envelope - stops broadcasting against it. Run the result
    of a round-trip through here before it meets the rest of the block.
    """
    m = x.shape[0]
    if m == n:
        return x
    if m > n:
        return x[:n]
    return np.vstack([x, np.zeros((n - m,) + x.shape[1:], x.dtype)])


# ── filters ─────────────────────────────────────────────────────────────

def butter_sos(order: int, hz, btype: str, sr: int) -> np.ndarray:
    nyq = sr / 2.0
    wn = np.clip(np.atleast_1d(np.asarray(hz, dtype=np.float64)) / nyq, 1e-5, 0.995)
    if len(wn) == 1:
        wn = float(wn[0])
    return sps.butter(order, wn, btype=btype, output="sos")


def lowpass(x: np.ndarray, hz: float, sr: int, order: int = 4) -> np.ndarray:
    if hz >= sr * 0.495:
        return x.astype(np.float32)
    return sps.sosfilt(butter_sos(order, hz, "low", sr), x, axis=0).astype(np.float32)


def highpass(x: np.ndarray, hz: float, sr: int, order: int = 2) -> np.ndarray:
    if hz <= 1.0:
        return x.astype(np.float32)
    return sps.sosfilt(butter_sos(order, hz, "high", sr), x, axis=0).astype(np.float32)


def bandpass(x: np.ndarray, lo: float, hi: float, sr: int, order: int = 2) -> np.ndarray:
    hi = min(hi, sr * 0.49)
    if lo >= hi:
        lo = hi * 0.5
    sos = butter_sos(order, [lo, hi], "band", sr)
    return sps.sosfilt(sos, x, axis=0).astype(np.float32)


# RBJ audio-EQ-cookbook biquads, returned as 1x6 sos rows -----------------

def _rbj(sr: int, f0: float, q: float):
    w0 = 2.0 * np.pi * np.clip(f0, 5.0, sr * 0.49) / sr
    return w0, np.sin(w0) / (2.0 * max(q, 0.05))


def peaking(sr: int, f0: float, gain_db: float, q: float = 1.0) -> np.ndarray:
    a = 10.0 ** (gain_db / 40.0)
    w0, alpha = _rbj(sr, f0, q)
    cw = np.cos(w0)
    b = [1 + alpha * a, -2 * cw, 1 - alpha * a]
    aa = [1 + alpha / a, -2 * cw, 1 - alpha / a]
    return (np.array([b + aa]) / aa[0]).astype(np.float64)


def shelf(sr: int, f0: float, gain_db: float, high: bool, s: float = 0.9) -> np.ndarray:
    a = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * np.pi * np.clip(f0, 5.0, sr * 0.49) / sr
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / 2.0 * np.sqrt((a + 1 / a) * (1 / max(s, 0.1) - 1) + 2)
    two_sqa = 2.0 * np.sqrt(a) * alpha
    if high:
        b0 = a * ((a + 1) + (a - 1) * cw + two_sqa)
        b1 = -2 * a * ((a - 1) + (a + 1) * cw)
        b2 = a * ((a + 1) + (a - 1) * cw - two_sqa)
        a0 = (a + 1) - (a - 1) * cw + two_sqa
        a1 = 2 * ((a - 1) - (a + 1) * cw)
        a2 = (a + 1) - (a - 1) * cw - two_sqa
    else:
        b0 = a * ((a + 1) - (a - 1) * cw + two_sqa)
        b1 = 2 * a * ((a - 1) - (a + 1) * cw)
        b2 = a * ((a + 1) - (a - 1) * cw - two_sqa)
        a0 = (a + 1) + (a - 1) * cw + two_sqa
        a1 = -2 * ((a - 1) + (a + 1) * cw)
        a2 = (a + 1) + (a - 1) * cw - two_sqa
    return (np.array([[b0, b1, b2, a0, a1, a2]]) / a0).astype(np.float64)


def sos_cascade(*rows: np.ndarray) -> np.ndarray:
    return np.vstack(rows) if rows else np.zeros((0, 6))


def apply_sos(x: np.ndarray, sos: np.ndarray) -> np.ndarray:
    if sos.shape[0] == 0:
        return x.astype(np.float32)
    return sps.sosfilt(sos, x, axis=0).astype(np.float32)


def tilt(x: np.ndarray, sr: int, db_at_top: float, pivot_hz: float = 1500.0) -> np.ndarray:
    """Gentle spectral tilt: high shelf of db_at_top around pivot."""
    if abs(db_at_top) < 0.01:
        return x.astype(np.float32)
    return apply_sos(x, shelf(sr, pivot_hz, db_at_top, high=True, s=0.5))


# ── modulation / control-rate noise ─────────────────────────────────────

def control_noise(
    rng: np.random.Generator,
    n_samples: int,
    sr: int,
    lo_hz: float,
    hi_hz: float,
    ctrl_sr: float = 1000.0,
) -> np.ndarray:
    """Band-limited noise in roughly [-1,1], length n_samples, built at a low
    control rate then linearly interpolated up (cheap for sub-audio rates)."""
    ctrl_sr = min(ctrl_sr, sr)
    nc = max(int(np.ceil(n_samples * ctrl_sr / sr)) + 8, 32)
    w = rng.standard_normal(nc)
    nyq = ctrl_sr / 2.0
    lo = max(lo_hz, 0.01) / nyq
    hi = min(hi_hz / nyq, 0.98)
    if lo >= hi:
        lo = hi * 0.5
    sos = sps.butter(2, [lo, hi], btype="band", output="sos")
    w = sps.sosfiltfilt(sos, w)
    p95 = np.percentile(np.abs(w), 95) + 1e-9
    w = w / p95
    t_ctrl = np.arange(nc) / ctrl_sr
    t_out = np.arange(n_samples) / sr
    return np.interp(t_out, t_ctrl, w).astype(np.float32)


def variable_speed(audio: np.ndarray, speed: np.ndarray) -> np.ndarray:
    """Resample through a modulated read position (speed 1.0 = normal).

    Integrates `speed` (per output sample) into fractional source positions and
    linearly interpolates. Positions past the end return silence with a short
    fade instead of a frozen last sample.
    """
    n = audio.shape[0]
    pos = np.cumsum(speed.astype(np.float64))
    pos -= pos[0]
    src = np.arange(n, dtype=np.float64)
    out = np.empty_like(audio)
    for c in range(audio.shape[1]):
        out[:, c] = np.interp(pos, src, audio[:, c].astype(np.float64), right=0.0)
    over = pos > (n - 1)
    if np.any(over):
        i0 = int(np.argmax(over))
        fade = 256  # short fade-out instead of a hard cut at end-of-source
        a = max(i0 - fade, 0)
        env = np.ones(n, np.float64)
        env[a:i0] = np.linspace(1.0, 0.0, i0 - a)
        env[i0:] = 0.0
        out *= env[:, None].astype(np.float32)
    return out.astype(np.float32)


def fractional_delay(x: np.ndarray, delay_samples: np.ndarray) -> np.ndarray:
    """Per-sample fractional delay (1-D signal), linear interpolation."""
    n = len(x)
    pos = np.arange(n, dtype=np.float64) - np.maximum(delay_samples, 0.0)
    pos = np.clip(pos, 0.0, n - 1)
    return np.interp(pos, np.arange(n, dtype=np.float64), x.astype(np.float64)).astype(np.float32)


# ── envelopes & dynamics (control-rate recursion) ───────────────────────

def envelope(
    audio: np.ndarray,
    sr: int,
    attack_ms: float,
    release_ms: float,
    mode: str = "peak",
    block: int = 0,
) -> np.ndarray:
    """Attack/release envelope follower.

    Detector runs at a decimated control rate (~2.5 ms blocks) with the
    classic asymmetric one-pole recursion, then linearly interpolates back to
    sample rate. Returns (n,) float32 linear envelope, mono (max over channels).
    """
    n = audio.shape[0]
    B = block or max(int(sr * 0.0025), 16)
    d = np.max(np.abs(audio), axis=1) if audio.ndim == 2 else np.abs(audio)
    nb = int(np.ceil(n / B))
    pad = nb * B - n
    if pad:
        d = np.concatenate([d, np.full(pad, d[-1] if n else 0.0, d.dtype)])
    blocks = d.reshape(nb, B)
    if mode == "rms":
        det = np.sqrt(np.mean(np.square(blocks, dtype=np.float64), axis=1))
    else:
        det = blocks.max(axis=1).astype(np.float64)
    dt = B / sr
    ca = np.exp(-dt / max(attack_ms * 1e-3, 1e-4))
    cr = np.exp(-dt / max(release_ms * 1e-3, 1e-4))
    env = np.empty(nb)
    e = det[0]
    for i in range(nb):  # unavoidable recursion, but at ~400 Hz control rate
        x = det[i]
        c = ca if x > e else cr
        e = c * e + (1.0 - c) * x
        env[i] = e
    centers = (np.arange(nb) + 0.5) * B
    return np.interp(np.arange(n), centers, env).astype(np.float32)


def smooth_gain(
    gain: np.ndarray,
    sr: int,
    attack_ms: float,
    release_ms: float,
    block: int = 0,
) -> np.ndarray:
    """Attack/release-smooth a per-sample linear gain curve (attack = gain
    falling). Same control-rate scheme as `envelope`."""
    n = len(gain)
    B = block or max(int(sr * 0.0025), 16)
    nb = int(np.ceil(n / B))
    pad = nb * B - n
    g = np.concatenate([gain, np.full(pad, gain[-1])]) if pad else gain
    det = g.reshape(nb, B).min(axis=1).astype(np.float64)  # honor fastest dip
    dt = B / sr
    ca = np.exp(-dt / max(attack_ms * 1e-3, 1e-4))
    cr = np.exp(-dt / max(release_ms * 1e-3, 1e-4))
    out = np.empty(nb)
    e = det[0]
    for i in range(nb):
        x = det[i]
        c = ca if x < e else cr  # falling gain = attack
        e = c * e + (1.0 - c) * x
        out[i] = e
    centers = (np.arange(nb) + 0.5) * B
    return np.interp(np.arange(n), centers, out).astype(np.float32)


# ── event placement ─────────────────────────────────────────────────────

def event_times(
    rng: np.random.Generator,
    per_minute: float,
    duration_s: float,
    min_gap_s: float = 0.25,
) -> np.ndarray:
    """Poisson-ish event start times (seconds), sorted, with a minimum gap."""
    lam = per_minute / 60.0 * duration_s
    k = int(rng.poisson(lam)) if lam > 0 else 0
    if k <= 0:
        return np.empty(0)
    t = np.sort(rng.uniform(0.0, duration_s, k))
    keep = [t[0]]
    for x in t[1:]:
        if x - keep[-1] >= min_gap_s:
            keep.append(x)
    return np.asarray(keep)


def add_at(dst: np.ndarray, src: np.ndarray, start: int) -> None:
    """Mix `src` (n,) or (n,ch) into dst at sample offset, clipped to bounds."""
    n = dst.shape[0]
    if start >= n or start + src.shape[0] <= 0:
        return
    a = max(start, 0)
    b = min(start + src.shape[0], n)
    s = src[a - start : b - start]
    if dst.ndim == 2 and s.ndim == 1:
        s = s[:, None]
    dst[a:b] += s


# ── speech-shaped murmur ────────────────────────────────────────────────

def speech_murmur(rng: np.random.Generator, n: int, sr: int,
                  syllable_hz: tuple = (2.5, 6.5)) -> np.ndarray:
    """Unintelligible 'other program / voices through the wall' murmur.

    Speech-shaped noise only - no real speech: formant-band filtered noise
    with slowly wandering band weights, amplitude-modulated at syllabic
    (3–6 Hz) rates with phrase-length swells and pauses.
    Returns (n,) float32 normalized to RMS ≈ 1 (caller sets level/band).
    """
    if n < 16:
        return np.zeros(n, np.float32)
    w = rng.standard_normal(n).astype(np.float32)
    base = lowpass(w[:, None], 3400.0, sr, order=2)[:, 0]
    bands = (
        (bandpass(base[:, None], 120.0, 400.0, sr, order=2)[:, 0], 1.0),   # voicing
        (bandpass(base[:, None], 350.0, 900.0, sr, order=2)[:, 0], 0.9),   # F1
        (bandpass(base[:, None], 900.0, 2000.0, sr, order=2)[:, 0], 0.65), # F2
        (bandpass(base[:, None], 2000.0, 3400.0, sr, order=2)[:, 0], 0.3), # F3/sibilant
    )
    out = np.zeros(n, np.float32)
    for b, g0 in bands:  # vowel-ish spectral movement
        drift = 0.55 + 0.45 * control_noise(rng, n, sr, 0.4, 1.6, ctrl_sr=100.0)
        out += b * (g0 * np.clip(drift, 0.05, 1.2)).astype(np.float32)
    syl = control_noise(rng, n, sr, syllable_hz[0], syllable_hz[1], ctrl_sr=200.0)
    syl = np.clip(0.25 + 0.75 * syl, 0.0, None) ** 1.4          # syllable pulses + gaps
    phrase = control_noise(rng, n, sr, 0.08, 0.35, ctrl_sr=50.0)
    phrase = np.clip(0.65 + 0.6 * phrase, 0.0, 1.0)             # sentence swells/pauses
    out *= (syl * phrase).astype(np.float32)
    return (out / (rms(out) + 1e-12)).astype(np.float32)


# ── companding ──────────────────────────────────────────────────────────

def mulaw_roundtrip(x: np.ndarray, mu: float = 255.0, bits: int = 8) -> np.ndarray:
    """Real μ-law companding: encode to `bits` quantized levels and decode."""
    x = np.clip(x, -1.0, 1.0).astype(np.float64)
    y = np.sign(x) * np.log1p(mu * np.abs(x)) / np.log1p(mu)
    q = 2 ** (bits - 1) - 1
    y = np.round(y * q) / q
    return (np.sign(y) * ((1.0 + mu) ** np.abs(y) - 1.0) / mu).astype(np.float32)


# ── Schroeder reverb core (shared by room + speakerphone) ───────────────

def schroeder(
    x: np.ndarray,
    sr: int,
    comb_ms: tuple,
    comb_fb: tuple,
    ap_ms: tuple = (5.0, 1.7),
    ap_g: float = 0.7,
    damp: float = 0.5,
) -> np.ndarray:
    """Parallel damped feedback combs + series allpasses. x is (n,) mono.

    The comb recursion y[n] = x[n] + g*damped(y[n-D]) is evaluated block-wise
    in chunks of D samples (the delay guarantees each chunk only needs the
    previous one), with the in-loop damping one-pole done by lfilter.
    """
    n = len(x)
    x64 = x.astype(np.float64)
    wet = np.zeros(n)
    dcoef = float(np.clip(damp, 0.0, 0.95))
    b_lp, a_lp = [1.0 - dcoef], [1.0, -dcoef]
    for ms, g in zip(comb_ms, comb_fb):
        D = max(int(sr * ms / 1000.0), 8)
        y = np.zeros(n + D)
        s_prev = np.zeros(D)  # damped previous chunk
        zi = np.zeros(1)
        for a in range(0, n, D):
            b = min(a + D, n)
            chunk = x64[a:b] + g * s_prev[: b - a]
            y[D + a : D + b] = chunk
            s, zi = sps.lfilter(b_lp, a_lp, chunk, zi=zi)
            s_prev = s if len(s) == D else np.concatenate([s, np.zeros(D - len(s))])
        wet += y[D : D + n]
    wet /= max(len(comb_ms), 1)
    for ms in ap_ms:
        D = max(int(sr * ms / 1000.0), 4)
        yp = np.zeros(n + D)
        xp = np.concatenate([np.zeros(D), wet])
        for a in range(0, n, D):
            b = min(a + D, n)
            yp[D + a : D + b] = (
                -ap_g * xp[D + a : D + b] + xp[a:b] + ap_g * yp[a:b]
            )
        wet = yp[D : D + n]
    return wet.astype(np.float32)
