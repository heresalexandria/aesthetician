#!/usr/bin/env python3
"""Read a pull request's labels and decide how the version moves.

    LABELS='["minor","docs"]' python3 scripts/release/select_bump.py
    minor

Exactly one of `major`, `minor` or `patch` has to be on the PR, or `no-release`
to merge without cutting anything. Anything else is an error, because the
alternative is guessing - and a wrong guess here ships a version number that can
never be taken back.

Prints the decision (`major`/`minor`/`patch`/`none`) on stdout and appends
`bump=` to $GITHUB_OUTPUT. Used by the PR gate and by the release workflow, so
the rule is written down once.
"""

from __future__ import annotations

import json
import os
import sys

RELEASE_LABELS = ("major", "minor", "patch")
SKIP_LABEL = "no-release"

HELP = (
    f"Label the pull request with exactly one of {', '.join(RELEASE_LABELS)} to say how the "
    f"version should move, or {SKIP_LABEL} to merge without cutting a release."
)


def parse_labels(raw: str) -> list[str]:
    """Accept the JSON array Actions hands us, or a plain comma/newline list."""
    raw = (raw or "").strip()
    if not raw:
        return []
    if raw.startswith("["):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = []
        out = []
        for item in data if isinstance(data, list) else []:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict) and isinstance(item.get("name"), str):
                out.append(item["name"])   # the raw labels array, unfiltered
        return out
    return [p.strip() for p in raw.replace("\n", ",").split(",") if p.strip()]


def select(labels: list[str]) -> str:
    names = {label.strip().lower() for label in labels}
    hits = [label for label in RELEASE_LABELS if label in names]
    if SKIP_LABEL in names:
        if hits:
            raise SystemExit(
                f"error: {SKIP_LABEL} cannot be combined with {', '.join(hits)}.\n{HELP}")
        return "none"
    if not hits:
        raise SystemExit(f"error: no release label found.\n{HELP}")
    if len(hits) > 1:
        raise SystemExit(f"error: {', '.join(hits)} are all set - pick one.\n{HELP}")
    return hits[0]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    raw = argv[0] if argv else os.environ.get("LABELS", "")
    bump = select(parse_labels(raw))
    print(bump)
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"bump={bump}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
