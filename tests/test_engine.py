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


def test_source_preserving_aesthetic_collection_contract():
    """The requested historical collection must never become an edit preset.

    These looks may model the camera, stock, carrier, transfer, and playback,
    but the user's frames, timing, graphics, and programme audio remain theirs.
    Keep this guard close to the registry count check so adding a tempting
    editorial effect fails before a release is packaged.
    """
    from aesthetician.engine.presets import all_presets

    collection = {
        pid: preset
        for pid, preset in all_presets().items()
        if "source-preserving" in preset.tags
    }
    assert len(collection) == 138, sorted(collection)
    assert all(pid.startswith("auth-") for pid in collection), sorted(collection)

    forbidden_video = {
        "cadence", "animate_on", "frame_damage", "codec_glitch",
        "vcr_transport", "changeover", "tape_junk", "framing",
        "captions", "osd", "timestamp",
    }
    forbidden_audio = {
        "a_gain", "a_bed", "a_projector", "a_cd_skip", "a_needle",
        "a_digital_glitch", "a_dat_error", "a_8track",
    }

    for pid, preset in collection.items():
        video_keys = {effect for effect, _ in preset.video}
        audio_keys = {effect for effect, _ in preset.audio}
        assert preset.video, f"{pid} has no capture/medium treatment"
        assert preset.audio, f"{pid} has no period-appropriate audio treatment"
        assert not video_keys & forbidden_video, (pid, video_keys & forbidden_video)
        assert not audio_keys & forbidden_audio, (pid, audio_keys & forbidden_audio)

        # A variant cannot smuggle a forbidden effect back into the chain.
        for variant in preset.variants:
            variant_video = {path.split(".", 1)[0].split("#", 1)[0]
                             for path in variant.video}
            variant_audio = {path.split(".", 1)[0].split("#", 1)[0]
                             for path in variant.audio}
            assert not variant_video & forbidden_video, (pid, variant.id, variant_video)
            assert not variant_audio & forbidden_audio, (pid, variant.id, variant_audio)


def test_legacy_matches_offer_source_clean_transfers():
    """Existing matches with incidental loss/masking expose a neutral carrier variant."""
    from aesthetician.engine.presets import all_presets

    expected = {
        "neorealismo-1948": {
            "frame_damage.splice_skip_rate": 0.0,
            "frame_damage.slip_rate": 0.0,
            "frame_damage.blotch_rate": 0.0,
            "frame_damage.static_flash": 0.0,
            "frame_damage.burn": False,
        },
        "golf-sunday-1977": {"framing.corner_radius": 0.0},
        "talk-show-1984": {"framing.corner_radius": 0.0},
        "game-show-1978": {"framing.corner_radius": 0.0},
        "fitness-vhs-1984": {"a_video_tape_audio.dropout_rate": 0.0},
        "corporate-umatic-1988": {"a_video_tape_audio.dropout_rate": 0.0},
        "tabloid-reenactment-1992": {"a_video_tape_audio.dropout_rate": 0.0},
        "local-cable-infomercial-1997": {"a_video_tape_audio.dropout_rate": 0.0},
        "wedding-master-1991": {"a_tape_dropouts.rate": 0.0},
        "vhs-dub-generation": {"a_tape_dropouts.rate": 0.0},
    }

    presets = all_presets()
    for pid, overrides in expected.items():
        variant = presets[pid].variant("source-clean")
        authored = {**variant.video, **variant.audio}
        assert authored.items() >= overrides.items(), (pid, authored)

    # Their aspect treatment is matte-box only: it retains every source pixel.
    for pid in ("golf-sunday-1977", "talk-show-1984", "game-show-1978"):
        framing = next(params for eid, params in presets[pid].video if eid == "framing")
        assert framing.get("mode", "box") == "box" and framing.get("zoom", 0.0) == 0.0


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


def test_aac_codec_is_real_mono_capable_and_fails_soft():
    """Modern source presets use native AAC, not an EQ approximation.

    Exercise the real encode/decode leg and its channel control, then remove
    AAC from the reported encoder inventory and prove that an unusually small
    ffmpeg build copies the source rather than aborting the render.
    """
    import subprocess

    from aesthetician.engine import media
    from aesthetician.effects.audio import digicodec

    root = os.path.join(os.path.dirname(__file__), "..")
    out_dir = os.path.join(root, "out")
    os.makedirs(out_dir, exist_ok=True)
    src = os.path.join(out_dir, "_t_aac_src.wav")
    encoded = os.path.join(out_dir, "_t_aac_roundtrip.wav")
    copied = os.path.join(out_dir, "_t_aac_fallback.wav")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "sine=f=733:sample_rate=48000:duration=1.03", "-ac", "2",
         "-c:a", "pcm_s24le", src], check=True,
    )

    ctx = Context(width=64, height=48, fps=30.0, n_frames=31, sr=48000, channels=2)
    effect = get_effect("a_codec_aac")(kbps=64, mono=True)
    effect.resolve(ctx)
    effect.prepare(ctx)
    assert effect._usable, "AAC is a required encoder in the supported ffmpeg build"
    effect.file_pass(src, encoded, ctx)
    got = media.probe(encoded)
    assert got.has_audio and got.channels == 1, got
    assert abs(got.duration - 1.03) < 0.04, got.duration

    real = digicodec._available_encoders
    digicodec._available_encoders = lambda: frozenset()
    try:
        fallback = get_effect("a_codec_aac")(kbps=128, mono=False)
        fallback.resolve(ctx)
        fallback.prepare(ctx)
        assert fallback._usable is False
        fallback.file_pass(src, copied, ctx)
        with open(src, "rb") as before, open(copied, "rb") as after:
            assert before.read() == after.read(), "missing AAC must be a byte-for-byte pass-through"
    finally:
        digicodec._available_encoders = real


