"""Effect graph: parameters, effect base classes, chains, render context."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Optional

import numpy as np

from . import texture as texture_mod
from .rng import TemporalNoise, stream

ParamKind = Literal["float", "int", "bool", "enum", "str"]

# Effect kinds:
#   frame          - pure per-frame video transform (streamed)
#   filepass       - operates on an encoded intermediate file (real codec round-trips)
#   audio          - full-buffer audio transform
#   audio_filepass - real audio codec round-trip on a wav file
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
        out_width: Optional[int] = None,
        out_height: Optional[int] = None,
        texture: float = 1.0,
        t0: float = 0.0,
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
        # Final delivery geometry. Presets often simulate at an era resolution
        # (`proc_height`) and are upscaled afterwards, which magnifies every
        # texture generated here - effects that care can compensate via
        # `upscale`.
        self.out_width = out_width if out_width is not None else width
        self.out_height = out_height if out_height is not None else height
        self.texture = texture
        # Where output frame 0 sits on the source clip's own timeline. A preview
        # is a short render taken from the middle of a clip, and without this
        # every render thinks it starts at the beginning of the tape: Rental
        # Tape's transport lock-up fired in *every* preview, wherever you had
        # scrubbed to, because "1.2 seconds in" meant 1.2 seconds into the
        # preview rather than into the clip.
        self.t0 = t0
        # Edits to the discrete-event schedule, applied by effects in `prepare`:
        # a list of {op, ...} dicts (see docs in render.py). Empty for a render
        # nobody has touched, which is every render there was before this
        # existed - so absent means exactly what it always meant.
        self.event_edits: list[dict] = []
        self.noise = TemporalNoise(seed, fps, n_frames)
        # Indices for the frame currently being processed (set by the runner).
        self.fi_out = 0   # index on the output timeline
        self.fi_src = 0   # index on the source timeline (differs under time remaps)
        self.extra: dict[str, Any] = {}

    @property
    def upscale(self) -> float:
        """Output height / processing height (1.0 when simulating at full size).

        A texture generated `n` px wide here lands `n * upscale` px wide in the
        delivered file.
        """
        return self.out_height / max(self.height, 1)

    def rng(self, key: str) -> np.random.Generator:
        return stream(self.seed, key)

    def abs_frame(self, fi: Optional[int] = None) -> int:
        """An output frame's index on the source clip's own timeline."""
        return int(round(self.t0 * self.fps)) + (self.fi_out if fi is None else fi)

    def frame_of(self, t_seconds: float) -> int:
        """Output frame index for a time written against the source clip.

        Comes back negative, or past `n_frames`, when that moment is not inside
        this render - which is the correct answer for a preview window that does
        not contain the event.
        """
        return int(round((t_seconds - self.t0) * self.fps))

    def frame_rng(self, key: str, fi: Optional[int] = None) -> np.random.Generator:
        """Generator unique to (key, frame) - for per-frame spatial noise.

        Keyed on the *source* frame, so the speckle a preview shows at 0:40 is
        the speckle the export has at 0:40. A render that starts at zero, which
        every export does, is keyed exactly as it always was.
        """
        return stream(self.seed, f"{key}@{self.abs_frame(fi)}")


@dataclass(frozen=True)
class Event:
    """One discrete thing an effect does at a moment on the source clip.

    Damage in this engine is not a haze, it is a series of incidents: a dropout
    is a streak on one row of one frame, a transport glitch is a shredded stretch
    of two thirds of a second. They were being decided a frame at a time deep
    inside `process`, which made them impossible to talk about - you could not
    ask where they were, let alone move one. An effect that deals in incidents
    works them out in `prepare` now and can hand the list over.

    `t` is seconds on the *clip's* timeline, so it means the same thing in a
    preview as in an export.
    """
    t: float
    dur: float
    kind: str
    detail: dict[str, Any] = field(default_factory=dict)


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
        explicit = set(merged)
        for p in self.PARAMS:
            raw = merged.get(p.name, p.default)
            val = p.coerce(raw)
            if p.iscale and p.kind in ("float", "int") and ctx.intensity != 1.0:
                val = p.coerce(float(val) * ctx.intensity)
            if ctx.texture != 1.0 and p.kind in ("float", "int"):
                scaled = texture_mod.scaled(self.eid, p.name, float(val), ctx.texture)
                if scaled != float(val):
                    val = p.coerce(scaled)
            values[p.name] = val
        self.v = values
        self.explicit = explicit

    # ── hooks ──────────────────────────────────────────────────────────
    def prepare(self, ctx: Context) -> None:
        """Called once before processing; allocate state, precompute tracks."""

    def events(self, ctx: Context) -> list["Event"]:
        """The discrete incidents this effect will produce, after `prepare`.

        Empty for the continuous effects - grain, tape noise, a rolling tracking
        band - which are a level rather than a list of moments and want a curve,
        not pins.
        """
        return []

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


# Every effect carries this, injected at registration rather than typed out 104
# times. Some effects have no dial that reaches "nothing": a Risograph is defined
# by its ink pair and a projection surface by its material, so zeroing every
# amount still leaves a duotone print on a matte screen. Taking the effect out of
# the chain is not the same thing - a preset is a fixed chain, and what you want
# while judging a look is to lift one link out and drop it back. Default True, so
# it means "no change" to every preset already written.
ENABLED = Param(
    "enabled", "Enabled", "bool", True,
    desc="Switch this effect off without taking it out of the chain. Off means "
         "the picture passes through untouched.",
)


def register(cls: type[Effect]) -> type[Effect]:
    if not cls.eid:
        raise ValueError(f"{cls.__name__} missing eid")
    if cls.eid in _REGISTRY:
        raise ValueError(f"duplicate effect id {cls.eid}")
    if not any(p.name == ENABLED.name for p in cls.PARAMS):
        cls.PARAMS = (ENABLED, *cls.PARAMS)
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
