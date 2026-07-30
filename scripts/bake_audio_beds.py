#!/usr/bin/env python
"""Bake procedural ambience beds for the a_bed effect.

Synthesizes period environment loops - running projectors, a wall of shop
TVs, HVAC halls, CRT whine… - entirely from noise, oscillators and filters
(no recordings, no downloads), and writes them to assets/audio-beds/ as
48 kHz stereo 16-bit WAVs, 12–20 s each, loop-ready (crossfaded ends),
peak ≤ −12 dBFS.

Run:  .venv/bin/python scripts/bake_audio_beds.py [bed_name ...]
      (no args = bake everything; --list shows available names)

Determinism: a fixed bake seed keyed per bed - re-running reproduces the
same files bit-for-bit.
"""

from __future__ import annotations

import os
import sys

import numpy as np
from scipy import signal as sps
from scipy.io import wavfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from aesthetician.effects.audio import _util as U  # noqa: E402
from aesthetician.engine.rng import stream as _stream  # noqa: E402

SR = 48000
BAKE_SEED = 926
XFADE_S = 0.8            # loop-seam crossfade folded from the tail
PEAK = 0.25              # −12.04 dBFS
OUT_DIR = os.path.join(ROOT, "assets", "audio-beds")


def rng(key: str) -> np.random.Generator:
    return _stream(BAKE_SEED, key)


def n_for(dur_s: float) -> int:
    return int((dur_s + XFADE_S) * SR)  # extra tail is folded onto the head


def t_axis(n: int) -> np.ndarray:
    return np.arange(n) / SR


def loop_fold(x: np.ndarray) -> np.ndarray:
    """Equal-power crossfade of the tail onto the head -> seamless loop."""
    xf = int(XFADE_S * SR)
    n = x.shape[0] - xf
    a = np.sqrt(np.linspace(0.0, 1.0, xf, dtype=np.float32))[:, None]
    y = x[:n].copy()
    y[:xf] = y[:xf] * a + x[n : n + xf] * a[::-1]
    return y


def stereoize(mono: np.ndarray, delay_ms: float = 0.35, gain_r: float = 0.94) -> np.ndarray:
    """Mono source given a small inter-channel delay - phantom-center realism."""
    d = int(SR * delay_ms / 1000.0)
    right = np.concatenate([np.zeros(d, np.float32), mono[:-d]]) if d else mono
    return np.stack([mono, right * gain_r], axis=1)


def decor_noise(g: np.random.Generator, n: int) -> np.ndarray:
    """Decorrelated stereo white noise."""
    return np.stack([g.standard_normal(n).astype(np.float32) for _ in range(2)], axis=1)


def set_rms(x: np.ndarray, db: float) -> np.ndarray:
    return (x * (U.db_to_lin(db) / (U.rms(x) + 1e-12))).astype(np.float32)


def tone_stack(phase: np.ndarray, partials) -> np.ndarray:
    """Sum of harmonics over a running phase; partials = [(k, amp), ...]."""
    out = np.zeros(len(phase), np.float64)
    for k, a in partials:
        out += a * np.sin(k * phase)
    return out.astype(np.float32)


def running_phase(freq_hz: np.ndarray | float, n: int) -> np.ndarray:
    f = np.broadcast_to(np.asarray(freq_hz, np.float64), (n,))
    return 2 * np.pi * np.cumsum(f) / SR


def impact_kernel(g: np.random.Generator, taps, band, dur_ms: float = 6.0) -> np.ndarray:
    """Mechanical contact kernel: a few decaying noise micro-impacts."""
    L = int(SR * dur_ms / 1000.0)
    k = np.zeros(L, np.float32)
    for off_ms, amp, dec_ms in taps:
        o = int(SR * off_ms / 1000.0)
        m = L - o
        if m <= 4:
            continue
        burst = g.standard_normal(m).astype(np.float32)
        burst *= np.exp(-np.arange(m) / (SR * dec_ms / 1000.0)).astype(np.float32)
        k[o:] += amp * burst
    k = U.bandpass(k[:, None], band[0], band[1], SR, order=2)[:, 0]
    return (k / (np.max(np.abs(k)) + 1e-9)).astype(np.float32)


