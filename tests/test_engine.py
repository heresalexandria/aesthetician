"""Unit tests for engine primitives (run: .venv/bin/python tests/test_engine.py)."""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aesthetician.engine.graph import Context, Param, build_chain, get_effect
from aesthetician.engine.presets import parse_override_paths
from aesthetician.engine.render import (
    _compose_src_map,
    _phase_weights,
    _PhasedProgress,
    _segment_chain,
)
from aesthetician.engine.rng import TemporalNoise, stream


def test_rng_determinism():
    a = stream(7, "grain").standard_normal(64)
    b = stream(7, "grain").standard_normal(64)
    c = stream(7, "other").standard_normal(64)
    assert np.array_equal(a, b), "same seed+key must reproduce"
    assert not np.array_equal(a, c), "different keys must decorrelate"

    tn1 = TemporalNoise(7, 30, 120)
    tn2 = TemporalNoise(7, 30, 120)
    assert np.array_equal(tn1.smooth("weave", 0.5), tn2.smooth("weave", 0.5))
    ev = tn1.events("hits", per_second=2.0, min_gap_s=0.5)
    gaps = np.diff(np.nonzero(ev)[0])
    assert len(gaps) == 0 or gaps.min() > 15 * 0.5, "min gap respected"


def test_param_coercion():
    p = Param("x", "X", "float", 0.5, 0.0, 1.0)
    assert p.coerce("0.75") == 0.75
    assert p.coerce(2.0) == 1.0  # clamped
    b = Param("b", "B", "bool", False)
    assert b.coerce("true") is True and b.coerce(0) is False
    e = Param("m", "M", "enum", "a", choices=("a", "b"))
    assert e.coerce("b") == "b"
    s = Param("t", "T", "str", "1990-01-01")
    assert s.coerce(1990) == "1990"
    try:
        e.coerce("zzz")
        assert False, "invalid enum must raise"
    except ValueError:
        pass


def test_intensity_scaling():
    ctx = Context(64, 64, 30, 30, seed=1, intensity=0.5)
    eff = get_effect("fade")(amount=0.8)
    eff.resolve(ctx)
    assert abs(eff.v["amount"] - 0.4) < 1e-6, "iscale params follow intensity"
    eff2 = get_effect("tone")(gamma=1.2)
    eff2.resolve(ctx)
    assert eff2.v["gamma"] == 1.2, "non-iscale params unaffected"


def test_texture_scaling():
    """The master Texture knob scales noise amounts and nothing else."""
    for tex, expect in ((0.0, 0.0), (0.5, 0.25), (1.0, 0.5), (1.5, 0.75)):
        ctx = Context(64, 64, 30, 30, seed=1, texture=tex)
        g = get_effect("grain")(amount=0.5, size=2.5)
        g.resolve(ctx)
        assert abs(g.v["amount"] - expect) < 1e-6, (tex, g.v["amount"])
        assert g.v["size"] == 2.5, "sizes must not be scaled by texture"
    # a non-noise param is untouched even at texture 0
    ctx = Context(64, 64, 30, 30, seed=1, texture=0.0)
    t = get_effect("tone")(contrast=1.2)
    t.resolve(ctx)
    assert t.v["contrast"] == 1.2


def test_upscale_reporting():
    """Effects can learn how much the final upscale will magnify their texture."""
    assert Context(704, 520, 30, 30, out_height=1280).upscale > 2.4
    assert Context(704, 1280, 30, 30).upscale == 1.0  # no proc_height → no magnification


def test_grain_size_ref():
    """size_ref='output' pre-shrinks grain so it lands at the requested size."""
    import numpy as np

    frame = np.full((520, 704, 3), 0.5, np.float32)
    sizes = {}
    for ref in ("processing", "output"):
        ctx = Context(704, 520, 30, 30, seed=4, out_height=1280)
        g = get_effect("grain")(amount=0.6, size=2.9, size_ref=ref)
        g.resolve(ctx)
        g.prepare(ctx)
        out = g.process(frame.copy(), ctx)
        resid = out[..., 1] - 0.5
        # correlation length: lag where horizontal autocorrelation halves
        ac = [float((resid[:, : resid.shape[1] - l] * resid[:, l:]).mean()) for l in range(12)]
        ac = np.array(ac) / ac[0]
        below = np.where(ac < 0.5)[0]
        sizes[ref] = below[0] if len(below) else 12
    assert sizes["output"] < sizes["processing"], sizes


def test_audio_only_source():
    """An audio file renders through the audio chain only, in its own format."""
    import subprocess

    from aesthetician.engine import Preset, RenderOptions, render
    from aesthetician.engine.media import probe

    root = os.path.join(os.path.dirname(__file__), "..")
    src = os.path.join(root, "out", "_t_audio_in.wav")
    os.makedirs(os.path.dirname(src), exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=440:d=2",
         "-c:a", "pcm_s16le", src], check=True)

    info = probe(src)
    assert info.has_video is False and info.has_audio is True
    assert info.width == 0 and info.duration > 1.5

    preset = Preset(
        id="t_audio", name="t", family="t", era="", desc="",
        video=[("tone", {"contrast": 1.4})],        # must be ignored, not crash
        audio=[("a_bandlimit", {"high_hz": 3000.0}), ("a_tape_hiss", {"level_db": -40.0})],
    )
    for ext in (".wav", ".m4a"):
        out = os.path.join(root, "out", f"_t_audio_out{ext}")
        render(src, out, preset, RenderOptions(seed=2, duration=1.0))
        got = probe(out)
        assert got.has_video is False, ext
        assert got.has_audio is True, ext
        assert abs(got.duration - 1.0) < 0.35, (ext, got.duration)


