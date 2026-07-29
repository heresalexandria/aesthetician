"""Chemical decay of the element itself: vinegar syndrome, water damage,
nitrate decomposition and sticky-shed tape binder failure.

These artifacts live on the print/tape, not in the scene, so their temporal
randomness keys on ctx.fi_out — decay keeps crawling even while a cadence
effect holds a source frame. All fields are built from slowly-crossfading
multi-octave noise (no geometric primitives), optionally enriched by the
"film_burns" plate pack when it is present, so nothing reads as procedural.
"""

from __future__ import annotations

import numpy as np
import cv2

from ...assets import store
from ...engine import color
from ...engine.graph import Context, Effect, Param, register
from .film import _EvolvingField


def _octaves(g: np.random.Generator, H: int, W: int,
             spec: tuple[tuple[int, float], ...]) -> np.ndarray:
    """Static multi-octave noise field, ~N(0,1), organic at every scale."""
    acc = np.zeros((H, W), np.float32)
    for cells, wgt in spec:
        gh = max(cells, 3)
        gw = max(int(round(cells * W / max(H, 1))), 3)
        f = g.standard_normal((gh, gw)).astype(np.float32)
        f = cv2.GaussianBlur(f, (0, 0), 0.85)
        acc += wgt * cv2.resize(f, (W, H), interpolation=cv2.INTER_LINEAR)
    acc /= float(acc.std()) + 1e-6
    return acc


def _edge_reach(H: int, W: int, span: float) -> np.ndarray:
    """1 at the frame edge → 0 by `span` (fraction of the short side) inward."""
    nx = np.minimum(np.arange(W, dtype=np.float32), np.arange(W - 1, -1, -1, dtype=np.float32))
    ny = np.minimum(np.arange(H, dtype=np.float32), np.arange(H - 1, -1, -1, dtype=np.float32))
    s = min(H, W)
    d = np.minimum(nx[None, :], ny[:, None]) / max(s, 1)
    return (1.0 - color.smoothstep(0.0, span, d)).astype(np.float32)


# ── vinegar syndrome ───────────────────────────────────────────────────


