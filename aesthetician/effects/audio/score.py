"""Procedural period scoring mixed under the source program.

The score is built from short, deterministic orchestral gestures rather than a
baked loop. Notes are anchored to the clip timeline, so a preview taken from the
middle of a clip hears the same phrase as the full export at that moment.
"""

from __future__ import annotations

import numpy as np

from ...engine.graph import Context, Effect, Param, register
from ...engine.rng import stream
from . import _util as U


_STYLES = ("japanese_spectacle_1962", "fantasy_sitcom_1964", "adventure_1985")


def _midi(note: float) -> float:
    return 440.0 * 2.0 ** ((note - 69.0) / 12.0)


def _degree(root: int, scale: tuple[int, ...], degree: int) -> float:
    octave, index = divmod(degree, len(scale))
    return _midi(root + scale[index] + 12 * octave)


def _pan_weights(channels: int, pan: float) -> np.ndarray:
    if channels <= 1:
        return np.ones(1, np.float32)
    angle = (float(np.clip(pan, -1.0, 1.0)) + 1.0) * np.pi / 4.0
    weights = np.full(channels, 0.35, np.float32)
    weights[0] = np.cos(angle)
    weights[1] = np.sin(angle)
    return weights


def _envelope(t: np.ndarray, duration: float, attack: float, release: float,
              decay: float = 0.0) -> np.ndarray:
    env = np.minimum(t / max(attack, 1e-4), 1.0)
    env *= np.minimum(np.maximum(duration - t, 0.0) / max(release, 1e-4), 1.0)
    if decay > 0:
        env *= np.exp(-t / decay)
    return env.astype(np.float32)


def _voice(t: np.ndarray, hz: float, timbre: str) -> np.ndarray:
    phase = 2.0 * np.pi * hz * t
    if timbre == "strings":
        vibrato = 0.035 * np.sin(2.0 * np.pi * 5.2 * t)
        p = phase + vibrato
        wave = (np.sin(p) + 0.38 * np.sin(2.0 * p) + 0.20 * np.sin(3.0 * p)
                + 0.10 * np.sin(4.0 * p))
    elif timbre == "brass":
        wave = np.tanh(1.35 * (np.sin(phase) + 0.48 * np.sin(2.0 * phase)
                               + 0.22 * np.sin(3.0 * phase)))
    elif timbre == "clarinet":
        wave = np.sin(phase) + 0.42 * np.sin(3.0 * phase) + 0.16 * np.sin(5.0 * phase)
    elif timbre == "flute":
        wave = np.sin(phase) + 0.16 * np.sin(2.0 * phase) + 0.07 * np.sin(3.0 * phase)
    elif timbre == "vibes":
        wave = np.sin(phase) + 0.32 * np.sin(3.01 * phase) + 0.15 * np.sin(5.04 * phase)
    elif timbre == "celesta":
        wave = np.sin(phase) + 0.42 * np.sin(2.01 * phase) + 0.20 * np.sin(4.03 * phase)
    elif timbre == "pizzicato":
        wave = np.sin(phase) + 0.36 * np.sin(2.0 * phase) + 0.14 * np.sin(3.0 * phase)
    elif timbre == "harp":
        wave = np.sin(phase) + 0.30 * np.sin(2.0 * phase) + 0.18 * np.sin(3.0 * phase)
    elif timbre == "synth":
        wave = (np.sin(phase) + 0.28 * np.sin(2.0 * phase)
                + 0.14 * np.sin(3.0 * phase) + 0.08 * np.sin(4.0 * phase))
    else:  # upright or orchestral bass
        wave = np.sin(phase) + 0.24 * np.sin(2.0 * phase) + 0.08 * np.sin(3.0 * phase)
    return wave.astype(np.float32)


def _note(score: np.ndarray, ctx: Context, start: float, duration: float, hz: float,
          amplitude: float, timbre: str, pan: float = 0.0) -> None:
    sr = ctx.sr
    local_start = start - ctx.t0
    i0 = max(int(np.floor(local_start * sr)), 0)
    i1 = min(int(np.ceil((local_start + duration) * sr)), len(score))
    if i1 <= i0:
        return
    t = np.arange(i0, i1, dtype=np.float64) / sr - local_start
    if timbre in ("pizzicato", "harp"):
        env = _envelope(t, duration, 0.004, min(0.12, duration * 0.4), decay=max(duration * 0.32, 0.04))
    elif timbre in ("vibes", "celesta"):
        env = _envelope(t, duration, 0.006, min(0.25, duration * 0.45), decay=max(duration * 0.75, 0.12))
    elif timbre == "brass":
        env = _envelope(t, duration, 0.025, min(0.15, duration * 0.35))
    elif timbre == "synth":
        env = _envelope(t, duration, min(0.35, duration * 0.25), min(0.5, duration * 0.35))
    else:
        env = _envelope(t, duration, min(0.08, duration * 0.2), min(0.2, duration * 0.35))
    tone = _voice(t, hz, timbre) * env * np.float32(amplitude)
    score[i0:i1] += tone[:, None] * _pan_weights(score.shape[1], pan)[None, :]


