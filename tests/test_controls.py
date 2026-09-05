"""Control contract and framing regression tests (python tests/test_controls.py)."""
from __future__ import annotations

import inspect
import os
from pathlib import Path
import re
import sys
import tempfile

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aesthetician.engine.graph import Context, all_effects, build_chain, get_effect
from aesthetician.engine.presets import all_presets, Preset
from aesthetician.engine import media
from aesthetician.engine.render import RenderOptions, render, render_still


def test_every_declared_control_resolves_and_has_a_reader():
    """No unknown paths, unconsumed declarations, or broken repeat-key overrides.

    This is a wiring audit, not proof that every conditional setting affects
    every input. The behavioral tests below cover the controls changed here.
    """
    ctx = Context(160, 90, 24, 48)
    count = 0
    for eid, cls in all_effects().items():
        source = inspect.getsource(cls)
        readers = set(re.findall(r'(?:self\.v|\bv|\bp)\[\s*[\'"](\w+)', source))
        names = [p.name for p in cls.PARAMS]
        assert len(names) == len(set(names)), eid
        chain = build_chain([(eid, {}), (eid, {})])
        assert chain[1].key == eid + '#2'
        for prm in cls.PARAMS:
            count += 1
            assert prm.name == 'enabled' or prm.name in readers, f'{eid}.{prm.name} has no reader'
            if prm.kind in ('float', 'int'):
                assert prm.lo <= prm.default <= prm.hi, (eid, prm.name)
                raw = prm.lo + (prm.hi - prm.lo) * .63
                for invalid in (float('nan'), float('inf'), -float('inf')):
                    try:
                        prm.coerce(invalid)
                    except ValueError:
                        pass
                    else:
                        raise AssertionError(f'{eid}.{prm.name} accepted {invalid}')
                assert prm.coerce(prm.hi + 1) == prm.hi
                assert prm.coerce(prm.lo - 1) == prm.lo
            elif prm.kind == 'enum':
                assert prm.default in prm.choices, (eid, prm.name)
                raw = prm.choices[-1]
            elif prm.kind == 'bool':
                raw = not prm.default
            else:
                raw = prm.default
            chain[1].resolve(ctx, {prm.name: raw})
            assert chain[1].v[prm.name] == prm.coerce(raw), (eid, prm.name)
    print(f'    {len(all_effects())} effects / {count} controls audited')


def test_all_preset_framing_defaults_follow_source():
    for pid, preset in all_presets().items():
        for eid, params in preset.video:
            if eid == 'framing':
                assert params.get('aspect', 'source') == 'source', pid
        for variant in preset.variants:
            for path, value in variant.video.items():
                if path.split('.')[0].split('#')[0] == 'framing' and path.endswith('.aspect'):
                    assert value == 'source', (pid, variant.id)
    assert next(p.default for p in get_effect('framing').PARAMS if p.name == 'aspect') == 'source'


def framed(frame, **params):
    h, w = frame.shape[:2]
    ctx = Context(w, h, 24, 48)
    eff = get_effect('framing')(**params)
    eff.resolve(ctx); eff.prepare(ctx)
    return eff.process(frame, ctx)


def test_framing_inherits_portrait_landscape_square_and_arbitrary_sources():
    for w, h in [(160, 90), (90, 160), (120, 120), (210, 90), (122, 78)]:
        frame = np.random.default_rng(4).random((h, w, 3), dtype=np.float32)
        for mode in ['box', 'crop']:
            assert np.array_equal(framed(frame, mode=mode), frame)
            assert np.array_equal(framed(frame, aspect='none', mode=mode), frame)
            assert not np.array_equal(framed(frame, mode=mode, zoom=.15), frame)
    # Subpixel video dimensions cannot produce a zero-sized OpenCV target.
    assert framed(np.ones((2, 2, 3), np.float32), aspect='2.35').shape == (2, 2, 3)


def test_framing_never_squeezes_the_picture_and_dials_are_live():
    frame = np.ones((180, 320, 3), np.float32)
    frame[70:110, 140:180] = [1, 0, 0]
    for mode in ['box', 'crop']:
        for aspect in ['4:3', '2.35', '1:1', '9:16']:
            out = framed(frame, mode=mode, aspect=aspect)
            ys, xs = np.where((out[..., 0] > .8) & (out[..., 1] < .2))
            assert abs(np.ptp(xs) - np.ptp(ys)) <= 1, (mode, aspect, np.ptp(xs), np.ptp(ys))
            assert out.shape == frame.shape
            assert not np.array_equal(out, frame), (mode, aspect)
            assert not np.array_equal(out, framed(frame, mode=mode, aspect=aspect, zoom=.15))
            assert not np.array_equal(out, framed(frame, mode=mode, aspect=aspect, matte_gray=.2))
        rounded = framed(frame, mode=mode, aspect='4:3', corner_radius=.2)
        assert not np.array_equal(rounded, framed(frame, mode=mode, aspect='4:3', corner_radius=.2, edge_soft=.04))
    assert not np.array_equal(framed(frame, aspect='4:3', mode='box'), framed(frame, aspect='4:3', mode='crop'))


