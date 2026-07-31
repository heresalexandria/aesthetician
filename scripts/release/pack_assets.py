#!/usr/bin/env python3
"""Bundle the generated asset packs so CI can build a real release.

    python3 scripts/release/pack_assets.py

`assets/` is gitignored on purpose - it is a couple of hundred megabytes of
generated media, and the overlay plates cost money to regenerate. A clean CI
runner therefore has none of it, and a build made there falls back to procedural
overlays with placeholder preset thumbnails: a visibly different product.

So the packs are published once, as a plain tarball attached to a GitHub release
that exists only to hold them, and the release workflow pulls that down before
it builds. Run this, then attach `dist/aesthetician-assets.tar.gz` to a release
tagged `assets-v1` (the tag the workflow looks for; override it with the
`ASSETS_RELEASE_TAG` repository variable). Re-run and bump the tag whenever the
plates change - docs/releases.md walks through it.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import tarfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = REPO_ROOT / "assets"
SUBDIRS = ("packs", "thumbs", "audio-beds")
DEFAULT_OUT = REPO_ROOT / "dist" / "aesthetician-assets.tar.gz"


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} GB"


def size_of(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    present = [s for s in SUBDIRS if (ASSETS_DIR / s).is_dir() and any((ASSETS_DIR / s).iterdir())]
    missing = [s for s in SUBDIRS if s not in present]
    if not present:
        print(f"error: nothing to pack - {ASSETS_DIR} has no packs/thumbs/audio-beds.\n"
              "Generate them first (see docs/packaging.md), then re-run.", file=sys.stderr)
        return 1
    for s in missing:
        print(f"warning: assets/{s} is empty and will not be in the bundle", file=sys.stderr)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Paths are stored relative to assets/, so CI untars straight into assets/.
    with tarfile.open(args.output, "w:gz") as tar:
        for sub in present:
            src = ASSETS_DIR / sub
            print(f"  packing assets/{sub} ({human(size_of(src))})", file=sys.stderr)
            tar.add(src, arcname=sub)

    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(f"\n{args.output.relative_to(REPO_ROOT)}  {human(args.output.stat().st_size)}",
          file=sys.stderr)
    print(f"sha256  {digest}", file=sys.stderr)
    print("\nAttach that file to a release tagged `assets-v1` (see docs/releases.md).",
          file=sys.stderr)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
