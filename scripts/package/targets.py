"""Pinned upstream versions and per-target layout facts.

Bump the pins here (and only here) to update the bundled Python or ffmpeg;
`docs/packaging.md` explains how to verify a bump.
"""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass, field

# ── pinned Python runtime ────────────────────────────────────────────────
# astral-sh/python-build-standalone "install_only" archives: a genuinely
# relocatable CPython (no absolute paths baked in, unlike a venv).
PY_VERSION = "3.12.13"
PY_XY = "3.12"
PBS_RELEASE = "20260728"
PBS_URL = (
    "https://github.com/astral-sh/python-build-standalone/releases/download/"
    "{rel}/cpython-{ver}%2B{rel}-{triple}-install_only.tar.gz"
)

# ── pinned ffmpeg ────────────────────────────────────────────────────────
# macOS: martin-riedl.de static builds (GPLv3: --enable-gpl --enable-version3,
#        no --enable-nonfree, so redistribution is possible under the GPL).
# Windows: BtbN/FFmpeg-Builds "win64-gpl" static build (GPLv3 likewise).
FFMPEG_MAC_URL = "https://ffmpeg.martin-riedl.de/redirect/latest/macos/{arch}/release/{tool}.zip"
FFMPEG_WIN_TAG = "n8.1"
FFMPEG_WIN_URL = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-{tag}-latest-win64-gpl-8.1.zip"
)

# Runtime dependencies installed into the bundled interpreter. Kept in sync with
# pyproject.toml [project.dependencies]; the project itself is installed too.
DEPS = ("numpy", "scipy", "opencv-python-headless", "click", "rich", "requests")


@dataclass(frozen=True)
class Target:
    key: str
    pbs_triple: str
    python_rel: str          # interpreter path relative to the runtime root
    site_rel: str            # site-packages relative to the runtime root
    exe_suffix: str
    eb_flag: str             # electron-builder platform flag
    eb_arch: str             # electron-builder --<arch> flag
    pip_platforms: tuple[str, ...] = field(default=())   # for cross installs


TARGETS: dict[str, Target] = {
    "mac-arm64": Target(
        key="mac-arm64",
        pbs_triple="aarch64-apple-darwin",
        python_rel="bin/python3",
        site_rel=f"lib/python{PY_XY}/site-packages",
        exe_suffix="",
        eb_flag="--mac",
        eb_arch="--arm64",
        pip_platforms=(
            "macosx_11_0_arm64",
            "macosx_12_0_arm64",
            "macosx_13_0_arm64",
            "macosx_14_0_arm64",
        ),
    ),
    "mac-x64": Target(
        key="mac-x64",
        pbs_triple="x86_64-apple-darwin",
        python_rel="bin/python3",
        site_rel=f"lib/python{PY_XY}/site-packages",
        exe_suffix="",
        eb_flag="--mac",
        eb_arch="--x64",
        pip_platforms=(
            "macosx_10_9_x86_64",
            "macosx_10_13_x86_64",
            "macosx_10_15_x86_64",
            "macosx_11_0_x86_64",
            "macosx_12_0_x86_64",
            "macosx_13_0_x86_64",
            "macosx_14_0_x86_64",
        ),
    ),
    "win-x64": Target(
        key="win-x64",
        pbs_triple="x86_64-pc-windows-msvc",
        python_rel="python.exe",
        site_rel="Lib/site-packages",
        exe_suffix=".exe",
        eb_flag="--win",
        eb_arch="--x64",
        pip_platforms=("win_amd64",),
    ),
}

# `--target mac` / `--target win` expand to these.
ALIASES: dict[str, tuple[str, ...]] = {
    "mac": ("mac-arm64",),
    "mac-both": ("mac-arm64", "mac-x64"),
    "mac-arm64": ("mac-arm64",),
    "mac-x64": ("mac-x64",),
    "win": ("win-x64",),
    "win-x64": ("win-x64",),
}


def host_target() -> str:
    if sys.platform == "darwin":
        return "mac-arm64" if platform.machine() == "arm64" else "mac-x64"
    if sys.platform.startswith("win"):
        return "win-x64"
    return ""


def is_native(target: Target) -> bool:
    """True when the host can execute this target's interpreter directly."""
    return target.key == host_target()