def test_cover_art_is_not_video():
    """A tagged MP3 carries its artwork as a video stream; it must not count."""
    import subprocess

    from aesthetician.engine.media import probe

    root = os.path.join(os.path.dirname(__file__), "..")
    out = os.path.join(root, "out")
    os.makedirs(out, exist_ok=True)
    wav = os.path.join(out, "_t_art.mp3")
    art = os.path.join(out, "_t_art.jpg")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=440:d=2",
                    "-c:a", "libmp3lame", os.path.join(out, "_t_bare.mp3")], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=red:s=600x600:d=1",
                    "-frames:v", "1", art], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(out, "_t_bare.mp3"),
                    "-i", art, "-map", "0:a", "-map", "1:v", "-c:a", "copy", "-c:v", "mjpeg",
                    "-disposition:v", "attached_pic", "-id3v2_version", "3", wav], check=True)

    info = probe(wav)
    assert info.has_video is False, "album art must not be treated as a video stream"
    assert info.width == 0 and info.height == 0
    assert info.has_audio is True and info.duration > 1.0


def test_overrides_and_chain_keys():
    o = parse_override_paths({"vhs.tracking": 0.7, "grain#2.amount": 0.2})
    assert o == {"vhs": {"tracking": 0.7}, "grain#2": {"amount": 0.2}}
    chain = build_chain([("tone", {}), ("fade", {}), ("tone", {"gamma": 1.3})])
    assert [e.key for e in chain] == ["tone", "fade", "tone#2"]


def test_remap_composition():
    ctx = Context(64, 64, 30, 10, seed=1)

    class Hold2:
        kind = "frame"

        def remap(self, _ctx):
            return np.repeat(np.arange(5), 2)  # 0011223344

    class Skip:
        kind = "frame"

        def remap(self, _ctx):
            r = np.arange(10)
            r[5:] += 2  # skip ahead
            return r

    # composed: src = hold2(skip(fi)) → skip=[0,1,2,3,4,7,8,9,9,9], hold2[k]=k//2
    m = _compose_src_map([Hold2(), Skip()], ctx, 10)
    assert m.tolist() == [0, 0, 1, 1, 2, 3, 4, 4, 4, 4], m.tolist()
    assert np.all(np.diff(m) >= 0), "monotonic"


def test_phased_progress_never_walks_backwards():
    """One bar out of many per-phase 0..1 runs, and it only ever climbs."""
    seen = []
    report = _PhasedProgress(lambda phase, frac: seen.append((phase, frac)),
                             _phase_weights(has_video_chain=True, has_audio=True))

    for i in range(11):
        report("video", i / 10)
    report("audio", 0.0)         # used to snap the bar back to zero
    report("audio", 1.0)
    report("mux", 0.0)           # and again, right at the end
    report("done", 1.0)

    fracs = [f for _, f in seen]
    assert all(b >= a for a, b in zip(fracs, fracs[1:])), f"went backwards: {fracs}"
    assert fracs[0] == 0.0 and fracs[-1] == 1.0
    # The video pass owns the bulk of the bar, so a finished video chain must not
    # already read as finished overall.
    video_end = next(f for p, f in seen if p == "audio")
    assert 0.8 < video_end < 0.9, video_end

    # A phase that never fires leaves the bar alone rather than rewinding it.
    seen.clear()
    silent = _PhasedProgress(lambda phase, frac: seen.append((phase, frac)),
                             _phase_weights(has_video_chain=True, has_audio=False))
    silent("video", 1.0)
    silent("mux", 0.0)
    silent("done", 1.0)
    fracs = [f for _, f in seen]
    assert all(b >= a for a, b in zip(fracs, fracs[1:])), f"went backwards: {fracs}"
    assert fracs[-1] == 1.0

    # No callback at all must stay a no-op.
    _PhasedProgress(None, _phase_weights(True, True))("video", 0.5)


def test_segmenting():
    tone = get_effect("tone")()
    fade = get_effect("fade")()

    class FP:
        kind = "filepass"

    fp = FP()
    segs = _segment_chain([tone, fp, fade])
    assert [len(s) for s in segs] == [1, 1, 1]
    segs2 = _segment_chain([fp, fade])  # leading filepass keeps an empty frame segment
    assert segs2[0] == [] and segs2[1][0] is fp
    segs3 = _segment_chain([tone, fade])
    assert len(segs3) == 1 and len(segs3[0]) == 2


if __name__ == "__main__":
    # Several tests synthesise their fixtures with ffmpeg and probe them with
    # ffprobe. Say so up front: without this it surfaces as a FileNotFoundError
    # at the bottom of a subprocess traceback, which reads like a bug in the
    # engine rather than a missing tool.
    import shutil

    missing = [tool for tool in ("ffmpeg", "ffprobe") if not shutil.which(tool)]
    if missing:
        raise SystemExit(
            f"{' and '.join(missing)} not found on PATH - these tests need them to build "
            "and read their fixtures. Install ffmpeg (`brew install ffmpeg`, "
            "`apt-get install ffmpeg`) and try again."
        )

    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok {fn.__name__}")
    print(f"{len(fns)} engine tests passed")
