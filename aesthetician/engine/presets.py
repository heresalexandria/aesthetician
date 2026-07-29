"""Preset model and registry.

A preset is a complete aesthetic: an ordered video chain, an ordered audio
chain, optional processing geometry (era resolution), and named variants that
override individual parameters ("EP tape", "5th-generation dub", …).

Override paths use "effect_key.param" where effect_key is the effect id, with
a #n suffix for repeated effects (e.g. "grain#2.amount").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ChainSpec = list[tuple[str, dict[str, Any]]]


@dataclass
class Variant:
    id: str
    name: str
    desc: str = ""
    video: dict[str, Any] = field(default_factory=dict)  # "effect_key.param" -> value
    audio: dict[str, Any] = field(default_factory=dict)


@dataclass
class Preset:
    id: str
    name: str
    family: str
    era: str
    desc: str
    video: ChainSpec = field(default_factory=list)
    audio: ChainSpec = field(default_factory=list)
    tags: tuple[str, ...] = ()
    proc_height: int | None = None      # simulate at this vertical resolution
    upscale: str = "auto"               # auto | sharp | soft  (final upscale flavor)
    variants: list[Variant] = field(default_factory=list)

    def variant(self, vid: str | None) -> Variant | None:
        if not vid:
            return None
        for v in self.variants:
            if v.id == vid:
                return v
        raise KeyError(f"preset '{self.id}' has no variant '{vid}'; options: {[v.id for v in self.variants]}")


_PRESETS: dict[str, Preset] = {}


def register_preset(p: Preset) -> Preset:
    if p.id in _PRESETS:
        raise ValueError(f"duplicate preset id {p.id}")
    _PRESETS[p.id] = p
    return p


def get_preset(pid: str) -> Preset:
    from .. import presets  # noqa: F401  (triggers registration)

    if pid not in _PRESETS:
        import difflib

        close = difflib.get_close_matches(pid, _PRESETS.keys(), n=3)
        hint = f" Did you mean: {', '.join(close)}?" if close else ""
        raise KeyError(f"unknown preset '{pid}'.{hint}")
    return _PRESETS[pid]


def all_presets() -> dict[str, Preset]:
    from .. import presets  # noqa: F401

    return dict(_PRESETS)


def parse_override_paths(overrides: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Split {"vhs.tracking": 0.7} into {"vhs": {"tracking": 0.7}}."""
    out: dict[str, dict[str, Any]] = {}
    for path, value in overrides.items():
        if "." not in path:
            raise ValueError(f"override '{path}' must be 'effect.param'")
        ekey, pname = path.split(".", 1)
        out.setdefault(ekey, {})[pname] = value
    return out
