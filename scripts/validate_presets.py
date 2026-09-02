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


def _vocabulary_problems(presets) -> list[str]:
    """Findability and house-style checks that no render would ever catch."""
    from aesthetician.collections import all_collections
    from aesthetician.presets._keywords import KEYWORDS
    from aesthetician.taxonomy import facets_for, is_audio_only

    out: list[str] = []
    for pid in KEYWORDS:
        if pid not in presets:
            out.append(f"_keywords.py names a preset that does not exist: '{pid}'")
    for c in all_collections():
        for pid in c.presets:
            if pid not in presets:
                out.append(f"collection '{c.id}' names a missing preset '{pid}'")
        for r in c.recipes:
            for pid in r.layers:
                if pid not in presets:
                    out.append(f"recipe '{c.id}/{r.id}' names a missing preset '{pid}'")
    for pid, p in sorted(presets.items()):
        texts = [("name", p.name), ("desc", p.desc), ("tagline", p.tagline)]
        texts += [(f"variant {v.id}", v.desc) for v in p.variants]
        texts += [(f"variant {v.id} name", v.name) for v in p.variants]
        for label, t in texts:
            if "\u2014" in t:
                out.append(f"{pid}: {label} contains an em-dash (house style: none, anywhere)")
        if len(p.tagline) > 45:
            out.append(f"{pid}: tagline is {len(p.tagline)} chars; the list clamps at 45")
        for k in p.keywords:
            if k != k.lower() or k.strip() != k:
                out.append(f"{pid}: keyword {k!r} must be lower-case and trimmed")
        if len(set(p.keywords)) != len(p.keywords):
            out.append(f"{pid}: duplicate keywords")
        if not p.tags:
            out.append(f"{pid}: no tags")
        facets = facets_for(p)
        if not facets["medium"] and p.family not in ("adjust", "captions"):
            out.append(f"{pid}: no medium facet - add a format word to tags/keywords "
                       f"(see aesthetician/taxonomy.py)")
        if not facets["genre"] and not is_audio_only(p) and p.family not in ("adjust", "captions"):
            out.append(f"{pid}: no genre facet - add a program/genre word to keywords")
    return out


def validate() -> int:
    ctx = Context(704, 1280, 30.0, 90, seed=3)
    problems: list[str] = []
    presets = all_presets()
    problems.extend(_vocabulary_problems(presets))
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
