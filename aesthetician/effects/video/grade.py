"""Color grading effects: tone, balance, saturation, era fades, stock looks."""

from __future__ import annotations

import cv2
import numpy as np

from ...engine import color
from ...engine.graph import Context, Effect, Param, register


@register
class Tone(Effect):
    eid = "tone"
    label = "Tone Curve"
    kind = "frame"
    desc = "Exposure, contrast around a pivot, gamma, black lift and soft highlight shoulder."
    PARAMS = (
        Param("exposure", "Exposure", "float", 0.0, -2.0, 2.0, unit="stops", desc="Linear exposure in stops."),
        Param("contrast", "Contrast", "float", 1.0, 0.3, 2.5, desc="S-contrast around the pivot."),
        Param("pivot", "Pivot", "float", 0.42, 0.1, 0.9, desc="Contrast pivot luminance."),
        Param("gamma", "Gamma", "float", 1.0, 0.4, 2.5, desc="Midtone gamma."),
        Param("lift", "Black Lift", "float", 0.0, -0.2, 0.35, desc="Raises (or crushes) blacks."),
        Param("knee", "Highlight Knee", "float", 0.9, 0.5, 1.0, desc="Soft shoulder start; 1 disables."),
    )

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        x = frame
        if self.v["exposure"]:
            x = x * (2.0 ** self.v["exposure"])
        c = self.v["contrast"]
        if c != 1.0:
            p = self.v["pivot"]
            x = (x - p) * c + p
        if self.v["gamma"] != 1.0:
            x = np.clip(x, 0.0, None) ** (1.0 / self.v["gamma"])
        lift = self.v["lift"]
        if lift:
            x = x * (1.0 - max(lift, 0.0)) + lift if lift > 0 else x + lift * (1.0 - x)
        if self.v["knee"] < 1.0:
            x = color.soft_clip_highlights(np.clip(x, 0.0, 1.2), self.v["knee"])
        return np.clip(x, 0.0, 1.0).astype(np.float32)


@register
class ColorBalance(Effect):
    eid = "balance"
    label = "Color Balance"
    kind = "frame"
    desc = "White-balance warmth/tint plus shadow/highlight split tones."
    PARAMS = (
        Param("warmth", "Warmth", "float", 0.0, -1.0, 1.0, desc="+warm (orange) / −cool (blue)."),
        Param("tint", "Tint", "float", 0.0, -1.0, 1.0, desc="+magenta / −green."),
        Param("shadow_tint", "Shadow Tint", "enum", "none",
              choices=("none", "blue", "teal", "green", "magenta", "brown"), desc="Cast in the shadows."),
        Param("shadow_amt", "Shadow Amount", "float", 0.0, 0.0, 1.0),
        Param("high_tint", "Highlight Tint", "enum", "none",
              choices=("none", "yellow", "cream", "cyan", "pink"), desc="Cast in the highlights."),
        Param("high_amt", "Highlight Amount", "float", 0.0, 0.0, 1.0),
    )

    _SHADOW = {
        "blue": (0.0, 0.02, 0.10), "teal": (0.0, 0.05, 0.07), "green": (0.0, 0.06, 0.0),
        "magenta": (0.06, 0.0, 0.06), "brown": (0.06, 0.03, 0.0),
    }
    _HIGH = {
        "yellow": (0.06, 0.05, -0.06), "cream": (0.05, 0.03, -0.02), "cyan": (-0.05, 0.02, 0.05),
        "pink": (0.06, -0.01, 0.03),
    }

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        x = color.temperature_shift(frame, self.v["warmth"] * 0.6, self.v["tint"] * 0.6)
        y = color.luma(x)
        if self.v["shadow_tint"] != "none" and self.v["shadow_amt"] > 0:
            w = (1.0 - color.smoothstep(0.0, 0.5, y))[..., None] * self.v["shadow_amt"]
            x = x + np.asarray(self._SHADOW[self.v["shadow_tint"]], np.float32) * w
        if self.v["high_tint"] != "none" and self.v["high_amt"] > 0:
            w = color.smoothstep(0.5, 1.0, y)[..., None] * self.v["high_amt"]
            x = x + np.asarray(self._HIGH[self.v["high_tint"]], np.float32) * w
        return np.clip(x, 0.0, 1.0).astype(np.float32)


