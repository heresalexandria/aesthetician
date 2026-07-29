"""Asset pack manifest: AI-generated overlay plates.

Plates live under assets/packs/<pack>/NN.png (gitignored — regenerate with
`aesthetician assets generate`). Every effect that can use plates also has a
procedural fallback, so a fresh clone works without them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from ..engine.render import default_asset_root


@dataclass(frozen=True)
class Pack:
    name: str
    desc: str
    count: int
    size: str            # OpenAI size string
    mode: str            # screen (black bg, additive) | multiply (white bg) | gray (texture)
    prompts: tuple[str, ...]  # cycled to reach count


PACKS: dict[str, Pack] = {
    "film_dust": Pack(
        name="film_dust",
        desc="Dust, fibers and hairs on black — screen-blended over film looks",
        count=8,
        size="1024x1536",
        mode="screen",
        prompts=(
            "Photorealistic scan of film gate dust on a pure black background: sparse scattered tiny white dust particles, a few short thin fibers, high contrast, no vignette, no text, evenly distributed, documentary archival plate",
            "Pure black background with scattered small white specks of dirt and two or three fine curved hairs, like dirt on an old 16mm film print, photoreal, high contrast, no glow",
            "Black background dust overlay plate: very sparse fine white particles of varied tiny sizes with occasional slightly larger fleck, film restoration reference, crisp focus",
        ),
    ),
    "light_leaks": Pack(
        name="light_leaks",
        desc="Warm light leaks on black — screen-blended camera leaks",
        count=8,
        size="1536x1024",
        mode="screen",
        prompts=(
            "Analog film light leak overlay on pure black background: soft warm orange-red organic glow entering from the left edge, gently feathered, photochemical look, no text",
            "Analog film light leak plate, pure black background, amber and magenta soft streaks sweeping from the top right corner, dreamy soft falloff, photoreal",
            "Vintage camera light leak on black: a soft vertical warm red-orange band with subtle yellow core near the frame edge, gradual falloff, organic irregular shape",
            "Subtle light leak overlay, black background, faint warm golden haze creeping from the bottom edge with small hot spot, soft and organic",
        ),
    ),
    "film_burns": Pack(
        name="film_burns",
        desc="Film burn / chemical decay plates on black",
        count=6,
        size="1536x1024",
        mode="screen",
        prompts=(
            "Burning film frame effect on pure black background: glowing orange-brown scorched edges with bright white-hot bubbling core, photochemical film burn, organic irregular shapes, no text",
            "Old film chemical decay overlay on black: mottled amber and sepia blotches with bright eaten-away patches, nitrate decomposition look, organic texture",
            "Film burn transition plate on black background: warm orange flare blooming with dark charred crackle texture around it, photoreal archival damage",
        ),
    ),
    "grime": Pack(
        name="grime",
        desc="Projector glass grime and smudges on black — subtle screen overlay",
        count=6,
        size="1024x1536",
        mode="screen",
        prompts=(
            "Dirty projector glass overlay on pure black background: faint gray smudges, fingerprint traces and greasy streaks, very subtle low contrast, photoreal, no text",
            "Dusty old lens grime plate on black: soft faint blotches and hazy patches with a few tiny bright dust points, subtle, archival",
        ),
    ),
    "paper_textures": Pack(
        name="paper_textures",
        desc="Cel board / paper textures (neutral gray) — overlay-blended for cartoon looks",
        count=6,
        size="1024x1536",
        mode="gray",
        prompts=(
            "Flat even scan of vintage animation cel board: neutral light gray paper texture with very subtle fibers and fine tooth, uniform lighting, no shadows, no vignette, no text",
            "Neutral gray vintage watercolor paper texture scan, extremely subtle grain and fibers, flat even illumination, seamless feel, no text",
            "Flat scan of aged drawing board paper, neutral mid-gray, faint mottling and fiber texture, even light, archival reproduction",
        ),
    ),
    "tape_creases": Pack(
        name="tape_creases",
        desc="VHS tape crease / damage streak plates on black",
        count=6,
        size="1536x1024",
        mode="screen",
        prompts=(
            "Horizontal white noise streaks on pure black background: a few thin ragged horizontal lines of static with small gaps, like VHS tape crease dropout damage, sharp, no text",
            "VHS dropout overlay plate: pure black background with sparse bright horizontal dashes and comet-tail streaks of white static at varying lengths, photoreal analog video damage",
        ),
    ),
}


def pack_dir(name: str) -> str:
    return os.path.join(default_asset_root(), "packs", name)


def pack_files(name: str) -> list[str]:
    d = pack_dir(name)
    if not os.path.isdir(d):
        return []
    return sorted(
        os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith((".png", ".jpg", ".jpeg"))
    )


def pack_status() -> dict[str, dict]:
    return {
        name: {"desc": p.desc, "count": p.count, "present": len(pack_files(name))}
        for name, p in PACKS.items()
    }
