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


def test_the_event_plan_is_what_actually_renders():
    """Every dropout is knowable before a frame is drawn, and the list is exact.

    This is what a timeline editor stands on. The draws used to happen inside
    `process`, a frame at a time, so nothing could ask where the damage was;
    they happen in `prepare` now, from the same per-frame generators in the same
    order, which leaves the picture untouched and the schedule readable. The
    test renders the preset twice - once as authored, once with dropouts off -
    and asserts the frames that differ are exactly the frames the plan named.
    """
    import subprocess

    import numpy as np

    from aesthetician.engine import Preset, RenderOptions, render
    from aesthetician.engine.render import Layer, plan_events

    root = os.path.join(os.path.dirname(__file__), "..")
    src = os.path.join(root, "out", "_t_plan_in.mp4")
    os.makedirs(os.path.dirname(src), exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "testsrc2=size=320x240:rate=30:duration=3", "-c:v", "libx264",
         "-crf", "0", "-pix_fmt", "yuv420p", src], check=True)

    quiet = {"luma_noise": 0, "chroma_noise": 0, "head_switch": 0, "time_base_error": 0,
             "flagging": 0, "jitter_v": 0, "tracking_error": 0, "sharpen": 0,
             "chroma_delay": 0, "dropout_burst": 0.5}
    on = Preset(id="t_plan_on", name="t", family="t", era="", desc="",
                video=[("vhs", {**quiet, "dropouts": 8.0})])
    off = Preset(id="t_plan_off", name="t", family="t", era="", desc="",
                 video=[("vhs", {**quiet, "dropouts": 0.0})])
    opts = RenderOptions(seed=99, duration=2.0, scale=1.0, crf=0)
    a = os.path.join(root, "out", "_t_plan_on.mp4")
    b = os.path.join(root, "out", "_t_plan_off.mp4")
    render(src, a, on, opts)
    render(src, b, off, opts)

    plan = plan_events(src, [Layer(preset=on, seed=99)], opts)
    fps = plan["fps"]
    planned = {int(round(e["t"] * fps)) for e in plan["events"] if e["kind"] == "dropout"}
    assert planned, "a preset at 8 events/s over two seconds must plan some"

    W, H = 320, 240
    def frames(path):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo",
                              "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
        n = len(raw) // (W * H)
        return np.frombuffer(raw[: n * W * H], np.uint8).reshape(n, H, W).astype(np.int16)

    fa, fb = frames(a), frames(b)
    n = min(len(fa), len(fb))
    # A dropout can land on picture it barely changes, so "differs at all"
    # rather than "differs loudly" is the honest comparison.
    changed = {i for i in range(n) if np.abs(fa[i] - fb[i]).max() > 2}
    assert changed <= planned, f"rendered damage the plan did not name: {sorted(changed - planned)}"
    # And most of what was planned really does show up.
    assert len(changed) >= 0.8 * len({p for p in planned if p < n}), (len(changed), len(planned))

    # Per-instance detail is there to be edited, and the id is how an edit
    # names its target.
    one = next(e for e in plan["events"] if e["kind"] == "dropout")
    assert set(one["detail"]) == {"id", "row", "x", "length_px", "rows", "polarity"}, one


