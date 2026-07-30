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
    duration: Optional[float] = None
    scale: float = 1.0            # output scale factor (previews)
    crf: int = 17
    keep_temp: bool = False


def _merged_overrides(variant: Optional[Variant], user: dict[str, Any], which: str) -> dict[str, dict[str, Any]]:
    merged: dict[str, Any] = {}
    if variant:
        merged.update(getattr(variant, which))
    merged.update(user)
    return parse_override_paths(merged)


def _even(x: int) -> int:
    return max(2, int(round(x / 2)) * 2)


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


def render(
    input_path: str,
    output_path: str,
    preset: Preset,
    opts: RenderOptions,
    progress: Optional[ProgressCb] = None,
) -> str:
    def report(phase: str, frac: float) -> None:
        if progress:
            progress(phase, min(max(frac, 0.0), 1.0))

    info = media.probe(input_path)
    duration = opts.duration if opts.duration is not None else max(info.duration - opts.t0, 0.1)
    duration = min(duration, max(info.duration - opts.t0, 0.1))
    fps = info.fps
    n_frames = max(int(round(duration * fps)), 1)

    if not info.has_video:
        return _render_audio_only(input_path, output_path, preset, opts, info, duration, report)

    out_w, out_h = _even(int(info.width * opts.scale)), _even(int(info.height * opts.scale))
    if preset.proc_height and preset.proc_height < out_h:
        proc_h = _even(preset.proc_height)
        proc_w = _even(out_w * proc_h / out_h)
    else:
        proc_w, proc_h = out_w, out_h

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
        )

        video_chain: list[Effect] = []
        audio_chain: list[Effect] = []
        if not opts.audio_only and preset.video:
            video_chain = build_chain(preset.video)
            v_over = _merged_overrides(variant, opts.video_overrides, "video")
            for eff in video_chain:
                eff.resolve(ctx, v_over.get(eff.key))
                eff.prepare(ctx)
        if not opts.video_only and info.has_audio and preset.audio:
            audio_chain = build_chain(preset.audio)
            a_over = _merged_overrides(variant, opts.audio_overrides, "audio")
            for eff in audio_chain:
                eff.resolve(ctx, a_over.get(eff.key))
                eff.prepare(ctx)

        # ── video ─────────────────────────────────────────────────────
        if video_chain:
            video_out = _render_video(
                input_path, tmp_root, video_chain, ctx, fps, n_frames,
                proc_w, proc_h, out_w, out_h, opts, preset, duration, report,
            )
        else:
            video_out = os.path.join(tmp_root, "video_copy.mp4")
            _plain_video(input_path, video_out, out_w, out_h, fps, opts.t0, duration, opts.crf)

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

    Presets whose audio chain is empty are a no-op here rather than an error —
    the file is simply re-encoded — so a video-led preset can still be pointed at
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
        )
        chain: list[Effect] = []
        if not opts.video_only and preset.audio:
            chain = build_chain(preset.audio)
            over = _merged_overrides(preset.variant(opts.variant), opts.audio_overrides, "audio")
            for eff in chain:
                eff.resolve(ctx, over.get(eff.key))
                eff.prepare(ctx)

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


def _plain_video(src: str, dst: str, w: int, h: int, fps: float, t0: float, duration: float, crf: int) -> None:
    cmd = [media.FFMPEG, "-v", "error", "-nostdin", "-y"]
    if t0 > 0:
        cmd += ["-ss", f"{t0:.6f}"]
    cmd += ["-i", src, "-t", f"{duration:.6f}",
            "-vf", f"scale={w}:{h}:flags=lanczos,fps={fps:.6f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
            "-pix_fmt", "yuv420p", "-an", dst]
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
                _plain_video(input_path, inter, proc_w, proc_h, fps, opts.t0, duration, 8)
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
        flavor = preset.upscale if preset.upscale != "auto" else "soft"
        flags = {"sharp": "lanczos", "soft": "bicubic"}.get(flavor, "bicubic")
        final = os.path.join(tmp_root, "video_final.mp4")
        media._run(
            [
                media.FFMPEG, "-v", "error", "-nostdin", "-y", "-i", cur_input,
                "-vf", f"scale={out_w}:{out_h}:flags={flags}",
                "-c:v", "libx264", "-preset", "medium", "-crf", str(opts.crf),
                "-pix_fmt", "yuv420p", "-an", final,
            ]
        )
        cur_input = final
    return cur_input


def default_asset_root() -> str:
    """Where overlay plates and audio beds live.

    Packaged builds install the package into a bundled runtime, so the
    repo-relative guess is wrong there — they set AESTHETICIAN_ASSETS instead.
    """
    env = os.environ.get("AESTHETICIAN_ASSETS")
    if env:
        return env
    pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(os.path.dirname(pkg_dir), "assets")