def _hit(score: np.ndarray, ctx: Context, start: float, kind: str, amplitude: float,
         event_id: str, pan: float = 0.0) -> None:
    sr = ctx.sr
    durations = {"timpani": 0.72, "snare": 0.20, "brush": 0.30, "cymbal": 1.8}
    duration = durations[kind]
    local_start = start - ctx.t0
    i0 = max(int(np.floor(local_start * sr)), 0)
    i1 = min(int(np.ceil((local_start + duration) * sr)), len(score))
    if i1 <= i0:
        return
    full_n = max(int(np.ceil(duration * sr)), 1)
    offset = max(-int(np.floor(local_start * sr)), 0)
    count = i1 - i0
    t_full = np.arange(full_n, dtype=np.float64) / sr
    rng = stream(ctx.seed, f"{event_id}:{kind}")
    if kind == "timpani":
        phase = 2.0 * np.pi * (72.0 * t_full + 13.0 * (1.0 - np.exp(-t_full * 8.0)) / 8.0)
        sound = np.sin(phase) * np.exp(-t_full * 4.2)
        sound += rng.standard_normal(full_n) * np.exp(-t_full * 15.0) * 0.08
    else:
        noise = rng.standard_normal(full_n).astype(np.float32)[:, None]
        if kind == "snare":
            sound = U.bandpass(noise, 900.0, 9000.0, sr, order=2)[:, 0]
            sound *= np.exp(-t_full * 20.0)
        elif kind == "brush":
            sound = U.bandpass(noise, 1800.0, 11000.0, sr, order=1)[:, 0]
            sound *= np.exp(-t_full * 10.0)
        else:
            sound = U.highpass(noise, 3500.0, sr, order=2)[:, 0]
            sound *= np.exp(-t_full * 2.4)
    sound = sound.astype(np.float32)
    peak = float(np.max(np.abs(sound))) + 1e-9
    sound = sound / peak * np.float32(amplitude)
    segment = sound[offset:offset + count]
    if len(segment) < count:
        segment = np.pad(segment, (0, count - len(segment)))
    score[i0:i1] += segment[:, None] * _pan_weights(score.shape[1], pan)[None, :]