def pulse_train(g: np.random.Generator, n: int, hz: float, jitter_ms: float = 0.8,
                amp_jitter: float = 0.3) -> np.ndarray:
    """Impulse train at hz with per-pulse timing and amplitude jitter."""
    period = SR / hz
    count = int(n / period) + 3
    starts = np.arange(count) * period + g.uniform(-1, 1, count) * jitter_ms * SR / 1000.0
    amps = 1.0 + g.uniform(-amp_jitter, amp_jitter, count)
    train = np.zeros(n, np.float32)
    idx = starts.astype(np.int64)
    ok = (idx >= 0) & (idx < n)
    np.add.at(train, idx[ok], amps[ok].astype(np.float32))
    return train


def wander(g: np.random.Generator, n: int, lo: float, hi: float, depth: float) -> np.ndarray:
    """1 ± depth slow multiplier."""
    return 1.0 + depth * U.control_noise(g, n, SR, lo, hi, ctrl_sr=100.0)


def room_smear(x: np.ndarray, combs, decay_s: float, damp: float, mix: float) -> np.ndarray:
    """Light Schroeder smear to place a source in a space (stereo in/out)."""
    out = np.empty_like(x)
    for c in range(x.shape[1]):
        cms = tuple(m * (1.0 + 0.013 * c) for m in combs)
        fb = tuple(10.0 ** (-3.0 * (m / 1000.0) / decay_s) for m in cms)
        wet = U.schroeder(x[:, c], SR, cms, fb, ap_ms=(5.9, 2.1), ap_g=0.65, damp=damp)
        out[:, c] = (1.0 - mix * 0.4) * x[:, c] + mix * wet
    return out


# ── projectors ──────────────────────────────────────────────────────────

def _projector_mech(key: str, n: int, pulse_hz: float, claw_band, claw_taps,
                    motor_hz: float, motor_parts, growl_band, growl_amt: float) -> np.ndarray:
    """Shared projector mechanics: claw clatter + gate rattle + motor (mono)."""
    g = rng(key)
    # claw: each frame advance is a cluster of micro-impacts, not a click
    kern = impact_kernel(g, claw_taps, claw_band, dur_ms=7.0)
    claw = sps.fftconvolve(pulse_train(g, n, pulse_hz, 0.7, 0.35), kern)[:n].astype(np.float32)
    # gate/pressure-plate rattle: weaker offset train, its own brighter kernel
    kern2 = impact_kernel(g, [(0.0, 1.0, 0.8), (1.7, 0.5, 0.6)], (1200.0, 3800.0), dur_ms=4.0)
    gate = sps.fftconvolve(pulse_train(g, n, pulse_hz, 1.1, 0.5), kern2)[:n].astype(np.float32)
    off = int(0.42 * SR / pulse_hz)
    gate = np.roll(gate, off) * 0.4
    mech = claw + gate
    mech /= np.percentile(np.abs(mech), 99.5) + 1e-9
    # motor tone + growl locked to it
    ph = running_phase(motor_hz * wander(g, n, 0.1, 0.6, 0.012), n)
    motor = tone_stack(ph, motor_parts)
    growl = g.standard_normal(n).astype(np.float32)
    growl = U.bandpass(growl[:, None], growl_band[0], growl_band[1], SR, order=2)[:, 0]
    growl *= (1.0 + 0.5 * np.sin(2 * ph)).astype(np.float32) * 0.5
    motor = motor + growl_amt * growl
    motor /= U.rms(motor) + 1e-9
    return mech, motor


