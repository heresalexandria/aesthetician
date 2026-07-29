"""Plate overlays: blends AI-generated (or procedural fallback) texture plates.

Complements the procedural damage effects with organic scanned-feel elements:
dust plates, light leaks, burns, glass grime, paper texture, tape creases.
"""

from __future__ import annotations

import cv2
import numpy as np

from ...assets import store
from ...engine.graph import Context, Effect, Param, register


@register
class PlateOverlay(Effect):
    eid = "plate"
    label = "Plate Overlay"
    kind = "frame"
    desc = "Blends organic overlay plates (dust, leaks, burns, grime, paper, tape damage) with era-correct motion: cycling, jitter, drift and flicker."
    PARAMS = (
        Param("pack", "Plate Pack", "enum", "film_dust",
              choices=("film_dust", "light_leaks", "film_burns", "grime", "paper_textures", "tape_creases"),
              desc="Which asset pack to draw from."),
        Param("opacity", "Opacity", "float", 0.5, 0.0, 1.0, iscale=True, group="Blend"),
        Param("blend", "Blend Mode", "enum", "screen", choices=("screen", "add", "multiply", "overlay"),
              group="Blend", desc="screen/add for black-background plates, multiply/overlay for textures."),
        Param("cycle", "Cycle Mode", "enum", "per_frame",
              choices=("per_frame", "per_second", "hold", "shuffle_fast"), group="Motion",
              desc="How often a new plate is chosen: every frame (dust), every second, held (texture), or chaotic."),
        Param("jitter", "Position Jitter", "float", 0.0, 0.0, 60.0, unit="px", group="Motion",
              desc="Random offset per plate swap — keeps plates from reading as static."),
        Param("drift", "Drift Speed", "float", 0.0, 0.0, 40.0, unit="px/s", group="Motion",
              desc="Slow wander of the plate position (light leaks breathe)."),
        Param("flicker", "Opacity Flicker", "float", 0.0, 0.0, 1.0, group="Motion",
              desc="Per-frame opacity variation."),
        Param("gate", "Appearance Gate", "float", 1.0, 0.0, 1.0, group="Motion",
              desc="Fraction of time the plate is visible at all (1 = always; 0.2 = occasional flashes)."),
        Param("scale", "Plate Scale", "float", 1.0, 0.5, 3.0, group="Blend"),
        Param("mono", "Desaturate Plate", "bool", False, group="Blend"),
    )

    def prepare(self, ctx: Context) -> None:
        self._n = store.n_plates(self.v["pack"])
        self._drift_x = ctx.noise.smooth(f"{self.key}:dx", 0.10)
        self._drift_y = ctx.noise.smooth(f"{self.key}:dy", 0.13)
        self._flick = ctx.noise.white(f"{self.key}:fl")
        self._gate_noise = ctx.noise.smooth(f"{self.key}:gate", 0.35)

    def _plate_index(self, ctx: Context) -> int:
        mode = self.v["cycle"]
        fi = ctx.fi_out
        if mode == "per_frame":
            return fi
        if mode == "per_second":
            return int(fi / max(ctx.fps, 1))
        if mode == "shuffle_fast":
            return int(ctx.frame_rng(f"{self.key}:pick").integers(0, max(self._n, 1)))
        return 0  # hold

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        if self._n == 0 or self.v["opacity"] <= 0:
            return frame  # pack not generated — procedural effects still cover the look
        if self.v["gate"] < 1.0:
            g = (self._gate_noise[ctx.fi_out] + 1.0) / 2.0
            if g > self.v["gate"]:
                return frame
        H, W = frame.shape[:2]
        s = self.v["scale"]
        pw, ph = int(W * s), int(H * s)
        idx = self._plate_index(ctx)
        p = store.plate(self.v["pack"], idx, pw, ph)
        if p is None:
            return frame

        # position: jitter on plate swap + slow drift
        rng = ctx.frame_rng(f"{self.key}:pos", idx)
        jx = int(rng.uniform(-self.v["jitter"], self.v["jitter"]))
        jy = int(rng.uniform(-self.v["jitter"], self.v["jitter"]))
        dx = int(self._drift_x[ctx.fi_out] * self.v["drift"] * ctx.fi_out / max(ctx.fps, 1))
        dy = int(self._drift_y[ctx.fi_out] * self.v["drift"] * ctx.fi_out / max(ctx.fps, 1))
        ox = (pw - W) // 2 + jx + dx
        oy = (ph - H) // 2 + jy + dy
        ox = int(np.clip(ox, 0, max(pw - W, 0)))
        oy = int(np.clip(oy, 0, max(ph - H, 0)))
        p = p[oy : oy + H, ox : ox + W]
        if p.shape[:2] != (H, W):
            p = cv2.resize(p, (W, H), interpolation=cv2.INTER_LINEAR)

        if self.v["mono"]:
            p = np.repeat(p.mean(axis=-1, keepdims=True), 3, axis=-1)

        op = self.v["opacity"]
        if self.v["flicker"] > 0:
            op = float(np.clip(op * (1.0 + self.v["flicker"] * 0.5 * self._flick[ctx.fi_out]), 0.0, 1.0))

        mode = self.v["blend"]
        if mode == "screen":
            out = 1.0 - (1.0 - frame) * (1.0 - p * op)
        elif mode == "add":
            out = frame + p * op
        elif mode == "multiply":
            out = frame * (1.0 - op + op * p)
        else:  # overlay
            low = 2.0 * frame * p
            high = 1.0 - 2.0 * (1.0 - frame) * (1.0 - p)
            ov = np.where(frame < 0.5, low, high)
            out = frame * (1.0 - op) + ov * op
        return np.clip(out, 0.0, 1.0).astype(np.float32)
