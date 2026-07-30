#!/usr/bin/env python
"""Calibration audit: flags preset parameter values outside vetted ranges.

These guardrails encode lessons from side-by-side comparison against real
archival footage. Violations are warnings, not errors - but every warning
should be a deliberate artistic choice, not an accident.

Run: .venv/bin/python scripts/audit_calibration.py
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from aesthetician.engine.presets import all_presets

# (effect, param) -> (lo, hi, why)
GUARDRAILS: dict[tuple[str, str], tuple[float, float, str]] = {
    ("grain", "chroma_grain"): (0.0, 0.28, "beyond ~0.25 color grain reads as rainbow confetti"),
    ("grain", "amount"): (0.0, 0.65, "heavy grain at era proc heights upscales louder than you think"),
    ("vhs", "chroma_noise"): (0.0, 0.6, "chroma speckle overwhelms above ~0.6 even on SP"),
    ("vhs", "luma_noise"): (0.0, 0.7, ""),
    ("cel_dirt", "visibility"): (0.0, 0.14, "cel dirt should read subliminally"),
    ("paper_texture", "amount"): (0.0, 0.07, "paper texture past ~0.06 reads as canvas, not print"),
    ("ntsc", "phase_noise"): (0.0, 6.0, "phase noise is in degrees; >6 is broken-set territory"),
    ("ntsc", "dot_crawl"): (0.0, 0.6, ""),
    ("halation", "strength"): (0.0, 0.6, ""),
    ("flicker", "amount"): (0.0, 0.6, "above ~0.55 reads as strobe, not projector"),
    ("dust", "density"): (0.0, 1.0, ""),
    ("crt", "scan_strength"): (0.0, 0.45, "hard scanlines read as 'retro shader', not CRT"),
}

# EP/LP internally multiply noise ~2.6x/1.7x
VHS_MODE_NOISE_CAP = {"ep": 0.32, "lp": 0.45, "sp": 0.7}


def audit() -> int:
    warnings = 0
    for pid, preset in sorted(all_presets().items()):
        chains = [("video", preset.video), ("audio", preset.audio)]
        for which, chain in chains:
            for eid, params in chain:
                for pname, val in params.items():
                    key = (eid, pname)
                    if key in GUARDRAILS and isinstance(val, (int, float)):
                        lo, hi, why = GUARDRAILS[key]
                        if not (lo <= float(val) <= hi):
                            print(f"  ⚠ {pid}: {eid}.{pname}={val} outside [{lo},{hi}]" + (f" - {why}" if why else ""))
                            warnings += 1
                if eid == "vhs":
                    mode = str(params.get("mode", "sp"))
                    cap = VHS_MODE_NOISE_CAP.get(mode, 0.7)
                    for np_ in ("luma_noise", "chroma_noise"):
                        v = params.get(np_)
                        if isinstance(v, (int, float)) and float(v) > cap:
                            print(f"  ⚠ {pid}: vhs.{np_}={v} too hot for mode={mode} (cap {cap}; mode multiplies internally)")
                            warnings += 1
    n = len(all_presets())
    if warnings:
        print(f"{warnings} calibration warning(s) across {n} presets")
    else:
        print(f"✓ all {n} presets within vetted calibration ranges")
    return 0


if __name__ == "__main__":
    sys.exit(audit())