def bake_projector_16mm_run() -> np.ndarray:
    n = n_for(18.0)
    g = rng("p16:mix")
    mech, motor = _projector_mech(
        "p16:mech", n, 24.0, (650.0, 3400.0),
        [(0.0, 1.0, 1.1), (2.1, 0.7, 0.9), (4.3, 0.35, 0.7)],
        55.0, [(1, 1.0), (2, 0.55), (3, 0.3), (4, 0.15), (6, 0.08)],
        (90.0, 420.0), 0.5)
    # fan whoosh, shutter-modulated, decorrelated
    wh = decor_noise(rng("p16:whoosh"), n)
    wh = U.lowpass(U.highpass(wh, 70.0, SR, 1), 950.0, SR, order=2)
    t = t_axis(n)
    wh *= (1.0 + 0.09 * np.sin(2 * np.pi * 24.0 * t) + 0.05 * np.sin(2 * np.pi * 48.0 * t))[:, None].astype(np.float32)
    wh /= U.rms(wh) + 1e-9
    # tiny reel squeaks, rare and faint
    squeak = np.zeros(n, np.float32)
    for t0 in U.event_times(rng("p16:squeak"), 9.0, n / SR, min_gap_s=1.5):
        L = int(g.uniform(0.15, 0.4) * SR)
        s = int(t0 * SR)
        tt = np.arange(min(L, n - s)) / SR
        f0 = g.uniform(1400.0, 2600.0)
        sq = np.sin(2 * np.pi * f0 * (1 + 0.02 * np.sin(2 * np.pi * 11 * tt)) * tt)
        sq *= np.sin(np.linspace(0, np.pi, len(tt))) ** 2 * g.uniform(0.02, 0.05)
        U.add_at(squeak, sq.astype(np.float32), s)
    mono_mech = mech * 1.15 + motor * 0.55
    # transport speed wander on the mechanics (the projector 'breathes')
    sp = 1.0 + 0.0035 * U.control_noise(rng("p16:speed"), n, SR, 0.15, 0.55, ctrl_sr=100.0)
    mono_mech = U.variable_speed(mono_mech[:, None], sp)[:, 0]
    breathe = wander(rng("p16:breathe"), n, 0.06, 0.25, 0.12).astype(np.float32)
    mono_mech *= breathe
    x = stereoize(mono_mech, 0.4) * 0.9 + wh * 0.5 + stereoize(squeak, 0.2)
    x = room_smear(x, (13.1, 17.3, 21.9), 0.28, 0.62, 0.35)  # small hard room
    return set_rms(U.lowpass(x, 9000.0, SR, 2), -20.0)


def bake_projector_8mm_run() -> np.ndarray:
    n = n_for(16.0)
    mech, motor = _projector_mech(
        "p8:mech", n, 18.0, (500.0, 2900.0),
        [(0.0, 1.0, 0.9), (2.6, 0.8, 0.8), (5.2, 0.3, 0.6)],
        50.0, [(1, 1.0), (2, 0.7), (3, 0.35), (4, 0.18), (5, 0.1)],
        (110.0, 520.0), 0.65)
    # die-cast body tick: light 36 Hz secondary train
    g = rng("p8:tick")
    kern = impact_kernel(g, [(0.0, 1.0, 0.5)], (2000.0, 4200.0), dur_ms=2.5)
    tick = sps.fftconvolve(pulse_train(g, n, 36.0, 1.3, 0.6), kern)[:n].astype(np.float32)
    tick /= np.percentile(np.abs(tick), 99.5) + 1e-9
    wh = decor_noise(rng("p8:whoosh"), n)
    wh = U.lowpass(U.highpass(wh, 90.0, SR, 1), 800.0, SR, order=2)
    wh /= U.rms(wh) + 1e-9
    mono = mech * 1.2 + motor * 0.75 + tick * 0.28
    sp = 1.0 + 0.005 * U.control_noise(rng("p8:speed"), n, SR, 0.2, 0.8, ctrl_sr=100.0)
    mono = U.variable_speed(mono[:, None], sp)[:, 0]
    mono *= wander(rng("p8:breathe"), n, 0.08, 0.3, 0.14).astype(np.float32)
    x = stereoize(mono, 0.3) * 0.95 + wh * 0.4
    x = room_smear(x, (9.7, 12.9, 16.3), 0.22, 0.7, 0.3)  # living room, close
    return set_rms(U.lowpass(x, 8000.0, SR, 2), -20.0)


