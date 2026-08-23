#!/usr/bin/env python3
"""Turn the merged pull request into release notes.

    python3 scripts/release/release_notes.py \
        --pr pr.json --comments comments.json \
        --version 0.6.0 --previous v0.5.0 --repo owner/name > notes.md

The PR description is the body of the notes, so writing a good PR is the whole
job. On top of that this collects any screenshots attached to the PR - in the
description or in its comments - and lists them under their own heading, then
appends the download table and the compare link.

`--pr` and `--comments` take GitHub API JSON. Both are optional: with neither,
you get a bare set of notes rather than an error, because a release that cannot
describe itself still beats a release that does not happen.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# GitHub serves PR attachments from a handful of hosts. Anything else in the
# body is left alone: this only promotes URLs we are confident render as images.
IMAGE_HOSTS = (
    "github.com/user-attachments/assets/",
    "user-images.githubusercontent.com/",
    "raw.githubusercontent.com/",
    "github.com/user-attachments/files/",
)
IMAGE_EXT = re.compile(r"\.(?:png|jpe?g|gif|webp|svg)(?:\?|$)", re.I)

MD_IMAGE = re.compile(r"!\[[^\]]*\]\(\s*(<?https://[^\s)>]+)>?[^)]*\)")
HTML_IMAGE = re.compile(r"""<img\b[^>]*\bsrc\s*=\s*["'](https://[^"']+)["']""", re.I)
BARE_URL = re.compile(r"(?<![(\"'=\]])\bhttps://\S+", re.I)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)


def looks_like_image(url: str) -> bool:
    return any(h in url for h in IMAGE_HOSTS) or bool(IMAGE_EXT.search(url))


def clean_body(body: str) -> str:
    """Drop PR-template comments and normalise whitespace."""
    text = HTML_COMMENT.sub("", body or "")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def collect_images(texts: list[str]) -> tuple[list[str], set[str]]:
    """Every image URL across `texts`, in order, plus the ones already inline.

    Images the description already renders are not repeated under Screenshots;
    the point is to surface the ones that would otherwise be lost, mostly
    attachments pasted into review comments.
    """
    found: list[str] = []
    inline: set[str] = set()
    seen: set[str] = set()

    def add(url: str, is_inline: bool) -> None:
        url = url.strip().strip("<>")
        if not url.startswith("https://") or not looks_like_image(url):
            return
        if is_inline:
            inline.add(url)
        if url not in seen:
            seen.add(url)
            found.append(url)

    for i, text in enumerate(texts):
        if not text:
            continue
        for m in MD_IMAGE.finditer(text):
            add(m.group(1), is_inline=(i == 0))
        for m in HTML_IMAGE.finditer(text):
            add(m.group(1), is_inline=(i == 0))
        # A pasted attachment URL on its own line renders as an image on GitHub
        # but is plain text anywhere else, so it gets wrapped explicitly.
        stripped = MD_IMAGE.sub("", HTML_IMAGE.sub("", text))
        for m in BARE_URL.finditer(stripped):
            add(m.group(0).rstrip(".,;:)"), is_inline=False)

    return found, inline


PLATFORMS = [
    ("-mac-arm64.dmg", "macOS, Apple silicon"),
    ("-mac-x64.dmg", "macOS, Intel"),
    ("-win-x64-setup.exe", "Windows 10/11, 64-bit"),
]


def human_size(n: int) -> str:
    mb = n / (1024 * 1024)
    return f"{mb / 1024:.2f} GB" if mb >= 1024 else f"{mb:.0f} MB"


def download_table(version: str, files: list[Path]) -> str:
    """Only list what actually built.

    Publication requires every target, but this helper is also useful for local
    dry runs. A table promising a file that is not present is worse than a table
    that is one row short.
    """
    rows = []
    by_name = {f.name: f for f in files}
    for suffix, label in PLATFORMS:
        match = next((n for n in by_name if n.endswith(suffix)), None)
        if match:
            rows.append(f"| {label} | `{match}` | {human_size(by_name[match].stat().st_size)} |")

    if not rows:
        # No file list given (a local dry run): fall back to the usual names.
        rows = [f"| {label} | `Aesthetician-{version}{suffix}` | |"
                for suffix, label in PLATFORMS]

    missing = [label for suffix, label in PLATFORMS
               if files and not any(n.endswith(suffix) for n in by_name)]

    out = [
        "## Download",
        "",
        "| platform | file | size |",
        "|---|---|---|",
        *rows,
        "",
    ]
    if missing:
        out += [f"No build for {', '.join(missing)} in this release.", ""]
    out += [
        "Already running Aesthetician? Click the version chip in the title bar and",
        "**Check for updates** - it installs this release in place. The `.zip` files are",
        "what that updater downloads; you do not need them by hand.",
        "",
        "These builds are not signed with a Developer ID. On first launch macOS needs a",
        "right-click (or Control-click) on the app then **Open**; Windows shows a",
        "SmartScreen warning behind **More info**. Updates installed from inside the app",
        "skip both, because the app is not downloading them through a browser.",
        "",
        "`SHA256SUMS.txt` lists the digest of every file here, and the in-app updater",
        "checks its download against it.",
    ]
    return "\n".join(out)


def build(pr: dict, comments: list[dict], version: str, previous: str, repo: str,
          files: list[Path] | None = None) -> str:
    parts: list[str] = []

    body = clean_body(pr.get("body", ""))
    title = (pr.get("title") or "").strip()
    if body:
        parts.append(body)
    elif title:
        parts.append(title)

    images, inline = collect_images([pr.get("body", "")] + [c.get("body", "") for c in comments])
    extra = [u for u in images if u not in inline]
    if extra:
        parts.append("## Screenshots\n\n" + "\n\n".join(
            f'<img src="{u}" alt="" width="900">' for u in extra))

    parts.append(download_table(version, files or []))

    footer = []
    number = pr.get("number")
    author = (pr.get("user") or {}).get("login")
    if number and repo:
        credit = f"Released from [#{number}](https://github.com/{repo}/pull/{number})"
        if author:
            credit += f" by @{author}"
        footer.append(credit + ".")
    if previous and repo:
        footer.append(
            f"[Full changelog](https://github.com/{repo}/compare/{previous}...v{version})")
    if footer:
        parts.append("---\n\n" + "  \n".join(footer))

    return "\n\n".join(parts).strip() + "\n"


def load(path: str | None, default):
    if not path:
        return default
    p = Path(path)
    if not p.exists() or not p.stat().st_size:
        return default
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError as err:
        print(f"warning: ignoring {path}: {err}", file=sys.stderr)
        return default


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pr", help="JSON for the merged pull request")
    ap.add_argument("--comments", help="JSON array of that PR's comments")
    ap.add_argument("--version", required=True, help="version being released, without the v")
    ap.add_argument("--previous", default="", help="previous tag, for the compare link")
    ap.add_argument("--repo", default="heresalexandria/aesthetician")
    ap.add_argument("--files", type=Path,
                    help="directory of the built artifacts, so the table lists what exists")
    ap.add_argument("-o", "--output", help="write here instead of stdout")
    args = ap.parse_args(argv)

    pr = load(args.pr, {})
    comments = load(args.comments, [])
    if not isinstance(comments, list):
        comments = []
    files = sorted(p for p in args.files.iterdir() if p.is_file()) \
        if args.files and args.files.is_dir() else []

    notes = build(pr, comments, args.version, args.previous, args.repo, files)
    if args.output:
        Path(args.output).write_text(notes, encoding="utf-8")
    else:
        sys.stdout.write(notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