@register
class Saturation(Effect):
    eid = "saturation"
    label = "Saturation & Hue"
    kind = "frame"
    desc = "Global saturation, skin-preserving vibrance and hue rotation."
    PARAMS = (
        Param("amount", "Saturation", "float", 1.0, 0.0, 2.5, desc="1 = unchanged."),
        Param("vibrance", "Vibrance", "float", 0.0, -1.0, 1.0, desc="Saturates muted colors more."),
        Param("hue", "Hue Rotate", "float", 0.0, -30.0, 30.0, unit="°"),
    )

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        x = frame
        if self.v["hue"]:
            th = np.deg2rad(self.v["hue"])
            yiq = color.rgb_to_yiq(x)
            i, q = yiq[..., 1].copy(), yiq[..., 2].copy()
            yiq[..., 1] = i * np.cos(th) - q * np.sin(th)
            yiq[..., 2] = i * np.sin(th) + q * np.cos(th)
            x = color.yiq_to_rgb(yiq)
        if self.v["vibrance"]:
            y = color.luma(x)[..., None]
            sat = np.abs(x - y).max(axis=-1, keepdims=True)
            boost = 1.0 + self.v["vibrance"] * (1.0 - np.clip(sat * 3.0, 0.0, 1.0))
            x = y + (x - y) * boost
        if self.v["amount"] != 1.0:
            x = color.saturate(x, self.v["amount"])
        return np.clip(x, 0.0, 1.0).astype(np.float32)


@register
class Sharpen(Effect):
    eid = "sharpen"
    label = "Sharpness"
    kind = "frame"
    desc = "Unsharp-mask detail control: positive crispens edges, negative softens toward a blur."
    PARAMS = (
        Param("amount", "Amount", "float", 0.0, -1.0, 2.0,
              desc="0 leaves the frame alone; negative blends toward the blur."),
        Param("radius", "Radius", "float", 1.0, 0.3, 5.0, unit="px",
              desc="Detail size the mask works at."),
    )

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        a = self.v["amount"]
        if a == 0.0:
            return frame
        blur = cv2.GaussianBlur(frame, (0, 0), max(self.v["radius"], 0.3))
        # One expression covers both directions: a > 0 adds the edge mask,
        # a < 0 walks the same line toward the blur (a = -1 lands exactly on it).
        x = frame + (frame - blur) * a
        return np.clip(x, 0.0, 1.0).astype(np.float32)


@register
class Fade(Effect):
    eid = "fade"
    label = "Age Fade"
    kind = "frame"
    desc = "Print/dye aging: lifted washed blacks, dimmed highlights, dye-loss color drift."
    PARAMS = (
        Param("amount", "Fade Amount", "float", 0.3, 0.0, 1.0, iscale=True),
        Param("profile", "Dye Profile", "enum", "neutral",
              choices=("neutral", "eastman_pink", "sepia", "cyan_loss", "bleach", "nitrate_amber"),
              desc="How the dyes failed: Eastman pink fade, sepia toning, cyan dye loss…"),
        Param("bloom_whites", "Milky Whites", "float", 0.25, 0.0, 1.0, desc="Hazy compressed highlights."),
    )

    _DRIFT = {
        "neutral": ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
        "eastman_pink": ((0.10, -0.02, -0.04), (0.06, -0.02, 0.00)),
        "sepia": ((0.09, 0.045, -0.06), (0.05, 0.02, -0.05)),
        "cyan_loss": ((0.12, 0.02, -0.10), (0.08, 0.02, -0.06)),
        "bleach": ((-0.02, -0.02, -0.02), (0.0, 0.0, 0.0)),
        "nitrate_amber": ((0.10, 0.05, -0.08), (0.03, 0.01, -0.04)),
    }

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        a = self.v["amount"]
        if a <= 0:
            return frame
        shadow_drift, mid_drift = self._DRIFT[self.v["profile"]]
        x = frame
        y = color.luma(x)
        # lifted, tinted blacks + slightly compressed highs
        x = x * (1.0 - 0.22 * a) + 0.085 * a
        x = x + np.asarray(shadow_drift, np.float32) * (a * (1.0 - color.smoothstep(0.1, 0.7, y))[..., None])
        x = x + np.asarray(mid_drift, np.float32) * (a * 0.8)
        if self.v["profile"] == "bleach":
            x = color.saturate(x, 1.0 - 0.55 * a)
        else:
            x = color.saturate(x, 1.0 - 0.35 * a)
        bw = self.v["bloom_whites"] * a
        if bw > 0:
            w = color.smoothstep(0.75, 1.0, y)[..., None]
            x = x + w * bw * 0.12
        return np.clip(x, 0.0, 1.0).astype(np.float32)