def bake_projector_35mm_booth() -> np.ndarray:
    n = n_for(16.0)
    g = rng("p35:mix")
    mech, motor = _projector_mech(
        "p35:mech", n, 24.0, (280.0, 1100.0),
        [(0.0, 1.0, 1.6), (3.0, 0.6, 1.2)],
        40.0, [(1, 1.0), (2, 0.6), (3, 0.35), (4, 0.2), (6, 0.1)],
        (60.0, 260.0), 0.8)
    # heavy building rumble under the booth
    rum = rng("p35:rumble").standard_normal(n).astype(np.float32)
    rum = U.lowpass(rum[:, None], 130.0, SR, order=3)[:, 0]
    rum *= wander(rng("p35:rumwander"), n, 0.05, 0.2, 0.3).astype(np.float32)
    rum /= U.rms(rum) + 1e-9
    vent = decor_noise(rng("p35:vent"), n)
    vent = U.lowpass(U.highpass(vent, 50.0, SR, 1), 500.0, SR, order=2)
    vent /= U.rms(vent) + 1e-9
    mono = mech * 0.5 + motor * 0.9 + rum * 0.8
    x = stereoize(mono, 0.6, 0.9) + vent * 0.45
    x = U.lowpass(x, 1300.0, SR, order=3)  # through the booth wall
    x = room_smear(x, (53.9, 67.1, 79.7), 1.1, 0.8, 0.5)  # big hard space
    return set_rms(x, -21.0)


# ── electric environments ───────────────────────────────────────────────

def bake_tv_shop_wall() -> np.ndarray:
    n = n_for(16.0)
    g = rng("tvwall:mix")
    x = np.zeros((n, 2), np.float32)
    n_sets = 5
    for i in range(n_sets):
        gi = rng(f"tvwall:set{i}")
        f0 = 60.0 * (1.0 + gi.uniform(-0.003, 0.003))  # each set slightly off
        ph = running_phase(f0 * wander(gi, n, 0.02, 0.15, 0.001), n)
        buzz = np.zeros(n, np.float64)
        tiltp = gi.uniform(1.0, 1.6)
        for k in range(1, 24):
            a = (1.0 / k ** tiltp) * (1.0 if k % 2 else 0.35)
            buzz += a * np.sin(k * ph + gi.uniform(0, 2 * np.pi) * (0 if k == 1 else 1))
        b = U.highpass(buzz.astype(np.float32)[:, None], 45.0, SR, 1)[:, 0]
        b *= wander(gi, n, 0.08, 0.5, 0.12).astype(np.float32)
        b /= U.rms(b) + 1e-9
        b *= U.db_to_lin(gi.uniform(-14.0, -6.0))
        # its flyback/PSU whine - aging sets sag below 15.7 kHz
        fw = gi.uniform(0.88, 1.0) * 15734.0
        whine = np.sin(running_phase(fw * wander(gi, n, 0.03, 0.2, 0.0004), n))
        whine += 0.5 * np.sin(running_phase(fw / 2.0, n) + gi.uniform(0, 2 * np.pi))
        whine = whine.astype(np.float32) * U.db_to_lin(gi.uniform(-30.0, -22.0))
        pan = gi.uniform(0.1, 0.9)
        st = np.stack([b * np.sqrt(1 - pan) + whine * np.sqrt(1 - pan),
                       b * np.sqrt(pan) + whine * np.sqrt(pan)], axis=1)
        x += st
    room = decor_noise(rng("tvwall:room"), n)
    room = U.lowpass(U.highpass(room, 60.0, SR, 1), 900.0, SR, order=2)
    room /= U.rms(room) + 1e-9
    x = x / (np.percentile(np.abs(x), 99.5) + 1e-9) + room * 0.30
    x = room_smear(x, (23.3, 29.9, 37.1), 0.5, 0.55, 0.4)
    return set_rms(x, -22.0)