def test_audio_effects_hand_back_the_block_they_were_given():
    """An audio effect must return exactly the samples it was passed.

    The telephone's mu-law trip down to 8 kHz and back rounds its length up on
    both legs, so a block that isn't a whole number of 8 kHz frames comes home
    a sample or two long - 1441600 samples in, 1441602 out. Everything built
    against the length we came in with (the line hum, the FM hiss, the exchange
    bed) then refuses to broadcast onto it, and the export dies mid-render with
    a numpy shape error. Five of the six telephone eras, on five of every six
    durations. The contract belongs to the whole chain, not to one effect: the
    next effect downstream is handed this buffer and does its own arithmetic
    against its length, so sweep every audio effect at an awkward length.
    """
    import numpy as np

    from aesthetician.engine.graph import Context, all_effects, get_effect

    sr = 48000
    n = 96001  # ~2 s, and deliberately not a multiple of the 6:1 48k/8k ratio
    ctx = Context(width=64, height=48, fps=30.0, n_frames=60, seed=3, sr=sr)
    audio = ((np.random.default_rng(1).random((n, 2)).astype(np.float32) - 0.5) * 0.2)

    checked, skipped, broke = 0, [], []
    for eid, cls in sorted(all_effects().items()):
        if cls.kind != "audio":
            continue
        eff = get_effect(eid)()
        eff.resolve(ctx)
        try:
            eff.prepare(ctx)
        except RuntimeError as exc:
            skipped.append(f"{eid}: {exc}")  # vetted below
            continue
        checked += 1
        try:
            out = eff.process_audio(audio.copy(), ctx)
        except Exception as exc:
            broke.append(f"{eid}: {type(exc).__name__}: {exc}")
            continue
        if out.shape != audio.shape or out.dtype != np.float32:
            broke.append(f"{eid}: gave back {out.shape} {out.dtype}, was handed "
                         f"{audio.shape} float32")
    # An ambience bed with nothing baked to play is a missing asset, which is a
    # different problem with a different answer - assets/ is gitignored, so a
    # runner has none of it. Anything else out of prepare is a real failure.
    for note in skipped:
        assert "bake_audio_beds" in note, f"prepare failed for a real reason: {note}"
    assert checked > 30, f"only {checked} audio effects swept - the filter is wrong"
    assert broke == [], f"{len(broke)} audio effects change the block: {broke[:4]}"

    # Every telephone era, with the extras that index against n switched on,
    # at a second awkward length: 3 s at 48k plus five stray samples.
    block = np.resize(audio, (144005, 2)).astype(np.float32)
    for era in get_effect("a_telephone")._ERAS:
        eff = get_effect("a_telephone")(era=era, exchange_noise=0.6, sidetone_click=True)
        eff.resolve(ctx)
        out = eff.process_audio(block.copy(), ctx)
        assert out.shape == block.shape, f"{era}: {out.shape} from {block.shape}"
        assert np.isfinite(out).all() and float(np.abs(out).max()) > 1e-4, \
            f"{era}: silence or NaN, so the shape check proves nothing"


def test_archive_audio_effects_are_repeatable_and_configurable():
    """The archival controls do real, deterministic DSP without changing length."""
    from aesthetician.engine.graph import Context, get_effect

    sr = 24000
    n = sr * 3 + 17
    t = np.arange(n, dtype=np.float32) / sr
    source = np.stack([
        0.18 * np.sin(2 * np.pi * 93.0 * t) + 0.12 * np.sin(2 * np.pi * 2800.0 * t),
        0.15 * np.sin(2 * np.pi * 131.0 * t) + 0.1 * np.sin(2 * np.pi * 6100.0 * t),
    ], axis=1).astype(np.float32)
    source[::4000] += 0.4
    cases = {
        "a_historical_mic": {"profile": "carbon_1925", "amount": 1.0,
                             "overload": 0.5, "self_noise_db": -48.0, "handling": 0.8},
        "a_disc_medium": {"medium": "wax_cylinder_1905", "wear": 0.7,
                          "surface_db": -40.0, "impacts": 40.0, "wow_cents": 20.0},
        "a_analog_dub": {"format": "cassette", "generations": 4,
                         "alignment": 0.7, "compression": 0.6, "hiss_db": -48.0},
        "a_print_through": {"delay_s": 0.25, "pre_echo_db": -30.0,
                            "post_echo_db": -34.0, "layers": 2, "softness": 0.7},
        "a_noise_reduction": {"system": "dolby_c", "decode_error": 0.8,
                              "pumping": 0.7, "hiss_db": -48.0},
        "a_video_tape_audio": {"format": "vhs_hifi", "tracking": 0.8,
                               "dropout_rate": 40.0, "noise_db": -45.0,
                               "head_switch_db": -48.0, "compander_error": -0.6},
        "a_channel_aging": {"width": 0.3, "imbalance_db": -3.0,
                            "crosstalk_db": -18.0, "skew_us": 700.0,
                            "phase_wander": 0.8, "mono_bass_hz": 300.0},
    }
    for eid, params in cases.items():
        ctx = Context(64, 48, 24.0, 72, sr=sr, channels=2, seed=37)
        eff = get_effect(eid)(**params)
        eff.resolve(ctx)
        out = eff.process_audio(source.copy(), ctx)
        assert out.shape == source.shape and out.dtype == np.float32, eid
        assert np.isfinite(out).all(), eid
        assert float(np.sqrt(np.mean((out - source) ** 2))) > 1e-4, f"{eid} did nothing"

        again = get_effect(eid)(**params)
        again.resolve(ctx)
        assert np.array_equal(out, again.process_audio(source.copy(), ctx)), eid


def test_new_archive_presets_are_audio_only_and_score_free():
    """Archive presets treat the supplied program without authoring picture or music."""
    from aesthetician.engine.graph import all_effects
    from aesthetician.engine.presets import all_presets

    wanted = {
        "audio-wax-cylinder-1905", "audio-wax-dictation-1922",
        "audio-aluminum-disc-1934", "audio-acetate-home-1947",
        "audio-ribbon-studio-1938", "audio-carbon-newsreel-1941",
        "audio-full-track-master-1953", "audio-magnetic-film-1957",
        "audio-broadcast-reel-1961", "audio-portable-reel-1965",
        "audio-16mm-mag-stripe-1969", "audio-nagra-location-1970",
        "audio-dictation-belt-1964", "audio-broadcast-cart-1976",
        "audio-cassette-field-1979", "audio-boombox-dub-1983",
        "audio-cassette-fourtrack-1987", "audio-umatic-linear-1977",
        "audio-betamax-linear-1981", "audio-vhs-linear-1985",
        "audio-betamax-hifi-1985", "audio-vhs-hifi-1988",
        "audio-video8-afm-1991", "audio-camcorder-onboard-1994",
        "audio-hi8-stereo-1996",
    }
    presets = all_presets()
    assert wanted <= presets.keys()
    assert len(wanted) == 25
    for pid in wanted:
        preset = presets[pid]
        assert preset.family == "audio" and preset.video == [], pid
        assert preset.audio, pid
        assert all(eid.startswith("a_") for eid, _ in preset.audio), pid
    assert all("score" not in eid and "music" not in eid for eid in all_effects())


def test_new_audiovisual_presets_treat_picture_and_supplied_sound():
    """The new era looks process both sections without authoring program material."""
    from aesthetician.engine.presets import all_presets

    wanted = {
        "vitaphone-palace-1929", "precode-studio-print-1932",
        "cinecolor-travel-print-1948", "anscochrome-pageant-1954",
        "vistavision-release-1956", "todd-ao-roadshow-1958",
        "hammer-eastmancolor-1960", "techniscope-blowup-1966",
        "supermarionation-print-1966", "psychedelic-optical-1968",
        "panavision-disaster-print-1974", "slasher-answer-print-1980",
        "quadruplex-variety-1958", "regional-weather-1973",
        "disco-variety-master-1979", "cband-superstation-1982",
        "fitness-vhs-1984", "home-shopping-cable-1987",
        "music-countdown-master-1987", "corporate-umatic-1988",
        "tabloid-reenactment-1992", "cdrom-mjpeg-1995",
        "local-cable-infomercial-1997", "digicam-mjpeg-2002",
    }
    presets = all_presets()
    assert len(wanted) == 24
    assert wanted <= presets.keys()
    for pid in wanted:
        preset = presets[pid]
        assert preset.family != "audio", pid
        assert preset.video, f"{pid} has no picture chain"
        assert preset.audio, f"{pid} has no sound chain"
        assert all(eid.startswith("a_") for eid, _ in preset.audio), pid