def test_event_edits_change_the_render_the_way_they_say():
    """Remove, move and add really do what the plan will claim they did.

    The editor is only honest if an edit's effect on the picture is exactly its
    effect on the plan: remove leaves the named frame identical to a render
    with no dropouts at all, move takes the damage from one frame to another,
    add puts damage where there was none - and a no-edit render is untouched
    by the machinery existing.
    """
    import subprocess

    import numpy as np

    from aesthetician.engine import Preset, RenderOptions, render
    from aesthetician.engine.render import Layer, plan_events

    root = os.path.join(os.path.dirname(__file__), "..")
    src = os.path.join(root, "out", "_t_edit_in.mp4")
    os.makedirs(os.path.dirname(src), exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "testsrc2=size=320x240:rate=30:duration=2", "-c:v", "libx264",
         "-crf", "0", "-pix_fmt", "yuv420p", src], check=True)

    quiet = {"luma_noise": 0, "chroma_noise": 0, "head_switch": 0, "time_base_error": 0,
             "flagging": 0, "jitter_v": 0, "tracking_error": 0, "sharpen": 0,
             "chroma_delay": 0, "dropout_burst": 0.0}
    # A sparse rate, so the frames involved carry one instance each and the
    # comparisons stay unambiguous.
    preset = Preset(id="t_edit", name="t", family="t", era="", desc="",
                    video=[("vhs", {**quiet, "dropouts": 2.5})])
    layer = lambda edits: [Layer(preset=preset, seed=31, event_edits=edits)]
    opts = lambda edits: RenderOptions(seed=31, duration=2.0, scale=1.0, crf=0,
                                       event_edits=edits)

    plan = plan_events(src, layer([]), RenderOptions(seed=31, duration=2.0, scale=1.0))
    drops = [e for e in plan["events"] if e["kind"] == "dropout"]
    assert len(drops) >= 2, f"need at least two dropouts to edit, got {len(drops)}"
    fps = plan["fps"]
    victim = drops[0]
    vid = victim["detail"]["id"]
    vfr = int(round(victim["t"] * fps))

    W, H = 320, 240
    def frames(path):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo",
                              "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
        n = len(raw) // (W * H)
        return np.frombuffer(raw[: n * W * H], np.uint8).reshape(n, H, W).astype(np.int16)

    def rendered(edits, name):
        out = os.path.join(root, "out", f"_t_edit_{name}.mp4")
        render(src, out, preset, opts(edits))
        return frames(out)

    base = rendered([], "base")
    clean = rendered([{"op": "remove", "id": e["detail"]["id"]} for e in drops], "clean")

    # Remove: the victim's frame becomes indistinguishable from a fully clean one.
    removed = rendered([{"op": "remove", "id": vid}], "removed")
    assert np.abs(base[vfr] - clean[vfr]).max() > 2, "victim must be visible to begin with"
    assert np.array_equal(removed[vfr], clean[vfr]), "removing must erase exactly that damage"

    # Move: the damage leaves one frame and turns up on the other, same shape.
    target_fi = vfr + 9 if vfr + 9 < len(base) else vfr - 9
    target_t = plan["t0"] + target_fi / fps
    moved = rendered([{"op": "move", "id": vid, "t": target_t}], "moved")
    assert np.array_equal(moved[vfr], clean[vfr]), "moved damage must vanish from its frame"
    assert np.abs(moved[target_fi] - base[target_fi]).max() > 2, "and land on the target"

    # Add: a synthetic dropout lands on a frame the seed left alone.
    quiet_fi = next(i for i in range(len(base))
                    if np.array_equal(base[i], clean[i]) and i not in (vfr, target_fi))
    added = rendered([{"op": "add", "kind": "dropout", "t": plan["t0"] + quiet_fi / fps,
                       "detail": {"row": 120, "x": 40, "length_px": 160,
                                  "polarity": "bright", "rows": 2}}], "added")
    d = np.abs(added[quiet_fi] - clean[quiet_fi])
    assert d.max() > 10, "an added dropout must be visible"
    hit_rows = np.nonzero((d > 5).any(axis=1))[0]
    assert len(hit_rows) and 118 <= hit_rows.min() and hit_rows.max() <= 123, hit_rows

    # The plan tells the same story as the pixels.
    plan_after = plan_events(src, layer([{"op": "remove", "id": vid}]),
                             RenderOptions(seed=31, duration=2.0, scale=1.0))
    ids_after = {e["detail"]["id"] for e in plan_after["events"] if e["kind"] == "dropout"}
    assert vid not in ids_after and len(ids_after) == len(drops) - 1

    # An op whose id the seed no longer produces is skipped, never guessed at.
    other_seed = rendered([{"op": "remove", "id": "vhs:dropout:9999:7"}], "orphan")
    assert np.array_equal(other_seed, base[: len(other_seed)])


