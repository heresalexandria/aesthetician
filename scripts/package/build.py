#!/usr/bin/env python3
"""End-to-end desktop packaging for Aesthetician.

    python3 scripts/package/build.py --target mac
    python3 scripts/package/build.py --target win

Builds a relocatable Python runtime, fetches static ffmpeg/ffprobe, stages the
asset packs, then runs electron-builder. Downloads and built runtimes are cached
under `.cache/package/`, so a second run is fast; `--clean` throws it all away.

Layout produced under `app/build-resources/` (electron-builder copies it into
`<app>/Contents/Resources`, which is what app/main.js resolves against):

    pyruntime/          relocatable CPython + aesthetician + deps
    bin/                ffmpeg, ffprobe
    assets/             packs/, thumbs/, audio-beds/
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

if __package__ in (None, ""):  # allow `python3 scripts/package/build.py`
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "scripts.package"

from .common import (  # noqa: E402
    APP_DIR,
    ASSETS_DIR,
    CACHE_DIR,
    REPO_ROOT,
    STAGE_DIR,
    human,
    log,
    rmtree,
    run,
    size_of,
)
from . import build_runtime, fetch_ffmpeg  # noqa: E402
from .targets import ALIASES, TARGETS, Target, host_target  # noqa: E402

ASSET_SUBDIRS = ("packs", "thumbs", "audio-beds")


# ── staging ──────────────────────────────────────────────────────────────
def _mirror(src: Path, dst: Path, *, hardlink: bool = False) -> None:
    """Mirror src/ -> dst/ (deleting extras). Hardlinks avoid duplicating media."""
    dst.mkdir(parents=True, exist_ok=True)
    cmd = ["rsync", "-a", "--delete"]
    if hardlink:
        cmd.append(f"--link-dest={src.resolve()}")
    cmd += [f"{src.resolve()}/", f"{dst}/"]
    run(cmd, quiet=True)


def stage(target: Target, runtime: Path, ffmpeg_dir: Path, with_assets: bool) -> dict:
    """Populate app/build-resources/ for exactly one target."""
    log(f"stage   {target.key} -> {STAGE_DIR.relative_to(REPO_ROOT)}")
    STAGE_DIR.mkdir(parents=True, exist_ok=True)

    _mirror(runtime, STAGE_DIR / "pyruntime")
    _mirror(ffmpeg_dir, STAGE_DIR / "bin")

    included: list[str] = []
    assets_dst = STAGE_DIR / "assets"
    rmtree(assets_dst)
    assets_dst.mkdir(parents=True, exist_ok=True)
    if with_assets:
        for sub in ASSET_SUBDIRS:
            src = ASSETS_DIR / sub
            # Asset packs are gitignored media; a fresh clone may not have them.
            # The engine has procedural fallbacks, so missing packs are not fatal.
            if src.is_dir() and any(src.iterdir()):
                _mirror(src, assets_dst / sub, hardlink=True)
                included.append(f"{sub} ({human(size_of(src))})")
            else:
                (assets_dst / sub).mkdir(parents=True, exist_ok=True)
                log(f"        assets/{sub} missing - bundling empty dir")
    else:
        for sub in ASSET_SUBDIRS:
            (assets_dst / sub).mkdir(parents=True, exist_ok=True)
        log("        --no-assets: bundling empty asset dirs")

    (STAGE_DIR / "STAGED.json").write_text(json.dumps({
        "target": target.key,
        "assets": included,
        "pyruntime_bytes": size_of(STAGE_DIR / "pyruntime"),
        "bin_bytes": size_of(STAGE_DIR / "bin"),
        "assets_bytes": size_of(assets_dst),
    }, indent=2))
    return {"assets_included": included}


# ── electron-builder ─────────────────────────────────────────────────────
def ensure_node_modules() -> None:
    if not (APP_DIR / "node_modules" / ".bin" / "electron-builder").exists():
        log("npm install (electron + electron-builder)")
        run(["npm", "install"], cwd=APP_DIR)


def run_electron_builder(target: Target, *, dir_only: bool) -> None:
    eb = APP_DIR / "node_modules" / ".bin" / "electron-builder"
    cmd = [eb, target.eb_flag, target.eb_arch, "--publish", "never"]
    if dir_only:
        cmd.append("--dir")
    env = dict(os.environ)
    # Nothing here is ever published or notarized; keep electron-builder quiet
    # about credentials it will not find.
    env.setdefault("CSC_IDENTITY_AUTO_DISCOVERY", "false")
    run(cmd, cwd=APP_DIR, env=env)


def artifacts() -> list[tuple[Path, int]]:
    dist = APP_DIR / "dist"
    out: list[tuple[Path, int]] = []
    if not dist.is_dir():
        return out
    for p in sorted(dist.iterdir()):
        if p.is_file() and p.suffix in (".dmg", ".zip", ".exe", ".blockmap"):
            out.append((p, p.stat().st_size))
        elif p.is_dir():
            for app in p.glob("*.app"):
                out.append((app, size_of(app)))
    return out


# ── main ─────────────────────────────────────────────────────────────────
def build_one(key: str, args) -> dict:
    target = TARGETS[key]
    log(f"══ {target.key} ══")
    runtime = build_runtime.build(
        target, force=args.force_runtime, bytecode=not args.no_bytecode
    )
    ffmpeg_dir = fetch_ffmpeg.fetch(target, force=args.force_ffmpeg)
    ff_note = fetch_ffmpeg.verify(target, ffmpeg_dir)
    log(f"ffmpeg  {ff_note}")
    engine_note = build_runtime.verify(target, runtime, ffmpeg_dir, ASSETS_DIR)
    log(f"engine  {engine_note}")

    info = stage(target, runtime, ffmpeg_dir, with_assets=not args.no_assets)
    info.update(target=target.key, ffmpeg=ff_note, engine=engine_note,
                runtime_bytes=size_of(runtime))
    if args.stage_only:
        log("--stage-only: skipping electron-builder")
        return info
    ensure_node_modules()
    run_electron_builder(target, dir_only=args.dir_only)
    return info


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", default="mac" if sys.platform == "darwin" else "win",
                    choices=sorted(ALIASES),
                    help="mac (host arch), mac-arm64, mac-x64, mac-both, win")
    ap.add_argument("--clean", action="store_true",
                    help="delete the download/runtime cache, staging dir and app/dist first")
    ap.add_argument("--no-assets", action="store_true",
                    help="bundle empty asset dirs (much smaller; plates fall back to procedural)")
    ap.add_argument("--no-bytecode", action="store_true",
                    help="strip __pycache__ from the runtime (smaller, slower cold start)")
    ap.add_argument("--force-runtime", action="store_true", help="rebuild the Python runtime")
    ap.add_argument("--force-ffmpeg", action="store_true", help="re-fetch ffmpeg")
    ap.add_argument("--stage-only", action="store_true",
                    help="prepare app/build-resources/ but do not run electron-builder")
    ap.add_argument("--dir-only", action="store_true",
                    help="electron-builder --dir (unpacked .app, no DMG/installer)")
    args = ap.parse_args(argv)

    if args.clean:
        log("clean   caches, staging and dist")
        for p in (CACHE_DIR, STAGE_DIR, APP_DIR / "dist"):
            rmtree(p)

    keys = ALIASES[args.target]
    if args.target == "mac":
        host = host_target()
        keys = (host,) if host.startswith("mac") else ("mac-arm64",)

    if not shutil.which("rsync"):
        raise SystemExit("rsync is required for staging")

    results = [build_one(k, args) for k in keys]

    log("── summary ──")
    for r in results:
        log(f"{r['target']}: runtime {human(r['runtime_bytes'])}; {r['engine']}")
        log(f"  assets: {', '.join(r['assets_included']) or 'none'}")
        log(f"  ffmpeg: {r['ffmpeg']}")
    for path, n in artifacts():
        log(f"artifact {human(n):>9}  {path.relative_to(REPO_ROOT)}")
    log(f"cache    {human(size_of(CACHE_DIR))} in {CACHE_DIR.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