def test_optical_composite_and_color_switches_are_live():
    """New optical and color dials have real zero stops and visible active states."""
    from aesthetician.engine.graph import Context, get_effect

    ctx = Context(160, 120, 24.0, 48, seed=9)
    frame = np.random.default_rng(4).random((120, 160, 3)).astype(np.float32)

    flat = get_effect("optical_composite")()
    flat.resolve(ctx)
    flat.prepare(ctx)
    assert flat.process(frame.copy(), ctx) is not None
    assert np.array_equal(flat.process(frame.copy(), ctx), frame)

    active = get_effect("optical_composite")(softness=0.4, matte_line=0.6, registration=0.8,
                                               layer_haze=0.2, density_breath=0.3)
    active.resolve(ctx)
    active.prepare(ctx)
    treated = active.process(frame.copy(), ctx)
    assert float(np.abs(treated - frame).mean()) > 0.005

    mono_off = get_effect("mono")(amount=0.0)
    mono_off.resolve(ctx)
    assert np.array_equal(mono_off.process(frame.copy(), ctx), frame)
    mono_on = get_effect("mono")(amount=1.0)
    mono_on.resolve(ctx)
    assert not np.array_equal(mono_on.process(frame.copy(), ctx), frame)

    sixties = get_effect("stock")(profile="eastman_60s")
    eighties = get_effect("stock")(profile="kodak_80s")
    sixties.resolve(ctx)
    eighties.resolve(ctx)
    assert not np.allclose(sixties.process(frame.copy(), ctx), eighties.process(frame.copy(), ctx))


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


def test_h264_codec_era_keeps_bitrate_and_crf_modes_distinct():
    """libx264 must receive bitrate or CRF control, never an accidental mix."""
    ctx = Context(width=192, height=144, fps=30.0, n_frames=30, seed=1)

    bitrate = get_effect("codec_era")(
        codec="h264", kbps=2800, qscale=19, crf=-1, gop=48,
    )
    bitrate.resolve(ctx)
    bargs = bitrate._codec_args("h264", None)
    assert bargs[bargs.index("-c:v") + 1] == "libx264", bargs
    assert bargs[bargs.index("-b:v") + 1] == "2800k", bargs
    assert "-maxrate" in bargs and "-bufsize" in bargs, bargs
    assert "-crf" not in bargs and "-q:v" not in bargs, bargs

    constant_quality = get_effect("codec_era")(
        codec="h264", kbps=2800, qscale=19, crf=22, gop=48,
    )
    constant_quality.resolve(ctx)
    cargs = constant_quality._codec_args("h264", None)
    assert cargs[cargs.index("-crf") + 1] == "22", cargs
    assert "-b:v" not in cargs and "-maxrate" not in cargs, cargs
    assert "-q:v" not in cargs, cargs

    lossless = get_effect("codec_era")(codec="h264", crf=0)
    lossless.resolve(ctx)
    largs = lossless._codec_args("h264", None)
    assert largs[largs.index("-crf") + 1] == "0", largs
    assert "-profile:v" not in largs, "plain High rejects x264 lossless"


def test_source_modern_uses_avc_aac_without_rewriting_earlier_web_codecs():
    """2010s carriers are AVC/AAC; Flash, ASP and HDV remain of their time."""
    from aesthetician.engine.presets import all_presets

    presets = all_presets()
    avc_aac = {
        "auth-anime-web-fansub-encode-2006",
        "auth-dslr-indie-naturalism-2012",
        "auth-gopro-action-footage-2014",
        "auth-body-camera-evidence-2017",
        "auth-dashcam-archive-2015",
        "auth-doorbell-camera-night-2018",
        "auth-streaming-true-crime-2017",
        "auth-square-social-filter-2013",
        "auth-asmr-close-mic-2018",
    }
    for pid in avc_aac:
        preset = presets[pid]
        video = dict(preset.video)
        audio_ids = {eid for eid, _ in preset.audio}
        assert video["codec_era"]["codec"] == "h264", (pid, video["codec_era"])
        assert "a_codec_aac" in audio_ids and "a_codec_mp3" not in audio_ids, (pid, audio_ids)

    period_carriers = {
        "auth-early-youtube-webcam-2006": ("flv1", "a_codec_mp3"),
        "auth-machinima-web-series-2005": ("mpeg4", "a_codec_mp3"),
        "auth-food-network-studio-2005": ("mpeg2video", "a_codec_mp3"),
        "auth-live-truck-local-news-2004": ("mpeg2video", "a_codec_mp3"),
    }
    for pid, (codec, audio_codec) in period_carriers.items():
        preset = presets[pid]
        assert dict(preset.video)["codec_era"]["codec"] == codec, pid
        assert audio_codec in {eid for eid, _ in preset.audio}, pid


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


def test_caption_text_primitives_hold_their_guarantees():
    """wrap_lines, reveal_chars and hex_rgb: the primitives every caption face bottoms out on.

    wrap_lines has to keep every character somewhere - a caption editor cannot silently eat
    text - and reveal_chars has to only ever grow as more of a cue is typed on, since typewriter
    and paint_on sample it fresh every frame and a mask that shrank would flicker backwards.
    hex_rgb is the one place a caption color string meets a parser a form can feed anything to.
    """
    from aesthetician.engine.text import hex_rgb, render_block, reveal_chars, wrap_lines

    # Manual newlines are paragraph breaks, never rewrapped.
    assert wrap_lines("HELLO\nWORLD", 32) == ["HELLO", "WORLD"]
    # Wrapping honors the width...
    wide = "a b c d e f g h i j k l m n o p q r s t"
    wrapped = wrap_lines(wide, 10)
    assert all(len(line) <= 10 for line in wrapped), wrapped
    # ...and drops no word, whitespace aside.
    assert " ".join(wrapped).split() == wide.split()
    # A single word longer than the width is force-split, not dropped or truncated.
    long_word = "supercalifragilisticexpialidocious"
    assert "".join(wrap_lines(long_word, 8)) == long_word
    # No text at all is a line, not a crash.
    assert wrap_lines("", 10) == [""]

    blk = render_block("HELLO WORLD FOO", font="mono", line_h=20, line_chars=8, align="left")
    sums = [int(reveal_chars(blk, n).sum()) for n in range(blk.n_chars + 1)]
    assert all(b >= a for a, b in zip(sums, sums[1:])), "reveal must never shrink as n grows"
    assert sums[0] == 0 and sums[-1] > 0, sums
    # Asking for more characters than the block has snaps to the whole frame - a safety net for
    # a caller racing past a cue's own length, not another step of the per-character reveal.
    assert reveal_chars(blk, blk.n_chars + 5).sum() == blk.h * blk.w

    # An empty cue has to rasterize to something sane, not raise.
    empty = render_block("", font="sans", line_h=16)
    assert empty.n_chars == 0
    assert empty.rgb.shape[:2] == empty.alpha.shape
    assert reveal_chars(empty, 0).sum() == 0

    assert hex_rgb("FFCC00") == (1.0, 0.8, 0.0)
    assert hex_rgb("#fc0") == (1.0, 0.8, 0.0)
    assert hex_rgb("garbage") == (1.0, 1.0, 1.0)
    assert hex_rgb("not-a-color", fallback=(0.0, 0.0, 0.0)) == (0.0, 0.0, 0.0)


