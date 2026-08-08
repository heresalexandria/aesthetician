#!/usr/bin/env python
"""Validate every preset: effects exist, params exist and coerce, variants apply.

Run: .venv/bin/python scripts/validate_presets.py
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from aesthetician.engine.graph import Context, build_chain
from aesthetician.engine.presets import all_presets, parse_override_paths


def _out_of_range(eff, params: dict) -> list[str]:
    """Values a preset writes that its own parameter will not accept.

    `Param.coerce` clips to the declared bounds, silently, so a preset asking for
    a 4.2 s reverb tail on a dial that stops at 1.5 renders at 1.5 and says 4.2
    forever. Nothing sounds broken, so nothing gets reported - twelve of these
    had accumulated before anyone went looking. Either the value is wrong or the
    range is too tight, and both are worth being made to choose between.
    """
    byname = {p.name: p for p in type(eff).PARAMS}
    bad = []
    for name, val in params.items():
        prm = byname.get(name)
        if prm is None or prm.kind not in ("float", "int"):
            continue
        if not (prm.lo <= float(val) <= prm.hi):
            bad.append(f"{eff.key}.{name} = {val} is outside {prm.lo}..{prm.hi} "
                       f"(renders as {max(prm.lo, min(prm.hi, float(val)))})")
    return bad


def validate() -> int:
    ctx = Context(704, 1280, 30.0, 90, seed=3)
    problems: list[str] = []
    presets = all_presets()
    for pid, preset in sorted(presets.items()):
        for which in ("video", "audio"):
            spec = getattr(preset, which)
            try:
                chain = build_chain(spec)
            except Exception as e:
                problems.append(f"{pid}: {which} chain build failed: {e}")
                continue
            keys = {e.key for e in chain}
            try:
                for eff in chain:
                    eff.resolve(ctx)
            except Exception as e:
                problems.append(f"{pid}: {which} resolve failed: {e}")
            for eff, (_, written) in zip(chain, spec):
                for bad in _out_of_range(eff, written):
                    problems.append(f"{pid}: {which} {bad}")
            for v in preset.variants:
                over = parse_override_paths(getattr(v, which))
                for ekey, params in over.items():
                    if ekey not in keys:
                        problems.append(f"{pid}[{v.id}]: {which} override targets missing effect '{ekey}'")
                        continue
                    eff = next(e for e in chain if e.key == ekey)
                    for bad in _out_of_range(eff, params):
                        problems.append(f"{pid}[{v.id}]: {which} {bad}")
                    try:
                        merged = dict(eff.overrides)
                        merged.update(params)
                        type(eff)(**merged).resolve(ctx)
                    except Exception as e:
                        problems.append(f"{pid}[{v.id}]: {e}")
    if problems:
        print(f"✗ {len(problems)} problem(s):")
        for p in problems:
            print("  -", p)
        return 1
    n_var = sum(len(p.variants) for p in presets.values())
    print(f"✓ {len(presets)} presets valid ({n_var} variants)")
    return 0


if __name__ == "__main__":
    sys.exit(validate())
