"""ffmpeg-backed media I/O: probing, frame streaming, audio buffers, muxing."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Iterator, Optional

import numpy as np

# Packaged builds ship their own static binaries and point these at them.
FFMPEG = os.environ.get("AESTHETICIAN_FFMPEG") or "ffmpeg"
FFPROBE = os.environ.get("AESTHETICIAN_FFPROBE") or "ffprobe"


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
    has_video: bool
    has_audio: bool
    sr: int
    channels: int
    color_space: str = ""  # ffprobe color_space tag, "" when the file is untagged


# Every YUV encode the engine produces is BT.709, and says so. Untagged output
# is what made exports drift: swscale converts RGB with BT.601 coefficients by
# default, players guess BT.709 for anything HD, and the preview (small, so
# guessed BT.601) was the only place the colors looked right.
BT709_TAGS = [
    "-colorspace", "bt709", "-color_primaries", "bt709",
    "-color_trc", "bt709", "-color_range", "tv",
]

# ffprobe color_space values mapped onto vf_scale's in_color_matrix names.
_MATRIX_NAMES = {
    "bt709": "bt709",
    "bt601": "bt601", "bt470bg": "bt601", "smpte170m": "bt601",
    "smpte240m": "smpte240m", "fcc": "fcc",
    "bt2020nc": "bt2020", "bt2020c": "bt2020",
}


def source_matrix(info: MediaInfo) -> str:
    """The YUV matrix a player would decode this file with: its tag when it has
    a usable one, else the SD/HD guess (untagged HD is shown as BT.709)."""
    tagged = _MATRIX_NAMES.get((info.color_space or "").lower())
    if tagged:
        return tagged
    return "bt709" if info.height >= 720 or info.width >= 1280 else "bt601"


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
    def _is_real_video(st: dict) -> bool:
        """Cover art is carried as a video stream. A tagged MP3 therefore looks
        like a 1-frame video file unless attached pictures are excluded."""
        if st.get("codec_type") != "video":
            return False
        if int(st.get("disposition", {}).get("attached_pic", 0)):
            return False
        # Some muxers omit the disposition flag; a single frame with no frame rate
        # is album art either way.
        if st.get("avg_frame_rate") in ("0/0", "0/1", None) and str(st.get("nb_frames", "")) in ("1", ""):
            return False
        return True

    v = next((st for st in data.get("streams", []) if _is_real_video(st)), None)
    a = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    if v is None and a is None:
        raise MediaError(f"no video or audio stream in {path}")

    fmt_duration = float(data.get("format", {}).get("duration") or 0.0)
    if v is None:
        # Audio-only source (a WAV, MP3, stem…). Geometry is meaningless, but the
        # engine still needs a nominal frame clock: audio effects draw their
        # per-frame modulation tracks from ctx.noise, which is indexed in frames.
        duration = fmt_duration or float(a.get("duration") or 0.0)
        fps = 30.0
        return MediaInfo(
            path=path,
            width=0,
            height=0,
            fps=fps,
            duration=duration,
            n_frames=max(int(round(duration * fps)), 1),
            has_video=False,
            has_audio=True,
            sr=int(a["sample_rate"]),
            channels=int(a.get("channels", 2)),
        )

    num, den = (v.get("r_frame_rate") or "30/1").split("/")
    fps = float(num) / max(float(den), 1.0)
    duration = fmt_duration or float(v.get("duration") or 0.0)
    n_frames = int(v.get("nb_frames") or 0) or max(int(round(duration * fps)), 1)
    width, height = display_geometry(v)
    return MediaInfo(
        path=path,
        width=width,
        height=height,
        fps=fps,
        duration=duration,
        n_frames=n_frames,
        has_video=True,
        has_audio=a is not None,
        sr=int(a["sample_rate"]) if a else 48000,
        channels=int(a.get("channels", 2)) if a else 2,
        color_space=v.get("color_space") or "",
    )


def display_geometry(video_stream: dict) -> tuple[int, int]:
    """Upright square-pixel dimensions, matching FFmpeg's automatic rotation.

    Phone footage often stores landscape pixels with a 90-degree display
    matrix; SD archives can store non-square pixels. Coded width/height alone
    would squeeze both before an effect even sees the source.
    """
    width, height = int(video_stream["width"]), int(video_stream["height"])
    try:
        num, den = map(float, (video_stream.get("sample_aspect_ratio") or "1:1").split(":"))
        if np.isfinite(num) and np.isfinite(den) and num > 0 and den > 0:
            width = max(1, round(width * num / den))
    except (ValueError, TypeError):
        pass
    rotation = video_stream.get("tags", {}).get("rotate", 0)
    for data in video_stream.get("side_data_list", []):
        if "rotation" in data:
            rotation = data["rotation"]
            break
    try:
        if round(float(rotation) / 90) % 2:
            width, height = height, width
    except (ValueError, TypeError, OverflowError):
        pass
    return width, height


def read_frames(
    path: str,
    width: int,
    height: int,
    fps: float,
    t0: float = 0.0,
    duration: Optional[float] = None,
    matrix: str = "auto",
) -> Iterator[np.ndarray]:
    """Stream frames as float32 RGB HxWx3 in [0,1], scaled to width x height.

    `matrix` is the YUV matrix used for the RGB conversion. "auto" honors the
    file's tag and suits engine intermediates (always tagged); pass
    source_matrix(info) when reading user files, so untagged HD decodes the way
    a player would show it instead of falling back to swscale's BT.601.
    """
    cmd = [FFMPEG, "-v", "error", "-nostdin"]
    if t0 > 0:
        cmd += ["-ss", f"{t0:.6f}"]
    cmd += ["-i", path]
    if duration is not None:
        cmd += ["-t", f"{duration:.6f}"]
    cmd += [
        "-vf", f"scale={width}:{height}:flags=lanczos:in_color_matrix={matrix},fps={fps:.6f}",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ]
    frame_bytes = width * height * 3
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    finished = False
    try:
        assert proc.stdout is not None
        while True:
            buf = proc.stdout.read(frame_bytes)
            if len(buf) < frame_bytes:
                finished = True
                break
            yield (
                np.frombuffer(buf, dtype=np.uint8).reshape(height, width, 3).astype(np.float32) / 255.0
            )
    finally:
        proc.stdout.close()  # type: ignore[union-attr]
        if not finished:
            # generator closed early (e.g. remap consumed fewer frames) - not an error
            proc.kill()
            proc.wait()
            if proc.stderr:
                proc.stderr.close()
        else:
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
        chain = []
        if pix_fmt == "yuv420p" and (width % 2 or height % 2):
            chain.append(f"pad={width + width % 2}:{height + height % 2}")
        # The format filter downstream makes this scale instance perform the
        # RGB->YUV conversion itself; without it the encoder inserts its own
        # with BT.601 coefficients.
        chain += ["scale=out_color_matrix=bt709:out_range=tv", f"format={pix_fmt}"]
        cmd = [
            FFMPEG, "-v", "error", "-nostdin", "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{width}x{height}", "-r", f"{fps:.6f}",
            "-i", "-",
            "-vf", ",".join(chain),
            "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
            *BT709_TAGS, "-movflags", "+faststart",
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


def encode_audio_only(wav_path: str, out_path: str, bitrate: str = "320k") -> None:
    """Deliver a treated audio-only render. WAV stays lossless; anything else
    becomes AAC (or MP3/FLAC/ALAC when the extension asks for it)."""
    ext = os.path.splitext(out_path)[1].lower()
    codec = {
        ".wav": ["-c:a", "pcm_s24le"],
        ".flac": ["-c:a", "flac"],
        ".mp3": ["-c:a", "libmp3lame", "-b:a", bitrate],
        ".m4a": ["-c:a", "aac", "-b:a", bitrate],
        ".aac": ["-c:a", "aac", "-b:a", bitrate],
        ".aif": ["-c:a", "pcm_s24be"],
        ".aiff": ["-c:a", "pcm_s24be"],
    }.get(ext, ["-c:a", "aac", "-b:a", bitrate])
    _run([FFMPEG, "-v", "error", "-nostdin", "-y", "-i", wav_path, "-vn", *codec, out_path])


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
    # Era codecs drop the color tags but never touch the matrix, so the
    # intermediate coming back is still BT.709 data; relabel it as such.
    _run(
        [
            FFMPEG, "-v", "error", "-nostdin", "-y", "-i", tmp,
            "-c:v", "libx264", "-preset", "fast", "-crf", "8", "-pix_fmt", "yuv444p",
            *BT709_TAGS, "-an",
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
            "-vf", f"scale={width}:{height}:flags=lanczos,setsar=1,fps={fps:.6f}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "8", "-pix_fmt", "yuv444p",
            *BT709_TAGS, "-an",
            out_path,
        ]
    )


def write_image(path: str, frame: np.ndarray, out_w: int, out_h: int, flags: str = "bicubic") -> None:
    """Write one float32 RGB frame as a PNG, scaled the way the clip would be.

    The scale filter mirrors the final upscale in render.py so a still and the
    clip it previews are the same picture at the same size. What the still does
    not carry is the clip's own H.264 pass, so it is the render one step before
    the preview's compression rather than a copy of the compressed result.
    """
    h, w = frame.shape[:2]
    buf = (np.clip(frame, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8).tobytes()
    vf = [] if (w, h) == (out_w, out_h) else ["-vf", f"scale={out_w}:{out_h}:flags={flags}"]
    proc = subprocess.Popen(
        [FFMPEG, "-v", "error", "-nostdin", "-y",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-i", "-",
         *vf, "-frames:v", "1", path],
        stdin=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    _, err = proc.communicate(buf)
    if proc.returncode != 0:
        raise MediaError(f"still encode failed ({proc.returncode}): {err.decode(errors='replace')[-1500:]}")


def write_one_frame_video(path: str, frame: np.ndarray, fps: float) -> None:
    """A one-frame clip, so a file-pass effect has a file to chew on."""
    h, w = frame.shape[:2]
    buf = (np.clip(frame, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8).tobytes()
    proc = subprocess.Popen(
        [FFMPEG, "-v", "error", "-nostdin", "-y",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", f"{fps:.6f}", "-i", "-",
         "-c:v", "libx264", "-preset", "fast", "-crf", "8", "-pix_fmt", "yuv444p",
         *BT709_TAGS, "-an", path],
        stdin=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    _, err = proc.communicate(buf)
    if proc.returncode != 0:
        raise MediaError(f"one-frame encode failed ({proc.returncode}): {err.decode(errors='replace')[-1500:]}")