def bake_fluorescent_office() -> np.ndarray:
    n = n_for(14.0)
    g = rng("fluor:buzz")
    ph = running_phase(120.0 * wander(g, n, 0.02, 0.12, 0.0008), n)
    buzz = np.zeros(n, np.float64)
    for k in range(1, 22):
        a = 1.0 / (k ** 1.05)
        if k % 2 == 0:
            a *= 0.75  # rectified supply: strong evens
        buzz += a * np.sin(k * ph + g.uniform(0, 2 * np.pi) * (0 if k == 1 else 1))
    b = U.highpass(buzz.astype(np.float32)[:, None], 70.0, SR, 1)[:, 0]
    b = U.apply_sos(b[:, None], U.peaking(SR, 720.0, 5.0, q=2.2))[:, 0]  # fixture tin
    # ballast instability: fast shimmer + occasional half-second surges
    shim = (1.0 + 0.05 * U.control_noise(g, n, SR, 6.0, 16.0, ctrl_sr=200.0)).astype(np.float32)
    surge = np.zeros(n, np.float32)
    for t0 in U.event_times(rng("fluor:surge"), 8.0, n / SR, min_gap_s=1.0):
        L = int(g.uniform(0.3, 0.8) * SR)
        s = int(t0 * SR)
        e = min(s + L, n)
        if e > s:
            surge[s:e] = np.maximum(surge[s:e],
                                    (np.sin(np.linspace(0, np.pi, e - s)) ** 2 * g.uniform(0.1, 0.25)).astype(np.float32))
    b *= shim * (1.0 + surge)
    b /= U.rms(b) + 1e-9
    vent = decor_noise(rng("fluor:vent"), n)
    vent = U.lowpass(U.highpass(vent, 90.0, SR, 1), 2200.0, SR, order=2)
    vent = U.tilt(vent, SR, -4.0, pivot_hz=800.0)
    vent *= wander(rng("fluor:ventw"), n, 0.05, 0.2, 0.15)[:, None].astype(np.float32)
    vent /= U.rms(vent) + 1e-9
    x = stereoize(b, 0.25, 0.9) * 0.8 + vent * 0.75
    return set_rms(x, -22.0)


