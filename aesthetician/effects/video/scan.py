"""Archive-digitization artifacts: what the TRANSFER adds on top of whatever
the film or tape already looked like - telecine/scanner transport, the
transfer suite's automatic color pumping, over-eager digital noise reduction,
botched deinterlacing, and the re-upload generation loss of the early web.

This is the meta-layer that sells "found footage": a 1987 tape doesn't just
look like 1987, it looks like 1987 *as digitized in 2009*. Stack these after
the era effects.

Conventions: float32 RGB in [0, 1]; everything stochastic draws from ctx
streams so a render reproduces exactly from its seed. Transport artifacts are
keyed on ctx.fi_out (the scanner sees frames, not drawings).
"""

from __future__ import annotations

import os

import cv2
import numpy as np

from ...engine import media
from ...engine.color import smoothstep
from ...engine.graph import Context, Effect, Param, register

_LUMA_W = np.array([0.299, 0.587, 0.114], dtype=np.float32)

# Tags restored on the way back to an editable intermediate; the MJPEG
# generations in between lose them but never convert the matrix.
_X264_444 = ["-c:v", "libx264", "-preset", "fast", "-crf", "8",
             "-pix_fmt", "yuv444p", *media.BT709_TAGS, "-an"]


def _even(x: float) -> int:
    return max(2, int(round(x / 2.0)) * 2)


# ═══════════════════════════════════════════════════════════════════════
# 1. Telecine / film-scanner transport
# ═══════════════════════════════════════════════════════════════════════
@register
class TelecineScan(Effect):
    eid = "telecine_scan"
    label = "Telecine Scan"
    kind = "frame"
    desc = (
        "The transfer machine itself: sprocket-worn per-frame registration hops, "
        "faint vertical line-sensor sensitivity stripes, and the slightly "
        "overzoomed, breathing safety crop of an operator hiding the frame edges."
    )
    PARAMS = (
        Param("pin_stability", "Transport", "enum", "pin_registered",
              choices=("pin_registered", "sprocket_worn"), group="Transport",
              desc="pin_registered = rock solid (modern archival scanner). "
                   "sprocket_worn = the claw rides worn perforations: small "
                   "per-frame vertical hops with the occasional double-hop."),
        Param("hop_px", "Hop Size", "float", 1.0, 0.2, 4.0, unit="px", group="Transport",
              desc="Scale of the sprocket hops (sprocket_worn only)."),
        Param("scanner_stripe", "Sensor Stripes", "float", 0.0, 0.0, 1.0, iscale=True,
              group="Sensor",
              desc="Per-column sensitivity variation of the line sensor: faint "
                   "static vertical streaks, the CCD-array fingerprint."),
        Param("frame_edge_crop", "Safety Crop", "float", 0.0, 0.0, 1.0, iscale=True,
              group="Framing",
              desc="Operator overzoom hiding the frame edge: a slight push-in "
                   "whose framing breathes and wanders instead of holding still."),
    )

    def prepare(self, ctx: Context) -> None:
        n = max(ctx.n_frames, 1)
        self._hop: np.ndarray | None = None
        if self.v["pin_stability"] == "sprocket_worn":
            g = ctx.rng(f"{self.key}:hops")
            a = float(self.v["hop_px"])
            dy = np.clip(g.normal(0.0, 0.45, n), -1.1, 1.1) * a
            dbl = g.random(n) < 0.05                       # occasional double-hop
            dy = np.where(dbl, dy + np.sign(g.standard_normal(n)) * a * (1.8 + 0.9 * g.random(n)), dy)
            dx = np.clip(g.normal(0.0, 0.18, n), -0.5, 0.5) * a
            self._hop = np.stack([dx, dy], axis=-1).astype(np.float32)

        self._stripe: np.ndarray | None = None
        st = float(self.v["scanner_stripe"])
        if st > 0:
            g = ctx.rng(f"{self.key}:stripe")
            W = ctx.width
            fine = g.standard_normal(W).astype(np.float32)
            fine = np.convolve(fine, np.ones(3, np.float32) / 3.0, mode="same")
            gain = 1.0 + fine * (0.012 * st)
            for _ in range(int(4 + 8 * st)):               # a few stronger columns
                x0 = int(g.integers(0, W))
                wd = 1 + int(g.integers(0, 3))
                gain[x0:x0 + wd] += float(g.uniform(-0.05, 0.05)) * st
            self._stripe = gain[None, :, None].astype(np.float32)

        self._crop_track: np.ndarray | None = None
        cr = float(self.v["frame_edge_crop"])
        if cr > 0:
            breath = ctx.noise.smooth(f"{self.key}:breath", 0.30)
            wx = ctx.noise.smooth(f"{self.key}:wx", 0.18)
            wy = ctx.noise.smooth(f"{self.key}:wy", 0.14)
            zoom = 1.0 + cr * (0.014 + 0.006 * breath)
            self._crop_track = np.stack(
                [zoom, wx * (2.2 * cr), wy * (2.6 * cr)], axis=-1).astype(np.float32)

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        H, W = frame.shape[:2]
        fi = min(ctx.fi_out, ctx.noise.n - 1)
        # compose hop + crop into a single warp
        zoom, cx, cy = 1.0, 0.0, 0.0
        if self._crop_track is not None:
            z, dx, dy = self._crop_track[min(fi, len(self._crop_track) - 1)]
            zoom, cx, cy = float(z), float(dx), float(dy)
        if self._hop is not None:
            hx, hy = self._hop[min(fi, len(self._hop) - 1)]
            cx += float(hx)
            cy += float(hy)
        if zoom != 1.0 or abs(cx) > 0.01 or abs(cy) > 0.01:
            M = cv2.getRotationMatrix2D((W / 2.0, H / 2.0), 0.0, zoom)
            M[0, 2] += cx
            M[1, 2] += cy
            frame = cv2.warpAffine(frame, M, (W, H), flags=cv2.INTER_LINEAR,
                                   borderMode=cv2.BORDER_REPLICATE)
        if self._stripe is not None:
            stripe = self._stripe
            if stripe.shape[1] != W:                       # preview-size fallback
                stripe = cv2.resize(stripe.reshape(1, -1), (W, 1),
                                    interpolation=cv2.INTER_LINEAR).reshape(1, W, 1)
            frame = frame * stripe
        return np.clip(frame, 0.0, 1.0).astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════
