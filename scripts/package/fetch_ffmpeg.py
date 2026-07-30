"""Fetch static ffmpeg + ffprobe binaries for a target.

The engine shells out to ffmpeg for every decode/encode and to ffprobe for every
probe, so a packaged app has to carry them: we cannot assume Homebrew.

Licensing: both sources below are built with `--enable-gpl --enable-version3`
(and *not* `--enable-nonfree`), i.e. GPLv3. Shipping them makes the resulting
DMG/installer a GPLv3 distribution - see docs/packaging.md.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

from .common import FFMPEG_CACHE, download, extract, human, log, rmtree, size_of
from .targets import FFMPEG_MAC_URL, FFMPEG_WIN_TAG, FFMPEG_WIN_URL, Target

MAC_ARCH = {"mac-arm64": "arm64", "mac-x64": "amd64"}


def _mark_exec(p: Path) -> None:
    p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _fetch_mac(target: Target, out: Path) -> None:
    arch = MAC_ARCH[target.key]
    for tool in ("ffmpeg", "ffprobe"):
        url = FFMPEG_MAC_URL.format(arch=arch, tool=tool)
        zip_path = download(url, f"{tool}-{target.key}.zip")
        staging = FFMPEG_CACHE / f".{target.key}-{tool}"
        extract(zip_path, staging)
        found = next((p for p in staging.rglob(tool) if p.is_file()), None)
        if found is None:
            raise SystemExit(f"{tool} not found inside {zip_path.name}")
        dest = out / tool
        rmtree(dest)
        found.replace(dest)
        _mark_exec(dest)
        rmtree(staging)


def _fetch_win(target: Target, out: Path) -> None:
    url = FFMPEG_WIN_URL.format(tag=FFMPEG_WIN_TAG)
    zip_path = download(url, f"ffmpeg-{FFMPEG_WIN_TAG}-win64-gpl.zip")
    staging = FFMPEG_CACHE / f".{target.key}-extract"
    extract(zip_path, staging)
    for tool in ("ffmpeg.exe", "ffprobe.exe"):
        found = next((p for p in staging.rglob(tool) if p.is_file()), None)
        if found is None:
            raise SystemExit(f"{tool} not found inside {zip_path.name}")
        dest = out / tool
        rmtree(dest)
        found.replace(dest)
    # Ship the GPL text alongside the binaries - required by the licence.
    lic = next((p for p in staging.rglob("LICENSE*") if p.is_file()), None)
    if lic is not None:
        (out / "FFMPEG-LICENSE.txt").write_bytes(lic.read_bytes())
    rmtree(staging)


def fetch(target: Target, *, force: bool = False) -> Path:
    """Return a directory containing ffmpeg/ffprobe for `target`."""
    out = FFMPEG_CACHE / target.key
    ffmpeg = out / f"ffmpeg{target.exe_suffix}"
    ffprobe = out / f"ffprobe{target.exe_suffix}"
    if not force and ffmpeg.is_file() and ffprobe.is_file():
        log(f"ffmpeg cached: {target.key} ({human(size_of(out))})")
        return out
    out.mkdir(parents=True, exist_ok=True)
    if target.key.startswith("mac"):
        _fetch_mac(target, out)
    else:
        _fetch_win(target, out)
    log(f"ffmpeg {target.key}: {human(size_of(out))}")
    return out


REQUIRED_VIDEO_ENCODERS = ("libx264", "mpeg1video", "mpeg2video", "mpeg4",
                           "msmpeg4", "flv", "h263p", "mjpeg")
REQUIRED_AUDIO_ENCODERS = ("aac", "libmp3lame", "pcm_s24le")


def verify(target: Target, ffmpeg_dir: Path) -> str:
    """Run the fetched ffmpeg and confirm the encoders the presets need exist."""
    exe = ffmpeg_dir / f"ffmpeg{target.exe_suffix}"
    launcher: list[str] = []
    if target.key == "mac-x64" and os.uname().machine == "arm64":
        launcher = ["arch", "-x86_64"]
    if target.key.startswith("win"):
        return "not executable here (Windows build)"
    ver = subprocess.run(launcher + [str(exe), "-version"], capture_output=True, text=True)
    if ver.returncode != 0:
        raise SystemExit(f"{exe} failed to run: {ver.stderr[-500:]}")
    first = ver.stdout.splitlines()[0]
    enc = subprocess.run(launcher + [str(exe), "-hide_banner", "-encoders"],
                         capture_output=True, text=True)
    names = {parts[1] for line in enc.stdout.splitlines()
             if len(parts := line.split()) >= 2}
    missing = [e for e in REQUIRED_VIDEO_ENCODERS + REQUIRED_AUDIO_ENCODERS
               if e not in names]
    if missing:
        raise SystemExit(f"{exe}: missing encoders required by presets: {missing}")
    return f"{first} - all {len(REQUIRED_VIDEO_ENCODERS) + len(REQUIRED_AUDIO_ENCODERS)} required encoders present"