def bake_vcr_transport() -> np.ndarray:
    n = n_for(16.0)
    g = rng("vcr:whine")
    # head drum: 1798.2 Hz (29.97 Hz drum x 60), AM'd at the drum rate,
    # with brief servo corrections dipping the pitch
    f_base = 1798.2
    fmod = wander(g, n, 0.05, 0.3, 0.0004)
    servo = np.zeros(n, np.float64)
    tickbed = np.zeros(n, np.float32)
    for t0 in U.event_times(rng("vcr:servo"), 12.0, n / SR, min_gap_s=1.2):
        L = int(g.uniform(0.2, 0.5) * SR)
        s = int(t0 * SR)
        e = min(s + L, n)
        if e <= s:
            continue
        dip = np.sin(np.linspace(0, np.pi, e - s)) ** 2
        servo[s:e] -= 0.006 * dip * g.uniform(0.5, 1.0)
        L2 = max(int(0.004 * SR), 32)
        tk = g.standard_normal(L2).astype(np.float32) * np.exp(-np.arange(L2) / (L2 / 6))
        tk = U.bandpass(tk[:, None], 900.0, 3800.0, SR, order=2)[:, 0]
        U.add_at(tickbed, tk * 0.03 / (np.max(np.abs(tk)) + 1e-9), s)
    ph = running_phase(f_base * (fmod + servo), n)
    t = t_axis(n)
    drum_am = (1.0 + 0.08 * np.sin(2 * np.pi * 29.97 * t + 0.4)).astype(np.float32)
    whine = (np.sin(ph) + 0.35 * np.sin(2 * ph + 1.1) + 0.15 * np.sin(3 * ph + 2.3)).astype(np.float32)
    whine *= drum_am
    whine /= U.rms(whine) + 1e-9
    # capstan/loading motor + spindle whir
    hum = tone_stack(running_phase(120.0, n), [(1, 1.0), (2, 0.4), (3, 0.2)])
    hum /= U.rms(hum) + 1e-9
    whir = rng("vcr:whir").standard_normal(n).astype(np.float32)
    whir = U.bandpass(whir[:, None], 200.0, 750.0, SR, order=2)[:, 0]
    whir *= wander(rng("vcr:whirw"), n, 0.1, 0.5, 0.2).astype(np.float32)
    whir /= U.rms(whir) + 1e-9
    hiss = decor_noise(rng("vcr:hiss"), n)
    hiss = U.tilt(hiss, SR, 4.0, pivot_hz=2500.0)
    hiss = U.lowpass(hiss, 12000.0, SR, order=3)
    hiss /= U.rms(hiss) + 1e-9
    mono = whine * 0.42 + hum * 0.34 + whir * 0.42 + tickbed
    x = stereoize(mono, 0.3, 0.96) + hiss * 0.5
    return set_rms(x, -23.0)


def bake_record_surface_loop() -> np.ndarray:
    n = n_for(14.0)
    g = rng("recsurf:main")
    rum = g.standard_normal(n).astype(np.float32)
    rum = U.lowpass(rum[:, None], 32.0, SR, order=4)[:, 0]
    rum /= U.rms(rum) + 1e-9
    # crackle: sparse clicks, mid-dull, a couple of ringing pops
    imp = np.zeros(n, np.float32)
    k = int(g.poisson(3.0 * n / SR))
    idx = g.integers(0, n, k)
    amp = (g.random(k) ** 1.9) * np.where(g.random(k) < 0.5, -1, 1)
    np.add.at(imp, idx, amp.astype(np.float32))
    crk = U.bandpass(imp[:, None], 900.0, 6500.0, SR, order=2)[:, 0] * 3.0
    for t0 in U.event_times(rng("recsurf:pops"), 6.0, n / SR, min_gap_s=1.0):
        L = int(g.uniform(0.02, 0.04) * SR)
        tt = np.arange(L) / SR
        ring = np.sin(2 * np.pi * g.uniform(250.0, 700.0) * tt) * np.exp(-tt / 0.008)
        U.add_at(crk, (ring * g.uniform(0.3, 0.7)).astype(np.float32), int(t0 * SR))
    fry = np.zeros(n, np.float32)
    kf = int(g.poisson(400.0 * n / SR))
    np.add.at(fry, g.integers(0, n, kf), ((g.random(kf) ** 2.2) * np.where(g.random(kf) < 0.5, -1, 1)).astype(np.float32))
    fry = U.bandpass(fry[:, None], 2000.0, 9000.0, SR, order=2)[:, 0]
    fry /= U.rms(fry) + 1e-9
    hiss = decor_noise(rng("recsurf:hiss"), n)
    hiss = U.bandpass(hiss, 500.0, 7500.0, SR, order=2)
    t = t_axis(n)
    swish = (1.0 + 0.07 * np.sin(2 * np.pi * 0.555 * t + 1.1)).astype(np.float32)
    hiss *= swish[:, None]
    hiss /= U.rms(hiss) + 1e-9
    x = stereoize(rum, 0.1, 1.0) * 0.9 + stereoize(crk * 0.55, 0.05) + hiss * 0.22 + stereoize(fry, 0.02) * 0.05
    return set_rms(x, -24.0)