@register
class APeriodScore(Effect):
    eid = "a_period_score"
    label = "Period Orchestral Score"
    kind = "audio"
    desc = ("Continuous procedural scoring with era-specific orchestration: 1962 Japanese spectacle, "
            "1964 fantasy sitcom, or 1985 adventure feature. The phrase stays locked to the clip timeline.")
    PARAMS = (
        Param("style", "Score Style", "enum", "japanese_spectacle_1962", choices=_STYLES,
              group="Orchestration", desc="Period ensemble, motif language and rhythmic arrangement."),
        Param("level_db", "Music Level", "float", -24.0, -60.0, -12.0, unit="dB",
              group="Mix", desc="Approximate score level under the source program."),
        Param("energy", "Energy", "float", 0.7, 0.0, 1.0, group="Orchestration",
              desc="Raises tempo and shifts the arrangement toward brass and percussion."),
        Param("duck", "Dialogue Ducking", "float", 0.35, 0.0, 1.0, group="Mix",
              desc="Lowers the score by up to 10 dB under loud source dialogue."),
    )

    _CONFIG = {
        "japanese_spectacle_1962": dict(tempo=128.0, root=50,
                                          scale=(0, 2, 3, 5, 7, 8, 10),
                                          progression=(0, 0, 5, 3, 0, 6, 5, 4)),
        "fantasy_sitcom_1964": dict(tempo=112.0, root=60,
                                      scale=(0, 2, 4, 5, 7, 9, 11),
                                      progression=(0, 3, 4, 0, 5, 3, 1, 4)),
        "adventure_1985": dict(tempo=122.0, root=55,
                                 scale=(0, 2, 4, 5, 7, 9, 10),
                                 progression=(0, 4, 5, 3, 0, 6, 3, 4)),
    }
    # Measured RMS of each unscaled arrangement. Separate calibration keeps the
    # Music Level dial honest even though pizzicato sitcom writing is naturally
    # much sparser than a string-and-timpani adventure bed.
    _NOMINAL_RMS = {
        "japanese_spectacle_1962": 0.106,
        "fantasy_sitcom_1964": 0.059,
        "adventure_1985": 0.107,
    }

    def _timing(self, ctx: Context) -> tuple[dict, float, range]:
        cfg = self._CONFIG[self.v["style"]]
        tempo = cfg["tempo"] * (0.88 + 0.20 * self.v["energy"])
        beat = 60.0 / tempo
        start, end = ctx.t0, ctx.t0 + len(self._score) / ctx.sr
        first = int(np.floor((start - 8.0 * beat) / beat))
        if ctx.t0 <= 0:
            first = max(first, 0)
        last = int(np.ceil(end / beat)) + 1
        return cfg, beat, range(first, last)

    def _jitter(self, ctx: Context, style: str, beat_index: int, lane: str) -> float:
        rng = stream(ctx.seed, f"{self.key}:{style}:{lane}:{beat_index}")
        return float(rng.uniform(-0.010, 0.010))

    def _japanese(self, ctx: Context) -> None:
        cfg, beat_s, beats = self._timing(ctx)
        energy = self.v["energy"]
        motif = (0, 2, 1, 0, 5, 3, 1, -1)
        for bi in beats:
            bar, beat = divmod(bi, 4)
            root_deg = cfg["progression"][bar % len(cfg["progression"])]
            t = bi * beat_s + self._jitter(ctx, "jp", bi, "pulse")
            for off, degree in ((0.0, root_deg), (0.5, root_deg + 4)):
                _note(self._score, ctx, t + off * beat_s, 0.43 * beat_s,
                      _degree(cfg["root"] - 12, cfg["scale"], degree), 0.14,
                      "strings", -0.25 if off == 0 else 0.25)
            _note(self._score, ctx, t, 0.92 * beat_s,
                  _degree(cfg["root"] + 12, cfg["scale"], motif[bi % len(motif)]),
                  0.12, "clarinet" if bar % 4 in (1, 2) else "brass", 0.20)
            _hit(self._score, ctx, t, "snare", 0.045 + 0.045 * energy,
                 f"{self.key}:jp:{bi}", pan=0.15)
            if beat in (0, 2):
                _hit(self._score, ctx, t, "timpani", 0.16 + 0.08 * energy,
                     f"{self.key}:jp:{bi}", pan=-0.15)
            if beat == 0:
                for degree, pan in ((root_deg, -0.32), (root_deg + 4, 0.32)):
                    _note(self._score, ctx, t, 3.7 * beat_s,
                          _degree(cfg["root"] - 12, cfg["scale"], degree), 0.075,
                          "strings", pan)
                if bar % 2 == 0:
                    for degree, pan in ((root_deg, -0.4), (root_deg + 4, 0.4)):
                        _note(self._score, ctx, t, 0.42 * beat_s,
                              _degree(cfg["root"] + 5, cfg["scale"], degree),
                              0.13 + 0.08 * energy, "brass", pan)
                if bar % 4 == 0:
                    _hit(self._score, ctx, t, "cymbal", 0.11 + 0.06 * energy,
                         f"{self.key}:jp:{bi}")

    def _sitcom(self, ctx: Context) -> None:
        cfg, beat_s, beats = self._timing(ctx)
        energy = self.v["energy"]
        motif = (2, 4, 5, 4, 1, 2, 0, 4)
        for bi in beats:
            bar, beat = divmod(bi, 4)
            root_deg = cfg["progression"][bar % len(cfg["progression"])]
            t = bi * beat_s + self._jitter(ctx, "sitcom", bi, "rhythm")
            for off, degree, pan in ((0.0, root_deg + 2, -0.35),
                                     (0.5, root_deg + 4, 0.35)):
                _note(self._score, ctx, t + off * beat_s, 0.36 * beat_s,
                      _degree(cfg["root"], cfg["scale"], degree), 0.12,
                      "pizzicato", pan)
            _note(self._score, ctx, t, 0.82 * beat_s,
                  _degree(cfg["root"] + 12, cfg["scale"], motif[bi % len(motif)]),
                  0.085, "flute" if bar % 2 == 0 else "clarinet", 0.28)
            _hit(self._score, ctx, t, "brush", 0.035 + 0.025 * energy,
                 f"{self.key}:sitcom:{bi}", pan=-0.1)
            if beat in (1, 3):
                _note(self._score, ctx, t, 1.15 * beat_s,
                      _degree(cfg["root"] + 12, cfg["scale"], root_deg + 4),
                      0.065, "vibes" if bar % 2 else "celesta", 0.38)
            if beat in (0, 2):
                _note(self._score, ctx, t, 0.8 * beat_s,
                      _degree(cfg["root"] - 12, cfg["scale"], root_deg),
                      0.10, "bass", -0.2)
            if beat == 0:
                for degree, pan in ((root_deg, -0.3), (root_deg + 2, 0.0), (root_deg + 4, 0.3)):
                    _note(self._score, ctx, t, 3.6 * beat_s,
                          _degree(cfg["root"] - 12, cfg["scale"], degree),
                          0.026, "strings", pan)
                if bar % 4 == 0:
                    for gi in range(7):
                        _note(self._score, ctx, t + gi * 0.075, 0.42,
                              _degree(cfg["root"] + 12, cfg["scale"], root_deg + gi),
                              0.045, "harp", -0.55 + gi * 0.18)
            if beat == 3 and bar % 4 == 3:
                for degree, pan in ((root_deg + 2, -0.3), (root_deg + 4, 0.3)):
                    _note(self._score, ctx, t, 0.55 * beat_s,
                          _degree(cfg["root"] + 5, cfg["scale"], degree),
                          0.08 + 0.05 * energy, "brass", pan)

    def _adventure(self, ctx: Context) -> None:
        cfg, beat_s, beats = self._timing(ctx)
        energy = self.v["energy"]
        motif = (0, 2, 4, 5, 4, 2, 1, -1)
        for bi in beats:
            bar, beat = divmod(bi, 4)
            root_deg = cfg["progression"][bar % len(cfg["progression"])]
            t = bi * beat_s + self._jitter(ctx, "adv", bi, "drive")
            for off, degree, pan in ((0.0, root_deg, -0.30), (0.5, root_deg + 4, 0.30)):
                _note(self._score, ctx, t + off * beat_s, 0.44 * beat_s,
                      _degree(cfg["root"], cfg["scale"], degree),
                      0.12 + 0.035 * energy, "strings", pan)
            _note(self._score, ctx, t, 0.86 * beat_s,
                  _degree(cfg["root"] + 12, cfg["scale"], motif[bi % len(motif)]),
                  0.10, "brass" if bar % 4 in (0, 3) else "flute", 0.2)
            _note(self._score, ctx, t, 0.82 * beat_s,
                  _degree(cfg["root"] - 12, cfg["scale"], root_deg),
                  0.11, "bass", -0.2)
            if beat in (0, 2):
                _hit(self._score, ctx, t, "timpani", 0.14 + 0.09 * energy,
                     f"{self.key}:adv:{bi}", pan=-0.15)
            if beat in (1, 3):
                _hit(self._score, ctx, t, "snare", 0.035 + 0.05 * energy,
                     f"{self.key}:adv:{bi}", pan=0.18)
            if beat == 0:
                for degree, pan in ((root_deg, -0.35), (root_deg + 2, 0.0), (root_deg + 4, 0.35)):
                    _note(self._score, ctx, t, 3.65 * beat_s,
                          _degree(cfg["root"] - 12, cfg["scale"], degree),
                          0.052, "strings", pan)
                if bar % 4 == 0:
                    _hit(self._score, ctx, t, "cymbal", 0.10 + 0.07 * energy,
                         f"{self.key}:adv:{bi}")
                    for degree, pan in ((root_deg, -0.25), (root_deg + 4, 0.25)):
                        _note(self._score, ctx, t, 7.4 * beat_s,
                              _degree(cfg["root"] - 12, cfg["scale"], degree),
                              0.032, "synth", pan)

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        if not len(audio):
            return audio.astype(np.float32)
        self._score = np.zeros_like(audio, dtype=np.float32)
        style = self.v["style"]
        if style == "japanese_spectacle_1962":
            self._japanese(ctx)
        elif style == "fantasy_sitcom_1964":
            self._sitcom(ctx)
        else:
            self._adventure(ctx)

        # Fixed calibration preserves the exact level and phrase between a
        # short preview window and the same moment in a full export.
        self._score *= np.float32(U.db_to_lin(self.v["level_db"]) / self._NOMINAL_RMS[style])
        duck = self.v["duck"]
        if duck > 0 and U.rms(audio) > 1e-7:
            env = U.envelope(audio, ctx.sr, attack_ms=25.0, release_ms=550.0, mode="rms")
            ref = np.percentile(env, 90) + 1e-9
            loud = np.clip(env / ref, 0.0, 1.2)
            self._score *= np.power(10.0, (-10.0 * duck * loud) / 20.0)[:, None].astype(np.float32)
        return U.peak_guard(audio + self._score)
