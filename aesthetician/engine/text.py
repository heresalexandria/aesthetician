"""Caption typography: bundled fonts, layout, and styled text-block rasterization.

Everything here is deterministic for a given input: FreeType rasterization is
stable per font file, and the only stochastic dressing (the etched-print edge)
draws from the seeded stream helpers in rng.py. Effects cache the returned
blocks per cue, so a caption that holds for seconds costs one rasterization.

The 5x7 dot-matrix glyphs live here so the timestamp/OSD effects and the
dotmatrix caption face share one table; overlay.py imports DOT_GLYPHS.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import cv2

from .rng import stream

FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "fonts")


# ── bundled faces ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class FontFace:
    file: str
    italic_file: str | None = None   # None: synthesize italic with a shear
    weight: int | None = None        # variation axis value for variable fonts
    pixel: int = 1                   # >1: rasterize small, threshold, block-upscale
    upper_only: bool = False


FONTS: dict[str, FontFace] = {
    "cc_mono": FontFace("ShareTechMono-Regular.ttf"),
    "mono": FontFace("SpaceMono-Regular.ttf"),
    "mono_bold": FontFace("SpaceMono-Bold.ttf"),
    "teletext": FontFace("bedstead.otf", pixel=2),
    "sans": FontFace("Arimo-Variable.ttf", italic_file="Arimo-Italic-Variable.ttf"),
    "sans_bold": FontFace("Arimo-Variable.ttf", italic_file="Arimo-Italic-Variable.ttf", weight=700),
    "serif": FontFace("Tinos-Regular.ttf", italic_file="Tinos-Italic.ttf"),
    "serif_bold": FontFace("Tinos-Bold.ttf"),
    "typewriter": FontFace("CourierPrime-Regular.ttf"),
    "typewriter_bold": FontFace("CourierPrime-Bold.ttf"),
    "heavy": FontFace("Anton-Regular.ttf"),
    "bookface": FontFace("OldStandard-Regular.ttf", italic_file="OldStandard-Italic.ttf"),
    "dotmatrix": FontFace("", upper_only=True),   # in-repo bitmap face below
}

FONT_CHOICES = tuple(FONTS.keys())


def hex_rgb(value: str, fallback=(1.0, 1.0, 1.0)) -> tuple[float, float, float]:
    """'FFCC00' or '#fc0' to float RGB. Bad input falls back quietly."""
    s = str(value).strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        return fallback
    try:
        return tuple(int(s[i : i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return fallback


@lru_cache(maxsize=64)
def _load_font(fname: str, size: int, weight: int | None):
    from PIL import ImageFont

    font = ImageFont.truetype(os.path.join(FONT_DIR, fname), size)
    if weight is not None:
        try:
            font.set_variation_by_axes([float(weight)])
        except Exception:
            pass                     # static fallback keeps the default weight
    return font


@lru_cache(maxsize=64)
def _sized_font(fname: str, line_h: int, weight: int | None):
    """A font whose ascent+descent lands on the requested line height."""
    probe = _load_font(fname, 100, weight)
    asc, desc = probe.getmetrics()
    size = max(6, int(round(100.0 * line_h / max(asc + desc, 1))))
    return _load_font(fname, size, weight)


def _balanced(words: list[str], width: int) -> list[str]:
    """Break a run of words into lines that come out even.

    Greedy wrapping fills the first line to the brim and leaves a stub trailing
    under it - the classic lopsided two-line subtitle. Subtitle houses set the
    same text as two lines of roughly equal length instead, so this minimizes
    the squared slack of *every* line, the last one included: a paragraph
    setter would leave the final line ragged, a caption never should.
    """
    n = len(words)
    if n <= 1:
        return list(words)
    inf = float("inf")
    cost = [inf] * n + [0.0]        # cost[i]: best layout of words[i:]
    brk = list(range(1, n + 2))     # brk[i]: where the line starting at i ends
    for i in range(n - 1, -1, -1):
        length = -1
        for j in range(i, n):
            length += len(words[j]) + 1
            if length > width:
                if j > i:
                    break
                c = cost[j + 1]     # a word wider than the line goes alone
            else:
                slack = width - length
                c = slack * slack + cost[j + 1]
            if c < cost[i]:
                cost[i] = c
                brk[i] = j + 1
    out: list[str] = []
    i = 0
    while i < n:
        j = brk[i]
        out.append(" ".join(words[i:j]))
        i = j
    return out


def wrap_lines(text: str, line_chars: int) -> list[str]:
    """Balanced word wrap honoring manual newlines. Never drops characters."""
    width = max(int(line_chars), 4)
    out: list[str] = []
    for para in str(text).replace("\r", "").split("\n"):
        words = para.split()
        if not words:
            out.append("")
            continue
        run: list[str] = []
        for w in words:
            while len(w) > width:
                # A word too long for any line has to break mid-word. Its head
                # becomes a line of its own rather than joining the run, so no
                # later join can smuggle a space into the middle of the word.
                if run:
                    out.extend(_balanced(run, width))
                    run = []
                out.append(w[:width])
                w = w[width:]
            if w:
                run.append(w)
        if run:
            out.extend(_balanced(run, width))
    while out and out[-1] == "":
        out.pop()
    return out or [""]


# ── 5x7 dot-matrix face (shared with overlay.py) ───────────────────────

DOT_GLYPHS = {
    "0": ".XXX.|X...X|X..XX|X.X.X|XX..X|X...X|.XXX.",
    "1": "..X..|.XX..|..X..|..X..|..X..|..X..|.XXX.",
    "2": ".XXX.|X...X|....X|...X.|..X..|.X...|XXXXX",
    "3": "XXXXX|....X|...X.|..XX.|....X|X...X|.XXX.",
    "4": "...X.|..XX.|.X.X.|X..X.|XXXXX|...X.|...X.",
    "5": "XXXXX|X....|XXXX.|....X|....X|X...X|.XXX.",
    "6": "..XX.|.X...|X....|XXXX.|X...X|X...X|.XXX.",
    "7": "XXXXX|....X|...X.|..X..|.X...|.X...|.X...",
    "8": ".XXX.|X...X|X...X|.XXX.|X...X|X...X|.XXX.",
    "9": ".XXX.|X...X|X...X|.XXXX|....X|...X.|.XX..",
    "A": ".XXX.|X...X|X...X|XXXXX|X...X|X...X|X...X",
    "B": "XXXX.|X...X|X...X|XXXX.|X...X|X...X|XXXX.",
    "C": ".XXX.|X...X|X....|X....|X....|X...X|.XXX.",
    "D": "XXXX.|X...X|X...X|X...X|X...X|X...X|XXXX.",
    "E": "XXXXX|X....|X....|XXXX.|X....|X....|XXXXX",
    "F": "XXXXX|X....|X....|XXXX.|X....|X....|X....",
    "G": ".XXX.|X...X|X....|X.XXX|X...X|X...X|.XXXX",
    "H": "X...X|X...X|X...X|XXXXX|X...X|X...X|X...X",
    "I": ".XXX.|..X..|..X..|..X..|..X..|..X..|.XXX.",
    "J": "..XXX|...X.|...X.|...X.|...X.|X..X.|.XX..",
    "K": "X...X|X..X.|X.X..|XX...|X.X..|X..X.|X...X",
    "L": "X....|X....|X....|X....|X....|X....|XXXXX",
    "M": "X...X|XX.XX|X.X.X|X.X.X|X...X|X...X|X...X",
    "N": "X...X|X...X|XX..X|X.X.X|X..XX|X...X|X...X",
    "O": ".XXX.|X...X|X...X|X...X|X...X|X...X|.XXX.",
    "P": "XXXX.|X...X|X...X|XXXX.|X....|X....|X....",
    "Q": ".XXX.|X...X|X...X|X...X|X.X.X|X..X.|.XX.X",
    "R": "XXXX.|X...X|X...X|XXXX.|X.X..|X..X.|X...X",
    "S": ".XXXX|X....|X....|.XXX.|....X|....X|XXXX.",
    "T": "XXXXX|..X..|..X..|..X..|..X..|..X..|..X..",
    "U": "X...X|X...X|X...X|X...X|X...X|X...X|.XXX.",
    "V": "X...X|X...X|X...X|X...X|X...X|.X.X.|..X..",
    "W": "X...X|X...X|X...X|X.X.X|X.X.X|XX.XX|X...X",
    "X": "X...X|X...X|.X.X.|..X..|.X.X.|X...X|X...X",
    "Y": "X...X|X...X|.X.X.|..X..|..X..|..X..|..X..",
    "Z": "XXXXX|....X|...X.|..X..|.X...|X....|XXXXX",
    ":": ".....|..XX.|..XX.|.....|..XX.|..XX.|.....",
    "/": "....X|....X|...X.|..X..|.X...|X....|X....",
    "-": ".....|.....|.....|XXXXX|.....|.....|.....",
    ".": ".....|.....|.....|.....|.....|.XX..|.XX..",
    " ": ".....|.....|.....|.....|.....|.....|.....",
    # punctuation added for caption text (the OSD effects never used these)
    ",": ".....|.....|.....|.....|.XX..|.XX..|.X...",
    "'": "..XX.|..XX.|..X..|.....|.....|.....|.....",
    "!": "..X..|..X..|..X..|..X..|..X..|.....|..X..",
    "?": ".XXX.|X...X|....X|...X.|..X..|.....|..X..",
    '"': ".X.X.|.X.X.|.X.X.|.....|.....|.....|.....",
    "(": "...X.|..X..|.X...|.X...|.X...|..X..|...X.",
    ")": ".X...|..X..|...X.|...X.|...X.|..X..|.X...",
    "&": ".XX..|X..X.|X.X..|.X...|X.X.X|X..X.|.XX.X",
    "+": ".....|..X..|..X..|XXXXX|..X..|..X..|.....",
    "#": ".X.X.|.X.X.|XXXXX|.X.X.|XXXXX|.X.X.|.X.X.",
    ";": ".....|..XX.|..XX.|.....|..XX.|..XX.|.X...",
    "%": "XX..X|XX.X.|...X.|..X..|.X...|.X.XX|X..XX",
    "=": ".....|.....|XXXXX|.....|XXXXX|.....|.....",
    "*": ".....|X.X.X|.XXX.|XXXXX|.XXX.|X.X.X|.....",
    "<": "...X.|..X..|.X...|X....|.X...|..X..|...X.",
    ">": ".X...|..X..|...X.|....X|...X.|..X..|.X...",
    "[": ".XXX.|.X...|.X...|.X...|.X...|.X...|.XXX.",
    "]": ".XXX.|...X.|...X.|...X.|...X.|...X.|.XXX.",
    "@": ".XXX.|X...X|X.XXX|X.X.X|X.XX.|X....|.XXX.",
    "♪": "...X.|...XX|...X.|...X.|.XXX.|XXXX.|.XX..",
}

_DOT_FONT = {
    ch: np.array([[c == "X" for c in row] for row in rows.split("|")], np.float32)
    for ch, rows in DOT_GLYPHS.items()
}
_DGW, _DGH, _DADV, _DLINE = 5, 7, 6, 9


# ── block rasterization ────────────────────────────────────────────────

@dataclass
class TextBlock:
    """A rasterized caption block plus the geometry reveals need."""

    rgb: np.ndarray                       # (h, w, 3) float32
    alpha: np.ndarray                     # (h, w) float32 in 0..1
    w: int
    h: int
    line_boxes: list[tuple[int, int, int, int]]   # per line: x0, y0, x1, y1 (layout extents)
    char_cols: list[list[tuple[int, int]]]        # per line, per char: x0, x1 column span
    n_chars: int
    # Where the ink actually is. The layout boxes span a full em - ascender to
    # descender - which is what the roll-up window and the decoder cells are
    # drawn from, but centering on it hangs a line of capitals visibly high in
    # its own strap. Placement and the bbox the plan reports use this instead.
    ink: tuple[int, int, int, int] = (0, 0, 0, 0)


def _dot_masks(lines, line_h, align, spacing):
    scale = max(1, int(round(line_h / float(_DLINE))))
    adv, gh = _DADV * scale, _DGH * scale
    step = max(int(round(_DLINE * scale * spacing / 1.0)), gh + scale)
    widths = [max(len(s), 1) * adv - scale for s in lines]
    W = max(widths)
    H = (len(lines) - 1) * step + gh
    mask = np.zeros((H, W), np.float32)
    line_boxes, char_cols = [], []
    for li, line in enumerate(lines):
        x = 0 if align == "left" else (W - widths[li] if align == "right" else (W - widths[li]) // 2)
        y = li * step
        cols = []
        for ch in line.upper():
            glyph = _DOT_FONT.get(ch)
            if glyph is not None:
                big = np.kron(glyph, np.ones((scale, scale), np.float32))
                mask[y : y + gh, x : x + _DGW * scale] = np.maximum(
                    mask[y : y + gh, x : x + _DGW * scale], big)
            cols.append((x, x + adv))
            x += adv
        line_boxes.append((cols[0][0] if cols else 0, y, x - scale if cols else 0, y + gh))
        char_cols.append(cols)
    if scale > 1:
        mask = cv2.GaussianBlur(mask, (0, 0), 0.55)
    return mask, line_boxes, char_cols


def _ttf_masks(lines, face, italic, line_h, align, spacing, weight):
    from PIL import Image, ImageDraw

    pixel = max(1, int(face.pixel))
    lh = max(6, line_h // pixel)
    fname = face.italic_file if (italic and face.italic_file) else face.file
    font = _sized_font(fname, lh, weight)
    asc, desc = font.getmetrics()
    step = max(int(round(lh * spacing)), asc + desc)
    widths = [max(int(np.ceil(font.getlength(s))), 1) for s in lines]
    shear = 0.22 if (italic and not face.italic_file) else 0.0
    W = max(widths) + int(np.ceil(shear * lh))
    H = (len(lines) - 1) * step + asc + desc
    img = Image.new("L", (max(W, 1), max(H, 1)), 0)
    draw = ImageDraw.Draw(img)
    line_boxes, char_cols = [], []
    for li, line in enumerate(lines):
        x = 0 if align == "left" else (W - widths[li] if align == "right" else (W - widths[li]) // 2)
        y = li * step
        draw.text((x, y), line, font=font, fill=255)
        cols, run = [], 0.0
        for i, _ch in enumerate(line):
            nxt = font.getlength(line[: i + 1])
            cols.append((x + int(round(run)), x + int(round(nxt))))
            run = nxt
        line_boxes.append((x, y, x + widths[li], y + asc + desc))
        char_cols.append(cols)
    mask = np.asarray(img, np.float32) / 255.0
    if shear > 0.0:
        # The warp samples src(x + shear*y), so ink slides left as y grows:
        # bottom lines lean left of the top, which is the italic. Two
        # consequences handled here: the mask needs left padding so the lowest
        # line cannot slide off the canvas, and the per-character geometry has
        # to lean with the ink or reveals would clip the slanted glyphs.
        pad_l = int(np.ceil(shear * mask.shape[0]))
        mask = np.pad(mask, ((0, 0), (pad_l, 0)))
        line_boxes = [(x0 + pad_l, y0, x1 + pad_l, y1) for x0, y0, x1, y1 in line_boxes]
        char_cols = [[(a + pad_l, b + pad_l) for a, b in cols] for cols in char_cols]
        M = np.float32([[1.0, shear, 0.0], [0.0, 1.0, 0.0]])
        mask = cv2.warpAffine(mask, M, (mask.shape[1], mask.shape[0]), flags=cv2.INTER_LINEAR)
        sheared_boxes, sheared_cols = [], []
        for (x0, y0, x1, y1), cols in zip(line_boxes, char_cols):
            sheared_boxes.append((int(x0 - shear * y1), y0, int(np.ceil(x1 - shear * y0)), y1))
            sheared_cols.append([(int(a - shear * y1), int(np.ceil(b - shear * y0))) for a, b in cols])
        line_boxes, char_cols = sheared_boxes, sheared_cols
    if pixel > 1:
        mask = (mask > 0.45).astype(np.float32)
        mask = np.kron(mask, np.ones((pixel, pixel), np.float32))
        line_boxes = [(x0 * pixel, y0 * pixel, x1 * pixel, y1 * pixel) for x0, y0, x1, y1 in line_boxes]
        char_cols = [[(a * pixel, b * pixel) for a, b in cols] for cols in char_cols]
    return mask, line_boxes, char_cols


def _over(base_rgb, base_a, layer_rgb, layer_a):
    """Standard 'over' compositing of a flat-color layer onto the block."""
    a = np.clip(layer_a, 0.0, 1.0)[..., None]
    out_a = np.clip(layer_a + base_a * (1.0 - layer_a), 0.0, 1.0)
    safe = np.maximum(out_a, 1e-6)[..., None]
    out_rgb = (np.asarray(layer_rgb, np.float32) * a + base_rgb * base_a[..., None] * (1.0 - a)) / safe
    return out_rgb, out_a


def _ink_rect(mask: np.ndarray, fallback: list[tuple[int, int, int, int]]) -> tuple[int, int, int, int]:
    """Tight bounds of the drawn ink, before any edge treatment widens it."""
    cols = np.nonzero(mask.max(axis=0) > 0.02)[0]
    rows = np.nonzero(mask.max(axis=1) > 0.02)[0]
    if not len(cols) or not len(rows):
        # A cue with nothing in it (or only spaces) still has to report a box
        # something can be placed and dragged by, so fall back to the layout.
        xs0 = [b[0] for b in fallback] or [0]
        ys0 = [b[1] for b in fallback] or [0]
        xs1 = [b[2] for b in fallback] or [mask.shape[1]]
        ys1 = [b[3] for b in fallback] or [mask.shape[0]]
        return min(xs0), min(ys0), max(xs1), max(ys1)
    return int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1


def render_block(
    text: str,
    font: str = "sans",
    italic: bool = False,
    line_h: int = 24,
    line_chars: int = 32,
    spacing: float = 1.15,
    align: str = "center",
    color: tuple[float, float, float] = (1.0, 1.0, 1.0),
    edge: str = "outline",
    edge_strength: float = 0.5,
    edge_color: tuple[float, float, float] = (0.0, 0.0, 0.0),
    box: str = "none",
    box_color: tuple[float, float, float] = (0.0, 0.0, 0.0),
    box_opacity: float = 0.75,
    upper: bool = False,
    etch_seed: int = 0,
) -> TextBlock:
    """Rasterize one caption into a self-contained RGBA block.

    `box` here covers the text-hugging modes (cells: one snug bar per line the
    way Line-21 decoders drew them; block: one rectangle around everything).
    Frame-wide bands and full-frame cards are the caller's business since they
    depend on frame geometry.
    """
    face = FONTS.get(font) or FONTS["sans"]
    if upper or face.upper_only:
        text = str(text).upper()
    lines = wrap_lines(text, line_chars)
    line_h = max(int(line_h), 6)
    if font == "dotmatrix":
        mask, line_boxes, char_cols = _dot_masks(lines, line_h, align, spacing)
    else:
        mask, line_boxes, char_cols = _ttf_masks(lines, face, italic, line_h, align, spacing,
                                                 face.weight)
    es = float(np.clip(edge_strength, 0.0, 1.0))
    # Kept as a float: the outline is drawn from a distance field, so a rim
    # narrower than a pixel is a legitimate thing to ask for and rounding it up
    # to 1 was what made small captions look like they were set in a slab.
    out_px = line_h * (0.045 + 0.075 * es) if edge in ("outline", "outline_shadow") else 0.0
    sh_px = max(1, int(round(line_h * (0.04 + 0.08 * es)))) if edge in ("shadow", "outline_shadow") else 0
    sh_blur = line_h * (0.012 + 0.05 * es) if sh_px else 0.0
    glow_sigma = line_h * (0.06 + 0.22 * es) if edge == "glow" else 0.0
    pad = int(np.ceil(max(out_px + 2.0, sh_px + sh_blur * 3.0, glow_sigma * 2.5, line_h * 0.28))) + 1
    mask = np.pad(mask, pad)
    line_boxes = [(x0 + pad, y0 + pad, x1 + pad, y1 + pad) for x0, y0, x1, y1 in line_boxes]
    char_cols = [[(a + pad, b + pad) for a, b in cols] for cols in char_cols]
    h, w = mask.shape

    if edge == "etch":
        # laser-etched print subtitles: bright core, nibbled edges
        noise = stream(etch_seed, f"caption-etch:{text}").random((h, w)).astype(np.float32)
        noise = cv2.GaussianBlur(noise, (0, 0), max(line_h * 0.02, 0.6))
        erode = np.clip((noise - 0.35) * (1.6 + 1.4 * es), 0.0, 1.0)
        mask = np.clip(mask - erode * 0.5 * es * (mask > 0), 0.0, 1.0)

    rgb = np.zeros((h, w, 3), np.float32)
    alpha = np.zeros((h, w), np.float32)

    if box in ("cells", "block"):
        box_a = np.zeros((h, w), np.float32)
        hpad = max(2, int(round(line_h * 0.22)))
        vpad = max(1, int(round(line_h * 0.10)))
        if box == "cells":
            for x0, y0, x1, y1 in line_boxes:
                if x1 > x0:
                    box_a[max(y0 - vpad, 0) : y1 + vpad, max(x0 - hpad, 0) : x1 + hpad] = 1.0
        else:
            xs = [b for lb in line_boxes for b in (lb[0], lb[2])]
            ys = [b for lb in line_boxes for b in (lb[1], lb[3])]
            if xs:
                box_a[max(min(ys) - vpad, 0) : max(ys) + vpad,
                      max(min(xs) - hpad, 0) : max(xs) + hpad] = 1.0
        rgb, alpha = _over(rgb, alpha, box_color, box_a * float(np.clip(box_opacity, 0.0, 1.0)))

    if sh_px:
        # A drop shadow is cast light, not a second copy of the letter. Offset
        # then blurred, so it reads as depth instead of the hard stair-stepped
        # duplicate that used to sit behind every serif subtitle.
        sh = np.zeros_like(mask)
        sh[sh_px:, sh_px:] = mask[:-sh_px, :-sh_px]
        if sh_blur > 0.35:
            sh = cv2.GaussianBlur(sh, (0, 0), sh_blur)
        rgb, alpha = _over(rgb, alpha, edge_color, np.clip(sh * (0.55 + 0.35 * es), 0.0, 1.0))
    if out_px >= 0.35:
        # The rim follows the letterform: distance out from the glyph, softened
        # over the last pixel, rather than a square max-filter that put right
        # angles on the corners of every round letter. It is laid down whole and
        # the glyph goes over it, so the antialiased edge of the type blends
        # into the rim instead of being punched out of it.
        d = cv2.distanceTransform((mask < 0.5).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
        ring = np.maximum(np.clip(out_px + 0.5 - d, 0.0, 1.0), mask)
        rgb, alpha = _over(rgb, alpha, edge_color, ring * (0.75 + 0.25 * es))
    if glow_sigma > 0.0:
        glow = cv2.GaussianBlur(mask, (0, 0), glow_sigma)
        rgb, alpha = _over(rgb, alpha, color, np.clip(glow * (0.5 + 0.5 * es), 0.0, 0.85))
    rgb, alpha = _over(rgb, alpha, color, mask)

    n_chars = sum(len(cols) for cols in char_cols)
    return TextBlock(rgb=rgb, alpha=alpha, w=w, h=h,
                     line_boxes=line_boxes, char_cols=char_cols, n_chars=n_chars,
                     ink=_ink_rect(mask, line_boxes))


# ── reveal masks (animated caption modes) ──────────────────────────────

def reveal_chars(block: TextBlock, n_visible: int) -> np.ndarray:
    """0/1 multiplier exposing the first n characters in reading order."""
    out = np.zeros((block.h, block.w), np.float32)
    left = int(max(n_visible, 0))
    for (x0, y0, x1, y1), cols in zip(block.line_boxes, block.char_cols):
        if left <= 0:
            break
        take = min(left, len(cols))
        if take > 0:
            xe = cols[take - 1][1]
            out[: y1 + max(2, (y1 - y0) // 3), : xe + 2] = 1.0
        left -= take
    if left > 0:
        out[:, :] = 1.0
    return out


def reveal_sweep(block: TextBlock, frac: float) -> np.ndarray:
    """0/1 column sweep across the text extent (karaoke fill boundary)."""
    xs = [b for lb in block.line_boxes for b in (lb[0], lb[2])]
    if not xs:
        return np.zeros((block.h, block.w), np.float32)
    x0, x1 = min(xs), max(xs)
    edge = int(round(x0 + (x1 - x0) * float(np.clip(frac, 0.0, 1.0))))
    out = np.zeros((block.h, block.w), np.float32)
    out[:, :edge] = 1.0
    return out
