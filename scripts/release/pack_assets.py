#!/usr/bin/env python3
"""Bundle the generated asset packs so CI can build a real release.

    python3 scripts/release/pack_assets.py

`assets/` is gitignored on purpose - it is a couple of hundred megabytes of
generated media, and the overlay plates cost money to regenerate. A clean CI
runner therefore has none of it. Release builds require this bundle so they
cannot silently ship procedural overlays and placeholder preset thumbnails.

So the packs are published once, as a plain tarball attached to a GitHub release
that exists only to hold them, and the release workflow pulls that down before
it builds. Run this, then attach `dist/aesthetician-assets.tar.gz` to a release
with a new `assets-vN` tag. Pin its tag and printed SHA-256 in
`scripts/release/asset_bundle.json`. Re-run whenever presets or their thumbnails
change - docs/releases.md walks through it.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tarfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = REPO_ROOT / "assets"
sys.path.insert(0, str(REPO_ROOT))
from scripts.release.asset_bundle import verify_assets
SUBDIRS = ("packs", "thumbs", "audio-beds")
DEFAULT_OUT = REPO_ROOT / "dist" / "aesthetician-assets.tar.gz"


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} GB"


def size_of(path: Path) -> int:
    return sum((Path(root) / f).stat().st_size
               for root, _, files in os.walk(path, followlinks=True) for f in files)


def portable_member(item: tarfile.TarInfo) -> tarfile.TarInfo | None:
    if Path(item.name).name == '.DS_Store':
        return None
    item.uid = item.gid = 0
    item.uname = item.gname = ''
    return item


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    verify_assets(ASSETS_DIR)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Paths are stored relative to assets/, so CI untars straight into assets/.
    # Worktrees may link to shared generated assets. Ship their bytes, never
    # machine-specific symlinks that break on a clean macOS/Windows runner.
    with tarfile.open(args.output, "w:gz", dereference=True) as tar:
        for sub in SUBDIRS:
            src = ASSETS_DIR / sub
            print(f"  packing assets/{sub} ({human(size_of(src))})", file=sys.stderr)
            tar.add(src, arcname=sub, filter=portable_member)

    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(f"\n{args.output}  {human(args.output.stat().st_size)}",
          file=sys.stderr)
    print(f"sha256  {digest}", file=sys.stderr)
    print("\nPublish on a new asset release and update scripts/release/asset_bundle.json (see docs/releases.md).",
          file=sys.stderr)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