def test_caption_lines_wrap_even_instead_of_greedy():
    """Two-line captions come out balanced, the way a subtitle house would set them.

    Greedy wrapping packs the first line to the wrap width and drops whatever is left onto the
    second, which is how you get a full line over a two-word stub - the single most common thing
    that makes a burned-in subtitle look homemade. The layout has to be even instead, without
    ever exceeding the width or losing a character, and without rewrapping across the manual
    newlines a writer put in on purpose.
    """
    from aesthetician.engine.text import wrap_lines

    line = "The night train is late again tonight"     # 37 chars, wraps at 24
    lines = wrap_lines(line, 24)
    assert len(lines) == 2, lines
    assert all(len(s) <= 24 for s in lines), lines
    # Greedy would give a 24 and a 12; even beats lopsided by a wide margin.
    assert abs(len(lines[0]) - len(lines[1])) <= 6, lines
    assert " ".join(lines).split() == line.split(), lines

    # Text that already fits is one line - balancing must never split for its own sake.
    assert wrap_lines("Short enough", 32) == ["Short enough"]
    # A hand-broken cue keeps the breaks it was given.
    assert wrap_lines("- Who's there?\n- Nobody.", 40) == ["- Who's there?", "- Nobody."]


def test_caption_edges_hug_the_letterform_and_stay_inside_the_block():
    """The rim follows the glyph at a fixed distance, and nothing spills off the canvas.

    The outline used to be an iterated 3x3 max-filter, which is a *square* structuring element:
    every round letter came out with right-angled corners on its rim, and at small sizes that
    reads as the caption being cut out of cardboard. It is a distance field now, so the rim is
    the same width in every direction - which is exactly what this measures, out from the corner
    of a stem along an axis and then along the diagonal at the same reach.

    The second half is the padding: edge treatments grow the block, and a rim or shadow clipped
    by the canvas it was drawn on would show up as a straight cut through the lettering once it
    was composited.
    """
    from aesthetician.engine.text import render_block

    line_h, es = 60, 1.0
    blk = render_block("H", font="sans_bold", line_h=line_h, edge="outline", edge_strength=es,
                       color=(1.0, 1.0, 1.0))
    r = int(round(line_h * (0.045 + 0.075 * es)))
    x0, y0, _x1, _y1 = blk.ink
    assert blk.alpha[y0, x0] > 0.5, "the ink box should start on ink"
    # Straight out from the corner of the stem, well inside the rim's reach: solid.
    assert blk.alpha[y0, x0 - (r - 2)] > 0.9, "no rim to the left of the stem"
    assert blk.alpha[y0 - (r - 2), x0] > 0.9, "no rim above the stem"
    # Diagonally out at the full reach the rim has fallen away, because it is a distance from
    # the letter rather than a box drawn around it. A square dilate lights this pixel.
    assert blk.alpha[y0 - r, x0 - r] < 0.1, "the rim has square corners"

    # A blurred shadow has an infinite tail, so the bar is what an 8-bit composite can
    # actually carry: nothing on the border may survive quantization.
    for edge in ("outline", "shadow", "outline_shadow", "glow"):
        b = render_block("Hg", font="serif", line_h=48, edge=edge, edge_strength=1.0)
        border = np.concatenate([b.alpha[0], b.alpha[-1], b.alpha[:, 0], b.alpha[:, -1]])
        assert border.max() < 1.0 / 255.0, f"{edge} runs off the edge of its own block"


def test_captions_are_a_true_no_op_with_no_cues():
    """A captions effect with nothing to draw must be invisible, not just quiet.

    Cues live entirely in event edits (docs/events.md), so an empty edit list is the ordinary
    state of every render nobody has touched yet - the same state a preset was in before
    captions existed at all. `process` has to answer that with the identical frame object, not
    a frame that merely looks the same, and a real render has to answer it with identical bytes
    no matter what the style knobs say, since none of them can matter without a cue to apply
    them to.
    """
    import hashlib
    import subprocess

    import numpy as np

    from aesthetician.engine import RenderOptions, render
    from aesthetician.engine.presets import get_preset

    # The cheapest form of the claim: no cues means process() never touches the frame at all.
    ctx = Context(64, 48, 30.0, 10, seed=1)
    eff = get_effect("captions")()
    eff.resolve(ctx)
    eff.prepare(ctx)
    frame = np.random.default_rng(0).random((48, 64, 3)).astype(np.float32)
    ctx.fi_out = 0
    assert eff.process(frame, ctx) is frame, "a cueless effect must not even copy the frame"
    assert eff.events(ctx) == []

    root = os.path.join(os.path.dirname(__file__), "..")
    src = os.path.join(root, "out", "_t_cap_noop_in.mp4")
    os.makedirs(os.path.dirname(src), exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "testsrc2=size=320x240:rate=30:duration=2", "-c:v", "libx264",
         "-crf", "0", "-pix_fmt", "yuv420p", src], check=True)

    preset = get_preset("cc-line21-1982")
    plain = RenderOptions(seed=3, duration=1.5, scale=1.0, crf=0)
    # A completely different style, still with no cue to apply it to.
    styled = RenderOptions(seed=3, duration=1.5, scale=1.0, crf=0,
                           video_overrides={"captions.color": "00FF00", "captions.box": "block",
                                            "captions.edge": "glow", "captions.size": 0.09})
    cued = RenderOptions(seed=3, duration=1.5, scale=1.0, crf=0,
                         event_edits=[{"op": "add", "id": "cap:a", "t": 0.3,
                                       "detail": {"text": "HI", "dur_s": 0.5}}])

    def h(path):
        return hashlib.sha256(open(path, "rb").read()).hexdigest()

    out_a = os.path.join(root, "out", "_t_cap_noop_a.mp4")
    out_b = os.path.join(root, "out", "_t_cap_noop_b.mp4")
    out_c = os.path.join(root, "out", "_t_cap_noop_c.mp4")
    render(src, out_a, preset, plain)
    render(src, out_b, preset, styled)
    render(src, out_c, preset, cued)
    assert h(out_a) == h(out_b), "style knobs must not matter when there is nothing to style"
    assert h(out_a) != h(out_c), "a real cue must actually change the render"