def test_every_window_plans_the_same_tape():
    """A preview window and the export must agree on every scheduled event.

    Schedules used to be drawn on the render's own noise tracks, and those
    tracks normalise over the render's length - so a three-second preview
    planned a different tape than the export, and an edit naming an exported
    storm's id was silently orphaned on screen. That is the bug that shipped as
    "editing tracking storms does nothing in the preview". Schedules now come
    from clip-timeline noise, and this holds every kind to it, window by window.
    """
    import subprocess

    import numpy as np

    from aesthetician.engine import Preset, RenderOptions, render
    from aesthetician.engine.render import Layer, plan_events

    root = os.path.join(os.path.dirname(__file__), "..")
    src = os.path.join(root, "out", "_t_win_in.mp4")
    os.makedirs(os.path.dirname(src), exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "testsrc2=size=320x240:rate=30:duration=9", "-c:v", "libx264",
         "-crf", "0", "-pix_fmt", "yuv420p", src], check=True)

    preset = Preset(id="t_win", name="t", family="t", era="", desc="",
                    video=[("vhs", {"tracking_error": 0.45, "dropouts": 3.0,
                                    "dropout_burst": 0.6, "skew_tear": 0.6}),
                           ("vcr_transport", {"start_glitch": False, "random_glitch_rate": 8.0})])
    layer = [Layer(preset=preset, seed=77)]
    full = plan_events(src, layer, RenderOptions(seed=77, scale=1.0))

    def keyset(plan, kinds):
        return sorted((e["kind"], round(e["t"], 3), round(e["dur"], 3), e["detail"]["id"])
                      for e in plan["events"] if e["kind"] in kinds)

    kinds = {"dropout", "tracking_storm", "skew_tear", "transport_glitch"}
    for t0 in (0.0, 2.0, 5.5):
        win = plan_events(src, layer, RenderOptions(seed=77, scale=1.0, t0=t0, duration=2.5))
        got = keyset(win, kinds)
        want = [k for k in keyset(full, kinds) if k[1] < t0 + 2.5 and k[1] + k[2] > t0]
        assert got == want, (t0, got[:3], want[:3])

    # And an edit named from the full plan lands inside a window's pixels.
    storm = next(e for e in full["events"] if e["kind"] == "tracking_storm")
    w0 = max(storm["t"] - 0.5, 0.0)
    base = os.path.join(root, "out", "_t_win_base.mp4")
    edit = os.path.join(root, "out", "_t_win_edit.mp4")
    render(src, base, preset, RenderOptions(seed=77, t0=w0, duration=2.0, scale=1.0, crf=0))
    render(src, edit, preset, RenderOptions(
        seed=77, t0=w0, duration=2.0, scale=1.0, crf=0,
        event_edits=[{"op": "remove", "kind": "tracking_storm", "id": storm["detail"]["id"]}]))
    W, H = 320, 240
    def gray(path):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo",
                              "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
        n = len(raw) // (W * H)
        return np.frombuffer(raw[: n * W * H], np.uint8).reshape(n, H, W).astype(np.int16)
    a, b = gray(base), gray(edit)
    assert np.abs(a[: len(b)] - b[: len(a)]).max() > 20, \
        "removing a full-plan storm must visibly change the window that contains it"


