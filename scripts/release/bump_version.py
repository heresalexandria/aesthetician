#!/usr/bin/env python3
"""Bump the project version everywhere it is written down.

    python3 scripts/release/bump_version.py patch
    python3 scripts/release/bump_version.py --show
    python3 scripts/release/bump_version.py minor --dry-run

The version lives in four files and they have to agree: `pyproject.toml` is what
pip sees, `aesthetician/__init__.py` is what the engine reports, and
`app/package.json` is what `app.getVersion()` returns - which is the number the
in-app updater compares against the latest GitHub release. `app/package-lock.json`
tags along so npm does not complain.

Prints the new version to stdout, and appends `version=`/`tag=` to $GITHUB_OUTPUT
when running in Actions.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PYPROJECT = REPO_ROOT / "pyproject.toml"
INIT_PY = REPO_ROOT / "aesthetician" / "__init__.py"
PACKAGE_JSON = REPO_ROOT / "app" / "package.json"
PACKAGE_LOCK = REPO_ROOT / "app" / "package-lock.json"

BUMPS = ("major", "minor", "patch")


def read_current() -> str:
    m = re.search(r'^version\s*=\s*"([^"]+)"', PYPROJECT.read_text(), re.M)
    if not m:
        raise SystemExit(f"no version found in {PYPROJECT}")
    return m.group(1)


def parse(version: str) -> tuple[int, int, int]:
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version.strip())
    if not m:
        raise SystemExit(f"not a MAJOR.MINOR.PATCH version: {version!r}")
    return int(m[1]), int(m[2]), int(m[3])


def bump(version: str, kind: str) -> str:
    major, minor, patch = parse(version)
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def _sub_once(path: Path, pattern: str, replacement: str) -> None:
    text = path.read_text()
    new, n = re.subn(pattern, replacement, text, count=1, flags=re.M)
    if n != 1:
        raise SystemExit(f"could not rewrite the version in {path} (matched {n} times)")
    path.write_text(new)


INTRODUCED_PY = REPO_ROOT / "aesthetician" / "presets" / "_introduced.py"


def stamp_introduced(version: str, path: Path = INTRODUCED_PY) -> int:
    """Presets that entered the library since the last release now have one.

    scripts/gen_introduced.py writes "unreleased" for a preset no release tag
    contains yet; the tag is being created right now, so this is the version
    those presets first ship in. Returns how many entries were stamped.
    """
    if not path.exists():
        return 0
    text = path.read_text()
    new, n = re.subn(r'"unreleased"\)', f'"{version}")', text)
    if n:
        path.write_text(new)
    return n


def write(version: str) -> list[str]:
    """Set `version` in every file that carries it. Returns what changed."""
    touched: list[str] = []

    _sub_once(PYPROJECT, r'^version\s*=\s*"[^"]+"', f'version = "{version}"')
    touched.append(str(PYPROJECT.relative_to(REPO_ROOT)))

    _sub_once(INIT_PY, r'^__version__\s*=\s*"[^"]+"', f'__version__ = "{version}"')
    touched.append(str(INIT_PY.relative_to(REPO_ROOT)))

    # Rewritten as text rather than json.dump: the file is hand-maintained and
    # a reformat would bury the one-line change in noise.
    _sub_once(PACKAGE_JSON, r'^(\s*)"version":\s*"[^"]+"', rf'\g<1>"version": "{version}"')
    touched.append(str(PACKAGE_JSON.relative_to(REPO_ROOT)))

    if PACKAGE_LOCK.exists():
        lock = json.loads(PACKAGE_LOCK.read_text())
        lock["version"] = version
        if "" in lock.get("packages", {}):
            lock["packages"][""]["version"] = version
        PACKAGE_LOCK.write_text(json.dumps(lock, indent=2) + "\n")
        touched.append(str(PACKAGE_LOCK.relative_to(REPO_ROOT)))

    if stamp_introduced(version):
        touched.append(str(INTRODUCED_PY.relative_to(REPO_ROOT)))

    return touched


def check() -> str:
    """Confirm every file agrees, and return the version they agree on."""
    current = read_current()
    init = re.search(r'^__version__\s*=\s*"([^"]+)"', INIT_PY.read_text(), re.M)
    pkg = json.loads(PACKAGE_JSON.read_text())
    problems = []
    if not init or init.group(1) != current:
        problems.append(f"{INIT_PY.name} says {init.group(1) if init else '?'}")
    if pkg.get("version") != current:
        problems.append(f"app/package.json says {pkg.get('version')}")
    if problems:
        raise SystemExit(f"version mismatch (pyproject says {current}): " + "; ".join(problems))
    return current


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", nargs="?", choices=BUMPS, help="which part to increment")
    ap.add_argument("--show", action="store_true", help="print the current version and exit")
    ap.add_argument("--check", action="store_true",
                    help="verify every file agrees on the version, then exit")
    ap.add_argument("--set", dest="exact", help="write this exact version instead of bumping")
    ap.add_argument("--dry-run", action="store_true", help="print the new version, change nothing")
    args = ap.parse_args(argv)

    if args.show:
        print(read_current())
        return 0
    if args.check:
        print(check())
        return 0

    if args.exact:
        new = str(parse(args.exact) and args.exact.strip())
    elif args.kind:
        new = bump(check(), args.kind)
    else:
        ap.error("give a bump kind, --set, --show or --check")

    if not args.dry_run:
        for path in write(new):
            print(f"  {path}", file=sys.stderr)

    print(new)
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"version={new}\ntag=v{new}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