def test_caption_cues_land_where_and_when_they_say():
    """A cue's pixels show up exactly inside the box the plan reports, and nowhere else.

    events() hands back a normalized bbox precisely so a front end can draw drag handles that
    match the picture; this is the check that the promise is real, by rendering rather than
    trusting the geometry math. A frame inside the cue's window must differ from a cueless
    render inside that box, and a frame outside the window must not differ at all - captions is
    a frame effect with no schedule of its own, so nothing about it should leak past the cue's
    own span.
    """
    import subprocess

    import numpy as np

    from aesthetician.engine import RenderOptions, render
    from aesthetician.engine.render import Layer, plan_events
    from aesthetician.engine.presets import get_preset

    root = os.path.join(os.path.dirname(__file__), "..")
    src = os.path.join(root, "out", "_t_cap_where_in.mp4")
    os.makedirs(os.path.dirname(src), exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "testsrc2=size=320x240:rate=30:duration=3", "-c:v", "libx264",
         "-crf", "0", "-pix_fmt", "yuv420p", src], check=True)

    preset = get_preset("cc-line21-1982")
    edits = [{"op": "add", "id": "cap:a", "t": 1.0,
              "detail": {"text": "HELLO WORLD", "dur_s": 1.0}}]
    plan = plan_events(src, [Layer(preset=preset, seed=1, event_edits=edits)],
                       RenderOptions(seed=1, scale=1.0))
    ev = next(e for e in plan["events"] if e["kind"] == "caption")
    fps = plan["fps"]

    W, H = 320, 240
    x0, y0, x1, y1 = ev["detail"]["bbox"]
    px0, py0 = int(round(x0 * W)), int(round(y0 * H))
    px1, py1 = int(round(x1 * W)), int(round(y1 * H))

    cued_opts = RenderOptions(seed=1, duration=3.0, scale=1.0, crf=0, event_edits=edits)
    plain_opts = RenderOptions(seed=1, duration=3.0, scale=1.0, crf=0)
    cued = os.path.join(root, "out", "_t_cap_where_cued.mp4")
    plain = os.path.join(root, "out", "_t_cap_where_plain.mp4")
    render(src, cued, preset, cued_opts)
    render(src, plain, preset, plain_opts)

    def frames(path):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo",
                              "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
        n = len(raw) // (W * H * 3)
        return np.frombuffer(raw[: n * W * H * 3], np.uint8).reshape(n, H, W, 3).astype(np.int16)

    fc, fp = frames(cued), frames(plain)
    inside_fi = int(round(1.5 * fps))
    before_fi = int(round(0.2 * fps))
    after_fi = int(round(2.5 * fps))

    inside = np.abs(fc[inside_fi, py0:py1, px0:px1] - fp[inside_fi, py0:py1, px0:px1])
    assert inside.mean() > 20, "the cue's own box must visibly change while it holds"

    for fi in (before_fi, after_fi):
        assert np.array_equal(fc[fi], fp[fi]), f"frame {fi} is outside the cue's span"


def test_caption_edits_add_move_tune_and_skip_unknown_ids():
    """add, move and tune compose in one edit list, and a bad id is skipped, never guessed at.

    Cues live purely in the edit list - there is no procedural schedule to diff against, unlike
    dropouts - so every op has to be checked against the cues the *earlier* ops in the same list
    produced: a move naming a cue the same edit just added, a tune landing on it afterwards, and
    stray ops naming an id nothing ever created quietly doing nothing, per docs/events.md.
    """
    import subprocess

    from aesthetician.engine import RenderOptions
    from aesthetician.engine.render import Layer, plan_events
    from aesthetician.engine.presets import get_preset

    root = os.path.join(os.path.dirname(__file__), "..")
    src = os.path.join(root, "out", "_t_cap_ops_in.mp4")
    os.makedirs(os.path.dirname(src), exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "testsrc2=size=160x120:rate=30:duration=6", "-c:v", "libx264",
         "-crf", "0", "-pix_fmt", "yuv420p", src], check=True)

    preset = get_preset("cc-line21-1982")
    edits = [
        {"op": "add", "id": "cap:a", "t": 1.0, "detail": {"text": "FIRST", "dur_s": 1.0}},
        {"op": "add", "id": "cap:b", "t": 3.0, "detail": {"text": "SECOND", "dur_s": 1.0}},
        {"op": "move", "id": "cap:b", "t": 5.0},
        {"op": "tune", "id": "cap:a", "detail": {"text": "CHANGED", "dur_s": 2.0}},
        {"op": "remove", "id": "cap:zzz"},
        {"op": "tune", "id": "cap:zzz", "detail": {"text": "NOPE"}},
    ]
    plan = plan_events(src, [Layer(preset=preset, seed=1, event_edits=edits)],
                       RenderOptions(seed=1, scale=1.0))
    evs = sorted((e for e in plan["events"] if e["kind"] == "caption"), key=lambda e: e["t"])
    assert len(evs) == 2, evs

    a, b = evs
    assert abs(a["t"] - 1.0) < 1e-6 and a["detail"]["text"] == "CHANGED", a
    assert abs(a["detail"]["dur_s"] - 2.0) < 1e-6, a
    assert abs(b["t"] - 5.0) < 1e-6 and b["detail"]["text"] == "SECOND", b
    assert b["detail"]["id"] == "cap:b"


def test_caption_position_override_and_null_clears_it():
    """A cue's own pos_y wins over the preset's, and null hands it back.

    Every placement knob on a cue is optional: unset, the preset's lower-third default places
    it, the way cc-line21-1982 always has. Pinning one is a tune with a value; un-pinning it is
    the same tune with JSON null, exactly like the tracking-storm band pins in docs/events.md.
    The plan is the honest record of which state a cue is in, so this reads it back both ways.
    """
    import subprocess

    from aesthetician.engine import RenderOptions
    from aesthetician.engine.render import Layer, plan_events
    from aesthetician.engine.presets import get_preset

    root = os.path.join(os.path.dirname(__file__), "..")
    src = os.path.join(root, "out", "_t_cap_pos_in.mp4")
    os.makedirs(os.path.dirname(src), exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "testsrc2=size=160x120:rate=30:duration=3", "-c:v", "libx264",
         "-crf", "0", "-pix_fmt", "yuv420p", src], check=True)

    preset = get_preset("cc-line21-1982")
    pinned = [{"op": "add", "id": "cap:a", "t": 1.0,
               "detail": {"text": "HELLO WORLD", "dur_s": 1.0, "pos_y": 0.2}}]
    opts = RenderOptions(seed=1, scale=1.0)

    plan = plan_events(src, [Layer(preset=preset, seed=1, event_edits=pinned)], opts)
    ev = next(e for e in plan["events"] if e["kind"] == "caption")
    assert ev["detail"]["pos_y"] == 0.2
    x0, y0, x1, y1 = ev["detail"]["bbox"]
    assert abs((y0 + y1) / 2 - 0.2) < 0.05, ev["detail"]["bbox"]

    cleared = pinned + [{"op": "tune", "id": "cap:a", "detail": {"pos_y": None}}]
    plan2 = plan_events(src, [Layer(preset=preset, seed=1, event_edits=cleared)], opts)
    ev2 = next(e for e in plan2["events"] if e["kind"] == "caption")
    assert ev2["detail"]["pos_y"] is None
    x0, y0, x1, y1 = ev2["detail"]["bbox"]
    assert (y0 + y1) / 2 > 0.7, "null must hand placement back to the preset's lower third"


