#!/usr/bin/env python
"""Distinctness audit: how close every preset is to its nearest neighbour.

Two presets are close when they run the same effects with nearly the same
numbers. This scores every pair on (a) the overlap of their effect sequences
and (b) the mean normalized distance of the parameters they share, then
reports each preset's nearest neighbour and flags pairs that are near-clones:
the same effect list, and parameters that differ by under the threshold.

Run:  .venv/bin/python scripts/audit_similarity.py            # whole library
      .venv/bin/python scripts/audit_similarity.py --only-new  # presets not on main
      .venv/bin/python scripts/audit_similarity.py --threshold 0.06 --top 3
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from aesthetician.engine.graph import all_effects, get_effect  # noqa: E402
from aesthetician.engine.presets import all_presets  # noqa: E402


def _param_meta():
    meta = {}
    for eid, cls in all_effects().items():
        for p in cls.PARAMS:
            meta[(eid, p.name)] = p
    return meta


META = _param_meta()


def signature(preset):
    """(effect sequence, {effect#n.param: effective value}) over video + audio."""
    seq = []
    vals = {}
    for which in ("video", "audio"):
        counts: dict[str, int] = {}
        for eid, params in getattr(preset, which):
            counts[eid] = counts.get(eid, 0) + 1
            key = eid if counts[eid] == 1 else f"{eid}#{counts[eid]}"
            seq.append(key)
            cls = get_effect(eid)
            for p in cls.PARAMS:
                vals[f"{key}.{p.name}"] = (eid, p.name, params.get(p.name, p.default), p.name in params)
    return tuple(seq), vals


def param_distance(a, b) -> float:
    """Mean normalized distance over the shared parameters either preset authored.

    Untouched defaults are ignored: two chains that both leave a knob alone
    have not said anything about it, and counting those agreements would make
    every pair look alike.
    """
    shared = [k for k in set(a) & set(b) if a[k][3] or b[k][3]]
    if not shared:
        return 1.0
    total = 0.0
    counted = 0
    for k in shared:
        eid, pname, va, _ = a[k]
        _, _, vb, _ = b[k]
        prm = META.get((eid, pname))
        if prm is None:
            continue
        counted += 1
        if prm.kind in ("float", "int"):
            span = float(prm.hi - prm.lo) or 1.0
            total += min(1.0, abs(float(va) - float(vb)) / span)
        else:
            total += 0.0 if va == vb else 1.0
    return total / counted if counted else 1.0


def similarity(sa, sb) -> tuple[float, float, float]:
    seq_a, vals_a = sa
    seq_b, vals_b = sb
    set_a, set_b = set(seq_a), set(seq_b)
    jaccard = len(set_a & set_b) / len(set_a | set_b) if (set_a | set_b) else 1.0
    pdist = param_distance(vals_a, vals_b)
    return 0.5 * jaccard + 0.5 * (1.0 - pdist), jaccard, pdist


def new_ids() -> set[str]:
    """Preset ids declared in modules main does not have: changed tracked files plus untracked ones."""
    paths: set[str] = set()
    for cmd in (["git", "diff", "--name-only", "main", "--", "aesthetician/presets"],
                ["git", "ls-files", "--others", "--exclude-standard", "aesthetician/presets"]):
        try:
            out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True).stdout
        except Exception:
            continue
        paths.update(out.split())
    ids: set[str] = set()
    for path in paths:
        full = os.path.join(ROOT, path)
        if not full.endswith(".py") or not os.path.exists(full):
            continue
        src = open(full).read()
        ids.update(re.findall(r'^\s*id="([a-z0-9\-]+)"', src, flags=re.M))
    # Editing a default in a legacy module does not make its presets new.
    # Use the same literal/positional parser as the introduction-date index.
    from scripts.gen_introduced import _ids_in
    base_files = subprocess.run(["git", "ls-tree", "-r", "--name-only", "main", "--",
                                 "aesthetician/presets"], cwd=ROOT, capture_output=True, text=True)
    for path in base_files.stdout.splitlines():
        if not path.endswith(".py") or os.path.basename(path).startswith("_"):
            continue
        source = subprocess.run(["git", "show", f"main:{path}"], cwd=ROOT,
                                capture_output=True, text=True)
        if source.returncode == 0:
            ids -= _ids_in(source.stdout)
    return ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.05,
                    help="flag pairs with the same effect list and mean param distance below this")
    ap.add_argument("--top", type=int, default=1, help="nearest neighbours to list per preset")
    ap.add_argument("--only-new", action="store_true", help="report only presets absent from main")
    ap.add_argument("--markdown", action="store_true", help="emit a markdown table")
    args = ap.parse_args()

    presets = all_presets()
    sigs = {pid: signature(p) for pid, p in presets.items()}
    focus = new_ids() if args.only_new else set(presets)
    focus = {pid for pid in focus if pid in presets}
    ids = sorted(presets)

    flagged = []
    rows = []
    for pid in sorted(focus):
        scored = []
        for other in ids:
            if other == pid:
                continue
            s, jac, pdist = similarity(sigs[pid], sigs[other])
            scored.append((s, jac, pdist, other))
        scored.sort(reverse=True)
        best = scored[: args.top]
        rows.append((pid, best))
        for s, jac, pdist, other in best:
            if sigs[pid][0] == sigs[other][0] and pdist < args.threshold and (other not in focus or pid < other):
                flagged.append((pid, other, pdist))

    if args.markdown:
        print("| preset | nearest | similarity | same effects | param distance |")
        print("|---|---|---|---|---|")
        for pid, best in rows:
            for s, jac, pdist, other in best:
                print(f"| `{pid}` | `{other}` | {s:.2f} | {jac:.2f} | {pdist:.2f} |")
    else:
        for pid, best in rows:
            s, jac, pdist, other = best[0]
            print(f"{pid:44} -> {other:44} sim {s:.2f}  effects {jac:.2f}  params {pdist:.2f}")

    n = len(rows)
    sims = [best[0][0] for _, best in rows if best]
    print(f"\n{n} presets audited; nearest-neighbour similarity mean {sum(sims)/max(1,len(sims)):.2f}, "
          f"max {max(sims) if sims else 0:.2f}")
    if flagged:
        print(f"⚠ {len(flagged)} near-clone pair(s) (identical effect list, mean param distance < {args.threshold}):")
        for a, b, d in flagged:
            print(f"  - {a} ~ {b} ({d:.3f})")
        return 1
    print("✓ no near-clones")
    return 0


if __name__ == "__main__":
    sys.exit(main())
