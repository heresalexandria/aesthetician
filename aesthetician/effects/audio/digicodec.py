"""Early-digital artifacts: real lossy codec round-trips (mp3, telephony),
bitcrushing, and buffer glitches."""

from __future__ import annotations

import functools
import subprocess

import numpy as np

from ...engine import media
from ...engine.graph import Context, Effect, Param, register
from ...engine.rng import stream
from . import _util as U


@functools.lru_cache(maxsize=1)
def _available_encoders() -> frozenset:
    try:
        out = subprocess.run(
            [media.FFMPEG, "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=15,
        ).stdout
    except Exception:
        return frozenset()
    names = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].startswith("A"):
            names.add(parts[1])
    return frozenset(names)


@register
class ACodecMp3(Effect):
    eid = "a_codec_mp3"
    label = "MP3 Codec"
    kind = "audio_filepass"
    desc = "Real libmp3lame encode/decode round-trip; low bitrates give the authentic swirly 2000s artifacts."
    PARAMS = (
        Param("kbps", "Bitrate", "enum", "24",
              choices=("8", "16", "24", "32", "48", "64", "96", "128"),
              desc="MP3 bitrate; 8–32 kbps is the heavily artifacted zone.", group="Bandwidth"),
        Param("mono", "Mono", "bool", True,
              desc="Encode mono (typical for low-rate files).", group="Bandwidth"),
    )
    # lame needs MPEG-2/2.5 sample rates for very low bitrates
    _FORCE_SR = {"8": 12000, "16": 16000, "24": 22050, "32": 24000}

    def prepare(self, ctx: Context) -> None:
        if "libmp3lame" not in _available_encoders():
            raise RuntimeError("a_codec_mp3 requires the ffmpeg libmp3lame encoder, which is not available in this ffmpeg build")

    def file_pass(self, in_path: str, out_path: str, ctx: Context) -> None:
        k = self.v["kbps"]
        args = ["-c:a", "libmp3lame", "-b:a", f"{k}k"]
        if k in self._FORCE_SR:
            args += ["-ar", str(self._FORCE_SR[k])]
        if self.v["mono"]:
            args += ["-ac", "1"]
        media.audio_roundtrip(in_path, out_path, args, mid_ext="mp3")


@register
class ACodecSpeech(Effect):
    eid = "a_codec_speech"
    label = "Speech Codec"
    kind = "audio_filepass"
    desc = "Real telephony codec round-trip at 8 kHz (G.726 ADPCM, AMR-NB, GSM, G.711, IMA ADPCM) — genuine cell/VoIP-era grit."
    # choice: (encoder, extra args, container ext, sample rate)
    _CODECS = {
        "g726_16": ("g726", ["-b:a", "16k"], "wav", 8000),
        "g726_24": ("g726", ["-b:a", "24k"], "wav", 8000),
        "g726_32": ("g726", ["-b:a", "32k"], "wav", 8000),
        "g726_40": ("g726", ["-b:a", "40k"], "wav", 8000),
        "amr_475": ("libopencore_amrnb", ["-b:a", "4750"], "amr", 8000),
        "amr_74": ("libopencore_amrnb", ["-b:a", "7400"], "amr", 8000),
        "amr_122": ("libopencore_amrnb", ["-b:a", "12200"], "amr", 8000),
        "gsm": ("libgsm", [], "gsm", 8000),
        "mulaw_8k": ("pcm_mulaw", [], "wav", 8000),
        "alaw_8k": ("pcm_alaw", [], "wav", 8000),
        "adpcm_ima_22k": ("adpcm_ima_wav", [], "wav", 22050),
    }
    PARAMS = (
        Param("codec", "Codec", "enum", "amr_74", choices=tuple(_CODECS),
              desc="Telephony codec and rate; amr_475 ≈ 2003 cellphone at one bar.", group="Bandwidth"),
    )

    def prepare(self, ctx: Context) -> None:
        enc = self._CODECS[self.v["codec"]][0]
        avail = _available_encoders()
        if enc not in avail:
            alts = sorted(c for c, spec in self._CODECS.items() if spec[0] in avail)
            raise RuntimeError(
                f"a_codec_speech: codec '{self.v['codec']}' needs ffmpeg encoder '{enc}', "
                f"which is not available. Available choices here: {', '.join(alts) or 'none'}"
            )

    def file_pass(self, in_path: str, out_path: str, ctx: Context) -> None:
        enc, extra, ext, rate = self._CODECS[self.v["codec"]]
        args = ["-ar", str(rate), "-ac", "1", "-c:a", enc, *extra]
        media.audio_roundtrip(in_path, out_path, args, mid_ext=ext)


