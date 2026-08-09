"""Render orchestration: source → video chain (streamed, segmented around
file passes) → audio chain → mux.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import numpy as np

from . import media
from .graph import Context, Effect, build_chain
from .presets import Preset, Variant, parse_override_paths

ProgressCb = Callable[[str, float], None]  # (phase, fraction 0..1)


class _PhasedProgress:
    """Fold several per-phase 0..1 fractions into one monotonic job fraction.

    Each phase used to report its own 0..1, so a treated video export climbed to
    100% during "video", snapped back to 0 for "audio", then back to 0 again for
    "mux". Anything drawing a single bar from these numbers - the GUI titlebar,
    the CLI's rich bar - walked backwards twice near the end of every render.

    Phases get a share of the bar proportional to their weight, in the order
    they are declared, and the reported value is clamped so it can never
    decrease: a phase that is skipped or ends early leaves the bar where it is
    rather than dragging it back.
    """

    def __init__(self, cb: Optional[ProgressCb], weights: dict[str, float]) -> None:
        self._cb = cb
        total = sum(weights.values()) or 1.0
        self._spans: dict[str, tuple[float, float]] = {}
        at = 0.0
        for phase, weight in weights.items():
            # Accumulate raw weights and divide, rather than summing normalized
            # shares: summing shares drifts, and the zero-weight "done" phase has
            # to land on exactly 1.0.
            self._spans[phase] = (at / total, weight / total)
            at += weight
        self._last = 0.0

    def __call__(self, phase: str, frac: float) -> None:
        if self._cb is None:
            return
        # "done" carries no weight, so it lands on 1.0 by construction. An
        # unknown phase parks at wherever the bar already is.
        start, span = self._spans.get(phase, (self._last, 0.0))
        value = start + span * min(max(frac, 0.0), 1.0)
        self._last = min(max(value, self._last), 1.0)
        self._cb(phase, self._last)


def _phase_weights(has_video_chain: bool, has_audio: bool) -> dict[str, float]:
    """Rough shares of wall clock per phase. Only their ratio matters.

    A treated video chain dominates a render; a straight copy (audio-only jobs,
    or a preset with no video effects) does not, so the audio pass gets a much
    larger share there.
    """
    weights = {
        "video": 0.86 if has_video_chain else 0.42,
        "audio": (0.11 if has_video_chain else 0.52) if has_audio else 0.0,
        "mux": 0.03,
        "done": 0.0,
    }
    return weights


@dataclass
class RenderOptions:
    seed: int = 1
    intensity: float = 1.0
    texture: float = 1.0          # master multiplier for grain/noise amounts
    variant: Optional[str] = None
    video_overrides: dict[str, Any] = field(default_factory=dict)
    audio_overrides: dict[str, Any] = field(default_factory=dict)
    video_only: bool = False
    audio_only: bool = False
    t0: float = 0.0
    # Where this render sits on the *original* clip, which is only the same as
    # `t0` for the first pass. Layer two of a stack reads an intermediate that
    # has already been trimmed, so it seeks from zero while still being, say,
    # forty seconds into the tape - and anything scheduled against the clip has
    # to know that. Defaults to `t0`.
    source_t0: Optional[float] = None
    duration: Optional[float] = None
    scale: float = 1.0            # output scale factor (previews)
    crf: int = 17
    keep_temp: bool = False

    @property
    def clip_t0(self) -> float:
        return self.t0 if self.source_t0 is None else self.source_t0


def _merged_overrides(variant: Optional[Variant], user: dict[str, Any], which: str) -> dict[str, dict[str, Any]]:
    merged: dict[str, Any] = {}
    if variant:
        merged.update(getattr(variant, which))
    merged.update(user)
    return parse_override_paths(merged)


def _even(x: int) -> int:
    return max(2, int(round(x / 2)) * 2)


def _timing(info: "media.MediaInfo", opts: RenderOptions) -> tuple[float, float, int]:
    """Clip length, frame rate and frame count for a render.

    Shared rather than repeated because `n_frames` is load-bearing well beyond
    "how many frames to write": the temporal noise tracks in rng.py are filtered
    and percentile-normalised across their whole length, so the same seed over a
    different number of frames is a different frame 0. Anything claiming to
    preview a clip has to agree with it here.
    """
    duration = opts.duration if opts.duration is not None else max(info.duration - opts.t0, 0.1)
    duration = min(duration, max(info.duration - opts.t0, 0.1))
    return duration, info.fps, max(int(round(duration * info.fps)), 1)


def _video_geometry(info: "media.MediaInfo", preset: Preset, opts: RenderOptions) -> tuple[int, int, int, int]:
    """(proc_w, proc_h, out_w, out_h) - the era resolution and the delivery size."""
    out_w, out_h = _even(int(info.width * opts.scale)), _even(int(info.height * opts.scale))
    if preset.proc_height and preset.proc_height < out_h:
        proc_h = _even(preset.proc_height)
        proc_w = _even(out_w * proc_h / out_h)
    else:
        proc_w, proc_h = out_w, out_h
    return proc_w, proc_h, out_w, out_h


def _live_chain(chain: list[Effect], ctx: Context, over: dict[str, dict[str, Any]]) -> list[Effect]:
    """Resolve a built chain and drop the effects switched off in it.

    Resolve first, filter second: `enabled` is an ordinary parameter, so a
    variant or a --set is what decides it. Filtering after `build_chain` has
    handed out the keys means a repeat still answers to `grain#2` whether or not
    the copy before it is switched on, and `prepare` only runs for the effects
    that are actually going to see a frame.
    """
    for eff in chain:
        eff.resolve(ctx, over.get(eff.key))
    live = [eff for eff in chain if eff.v.get("enabled", True)]
    for eff in live:
        eff.prepare(ctx)
    return live


def _upscale_flags(preset: Preset) -> str:
    flavor = preset.upscale if preset.upscale != "auto" else "soft"
    return {"sharp": "lanczos", "soft": "bicubic"}.get(flavor, "bicubic")


def _segment_chain(chain: list[Effect]) -> list[list[Effect]]:
    """Split into frame-effect runs separated by single-filepass segments.

    A leading empty frame segment is kept when the chain starts with a file
    pass, so source trimming and time remaps always happen in a frame pass.
    """
    segments: list[list[Effect]] = [[]]
    for eff in chain:
        if eff.kind == "filepass":
            segments.append([eff])
            segments.append([])
        else:
            segments[-1].append(eff)
    # drop empty segments except a required leading one
    out: list[list[Effect]] = []
    for i, seg in enumerate(segments):
        if seg or (i == 0 and len(segments) > 1 and segments[1] and segments[1][0].kind == "filepass"):
            out.append(seg)
    return out or [[]]


def _compose_src_map(chain: list[Effect], ctx: Context, n_frames: int) -> np.ndarray:
    """Compose all time remaps into output-index → source-index (monotonic)."""
    idx = np.arange(n_frames, dtype=np.int64)
    for eff in reversed(chain):
        r = eff.remap(ctx)
        if r is not None:
            r = np.clip(np.asarray(r, dtype=np.int64), 0, n_frames - 1)
            idx = np.take(r, idx)
    idx = np.maximum.accumulate(idx)  # enforce non-decreasing for streaming
    return idx


@dataclass
class Layer:
    """One preset in a stack, with the knobs that belong to it alone."""
    preset: Preset
    variant: Optional[str] = None
    video_overrides: dict[str, Any] = field(default_factory=dict)
    audio_overrides: dict[str, Any] = field(default_factory=dict)
    seed: int = 1
    intensity: float = 1.0
    texture: float = 1.0


# Intermediate passes are encoded near-losslessly. The generation loss a stack
# is meant to show comes from the era simulations themselves - which do their
# own real codec round-trips - not from us quietly mushing the picture between
# layers on top of that.
INTERMEDIATE_CRF = 12


def render_layers(
    input_path: str,
    output_path: str,
    layers: list[Layer],
    opts: RenderOptions,
    progress: Optional[ProgressCb] = None,
) -> str:
    """Render through each layer in turn, feeding each pass into the next.

    Sequential rather than one merged chain, so a stack compounds the way real
    generations do: layer 2 treats what layer 1 actually produced, including
    whatever resolution and detail layer 1 threw away. That also settles the era
    resolution question by construction - the harshest `proc_height` in the
    stack has already destroyed the detail by the time later layers run, so
    nothing can put it back.

    The cost is honest: N layers is N encodes and roughly N times the wall clock.
    """
    if not layers:
        raise ValueError("render_layers needs at least one layer")

    # Trimming and preview scaling belong to the first pass only; afterwards the
    # intermediate already *is* the trimmed, scaled clip.
    tmp_root = tempfile.mkdtemp(prefix="aesth_stack_", dir=os.environ.get("AESTHETICIAN_TMP") or None)
    total = len(layers)
    try:
        current = input_path
        for i, layer in enumerate(layers):
            last = i == total - 1
            step = RenderOptions(
                seed=layer.seed,
                intensity=layer.intensity,
                texture=layer.texture,
                variant=layer.variant,
                video_overrides=layer.video_overrides,
                audio_overrides=layer.audio_overrides,
                video_only=opts.video_only,
                audio_only=opts.audio_only,
                t0=opts.t0 if i == 0 else 0.0,
                source_t0=opts.clip_t0,
                duration=opts.duration if i == 0 else None,
                scale=opts.scale if i == 0 else 1.0,
                crf=opts.crf if last else INTERMEDIATE_CRF,
                keep_temp=opts.keep_temp,
            )
            dest = output_path if last else os.path.join(tmp_root, f"layer_{i}.mp4")

            # Each layer owns its slice of the bar, so one climb covers the lot.
            def scaled(phase: str, frac: float, _i: int = i) -> None:
                if progress:
                    progress(f"{phase} {_i + 1}/{total}" if total > 1 else phase,
                             min((_i + frac) / total, 1.0))

            render(current, dest, layer.preset, step, progress=scaled)
            current = dest
        return output_path
    finally:
        if opts.keep_temp:
            print(f"[aesthetician] stack temp kept at {tmp_root}")
        else:
            shutil.rmtree(tmp_root, ignore_errors=True)


def render(
    input_path: str,
    output_path: str,
    preset: Preset,
    opts: RenderOptions,
    progress: Optional[ProgressCb] = None,
) -> str:
    info = media.probe(input_path)
    duration, fps, n_frames = _timing(info, opts)

    if not info.has_video:
        return _render_audio_only(
            input_path, output_path, preset, opts, info, duration,
            _PhasedProgress(progress, {"audio": 0.86, "encode": 0.14, "done": 0.0}),
        )

    proc_w, proc_h, out_w, out_h = _video_geometry(info, preset, opts)

    variant = preset.variant(opts.variant)
    tmp_root = tempfile.mkdtemp(prefix="aesth_", dir=os.environ.get("AESTHETICIAN_TMP") or None)

    try:
        ctx = Context(
            width=proc_w,
            height=proc_h,
            fps=fps,
            n_frames=n_frames,
            sr=info.sr if info.has_audio else 48000,
            channels=min(info.channels, 2) if info.has_audio else 2,
            seed=opts.seed,
            intensity=opts.intensity,
            scratch_dir=tmp_root,
            asset_root=default_asset_root(),
            out_width=out_w,
            out_height=out_h,
            texture=opts.texture,
            t0=opts.clip_t0,
        )

        video_chain: list[Effect] = []
        audio_chain: list[Effect] = []
        if not opts.audio_only and preset.video:
            v_over = _merged_overrides(variant, opts.video_overrides, "video")
            video_chain = _live_chain(build_chain(preset.video), ctx, v_over)
        if not opts.video_only and info.has_audio and preset.audio:
            a_over = _merged_overrides(variant, opts.audio_overrides, "audio")
            audio_chain = _live_chain(build_chain(preset.audio), ctx, a_over)

        report = _PhasedProgress(progress, _phase_weights(bool(video_chain), info.has_audio))

        # ── video ─────────────────────────────────────────────────────
        src_matrix = media.source_matrix(info)
        if video_chain:
            video_out = _render_video(
                input_path, tmp_root, video_chain, ctx, fps, n_frames,
                proc_w, proc_h, out_w, out_h, opts, preset, duration, report, src_matrix,
            )
        else:
            # A straight copy still costs a transcode, and ffmpeg reports nothing
            # useful through this path, so bracket it rather than leaving the bar
            # parked at zero.
            report("video", 0.0)
            video_out = os.path.join(tmp_root, "video_copy.mp4")
            _plain_video(input_path, video_out, out_w, out_h, fps, opts.t0, duration, opts.crf, src_matrix)
            report("video", 1.0)

        # ── audio ─────────────────────────────────────────────────────
        audio_out: Optional[str] = None
        if info.has_audio:
            report("audio", 0.0)
            audio = media.read_audio(input_path, ctx.sr, ctx.channels, opts.t0, duration)
            for i, eff in enumerate(audio_chain):
                if eff.kind == "audio_filepass":
                    w_in = os.path.join(tmp_root, f"a_{i}_in.wav")
                    w_out = os.path.join(tmp_root, f"a_{i}_out.wav")
                    media.write_wav(w_in, audio, ctx.sr)
                    eff.file_pass(w_in, w_out, ctx)
                    audio = media.read_audio(w_out, ctx.sr, ctx.channels)
                else:
                    audio = eff.process_audio(audio, ctx)
                report("audio", (i + 1) / max(len(audio_chain), 1))
            n_target = int(round(duration * ctx.sr))
            if audio.shape[0] > n_target:
                audio = audio[:n_target]
            elif audio.shape[0] < n_target:
                audio = np.vstack([audio, np.zeros((n_target - audio.shape[0], audio.shape[1]), np.float32)])
            peak = float(np.max(np.abs(audio))) if audio.size else 0.0
            if peak > 0.999:
                audio = audio * (0.999 / peak)
            audio_out = os.path.join(tmp_root, "audio_final.wav")
            media.write_wav(audio_out, audio, ctx.sr)

        report("mux", 0.0)
        media.mux(video_out, audio_out, output_path)
        report("done", 1.0)
        return output_path
    finally:
        if opts.keep_temp:
            print(f"[aesthetician] temp kept at {tmp_root}")
        else:
            shutil.rmtree(tmp_root, ignore_errors=True)


def _render_audio_only(
    input_path: str,
    output_path: str,
    preset: Preset,
    opts: RenderOptions,
    info: "media.MediaInfo",
    duration: float,
    report: ProgressCb,
) -> str:
    """Treat a source that has no picture: only the preset's audio chain runs.

    Presets whose audio chain is empty are a no-op here rather than an error -
    the file is simply re-encoded - so a video-led preset can still be pointed at
    a stem without blowing up.
    """
    tmp_root = tempfile.mkdtemp(prefix="aesth_a_", dir=os.environ.get("AESTHETICIAN_TMP") or None)
    try:
        ctx = Context(
            width=0,
            height=0,
            fps=info.fps,
            n_frames=max(int(round(duration * info.fps)), 1),
            sr=info.sr,
            channels=min(info.channels, 2),
            seed=opts.seed,
            intensity=opts.intensity,
            scratch_dir=tmp_root,
            asset_root=default_asset_root(),
            texture=opts.texture,
            t0=opts.clip_t0,
        )
        chain: list[Effect] = []
        if not opts.video_only and preset.audio:
            over = _merged_overrides(preset.variant(opts.variant), opts.audio_overrides, "audio")
            chain = _live_chain(build_chain(preset.audio), ctx, over)

        report("audio", 0.0)
        audio = media.read_audio(input_path, ctx.sr, ctx.channels, opts.t0, duration)
        for i, eff in enumerate(chain):
            if eff.kind == "audio_filepass":
                w_in = os.path.join(tmp_root, f"a_{i}_in.wav")
                w_out = os.path.join(tmp_root, f"a_{i}_out.wav")
                media.write_wav(w_in, audio, ctx.sr)
                eff.file_pass(w_in, w_out, ctx)
                audio = media.read_audio(w_out, ctx.sr, ctx.channels)
            else:
                audio = eff.process_audio(audio, ctx)
            report("audio", (i + 1) / max(len(chain), 1))

        n_target = int(round(duration * ctx.sr))
        if audio.shape[0] > n_target:
            audio = audio[:n_target]
        elif audio.shape[0] < n_target:
            audio = np.vstack([audio, np.zeros((n_target - audio.shape[0], audio.shape[1]), np.float32)])
        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        if peak > 0.999:
            audio = audio * (0.999 / peak)

        report("encode", 0.0)
        wav = os.path.join(tmp_root, "final.wav")
        media.write_wav(wav, audio, ctx.sr)
        media.encode_audio_only(wav, output_path)
        report("done", 1.0)
        return output_path
    finally:
        if opts.keep_temp:
            print(f"[aesthetician] temp kept at {tmp_root}")
        else:
            shutil.rmtree(tmp_root, ignore_errors=True)


def _plain_video(src: str, dst: str, w: int, h: int, fps: float, t0: float, duration: float, crf: int,
                 src_matrix: str = "auto") -> None:
    """Scale/trim without frame processing, normalized to tagged BT.709.

    Downscaling alone used to flip how players read the result: an untagged HD
    source (shown as BT.709) became an untagged SD file (shown as BT.601).
    Converting to BT.709 and saying so keeps the colors identical at any size.
    """
    cmd = [media.FFMPEG, "-v", "error", "-nostdin", "-y"]
    if t0 > 0:
        cmd += ["-ss", f"{t0:.6f}"]
    cmd += ["-i", src, "-t", f"{duration:.6f}",
            "-vf", f"scale={w}:{h}:flags=lanczos:in_color_matrix={src_matrix}:out_color_matrix=bt709:out_range=tv,fps={fps:.6f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
            "-pix_fmt", "yuv420p", *media.BT709_TAGS, "-an", dst]
    media._run(cmd)


def _render_video(
    input_path: str,
    tmp_root: str,
    chain: list[Effect],
    ctx: Context,
    fps: float,
    n_frames: int,
    proc_w: int,
    proc_h: int,
    out_w: int,
    out_h: int,
    opts: RenderOptions,
    preset: Preset,
    duration: float,
    report: ProgressCb,
    src_matrix: str = "auto",
) -> str:
    segments = _segment_chain(chain)
    src_map = _compose_src_map(chain, ctx, n_frames)
    map_identity = bool(np.all(src_map == np.arange(n_frames)))
    map_consumed = False

    total_stream_frames = max(n_frames * len(segments), 1)
    done_frames = 0

    cur_input = input_path
    cur_is_source = True

    for si, seg in enumerate(segments):
        last = si == len(segments) - 1

        if seg and seg[0].kind == "filepass":
            if cur_is_source:
                inter = os.path.join(tmp_root, "seg_src.mp4")
                _plain_video(input_path, inter, proc_w, proc_h, fps, opts.t0, duration, 8, src_matrix)
                cur_input, cur_is_source = inter, False
            nxt = os.path.join(tmp_root, f"seg_{si}.mp4")
            seg[0].file_pass(cur_input, nxt, ctx)
            cur_input = nxt
            done_frames += n_frames
            report("video", done_frames / total_stream_frames)
            continue

        nxt = os.path.join(tmp_root, f"seg_{si}.mp4")
        final_here = last and (proc_w, proc_h) == (out_w, out_h)
        writer = media.FrameWriter(
            nxt, proc_w, proc_h, fps,
            crf=opts.crf if final_here else 8,
            preset="medium" if final_here else "fast",
            pix_fmt="yuv420p" if final_here else "yuv444p",
        )
        reader = media.read_frames(
            cur_input, proc_w, proc_h, fps,
            t0=opts.t0 if cur_is_source else 0.0,
            duration=duration if cur_is_source else None,
            matrix=src_matrix if cur_is_source else "auto",
        )
        use_map = not map_consumed and not map_identity
        cur_frame: Optional[np.ndarray] = None
        cur_idx = -1
        try:
            for fi in range(n_frames):
                want = int(src_map[fi]) if use_map else fi
                while cur_idx < want:
                    try:
                        cur_frame = next(reader)
                        cur_idx += 1
                    except StopIteration:
                        break
                if cur_frame is None:
                    break
                ctx.fi_out = fi
                ctx.fi_src = int(src_map[fi]) if not map_consumed else fi
                frame = cur_frame.copy()
                for eff in seg:
                    frame = eff.process(frame, ctx)
                    if frame.dtype != np.float32:
                        frame = frame.astype(np.float32)
                writer.write(np.clip(frame, 0.0, 1.0))
                done_frames += 1
                if fi % 10 == 0:
                    report("video", done_frames / total_stream_frames)
        finally:
            writer.close()
        map_consumed = True
        cur_input, cur_is_source = nxt, False

    if (proc_w, proc_h) != (out_w, out_h):
        flags = _upscale_flags(preset)
        final = os.path.join(tmp_root, "video_final.mp4")
        media._run(
            [
                media.FFMPEG, "-v", "error", "-nostdin", "-y", "-i", cur_input,
                "-vf", f"scale={out_w}:{out_h}:flags={flags}",
                "-c:v", "libx264", "-preset", "medium", "-crf", str(opts.crf),
                "-pix_fmt", "yuv420p", *media.BT709_TAGS, "-an", final,
            ]
        )
        cur_input = final
    return cur_input


def default_asset_root() -> str:
    """Where overlay plates and audio beds live.

    Packaged builds install the package into a bundled runtime, so the
    repo-relative guess is wrong there - they set AESTHETICIAN_ASSETS instead.
    """
    env = os.environ.get("AESTHETICIAN_ASSETS")
    if env:
        return env
    pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(os.path.dirname(pkg_dir), "assets")


# ── stills ─────────────────────────────────────────────────────────────
@dataclass
class Still:
    """The result of a still render."""
    path: str
    # True when this is exactly frame 0 of the clip, one H.264 pass aside.
    exact: bool


def render_still(
    input_path: str,
    output_path: str,
    preset: Preset,
    opts: RenderOptions,
    n_frames_override: Optional[int] = None,
) -> Still:
    """Frame 0 of what `render` would produce, without rendering the rest.

    The point is a picture to judge a knob by, several seconds before the clip
    that confirms it. Everything that decides a pixel is set up exactly as
    `render` sets it up - era resolution, delivery size, seed, master dials,
    variant, overrides - and `n_frames` above all, because the temporal tracks
    in rng.py are filtered and percentile-normalised across their whole length.
    Rendering one frame *as a one-frame clip* would move time-base error,
    flagging, tracking error and gate weave to a full-scale excursion and show
    you a frame the preview never contains. Keeping the count and stopping after
    the first frame costs a ninetieth of the work and reproduces it.

    Real codec passes are the exception. They treat an encoded clip, and one
    frame is not one: they run here on a one-frame file, which is the same codec
    doing the same thing with no neighbouring frames to predict from. Close, but
    not the clip, and `Still.exact` says so.
    """
    info = media.probe(input_path)
    if not info.has_video:
        raise ValueError("a still needs a source with a picture")
    duration, fps, n_frames = _timing(info, opts)
    if n_frames_override is not None:
        n_frames = max(int(n_frames_override), 1)
    proc_w, proc_h, out_w, out_h = _video_geometry(info, preset, opts)
    variant = preset.variant(opts.variant)
    tmp_root = tempfile.mkdtemp(prefix="aesth_still_", dir=os.environ.get("AESTHETICIAN_TMP") or None)

    try:
        ctx = Context(
            width=proc_w,
            height=proc_h,
            fps=fps,
            n_frames=n_frames,
            sr=info.sr if info.has_audio else 48000,
            channels=min(info.channels, 2) if info.has_audio else 2,
            seed=opts.seed,
            intensity=opts.intensity,
            scratch_dir=tmp_root,
            asset_root=default_asset_root(),
            out_width=out_w,
            out_height=out_h,
            texture=opts.texture,
            t0=opts.clip_t0,
        )

        chain: list[Effect] = []
        if preset.video:
            v_over = _merged_overrides(variant, opts.video_overrides, "video")
            chain = _live_chain(build_chain(preset.video), ctx, v_over)

        exact = not any(eff.kind == "filepass" for eff in chain)

        # Frame 0 of the output can be a later frame of the source, if anything
        # in the chain remaps time.
        want = int(_compose_src_map(chain, ctx, n_frames)[0]) if chain else 0
        reader = media.read_frames(
            input_path, proc_w, proc_h, fps,
            t0=opts.t0, duration=duration, matrix=media.source_matrix(info),
        )
        frame: Optional[np.ndarray] = None
        try:
            for i, got in enumerate(reader):
                frame = got
                if i >= want:
                    break
        finally:
            reader.close()
        if frame is None:
            raise media.MediaError("no frame to build a still from")

        ctx.fi_out = 0
        ctx.fi_src = want
        for eff in chain:
            if eff.kind == "filepass":
                one_in = os.path.join(tmp_root, f"{eff.key}_in.mp4")
                one_out = os.path.join(tmp_root, f"{eff.key}_out.mp4")
                media.write_one_frame_video(one_in, frame, fps)
                eff.file_pass(one_in, one_out, ctx)
                got = next(media.read_frames(one_out, proc_w, proc_h, fps), None)
                if got is not None:
                    frame = got
            else:
                frame = eff.process(frame, ctx)
                if frame.dtype != np.float32:
                    frame = frame.astype(np.float32)

        media.write_image(output_path, frame, out_w, out_h, _upscale_flags(preset))
        return Still(path=output_path, exact=exact)
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def render_still_layers(
    input_path: str,
    output_path: str,
    layers: list[Layer],
    opts: RenderOptions,
) -> Still:
    """A stack's frame 0: each layer's still treated by the next.

    The clip version feeds each layer the *video* the one below produced, so a
    still of a stack is an approximation by construction - layer two is reading
    one frame where it would have read a clip. Every layer still keeps the real
    frame count, so nothing drifts on the temporal tracks; what it cannot keep
    is the generation loss of a full encode between layers.
    """
    if not layers:
        raise ValueError("render_still_layers needs at least one layer")
    tmp_root = tempfile.mkdtemp(prefix="aesth_still_stack_", dir=os.environ.get("AESTHETICIAN_TMP") or None)
    try:
        info = media.probe(input_path)
        _, _, n_frames = _timing(info, opts)
        current = input_path
        exact = len(layers) == 1
        for i, layer in enumerate(layers):
            last = i == len(layers) - 1
            step = RenderOptions(
                seed=layer.seed,
                intensity=layer.intensity,
                texture=layer.texture,
                variant=layer.variant,
                video_overrides=layer.video_overrides,
                audio_overrides=layer.audio_overrides,
                # Trimming and preview scaling belong to the first pass only,
                # exactly as render_layers does it.
                t0=opts.t0 if i == 0 else 0.0,
                source_t0=opts.clip_t0,
                duration=opts.duration if i == 0 else None,
                scale=opts.scale if i == 0 else 1.0,
                crf=opts.crf,
            )
            dest = output_path if last else os.path.join(tmp_root, f"still_{i}.png")
            got = render_still(current, dest, layer.preset, step, n_frames_override=n_frames)
            exact = exact and got.exact
            current = dest
        return Still(path=output_path, exact=exact)
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


# ── event plans ────────────────────────────────────────────────────────
def _plan_one(input_w: int, input_h: int, info: "media.MediaInfo", preset: Preset,
              opts: RenderOptions, tmp_root: str) -> tuple[list[dict], int, int]:
    """Events for one preset, plus the size it hands on to the next layer."""
    duration, fps, n_frames = _timing(info, opts)
    out_w, out_h = _even(int(input_w * opts.scale)), _even(int(input_h * opts.scale))
    if preset.proc_height and preset.proc_height < out_h:
        proc_h = _even(preset.proc_height)
        proc_w = _even(out_w * proc_h / out_h)
    else:
        proc_w, proc_h = out_w, out_h
    ctx = Context(
        width=proc_w, height=proc_h, fps=fps, n_frames=n_frames,
        sr=info.sr if info.has_audio else 48000,
        channels=min(info.channels, 2) if info.has_audio else 2,
        seed=opts.seed, intensity=opts.intensity, scratch_dir=tmp_root,
        asset_root=default_asset_root(), out_width=out_w, out_height=out_h,
        texture=opts.texture, t0=opts.clip_t0,
    )
    over = _merged_overrides(preset.variant(opts.variant), opts.video_overrides, "video")
    rows: list[dict] = []
    for eff in _live_chain(build_chain(preset.video), ctx, over):
        for ev in eff.events(ctx):
            rows.append({"effect": eff.key, "kind": ev.kind,
                         "t": round(ev.t, 4), "dur": round(ev.dur, 4),
                         "detail": ev.detail})
    return rows, out_w, out_h


def plan_events(input_path: str, layers: list[Layer], opts: RenderOptions) -> dict:
    """What discrete damage a render would produce, without rendering it.

    The whole point of hoisting the schedules: a timeline can draw these, and
    eventually you can move one. Costs a chain `prepare`, not a render.
    """
    info = media.probe(input_path)
    if not info.has_video:
        return {"duration": info.duration, "fps": info.fps, "events": []}
    duration, fps, n_frames = _timing(info, opts)
    tmp_root = tempfile.mkdtemp(prefix="aesth_plan_", dir=os.environ.get("AESTHETICIAN_TMP") or None)
    try:
        rows: list[dict] = []
        w, h = info.width, info.height
        for i, layer in enumerate(layers):
            step = RenderOptions(
                seed=layer.seed, intensity=layer.intensity, texture=layer.texture,
                variant=layer.variant, video_overrides=layer.video_overrides,
                audio_overrides=layer.audio_overrides,
                t0=opts.t0 if i == 0 else 0.0, source_t0=opts.clip_t0,
                duration=opts.duration if i == 0 else None,
                scale=opts.scale if i == 0 else 1.0, crf=opts.crf,
            )
            got, w, h = _plan_one(w, h, info, layer.preset, step, tmp_root)
            for r in got:
                r["layer"] = i
            rows.extend(got)
        rows.sort(key=lambda r: (r["t"], r["layer"], r["effect"]))
        return {"t0": opts.clip_t0, "duration": duration, "fps": fps,
                "n_frames": n_frames, "events": rows}
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