@register
class Vinegar(Effect):
    eid = "vinegar"
    label = "Vinegar Syndrome"
    kind = "frame"
    desc = ("Acetate base decay: the film buckles into slow wavy distortion, the color layers physically "
            "separate into locally varying red/blue vertical offsets, and a milky blotchy haze veils the image.")
    PARAMS = (
        Param("warp", "Buckle Warp", "float", 0.35, 0.0, 1.0, iscale=True, group="Decay",
              desc="Local low-frequency wavy geometric distortion from the shrinking, channeling base — "
                   "evolves very slowly, like the film breathing in the gate."),
        Param("channel_split", "Layer Separation", "float", 0.2, 0.0, 1.0, iscale=True, group="Decay",
              desc="Dye layers delaminating: red/blue vertical offsets that vary ACROSS the frame rather "
                   "than shifting globally."),
        Param("haze", "Crystal Haze", "float", 0.25, 0.0, 1.0, iscale=True, group="Decay",
              desc="Milky veil with blotchy structure — plasticizer exudation and crystal bloom on the base."),
    )

    def prepare(self, ctx: Context) -> None:
        ar = ctx.width / max(ctx.height, 1)
        gw = max(int(round(7 * ar)), 3)
        self._fx = _EvolvingField(f"{self.key}:wx", 7, gw, 0.085, sigma=1.0)
        self._fy = _EvolvingField(f"{self.key}:wy", 7, gw, 0.070, sigma=1.0)
        self._fs = _EvolvingField(f"{self.key}:cs", 9, max(int(round(9 * ar)), 4), 0.055, sigma=0.9)
        self._fh = _EvolvingField(f"{self.key}:hz", 8, max(int(round(8 * ar)), 4), 0.045, sigma=0.9)
        self._grid: tuple | None = None

    def _base_grid(self, H: int, W: int) -> tuple[np.ndarray, np.ndarray]:
        if self._grid is None or self._grid[0].shape != (H, W):
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            self._grid = (xx, yy)
        return self._grid

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        H, W = frame.shape[:2]
        t = ctx.fi_out / max(ctx.fps, 1.0)
        warp, split, haze = self.v["warp"], self.v["channel_split"], self.v["haze"]

        if warp > 0 or split > 0:
            xx, yy = self._base_grid(H, W)
            if warp > 0:
                xmap = xx + self._fx.sample(ctx, t, W, H) * np.float32(warp * 0.0110 * H)
                ymap = yy + self._fy.sample(ctx, t, W, H) * np.float32(warp * 0.0085 * H)
            else:
                xmap, ymap = xx, yy
            if split > 0:
                sf = self._fs.sample(ctx, t, W, H) * np.float32(split * 3.0 * H / 720.0)
                out = np.empty_like(frame)
                if warp > 0:
                    out[..., 1] = cv2.remap(np.ascontiguousarray(frame[..., 1]), xmap, ymap,
                                            cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
                else:
                    out[..., 1] = frame[..., 1]
                out[..., 0] = cv2.remap(np.ascontiguousarray(frame[..., 0]), xmap, ymap + sf,
                                        cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
                out[..., 2] = cv2.remap(np.ascontiguousarray(frame[..., 2]), xmap, ymap - 0.8 * sf,
                                        cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
                frame = out
            else:
                frame = cv2.remap(frame, xmap, ymap, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

        if haze > 0:
            hb = self._fh.sample(ctx, t, W, H)
            blotch = color.smoothstep(-0.5, 1.6, hb)
            v = haze * (0.09 + 0.19 * blotch)
            for ci, milk in enumerate((0.85, 0.83, 0.76)):
                fc = frame[..., ci]
                fc *= 1.0 - v
                fc += v * milk
            np.clip(frame, 0.0, 1.0, out=frame)
        return frame


# ── water damage ───────────────────────────────────────────────────────


@register
class WaterDamage(Effect):
    eid = "water_damage"
    label = "Water Damage"
    kind = "frame"
    desc = ("Flooded-archive stains: dark-edged tide marks that drift and breathe as the waterline they "
            "record, and patches of small ring-shaped emulsion blisters.")
    PARAMS = (
        Param("tide_marks", "Tide Marks", "float", 0.5, 0.0, 1.0, iscale=True, group="Decay",
              desc="Irregular stain boundaries with the dark mineral ring at the edge — the interior "
                   "discolors gently, the waterline is what you see."),
        Param("blistering", "Blistering", "float", 0.25, 0.0, 1.0, iscale=True, group="Decay",
              desc="Clusters of small circular emulsion blisters: bright-ringed dots where the gelatin "
                   "lifted, appearing in patches."),
    )

    def prepare(self, ctx: Context) -> None:
        ar = ctx.width / max(ctx.height, 1)
        self._tf = _EvolvingField(f"{self.key}:tide", 6, max(int(round(6 * ar)), 3), 0.030, sigma=1.05)
        self._th = ctx.noise.smooth(f"{self.key}:th", 0.045)
        self._bbreath = ctx.noise.smooth(f"{self.key}:bb", 0.06)
        self._rag: np.ndarray | None = None
        self._blist: tuple | None = None

    def _ragged(self, H: int, W: int, ctx: Context) -> np.ndarray:
        if self._rag is None or self._rag.shape != (H, W):
            g = ctx.rng(f"{self.key}:rag")
            self._rag = _octaves(g, H, W, ((16, 0.55), (42, 0.30), (110, 0.16)))
        return self._rag

    def _blisters(self, H: int, W: int, ctx: Context) -> tuple[np.ndarray, np.ndarray]:
        if self._blist is None or self._blist[0].shape != (H, W):
            g = ctx.rng(f"{self.key}:bl")
            ring = np.zeros((H, W), np.float32)
            core = np.zeros((H, W), np.float32)
            sc = max(H / 720.0, 0.5)
            nc = 1 + int(g.random() < 0.7) + int(g.random() < 0.35)
            for _ in range(nc):
                cx, cy = g.uniform(0.12, 0.88) * W, g.uniform(0.12, 0.88) * H
                spread = g.uniform(0.045, 0.11) * H
                count = int(g.integers(14, 46))
                xs = g.normal(cx, spread, count)
                ys = g.normal(cy, spread * g.uniform(0.7, 1.3), count)
                for j in range(count):
                    r = max(int(round(g.uniform(1.4, 4.2) * sc)), 1)
                    p = (int(xs[j]), int(ys[j]))
                    val = float(g.uniform(0.45, 0.95))
                    cv2.circle(ring, p, r, val, 1, cv2.LINE_AA)
                    if r > 1:
                        cv2.circle(core, p, r - 1, val * 0.6, -1, cv2.LINE_AA)
            ring = cv2.GaussianBlur(ring, (0, 0), 0.55)
            core = cv2.GaussianBlur(core, (0, 0), 0.55)
            self._blist = (np.clip(ring, 0.0, 1.0), np.clip(core, 0.0, 1.0))
        return self._blist

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        H, W = frame.shape[:2]
        fi = ctx.fi_out
        t = fi / max(ctx.fps, 1.0)
        tm = self.v["tide_marks"]
        if tm > 0:
            F = self._tf.sample(ctx, t, W, H) + 0.4 * self._ragged(H, W, ctx)
            th = 0.52 + 0.09 * float(self._th[min(fi, len(self._th) - 1)])
            interior = color.smoothstep(th, th + 0.34, F)
            ring = color.smoothstep(th - 0.055, th + 0.005, F) * (1.0 - color.smoothstep(th + 0.005, th + 0.11, F))
            th2 = th - 0.24  # an older, fainter waterline further out
            ring2 = color.smoothstep(th2 - 0.045, th2, F) * (1.0 - color.smoothstep(th2, th2 + 0.08, F))
            dark = tm * (0.18 * interior + 0.60 * ring + 0.22 * ring2)
            # mineral browns: blue dies first, red survives
            for ci, wc in enumerate((0.55, 0.78, 1.0)):
                frame[..., ci] *= 1.0 - dark * wc
        bl = self.v["blistering"]
        if bl > 0:
            ring, core = self._blisters(H, W, ctx)
            breath = 0.82 + 0.18 * float(self._bbreath[min(fi, len(self._bbreath) - 1)])
            a = bl * breath
            for ci in range(3):
                fc = frame[..., ci]
                fc *= 1.0 - core * (a * 0.30)
                fc += ring * (a * 0.5) * (1.0 - fc)
            np.clip(frame, 0.0, 1.0, out=frame)
        return frame


# ── nitrate decomposition ──────────────────────────────────────────────


@register
class NitrateDecay(Effect):
    eid = "nitrate"
    label = "Nitrate Decomposition"
    kind = "frame"
    desc = ("The five stages of nitrate base decay: amber edge fog, spreading stains, bubbling emulsion "
            "with dark rims, and finally molten honey-colored voids swallowing the image. Built from "
            "multi-octave fields (plus burn plates when present) so every boundary is organic.")
    PARAMS = (
        Param("stage", "Decay Stage", "int", 3, 1, 5, group="Decay",
              desc="1 amber edge fog · 2 spreading stain · 3 bubbling emulsion patches with dark rims · "
                   "4 patches merge, goo deepens · 5 molten voids with honey edges."),
        Param("spread", "Spread", "float", 0.5, 0.0, 1.0, iscale=True, group="Decay",
              desc="Area coverage of the decay at the chosen stage (0.5 is the nominal look; it also "
                   "creeps very slightly over the clip)."),
    )

    #        area  fog  stain molten rim  deep  bubble
    _STAGE = {
        1: (0.10, 0.52, 0.00, 0.00, 0.00, 0.00, 0.05),
        2: (0.16, 0.66, 0.60, 0.00, 0.10, 0.00, 0.08),
        3: (0.24, 0.55, 0.85, 0.90, 0.80, 0.30, 0.20),
        4: (0.40, 0.65, 1.00, 0.96, 0.88, 0.65, 0.26),
        5: (0.62, 0.75, 1.00, 1.00, 0.92, 1.00, 0.15),
    }

    def prepare(self, ctx: Context) -> None:
        ar = ctx.width / max(ctx.height, 1)
        stage = self.v["stage"]
        rate = (0.22, 0.30, 0.55, 0.72, 0.45)[stage - 1]
        self._bub = _EvolvingField(f"{self.key}:bub", 16, max(int(round(16 * ar)), 6), rate, sigma=0.8)
        self._btex = _EvolvingField(f"{self.key}:btex", 42, max(int(round(42 * ar)), 14),
                                    rate * 1.4, sigma=0.7)
        self._grow = ctx.noise.smooth(f"{self.key}:grow", 0.035)
        self._pidx = int(ctx.rng(f"{self.key}:plate").integers(0, 1 << 20))
        self._built: tuple | None = None

    def _build(self, H: int, W: int, ctx: Context) -> None:
        if self._built is not None and self._built[0].shape == (H, W):
            return
        g = ctx.rng(f"{self.key}:field")
        # mid-heavy octaves → distinct islands rather than one continent
        D = _octaves(g, H, W, ((5, 0.85), (13, 0.80), (34, 0.42), (90, 0.20)))
        D += _edge_reach(H, W, 0.50) * 0.85          # decay works in from the reel edge
        ptex = None
        if store.n_plates("film_burns") > 0:
            p = store.plate("film_burns", self._pidx, W, H)
            if p is not None:
                pl = p.mean(axis=-1)
                pl = cv2.GaussianBlur(pl, (0, 0), 2.2)
                pl = (pl - float(pl.mean())) / (float(pl.std()) + 1e-6)
                D += 0.38 * pl                        # organic islands from the plate
                ptex = np.clip(pl * 0.5 + 0.5, 0.0, 1.5)  # texture octave for the goo
        D = cv2.GaussianBlur(D, (0, 0), 1.2)
        # static fine detail: breaks rims, chars flecks into the goo
        fine = _octaves(g, H, W, ((130, 0.8), (60, 0.5)))
        qs = np.quantile(D[::4, ::4], np.linspace(0.0, 1.0, 257)).astype(np.float32)
        reach = _edge_reach(H, W, 0.55)
        self._built = (D.astype(np.float32), qs, ptex, fine.astype(np.float32), reach)

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        H, W = frame.shape[:2]
        fi = ctx.fi_out
        t = fi / max(ctx.fps, 1.0)
        stage = self.v["stage"]
        area0, k_fog, k_stain, k_molten, k_rim, k_deep, a_bub = self._STAGE[stage]
        self._build(H, W, ctx)
        D0, qs, ptex, fine, reach = self._built

        # coverage: spread scales the stage's nominal area, breathing slightly
        # and creeping forward over the clip — decay never retreats
        g01 = fi / max(ctx.n_frames - 1, 1)
        breathe = 1.0 + 0.05 * float(self._grow[min(fi, len(self._grow) - 1)])
        area = area0 * (0.30 + 1.40 * self.v["spread"]) * breathe * (0.92 + 0.14 * g01)
        area = float(np.clip(area, 0.004, 0.90))
        th = float(qs[int(round((1.0 - area) * 256))])

        Da = D0
        if a_bub > 0:
            Da = D0 + self._bub.sample(ctx, t, W, H) * np.float32(a_bub)

        amber = np.asarray((1.00, 0.66, 0.28), np.float32)
        if k_fog > 0:
            # fog reaches well beyond the active decay boundary
            af = float(np.clip(area * 2.6 + 0.05, 0.02, 0.88))
            th_f = float(qs[int(round((1.0 - af) * 256))])
            fog = color.smoothstep(th_f - 0.30, th_f + 0.30, Da)
            if stage <= 2:
                # early decay: the fog is an edge phenomenon
                fog *= 0.30 + 0.70 * reach
            v = (k_fog * 0.40) * fog
            for ci in range(3):
                fc = frame[..., ci]
                fc *= 1.0 - v * (0.30 + 0.40 * (1.0 - amber[ci]))
                fc += v * amber[ci] * 0.80

        if k_stain > 0:
            st = color.smoothstep(th - 0.14, th + 0.08, Da)
            sv = k_stain * 0.24 * st
            # stain browns and densifies without hiding the image yet
            for ci, wc in enumerate((0.10, 0.32, 0.60)):
                frame[..., ci] *= 1.0 - sv * wc

        if k_molten > 0:
            bt = self._btex.sample(ctx, t, W, H)
            bubtex = np.clip(0.5 + 0.5 * bt, 0.0, 1.0)
            if ptex is not None:
                bubtex = np.clip(0.68 * bubtex + 0.38 * ptex, 0.0, 1.05)
            m_in = color.smoothstep(th + 0.02, th + 0.17, Da)
            depth = color.smoothstep(th + 0.03, th + 0.36, Da)      # 0 fringe → 1 core
            # goo: warm tar-amber at the fringe, luminous honey toward the core,
            # bubble cells modulating density throughout
            glow = (0.30 + 0.70 * depth) * (0.40 + 0.60 * bubtex)
            goo_r = 0.70 + 0.34 * glow
            goo_g = 0.34 + 0.50 * glow
            goo_b = 0.09 + 0.36 * glow * glow
            # translucent fringe: the image drowns gradually
            alpha = m_in * (k_molten * (0.40 + 0.60 * depth)) * (0.82 + 0.18 * bubtex)
            np.clip(alpha, 0.0, 0.96, out=alpha)
            for ci, gc in enumerate((goo_r, goo_g, goo_b)):
                fc = frame[..., ci]
                fc *= 1.0 - alpha
                fc += alpha * gc
            # charred flecks trapped in the goo — sparse, mostly late-stage
            fleck = color.smoothstep(1.5, 2.1, fine) * m_in * (0.2 + 0.8 * k_deep)
            if float(fleck.max()) > 1e-3:
                fl = np.clip(fleck * 0.6, 0.0, 0.75)
                for ci, rc in enumerate((0.26, 0.11, 0.04)):
                    fc = frame[..., ci]
                    fc *= 1.0 - fl
                    fc += fl * rc
            if k_deep > 0:
                # the heart of the void: hot honey-white, image fully consumed
                m_deep = color.smoothstep(th + 0.24, th + 0.46, Da)
                a2 = m_deep * k_deep
                for ci, (hc, hm) in enumerate(((1.00, 0.14), (0.90, 0.22), (0.62, 0.34))):
                    fc = frame[..., ci]
                    hot = hc - hm * (1.0 - bubtex)
                    fc *= 1.0 - a2
                    fc += a2 * hot

        if k_rim > 0:
            rim = color.smoothstep(th - 0.022, th + 0.022, Da) * \
                (1.0 - color.smoothstep(th + 0.022, th + 0.085, Da))
            rim *= k_rim * (0.45 + 0.55 * color.smoothstep(-0.9, 0.9, fine))  # broken, not ruled
            # scorched tar line where the goo meets surviving image
            a3 = rim * 0.72
            for ci, rc in enumerate((0.30, 0.13, 0.05)):
                fc = frame[..., ci]
                fc *= 1.0 - a3
                fc += a3 * rc

        return np.clip(frame, 0.0, 1.0, out=frame)


# ── sticky-shed syndrome (tape) ────────────────────────────────────────


@register
class StickyShed(Effect):
    eid = "sticky_shed"
    label = "Sticky-Shed Tape"
    kind = "frame"
    desc = ("Binder hydrolysis on tape: bouts of full-width luma dropout bands with smeared trails, arriving "
            "in waves that worsen over the clip as the shedding oxide gums the heads.")
    PARAMS = (
        Param("severity", "Severity", "float", 0.5, 0.0, 1.0, iscale=True, group="Decay",
              desc="How badly the binder has gone: sets both the frequency of dropout bouts and how deep "
                   "and smeared the bands get. Bouts cluster and worsen toward the end."),
    )

    def prepare(self, ctx: Context) -> None:
        n = ctx.n_frames
        sev = self.v["severity"]
        self._env = np.zeros(n, np.float32)
        if sev > 0:
            bout = ctx.noise.smooth(f"{self.key}:bout", 0.22)
            t01 = np.arange(n, dtype=np.float32) / max(n - 1, 1)
            worsen = 0.30 + 0.70 * t01
            th = 1.02 - 0.92 * sev * worsen
            self._env = np.clip((bout[:n] - th) / 0.35, 0.0, 1.0).astype(np.float32)
        self._bands: list[dict] = []

    def process(self, frame: np.ndarray, ctx: Context) -> np.ndarray:
        fi = ctx.fi_out
        e = float(self._env[min(fi, len(self._env) - 1)])
        if e <= 0 and not self._bands:
            return frame
        H, W = frame.shape[:2]
        sev = self.v["severity"]
        g = ctx.frame_rng(f"{self.key}:bands")
        p = e * (0.25 + 0.75 * sev)
        while g.random() < p and len(self._bands) < 6:
            self._bands.append(dict(
                y=float(g.uniform(0.04, 0.96)),
                h=float(g.uniform(0.006, 0.020) + 0.020 * e),
                life=int(g.integers(2, 9)),
                drift=float(g.uniform(-0.004, 0.009)),
                depth=float(g.uniform(0.40, 0.9)) * (0.5 + 0.5 * e),
            ))
            p *= 0.45
        alive: list[dict] = []
        for b in self._bands:
            y0 = int(np.clip(b["y"] * H, 0, H - 2))
            rows = max(int(b["h"] * H), 2)
            y1 = min(y0 + rows, H)
            region = frame[y0:y1]
            # the head loses lock: the line smears into a horizontal trail
            smear = cv2.blur(region, (max(int(W * 0.09), 9) | 1, 1))
            depth = b["depth"] * (0.6 + 0.4 * float(g.random()))
            nz = g.standard_normal((y1 - y0, W), dtype=np.float32) * (0.05 * depth)
            wprof = np.sin(np.linspace(0.0, np.pi, y1 - y0, dtype=np.float32))[:, None, None]
            mix = np.clip(wprof * depth, 0.0, 0.96)
            region *= 1.0 - mix
            region += mix * (smear * (1.0 - 0.55 * depth) + 0.02)
            region += nz[..., None] * mix
            b["y"] += b["drift"]
            b["life"] -= 1
            if b["life"] > 0 and 0.0 < b["y"] < 1.0:
                alive.append(b)
        self._bands = alive
        return np.clip(frame, 0.0, 1.0, out=frame)
