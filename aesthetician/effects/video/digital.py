"""Digital-era degradation: real codec round-trips, bitstream glitches,
palettized computer graphics, DV chroma subsampling, LCD playback surfaces.

`codec_era` and `codec_glitch` shell out to ffmpeg and push the video through
the actual period encoders (MPEG-1/2/4, H.264/AVC, MS-MPEG4 v3,
Sorenson/FLV1, H.263+, MJPEG): the block structure, mosquito noise,
rate-control pulsing and error concealment are produced by the real codecs,
not approximated with filters.
"""

from __future__ import annotations

import os
import subprocess

import cv2
import numpy as np
from scipy import fft as sfft

from ...engine import media
from ...engine.graph import Context, Effect, Param, register

# ── real encoder inventory ─────────────────────────────────────────────
# Enum value → (ffmpeg encoder name). Values are codec names, not encoder
# names (flv1 is encoded by ffmpeg's "flv" encoder).
_ENCODER_FOR = {
    "mpeg2video": "mpeg2video",  # DVD / broadcast MPEG-2
    "mpeg1video": "mpeg1video",  # VCD
    "mpeg4": "mpeg4",            # early-2000s MPEG-4 ASP (DivX/XviD era)
    "h264": "libx264",            # H.264/AVC - DSLR, action camera, modern web
    "msmpeg4": "msmpeg4",        # MS-MPEG4 v3 - late-90s web video / WMV7-ish
    "flv1": "flv",               # Sorenson Spark - 2005 Flash web video
    "h263p": "h263p",            # H.263+ videoconferencing
    "mjpeg": "mjpeg",            # Motion-JPEG cameras
}


def _available_encoders() -> frozenset[str]:
    """Query ffmpeg once for the encoders actually compiled in."""
    try:
        proc = subprocess.run(
            [media.FFMPEG, "-hide_banner", "-encoders"], capture_output=True, timeout=15
        )
        names = set()
        for line in proc.stdout.decode(errors="replace").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0].startswith("V") and parts[1] != "=":
                names.add(parts[1])
        return frozenset(names)
    except Exception:
        return frozenset()


_AVAILABLE = _available_encoders()


def _codec_choices() -> tuple[str, ...]:
    if not _AVAILABLE:  # probe failed (no ffmpeg yet) - expose all, fail late
        return tuple(_ENCODER_FOR)
    avail = tuple(k for k, enc in _ENCODER_FOR.items() if enc in _AVAILABLE)
    return avail or tuple(_ENCODER_FOR)


_CODECS = _codec_choices()
_DEFAULT_CODEC = "mpeg2video" if "mpeg2video" in _CODECS else _CODECS[0]

# Codecs whose encoders support true interlaced DCT / motion estimation.
_ILACE_CODECS = frozenset({"mpeg2video", "mpeg4"})

# MPEG-1 only accepts the broadcast frame rates.
_MPEG1_FPS = (23.976, 24.0, 25.0, 29.97, 30.0, 50.0, 59.94, 60.0)

# Era codecs drop the color tags but never touch the matrix, so the return leg
# relabels what is still BT.709 data.
_INTERMEDIATE = ["-c:v", "libx264", "-preset", "fast", "-crf", "8", "-pix_fmt", "yuv444p",
                 *media.BT709_TAGS, "-an"]


def _even(x: int) -> int:
    return max(2, int(round(x / 2.0)) * 2)


def _res_target(w: int, h: int, res: str) -> tuple[int, int] | None:
    """Era-ladder size: `res` names the SHORTER side, so portrait video
    degrades on the same ladder as landscape (360p portrait = 360 wide)."""
    tgt = {"480p": 480, "360p": 360, "240p": 240, "144p": 144}.get(res)
    if tgt is None or tgt >= min(w, h):
        return None
    if w <= h:
        return _even(tgt), _even(round(h * tgt / w))
    return _even(round(w * tgt / h)), _even(tgt)


