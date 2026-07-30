"""How the picture was shown: reel changeovers, the surface it was thrown at,
rear-projection televisions and the drive-in windshield.

Presentation artifacts happen at playback, so temporal tracks key on
ctx.fi_out - a held source frame still flickers, shakes and gets its cue dots.
"""

from __future__ import annotations

import numpy as np
import cv2

from ...engine import color
from ...engine.graph import Context, Effect, Param, register


# ── reel changeover ────────────────────────────────────────────────────


@register
class Changeover(Effect):
    eid = "changeover"
    label = "Reel Changeover"
    kind = "frame"
    desc = ("Projection reel changes: the two cue dots blinking in the top-right corner a beat apart, then "
            "a one-frame splice jump with a brief focus and brightness dip as the incoming projector settles.")
    PARAMS = (
        Param("cue_dots", "Cue Dots", "bool", True, group="Changeover",
              desc="The iconic corner circles: a motor cue ~7 s before the change and a changeover cue just "
                   "ahead of it, each visible for ~4 frames."),
        Param("reel_min", "Reel Length", "float", 8.0, 0.25, 30.0, unit="min", group="Changeover",
              desc="Minutes between changeovers - at the default 8 you will rarely see one on a short clip; "
                   "use force_at_s to place one deliberately."),
        Param("force_at_s", "Force At", "float", -1.0, -1.0, 1200.0, unit="s", group="Changeover",
              desc="-1 = natural schedule; set a time to place a single changeover exactly there."),
        Param("splice_bump", "Splice Bump", "float", 0.6, 0.0, 1.0, iscale=True, group="Changeover",
              desc="Severity of the changeover itself: the one-frame jump and the momentary "
                   "brightness/focus dip on the incoming reel."),
    )

    def prepare(self, ctx: Context) -> None:
        n, fps = ctx.n_frames, max(ctx.fps, 1.0)
        times: list[float] = []
        if self.v["force_at_s"] >= 0:
            times = [self.v["force_at_s"]]
        else:
            step = self.v["reel_min"] * 60.0
            tt = step
            while tt < n / fps:
                times.append(tt)
                tt += step
        g = ctx.rng(f"{self.key}:init")
        dot_len = max(int(round(fps / 6.0)), 3)  # ~4 frames at 24
        self._dots: dict[int, dict] = {}
        self._bumps: list[int] = []
        for tc in times:
            fc = int(round(tc * fps))
            if fc >= n + dot_len:
                continue
            jx, jy = float(g.uniform(-0.006, 0.006)), float(g.uniform(-0.006, 0.006))
            for lead_s in (7.0, 1.2):  # motor cue, then changeover cue
                f0 = fc - int(round(lead_s * fps))
                f0 = max(f0, 0)
                for k in range(dot_len):
                    self._dots[f0 + k] = dict(jx=jx, jy=jy)
            if 0 <= fc < n:
                self._bumps.append(fc)
        self._dip_len = max(int(round(0.45 * fps)), 4)

    def _draw_dot(self, frame: np.ndarray, d: dict, ctx: Context) -> None:
        H, W = frame.shape[:2]
        r = max(int(round(0.0195 * H)), 3)
        cx = int(W * (0.938 + d["jx"]))
        cy = int(H * (0.072 + d["jy"]))
        g = ctx.frame_rng(f"{self.key}:dot")
        cx += int(g.integers(-1, 2))
        cy += int(g.integers(-1, 2))
        pad = r + 4
        x0, x1 = max(cx - pad, 0), min(cx + pad + 1, W)
        y0, y1 = max(cy - pad, 0), min(cy + pad + 1, H)
        if x1 <= x0 or y1 <= y0:
            return
        m = np.zeros((y1 - y0, x1 - x0), np.float32)
        ring = np.zeros_like(m)
        c = (cx - x0, cy - y0)
        cv2.circle(m, c, r, 1.0, -1, cv2.LINE_AA)
        cv2.circle(ring, c, r, 1.0, max(int(r * 0.34), 1), cv2.LINE_AA)
        m = cv2.GaussianBlur(m, (0, 0), 0.7)
        ring = cv2.GaussianBlur(ring, (0, 0), 0.7)
        a = float(g.uniform(0.80, 0.95))
        region = frame[y0:y1, x0:x1]
        white = m[..., None] * a
        region += white * (0.94 - region)               # punched hole → near-white
        region *= 1.0 - (ring * 0.55 * a)[..., None]    # scribed dark ring
        np.clip(region, 0.0, 1.0, out=region)

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        fi = ctx.fi_out
        sb = self.v["splice_bump"]
        if sb > 0:
            for fc in self._bumps:
                k = fi - fc
                if k == 0:
                    H, W = frame.shape[:2]
                    g = ctx.frame_rng(f"{self.key}:jump")
                    M = np.float32([[1, 0, g.uniform(-0.012, 0.012) * W],
                                    [0, 1, (0.030 + 0.030 * g.random()) * H * sb *
                                     (1.0 if g.random() < 0.5 else -1.0)]])
                    frame = cv2.warpAffine(frame, M, (W, H), flags=cv2.INTER_LINEAR,
                                           borderMode=cv2.BORDER_REPLICATE)
                if 0 <= k < self._dip_len:
                    decay = float(np.exp(-k / max(self._dip_len * 0.30, 1.0)))
                    frame *= np.float32(1.0 - 0.17 * sb * decay)
                    sig = 2.3 * sb * decay * (frame.shape[0] / 1080.0)
                    if sig > 0.35:
                        frame = cv2.GaussianBlur(frame, (0, 0), sig)
        if self.v["cue_dots"]:
            d = self._dots.get(fi)
            if d is not None:
                self._draw_dot(frame, d, ctx)
        return frame


