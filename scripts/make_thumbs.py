#!/usr/bin/env python
"""Render one animated thumbnail per preset for the GUI's preset browser.

For every preset we render ~1 s of the same source moment through the engine
and emit two files into ``assets/thumbs/``:

  ``<preset-id>.png``   square poster frame, 100x100 (2x for a 50px CSS box)
  ``<preset-id>.webp``  animated square loop of the same second, ~12 fps
                        (falls back to ``<preset-id>.gif`` when the ffmpeg
                        build has no libwebp)

Framing/scale decisions (kept identical for every preset so the list reads as
a controlled comparison):

* ``--t0 7.9 --duration 1.0`` - a continuous close-up shot (the shot starts at
  7.42 s) with a face, skin tones, a blown-white shirt, a saturated cardigan
  and dark hair: enough tonal range to judge a grade, and enough movement
  (talking + camera drift) to see temporal artifacts crawl.
* ``--scale 0.55`` - the engine renders 396x704, i.e. close to the era
  resolutions the ``proc_height`` presets simulate at, so VHS/broadcast/print
  families keep their character; visually indistinguishable from a scale-1.0
  render downsampled to 100px, at a third of the cost.
* ``--crop-bias 0.32`` - the square crop sits slightly above centre so the
  head is framed as a portrait instead of being cut at the forehead.

Presets with an empty video chain (family ``audio``) get a poster only - there
is nothing to animate - and the GUI badges those rows with a ♪.

Usage:
  .venv/bin/python scripts/make_thumbs.py                  # incremental, 4 jobs
  .venv/bin/python scripts/make_thumbs.py --jobs 8
  .venv/bin/python scripts/make_thumbs.py --only vhs-1985,halftone-news --force
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DEFAULT_INPUT = os.path.join(ROOT, "videos-samples", "untreated.mp4")
DEFAULT_OUT = os.path.join(ROOT, "assets", "thumbs")

FFMPEG = "ffmpeg"


# ── animation container ────────────────────────────────────────────────
def anim_codec() -> tuple[str, str]:
    """Return (ext, ffmpeg codec) for animated thumbs: webp when available."""
    try:
        enc = subprocess.run(
            [FFMPEG, "-hide_banner", "-encoders"], capture_output=True, text=True
        ).stdout
    except FileNotFoundError:
        raise SystemExit("ffmpeg not found on PATH")
    if "libwebp_anim" in enc:
        return ".webp", "libwebp_anim"
    if "libwebp" in enc:
        return ".webp", "libwebp"
    return ".gif", "gif"


# ── framing ────────────────────────────────────────────────────────────
def _longest_run(mask):
    import numpy as np

    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return None
    splits = np.flatnonzero(np.diff(idx) > 1)
    starts = np.concatenate([[0], splits + 1])
    ends = np.concatenate([splits, [idx.size - 1]])
    k = int(np.argmax(ends - starts))
    return int(idx[starts[k]]), int(idx[ends[k]])


def active_bbox(frames, min_px: int = 100) -> tuple[int, int, int, int]:
    """(x, y, w, h) of the live picture, ignoring dead letterbox/pillarbox.

    Exhibition/kinescope/pixelvision-style presets inset a small 4:3 picture in
    the middle of the (vertical) frame; a naive centre crop of those is mostly
    black. Rows/columns that never light up across the whole second are dropped.
    """
    import numpy as np

    h, w = frames[0].shape[:2]
    peak = np.max(np.stack([f.max(axis=2) for f in frames]), axis=0).astype(np.float32)
    thr = max(6.0, 0.12 * float(np.percentile(peak, 99.5)))
    rows = _longest_run(np.percentile(peak, 90, axis=1) > thr)
    cols = _longest_run(np.percentile(peak, 90, axis=0) > thr)
    if rows is None or cols is None:
        return 0, 0, w, h
    y0, y1 = rows
    x0, x1 = cols
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    # a pathological trim (near-black preset, one bright dropout band) falls
    # back to the full frame rather than inventing a crop out of nothing
    if bw < max(min_px, 0.15 * w) or bh < max(min_px, 0.15 * h):
        return 0, 0, w, h
    return x0, y0, bw, bh


def square(frame, size: int, bias: float, box: tuple[int, int, int, int] | None = None):
    """Crop a square out of `box` (vertically biased by `bias`) and resize."""
    import cv2

    h, w = frame.shape[:2]
    bx, by, bw, bh = box if box else (0, 0, w, h)
    side = min(bw, bh)
    x = bx + (bw - side) // 2
    y = by + int(round((bh - side) * bias))
    frame = frame[y : y + side, x : x + side]
    interp = cv2.INTER_AREA if side > size else cv2.INTER_CUBIC
    return cv2.resize(frame, (size, size), interpolation=interp)


# Captions presets render nothing without cues, so their thumbs carry one
# sample line each - in the voice of the era the style comes from.
CAPTION_SAMPLES = {
    "cc-line21-1982": "WE'LL BE RIGHT BACK",
    "cc-rollup-1987": ">> AND NOW THE WEATHER",
    "teletext-1979": "888 SUBTITLES",
    "cc-dtv-2004": "Captions, the digital way",
    "cinema-subs-1968": "I never left the harbor.",
    "print-etch-1957": "The night train is late.",
    "dvd-subs-1999": "You are watching chapter three.",
    "fansub-vhs-1994": "This tape subbed by fans",
    "sdh-2007": "[ distant thunder ]",
    "lower-third-1985": "LIVE: DOWNTOWN",
    "vcr-osd-1990": "PLAY",
    "typewriter-doc-1976": "PRIPYAT, 1986",
    "karaoke-1988": "SING ALONG WITH US",
    "intertitle-1923": "And so it begins.",
}


def caption_edits(preset, cfg) -> list:
    """One sample cue for a captions-family preset, timed so the style's own
    motion (typing, rolling, the karaoke sweep) happens inside the thumb."""
    if preset.family != "captions":
        return []
    text = CAPTION_SAMPLES.get(preset.id, "Caption text")
    appear = ""
    for eid, params in preset.video:
        if eid == "captions":
            appear = str(params.get("appear", ""))
    t = cfg["t0"] if appear in ("typewriter", "roll_up", "paint_on") else 0.0
    dur = cfg["t0"] + cfg["duration"] + 1.0 if appear == "karaoke" else 9999.0
    detail = {"text": text, "dur_s": dur}
    # The thumb is a square crop that usually loses the lower third, so the
    # sample rides near center. Styles that place themselves keep their spot.
    if preset.id not in ("vcr-osd-1990", "intertitle-1923"):
        detail["pos_y"] = 0.55 if preset.id == "lower-third-1985" else 0.45
    return [{"op": "add", "kind": "caption", "id": "thumb:cap", "t": t,
             "detail": detail}]


def lead_in_seconds(preset) -> float:
    """Extra seconds to render *before* t0 for presets whose look starts with a
    one-off intro artifact anchored to the first frame (tape junk after PLAY,
    VCR transport start glitch). Those frames are rendered, then discarded, so
    the thumbnail shows the settled look instead of a second of rainbow snow.
    """
    lead = 0.0
    for eid, params in preset.video:
        if eid == "tape_junk":
            lead = max(lead, float(params.get("at_start_s", 0.0) or 0.0))
        elif eid == "vcr_transport" and params.get("start_glitch"):
            lead = max(lead, float(params.get("start_glitch_s", 1.2) or 1.2))
    return min(lead + 0.4, 4.0) if lead > 0 else 0.0


def poster_index(frames) -> int:
    """Pick the most *typical* frame: closest to the median (mean, std).

    Avoids both dropout/black frames and one-off glitch frames becoming the
    still that represents the whole preset.
    """
    import numpy as np

    stats = np.array([[float(f.mean()), float(f.std())] for f in frames], np.float64)
    med = np.median(stats, axis=0)
    spread = np.maximum(stats.std(axis=0), 1e-6)
    d = np.abs((stats - med) / spread).sum(axis=1)
    return int(np.argmin(d))


def write_anim(frames, path: str, codec: str, fps: int, quality: int, size: int) -> None:
    """Encode `frames` (BGR uint8, square, already `size`px) as a looping anim."""
    import numpy as np

    if codec == "gif":
        vf = "split[a][b];[a]palettegen=max_colors=64:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3"
        tail = ["-filter_complex", vf, "-loop", "0"]
    else:
        tail = ["-c:v", codec, "-loop", "0", "-q:v", str(quality),
                "-compression_level", "6", "-preset", "picture"]
    cmd = [
        FFMPEG, "-v", "error", "-nostdin", "-y",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{size}x{size}",
        "-r", str(fps), "-i", "-", "-an", *tail, path,
    ]
    proc = subprocess.run(cmd, input=np.ascontiguousarray(np.stack(frames)).tobytes(),
                          capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"anim encode failed: {proc.stderr.decode(errors='replace')[-400:]}"
        )


# ── per-preset worker ──────────────────────────────────────────────────
def make_one(pid: str, cfg: dict) -> dict:
    import cv2

    from aesthetician.engine import RenderOptions, get_preset, render

    res = {"id": pid, "status": "ok", "poster": 0, "anim": 0, "seconds": 0.0,
           "error": "", "crop": "", "lead": 0.0}
    t_start = time.time()
    preset = get_preset(pid)
    animated = bool(preset.video)  # audio-only presets get a poster only
    poster_path = os.path.join(cfg["out"], f"{pid}.png")
    anim_path = os.path.join(cfg["out"], f"{pid}{cfg['ext']}")

    have_poster = os.path.exists(poster_path) and os.path.getsize(poster_path) > 0
    have_anim = (not animated) or (
        os.path.exists(anim_path) and os.path.getsize(anim_path) > 0
    )
    if have_poster and have_anim and not cfg["force"]:
        res["status"] = "skip"
        res["poster"] = os.path.getsize(poster_path)
        res["anim"] = os.path.getsize(anim_path) if animated else 0
        return res

    try:
        lead = 0.0 if not animated else lead_in_seconds(preset)
        with tempfile.TemporaryDirectory(prefix="thumb_") as tmp:
            mp4 = os.path.join(tmp, "t.mp4")
            render(
                cfg["input"], mp4, preset,
                RenderOptions(
                    seed=cfg["seed"], t0=max(cfg["t0"] - lead, 0.0),
                    duration=cfg["duration"] + lead,
                    scale=cfg["scale"], video_only=True, crf=14,
                    event_edits=caption_edits(preset, cfg),
                ),
            )
            cap = cv2.VideoCapture(mp4)
            raw = []
            while True:
                ok, fr = cap.read()
                if not ok:
                    break
                raw.append(fr)
            cap.release()
        if not raw:
            raise RuntimeError("render produced no frames")
        if lead > 0:
            keep = max(int(round(len(raw) * cfg["duration"] / (cfg["duration"] + lead))), 2)
            raw = raw[-keep:]
        box = active_bbox(raw, min_px=cfg["size"])
        frames = [square(fr, cfg["size"], cfg["bias"], box) for fr in raw]
        res["crop"] = f"{box[2]}x{box[3]}+{box[0]}+{box[1]}"
        res["lead"] = lead

        os.makedirs(cfg["out"], exist_ok=True)
        cv2.imwrite(poster_path, frames[poster_index(frames)],
                    [cv2.IMWRITE_PNG_COMPRESSION, 9])
        res["poster"] = os.path.getsize(poster_path)

        if animated:
            step = max(len(frames) / max(cfg["fps"] * cfg["duration"], 1), 1.0)
            picks = [frames[min(int(i * step), len(frames) - 1)]
                     for i in range(int(len(frames) / step))]
            write_anim(picks or frames, anim_path, cfg["codec"], cfg["fps"],
                       cfg["quality"], cfg["size"])
            res["anim"] = os.path.getsize(anim_path)
        elif os.path.exists(anim_path):
            os.remove(anim_path)
    except Exception as exc:  # noqa: BLE001 - one bad preset must not sink the batch
        res["status"] = "fail"
        res["error"] = f"{type(exc).__name__}: {exc}"[:400]
    res["seconds"] = time.time() - t_start
    return res


# ── manifest ───────────────────────────────────────────────────────────
def write_manifest(out_dir: str, ext: str) -> dict:
    from aesthetician.engine.presets import all_presets

    entries: dict[str, dict] = {}
    for pid, p in sorted(all_presets().items()):
        poster = os.path.join(out_dir, f"{pid}.png")
        anim = os.path.join(out_dir, f"{pid}{ext}")
        if not os.path.exists(poster):
            continue
        entries[pid] = {
            "poster": os.path.basename(poster),
            "anim": os.path.basename(anim) if os.path.exists(anim) else None,
            "audioOnly": not p.video,
        }
    manifest = {"version": 1, "ext": ext, "count": len(entries), "thumbs": entries}
    with open(os.path.join(out_dir, "index.json"), "w") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
    return manifest


def human(n: int) -> str:
    return f"{n / 1024:.0f} KB" if n < 1024 * 1024 else f"{n / 1048576:.1f} MB"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", default=DEFAULT_INPUT, help="source clip")
    ap.add_argument("--out", default=DEFAULT_OUT, help="output directory")
    ap.add_argument("--t0", type=float, default=7.9, help="source timestamp (s)")
    ap.add_argument("--duration", type=float, default=1.0, help="loop length (s)")
    ap.add_argument("--scale", type=float, default=0.55, help="engine render scale")
    ap.add_argument("--crop-bias", type=float, default=0.32,
                    help="0=top, .5=centre: vertical position of the square crop")
    ap.add_argument("--size", type=int, default=100, help="thumbnail px (2x of CSS box)")
    ap.add_argument("--fps", type=int, default=12, help="animation frame rate")
    ap.add_argument("--quality", type=int, default=55, help="webp -q:v")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--only", default="", help="comma-separated preset ids")
    ap.add_argument("--force", action="store_true", help="re-render existing thumbs")
    args = ap.parse_args()

    from aesthetician.engine.presets import all_presets

    if not os.path.exists(args.input):
        print(f"no such input: {args.input}", file=sys.stderr)
        return 2

    presets = all_presets()
    if args.only:
        ids = [s.strip() for s in args.only.split(",") if s.strip()]
        missing = [i for i in ids if i not in presets]
        if missing:
            print(f"unknown preset ids: {', '.join(missing)}", file=sys.stderr)
            return 2
    else:
        ids = sorted(presets)

    ext, codec = anim_codec()
    os.makedirs(args.out, exist_ok=True)
    cfg = {
        "input": args.input, "out": args.out, "t0": args.t0, "duration": args.duration,
        "scale": args.scale, "bias": args.crop_bias, "size": args.size, "fps": args.fps,
        "quality": args.quality, "seed": args.seed, "force": args.force,
        "ext": ext, "codec": codec,
    }
    print(f"[thumbs] {len(ids)} presets → {args.out}  ({codec}, {args.size}px, "
          f"t0={args.t0}s, {args.duration}s @ {args.fps}fps, scale={args.scale})")

    t0 = time.time()
    done = fails = skipped = 0
    total_bytes = 0
    errors: list[tuple[str, str]] = []
    with ProcessPoolExecutor(max_workers=max(args.jobs, 1)) as pool:
        futs = {pool.submit(make_one, pid, cfg): pid for pid in ids}
        for fut in as_completed(futs):
            r = fut.result()
            done += 1
            total_bytes += r["poster"] + r["anim"]
            if r["status"] == "fail":
                fails += 1
                errors.append((r["id"], r["error"]))
                mark = "FAIL"
            elif r["status"] == "skip":
                skipped += 1
                mark = "skip"
            else:
                mark = "ok"
            print(f"[{done:3d}/{len(ids)}] {mark:4s} {r['id']:<34s} "
                  f"{r['seconds']:5.1f}s  png {human(r['poster'])}"
                  + (f"  anim {human(r['anim'])}" if r["anim"] else "  (audio-only)")
                  + (f"  crop {r['crop']}" if r.get("crop") else "")
                  + (f"  lead {r['lead']:.1f}s" if r.get("lead") else "")
                  + (f"\n        {r['error']}" if r["error"] else ""), flush=True)

    m = write_manifest(args.out, ext)
    dt = time.time() - t0
    disk = sum(
        os.path.getsize(os.path.join(args.out, f)) for f in os.listdir(args.out)
    )
    built = done - skipped
    rate = f", {dt / built:.1f}s per render wall-clock" if built else ""
    print(f"\n[thumbs] {built - fails} rendered, {skipped} skipped, "
          f"{fails} failed in {dt / 60:.1f} min ({args.jobs} jobs{rate})")
    print(f"[thumbs] manifest: {m['count']} entries · dir total {human(disk)}")
    if errors:
        print("\nfailures:")
        for pid, err in errors:
            print(f"  {pid}: {err}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
