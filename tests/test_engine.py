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


def test_source_counts_match_the_registry():
    """The packaging check counts effects and presets by parsing the source.

    It has to, because it runs on a build host with no engine installed - but
    that only works while the parse agrees with what import-time registration
    actually produces. If someone registers a preset inside a loop or behind a
    conditional, the packaging build starts failing at the very end of a release
    with a confusing message. Catch the divergence here instead.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from aesthetician.engine.graph import all_effects
    from aesthetician.engine.presets import all_presets
    from scripts.package.build_runtime import source_counts

    assert source_counts() == (len(all_effects()), len(all_presets())), (
        f"source scan says {source_counts()} but the registry has "
        f"{len(all_effects())} effects / {len(all_presets())} presets"
    )


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


def test_events_are_scheduled_against_the_clip_not_the_window():
    """A preview is a short render from the middle of a clip, not a second clip.

    Everything timed used to be timed from the render's own frame 0, so Rental
    Tape's transport lock-up - authored at 1.2 s, meaning 1.2 s into the tape -
    fired at the top of *every* preview, wherever the scrubber was. The same
    went for every per-frame random draw: the speckle a preview showed at 0:40
    was the speckle the export had at 0:00.

    The two halves pinned here are that a render starting at zero is keyed
    exactly as it always was - so no export moves - and that one starting later
    is keyed to where it sits on the clip.
    """
    from aesthetician.engine.graph import Context
    from aesthetician.engine.rng import stream

    at_zero = Context(width=64, height=48, fps=30.0, n_frames=90, seed=7, t0=0.0)
    for fi in (0, 5, 89):
        at_zero.fi_out = fi
        assert at_zero.frame_rng("k").bit_generator.state == stream(7, f"k@{fi}").bit_generator.state
        assert at_zero.abs_frame() == fi
    for t in (0.0, 1.2, 4.5, 12.0):
        assert at_zero.frame_of(t) == int(round(t * 30.0))

    mid = Context(width=64, height=48, fps=30.0, n_frames=90, seed=7, t0=4.0)
    mid.fi_out = 0
    assert mid.frame_rng("k").bit_generator.state == stream(7, "k@120").bit_generator.state
    # An event authored before this window simply is not in it.
    assert mid.frame_of(1.2) < 0
    assert mid.frame_of(4.0) == 0
    assert mid.frame_of(5.0) == 30

    # A stack's later layers seek from zero but stay where they are on the clip.
    from aesthetician.engine.render import RenderOptions

    assert RenderOptions(t0=4.0).clip_t0 == 4.0
    assert RenderOptions(t0=0.0, source_t0=4.0).clip_t0 == 4.0


def test_optional_ffmpeg_encoders_degrade_instead_of_dying():
    """A preset must render on an ffmpeg build missing an optional encoder.

    The desktop app ships an ffmpeg it does not build itself, and what is
    compiled into it varies: the macOS bundle has libmp3lame but no
    libopencore_amrnb and no libgsm. `a_codec_speech` raised on a missing
    encoder, which took the entire render with it - so Flip Phone Clip, the one
    preset that asks for AMR, could not render at all in a packaged build while
    working perfectly from a checkout against a Homebrew ffmpeg. That gap
    between the two environments is exactly what a test has to close, so this
    runs every preset's audio chain against a deliberately threadbare build.
    """
    from aesthetician.engine.graph import Context, all_effects, build_chain, get_effect
    from aesthetician.engine.presets import all_presets
    from aesthetician.effects.audio import digicodec

    # The effects that shell out to an encoder are exactly the audio file passes,
    # so selecting them by kind keeps this covering the next one too. Everything
    # else in a chain is left alone: a bed that cannot find its baked wav is a
    # missing asset, which is a different problem with a different answer.
    gated = {eid for eid, cls in all_effects().items() if cls.kind == "audio_filepass"}
    assert gated, "no audio file passes left to check"

    # Everything optional stripped out: no lame, no AMR, no GSM.
    bare = frozenset({"pcm_s16le", "pcm_mulaw", "pcm_alaw", "g726", "adpcm_ima_wav", "aac"})
    real = digicodec._available_encoders
    digicodec._available_encoders = lambda: bare
    try:
        ctx = Context(width=320, height=240, fps=30.0, n_frames=60, seed=3)
        broke = []
        for pid, preset in sorted(all_presets().items()):
            for eid, params in preset.audio:
                if eid not in gated:
                    continue
                try:
                    eff = get_effect(eid)(**params)
                    eff.resolve(ctx)
                    eff.prepare(ctx)
                except Exception as exc:
                    broke.append(f"{pid} [{eid}]: {type(exc).__name__}: {exc}")
        assert broke == [], f"{len(broke)} presets cannot render without optional encoders: {broke[:4]}"

        # And the substitution is a real one, not a silent nothing.
        speech = build_chain([("a_codec_speech", {"codec": "amr_74"})])[0]
        speech.resolve(ctx)
        speech.prepare(ctx)
        assert speech._codec == "g726_16", speech._codec
    finally:
        digicodec._available_encoders = real


def test_every_effect_can_be_switched_off_in_place():
    """`enabled` is the one dial guaranteed to reach nothing, on all of them.

    Most effects can be neutralised by turning their amounts down, but not all:
    a Risograph is defined by its ink pair and a projection surface by its
    material, so zeroing every number still leaves a duotone print on a matte
    screen. Taking the effect out of the chain is a different thing from
    switching it off in place - a preset's chain is fixed, and the useful move
    while judging a look is to lift one link out and drop it back.
    """
    import numpy as np

    from aesthetician.engine.graph import Context, all_effects, get_effect

    effects = all_effects()
    assert len(effects) > 90
    missing = [eid for eid, cls in effects.items()
               if not any(p.name == "enabled" for p in cls.PARAMS)]
    assert missing == [], f"effects with no way to switch them off: {missing}"
    for eid, cls in effects.items():
        prm = next(p for p in cls.PARAMS if p.name == "enabled")
        assert prm.default is True, f"{eid}: the default has to mean 'no change'"

    # And the chain builder actually drops them, keys intact for the survivors.
    from aesthetician.engine.graph import build_chain
    from aesthetician.engine.render import _live_chain

    ctx = Context(width=32, height=24, fps=30, n_frames=10, seed=3)
    chain = build_chain([("tone", {}), ("grain", {}), ("tone", {"gamma": 1.2})])
    live = _live_chain(chain, ctx, {"grain": {"enabled": False}})
    assert [e.key for e in live] == ["tone", "tone#2"], [e.key for e in live]

    # A disabled effect is a pass-through, not a quieter version of itself.
    frame = np.random.default_rng(4).random((24, 32, 3)).astype(np.float32)
    for eid in ("riso_print", "screen", "nitrate", "vhs"):
        eff = get_effect(eid)(enabled=False)
        eff.resolve(ctx)
        assert eff.v["enabled"] is False, eid
        kept = _live_chain(build_chain([(eid, {"enabled": False})]), ctx, {})
        assert kept == [], f"{eid} survived being switched off"
    assert frame.shape == (24, 32, 3)


def test_still_is_frame_zero_of_the_clip():
    """A still must be the frame the clip opens on, not a one-frame render of it.

    The temporal tracks in rng.py are lowpassed and percentile-normalised across
    their whole length, so `n_frames` decides what frame 0 looks like. Render one
    frame *as a one-frame clip* and every wobble - time-base error, flagging,
    tracking - normalises against a single sample and lands at full excursion.
    This pins both halves: keeping the frame count reproduces the clip, and
    dropping it does not, so nobody can "simplify" render_still into the obvious
    thing without a red test.
    """
    import subprocess

    import numpy as np

    from aesthetician.engine import Preset, RenderOptions, render
    from aesthetician.engine.render import render_still

    root = os.path.join(os.path.dirname(__file__), "..")
    src = os.path.join(root, "out", "_t_still_in.mp4")
    os.makedirs(os.path.dirname(src), exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "testsrc2=size=320x240:rate=30:duration=2", "-c:v", "libx264",
         "-crf", "0", "-pix_fmt", "yuv420p", src], check=True)

    # Wobble on purpose: with a still chain the two paths agree trivially.
    preset = Preset(
        id="t_still", name="t", family="t", era="", desc="",
        video=[("vhs", {"time_base_error": 0.9, "flagging": 0.8, "tracking_error": 0.6,
                        "dropouts": 0.0})],
    )
    opts = RenderOptions(seed=1234, duration=1.5, scale=1.0, crf=0)

    clip = os.path.join(root, "out", "_t_still_clip.mp4")
    render(src, clip, preset, opts)
    kept = render_still(src, os.path.join(root, "out", "_t_still_kept.png"), preset, opts)
    one = render_still(src, os.path.join(root, "out", "_t_still_one.png"), preset, opts,
                       n_frames_override=1)
    assert kept.exact is True, "a chain with no file pass is exactly reproducible"

    def pixels(path, first_frame_only=False):
        # RGB on both sides. Asking ffmpeg for gray instead would convert the
        # PNG with BT.601 and the tagged clip with BT.709, and the gap between
        # those two matrices is larger than anything this test is looking for.
        cmd = ["ffmpeg", "-v", "error", "-i", path]
        if first_frame_only:
            cmd += ["-vframes", "1"]
        cmd += ["-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        raw = subprocess.run(cmd, capture_output=True, check=True).stdout
        return np.frombuffer(raw, np.uint8).astype(np.int16)

    truth = pixels(clip, first_frame_only=True)
    kept_px = pixels(kept.path)
    one_px = pixels(one.path)
    assert kept_px.size == truth.size == one_px.size

    # The still carries no H.264 pass of its own, so what is left against the
    # clip is that encode: small, and nothing like a different frame.
    kept_err = float(np.abs(kept_px - truth).mean())
    one_err = float(np.abs(one_px - truth).mean())
    assert kept_err < 6.0, f"still drifted from frame 0 of the clip ({kept_err:.2f}/255)"
    # How much worse the one-frame version looks depends on where the wobble
    # happens to sit at frame 0, so this is deliberately a loose floor; the sharp
    # statement of the same fact lives in test_temporal_tracks_need_the_real_length.
    assert one_err > kept_err * 1.5, (
        f"a one-frame render came out as close as the real thing "
        f"({one_err:.2f} vs {kept_err:.2f}) - has rng.py stopped depending on n_frames?"
    )


def test_temporal_tracks_need_the_real_length():
    """Why render_still keeps the clip's frame count instead of asking for one frame.

    `smooth` lowpasses white noise across the whole track and divides by the 95th
    percentile of the result; with a single sample that percentile *is* the
    sample, so the track normalises to a full-scale excursion no matter what the
    seed drew. Every wobble built on it - time-base error, flagging, gate weave,
    tracking - comes out pinned to its limit. This is the root of it, stated
    where it cannot be mistaken for a rounding difference.
    """
    from aesthetician.engine.rng import TemporalNoise

    clip = TemporalNoise(7, 30.0, 90)
    alone = TemporalNoise(7, 30.0, 1)
    assert abs(clip.smooth("k", 1.2)[0] - alone.smooth("k", 1.2)[0]) > 0.3
    assert abs(alone.smooth("k", 1.2)[0]) == 1.0, "one sample always normalises to the rail"
    # White noise is drawn per frame and never normalised, so it does not care.
    assert clip.white("k")[0] == alone.white("k")[0]


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
