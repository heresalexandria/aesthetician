"""End-to-end smoke test: renders 2 s of a sample through a small chain."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aesthetician.engine import Preset, RenderOptions, render
from aesthetician.engine.media import probe

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "videos-samples", "untreated.mp4")
OUT = os.path.join(os.path.dirname(__file__), "..", "out", "smoke.mp4")


def main() -> None:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    preset = Preset(
        id="smoke", name="Smoke", family="test", era="", desc="",
        video=[
            ("tone", {"contrast": 1.15, "lift": 0.05}),
            ("stock", {"profile": "kodachrome"}),
            ("fade", {"amount": 0.35, "profile": "eastman_pink"}),
            ("framing", {"aspect": "4:3", "corner_radius": 0.06}),
        ],
        audio=[
            ("a_bandlimit", {"high_hz": 9000.0, "low_hz": 90.0}),
            ("a_mono", {"amount": 1.0}),
        ],
        proc_height=540,
    )
    render(SAMPLE, OUT, preset, RenderOptions(duration=2.0), progress=lambda p, f: print(f"  {p}: {f:.0%}"))
    info = probe(OUT)
    assert info.duration > 1.5, info
    assert info.has_audio, "audio missing"
    print("smoke OK:", OUT, f"{info.width}x{info.height} {info.duration:.2f}s")


if __name__ == "__main__":
    main()