def test_cinema_finish_controls_are_live_bounded_and_repeatable():
    rng = np.random.default_rng(7)
    frame = cv2.GaussianBlur(rng.random((120, 160, 3), dtype=np.float32), (0, 0), 1.1)
    frame[:30] = np.clip(frame[:30] + .4, 0, 1)
    frame[30:70, 20:100] *= [1, .25, .5]
    ctx = Context(160, 120, 24, 48)
    def run(**kw):
        eff = get_effect('cinema_finish')(**kw)
        eff.resolve(ctx); eff.prepare(ctx)
        return eff.process(frame, ctx)
    assert np.array_equal(run(), frame)
    assert np.array_equal(run(mix=0, silver=1, density=1, local_contrast=1), frame)
    for key in ['highlight_desat', 'density', 'silver', 'local_contrast']:
        a = run(**{key: .8})
        assert np.max(np.abs(a - frame)) > .001, key
        assert np.array_equal(a, run(**{key: .8})), key
        assert a.dtype == np.float32 and np.isfinite(a).all()
        assert a.min() >= 0 and a.max() <= 1
    assert not np.array_equal(run(local_contrast=.8, radius=.005), run(local_contrast=.8, radius=.15))
    assert not np.array_equal(run(silver=.8, mix=.2), run(silver=.8, mix=.8))
    gray = np.full((120, 160, 3), .5, np.float32)
    e = get_effect('cinema_finish')(density=1,highlight_desat=1)
    e.resolve(ctx)
    assert np.array_equal(e.process(gray, ctx), gray)


def test_display_geometry_reads_rotation_and_non_square_pixels():
    assert media.display_geometry({'width': 720, 'height': 576, 'sample_aspect_ratio': '16:15'}) == (768, 576)
    assert media.display_geometry({'width': 1920, 'height': 1080, 'side_data_list': [{'rotation': -90}]}) == (1080, 1920)
    assert media.display_geometry({'width': 720, 'height': 480, 'sample_aspect_ratio': '8:9', 'tags': {'rotate': '90'}}) == (480, 640)
    for sar in ('0:1', 'N/A', 'nan:1'):
        assert media.display_geometry({'width': 160, 'height': 90, 'sample_aspect_ratio': sar}) == (160, 90)


def test_source_geometry_survives_preview_still_and_export():
    with tempfile.TemporaryDirectory() as tmp:
        base = os.path.join(tmp, 'base.mp4')
        media._run([media.FFMPEG, '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=s=160x90:r=24:d=0.6',
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-y', base])
        rotated = os.path.join(tmp, 'phone.mp4')
        media._run([media.FFMPEG, '-v', 'error', '-display_rotation:v:0', '90', '-i', base, '-c', 'copy', '-y', rotated])
        anamorphic = os.path.join(tmp, 'sd.mp4')
        media._run([media.FFMPEG, '-v', 'error', '-i', base, '-vf', 'setsar=2/1', '-c:v', 'libx264', '-y', anamorphic])
        preset = Preset('geometry', 'Geometry', 'adjust', '', '', video=[('framing', {})])
        for src, expected in [(rotated, (90, 160)), (anamorphic, (320, 90))]:
            info = media.probe(src)
            assert (info.width, info.height) == expected, (src, info, expected)
            intermediate = os.path.join(tmp, 'intermediate.mp4')
            media.extract_intermediate(src, intermediate, *expected, info.fps)
            checked = media.probe(intermediate)
            assert (checked.width, checked.height) == expected
            for scale in (1, .5):
                opts = RenderOptions(duration=.5, scale=scale)
                out = os.path.join(tmp, 'out.mp4')
                render(src, out, preset, opts)
                rendered = media.probe(out)
                # Delivery rounding keeps yuv420 sizes even.
                ew = int(expected[0] * scale) // 2 * 2
                eh = int(expected[1] * scale) // 2 * 2
                assert (rendered.width, rendered.height) == (ew, eh), rendered
                still = os.path.join(tmp, 'still.png')
                render_still(src, still, preset, opts)
                image = cv2.imread(still)
                assert image.shape[:2] == (eh, ew)
                # The bypass path encodes directly through FFmpeg, without the
                # square-pixel raw-frame writer used by live picture effects.
                render(src, out, Preset('plain', 'Plain', 'adjust', '', ''), opts)
                bypassed = media.probe(out)
                assert (bypassed.width, bypassed.height) == (ew, eh), bypassed


def test_atlas_is_211_complete_and_distinct_recipes():
    atlas = [p for p in all_presets().values() if p.id.startswith('atlas-')]
    assert len(atlas) == 211
    assert len({p.name for p in atlas}) == 211
    assert len({repr((p.video, p.audio, p.proc_height)) for p in atlas}) == 211
    assert len([p for p in atlas if p.family == 'audio']) == 10
    assert sum(p.family == 'arthouse' for p in atlas) == 40
    for p in atlas:
        assert p.audio and (p.video or p.family == 'audio'), p.id
        assert not any(eid in {'captions','timestamp','osd'} for eid, _ in p.video)


if __name__ == '__main__':
    tests = [v for k, v in list(globals().items()) if k.startswith('test_') and callable(v)]
    for test in tests:
        test()
        print('  ok', test.__name__)
    print(f'{len(tests)} control tests passed')