def test_tracking_storms_are_instances_with_teeth():
    """The shredded band is addressable: planned, removed, moved, added.

    Tracking error was continuous machinery with episodic results - a gate
    track crossing a threshold - so it never appeared in the plan and could not
    be edited. Now the runs are instances. The checks are physical: a banding
    metric (rows disagreeing sharply with their neighbours) must light up
    exactly where the plan says a storm is, go dark when the storm is removed,
    and light up on a preset whose dial is at zero when one is added there.
    """
    import subprocess

    import numpy as np

    from aesthetician.engine import Preset, RenderOptions, render
    from aesthetician.engine.render import Layer, plan_events

    root = os.path.join(os.path.dirname(__file__), "..")
    src = os.path.join(root, "out", "_t_storm_in.mp4")
    os.makedirs(os.path.dirname(src), exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "testsrc2=size=320x240:rate=30:duration=3", "-c:v", "libx264",
         "-crf", "0", "-pix_fmt", "yuv420p", src], check=True)

    quiet = {"luma_noise": 0, "chroma_noise": 0, "head_switch": 0, "time_base_error": 0,
             "flagging": 0, "jitter_v": 0, "sharpen": 0, "chroma_delay": 0,
             "dropouts": 0.0, "dropout_burst": 0.0, "skew_tear": 0}
    stormy = Preset(id="t_storm", name="t", family="t", era="", desc="",
                    video=[("vhs", {**quiet, "tracking_error": 0.55})])
    calm = Preset(id="t_calm", name="t", family="t", era="", desc="",
                  video=[("vhs", {**quiet, "tracking_error": 0.0})])
    opts = lambda edits=(): RenderOptions(seed=1234, duration=3.0, scale=1.0, crf=0,
                                          event_edits=list(edits))

    W, H = 320, 240
    def banded(path):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo",
                              "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
        n = len(raw) // (W * H)
        v = np.frombuffer(raw[: n * W * H], np.uint8).reshape(n, H, W).astype(np.float32)
        d = np.abs(np.diff(v, axis=1)).mean(axis=2)
        return (d > 14).sum(axis=1)          # shredded rows per frame

    a = os.path.join(root, "out", "_t_storm_base.mp4")
    render(src, a, stormy, opts())
    plan = plan_events(src, [Layer(preset=stormy, seed=1234)], opts())
    storms = [e for e in plan["events"] if e["kind"] == "tracking_storm"]
    assert storms, "tracking 0.55 over three seconds must produce at least one storm"
    fps = plan["fps"]
    rows = banded(a)
    storm_frames = set()
    for e in storms:
        f0 = int(round(e["t"] * fps))
        storm_frames.update(range(f0, min(f0 + int(round(e["dur"] * fps)), len(rows))))
    # The banding lives inside the planned storms and nowhere else.
    outside = [i for i in range(len(rows)) if rows[i] > 25 and i not in storm_frames]
    assert outside == [], f"shredding outside every planned storm: {outside}"
    assert max(rows[i] for i in storm_frames) > 25, "a planned storm must actually shred"

    # Removing every storm calms the tape to the dial-at-zero picture.
    b = os.path.join(root, "out", "_t_storm_removed.mp4")
    render(src, b, stormy, opts([{"op": "remove", "kind": "tracking_storm",
                                  "id": e["detail"]["id"]} for e in storms]))
    assert max(banded(b)) <= 25, "removed storms must leave no shredding behind"

    # An added storm shreds a preset whose dial is at zero, where it was asked to.
    c = os.path.join(root, "out", "_t_storm_added.mp4")
    render(src, c, calm, opts([{"op": "add", "kind": "tracking_storm", "t": 1.0,
                                "detail": {"dur_s": 0.5, "intensity": 0.9}}]))
    rows_c = banded(c)
    hot = {i for i in range(len(rows_c)) if rows_c[i] > 25}
    want = set(range(int(1.0 * fps), int(1.5 * fps) + 1))
    assert hot and hot <= want, f"added storm landed at frames {sorted(hot)}, wanted within {sorted(want)}"

    # And the plan agrees about the addition, dial at zero notwithstanding.
    plan_c = plan_events(src, [Layer(preset=calm, seed=1234,
                                     event_edits=[{"op": "add", "kind": "tracking_storm",
                                                   "t": 1.0, "detail": {"dur_s": 0.5, "intensity": 0.9}}])],
                         opts())
    got = [e for e in plan_c["events"] if e["kind"] == "tracking_storm"]
    assert len(got) == 1 and abs(got[0]["t"] - 1.0) < 0.05, got


