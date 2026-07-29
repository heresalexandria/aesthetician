#!/usr/bin/env python
"""Render EVERY preset (short, low-res) and assert output health.

Checks per preset: render completes; output probes; video is not black/blank;
duration ≈ requested; audio stream present. Run with a worker pool.

Usage: .venv/bin/python scripts/smoke_all_presets.py [--duration 1.2] [--scale 0.3] [--jobs 4]
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SAMPLES = {
    "cartoon": os.path.join(ROOT, "videos-samples", "classic-cartoon.mp4"),
    "default": os.path.join(ROOT, "videos-samples", "untreated.mp4"),
}
OUT_DIR = os.path.join(ROOT, "out", "smoke-all")


def check_one(pid: str, duration: float, scale: float, seed: int) -> tuple[str, str]:
    """Returns (pid, "" on success | error text)."""
    import numpy as np

    from aesthetician.engine import RenderOptions, get_preset, render
    from aesthetician.engine.media import probe, read_frames

    preset = get_preset(pid)
    src = SAMPLES["cartoon"] if preset.family == "cartoon" else SAMPLES["default"]
    out = os.path.join(OUT_DIR, f"{pid.replace('/', '-')}.mp4")
    try:
        t0 = time.time()
        render(src, out, preset, RenderOptions(seed=seed, t0=2.0, duration=duration, scale=scale))
        dt = time.time() - t0
        info = probe(out)
        if abs(info.duration - duration) > 0.75:
            return pid, f"duration {info.duration:.2f} vs {duration}"
        if not info.has_audio:
            return pid, "no audio stream"
        means = []
        for i, fr in enumerate(read_frames(out, info.width, info.height, info.fps)):
            means.append(float(fr.mean()))
            if i >= 6:
                break
        if not means or max(means) < 0.012:
            return pid, f"output near-black (max mean {max(means or [0]):.4f})"
        if any(not np.isfinite(m) for m in means):
            return pid, "non-finite pixels"
        return pid, f"OK {dt:.1f}s"
    except Exception as e:  # noqa: BLE001
        return pid, f"FAIL {type(e).__name__}: {str(e)[:300]}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=float, default=1.2)
    ap.add_argument("--scale", type=float, default=0.3)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--only", default="", help="comma-separated preset ids")
    args = ap.parse_args()

    from aesthetician.engine.presets import all_presets

    os.makedirs(OUT_DIR, exist_ok=True)
    pids = sorted(all_presets().keys())
    if args.only:
        pids = [p for p in pids if p in set(args.only.split(","))]

    failures: list[tuple[str, str]] = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        futs = {ex.submit(check_one, pid, args.duration, args.scale, args.seed): pid for pid in pids}
        done = 0
        for fut in as_completed(futs):
            pid, msg = fut.result()
            done += 1
            ok = msg.startswith("OK")
            if not ok:
                failures.append((pid, msg))
            print(f"[{done}/{len(pids)}] {'✓' if ok else '✗'} {pid:<30} {msg}")
    print(f"\n{len(pids) - len(failures)}/{len(pids)} presets healthy in {time.time() - t0:.0f}s")
    if failures:
        print("FAILURES:")
        for pid, msg in failures:
            print(f"  ✗ {pid}: {msg}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