@register
class CodecEra(Effect):
    eid = "codec_era"
    label = "Codec Era"
    kind = "filepass"
    desc = (
        "Round-trip through a real period video encoder (MPEG-1/2/4, "
        "H.264/AVC, MS-MPEG4, FLV1, H.263+, MJPEG): authentic macroblocking, "
        "mosquito noise, DCT ringing and rate-control breathing, with optional "
        "era resolution ladder and repeated re-encode generation loss."
    )
    PARAMS = (
        Param("codec", "Codec", "enum", _DEFAULT_CODEC, choices=_CODECS, group="Codec",
              desc="mpeg2video = DVD/broadcast, mpeg1video = VCD, mpeg4 = DivX era, "
                   "h264 = DSLR/action-camera/modern web AVC via libx264, msmpeg4 = "
                   "late-90s web/WMV, flv1 = 2005 Flash video, h263p = "
                   "videoconferencing, mjpeg = motion-JPEG cameras."),
        # A 100 kbps floor assumed broadband. The presets that exist for the era
        # before it - RealPlayer over a 56k modem, a 2007 cameraphone - were
        # written at 60-96 and silently pulled back up to 100, which is precisely
        # the starvation they were built to show.
        Param("kbps", "Bitrate", "int", 900, 8, 8000, unit="kbps", group="Quality",
              desc="Target bitrate. Used by every codec unless H.264 CRF is enabled; "
                   "low values starve the encoder into classic blocks."),
        Param("qscale", "Quantizer", "int", 0, 0, 31, group="Quality",
              desc="Fixed MPEG-era/MJPEG quantizer 2–31 (31 = worst). When > 0 it "
                   "replaces bitrate for those codecs; H.264 uses CRF instead."),
        Param("crf", "H.264 CRF", "int", -1, -1, 51, group="Quality",
              desc="H.264 constant-quality rate control: -1 uses target bitrate, "
                   "0 is lossless, 18 is visually transparent, 23 is typical, and "
                   "51 is worst. Ignored by the other codecs."),
        Param("res", "Resolution", "enum", "native",
              choices=("native", "480p", "360p", "240p", "144p"), group="Geometry",
              desc="Downscale to the era ladder before encoding, upscale back after; "
                   "sizes name the shorter side. The upscale softness is authentic."),
        Param("gop", "Keyframe Interval", "int", 30, 1, 300, unit="frames", group="Codec",
              desc="GOP length. Long GOPs smear motion errors further between keyframes."),
        Param("passes", "Generations", "int", 1, 1, 3, group="Quality",
              desc="Repeated decode→re-encode cycles - the web-era generation loss "
                   "of clips re-uploaded over and over."),
        Param("field_mode", "Field Mode", "enum", "progressive",
              choices=("progressive", "interlaced_tff"), group="Codec",
              desc="interlaced_tff encodes with real interlaced DCT and motion "
                   "estimation (+ilme+ildct, top field first) - the genuine "
                   "DVD/broadcast MPEG-2 field structure. Ignored by codecs "
                   "without interlaced modes."),
        Param("denoise_pre", "Encoder Pre-Filter", "float", 0.0, 0.0, 1.0, iscale=True,
              group="Quality",
              desc="Broadcast-encoder noise pre-filter ahead of the first encode: "
                   "trades fine texture for cleaner blocks - the slightly waxy "
                   "softness of professionally bit-starved digital TV."),
    )

    def _interlaced(self, codec: str) -> bool:
        return self.v["field_mode"] == "interlaced_tff" and codec in _ILACE_CODECS

    def _codec_args(self, codec: str, fps_out: float | None) -> list[str]:
        enc = _ENCODER_FOR[codec]
        args = ["-c:v", enc, "-g", str(int(self.v["gop"]))]
        if self._interlaced(codec):
            # Field order is flagged per-frame with setparams in the filter
            # chain: the -top CLI option is gone in ffmpeg 8+, and the codec
            # AVOption it falls through to is decode-only, so the bundled
            # ffmpeg rejects the whole encode.
            args += ["-flags", "+ilme+ildct"]
        if codec == "h264":
            # libx264's qscale mode is not the MPEG-4 Part 2 quantizer exposed
            # above. AVC has two distinct and useful controls: constrained
            # average bitrate for cameras/delivery ladders, or CRF for a
            # constant-quality transcode. Never pass both: doing so silently
            # turns CRF into constrained quality and makes the UI lie about
            # which rate-control mode is being modelled.
            crf = int(self.v["crf"])
            args += ["-preset", "medium"]
            # x264's mathematically lossless CRF 0 stream is signalled as High
            # 4:4:4 Predictive even with 4:2:0 samples; forcing plain High makes
            # the encoder reject it. Let x264 choose that profile only at 0.
            if crf != 0:
                args += ["-profile:v", "high"]
            if crf >= 0:
                args += ["-crf", str(crf)]
            else:
                kbps = int(self.v["kbps"])
                args += ["-b:v", f"{kbps}k", "-maxrate", f"{int(kbps * 1.6)}k",
                         "-bufsize", f"{max(kbps * 2, 200)}k"]
            args += ["-pix_fmt", "yuv420p"]
        elif codec == "mjpeg":
            q = int(self.v["qscale"]) or max(2, min(31, int(round(24 - 20 * (self.v["kbps"] / 8000.0)))))
            args += ["-q:v", str(q), "-pix_fmt", "yuvj420p"]
        else:
            if self.v["qscale"] > 0:
                q = max(2, int(self.v["qscale"]))
                args += ["-q:v", str(q), "-qmin", str(q), "-qmax", str(q)]
            else:
                kbps = int(self.v["kbps"])
                args += ["-b:v", f"{kbps}k", "-maxrate", f"{int(kbps * 1.6)}k",
                         "-bufsize", f"{max(kbps * 2, 200)}k"]
            args += ["-pix_fmt", "yuv420p"]
        if fps_out is not None:
            args += ["-r", f"{fps_out:.6f}"]
        return args

    def file_pass(self, in_path: str, out_path: str, ctx: Context) -> None:
        info = media.probe(in_path)
        codec = self.v["codec"]
        tgt = _res_target(info.width, info.height, self.v["res"])

        enc_fps: float | None = None
        if codec == "mpeg1video":
            best = min(_MPEG1_FPS, key=lambda r: abs(r - info.fps))
            if abs(best - info.fps) > 0.02:
                enc_fps = best  # resample to a legal MPEG-1 rate, restore after

        if tgt is not None:
            first_chain = [f"scale={tgt[0]}:{tgt[1]}:flags=lanczos"]
        else:
            first_chain = ["scale=trunc(iw/2)*2:trunc(ih/2)*2"]
        dn = float(self.v["denoise_pre"])
        if dn > 0.0:
            # hqdn3d at its stock 4:3:6:4.5 strength when denoise_pre = 1
            first_chain.append(
                f"hqdn3d={4.0 * dn:.3f}:{3.0 * dn:.3f}:{6.0 * dn:.3f}:{4.5 * dn:.3f}"
            )
        gen_chain: list[str] = []
        if self._interlaced(codec):
            # Every generation re-flags TFF rather than trusting the decoder
            # to carry it through the nut intermediate.
            first_chain.append("setparams=field_mode=tff")
            gen_chain.append("setparams=field_mode=tff")
        first_vf = ["-vf", ",".join(first_chain)]
        gen_vf = ["-vf", ",".join(gen_chain)] if gen_chain else []

        temps: list[str] = []
        try:
            cur = in_path
            for gen in range(int(self.v["passes"])):
                nxt = f"{out_path}.g{gen}.nut"
                temps.append(nxt)
                vf = first_vf if gen == 0 else gen_vf
                media._run(
                    [media.FFMPEG, "-v", "error", "-nostdin", "-y", "-i", cur,
                     *vf, *self._codec_args(codec, enc_fps), "-an", nxt]
                )
                cur = nxt
            back: list[str] = []
            if tgt is not None:
                back += ["-vf", f"scale={info.width}:{info.height}:flags=bicubic"]
            if enc_fps is not None:
                back += ["-r", f"{info.fps:.6f}"]
            media._run(
                [media.FFMPEG, "-v", "error", "-nostdin", "-y", "-i", cur,
                 *back, *_INTERMEDIATE, out_path]
            )
        finally:
            for t in temps:
                if os.path.exists(t):
                    os.unlink(t)


