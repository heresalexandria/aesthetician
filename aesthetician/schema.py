"""Machine-readable export of the effect registry and preset library (GUI food)."""

from __future__ import annotations

from typing import Any

from . import __version__
from .engine.graph import all_effects
from .engine.presets import all_presets


def effect_schema() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for eid, cls in sorted(all_effects().items()):
        out[eid] = {
            "id": eid,
            "label": cls.label,
            "kind": cls.kind,
            "desc": cls.desc,
            "params": [
                {
                    "name": p.name,
                    "label": p.label,
                    "kind": p.kind,
                    "default": p.default,
                    "lo": p.lo,
                    "hi": p.hi,
                    "step": p.step,
                    "choices": list(p.choices),
                    "unit": p.unit,
                    "desc": p.desc,
                    "group": p.group,
                    "iscale": p.iscale,
                }
                for p in cls.PARAMS
            ],
        }
    return out


def preset_schema() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for pid, p in sorted(all_presets().items()):
        out[pid] = {
            "id": p.id,
            "name": p.name,
            "family": p.family,
            "era": p.era,
            "desc": p.desc,
            "tags": list(p.tags),
            "proc_height": p.proc_height,
            "upscale": p.upscale,
            "video": [[eid, params] for eid, params in p.video],
            "audio": [[eid, params] for eid, params in p.audio],
            "variants": [
                {"id": v.id, "name": v.name, "desc": v.desc, "video": v.video, "audio": v.audio}
                for v in p.variants
            ],
        }
    return out


def full_schema() -> dict[str, Any]:
    return {"version": __version__, "effects": effect_schema(), "presets": preset_schema()}