# 2. Transfer-suite auto color pumping
# ═══════════════════════════════════════════════════════════════════════
@register
class AutoColor(Effect):
    eid = "auto_color"
    label = "Auto Color Pump"
    kind = "frame"
    desc = (
        "The transfer deck's automatic correction chasing the picture: white "
        "balance re-targets on scene content with a lag, so hue breathes when "
        "dominant colors change, and auto-levels stretch blacks and whites in "
        "visible stepped jumps."
    )
    PARAMS = (
        Param("wb_pump", "White Balance Pump", "float", 0.35, 0.0, 1.0, iscale=True,
              group="Color",
              desc="Auto white balance driven by whatever's in frame: a red "
                   "jacket walks in and the whole picture leans cyan a half "
                   "second later."),
        Param("level_pump", "Auto Levels Pump", "float", 0.35, 0.0, 1.0, iscale=True,
              group="Levels",
              desc="Per-shot black/white stretching that updates in discrete "
                   "visible steps as scene brightness changes."),
        Param("lag_s", "Reaction Lag", "float", 0.7, 0.1, 3.0, unit="s", group="Color",
              desc="How far the automatics trail the picture."),
    )

    def prepare(self, ctx: Context) -> None:
        self._wb_ema: np.ndarray | None = None
        self._alpha = 1.0 - float(np.exp(-1.0 / (max(self.v["lag_s"], 0.05) * max(ctx.fps, 1.0))))
        self._lv_applied: tuple[float, float] | None = None
        self._lv_step_frames = max(int(0.45 * ctx.fps), 2)
        self._lv_meas: tuple[float, float] = (0.0, 1.0)

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        x = frame
        wb = float(self.v["wb_pump"])
        if wb > 0:
            means = x.reshape(-1, 3).mean(axis=0) + 1e-4
            gray = float(means @ np.asarray([1 / 3, 1 / 3, 1 / 3], np.float32))
            corr = np.clip(gray / means, 0.65, 1.55).astype(np.float32)
            if self._wb_ema is None:
                self._wb_ema = corr
            else:
                self._wb_ema = self._wb_ema + (corr - self._wb_ema) * self._alpha
            gains = 1.0 + (self._wb_ema - 1.0) * (0.85 * wb)
            x = x * gains[None, None, :]

        lv = float(self.v["level_pump"])
        if lv > 0:
            y = x[::4, ::4] @ _LUMA_W
            lo = float(np.percentile(y, 2.0))
            hi = float(np.percentile(y, 98.0))
            self._lv_meas = (lo, hi)
            if self._lv_applied is None:
                self._lv_applied = (lo, hi)
            elif ctx.fi_out % self._lv_step_frames == 0:
                # snap toward the measurement in coarse quantized steps -
                # the visible stair-step of consumer auto-levels
                q = 0.035
                alo, ahi = self._lv_applied
                alo += np.round((lo - alo) / q) * q * 0.6
                ahi += np.round((hi - ahi) / q) * q * 0.6
                self._lv_applied = (float(alo), float(ahi))
            alo, ahi = self._lv_applied
            alo = np.clip(alo, 0.0, 0.35)
            ahi = np.clip(ahi, 0.55, 1.0)
            stretched = (x - alo) / max(ahi - alo, 0.30)
            x = x + (stretched - x) * (0.85 * lv)
        return np.clip(x, 0.0, 1.0).astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════
