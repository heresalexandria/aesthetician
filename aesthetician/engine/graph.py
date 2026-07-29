"""Effect graph: parameters, effect base classes, chains, render context."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Optional

import numpy as np

from .rng import TemporalNoise, stream

ParamKind = Literal["float", "int", "bool", "enum", "str"]

# Effect kinds:
#   frame          — pure per-frame video transform (streamed)
#   filepass       — operates on an encoded intermediate file (real codec round-trips)
#   audio          — full-buffer audio transform
#   audio_filepass — real audio codec round-trip on a wav file
EffectKind = Literal["frame", "filepass", "audio", "audio_filepass"]


@dataclass(frozen=True)
class Param:
    name: str
    label: str
    kind: ParamKind
    default: Any
    lo: float = 0.0
    hi: float = 1.0
    step: Optional[float] = None
    choices: tuple[str, ...] = ()
    unit: str = ""
    desc: str = ""
    group: str = ""
    # If True, the resolved value is scaled by the render's master intensity
    # (only sensible for zero-based "amount" parameters).
    iscale: bool = False

    def coerce(self, value: Any) -> Any:
        if self.kind == "bool":
            if isinstance(value, str):
                return value.lower() in ("1", "true", "yes", "on")
            return bool(value)
        if self.kind == "int":
            return int(np.clip(int(round(float(value))), self.lo, self.hi))
        if self.kind == "float":
            return float(np.clip(float(value), self.lo, self.hi))
        if self.kind == "enum":
            v = str(value)
            if v not in self.choices:
                raise ValueError(f"invalid choice {v!r} for {self.name}; options: {', '.join(self.choices)}")
            return v
        if self.kind == "str":
            return str(value)
        raise ValueError(f"unknown param kind {self.kind}")


class Context:
    """Per-render state shared by all effects in a chain."""

    def __init__(
        self,
        width: int,
        height: int,
        fps: float,
        n_frames: int,
        sr: int = 48000,
        channels: int = 2,
        seed: int = 1,
        intensity: float = 1.0,
        scratch_dir: str = "",
        asset_root: str = "",
        is_preview: bool = False,
    ):
        self.width = width
        self.height = height
        self.fps = fps
        self.n_frames = n_frames
        self.sr = sr
        self.channels = channels
        self.seed = seed
        self.intensity = intensity
        self.scratch_dir = scratch_dir
        self.asset_root = asset_root
        self.is_preview = is_preview
        self.noise = TemporalNoise(seed, fps, n_frames)
        # Indices for the frame currently being processed (set by the runner).
        self.fi_out = 0   # index on the output timeline
        self.fi_src = 0   # index on the source timeline (differs under time remaps)
        self.extra: dict[str, Any] = {}

    def rng(self, key: str) -> np.random.Generator:
        return stream(self.seed, key)

    def frame_rng(self, key: str, fi: Optional[int] = None) -> np.random.Generator:
        """Generator unique to (key, frame) — for per-frame spatial noise."""
        return stream(self.seed, f"{key}@{self.fi_out if fi is None else fi}")


class Effect:
    """Base class. Subclasses define eid/label/kind and PARAMS, then implement
    the hook for their kind.

    Video frames are float32 RGB HxWx3 in [0, 1]. Audio is float32 (n, ch).
    """

    eid: str = ""
    label: str = ""
    kind: EffectKind = "frame"
    desc: str = ""
    PARAMS: tuple[Param, ...] = ()

    def __init__(self, **overrides: Any):
        self.overrides = dict(overrides)
        self.v: dict[str, Any] = {}
        self.key = self.eid  # may get a #n suffix when duplicated in a chain

    def resolve(self, ctx: Context, user_overrides: dict[str, Any] | None = None) -> None:
        merged = dict(self.overrides)
        if user_overrides:
            merged.update(user_overrides)
        values: dict[str, Any] = {}
        byname = {p.name: p for p in self.PARAMS}
        for name, value in merged.items():
            if name not in byname:
                raise ValueError(f"effect '{self.eid}' has no parameter '{name}'")
        for p in self.PARAMS:
            raw = merged.get(p.name, p.default)
            val = p.coerce(raw)
            if p.iscale and p.kind in ("float", "int") and ctx.intensity != 1.0:
                val = p.coerce(float(val) * ctx.intensity)
            values[p.name] = val
        self.v = values

    # ── hooks ──────────────────────────────────────────────────────────
    def prepare(self, ctx: Context) -> None:
        """Called once before processing; allocate state, precompute tracks."""

    def remap(self, ctx: Context) -> Optional[np.ndarray]:
        """Optional time remap: array of source indices, one per output frame."""
        return None

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        """Per-frame video hook (kind='frame')."""
        return frame

    def process_audio(self, audio: np.ndarray, ctx: Context) -> np.ndarray:
        """Full-buffer audio hook (kind='audio')."""
        return audio

    def file_pass(self, in_path: str, out_path: str, ctx: Context) -> None:
        """File-level hook (kind='filepass' / 'audio_filepass')."""
        raise NotImplementedError


# ── registry ───────────────────────────────────────────────────────────
_REGISTRY: dict[str, type[Effect]] = {}


def register(cls: type[Effect]) -> type[Effect]:
    if not cls.eid:
        raise ValueError(f"{cls.__name__} missing eid")
    if cls.eid in _REGISTRY:
        raise ValueError(f"duplicate effect id {cls.eid}")
    _REGISTRY[cls.eid] = cls
    return cls


def get_effect(eid: str) -> type[Effect]:
    from .. import effects  # noqa: F401  (triggers registration on first use)

    if eid not in _REGISTRY:
        raise KeyError(f"unknown effect '{eid}'")
    return _REGISTRY[eid]


def all_effects() -> dict[str, type[Effect]]:
    from .. import effects  # noqa: F401

    return dict(_REGISTRY)


def build_chain(spec: list[tuple[str, dict[str, Any]]]) -> list[Effect]:
    """Instantiate [(eid, params), ...] into effect objects with unique keys."""
    out: list[Effect] = []
    counts: dict[str, int] = {}
    for eid, params in spec:
        cls = get_effect(eid)
        eff = cls(**params)
        counts[eid] = counts.get(eid, 0) + 1
        eff.key = eid if counts[eid] == 1 else f"{eid}#{counts[eid]}"
        out.append(eff)
    return out