def test_caption_renders_reproduce_byte_for_byte():
    """Same seed, same cue, same bytes - including through jitter and a per-character reveal.

    Nothing about drawing a cue should read from anything but the seed: not wall-clock, not
    dict iteration order, not thread scheduling in the encoder. jitter draws its wobble from
    ctx.frame_rng and typewriter draws its cursor blink from the absolute frame number, so both
    are exercised here rather than just the plain cut-and-hold case every other test covers.
    """
    import hashlib
    import subprocess

    from aesthetician.engine import RenderOptions, render
    from aesthetician.engine.presets import get_preset

    root = os.path.join(os.path.dirname(__file__), "..")
    src = os.path.join(root, "out", "_t_cap_det_in.mp4")
    os.makedirs(os.path.dirname(src), exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "testsrc2=size=320x240:rate=30:duration=3", "-c:v", "libx264",
         "-crf", "0", "-pix_fmt", "yuv420p", src], check=True)

    edits = [{"op": "add", "id": "cap:a", "t": 0.5,
              "detail": {"text": "HELLO WORLD", "dur_s": 1.5}}]

    def h(path):
        return hashlib.sha256(open(path, "rb").read()).hexdigest()

    cases = [
        ("typewriter-doc-1976", {}),                            # per-character typewriter reveal
        ("fansub-vhs-1994", {"captions.jitter": 0.4}),          # position/brightness jitter
    ]
    for pid, over in cases:
        preset = get_preset(pid)
        opts = RenderOptions(seed=42, duration=2.0, scale=1.0, crf=0,
                             event_edits=edits, video_overrides=over)
        out_a = os.path.join(root, "out", f"_t_cap_det_{pid}_a.mp4")
        out_b = os.path.join(root, "out", f"_t_cap_det_{pid}_b.mp4")
        render(src, out_a, preset, opts)
        render(src, out_b, preset, opts)
        assert h(out_a) == h(out_b), pid


def test_caption_cues_still_show_through_a_stacked_look():
    """A caption layer holds up under a look stacked on top of it, the way it will in practice.

    Captions almost never renders alone: cc-line21-1982 (or any caption preset) is meant to sit
    under a tape or film look so the era chews the lettering the way it chewed everything else.
    render_layers feeds layer one's actual output into layer two, so this is the only test here
    that proves a cue survives being re-encoded and processed by a second preset rather than
    living in an isolated single-effect chain.
    """
    import subprocess

    import numpy as np

    from aesthetician.engine import RenderOptions
    from aesthetician.engine.render import Layer, plan_events, render_layers
    from aesthetician.engine.presets import get_preset

    root = os.path.join(os.path.dirname(__file__), "..")
    src = os.path.join(root, "out", "_t_cap_stack_in.mp4")
    os.makedirs(os.path.dirname(src), exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "testsrc2=size=320x240:rate=30:duration=2", "-c:v", "libx264",
         "-crf", "0", "-pix_fmt", "yuv420p", src], check=True)

    cap_preset = get_preset("cc-line21-1982")
    vhs_preset = get_preset("vhs-1985-sp")
    edits = [{"op": "add", "id": "cap:a", "t": 0.3,
              "detail": {"text": "HELLO WORLD", "dur_s": 1.0}}]

    plan = plan_events(src, [Layer(preset=cap_preset, seed=9, event_edits=edits)],
                       RenderOptions(seed=9, scale=1.0))
    ev = next(e for e in plan["events"] if e["kind"] == "caption")
    fps = plan["fps"]

    opts = RenderOptions(seed=9, duration=1.5, scale=1.0, crf=0)
    with_cue = [Layer(preset=cap_preset, seed=9, event_edits=edits),
               Layer(preset=vhs_preset, seed=9)]
    no_cue = [Layer(preset=cap_preset, seed=9, event_edits=[]),
             Layer(preset=vhs_preset, seed=9)]

    out_cue = os.path.join(root, "out", "_t_cap_stack_cue.mp4")
    out_none = os.path.join(root, "out", "_t_cap_stack_none.mp4")
    render_layers(src, out_cue, with_cue, opts)
    render_layers(src, out_none, no_cue, opts)

    W, H = 320, 240

    def frames(path):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo",
                              "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
        n = len(raw) // (W * H * 3)
        return np.frombuffer(raw[: n * W * H * 3], np.uint8).reshape(n, H, W, 3).astype(np.int16)

    fc, fn = frames(out_cue), frames(out_none)
    x0, y0, x1, y1 = ev["detail"]["bbox"]
    px0, py0 = int(round(x0 * W)), int(round(y0 * H))
    px1, py1 = int(round(x1 * W)), int(round(y1 * H))
    mid_fi = int(round((ev["t"] + ev["dur"] / 2) * fps))
    diff = np.abs(fc[mid_fi, py0:py1, px0:px1] - fn[mid_fi, py0:py1, px0:px1])
    assert diff.mean() > 20, "the cue must still read through a stacked look"