def test_bands_pin_where_the_tape_roamed():
    """band_pos/band_height place an instance's damage on the picture.

    The tape decides by default - the rolling tracking band, the near-the-top
    tear, the whole-frame transport shred - and a pinned instance overrides
    that alone: 0 hugs the top edge, 1 the bottom, height is a share of the
    frame. Checked physically per kind by diffing an edited render against the
    same preset untouched and reading where the disturbed rows sit. Also holds
    the fix that adds land on presets whose dial sits at zero (tears and
    dropouts had the storm bug), and that the plan reports pins back with null
    meaning auto.
    """
    import subprocess

    import numpy as np

    from aesthetician.engine import Preset, RenderOptions, render
    from aesthetician.engine.render import Layer, plan_events

    root = os.path.join(os.path.dirname(__file__), "..")
    src = os.path.join(root, "out", "_t_band_in.mp4")
    os.makedirs(os.path.dirname(src), exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "testsrc2=size=320x240:rate=30:duration=3", "-c:v", "libx264",
         "-crf", "0", "-pix_fmt", "yuv420p", src], check=True)

    quiet = {"luma_noise": 0, "chroma_noise": 0, "head_switch": 0, "time_base_error": 0,
             "flagging": 0, "jitter_v": 0, "sharpen": 0, "chroma_delay": 0,
             "dropouts": 0.0, "dropout_burst": 0.0, "skew_tear": 0, "tracking_error": 0.0}
    calm = Preset(id="t_band_c", name="t", family="t", era="", desc="",
                  video=[("vhs", quiet)])
    deck = Preset(id="t_band_t", name="t", family="t", era="", desc="",
                  video=[("vcr_transport", {"start_glitch": False, "random_glitch_rate": 0.0})])
    opts = lambda edits=(): RenderOptions(seed=1234, duration=3.0, scale=1.0, crf=0,
                                          event_edits=list(edits))

    W, H = 320, 240
    def frames(path):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo",
                              "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
        n = len(raw) // (W * H)
        return np.frombuffer(raw[: n * W * H], np.uint8).reshape(n, H, W).astype(np.float32)

    def hot_rows(edited, base, f0, f1):
        d = np.abs(frames(edited)[f0:f1] - frames(base)[f0:f1]).mean(axis=(0, 2))
        rows = np.nonzero(d > max(d.max() * 0.25, 2.0))[0]
        assert len(rows), "the edit must disturb some rows"
        return int(rows.min()), int(rows.max())

    base_c = os.path.join(root, "out", "_t_band_base_c.mp4")
    base_t = os.path.join(root, "out", "_t_band_base_t.mp4")
    render(src, base_c, calm, opts())
    render(src, base_t, deck, opts())

    def rendered(tag, preset, edits):
        out = os.path.join(root, "out", f"_t_band_{tag}.mp4")
        render(src, out, preset, opts(edits))
        return out

    # A storm pinned near the top vs near the bottom of the frame. Band height
    # 0.15 of 240 is 36 px; centers land at bh/2 + pos*(H-bh) = 38 and 202.
    for tag, pos, center in (("st_top", 0.1, 38), ("st_bot", 0.9, 202)):
        out = rendered(tag, calm,
                       [{"op": "add", "kind": "tracking_storm", "t": 1.0,
                         "detail": {"dur_s": 0.6, "intensity": 0.9,
                                    "band_pos": pos, "band_height": 0.15}}])
        lo, hi = hot_rows(out, base_c, 32, 46)
        assert center - 45 < lo and hi < center + 45, \
            f"storm pos={pos}: rows {lo}..{hi} not around {center}"

    # A transport glitch banded low on a deck that coughs nowhere on its own.
    out = rendered("gl_low", deck,
                   [{"op": "add", "kind": "transport_glitch", "t": 1.0,
                     "detail": {"dur_s": 0.6, "intensity": 1.0,
                                "band_pos": 0.85, "band_height": 0.2}}])
    lo, hi = hot_rows(out, base_t, 32, 46)
    assert lo > H * 0.55, f"banded glitch must stay low, disturbed {lo}..{hi}"

    # A tear pinned mid-frame on a dial at zero - both halves were bugs: the
    # tape's own tears sit at 3-14% from the top, and a zero dial used to
    # swallow added tears (and added dropouts) entirely.
    out = rendered("tear_mid", calm,
                   [{"op": "add", "kind": "skew_tear", "t": 1.0,
                     "detail": {"intensity": 1.5, "band_pos": 0.6, "band_height": 0.05}}])
    lo, hi = hot_rows(out, base_c, 30, 32)
    assert H * 0.45 < lo and hi < H * 0.75, f"pinned tear at rows {lo}..{hi}, wanted mid-frame"

    out = rendered("drop_zero", calm,
                   [{"op": "add", "kind": "dropout", "t": 1.0,
                     "detail": {"row": 120, "x": 40, "length_px": 200}}])
    lo, hi = hot_rows(out, base_c, 30, 31)
    assert 110 <= lo and hi <= 130, f"added dropout on a zero dial at rows {lo}..{hi}"

    # Tuning a band onto one of the tape's own storms moves that storm's band.
    stormy = Preset(id="t_band_s", name="t", family="t", era="", desc="",
                    video=[("vhs", {**quiet, "tracking_error": 0.55})])
    plan = plan_events(src, [Layer(preset=stormy, seed=1234)], opts())
    st = next(e for e in plan["events"] if e["kind"] == "tracking_storm")
    assert st["detail"]["band_pos"] is None and st["detail"]["band_height"] is None, \
        "an untouched storm must report auto placement"
    tune = [{"op": "tune", "kind": "tracking_storm", "id": st["detail"]["id"],
             "detail": {"band_pos": 0.9, "band_height": 0.12}}]
    out = rendered("st_tune", stormy, tune)
    fps = plan["fps"]
    f0 = int(round(st["t"] * fps))
    f1 = min(f0 + int(round(st["dur"] * fps)), 89)
    # Against the calm render, which differs from stormy only by the tracking
    # dial: inside this storm's frames every disturbed row is the tuned band's
    # own, not the union with wherever the tape's rolling band used to be.
    lo, hi = hot_rows(out, base_c, f0, f1)
    assert lo > H * 0.5, f"tuned band must sit low, disturbed {lo}..{hi}"

    # And the plan hands the pin back - then null hands it back to the tape.
    plan2 = plan_events(src, [Layer(preset=stormy, seed=1234, event_edits=tune)], opts())
    st2 = next(e for e in plan2["events"] if e["detail"]["id"] == st["detail"]["id"])
    assert st2["detail"]["band_pos"] == 0.9 and st2["detail"]["band_height"] == 0.12, st2
    clear = tune + [{"op": "tune", "kind": "tracking_storm", "id": st["detail"]["id"],
                     "detail": {"band_pos": None, "band_height": None}}]
    plan3 = plan_events(src, [Layer(preset=stormy, seed=1234, event_edits=clear)], opts())
    st3 = next(e for e in plan3["events"] if e["detail"]["id"] == st["detail"]["id"])
    assert st3["detail"]["band_pos"] is None and st3["detail"]["band_height"] is None, st3


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


