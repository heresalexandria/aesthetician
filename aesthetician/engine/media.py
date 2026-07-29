"""ffmpeg-backed media I/O: probing, frame streaming, audio buffers, muxing."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Iterator, Optional

import numpy as np

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"


class MediaError(RuntimeError):
    pass


@dataclass
class MediaInfo:
    path: str
    width: int
    height: int
    fps: float
    duration: float
    n_frames: int
    has_audio: bool
    sr: int
    channels: int


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, **kw)
    if proc.returncode != 0:
        raise MediaError(
            f"command failed ({proc.returncode}): {' '.join(cmd[:12])}…\n{proc.stderr.decode(errors='replace')[-2000:]}"
        )
    return proc


def probe(path: str) -> MediaInfo:
    if not os.path.exists(path):
        raise MediaError(f"no such file: {path}")
    proc = _run(
        [
            FFPROBE, "-v", "error", "-print_format", "json",
            "-show_format", "-show_streams", path,
        ]
    )
    data = json.loads(proc.stdout.decode())
    v = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    if v is None:
        raise MediaError(f"no video stream in {path}")
    num, den = (v.get("r_frame_rate") or "30/1").split("/")
    fps = float(num) / max(float(den), 1.0)
    duration = float(data.get("format", {}).get("duration") or v.get("duration") or 0.0)
    n_frames = int(v.get("nb_frames") or 0) or max(int(round(duration * fps)), 1)
    return MediaInfo(
        path=path,
        width=int(v["width"]),
        height=int(v["height"]),
        fps=fps,
        duration=duration,
        n_frames=n_frames,
        has_audio=a is not None,
        sr=int(a["sample_rate"]) if a else 48000,
        channels=int(a.get("channels", 2)) if a else 2,
    )


def read_frames(
    path: str,
    width: int,
    height: int,
    fps: float,
    t0: float = 0.0,
    duration: Optional[float] = None,
) -> Iterator[np.ndarray]:
    """Stream frames as float32 RGB HxWx3 in [0,1], scaled to width x height."""
    cmd = [FFMPEG, "-v", "error", "-nostdin"]
    if t0 > 0:
        cmd += ["-ss", f"{t0:.6f}"]
    cmd += ["-i", path]
    if duration is not None:
        cmd += ["-t", f"{duration:.6f}"]
    cmd += [
        "-vf", f"scale={width}:{height}:flags=lanczos,fps={fps:.6f}",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ]
    frame_bytes = width * height * 3
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        assert proc.stdout is not None
        while True:
            buf = proc.stdout.read(frame_bytes)
            if len(buf) < frame_bytes:
                break
            yield (
                np.frombuffer(buf, dtype=np.uint8).reshape(height, width, 3).astype(np.float32) / 255.0
            )
    finally:
        proc.stdout.close()  # type: ignore[union-attr]
        stderr = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
        code = proc.wait()
        if code not in (0, -13):  # -13: SIGPIPE when we stop early
            raise MediaError(f"ffmpeg decode failed ({code}): {stderr[-1500:]}")


class FrameWriter:
    """Pipe float32 RGB frames into an x264 encode."""

    def __init__(
        self,
        path: str,
        width: int,
        height: int,
        fps: float,
        crf: int = 17,
        preset: str = "medium",
        pix_fmt: str = "yuv420p",
    ):
        self.path = path
        self.width = width
        self.height = height
        vf = []
        if pix_fmt == "yuv420p" and (width % 2 or height % 2):
            vf = ["-vf", f"pad={width + width % 2}:{height + height % 2}"]
        cmd = [
            FFMPEG, "-v", "error", "-nostdin", "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{width}x{height}", "-r", f"{fps:.6f}",
            "-i", "-",
            *vf,
            "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
            "-pix_fmt", pix_fmt, "-movflags", "+faststart",
            path,
        ]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    def write(self, frame: np.ndarray) -> None:
        assert self.proc.stdin is not None
        data = np.clip(frame * 255.0 + 0.5, 0, 255).astype(np.uint8).tobytes()
        self.proc.stdin.write(data)

    def close(self) -> None:
        if self.proc.stdin:
            self.proc.stdin.close()
        stderr = self.proc.stderr.read().decode(errors="replace") if self.proc.stderr else ""
        if self.proc.wait() != 0:
            raise MediaError(f"ffmpeg encode failed: {stderr[-1500:]}")

    def __enter__(self) -> "FrameWriter":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def read_audio(path: str, sr: int, channels: int = 2, t0: float = 0.0, duration: Optional[float] = None) -> np.ndarray:
    """Decode audio to float32 (n, channels)."""
    cmd = [FFMPEG, "-v", "error", "-nostdin"]
    if t0 > 0:
        cmd += ["-ss", f"{t0:.6f}"]
    cmd += ["-i", path]
    if duration is not None:
        cmd += ["-t", f"{duration:.6f}"]
    cmd += ["-vn", "-f", "f32le", "-acodec", "pcm_f32le", "-ar", str(sr), "-ac", str(channels), "-"]
    proc = _run(cmd)
    x = np.frombuffer(proc.stdout, dtype=np.float32)
    if channels > 1:
        x = x.reshape(-1, channels)
    else:
        x = x.reshape(-1, 1)
    return x.copy()


def write_wav(path: str, audio: np.ndarray, sr: int) -> None:
    audio = np.asarray(audio, dtype=np.float32)
    ch = 1 if audio.ndim == 1 else audio.shape[1]
    cmd = [
        FFMPEG, "-v", "error", "-nostdin", "-y",
        "-f", "f32le", "-ar", str(sr), "-ac", str(ch), "-i", "-",
        "-c:a", "pcm_s24le", path,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdin is not None
    proc.stdin.write(audio.astype(np.float32).tobytes())
    proc.stdin.close()
    stderr = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
    if proc.wait() != 0:
        raise MediaError(f"wav write failed: {stderr[-1000:]}")


def mux(video_path: str, audio_path: Optional[str], out_path: str, audio_bitrate: str = "320k") -> None:
    if audio_path:
        cmd = [
            FFMPEG, "-v", "error", "-nostdin", "-y",
            "-i", video_path, "-i", audio_path,
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", audio_bitrate,
            "-movflags", "+faststart", "-shortest",
            out_path,
        ]
    else:
        cmd = [
            FFMPEG, "-v", "error", "-nostdin", "-y",
            "-i", video_path, "-an", "-c:v", "copy", "-movflags", "+faststart", out_path,
        ]
    _run(cmd)


def video_roundtrip(in_path: str, out_path: str, vcodec_args: list[str], scale: Optional[str] = None) -> None:
    """Encode through a real (era) codec then back to an editable intermediate.

    `vcodec_args` example: ["-c:v", "mpeg2video", "-b:v", "1200k"].
    """
    tmp = out_path + ".rt.nut"
    vf = ["-vf", scale] if scale else []
    _run([FFMPEG, "-v", "error", "-nostdin", "-y", "-i", in_path, *vf, *vcodec_args, "-an", tmp])
    _run(
        [
            FFMPEG, "-v", "error", "-nostdin", "-y", "-i", tmp,
            "-c:v", "libx264", "-preset", "fast", "-crf", "8", "-pix_fmt", "yuv444p", "-an",
            out_path,
        ]
    )
    os.unlink(tmp)


def audio_roundtrip(in_wav: str, out_wav: str, acodec_args: list[str], mid_ext: str = "bin.nut") -> None:
    """Round-trip audio through a real lossy codec (mp3, gsm, adpcm…)."""
    tmp = out_wav + "." + mid_ext
    _run([FFMPEG, "-v", "error", "-nostdin", "-y", "-i", in_wav, *acodec_args, tmp])
    _run([FFMPEG, "-v", "error", "-nostdin", "-y", "-i", tmp, "-c:a", "pcm_s24le", out_wav])
    os.unlink(tmp)


def extract_intermediate(in_path: str, out_path: str, width: int, height: int, fps: float) -> None:
    """Write a high-quality intermediate for file-pass chains."""
    _run(
        [
            FFMPEG, "-v", "error", "-nostdin", "-y", "-i", in_path,
            "-vf", f"scale={width}:{height}:flags=lanczos,fps={fps:.6f}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "8", "-pix_fmt", "yuv444p", "-an",
            out_path,
        ]
    )