# 3. DVNR - the over-denoised transfer
# ═══════════════════════════════════════════════════════════════════════
@register
class DVNR(Effect):
    eid = "dvnr"
    label = "DVNR"
    kind = "frame"
    desc = (
        "Aggressive digital video noise reduction, as run on 90s/00s transfers: "
        "temporal averaging that misjudges motion and drags ghost trails, plus "
        "spatial over-smoothing with edge ringing - the waxy DVD look."
    )
    PARAMS = (
        Param("strength", "Temporal Smear", "float", 0.35, 0.0, 1.0, iscale=True,
              group="Temporal",
              desc="Recursive temporal averaging: static areas polish clean, "
                   "moderate motion smears into trailing ghosts. Hard cuts "
                   "punch through."),
        Param("wax", "Waxiness", "float", 0.3, 0.0, 1.0, iscale=True, group="Spatial",
              desc="Spatial over-smooth plus compensating edge sharpen: texture "
                   "melts, edges ring - faces go candle-wax."),
    )

    def prepare(self, ctx: Context) -> None:
        self._prev: np.ndarray | None = None

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        x = frame
        wax = float(self.v["wax"])
        if wax > 0:
            H, W = x.shape[:2]
            half = cv2.resize(x, (max(2, W // 2), max(2, H // 2)),
                              interpolation=cv2.INTER_AREA)
            sm = cv2.bilateralFilter(half, 7, 0.09 + 0.14 * wax, 3.0 + 3.0 * wax)
            x = x + cv2.resize(sm - half, (W, H), interpolation=cv2.INTER_LINEAR)
            blur = cv2.GaussianBlur(x, (0, 0), 1.5)
            x = x + (x - blur) * (0.75 * wax)      # the compensating sharpen rings

        s = float(self.v["strength"])
        if s > 0:
            if self._prev is not None and self._prev.shape == x.shape:
                d = np.abs(x - self._prev) @ _LUMA_W
                d = cv2.GaussianBlur(d, (0, 0), 2.0)
                # weight peaks on static/slow areas, decays on real motion:
                # moderate motion still gets averaged → the DVNR trail
                w = (s * 0.80) * np.exp(-d * np.float32(1.0 / 0.13))
                x = x + (self._prev - x) * w[..., None]
            self._prev = x.copy()                   # recurse on OUTPUT frames
        return np.clip(x, 0.0, 1.0).astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════
# 4. Deinterlace artifacts
# ═══════════════════════════════════════════════════════════════════════
@register
class DeinterlaceArtifact(Effect):
    eid = "deinterlace_artifact"
    label = "Deinterlace Artifact"
    kind = "frame"
    desc = (
        "What a cheap deinterlacer leaves behind - pick your poison: bob (line "
        "twitter and a half-line vertical bounce), weave (leftover mice-teeth "
        "combing on motion), or blend (a 30%-opacity double exposure on "
        "anything moving). The 'uploaded TV rip' tell."
    )
    PARAMS = (
        Param("mode", "Mode", "enum", "bob_shimmer",
              choices=("bob_shimmer", "weave_comb", "blend_ghost"), group="Mode",
              desc="bob_shimmer = half-res fields bounce line to line; "
                   "weave_comb = combing survives on motion; blend_ghost = "
                   "fields averaged into motion ghosts."),
        Param("amount", "Amount", "float", 0.7, 0.0, 1.0, iscale=True, group="Mode",
              desc="How much of the artifact survives whatever player smoothed it."),
    )

    def prepare(self, ctx: Context) -> None:
        self._prev: np.ndarray | None = None

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        a = float(self.v["amount"])
        if a <= 0:
            return frame
        mode = self.v["mode"]
        H, W = frame.shape[:2]
        cur = frame.copy()

        if mode == "bob_shimmer":
            p = ctx.fi_out & 1
            field = frame[p::2]
            up = cv2.resize(field, (W, H), interpolation=cv2.INTER_LINEAR)
            # the parity flip supplies the half-line bounce; fine horizontal
            # detail flickers as it lands on alternating field grids
            out = frame + (up - frame) * a
        elif mode == "weave_comb":
            if self._prev is None or self._prev.shape != frame.shape:
                out = frame
            else:
                d = np.abs(frame - self._prev) @ _LUMA_W
                d = cv2.GaussianBlur(d, (0, 0), 1.6)
                m = smoothstep(0.02, 0.10, d) * a
                out = frame.copy()
                rows = out[1::2]
                mm = m[1::2, :, None]
                rows += (self._prev[1::2] - rows) * mm
        else:  # blend_ghost
            if self._prev is None or self._prev.shape != frame.shape:
                out = frame
            else:
                out = frame + (self._prev - frame) * (0.30 * a)

        self._prev = cur
        return np.clip(out, 0.0, 1.0).astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════
# 5. Upload generations
# ═══════════════════════════════════════════════════════════════════════
@register
class UploadGen(Effect):
    eid = "upload_gen"
    label = "Upload Generations"
    kind = "filepass"
    desc = (
        "Internet re-upload generation loss: each generation is a slight "
        "rescale, a slight sharpen and a real MJPEG re-encode (later "
        "generations approximated frame-side as accumulating blockiness and "
        "ringing), with posterization creeping into smooth gradients."
    )
    PARAMS = (
        Param("gens", "Generations", "int", 2, 1, 5, group="Loss",
              desc="How many times the clip was downloaded and re-uploaded. "
                   "1–2 are real codec round-trips; 3+ pile on approximated "
                   "block/ringing residue."),
        Param("deband_loss", "Gradient Posterize", "float", 0.25, 0.0, 1.0, iscale=True,
              group="Loss",
              desc="Posterization creep in smooth gradients - skies and vignettes "
                   "collapse into contour bands after repeated 8-bit round trips."),
        Param("qscale", "Base Quality", "int", 6, 2, 20, group="Loss",
              desc="MJPEG quantizer of the first re-encode; each generation bumps "
                   "it further down."),
    )

    def file_pass(self, in_path: str, out_path: str, ctx: Context) -> None:
        info = media.probe(in_path)
        gens = int(self.v["gens"])
        deband = float(self.v["deband_loss"])
        g = ctx.rng(f"{self.key}:gens")
        W0, H0 = info.width, info.height

        temps: list[str] = []
        cur = in_path
        try:
            for gi in range(min(gens, 2)):                 # real re-encodes
                scale = 1.0 + float(g.uniform(-0.02, 0.02))
                w2, h2 = _even(W0 * scale), _even(H0 * scale)
                sharp = 0.45 + 0.35 * float(g.random())
                q = int(self.v["qscale"]) + gi * 3
                nxt = f"{out_path}.up{gi}.avi"
                temps.append(nxt)
                media._run(
                    [media.FFMPEG, "-v", "error", "-nostdin", "-y", "-i", cur,
                     "-vf", f"scale={w2}:{h2}:flags=bicubic,unsharp=5:5:{sharp:.2f}:5:5:0.0",
                     "-c:v", "mjpeg", "-q:v", str(q), "-pix_fmt", "yuvj420p",
                     "-an", nxt]
                )
                cur = nxt

            extra = max(gens - 2, 0)
            if extra > 0 or deband > 0:
                self._frame_residue(cur, out_path, info, extra, deband, ctx)
            else:
                media._run(
                    [media.FFMPEG, "-v", "error", "-nostdin", "-y", "-i", cur,
                     "-vf", f"scale={W0}:{H0}:flags=bicubic", *_X264_444, out_path]
                )
        finally:
            for t in temps:
                if os.path.exists(t):
                    os.unlink(t)

    # frame-side approximation of generations 3+ and gradient posterize
    def _frame_residue(self, src: str, dst: str, info: media.MediaInfo,
                       extra: int, deband: float, ctx: Context) -> None:
        W, H, fps = info.width, info.height, info.fps
        writer = media.FrameWriter(dst, W, H, fps, crf=8, preset="fast", pix_fmt="yuv444p")
        bw, bh = max(W // 8, 4), max(H // 8, 4)
        levels = np.float32(30.0)
        try:
            for frame in media.read_frames(src, W, H, fps):
                x = frame
                for _gi in range(extra):
                    # blockiness: pull flat areas toward their 8px block mean
                    blocks = cv2.resize(x, (bw, bh), interpolation=cv2.INTER_AREA)
                    blocks = cv2.resize(blocks, (W, H), interpolation=cv2.INTER_NEAREST)
                    y = x @ _LUMA_W
                    gx = cv2.Sobel(cv2.GaussianBlur(y, (0, 0), 1.2), cv2.CV_32F, 1, 0)
                    gy = cv2.Sobel(cv2.GaussianBlur(y, (0, 0), 1.2), cv2.CV_32F, 0, 1)
                    flat = 1.0 - smoothstep(0.02, 0.12, np.sqrt(gx * gx + gy * gy))
                    x = x + (blocks - x) * (0.16 * flat)[..., None]
                    # ringing: truncated-kernel sharpen overshoot near edges
                    blur = cv2.GaussianBlur(x, (0, 0), 1.1)
                    x = x + (x - blur) * 0.34
                    x = np.clip(x, 0.0, 1.0)
                if deband > 0:
                    y = x @ _LUMA_W
                    gx = cv2.Sobel(cv2.GaussianBlur(y, (0, 0), 2.0), cv2.CV_32F, 1, 0)
                    gy = cv2.Sobel(cv2.GaussianBlur(y, (0, 0), 2.0), cv2.CV_32F, 0, 1)
                    smooth_m = 1.0 - smoothstep(0.015, 0.10, np.sqrt(gx * gx + gy * gy))
                    post = np.round(x * levels) / levels
                    x = x + (post - x) * (deband * smooth_m)[..., None]
                writer.write(np.clip(x, 0.0, 1.0))
        finally:
            writer.close()