def bake_tape_deck_room() -> np.ndarray:
    n = n_for(14.0)
    g = rng("deck:motor")
    hum = tone_stack(running_phase(100.0 * wander(g, n, 0.03, 0.2, 0.001), n),
                     [(1, 1.0), (2, 0.5), (3, 0.28), (4, 0.12), (6, 0.06)])
    hum /= U.rms(hum) + 1e-9
    whir = rng("deck:whir").standard_normal(n).astype(np.float32)
    whir = U.bandpass(whir[:, None], 260.0, 900.0, SR, order=2)[:, 0]
    t = t_axis(n)
    whir *= (1.0 + 0.18 * np.sin(2 * np.pi * 6.25 * t)).astype(np.float32)  # reel-hub rate
    whir /= U.rms(whir) + 1e-9
    # the tell: noise floor with audible flutter on it
    hiss = decor_noise(rng("deck:hiss"), n)
    hiss = U.tilt(hiss, SR, 5.0, pivot_hz=2500.0)
    hiss = U.lowpass(hiss, 11000.0, SR, order=3)
    flut = (1.0 + 0.13 * np.sin(2 * np.pi * 9.7 * t + 0.7)
            + 0.09 * U.control_noise(rng("deck:flut"), n, SR, 5.0, 16.0, ctrl_sr=200.0))
    hiss *= flut[:, None].astype(np.float32)
    hiss /= U.rms(hiss) + 1e-9
    # counter-roller tick, barely there
    tick = np.zeros(n, np.float32)
    kern = impact_kernel(g, [(0.0, 1.0, 0.6)], (1500.0, 3400.0), dur_ms=2.0)
    tick_train = pulse_train(g, n, 0.75, 2.0, 0.3)
    tick = sps.fftconvolve(tick_train, kern)[:n].astype(np.float32) * 0.02
    room = decor_noise(rng("deck:room"), n)
    room = U.lowpass(room, 420.0, SR, order=2)
    room /= U.rms(room) + 1e-9
    x = stereoize(hum * 0.5 + whir * 0.45 + tick, 0.35, 0.93) + hiss * 0.8 + room * 0.35
    return set_rms(x, -23.0)


def bake_crt_whine() -> np.ndarray:
    n = n_for(12.0)
    g = rng("crt:whine")
    dur = n / SR
    f_line = round(15734.26 * dur) / dur  # integer cycles -> clean loop
    ph = running_phase(f_line * wander(g, n, 0.02, 0.1, 0.00006), n)
    t = t_axis(n)
    am = (1.0 + 0.03 * np.sin(2 * np.pi * 0.21 * t + 0.9)).astype(np.float32)
    line = np.sin(ph).astype(np.float32) * am
    sub = np.sin(ph / 2.0 + 0.6).astype(np.float32) * U.db_to_lin(-9.0)  # 7.87k, laptop-audible
    buzz = tone_stack(running_phase(60.0, n), [(1, 1.0), (2, 0.45), (3, 0.3), (5, 0.12)])
    buzz /= U.rms(buzz) + 1e-9
    hiss = decor_noise(rng("crt:hiss"), n)
    hiss = U.lowpass(hiss, 14000.0, SR, order=2)
    hiss /= U.rms(hiss) + 1e-9
    mono = line + sub
    mono /= U.rms(mono) + 1e-9
    x = stereoize(mono, 0.05, 0.99) + stereoize(buzz, 0.3) * U.db_to_lin(-26.0) + hiss * U.db_to_lin(-34.0)
    return set_rms(x, -26.0)


