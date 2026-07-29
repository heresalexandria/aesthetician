#!/usr/bin/env python
"""Render a grid of presets against sample clips and build labeled contact sheets.

Usage:
  .venv/bin/python scripts/make_gallery.py --presets vhs-1985,film-16mm-doc --input videos-samples/untreated.mp4
  .venv/bin/python scripts/make_gallery.py --all --duration 4

Outputs go to gallery/ (gitignored): one treated mp4 per preset plus
gallery/sheet_<input>.png contact sheets (original in the top-left).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cv2
import numpy as np

from aesthetician.engine import RenderOptions, get_preset, all_presets, render
from aesthetician.engine.media import probe, read_frames


def render_preset(input_path: str, pid: str, out_dir: str, t0: float, duration: float, seed: int, variant=None) -> str:
    tag = pid.replace("/", "-") + (f"-{variant}" if variant else "")
    out = os.path.join(out_dir, f"{os.path.splitext(os.path.basename(input_path))[0]}.{tag}.mp4")
    preset = get_preset(pid)
    opts = RenderOptions(seed=seed, t0=t0, duration=duration, variant=variant)
    print(f"  render {pid}" + (f" [{variant}]" if variant else ""))
    render(input_path, out, preset, opts)
    return out


def grab_frame(path: str, at: float, width: int) -> np.ndarray:
    info = probe(path)
    h = int(round(info.height * width / info.width))
    for f in read_frames(path, width, h, info.fps, t0=min(at, max(info.duration - 0.2, 0)), duration=0.3):
        return (f * 255).astype(np.uint8)
    return np.zeros((h, width, 3), np.uint8)


def label(img: np.ndarray, text: str) -> np.ndarray:
    out = img.copy()
    cv2.rectangle(out, (0, 0), (out.shape[1], 26), (0, 0, 0), -1)
    cv2.putText(out, text, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (240, 230, 210), 1, cv2.LINE_AA)
    return out


def sheet(cells: list[tuple[str, np.ndarray]], cols: int, path: str) -> None:
    w = max(c.shape[1] for _, c in cells)
    h = max(c.shape[0] for _, c in cells)
    rows = (len(cells) + cols - 1) // cols
    canvas = np.zeros((rows * h, cols * w, 3), np.uint8)
    for i, (name, img) in enumerate(cells):
        img = label(img, name)
        r, c = divmod(i, cols)
        canvas[r * h : r * h + img.shape[0], c * w : c * w + img.shape[1]] = img
    cv2.imwrite(path, canvas[..., ::-1])
    print(f"sheet → {path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=os.path.join(ROOT, "videos-samples", "untreated.mp4"))
    ap.add_argument("--presets", default="")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--family", default="")
    ap.add_argument("--t0", type=float, default=4.0)
    ap.add_argument("--duration", type=float, default=3.0)
    ap.add_argument("--frame-at", type=float, default=1.5, help="which second of the rendered clip to show")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--width", type=int, default=420)
    args = ap.parse_args()

    if args.all:
        pids = sorted(all_presets().keys())
    elif args.family:
        pids = sorted(p.id for p in all_presets().values() if p.family == args.family)
    else:
        pids = [p for p in args.presets.split(",") if p]
    if not pids:
        ap.error("give --presets, --family or --all")

    out_dir = os.path.join(ROOT, "gallery")
    os.makedirs(out_dir, exist_ok=True)

    cells = [("ORIGINAL", grab_frame(args.input, args.t0 + args.frame_at, args.width))]
    for pid in pids:
        try:
            clip = render_preset(args.input, pid, out_dir, args.t0, args.duration, args.seed)
            cells.append((pid, grab_frame(clip, args.frame_at, args.width)))
        except Exception as e:  # keep going; report at end
            print(f"  !! {pid} failed: {e}", file=sys.stderr)
            cells.append((f"{pid} (FAILED)", np.zeros_like(cells[0][1])))

    base = os.path.splitext(os.path.basename(args.input))[0]
    sheet(cells, args.cols, os.path.join(out_dir, f"sheet_{base}.png"))


if __name__ == "__main__":
    main()