@register
class CodecGlitch(Effect):
    eid = "codec_glitch"
    label = "Codec Glitch"
    kind = "filepass"
    desc = (
        "Real datamosh-style corruption: encodes to a long-GOP era codec, then "
        "damages the actual bitstream with ffmpeg's noise filter and decodes "
        "with error concealment - dragging smears, stale-reference pulls and "
        "blocky tears come from the codec itself. Falls back to a clean copy "
        "if the stream is corrupted beyond decodability."
    )
    PARAMS = (
        Param("codec", "Codec", "enum",
              "mpeg4" if "mpeg4" in _CODECS else _DEFAULT_CODEC,
              choices=tuple(c for c in ("mpeg4", "mpeg2video", "msmpeg4", "flv1") if c in _CODECS) or _CODECS,
              group="Codec", desc="Carrier codec for the corrupted stream."),
        Param("amount", "Corruption", "float", 0.35, 0.0, 1.0, iscale=True, group="Damage",
              desc="Bitstream damage density. ~0.2 = occasional block tears, "
                   "~0.4 = visible dragging smears, ~0.8 = heavy digital soup."),
        Param("drop_p", "Packet Drops", "float", 0.06, 0.0, 1.0, group="Damage",
              desc="Fraction of predicted frames whose packets are discarded - "
                   "frozen drags that snap forward. Dominant artifact; a little "
                   "goes a long way on long GOPs."),
        Param("keyframes", "Protect Keyframes", "bool", True, group="Damage",
              desc="Off = keyframes get corrupted and preferentially dropped: the "
                   "classic datamosh pull-smear where motion drags stale imagery."),
        Param("kbps", "Bitrate", "int", 2500, 500, 8000, unit="kbps", group="Codec",
              desc="Carrier bitrate before corruption."),
        Param("gop", "Keyframe Interval", "int", 48, 12, 300, unit="frames", group="Codec",
              desc="Long GOPs make each glitch drag further before resyncing - "
                   "damage compounds until the next keyframe."),
        Param("freeze_p", "Freeze-Ups", "float", 0.0, 0.0, 1.0, iscale=True, group="Damage",
              desc="Brief full-frame stalls: every packet in a window is discarded, "
                   "so the picture freezes while time (and audio) march on, then "
                   "snaps forward. ~0.3 = a stall every ten seconds or so."),
        Param("slice_shift", "Slice Drag", "float", 0.0, 0.0, 1.0, iscale=True, group="Damage",
              desc="Extra per-slice displacement after decode: macroblock-row bands "
                   "shear sideways and hold for a beat - the classic sliced-drag "
                   "tear of a corrupted transport stream."),
    )

    # Note on determinism: the noise bitstream filter has no seed option, but
    # its byte-position PRNG is a fixed state machine - identical input bytes
    # and identical filter args reproduce the identical corruption. The render
    # seed enters through the drop pattern offset and an amount jitter, so
    # different seeds give different glitches and the same seed repeats exactly.

    def file_pass(self, in_path: str, out_path: str, ctx: Context) -> None:
        info = media.probe(in_path)
        amount = float(self.v["amount"])
        drop_p = float(self.v["drop_p"])
        freeze_p = float(self.v["freeze_p"])
        slice_shift = float(self.v["slice_shift"])
        if amount <= 0.0 and drop_p <= 0.0 and freeze_p <= 0.0:
            media._run([media.FFMPEG, "-v", "error", "-nostdin", "-y", "-i", in_path,
                        *_INTERMEDIATE, out_path])
            if slice_shift > 0.0:
                self._slice_drag(out_path, ctx, slice_shift)
            return

        g = self.rng_stream(ctx)
        seed_off = int(g.integers(0, 997))
        jitter = 0.8 + 0.4 * float(g.random())
        self._freezes = self._freeze_windows(ctx, freeze_p, info.n_frames, info.fps)

        enc = _ENCODER_FOR[self.v["codec"]]
        base = f"{out_path}.carrier.avi"
        temps = [base]
        try:
            media._run(
                [media.FFMPEG, "-v", "error", "-nostdin", "-y", "-i", in_path,
                 "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                 "-c:v", enc, "-b:v", f"{int(self.v['kbps'])}k",
                 "-g", str(int(self.v["gop"])), "-bf", "0",
                 "-pix_fmt", "yuv420p", "-an", base]
            )
            # amount → bsf value: bsf corrupts ~1 byte per `value` bytes, so
            # smaller = heavier. Log-map amount 0→1 onto ~180 kB→0.3 kB spacing.
            bsf_amount = int(round(self._bsf_scale(amount) * jitter))
            expected = max(info.n_frames, 1)

            for attempt in range(4):
                amt_v = bsf_amount * (2 ** attempt)          # halve severity each retry
                drop_v = drop_p / (2 ** attempt)
                corrupted = f"{out_path}.glitch{attempt}.avi"
                temps.append(corrupted)
                self._corrupt(base, corrupted, amt_v if amount > 0 else 0, drop_v, seed_off)
                try:
                    media._run(
                        [media.FFMPEG, "-v", "error", "-nostdin", "-y",
                         "-err_detect", "ignore_err", "-fflags", "+genpts",
                         "-ec", "guess_mvs+deblock+favor_inter",
                         # Concealment over a damaged stream is racy under
                         # frame threading: the same corrupted bytes decoded
                         # twice gave two different pictures, which broke the
                         # per-seed determinism the note above promises. One
                         # thread makes the guesswork reproducible.
                         "-threads", "1",
                         "-i", corrupted,
                         "-fps_mode", "cfr", "-r", f"{info.fps:.6f}",
                         *_INTERMEDIATE, out_path]
                    )
                    got = media.probe(out_path).n_frames
                    if got >= 0.9 * expected:
                        if slice_shift > 0.0:
                            self._slice_drag(out_path, ctx, slice_shift)
                        return
                except media.MediaError:
                    pass
            # beyond salvage - clean passthrough so the render never breaks
            media._run([media.FFMPEG, "-v", "error", "-nostdin", "-y", "-i", in_path,
                        *_INTERMEDIATE, out_path])
            if slice_shift > 0.0:
                self._slice_drag(out_path, ctx, slice_shift)
        finally:
            for t in temps:
                if os.path.exists(t):
                    os.unlink(t)

    @staticmethod
    def _bsf_scale(amount: float) -> float:
        # Mean bytes between corruptions; the per-packet burst modulation in
        # _corrupt multiplies this by 0.4–7.4 (harmonic mean ≈ 0.58), which is
        # folded in here so `amount` maps to the intended average density.
        return 10 ** (5.55 - 2.85 * min(amount, 1.0)) * 0.58

    def rng_stream(self, ctx: Context) -> np.random.Generator:
        return ctx.rng(f"{self.key}:bsf")

    def _freeze_windows(self, ctx: Context, freeze_p: float, n_frames: int, fps: float) -> list[tuple[int, int]]:
        """Packet-index windows to drop wholesale → full-frame stalls.

        The AVI carrier keeps timing with null chunks, so the CFR decode
        duplicates the last good frame across the hole: a genuine freeze that
        snaps forward, duration preserved (audio keeps running)."""
        if freeze_p <= 0.0:
            return []
        g = ctx.rng(f"{self.key}:freeze")
        fps = max(fps, 1.0)
        n = max(n_frames, 8)
        windows: list[tuple[int, int]] = []
        fi = int(fps * 0.5)                      # never stall the very first beat
        p_start = freeze_p / (3.5 * fps)         # ~1 stall / 3.5 s at freeze_p = 1
        while fi < n - 4 and len(windows) < 10:
            if g.random() < p_start:
                dur = max(3, int(fps * (0.25 + 0.65 * float(g.random()))))
                windows.append((fi, min(fi + dur, n - 2)))
                fi += dur + int(fps * 0.8)       # refractory gap after a stall
            else:
                fi += 1
        return windows

    def _corrupt(self, src: str, dst: str, bsf_amount: int, drop_p: float, seed_off: int) -> None:
        protect = bool(self.v["keyframes"])
        opts: list[str] = []
        if bsf_amount > 0:
            # Bursty damage: per-packet density swings 0.4x–7.4x (glitches come
            # in bursts), and the seed offset shifts which packets get hit.
            burst = f"({bsf_amount}*(0.4+mod(n*3+{seed_off}\\,8)))"
            expr = f"not(key)*{burst}" if protect else f"gt(n\\,0)*{burst}"
            opts.append(f"amount={expr}")
        drop_parts: list[str] = []
        if drop_p > 0:
            t = int(round(min(drop_p, 1.0) * 997))
            if protect:
                drop_parts.append(f"not(key)*gt(n\\,0)*lt(mod(n*7919+{seed_off}\\,997)\\,{t})")
            else:
                # unprotected: keyframes 3x more likely to drop → stale-reference pulls
                drop_parts.append(f"gt(n\\,0)*lt(mod(n*7919+{seed_off}\\,997)\\,{t}*(1+2*key))")
        # freeze windows drop everything - keyframes included, that's the stall
        drop_parts += [f"between(n\\,{a}\\,{b})" for a, b in getattr(self, "_freezes", [])]
        if drop_parts:
            opts.append("drop=" + "+".join(drop_parts))
        media._run(
            [media.FFMPEG, "-v", "error", "-nostdin", "-y", "-i", src,
             "-c", "copy", "-bsf:v", "noise=" + ":".join(opts), dst]
        )

    def _slice_drag(self, path: str, ctx: Context, amount: float) -> None:
        """Post-decode per-slice horizontal displacement: macroblock-row bands
        shear sideways and hold for a stretch - decoded slices landing at the
        wrong offset. Streams the decoded intermediate through a numpy pass."""
        info = media.probe(path)
        W, H, fps = info.width, info.height, info.fps
        n = max(info.n_frames, 1)
        g = ctx.rng(f"{self.key}:slices")
        # events: (first frame, last frame, rows of (y0, h, dx, grow))
        events = []
        n_ev = int(g.poisson(amount * n / max(fps, 1.0) * 0.55)) + (1 if amount > 0.15 else 0)
        for _ in range(min(n_ev, 24)):
            f0 = int(g.integers(0, max(n - 4, 1)))
            dur = max(2, int(max(fps, 1.0) * (0.20 + 0.85 * float(g.random()))))
            bands = []
            for _b in range(1 + int(g.integers(0, 3))):
                y0 = int(g.integers(0, max(H // 16, 1))) * 16
                bh = 16 * (1 + int(g.integers(0, 3)))
                dx = float(g.uniform(8.0, 90.0)) * amount * (1.0 if g.random() < 0.5 else -1.0)
                grow = float(g.uniform(0.0, 0.05))       # drag accumulates a little
                bands.append((y0, min(bh, H - y0), dx, grow))
            events.append((f0, min(f0 + dur, n), bands))
        if not events:
            return
        active: dict[int, list] = {}
        for f0, f1, bands in events:
            for fi in range(f0, f1):
                active.setdefault(fi, []).extend((y0, bh, dx * (1.0 + grow * (fi - f0)))
                                                 for y0, bh, dx, grow in bands)
        tmp = path + ".slice.mp4"
        writer = media.FrameWriter(tmp, W, H, fps, crf=8, preset="fast", pix_fmt="yuv444p")
        try:
            for fi, frame in enumerate(media.read_frames(path, W, H, fps)):
                for y0, bh, dx in active.get(fi, ()):  # type: ignore[misc]
                    band = frame[y0:y0 + bh]
                    s = int(np.clip(round(dx), -(W - 2), W - 2))
                    if s > 0:
                        band[:, s:] = band[:, :-s].copy()
                        band[:, :s] = band[:, s:s + 1]
                    elif s < 0:
                        band[:, :s] = band[:, -s:].copy()
                        band[:, s:] = band[:, s - 1:s]
                writer.write(frame)
        finally:
            writer.close()
        os.replace(tmp, path)


# ── frame effects ──────────────────────────────────────────────────────

_LUMA_W = np.array([0.299, 0.587, 0.114], dtype=np.float32)


def _pal(*hexes: str) -> np.ndarray:
    out = np.array(
        [[int(h[i : i + 2], 16) for i in (0, 2, 4)] for h in hexes], dtype=np.float32
    )
    return out / 255.0


_PALETTES: dict[str, np.ndarray] = {
    "gameboy_dmg": _pal("0F380F", "306230", "8BAC0F", "9BBC0F"),  # dark → light
    "cga": _pal("000000", "55FFFF", "FF55FF", "FFFFFF"),
    # CGA mode-1 low intensity: black / cyan / magenta / light gray
    "cga_cyan": _pal("000000", "00AAAA", "AA00AA", "AAAAAA"),
    "ega16": _pal("000000", "0000AA", "00AA00", "00AAAA", "AA0000", "AA00AA",
                  "AA5500", "AAAAAA", "555555", "5555FF", "55FF55", "55FFFF",
                  "FF5555", "FF55FF", "FFFF55", "FFFFFF"),
    "c64": _pal("000000", "FFFFFF", "68372B", "70A4B2", "6F3D86", "588D43",
                "352879", "B8C76F", "6F4F25", "433900", "9A6759", "444444",
                "6C6C6C", "9AD284", "6C5EB5", "959595"),
    "apple2": _pal("000000", "FFFFFF", "14F53C", "FF44FD", "FF6A3C", "14CFFD"),
    "teletext": _pal("000000", "FF0000", "00FF00", "FFFF00", "0000FF", "FF00FF",
                     "00FFFF", "FFFFFF"),
    # ZX Spectrum non-bright palette; attribute clash is applied on top
    "zx_spectrum": _pal("000000", "0000D8", "D80000", "D800D8", "00D800",
                        "00D8D8", "D8D800", "D8D8D8"),
}

# Ordered-dither spread ≈ quantization step of each palette.
_DITHER_SPREAD = {
    "none": 0.0, "gameboy_dmg": 0.30, "cga": 0.30, "cga_cyan": 0.30, "ega16": 0.17,
    "vga256": 0.10, "c64": 0.17, "apple2": 0.26, "teletext": 0.30, "zx_spectrum": 0.24,
}


def _zx_attribute_clash(small: np.ndarray, idx: np.ndarray, pal: np.ndarray) -> np.ndarray:
    """The Spectrum's attribute grid: every 8x8 character cell may hold only
    TWO palette colors (ink + paper). Pick each cell's two dominant mapped
    colors and re-snap every pixel in the cell to the nearer of the pair."""
    h, w = idx.shape
    npal = len(pal)
    ch, cw = -(-h // 8), -(-w // 8)
    ph, pw = ch * 8, cw * 8
    pidx = np.zeros((ph, pw), np.int64)
    pidx[:h, :w] = idx
    if pw > w:                                  # pad with the edge column/row so
        pidx[:h, w:] = idx[:, -1:]              # border cells vote with real data
    if ph > h:
        pidx[h:, :] = pidx[h - 1: h, :]
    cells = pidx.reshape(ch, 8, cw, 8).transpose(0, 2, 1, 3).reshape(-1, 64)
    counts = np.bincount(
        (cells + np.arange(cells.shape[0])[:, None] * npal).ravel(),
        minlength=cells.shape[0] * npal,
    ).reshape(-1, npal)
    order = np.argsort(counts, axis=1)
    a = order[:, -1]                            # paper (dominant)
    b = order[:, -2]                            # ink (runner-up)
    b = np.where(counts[np.arange(len(b)), b] == 0, a, b)
    ps = np.zeros((ph, pw, 3), np.float32)
    ps[:h, :w] = small
    if pw > w:
        ps[:h, w:] = small[:, -1:]
    if ph > h:
        ps[h:, :] = ps[h - 1: h, :]
    cellpx = ps.reshape(ch, 8, cw, 8, 3).transpose(0, 2, 1, 3, 4).reshape(-1, 64, 3)
    da = (((cellpx - pal[a][:, None, :]) ** 2) * _LUMA_W).sum(-1)
    db = (((cellpx - pal[b][:, None, :]) ** 2) * _LUMA_W).sum(-1)
    pick = np.where(da <= db, a[:, None], b[:, None])
    out = pick.reshape(ch, cw, 8, 8).transpose(0, 2, 1, 3).reshape(ph, pw)
    return out[:h, :w]


def _bayer(n: int) -> np.ndarray:
    m = np.zeros((1, 1), dtype=np.float64)
    size = 1
    while size < n:
        m = np.block([[4 * m + 0, 4 * m + 2], [4 * m + 3, 4 * m + 1]])
        size *= 2
    return ((m + 0.5) / (n * n) - 0.5).astype(np.float32)


@register
class PixelEra(Effect):
    eid = "pixel_era"
    label = "Pixel Era"
    kind = "frame"
    desc = (
        "Computer/console graphics: fat nearest-neighbor pixels at a coarse "
        "resolution, mapped into a real machine palette (Game Boy, CGA, EGA, "
        "VGA, C64, Apple II, teletext) with ordered dithering."
    )
    PARAMS = (
        Param("res_h", "Vertical Resolution", "int", 240, 64, 480, unit="px", group="Geometry",
              desc="Vertical pixel count of the simulated display."),
        Param("palette", "Palette", "enum", "none",
              choices=("none", "gameboy_dmg", "cga", "cga_cyan", "ega16", "vga256",
                       "c64", "apple2", "teletext", "zx_spectrum"),
              group="Color", desc="Machine palette; vga256 quantizes to the 6x6x6 cube, "
                                  "cga_cyan is the low-intensity mode-1 cyan/magenta set, "
                                  "zx_spectrum adds true 8x8 attribute clash."),
        Param("dither", "Dithering", "enum", "bayer4",
              choices=("none", "bayer2", "bayer4", "bayer8"), group="Color",
              desc="Ordered (Bayer) dither applied before quantization."),
        Param("contrast_snap", "Contrast Snap", "float", 0.3, 0.0, 1.0, group="Color",
              desc="Pre-quantization contrast so midtones don't collapse into mud."),
        Param("pixel_aspect", "Pixel Aspect", "float", 1.0, 0.5, 2.0, group="Geometry",
              desc="Pixel width ÷ height. 1.25 ≈ 320x200 stretched over a 4:3 tube "
                   "(fat pixels); below 1 gives tall skinny pixels."),
    )

    def prepare(self, ctx: Context) -> None:
        self._bayers = {"bayer2": _bayer(2), "bayer4": _bayer(4), "bayer8": _bayer(8)}

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        H, W = frame.shape[:2]
        hl = min(int(self.v["res_h"]), H)
        wl = max(2, int(round(W * hl / (H * float(self.v["pixel_aspect"])))))
        small = cv2.resize(frame, (wl, hl), interpolation=cv2.INTER_AREA)

        cs = self.v["contrast_snap"]
        if cs > 0:
            small = np.clip((small - 0.5) * (1.0 + 1.6 * cs) + 0.5, 0.0, 1.0)

        pal_name = self.v["palette"]
        spread = _DITHER_SPREAD[pal_name]
        dm = self._bayers.get(self.v["dither"])
        if dm is not None and spread > 0 and pal_name != "none":
            ty = -(-hl // dm.shape[0])
            tx = -(-wl // dm.shape[1])
            d = np.tile(dm, (ty, tx))[:hl, :wl]
            small = small + d[..., None] * spread

        if pal_name == "none":
            out_small = np.clip(small, 0.0, 1.0)
        elif pal_name == "vga256":
            out_small = np.round(np.clip(small, 0.0, 1.0) * 5.0) / 5.0
        elif pal_name == "gameboy_dmg":
            pal = _PALETTES[pal_name]
            y = np.clip(small @ _LUMA_W, 0.0, 1.0)
            idx = np.clip((y * len(pal)).astype(np.int32), 0, len(pal) - 1)
            out_small = pal[idx]
        else:
            pal = _PALETTES[pal_name]
            snapped = np.clip(small, 0.0, 1.0)
            px = snapped.reshape(-1, 1, 3)
            d2 = ((px - pal[None, :, :]) ** 2 * _LUMA_W).sum(axis=-1)
            idx = np.argmin(d2, axis=-1).reshape(hl, wl)
            if pal_name == "zx_spectrum":
                idx = _zx_attribute_clash(snapped, idx, pal)
            out_small = pal[idx]

        return cv2.resize(
            out_small.astype(np.float32), (W, H), interpolation=cv2.INTER_NEAREST
        )


@register
class ChromaDV(Effect):
    eid = "chroma_dv"
    label = "DV Chroma"
    kind = "frame"
    desc = (
        "Brutal digital chroma subsampling (4:2:0 / 4:1:1 DV-NTSC / 4:1:0) with "
        "nearest-neighbor chroma reconstruction - the stair-stepped color edges "
        "of DV tape and early digital cameras - plus in-camera edge sharpening."
    )
    PARAMS = (
        Param("ratio", "Subsampling", "enum", "4:1:1",
              choices=("4:2:0", "4:1:1", "4:1:0"), group="Chroma",
              desc="4:2:0 = DVD/webcam, 4:1:1 = NTSC DV (4x horizontal), "
                   "4:1:0 = quarter-res chroma both ways."),
        Param("edge_sharpen", "Edge Sharpen", "float", 0.35, 0.0, 2.0, iscale=True,
              group="Luma", desc="DV in-camera sharpening with its telltale halos."),
        Param("dct_blocks", "DCT Blocks", "float", 0.0, 0.0, 1.0, iscale=True, group="Luma",
              desc="Faint 8x8 luma block boundaries surfacing under motion - real "
                   "intra-frame DCT quantization, DV's compression signature. "
                   "Keep low; it should whisper, not shout."),
    )

    _FACTORS = {"4:2:0": (2, 2), "4:1:1": (4, 1), "4:1:0": (4, 4)}

    # JPEG/DV-style luminance quantization weights, normalized so DC = 1.
    _QTAB = (np.array(
        [[16, 11, 10, 16, 24, 40, 51, 61],
         [12, 12, 14, 19, 26, 58, 60, 55],
         [14, 13, 16, 24, 40, 57, 69, 56],
         [14, 17, 22, 29, 51, 87, 80, 62],
         [18, 22, 37, 56, 68, 109, 103, 77],
         [24, 35, 55, 64, 81, 104, 113, 92],
         [49, 64, 78, 87, 103, 121, 120, 101],
         [72, 92, 95, 98, 112, 100, 103, 99]], dtype=np.float32,
    ) / 16.0).reshape(1, 8, 1, 8)

    def prepare(self, ctx: Context) -> None:
        self._prev_y: np.ndarray | None = None

    def _dct_quant(self, y: np.ndarray, db: float) -> np.ndarray:
        """Real 8x8 DCT quantization of the luma plane."""
        H, W = y.shape
        ph, pw = -(-H // 8) * 8, -(-W // 8) * 8
        y2 = y if (ph, pw) == (H, W) else cv2.copyMakeBorder(
            y, 0, ph - H, 0, pw - W, cv2.BORDER_REPLICATE)
        blocks = y2.reshape(ph // 8, 8, pw // 8, 8)
        coef = sfft.dctn(blocks, axes=(1, 3), norm="ortho")
        q = self._QTAB * np.float32(0.11 * db)
        coef = np.round(coef / q) * q
        out = sfft.idctn(coef, axes=(1, 3), norm="ortho").astype(np.float32)
        return np.ascontiguousarray(out.reshape(ph, pw)[:H, :W])

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        H, W = frame.shape[:2]
        fh, fv = self._FACTORS[self.v["ratio"]]
        ycc = cv2.cvtColor(frame, cv2.COLOR_RGB2YCrCb)
        cw, chh = max(1, W // fh), max(1, H // fv)
        for c in (1, 2):
            small = cv2.resize(ycc[..., c], (cw, chh), interpolation=cv2.INTER_AREA)
            ycc[..., c] = cv2.resize(small, (W, H), interpolation=cv2.INTER_NEAREST)
        k = self.v["edge_sharpen"]
        if k > 0:
            y = ycc[..., 0]
            blur = cv2.GaussianBlur(y, (0, 0), 1.1)
            ycc[..., 0] = y + (y - blur) * (k * 0.9)
        db = float(self.v["dct_blocks"])
        if db > 0:
            y = np.ascontiguousarray(ycc[..., 0])
            if self._prev_y is not None and self._prev_y.shape == y.shape:
                # the quantizer coarsens where the picture is changing - block
                # edges surface with motion and melt away on stills
                d = cv2.GaussianBlur(np.abs(y - self._prev_y), (0, 0), 2.5)
                m = np.clip(d * 16.0, 0.0, 1.0)
                yq = self._dct_quant(y, db)
                ycc[..., 0] = y + (yq - y) * m
            self._prev_y = y
        out = cv2.cvtColor(ycc, cv2.COLOR_YCrCb2RGB)
        return np.clip(out, 0.0, 1.0).astype(np.float32)


@register
class LCDScreen(Effect):
    eid = "lcd_screen"
    label = "LCD Screen"
    kind = "frame"
    desc = (
        "Footage-of-an-LCD playback surface: thin pixel grid, slow-response "
        "ghosting (worst in the darks), uneven backlight bleed and a slight "
        "viewing-angle gamma tilt. Subtle by default."
    )
    PARAMS = (
        Param("grid", "Pixel Grid", "float", 0.25, 0.0, 1.0, iscale=True, group="Panel",
              desc="Darkness of the LCD pixel lattice."),
        Param("scale", "Grid Pitch", "int", 3, 2, 10, unit="px", group="Panel",
              desc="Pixel pitch of the simulated panel."),
        Param("response_smear", "Response Smear", "float", 0.3, 0.0, 1.0, iscale=True,
              group="Panel", desc="Slow pixel response: previous frame ghosts through, "
                                  "strongest on dark-to-dark transitions."),
        Param("backlight_bleed", "Backlight Bleed", "float", 0.15, 0.0, 1.0, iscale=True,
              group="Panel", desc="Uneven corner/edge glow lifting the blacks."),
        Param("viewing_angle", "Viewing Angle", "float", 0.15, -1.0, 1.0, group="Panel",
              desc="Off-axis gamma shift across the frame (+right side washed, "
                   "-left side washed)."),
        Param("subpixel", "Subpixel Structure", "enum", "none",
              choices=("none", "rgb_stripe_lcd"), group="Panel",
              desc="Resolve the panel's R/G/B stripe triads inside each pixel cell "
                   "- the close-enough-to-see-the-subpixels camera look. Wants "
                   "scale >= 3 so each stripe gets a column."),
        Param("dead_pixels", "Dead Pixels", "int", 0, 0, 24, group="Panel",
              desc="Stuck panel pixels at seed-stable positions: mostly dark-dead, "
                   "sometimes a subpixel latched bright red/green/blue."),
        Param("moire_cam", "Camera Moiré", "float", 0.0, 0.0, 1.0, iscale=True, group="Camera",
              desc="The interference bands of pointing a camera at an LCD: broad "
                   "magenta/green fringes drifting slowly as the framing breathes."),
    )

    def prepare(self, ctx: Context) -> None:
        H, W = ctx.height, ctx.width
        self._prev: np.ndarray | None = None
        s = int(self.v["scale"])
        tile = np.ones((s, s), dtype=np.float32)
        g = float(self.v["grid"])
        if g > 0:
            tile[-1, :] *= 1.0 - 0.75 * g
            tile[:, -1] *= 1.0 - 0.75 * g
        if self.v["subpixel"] == "rgb_stripe_lcd":
            # each s-wide cell splits into R/G/B thirds; a channel lights only
            # inside its own stripe (with leak), roughly energy-preserving
            sub = np.empty((s, s, 3), np.float32)
            for c in range(s):
                stripe = min(c * 3 // max(s, 1), 2)
                gains = np.full(3, 0.26, np.float32)
                gains[stripe] = 2.05
                sub[:, c, :] = gains
            sub *= tile[..., None] * 1.10
            self._grid = np.ascontiguousarray(
                np.tile(sub, (-(-H // s), -(-W // s), 1))[:H, :W])
        else:
            self._grid = np.tile(tile, (-(-H // s), -(-W // s)))[:H, :W][..., None]

        self._dead: list[tuple[int, int, np.ndarray]] = []
        ndp = int(self.v["dead_pixels"])
        if ndp > 0:
            gd = ctx.rng(f"{self.key}:dead")
            for _ in range(ndp):
                cy = int(gd.integers(0, max(H // s, 1))) * s
                cx = int(gd.integers(0, max(W // s, 1))) * s
                if gd.random() < 0.6:            # dark dead pixel
                    col = np.full(3, float(gd.uniform(0.0, 0.02)), np.float32)
                else:                            # stuck-bright subpixel
                    col = np.full(3, 0.03, np.float32)
                    col[int(gd.integers(0, 3))] = float(gd.uniform(0.85, 1.0))
                self._dead.append((cy, cx, col))

        self._moire_a = self._moire_b = None
        if self.v["moire_cam"] > 0:
            gm = ctx.rng(f"{self.key}:moire")
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            a = np.zeros((H, W), np.float32)
            b = np.zeros((H, W), np.float32)
            for _ in range(2):                   # two detuned beat components
                th = float(gm.uniform(0.0, np.pi))
                lam = float(gm.uniform(0.16, 0.42)) * min(H, W)   # beat wavelength
                ph = (np.cos(th) * xx + np.sin(th) * yy) * (2.0 * np.pi / lam)
                w = float(gm.uniform(0.6, 1.0))
                a += np.cos(ph) * w
                b += np.sin(ph) * w
            self._moire_a, self._moire_b = a * 0.5, b * 0.5
            self._moire_ph = ctx.noise.smooth(f"{self.key}:mo_ph", 0.25) * np.pi
            self._moire_amp = 0.65 + 0.35 * ctx.noise.smooth(f"{self.key}:mo_amp", 0.15)
            # camera moiré is colored: opposing magenta/green fringes
            self._moire_tint = np.asarray([1.0, -0.85, 0.75], np.float32)

        rng = ctx.rng(f"{self.key}:bleed")
        gh, gw = max(2, H // 16), max(2, W // 16)
        m = np.zeros((gh, gw), dtype=np.float32)
        yy, xx = np.mgrid[0:gh, 0:gw].astype(np.float32)
        corners = [(0, 0), (0, gw - 1), (gh - 1, 0), (gh - 1, gw - 1)]
        rng.shuffle(corners)
        for cy, cx in corners[: 2 + int(rng.integers(0, 3))]:
            jy = cy + rng.uniform(-0.12, 0.12) * gh
            jx = cx + rng.uniform(-0.12, 0.12) * gw
            sig = rng.uniform(0.20, 0.38) * min(gh, gw)
            amp = rng.uniform(0.5, 1.0)
            m += amp * np.exp(-((yy - jy) ** 2 + (xx - jx) ** 2) / (2 * sig**2))
        m /= max(float(m.max()), 1e-6)
        self._bleed = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]

        va = float(self.v["viewing_angle"])
        self._gamma = None
        if abs(va) > 1e-3:
            gam = 1.0 + 0.35 * va * np.linspace(-1.0, 1.0, W, dtype=np.float32)
            self._gamma = (1.0 / gam)[None, :].astype(np.float32)
        self._prev_y: np.ndarray | None = None

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        x = frame
        smear = float(self.v["response_smear"])
        if smear > 0:
            y = x @ _LUMA_W
            if self._prev is not None:
                y_hi = np.maximum(y, self._prev_y)
                w = np.clip(smear * (0.25 + 0.75 * (1.0 - y_hi)), 0.0, 0.92)[..., None]
                x = x * (1.0 - w) + self._prev * w
                y = x @ _LUMA_W
            self._prev = x.copy()
            self._prev_y = y
        if self._gamma is not None:
            # apply the per-column gamma tilt on luma and rescale RGB by the
            # ratio - one-channel pow instead of three, visually identical
            y = x @ _LUMA_W if smear <= 0 else y
            ys = np.clip(y, 1e-4, 1.0)
            ratio = (np.power(ys, self._gamma) / ys)[..., None]
            x = x * ratio
        if self._dead:
            s = int(self.v["scale"])
            gap = 1 if self.v["grid"] > 0 else 0   # leave the lattice line dark
            for cy, cx, col in self._dead:
                x[cy:cy + s - gap, cx:cx + s - gap] = col
        if self.v["grid"] > 0 or self.v["subpixel"] != "none":
            x = x * self._grid
        bb = float(self.v["backlight_bleed"])
        if bb > 0:
            x = x + self._bleed * (bb * 0.22) * (1.0 - x)
        mo = float(self.v["moire_cam"])
        if mo > 0 and self._moire_a is not None:
            fi = min(ctx.fi_out, len(self._moire_ph) - 1)
            ph = float(self._moire_ph[fi])
            pat = self._moire_a * np.cos(ph) + self._moire_b * np.sin(ph)
            amp = mo * 0.13 * float(self._moire_amp[fi])
            for c in range(3):
                x[..., c] *= 1.0 + (amp * float(self._moire_tint[c])) * pat
        return np.clip(x, 0.0, 1.0).astype(np.float32)