def bake_air_handler_hall() -> np.ndarray:
    n = n_for(18.0)
    g = rng("hall:hvac")
    rum = g.standard_normal(n).astype(np.float32)
    rum = U.lowpass(rum[:, None], 110.0, SR, order=3)[:, 0]
    blade = tone_stack(running_phase(24.8 * wander(g, n, 0.03, 0.15, 0.004), n),
                       [(1, 1.0), (2, 0.5), (3, 0.3), (4, 0.15)])
    blade /= U.rms(blade) + 1e-9
    rum = rum / (U.rms(rum) + 1e-9) + blade * 0.4
    duct = decor_noise(rng("hall:duct"), n)
    duct = U.bandpass(duct, 130.0, 1400.0, SR, order=2)
    duct = U.tilt(duct, SR, -3.0, pivot_hz=600.0)
    swell = wander(rng("hall:swell"), n, 0.04, 0.16, 0.3)
    duct *= swell[:, None].astype(np.float32)
    duct /= U.rms(duct) + 1e-9
    # far-off voices: speech-shaped noise only, heavily lowpassed
    mur = U.speech_murmur(rng("hall:murmur"), n, SR, syllable_hz=(2.0, 5.0))
    mur = U.lowpass(mur[:, None], 700.0, SR, order=3)[:, 0]
    mur /= U.rms(np.abs(mur) + 1e-6) + 1e-9
    # one distant door thud for life (quiet; the loop crossfade keeps it clean)
    thud = np.zeros(n, np.float32)
    L = int(0.5 * SR)
    tt = np.arange(L) / SR
    td = np.sin(2 * np.pi * 55.0 * tt) * np.exp(-tt / 0.09) + 0.3 * np.sin(2 * np.pi * 130.0 * tt) * np.exp(-tt / 0.04)
    U.add_at(thud, (td * 0.5).astype(np.float32), int(n * 0.62))
    wet = np.stack([duct[:, 0] + mur * 0.5 + thud, duct[:, 1] + mur * 0.48 + thud], axis=1)
    wet = room_smear(wet, (67.9, 77.3, 89.9, 103.3), 2.2, 0.85, 0.6)  # long hall tail
    x = stereoize(rum, 0.8, 0.97) * 1.1 + wet * 0.8
    x = U.lowpass(x, 4500.0, SR, order=2)
    return set_rms(x, -21.0)


BEDS = {
    "projector_16mm_run": bake_projector_16mm_run,
    "projector_8mm_run": bake_projector_8mm_run,
    "projector_35mm_booth": bake_projector_35mm_booth,
    "tv_shop_wall": bake_tv_shop_wall,
    "fluorescent_office": bake_fluorescent_office,
    "vcr_transport": bake_vcr_transport,
    "record_surface_loop": bake_record_surface_loop,
    "tape_deck_room": bake_tape_deck_room,
    "crt_whine": bake_crt_whine,
    "air_handler_hall": bake_air_handler_hall,
}


def bake(name: str) -> str:
    x = BEDS[name]()
    x = U.highpass(x, 22.0, SR, order=2)  # no DC into the loop fold
    x = loop_fold(x)
    peak = float(np.max(np.abs(x))) + 1e-12
    x = x * (PEAK / peak)  # exact −12.04 dBFS peak
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{name}.wav")
    wavfile.write(path, SR, (np.clip(x, -1.0, 1.0) * 32767.0).astype(np.int16))
    return path


def main(argv: list[str]) -> int:
    if "--list" in argv:
        print("\n".join(BEDS))
        return 0
    names = [a for a in argv if not a.startswith("-")] or list(BEDS)
    unknown = [nm for nm in names if nm not in BEDS]
    if unknown:
        print(f"unknown bed(s): {', '.join(unknown)}; use --list")
        return 1
    for nm in names:
        p = bake(nm)
        sz = os.path.getsize(p) / 1e6
        info = wavfile.read(p)[1]
        print(f"  baked {nm}: {info.shape[0]/SR:.1f}s stereo, {sz:.1f} MB -> {p}")
    print(f"done: {len(names)} bed(s) in {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
