"""Unit tests for engine primitives (run: .venv/bin/python tests/test_engine.py)."""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aesthetician.engine.graph import Context, Param, build_chain, get_effect
from aesthetician.engine.presets import parse_override_paths
from aesthetician.engine.render import _compose_src_map, _segment_chain
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
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok {fn.__name__}")
    print(f"{len(fns)} engine tests passed")