def test_interlaced_codec_era_survives_an_ffmpeg_without_top():
    """codec_era's interlaced mode must not lean on the removed -top option.

    Tapes to DVD asks MPEG-2 for real top-field-first structure, which used to
    be requested with `-top 1`. ffmpeg 8 removed that CLI option, so on the
    ffmpeg the app bundles the flag falls through to the codec AVOption `top`
    - decode-only - and the whole encode is refused ("is not a encoding
    option"). Field order is now flagged per-frame with setparams, which both
    old and new builds understand. This runs the real file pass, checks no
    command asks for -top, and reads the flags back out of the frames the
    encoder produced - the genuine field structure is the preset's point.
    """
    import subprocess

    from aesthetician.engine import media
    from aesthetician.engine.graph import Context, get_effect

    root = os.path.join(os.path.dirname(__file__), "..")
    out_dir = os.path.join(root, "out")
    os.makedirs(out_dir, exist_ok=True)
    src = os.path.join(out_dir, "_t_ilace_src.mp4")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "testsrc2=size=192x144:rate=30:duration=1",
         "-pix_fmt", "yuv420p", src], check=True)

    cmds: list[list[str]] = []
    frame_flags: list[str] = []
    real_run = media._run

    def spy(cmd, **kw):
        cmds.append(cmd)
        proc = real_run(cmd, **kw)
        if cmd[-1].endswith(".nut"):  # the intermediates are gone by the end
            got = real_run(
                [media.FFPROBE, "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "frame=interlaced_frame,top_field_first",
                 "-of", "csv=p=0", cmd[-1]])
            frame_flags.extend(got.stdout.decode().split())
        return proc

    ctx = Context(width=192, height=144, fps=30.0, n_frames=30, seed=1)
    eff = get_effect("codec_era")(codec="mpeg2video", kbps=4200, gop=15,
                                  passes=2, field_mode="interlaced_tff")
    eff.resolve(ctx)
    eff.prepare(ctx)
    out = os.path.join(out_dir, "_t_ilace_out.mp4")
    media._run = spy
    try:
        eff.file_pass(src, out, ctx)
    finally:
        media._run = real_run

    encodes = [c for c in cmds if c[-1].endswith(".nut")]
    assert len(encodes) == 2, [c[-1] for c in encodes]
    for cmd in encodes:
        assert "-top" not in cmd, "ffmpeg 8+ has no -top; TFF comes from setparams"
        assert "+ilme+ildct" in cmd, cmd
        assert "setparams=field_mode=tff" in cmd[cmd.index("-vf") + 1], cmd
    # Both generations, every frame: interlaced and top field first.
    assert frame_flags and all(f.startswith("1,1") for f in frame_flags), frame_flags[:4]
    assert media.probe(out).n_frames >= 28


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
    # The one-frame render used to be dramatically worse, because tracking
    # storms normalised against the render length. Clip-timeline scheduling
    # fixed that on purpose, so the residual gap is only the continuous look
    # tracks (time-base error, flagging) - small, but it must not vanish: if
    # these two ever match, someone has made the still path stop rendering the
    # same wobbles, and the sharp statement of the underlying mechanism lives
    # in test_temporal_tracks_need_the_real_length.
    assert one_err > kept_err * 1.02, (
        f"a one-frame render came out as close as the real thing "
        f"({one_err:.2f} vs {kept_err:.2f}) - has the still path stopped rendering wobbles?"
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