@register
class StockLook(Effect):
    eid = "stock"
    label = "Stock / Process Look"
    kind = "frame"
    desc = "Color rendering of period stocks & processes (Technicolor, Kodachrome, Ektachrome…)."
    PARAMS = (
        Param("profile", "Profile", "enum", "none",
              choices=("none", "technicolor3", "technicolor2", "kodachrome", "ektachrome",
                       "eastman_70s", "agfa_60s", "orwo_east", "vision_90s", "tube_70s", "tube_80s"),
              desc="Era color-rendering profile."),
        Param("strength", "Strength", "float", 1.0, 0.0, 1.0),
    )

    # 3x3 matrices (applied on linear-ish RGB) + per-profile tone tweaks
    _M = {
        "technicolor3": np.array([[1.30, -0.18, -0.12], [-0.10, 1.18, -0.08], [-0.06, -0.16, 1.22]]),
        "technicolor2": np.array([[1.15, 0.10, -0.25], [0.05, 0.95, 0.00], [-0.30, 0.20, 1.10]]),
        "kodachrome": np.array([[1.22, -0.14, -0.08], [-0.06, 1.10, -0.04], [-0.04, -0.10, 1.14]]),
        "ektachrome": np.array([[1.08, -0.04, -0.04], [-0.02, 1.04, -0.02], [0.00, -0.06, 1.12]]),
        "eastman_70s": np.array([[1.10, -0.03, -0.07], [-0.02, 1.02, 0.00], [-0.04, -0.02, 1.02]]),
        "agfa_60s": np.array([[1.06, 0.02, -0.08], [0.02, 1.00, -0.02], [-0.02, 0.04, 0.98]]),
        "orwo_east": np.array([[1.02, 0.06, -0.08], [0.04, 0.96, 0.00], [0.02, 0.08, 0.90]]),
        "vision_90s": np.array([[1.12, -0.08, -0.04], [-0.04, 1.08, -0.04], [-0.02, -0.06, 1.08]]),
        "tube_70s": np.array([[1.04, 0.03, -0.07], [0.01, 1.00, -0.01], [-0.03, 0.02, 1.01]]),
        "tube_80s": np.array([[1.10, -0.02, -0.08], [-0.02, 1.06, -0.04], [-0.04, -0.02, 1.06]]),
    }
    _SAT = {
        "technicolor3": 1.35, "technicolor2": 1.10, "kodachrome": 1.18, "ektachrome": 1.06,
        "eastman_70s": 0.92, "agfa_60s": 0.95, "orwo_east": 0.85, "vision_90s": 1.05,
        "tube_70s": 0.95, "tube_80s": 1.12,
    }

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        p = self.v["profile"]
        if p == "none" or self.v["strength"] <= 0:
            return frame
        s = self.v["strength"]
        x = color.apply_matrix(frame, self._M[p].astype(np.float32))
        x = color.saturate(x, self._SAT[p])
        if p == "technicolor2":
            # two-strip cannot reproduce pure blue/yellow; pull blues toward teal
            yiq = color.rgb_to_yiq(x)
            yiq[..., 2] *= 0.55
            x = color.yiq_to_rgb(yiq)
        x = np.clip(x, 0.0, 1.0)
        if s < 1.0:
            x = frame * (1.0 - s) + x * s
        return x.astype(np.float32)


@register
class Mono(Effect):
    eid = "mono"
    label = "Black & White"
    kind = "frame"
    desc = "Monochrome conversion with period filter response and optional paper/print tint."
    PARAMS = (
        Param("response", "Film Response", "enum", "panchromatic",
              choices=("panchromatic", "orthochromatic", "blue_sensitive", "modern"),
              desc="Orthochromatic (pre-1927) renders reds dark; blue-sensitive even darker lips/skin."),
        Param("tint", "Print Tint", "enum", "neutral",
              choices=("neutral", "silver", "sepia", "cyanotype", "nitrate_warm", "phosphor_green", "amber_crt"),
              desc="Toning of the print (or CRT phosphor color for tube looks)."),
        Param("tint_amt", "Tint Amount", "float", 0.25, 0.0, 1.0),
    )

    _W = {
        "panchromatic": (0.28, 0.55, 0.17),
        "orthochromatic": (0.10, 0.60, 0.30),
        "blue_sensitive": (0.02, 0.38, 0.60),
        "modern": (0.2126, 0.7152, 0.0722),
    }
    _T = {
        "silver": (1.00, 1.02, 1.06), "sepia": (1.12, 1.00, 0.82),
        "cyanotype": (0.82, 0.98, 1.16), "nitrate_warm": (1.08, 1.01, 0.90),
        "phosphor_green": (0.42, 1.22, 0.52), "amber_crt": (1.24, 0.86, 0.38),
    }

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        w = np.asarray(self._W[self.v["response"]], np.float32)
        y = frame @ w
        x = np.repeat(y[..., None], 3, axis=-1)
        if self.v["tint"] != "neutral" and self.v["tint_amt"] > 0:
            t = np.asarray(self._T[self.v["tint"]], np.float32)
            gains = 1.0 + (t - 1.0) * self.v["tint_amt"]
            x = x * gains
        return np.clip(x, 0.0, 1.0).astype(np.float32)
