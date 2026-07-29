"""Period optics: lens character (aberration, diffusion, distortion, focus
behavior) and camcorder auto-exposure feel.

Optical behaviors here happen at the camera, so temporal tracks are keyed on
ctx.fi_src — a held frame under a cadence remap keeps its optical state.
"""

from __future__ import annotations

import numpy as np
import cv2

from ...engine import color
from ...engine.graph import Context, Effect, Param, register


@register
class Optics(Effect):
    eid = "optics"
    label = "Lens Character"
    kind = "frame"
    desc = "Period lens flaws: chromatic aberration, glamour soft-focus, Pro-Mist diffusion, barrel/pincushion distortion, soft corners and drifting/hunting focus."
    PARAMS = (
        Param("chromatic_aberration", "Chromatic Aberration", "float", 0.0, 0.0, 6.0, unit="px", iscale=True,
              group="Optics", desc="Radial R/B fringing in pixels at the corners."),
        Param("soft_focus", "Soft Focus", "float", 0.0, 0.0, 1.0, iscale=True, group="Optics",
              desc="1930s glamour diffusion: blur blended over a sharp core."),
        Param("bloom_mids", "Mid Bloom", "float", 0.3, 0.0, 1.0, group="Optics",
              desc="With soft focus: extra glow lifted out of the midtones."),
        Param("diffusion", "Diffusion Filter", "float", 0.0, 0.0, 1.0, iscale=True, group="Optics",
              desc="Pro-Mist look: milky blooming highlights and lowered local contrast."),
        Param("distortion", "Distortion", "float", 0.0, -0.3, 0.3, group="Optics",
              desc="Barrel (+) or pincushion (−) geometric distortion."),
        Param("corner_softness", "Corner Softness", "float", 0.0, 0.0, 1.0, iscale=True, group="Optics",
              desc="Cheap-lens blur increasing toward the corners."),
        Param("focus_drift", "Focus Drift", "float", 0.0, 0.0, 1.0, iscale=True, group="Focus",
              desc="Slow wandering of overall focus."),
        Param("hunt_rate", "Focus Hunts", "float", 0.0, 0.0, 20.0, unit="/min", group="Focus",
              desc="Autofocus hunting: quick out-and-back focus excursions."),
        Param("bokeh_swirl", "Swirl", "float", 0.0, 0.0, 1.0, iscale=True, group="Optics",
              desc="Petzval/triplet field curvature: low-frequency (defocused) detail smears tangentially "
                   "toward the frame edges while the sharp core stays put."),
        Param("veiling_flare", "Veiling Flare", "float", 0.0, 0.0, 1.0, iscale=True, group="Optics",
              desc="Uncoated-glass scatter: when bright sources are present, a milky veil lifts contrast "
                   "across the whole frame, heaviest near the source."),
        Param("aperture_ghost", "Aperture Ghost", "float", 0.0, 0.0, 1.0, iscale=True, group="Optics",
              desc="Faint iris-shaped ghost mirrored through the frame center opposite a strong light source."),
    )

    def prepare(self, ctx: Context) -> None:
        self._maps: dict = {}
        self._corner_mask: np.ndarray | None = None
        self._shape: tuple | None = None
        n, fps = ctx.n_frames, ctx.fps
        fd = self.v["focus_drift"]
        drift = ctx.noise.smooth(f"{self.key}:fd", 0.13)
        base = fd * (0.20 + 0.80 * np.clip(0.5 + 0.5 * drift, 0.0, 1.0) ** 1.6)
        env = np.zeros(n, np.float32)
        if self.v["hunt_rate"] > 0:
            ev = ctx.noise.events(f"{self.key}:hunt", self.v["hunt_rate"] / 60.0, min_gap_s=1.5)
            klen = max(int(0.7 * fps), 3)
            kern = np.sin(np.linspace(0.0, np.pi, klen)).astype(np.float32) ** 1.5
            env = np.convolve(ev, kern)[:n].astype(np.float32)
        self._sigma_track = (base + np.clip(env, 0.0, 1.2) * 0.9).astype(np.float32)
        self._swirl_mask: np.ndarray | None = None
        self._ghost_pos: tuple[float, float] | None = None
        self._ghost_s = 0.0
        self._ghost_rot = ctx.noise.smooth(f"{self.key}:grot", 0.05) if self.v["aperture_ghost"] > 0 else None

    # ── geometry: distortion + CA composed into per-channel remap grids ─

    def _build_maps(self, H: int, W: int) -> None:
        k = self.v["distortion"]
        ca = self.v["chromatic_aberration"]
        self._maps = {}
        if abs(k) < 1e-4 and ca <= 0:
            return
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        cx, cy = (W - 1) / 2.0, (H - 1) / 2.0
        dx, dy = xx - cx, yy - cy
        corner = float(np.hypot(cx, cy))
        rn2 = (dx * dx + dy * dy) * np.float32(1.0 / (corner * corner))
        base = 1.0 + np.float32(k) * rn2  # sample position scale (k>0 → barrel)
        e = ca / corner                   # per-channel CA scale at the corners
        scales = {"r": 1.0 - e, "g": 1.0, "b": 1.0 + e}
        for ch, s in scales.items():
            if ch == "g" and abs(k) < 1e-4:
                continue  # green untouched when only CA is active
            f = base * np.float32(s)
            self._maps[ch] = ((cx + dx * f).astype(np.float32), (cy + dy * f).astype(np.float32))

    def _apply_geometry(self, frame: np.ndarray) -> np.ndarray:
        if not self._maps:
            return frame
        out = frame.copy() if "g" not in self._maps else np.empty_like(frame)
        for ci, ch in enumerate("rgb"):
            m = self._maps.get(ch)
            if m is not None:
                out[..., ci] = cv2.remap(np.ascontiguousarray(frame[..., ci]), m[0], m[1],
                                         cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return out

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        H, W = frame.shape[:2]
        if self._shape != (H, W):
            self._build_maps(H, W)
            self._corner_mask = None
            self._shape = (H, W)
        hscale = H / 1080.0

        frame = self._apply_geometry(frame)

        # focus drift / hunting
        fi = min(ctx.fi_src, len(self._sigma_track) - 1)
        sd = float(self._sigma_track[fi]) * 4.2 * hscale
        if sd > 0.25:
            frame = cv2.GaussianBlur(frame, (0, 0), sd)

        sf = self.v["soft_focus"]
        if sf > 0:
            b = cv2.GaussianBlur(frame, (0, 0), (1.5 + 4.5 * sf) * hscale)
            frame = cv2.addWeighted(frame, 1.0 - 0.55 * sf, b, 0.55 * sf, 0.0)
            bm = self.v["bloom_mids"] * sf
            if bm > 0:
                y = color.luma(b)
                mid = color.smoothstep(0.25, 0.65, y) * (1.0 - color.smoothstep(0.75, 0.98, y))
                mid *= 0.22 * bm
                for ci in range(3):
                    frame[..., ci] += b[..., ci] * mid

        d = self.v["diffusion"]
        if d > 0:
            sigma = (8.0 + 14.0 * d) * hscale
            ds = max(int(sigma / 3.0), 1)
            small = np.ascontiguousarray(frame[::ds, ::ds])
            small = cv2.GaussianBlur(small, (0, 0), max(sigma / ds, 1.0))
            b = cv2.resize(small, (W, H), interpolation=cv2.INTER_LINEAR)
            m = color.smoothstep(0.30, 0.95, color.luma(b))
            m *= 0.75 * d
            for ci in range(3):
                fc = frame[..., ci]
                hi = b[..., ci] * m
                hi *= 1.0 - fc
                fc += hi                                              # milky highlights
            frame = cv2.addWeighted(frame, 1.0 - 0.12 * d, b, 0.12 * d, 0.0)  # lowered local contrast

        bs = self.v["bokeh_swirl"]
        if bs > 0:
            # tangential smear of the low-pass band: rotate the low band a touch
            # both ways about center and average — the sharp core is added back
            hw, hh = max(W // 2, 16), max(H // 2, 16)
            small = cv2.resize(frame, (hw, hh), interpolation=cv2.INTER_AREA)
            lp = cv2.GaussianBlur(small, (0, 0), 1.6 * max(hscale, 0.4) + 0.6)
            ang = 1.0 + 2.0 * bs
            ctr = ((hw - 1) / 2.0, (hh - 1) / 2.0)
            r1 = cv2.warpAffine(lp, cv2.getRotationMatrix2D(ctr, ang, 1.0), (hw, hh),
                                flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            r2 = cv2.warpAffine(lp, cv2.getRotationMatrix2D(ctr, -ang, 1.0), (hw, hh),
                                flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            diff = cv2.resize((r1 + r2 + lp) * np.float32(1.0 / 3.0) - lp, (W, H),
                              interpolation=cv2.INTER_LINEAR)
            if self._swirl_mask is None:
                nx = np.linspace(-1, 1, W, dtype=np.float32)[None, :] ** 2
                ny = np.linspace(-1, 1, H, dtype=np.float32)[:, None] ** 2
                self._swirl_mask = (color.smoothstep(0.30, 1.05, np.sqrt(nx + ny)) ** 1.3).astype(np.float32)
            m = self._swirl_mask * np.float32(min(bs * 1.4, 1.0))
            for ci in range(3):
                frame[..., ci] += diff[..., ci] * m

        vf = self.v["veiling_flare"]
        if vf > 0:
            y = color.luma(frame)
            hot = color.smoothstep(0.78, 0.97, y)
            e = float(hot.mean())
            if e > 4e-4:
                ds = 6
                sm = np.ascontiguousarray(hot[::ds, ::ds])
                sm = cv2.GaussianBlur(sm, (0, 0), max(H * 0.16 / ds, 2.0))
                veil = cv2.resize(sm, (W, H), interpolation=cv2.INTER_LINEAR)
                eg = min(e * 9.0, 1.0)
                k = vf * (0.10 * eg + 0.24 * veil)   # local halo + global lift
                for ci, wc in enumerate((1.0, 0.97, 0.90)):
                    fc = frame[..., ci]
                    fc += k * wc * (1.0 - fc)

        ag = self.v["aperture_ghost"]
        if ag > 0:
            frame = self._apply_ghost(frame, ag, ctx, H, W)

        cs = self.v["corner_softness"]
        if cs > 0:
            if self._corner_mask is None:
                nx = np.linspace(-1, 1, W, dtype=np.float32)[None, :] ** 2
                ny = np.linspace(-1, 1, H, dtype=np.float32)[:, None] ** 2
                dgrid = np.sqrt(nx + ny)
                self._corner_mask = (color.smoothstep(0.45, 1.25, dgrid) ** 1.2).astype(np.float32)
            b = cv2.GaussianBlur(frame, (0, 0), (1.2 + 3.8 * cs) * hscale)
            m = self._corner_mask * cs
            for ci in range(3):
                fc = frame[..., ci]
                fc *= 1.0 - m
                fc += b[..., ci] * m

        return np.clip(frame, 0.0, 1.0, out=frame)

    def _apply_ghost(self, frame: np.ndarray, ag: float, ctx: Context, H: int, W: int) -> np.ndarray:
        """Iris-shaped internal reflection mirrored through the frame center."""
        step = 6
        ys = color.luma(frame[::step, ::step])
        hotm = np.clip((ys - 0.90) * 12.0, 0.0, 1.0)
        mass = float(hotm.mean())
        if mass > 2e-4:
            mm = cv2.moments(hotm)
            if mm["m00"] > 1e-6:
                cx = mm["m10"] / mm["m00"] * step
                cy = mm["m01"] / mm["m00"] * step
                a = 0.30  # positional smoothing so the ghost doesn't jitter
                if self._ghost_pos is None:
                    self._ghost_pos = (cx, cy)
                else:
                    self._ghost_pos = (self._ghost_pos[0] + a * (cx - self._ghost_pos[0]),
                                       self._ghost_pos[1] + a * (cy - self._ghost_pos[1]))
                # a lamp-sized source (~0.1% of frame) already casts a clear ghost
                self._ghost_s += 0.35 * (min((mass * 250.0) ** 0.6, 1.0) - self._ghost_s)
        else:
            self._ghost_s *= 0.82
        if self._ghost_s < 0.03 or self._ghost_pos is None:
            return frame
        gx = (W - 1) - self._ghost_pos[0]
        gy = (H - 1) - self._ghost_pos[1]
        ds = 4
        cw, ch = max(W // ds, 16), max(H // ds, 16)
        canvas = np.zeros((ch, cw), np.float32)
        rad = H * (0.040 + 0.035 * self._ghost_s) / ds
        rot = 0.28
        if self._ghost_rot is not None:
            rot += 0.2 * float(self._ghost_rot[min(ctx.fi_src, len(self._ghost_rot) - 1)])
        angs = rot + np.arange(7, dtype=np.float32) * (2 * np.pi / 7)
        pts = np.stack([gx / ds + rad * np.cos(angs), gy / ds + rad * np.sin(angs)], axis=-1)
        cv2.fillConvexPoly(canvas, pts.astype(np.int32), 1.0, cv2.LINE_AA)
        canvas = cv2.GaussianBlur(canvas, (0, 0), max(rad * 0.13, 0.8))
        ghost = cv2.resize(canvas, (W, H), interpolation=cv2.INTER_LINEAR)
        alpha = ag * 0.30 * self._ghost_s
        for ci, wc in enumerate((0.55, 0.92, 0.75)):  # coating-green reflection
            fc = frame[..., ci]
            fc += ghost * (alpha * wc) * (1.0 - fc)
        return frame


@register
class ExposureAuto(Effect):
    eid = "exposure_auto"
    label = "Auto Exposure (Camcorder)"
    kind = "frame"
    desc = "Camcorder AE/AGC behavior: exposure chases mid-gray with lag and overshoot, gain noise rises in the dark, and auto white balance slowly wanders."
    PARAMS = (
        Param("target", "Target Level", "float", 0.42, 0.25, 0.60, group="Exposure",
              desc="Mid-gray level the controller chases."),
        Param("lag", "Response Lag", "float", 0.8, 0.1, 3.0, unit="s", group="Exposure",
              desc="Time constant of the exposure response (the pump)."),
        Param("overshoot", "Overshoot", "float", 0.3, 0.0, 1.0, group="Exposure",
              desc="Underdamping: how much the exposure overshoots then settles."),
        Param("max_boost", "Max Gain", "float", 3.0, 1.0, 8.0, unit="×", group="Exposure",
              desc="AGC ceiling in dark scenes."),
        Param("agc_gain_noise", "Gain Noise", "float", 0.5, 0.0, 1.0, iscale=True, group="Exposure",
              desc="Luma noise added proportionally as AGC gain rises."),
        Param("wb_amount", "WB Drift", "float", 0.3, 0.0, 1.0, iscale=True, group="Exposure",
              desc="Auto white balance wandering warm/cool."),
        Param("flicker_60hz", "Mains Beat", "float", 0.0, 0.0, 1.0, iscale=True, group="Exposure",
              desc="Fluorescent/mains beat: a fast, shallow luma ripple from the shutter beating against "
                   "50/60 Hz lighting — the indoor-camcorder shimmer."),
        Param("iris_step", "Stepped Iris", "float", 0.0, 0.0, 1.0, group="Exposure",
              desc="Auto-iris moves in discrete clicks instead of gliding: exposure corrections land as "
                   "small visible steps."),
    )

    def prepare(self, ctx: Context) -> None:
        self._g = 0.0       # log gain
        self._vel = 0.0
        self._init = False
        self._wb = ctx.noise.smooth(f"{self.key}:wb", 0.06)
        self._wb2 = ctx.noise.smooth(f"{self.key}:wb2", 0.045)
        self._beat = None
        if self.v["flicker_60hz"] > 0:
            fps = max(ctx.fps, 1.0)
            hz = 9.0 + 2.8 * ctx.noise.smooth(f"{self.key}:beathz", 0.06)  # aliased beat wanders
            ph = np.cumsum(2 * np.pi * hz / fps)
            depth = 0.55 + 0.45 * ctx.noise.smooth(f"{self.key}:beatd", 0.16)
            self._beat = (np.sin(ph) * depth).astype(np.float32)
        self._iris_q: float | None = None

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        H, W = frame.shape[:2]
        maxb = self.v["max_boost"]
        m = float(color.luma(frame[::4, ::4]).mean())
        desired = float(np.log(np.clip(self.v["target"] / max(m, 1e-4), 0.25, maxb)))
        if not self._init:
            self._g, self._init = desired, True
        wn = 2.2 / max(self.v["lag"], 0.05)
        zeta = float(np.clip(1.0 - 0.55 * self.v["overshoot"], 0.25, 1.2))
        dt = 1.0 / max(ctx.fps, 1.0)
        acc = wn * wn * (desired - self._g) - 2.0 * zeta * wn * self._vel
        self._vel += acc * dt
        self._g += self._vel * dt
        g_applied = self._g
        step = self.v["iris_step"]
        if step > 0:
            # quantize the applied gain: the servo still glides, the iris clicks
            q = 0.046 + 0.231 * step  # ≈1/15 .. 0.4 stop per click
            if self._iris_q is None or abs(self._g - self._iris_q) > 0.62 * q:
                self._iris_q = round(self._g / q) * q
            g_applied = self._iris_q
        gain = float(np.exp(np.clip(g_applied, np.log(0.2), np.log(maxb * 1.25))))
        frame *= gain
        if gain > 1.02:
            frame = color.soft_clip_highlights(frame, 0.90)

        if self._beat is not None:
            b = float(self._beat[min(ctx.fi_src, len(self._beat) - 1)])
            frame *= np.float32(1.0 + self.v["flicker_60hz"] * 0.034 * b)

        agc = self.v["agc_gain_noise"]
        if agc > 0 and gain > 1.05:
            boost = float(np.clip((gain - 1.0) / max(maxb - 1.0, 0.2), 0.0, 1.0))
            sigma = agc * 0.085 * boost
            if sigma > 0.003:
                g = ctx.frame_rng(f"{self.key}:agc", fi=ctx.fi_src)
                nz = g.standard_normal((H // 2, W // 2), dtype=np.float32)
                nz = cv2.resize(nz, (W, H), interpolation=cv2.INTER_LINEAR)
                y = color.luma(frame)
                resp = (0.35 + 0.65 * (1.0 - color.smoothstep(0.4, 0.9, y))) * sigma
                nz *= resp
                for ci in range(3):
                    frame[..., ci] += nz

        wb = self.v["wb_amount"]
        if wb > 0:
            fi = min(ctx.fi_src, len(self._wb) - 1)
            t = float(self._wb[fi]) * 0.05 * wb
            tg = float(self._wb2[fi]) * 0.02 * wb
            for ci, gn in enumerate((1.0 + t, 1.0 + tg, 1.0 - t)):
                frame[..., ci] *= gn

        return np.clip(frame, 0.0, 1.0, out=frame)
