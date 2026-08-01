"""Shared plumbing for the desktop packaging scripts: paths, logging, download cache."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = REPO_ROOT / "app"
ASSETS_DIR = REPO_ROOT / "assets"

# Downloads and built runtimes are cached here so repeat builds are cheap.
CACHE_DIR = REPO_ROOT / ".cache" / "package"
DOWNLOAD_DIR = CACHE_DIR / "downloads"
RUNTIME_CACHE = CACHE_DIR / "pyruntime"
FFMPEG_CACHE = CACHE_DIR / "ffmpeg"

# What electron-builder copies into Contents/Resources (see app/package.json).
STAGE_DIR = APP_DIR / "build-resources"

_T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - _T0:6.1f}s] {msg}", flush=True)


def die(msg: str) -> "None":
    print(f"error: {msg}", file=sys.stderr, flush=True)
    raise SystemExit(1)


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n / 1.0:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} GB"


def size_of(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            p = Path(root) / f
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total


def run(cmd, cwd: Path | None = None, env: dict | None = None, check: bool = True,
        capture: bool = False, quiet: bool = False):
    if not quiet:
        log("$ " + " ".join(str(c) for c in cmd))
    return subprocess.run(
        [str(c) for c in cmd],
        cwd=str(cwd) if cwd else None,
        env=env,
        check=check,
        capture_output=capture,
        text=capture,
    )


def rmtree(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.exists():
        shutil.rmtree(path)


def download(url: str, dest_name: str | None = None, *, force: bool = False) -> Path:
    """Fetch `url` into the download cache and return the local path."""
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    name = dest_name or (url.rsplit("/", 1)[-1] or hashlib.sha1(url.encode()).hexdigest())
    dest = DOWNLOAD_DIR / name
    if dest.exists() and dest.stat().st_size > 0 and not force:
        log(f"cached  {name} ({human(dest.stat().st_size)})")
        return dest
    log(f"fetch   {url}")
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "aesthetician-packager"})
    with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        got = 0
        last = 0.0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            now = time.time()
            if now - last > 2.0:
                last = now
                pct = f" {100 * got / total:.0f}%" if total else ""
                log(f"        …{human(got)}{pct}")
    tmp.replace(dest)
    log(f"got     {name} ({human(dest.stat().st_size)})")
    return dest


def extract(archive: Path, dest: Path) -> None:
    """Extract a .tar.gz / .tar.xz / .zip into `dest` (created fresh)."""
    rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    name = archive.name.lower()
    log(f"extract {archive.name} -> {dest}")
    if name.endswith(".zip"):
        with zipfile.ZipFile(archive) as z:
            z.extractall(dest)
            # zipfile drops the executable bit; restore it from the archive mode.
            for info in z.infolist():
                mode = info.external_attr >> 16
                if mode & 0o111:
                    p = dest / info.filename
                    if p.is_file():
                        p.chmod(p.stat().st_mode | 0o755)
    else:
        with tarfile.open(archive) as t:
            # filter="data" (3.12+) refuses absolute/parent paths.
            t.extractall(dest, filter="data")


def mirror(src: Path, dst: Path, *, hardlink: bool = False) -> None:
    """Mirror src/ into dst/, deleting extras.

    rsync when it is there (fast, and a near no-op on a repeat build), a plain
    Python copy when it is not - which is every Windows runner, where the whole
    packaging flow would otherwise stop at the staging step. `hardlink` asks for
    hardlinks instead of copies so the asset packs are not duplicated on disk;
    it is an optimisation, and falling back to a real copy is always correct.
    """
    dst.mkdir(parents=True, exist_ok=True)
    if shutil.which("rsync"):
        cmd = ["rsync", "-a", "--delete"]
        if hardlink:
            cmd.append(f"--link-dest={src.resolve()}")
        cmd += [f"{src.resolve()}/", f"{dst}/"]
        run(cmd, quiet=True)
        return

    keep: set[Path] = set()
    for root, _dirs, files in os.walk(src):
        rel = Path(root).relative_to(src)
        (dst / rel).mkdir(parents=True, exist_ok=True)
        keep.add(dst / rel)
        for name in files:
            s = Path(root) / name
            d = dst / rel / name
            keep.add(d)
            if d.exists() or d.is_symlink():
                d.unlink()
            if s.is_symlink():
                os.symlink(os.readlink(s), d)
                continue
            if hardlink:
                try:
                    os.link(s, d)
                    continue
                except OSError:
                    pass          # across devices, or a filesystem without links
            shutil.copy2(s, d)

    # --delete, by hand: anything in dst that is no longer in src.
    for root, dirs, files in os.walk(dst, topdown=False):
        for name in files:
            p = Path(root) / name
            if p not in keep:
                p.unlink(missing_ok=True)
        for name in dirs:
            p = Path(root) / name
            if p not in keep and not any(p.iterdir()):
                p.rmdir()


def rsync(src: Path, dst: Path) -> None:
    """Back-compat alias for `mirror`."""
    mirror(src, dst)


def which(prog: str) -> str | None:
    return shutil.which(prog)