def test_dials_at_zero_reach_zero():
    """The dial-at-zero traps a full audit surfaced, pinned one by one.

    The promise across the whole library is the same: an amount/rate dial at
    its bottom stop contributes nothing. Each block here reproduced a real leak
    before its fix - a plate flashing through gate 0, dust hairs dying with an
    unrelated dial, an echo that 0 could not switch off.
    """
    import numpy as np

    from aesthetician.engine.graph import Context, get_effect

    ctx = Context(width=160, height=120, fps=24, n_frames=300, seed=11)

    def run(eff, frame, fi):
        ctx.fi_out = fi
        ctx.fi_src = fi
        return eff.process(frame.copy(), ctx)

    base = np.random.default_rng(5).random((120, 160, 3)).astype(np.float32)

    # dust: hairs are their own dial - density 0 must kill specks, not hairs.
    both_off = get_effect("dust")()
    both_off.key = "dust"
    both_off.resolve(ctx, {"density": 0, "hairs": 0})
    both_off.prepare(ctx)
    hairs_only = get_effect("dust")()
    hairs_only.key = "dust"
    hairs_only.resolve(ctx, {"density": 0, "hairs": 1.0})
    hairs_only.prepare(ctx)
    hair_frames = 0
    for fi in range(300):
        assert np.array_equal(run(both_off, base, fi), base), "dust at all-zero must pass through"
        if not np.array_equal(run(hairs_only, base, fi), base):
            hair_frames += 1
    assert hair_frames > 0, "hairs at 1.0 with density 0 must still draw hairs"

    # plate: gate 0 means never, and jitter must actually move a frame-sized
    # plate. Plates ship outside git, so stand in for the store.
    from aesthetician.assets import store as plate_store

    real_n, real_plate = plate_store.n_plates, plate_store.plate

    def fake_plate(_pack, _idx, pw, ph):
        yy = np.linspace(0.0, 1.0, ph, dtype=np.float32)[:, None]
        xx = np.linspace(0.0, 1.0, pw, dtype=np.float32)[None, :]
        return np.repeat(((xx + yy) / 2.0)[..., None], 3, axis=-1)

    plate_store.n_plates = lambda _pack: 4
    plate_store.plate = fake_plate
    try:
        gated = get_effect("plate")()
        gated.key = "plate"
        gated.resolve(ctx, {"gate": 0.0, "opacity": 1.0})
        gated.prepare(ctx)
        for fi in range(300):
            assert np.array_equal(run(gated, base, fi), base), f"plate showed through gate 0 at frame {fi}"

        def jitter_run(j):
            eff = get_effect("plate")()
            eff.key = "plate"
            eff.resolve(ctx, {"jitter": j, "opacity": 1.0, "cycle": "per_second"})
            eff.prepare(ctx)
            return [run(eff, base, fi) for fi in (0, 30, 60, 90)]

        still_, moved = jitter_run(0.0), jitter_run(30.0)
        assert any(not np.array_equal(a, b) for a, b in zip(still_, moved)), \
            "jitter at default scale must move the plate (it used to clamp to 0)"
    finally:
        plate_store.n_plates, plate_store.plate = real_n, real_plate

    # cel_dirt tape: the trigger had a ~3.5% floor the moment the dial left 0.
    def tape_events(ts):
        eff = get_effect("cel_dirt")()
        eff.key = "cel_dirt"
        eff.resolve(ctx, {"tape_splice": ts})
        eff.prepare(ctx)
        n = 0
        for fi in range(1200):
            ctx.fi_src = fi
            eff._tape_cache = None
            if eff._tape_for_drawing(ctx, 120) is not None:
                n += 1
        return n

    lo_n, hi_n = tape_events(0.01), tape_events(0.4)
    assert hi_n > 0, "the authored range must still fire"
    assert lo_n <= hi_n * 0.25, f"tape at 0.01 fired {lo_n}x vs {hi_n}x at 0.4 - the floor is back"

    # riso: misregister 0 locks the drums - no static offset, no wobble.
    riso = get_effect("riso_print")()
    riso.key = "riso_print"
    riso.resolve(ctx, {"misregister": 0.0})
    riso.prepare(ctx)
    assert riso._off == (0.0, 0.0)
    assert float(np.abs(riso._wob_x).max()) == 0.0 and float(np.abs(riso._wob_y).max()) == 0.0

    # screen: hotspot 0 means a flat screen, not half the falloff.
    flat = np.full((120, 160, 3), 0.5, np.float32)
    scr = get_effect("screen")()
    scr.key = "screen"
    scr.resolve(ctx, {"hotspot": 0.0})
    scr.prepare(ctx)
    got = run(scr, flat, 0)
    # Patch means, so the surface's own texture mottle averages out and only
    # the radial falloff (the bug: ~8% at the corners) can trip this.
    corner, center = float(got[:12, :12].mean()), float(got[54:66, 74:86].mean())
    assert abs(corner - center) < 3e-3, f"hotspot 0 left a vignette: corner {corner} vs center {center}"

    # framing: the overscan zoom dial now works in crop mode too.
    fr_a = get_effect("framing")()
    fr_a.key = "framing"
    fr_a.resolve(ctx, {"mode": "crop", "aspect": "4:3", "zoom": 0.0})
    fr_a.prepare(ctx)
    fr_b = get_effect("framing")()
    fr_b.key = "framing"
    fr_b.resolve(ctx, {"mode": "crop", "aspect": "4:3", "zoom": 0.2})
    fr_b.prepare(ctx)
    assert not np.array_equal(run(fr_a, base, 0), run(fr_b, base, 0)), \
        "zoom must change a crop-mode frame (it was a dead knob there)"

    # captions: edge strength 0 is the same picture as no edge at all.
    from aesthetician.engine import text as textmod

    for edge in ("outline", "shadow", "glow", "outline_shadow"):
        zero = textmod.render_block("EDGE CASE", edge=edge, edge_strength=0.0)
        none = textmod.render_block("EDGE CASE", edge="none")
        assert np.allclose(zero.alpha, none.alpha, atol=1e-6), f"edge {edge} at 0 still drew"
        assert np.allclose(zero.rgb, none.rgb, atol=1e-6), f"edge {edge} at 0 tinted the block"

    # a_speaker: "strength 0 is truly flat" has to include the cabinet knock,
    # which used to fire at full gain exactly at 0.
    actx = Context(width=0, height=0, fps=24, n_frames=48, sr=48000, channels=2, seed=7)
    tone = (0.1 * np.sin(2 * np.pi * 180.0 * np.arange(48000) / 48000.0)).astype(np.float32)
    tone = np.stack([tone, tone], axis=1)
    spk = get_effect("a_speaker")()
    spk.key = "a_speaker"
    spk.resolve(actx, {"strength": 0.0, "cabinet_knock": 0.8})
    spk.prepare(actx)
    assert np.allclose(spk.process_audio(tone.copy(), actx), tone, atol=1e-5), \
        "speaker strength 0 with knock must be flat"

    # a_pa_bullhorn: 0 repeats means no echo; -1 still means the device's own.
    def horn(**over):
        eff = get_effect("a_pa_bullhorn")()
        eff.key = "a_pa_bullhorn"
        eff.resolve(actx, {"device": "pa_hall", **over})
        eff.prepare(actx)
        return eff.process_audio(tone.copy(), actx)

    no_slap = horn(slap_ms=0.0)
    assert np.allclose(horn(slap_repeats=0), no_slap, atol=1e-6), \
        "slap_repeats 0 must mean none, not the device default"
    assert not np.allclose(horn(slap_repeats=-1), no_slap, atol=1e-4), \
        "the -1 sentinel must still bring the device's own slap"
    assert not np.allclose(horn(slap_gain_db=-3.0), horn(slap_gain_db=-25.0), atol=1e-5), \
        "slap level must be live even with slap_ms at its default"


