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
            for v in preset.variants:
                over = parse_override_paths(getattr(v, which))
                for ekey, params in over.items():
                    if ekey not in keys:
                        problems.append(f"{pid}[{v.id}]: {which} override targets missing effect '{ekey}'")
                        continue
                    eff = next(e for e in chain if e.key == ekey)
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