@register
class ABitcrush(Effect):
    eid = "a_bitcrush"
    label = "Bitcrush"
    kind = "audio"
    desc = "Word-length and sample-rate reduction: crunchy quantize (optional dither) and zero-order-hold downsampling with audible aliasing."
    PARAMS = (
        Param("bits", "Bits", "int", 8, 3, 16,
              desc="Quantizer word length.", group="Bandwidth"),
        Param("dither", "Dither", "bool", False,
              desc="TPDF dither before quantizing (off = crunchier).", group="Bandwidth"),
        Param("sr_hz", "Sample Rate", "float", 0.0, 0.0, 48000.0, unit="Hz",
              desc="Zero-order-hold resample target; 0 = off.", group="Bandwidth"),
        Param("antialias", "Anti-alias", "bool", False,
              desc="Polite lowpass before the hold (default off — aliasing is the point).", group="Bandwidth"),
        Param("mix", "Mix", "float", 1.0, 0.0, 1.0,
              desc="Dry/wet blend.", group="Dynamics", iscale=True),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n = audio.shape[0]
        x = audio.astype(np.float32)
        srr = self.v["sr_hz"]
        if 0 < srr < ctx.sr:
            if self.v["antialias"]:
                x = U.lowpass(x, srr * 0.45, ctx.sr, order=6)
            step = ctx.sr / srr
            idx = (np.floor(np.arange(n) / step) * step).astype(np.int64)
            x = x[np.clip(idx, 0, n - 1)]
        q = float(2 ** (self.v["bits"] - 1) - 1)
        if self.v["dither"]:
            g = stream(ctx.seed, f"{self.key}:dither")
            x = x + ((g.random(x.shape) - g.random(x.shape)) / q).astype(np.float32)
        x = np.round(np.clip(x, -1.0, 1.0) * q) / q
        m = self.v["mix"]
        out = audio * (1.0 - m) + x.astype(np.float32) * m
        return out.astype(np.float32)


@register
class ADigitalGlitch(Effect):
    eid = "a_digital_glitch"
    label = "Digital Glitch"
    kind = "audio"
    desc = "Early-digital buffer failures: stutter repeats, hard dropout mutes, and single-sample spikes."
    PARAMS = (
        Param("stutter_rate", "Stutters", "float", 2.0, 0.0, 30.0, unit="/min",
              desc="Buffer-repeat events per minute (a 15–60 ms block loops 2–6x).", group="Damage", iscale=True),
        Param("mute_rate", "Mutes", "float", 2.0, 0.0, 60.0, unit="/min",
              desc="Hard 10–80 ms dropouts per minute (with edge clicks).", group="Damage", iscale=True),
        Param("crackle_rate", "Spikes", "float", 4.0, 0.0, 120.0, unit="/min",
              desc="Single-sample digital spikes per minute.", group="Damage", iscale=True),
    )

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        n, ch = audio.shape
        sr = ctx.sr
        x = audio.copy()
        dur = n / sr

        if self.v["stutter_rate"] > 0:
            g = stream(ctx.seed, f"{self.key}:stutter")
            for t0 in U.event_times(g, self.v["stutter_rate"], dur, min_gap_s=0.5):
                L = int(g.uniform(0.015, 0.060) * sr)
                reps = int(g.integers(2, 7))
                s = int(t0 * sr)
                if s + L >= n:
                    continue
                block = x[s : s + L].copy()
                for r in range(1, reps + 1):
                    a = s + r * L
                    if a >= n:
                        break
                    b = min(a + L, n)
                    x[a:b] = block[: b - a]  # hung DMA buffer: overwrite forward

        if self.v["mute_rate"] > 0:
            g = stream(ctx.seed, f"{self.key}:mute")
            for t0 in U.event_times(g, self.v["mute_rate"], dur, min_gap_s=0.3):
                L = int(g.uniform(0.010, 0.080) * sr)
                s = int(t0 * sr)
                e = min(s + L, n)
                if e > s:
                    x[s:e] = 0.0  # abrupt edges = the click

        if self.v["crackle_rate"] > 0:
            g = stream(ctx.seed, f"{self.key}:spike")
            k = int(g.poisson(self.v["crackle_rate"] / 60.0 * dur))
            if k > 0:
                idx = g.integers(0, n, k)
                amp = g.uniform(0.2, 0.7, k) * np.where(g.random(k) < 0.5, -1, 1)
                for i, a in zip(idx, amp):
                    x[i] = np.clip(x[i] + a, -0.98, 0.98)
        return x.astype(np.float32)