# ── projection surface ─────────────────────────────────────────────────


@register
class ScreenSurface(Effect):
    eid = "screen"
    label = "Projection Surface"
    kind = "frame"
    desc = ("Projected on something: matte screen, glass-beaded screen with its hotspot and sparkle, painted "
            "wall or a bedsheet - plus vertical keystone, warm room spill and the occasional projector bump.")
    PARAMS = (
        Param("surface", "Surface", "enum", "matte_white",
              choices=("matte_white", "glass_beaded", "wall_paint", "bedsheet"), group="Surface",
              desc="matte_white is honest; glass_beaded adds a hot center and bead sparkle; wall_paint has "
                   "roller mottle; bedsheet drapes, weaves and sags."),
        Param("hotspot", "Hotspot", "float", 0.35, 0.0, 1.0, iscale=True, group="Surface",
              desc="Directional screen gain: bright center, dimmer edges (beaded screens focus it hardest)."),
        Param("keystone_v", "Keystone", "float", 0.0, -0.2, 0.2, group="Geometry",
              desc="Vertical keystone from a projector below (+, top pinched) or above (−) the screen center."),
        Param("room_spill", "Room Spill", "float", 0.15, 0.0, 1.0, iscale=True, group="Room",
              desc="Warm ambient light creeping up the bottom half of the screen - exit signs, a door ajar."),
        Param("shake_event", "Bumps", "float", 0.5, 0.0, 10.0, unit="/min", group="Room",
              desc="Somebody nudges the projector cart: a short damped shake."),
    )

    #                 falloff  hot_k  hot_sig  desc-of-texture
    _SURF = {
        "matte_white":  (0.16, 0.55, 0.55),
        "glass_beaded": (0.30, 1.00, 0.38),
        "wall_paint":   (0.22, 0.62, 0.52),
        "bedsheet":     (0.27, 0.58, 0.50),
    }

    def prepare(self, ctx: Context) -> None:
        n, fps = ctx.n_frames, max(ctx.fps, 1.0)
        dx = np.zeros(n + 8, np.float32)
        dy = np.zeros(n + 8, np.float32)
        if self.v["shake_event"] > 0:
            ev = ctx.noise.events(f"{self.key}:shake", self.v["shake_event"] / 60.0, min_gap_s=2.0)
            g = ctx.rng(f"{self.key}:shakeamp")
            klen = max(int(0.55 * fps), 4)
            tt = np.arange(klen, dtype=np.float32) / fps
            for i in np.nonzero(ev)[0]:
                amp = g.uniform(3.5, 8.0)
                f0 = g.uniform(5.5, 8.5)
                ph = g.uniform(0, 2 * np.pi)
                kx = amp * np.exp(-tt / 0.16) * np.sin(2 * np.pi * f0 * tt + ph)
                ky = amp * 0.6 * np.exp(-tt / 0.13) * np.sin(2 * np.pi * f0 * 1.3 * tt + ph)
                span = max(0, min(klen, len(dx) - int(i)))
                dx[i:i + span] += kx[:span].astype(np.float32)
                dy[i:i + span] += ky[:span].astype(np.float32)
        self._dx, self._dy = dx, dy
        self._shim = ctx.noise.white(f"{self.key}:shim")
        self._gain: np.ndarray | None = None
        self._spark: np.ndarray | None = None
        self._spill: np.ndarray | None = None
        self._M: np.ndarray | None = None
        self._shape: tuple | None = None

    def _build(self, H: int, W: int, ctx: Context) -> None:
        fall, hot_k, hot_sig = self._SURF[self.v["surface"]]
        nx = np.linspace(-1, 1, W, dtype=np.float32)[None, :]
        ny = np.linspace(-1, 1, H, dtype=np.float32)[:, None]
        d = np.sqrt(nx * nx + ny * ny)
        hs = self.v["hotspot"]
        gain = (1.0 - fall * (0.5 + 0.5 * hs) * color.smoothstep(0.35, 1.35, d)) * \
               (1.0 + hs * hot_k * 0.26 * np.exp(-(d / hot_sig) ** 2))
        g = ctx.rng(f"{self.key}:tex")
        surf = self.v["surface"]
        self._spark = None
        if surf == "glass_beaded":
            fine = g.standard_normal((H, W)).astype(np.float32)
            fine = cv2.GaussianBlur(fine, (0, 0), 0.55)
            spark = np.clip((fine - 1.9) * 1.4, 0.0, 1.0)      # rare hot beads
            self._spark = (spark * (0.5 + 0.5 * np.exp(-(d / 0.75) ** 2))).astype(np.float32)
            gain *= 1.0 + 0.012 * fine
        elif surf == "wall_paint":
            m = g.standard_normal((H // 9 + 2, W // 9 + 2)).astype(np.float32)
            m = cv2.resize(cv2.GaussianBlur(m, (0, 0), 1.1), (W, H), interpolation=cv2.INTER_LINEAR)
            m2 = g.standard_normal((H // 3 + 2, W // 3 + 2)).astype(np.float32)
            m2 = cv2.resize(cv2.GaussianBlur(m2, (0, 0), 0.9), (W, H), interpolation=cv2.INTER_LINEAR)
            gain *= 1.0 + 0.030 * m + 0.012 * m2               # roller mottle
        elif surf == "bedsheet":
            xw = np.arange(W, dtype=np.float32)
            yw = np.arange(H, dtype=np.float32)
            p = max(3.2 * H / 720.0, 2.2)
            weave = 0.5 * np.sin(2 * np.pi * xw / p)[None, :] + 0.5 * np.sin(2 * np.pi * yw / (p * 1.08))[:, None]
            drape = g.standard_normal((6, max(int(6 * W / H), 3))).astype(np.float32)
            drape = cv2.resize(cv2.GaussianBlur(drape, (0, 0), 1.0), (W, H), interpolation=cv2.INTER_LINEAR)
            gain *= (1.0 + 0.020 * weave) * (1.0 + 0.045 * drape)
        else:  # matte_white
            fine = g.standard_normal((H // 2 + 1, W // 2 + 1)).astype(np.float32)
            fine = cv2.resize(fine, (W, H), interpolation=cv2.INTER_LINEAR)
            gain *= 1.0 + 0.006 * fine
        self._gain = gain.astype(np.float32)
        rs = self.v["room_spill"]
        self._spill = None
        if rs > 0:
            grad = color.smoothstep(0.42, 1.05, np.linspace(0.0, 1.0, H, dtype=np.float32)) ** 1.4
            self._spill = np.repeat(grad[:, None], 1, axis=1).astype(np.float32)
        k = self.v["keystone_v"]
        self._M = None
        if abs(k) > 1e-4:
            dxp = abs(k) * W * 0.5
            src = np.float32([(0, 0), (W, 0), (W, H), (0, H)])
            if k > 0:
                dst = np.float32([(dxp, 0), (W - dxp, 0), (W, H), (0, H)])
            else:
                dst = np.float32([(0, 0), (W, 0), (W - dxp, H), (dxp, H)])
            self._M = cv2.getPerspectiveTransform(src, dst)
        self._shape = (H, W)

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        H, W = frame.shape[:2]
        if self._shape != (H, W):
            self._build(H, W, ctx)
        if self._M is not None:
            frame = cv2.warpPerspective(frame, self._M, (W, H), flags=cv2.INTER_LINEAR,
                                        borderMode=cv2.BORDER_CONSTANT, borderValue=(0.01, 0.01, 0.01))
        fi = min(ctx.fi_out, len(self._dx) - 1)
        sx, sy = float(self._dx[fi]) * (H / 720.0), float(self._dy[fi]) * (H / 720.0)
        if abs(sx) + abs(sy) > 0.25:
            M = np.float32([[1, 0, sx], [0, 1, sy]])
            frame = cv2.warpAffine(frame, M, (W, H), flags=cv2.INTER_LINEAR,
                                   borderMode=cv2.BORDER_REPLICATE)
        for ci in range(3):
            frame[..., ci] *= self._gain
        if self._spark is not None:
            shim = 0.75 + 0.25 * float(self._shim[min(ctx.fi_out, len(self._shim) - 1)])
            y = color.luma(frame)
            sp = self._spark * (shim * 0.5)
            for ci in range(3):
                frame[..., ci] += sp * y
        if self._spill is not None:
            rs = self.v["room_spill"]
            for ci, wc in enumerate((0.30, 0.235, 0.155)):
                fc = frame[..., ci]
                fc += self._spill * (rs * wc) * (1.0 - fc)
        return np.clip(frame, 0.0, 1.0, out=frame)


# ── rear-projection TV ─────────────────────────────────────────────────


@register
class RearProjectionTV(Effect):
    eid = "rear_projection_tv"
    label = "Rear-Projection TV"
    kind = "frame"
    desc = ("The 80s/90s big screen: three CRT guns splitting vertically toward the corners, the fresnel "
            "hotspot that follows you around the room, and the fine vertical lenticular louvres.")
    PARAMS = (
        Param("convergence", "Misconvergence", "float", 0.35, 0.0, 1.0, iscale=True, group="RPTV",
              desc="CRT gun misalignment growing toward the corners - vertical red/blue splits, the "
                   "signature of a projection set nobody ever converged."),
        Param("hotspot", "Fresnel Hotspot", "float", 0.5, 0.0, 1.0, iscale=True, group="RPTV",
              desc="Strong center brightness with steep falloff - the fresnel only aims at one couch."),
        Param("screen_louvre", "Louvres", "float", 0.35, 0.0, 1.0, iscale=True, group="RPTV",
              desc="Fine vertical lenticular line texture of the projection screen."),
    )

    def prepare(self, ctx: Context) -> None:
        self._maps: tuple | None = None
        self._gain: np.ndarray | None = None
        self._lou: np.ndarray | None = None
        self._shape: tuple | None = None

    def _build(self, H: int, W: int) -> None:
        conv = self.v["convergence"]
        self._maps = None
        if conv > 0:
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            nx = (xx / max(W - 1, 1)) * 2.0 - 1.0
            ny = (yy / max(H - 1, 1)) * 2.0 - 1.0
            c = conv * 3.2 * (H / 720.0)
            dyR = c * (ny * (0.35 + 0.65 * nx * nx) + 0.15 * nx)
            dxR = c * 0.22 * nx * np.abs(ny)
            self._maps = (
                (xx + dxR, yy + dyR),
                (xx - 0.85 * dxR, yy - 0.85 * dyR),
            )
        hs = self.v["hotspot"]
        self._gain = None
        if hs > 0:
            nx1 = np.linspace(-1, 1, W, dtype=np.float32)[None, :]
            ny1 = np.linspace(-1, 1, H, dtype=np.float32)[:, None]
            d = np.sqrt(nx1 * nx1 + ny1 * ny1)
            g = (1.0 + hs * 0.30 * np.exp(-(d / 0.52) ** 2)) * \
                (1.0 - hs * 0.38 * color.smoothstep(0.42, 1.30, d))
            self._gain = g.astype(np.float32)
        lv = self.v["screen_louvre"]
        self._lou = None
        if lv > 0:
            p = max(2.4 * W / 704.0, 2.0)
            x = np.arange(W, dtype=np.float32)
            lou = 1.0 - lv * 0.075 * (0.5 + 0.5 * np.cos(2 * np.pi * x / p)) ** 1.6
            self._lou = lou.astype(np.float32)[None, :]
        self._shape = (H, W)

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        H, W = frame.shape[:2]
        if self._shape != (H, W):
            self._build(H, W)
        if self._maps is not None:
            (rx, ry), (bx, by) = self._maps
            out = frame.copy()
            out[..., 0] = cv2.remap(np.ascontiguousarray(frame[..., 0]), rx, ry,
                                    cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            out[..., 2] = cv2.remap(np.ascontiguousarray(frame[..., 2]), bx, by,
                                    cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            frame = out
        if self._gain is not None:
            for ci in range(3):
                frame[..., ci] *= self._gain
        if self._lou is not None:
            for ci in range(3):
                frame[..., ci] *= self._lou
        return np.clip(frame, 0.0, 1.0, out=frame)


# ── drive-in ───────────────────────────────────────────────────────────


@register
class DriveIn(Effect):
    eid = "drive_in"
    label = "Through The Windshield"
    kind = "frame"
    desc = ("Watching from the front seat: a faint vertical double image off the glass and the warm glow "
            "of the dashboard rising from the bottom of the view.")
    PARAMS = (
        Param("glass_ghost", "Glass Ghost", "float", 0.35, 0.0, 1.0, iscale=True, group="Windshield",
              desc="Faint vertically-offset reflection of the screen in the windshield glass - reads on "
                   "bright picture areas."),
        Param("dashboard_glow", "Dashboard Glow", "float", 0.35, 0.0, 1.0, iscale=True, group="Windshield",
              desc="Warm instrument-panel glow breathing along the bottom edge of the view."),
    )

    def prepare(self, ctx: Context) -> None:
        g = ctx.rng(f"{self.key}:init")
        self._dy = float(g.uniform(0.011, 0.020))
        self._dx = float(g.uniform(-0.004, 0.004))
        self._breath = ctx.noise.smooth(f"{self.key}:dash", 0.07)
        self._grad: np.ndarray | None = None

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        H, W = frame.shape[:2]
        gg = self.v["glass_ghost"]
        if gg > 0:
            M = np.float32([[1, 0, self._dx * W], [0, 1, self._dy * H]])
            ghost = cv2.warpAffine(frame, M, (W, H), flags=cv2.INTER_LINEAR,
                                   borderMode=cv2.BORDER_REPLICATE)
            ghost = cv2.GaussianBlur(ghost, (0, 0), 1.1 * max(H / 1080.0, 0.4))
            a = gg * 0.14
            for ci in range(3):
                fc = frame[..., ci]
                fc += ghost[..., ci] * a * (1.0 - fc)
        dg = self.v["dashboard_glow"]
        if dg > 0:
            if self._grad is None or self._grad.shape[0] != H:
                yn = np.linspace(0.0, 1.0, H, dtype=np.float32)
                self._grad = (color.smoothstep(0.60, 1.02, yn) ** 1.7)[:, None].astype(np.float32)
            b = 0.75 + 0.25 * float(self._breath[min(ctx.fi_out, len(self._breath) - 1)])
            k = dg * 0.24 * b
            for ci, wc in enumerate((1.0, 0.50, 0.16)):
                fc = frame[..., ci]
                fc += self._grad * (k * wc) * (1.0 - fc)
        return np.clip(frame, 0.0, 1.0, out=frame)