def test_master_intensity_zero_means_no_damage_events():
    """--intensity 0 has to silence the damage schedules, not just fade them.

    frame_damage's rates, gate_weave's splice bumps and dust's hairs sat
    outside the intensity scaling, so a render at intensity 0 still spliced,
    bumped and grew blotches - which reads exactly like "I turned everything
    off and it is still damaged".
    """
    import numpy as np

    from aesthetician.engine.graph import Context, get_effect

    ctx = Context(width=160, height=120, fps=24, n_frames=480, seed=3, intensity=0.0)

    fd = get_effect("frame_damage")()
    fd.key = "frame_damage"
    fd.resolve(ctx, {"splice_skip_rate": 6.0, "slip_rate": 6.0, "blotch_rate": 12.0,
                     "static_flash": 6.0})
    fd.prepare(ctx)
    assert not fd._splice and not fd._slip and not fd._blotches and not fd._flash
    assert fd.remap(ctx) is None

    gw = get_effect("gate_weave")()
    gw.key = "gate_weave"
    gw.resolve(ctx, {"amount": 3.0, "splice_bump": 12.0})
    gw.prepare(ctx)
    assert float(np.abs(gw._bump).max()) == 0.0, "intensity 0 must silence splice bumps"
    assert gw.v["amount"] == 0.0

    dust = get_effect("dust")()
    dust.key = "dust"
    dust.resolve(ctx, {"density": 1.0, "hairs": 1.0})
    assert dust.v["density"] == 0.0 and dust.v["hairs"] == 0.0


def test_codec_glitch_repeats_per_seed():
    """Corruption is curated, so it has to repeat: same seed, same glitches.

    The whole library promises determinism per seed, and codec_glitch was the
    one effect breaking it - not in the corruption (the bitstream damage is a
    fixed state machine) but in the *decode*: error concealment over a damaged
    stream is racy under frame threading, and the same corrupted bytes came
    back as different pictures run to run. A preview could show a smear the
    export then didn't have. Single-threaded concealment pins it.
    """
    import hashlib
    import subprocess

    from aesthetician.engine.graph import Context, get_effect

    root = os.path.join(os.path.dirname(__file__), "..")
    src = os.path.join(root, "out", "_t_glitch_in.mp4")
    os.makedirs(os.path.dirname(src), exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "testsrc2=size=320x240:rate=30:duration=2", "-c:v", "libx264",
         "-crf", "12", "-pix_fmt", "yuv420p", src], check=True)

    def frames_sha(path):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo",
                              "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
        return hashlib.sha1(raw).hexdigest()

    hashes = set()
    for run in (1, 2):
        ctx = Context(width=320, height=240, fps=30, n_frames=60, seed=44,
                      scratch_dir=os.path.join(root, "out"))
        eff = get_effect("codec_glitch")()
        eff.key = "codec_glitch"
        eff.resolve(ctx, {"amount": 0.5, "drop_p": 0.3})
        eff.prepare(ctx)
        out = os.path.join(root, "out", f"_t_glitch_{run}.mp4")
        eff.file_pass(src, out, ctx)
        hashes.add(frames_sha(out))
    assert len(hashes) == 1, "the same seed must decode to the same glitches"


def test_layer_picture_and_sound_switches():
    """A layer's PICTURE / SOUND master switches mute a whole chain in place.

    Off is the real thing: the muted chain is simply not built, so the picture
    (or sound) passes through exactly as a preset with no such chain would
    hand it on - while the other chain keeps rendering, and per-effect enabled
    overrides are left untouched for when the section comes back.
    """
    import json
    import subprocess

    import numpy as np

    from aesthetician.cli import _parse_layers
    from aesthetician.engine import Preset, RenderOptions
    from aesthetician.engine.media import read_audio, read_frames
    from aesthetician.engine.render import Layer, plan_events, render_layers

    root = os.path.join(os.path.dirname(__file__), "..")
    src = os.path.join(root, "out", "_t_sections_in.mp4")
    os.makedirs(os.path.dirname(src), exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y",
         "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=30:duration=2",
         "-f", "lavfi", "-i", "sine=f=440:d=2",
         "-c:v", "libx264", "-crf", "0", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-shortest", src], check=True)

    loud = Preset(id="t_sec", name="t", family="t", era="", desc="",
                  video=[("mono", {})],                  # unmissable: grayscale
                  audio=[("a_gain", {"db": -26.0})])     # unmissable: -26 dB
    opts = RenderOptions(seed=5, duration=1.5, crf=12)

    def gray_spread(path):
        # channel spread ~0 everywhere means the mono effect really ran
        f = next(read_frames(path, 320, 240, 30))
        return float(np.abs(f.max(axis=-1) - f.min(axis=-1)).mean())

    def rms(path):
        a = read_audio(path, 48000, 2)
        return float(np.sqrt(np.mean(a ** 2)))

    both = os.path.join(root, "out", "_t_sec_both.mp4")
    no_pic = os.path.join(root, "out", "_t_sec_nopic.mp4")
    no_snd = os.path.join(root, "out", "_t_sec_nosnd.mp4")
    render_layers(src, both, [Layer(preset=loud, seed=5)], opts)
    render_layers(src, no_pic, [Layer(preset=loud, seed=5, picture=False)], opts)
    render_layers(src, no_snd, [Layer(preset=loud, seed=5, sound=False)], opts)

    assert gray_spread(both) < 0.02, "control: the mono chain must actually run"
    assert gray_spread(no_snd) < 0.02, "sound off must leave the picture chain running"
    assert gray_spread(no_pic) > 0.05, "picture off must leave the source's colors alone"
    assert rms(no_pic) < rms(no_snd) * 0.2, \
        "picture off keeps the treated (-26 dB) sound; sound off keeps the original level"
    assert rms(both) < rms(no_snd) * 0.2

    # A muted picture chain plans no damage pins either.
    vhs = Preset(id="t_sec_vhs", name="t", family="t", era="", desc="",
                 video=[("vhs", {"dropouts": 8.0})])
    on_plan = plan_events(src, [Layer(preset=vhs, seed=9)], opts)
    off_plan = plan_events(src, [Layer(preset=vhs, seed=9, picture=False)], opts)
    assert on_plan["events"], "control: the dropout schedule must plan events"
    assert off_plan["events"] == [], "picture off must plan nothing"

    # The GUI's layer spec round-trips the switches, and a fully muted layer
    # is dropped exactly like a disabled one.
    spec = json.dumps([
        {"preset": "grindhouse-1973", "picture": False},
        {"preset": "grindhouse-1973", "sound": False},
        {"preset": "grindhouse-1973", "picture": False, "sound": False},
    ])
    layers = _parse_layers(spec)
    assert [(la.picture, la.sound) for la in layers] == [(False, True), (True, False)]
    try:
        _parse_layers(json.dumps([{"preset": "grindhouse-1973",
                                   "picture": False, "sound": False}]))
        raise AssertionError("an all-muted stack must be rejected like an all-disabled one")
    except Exception as err:
        assert "disabled" in str(err)


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
