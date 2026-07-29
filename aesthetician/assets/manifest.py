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
    "water_stains": Pack(
        name="water_stains",
        desc="Water damage tide marks on white — multiply-blended",
        count=6,
        size="1024x1536",
        mode="multiply",
        prompts=(
            "Pure white background with large light-brown water stain tide marks: irregular organic rings with darker edges, like water-damaged archival paper or film, photoreal scan, no text",
            "White background, faint sepia water damage blotches with pronounced darker rim lines and pale centers, organic irregular shapes reaching in from one corner, archival damage scan",
        ),
    ),
    "mold": Pack(
        name="mold",
        desc="Mold and fungus growth on white — multiply-blended",
        count=6,
        size="1024x1536",
        mode="multiply",
        prompts=(
            "Pure white background with scattered dark olive-brown mold spots: clustered organic dots with fuzzy halos, some joining into patches, like mold on archival film, photoreal, no text",
            "White background with delicate branching gray-green mildew colonies radiating from the edges, fine organic filament texture, archival decay reference, no text",
        ),
    ),
    "emulsion_decay": Pack(
        name="emulsion_decay",
        desc="Bubbling emulsion / nitrate decay cellular texture on black",
        count=6,
        size="1536x1024",
        mode="screen",
        prompts=(
            "Pure black background with amber-honey colored bubbling cellular texture patches: organic rounded blisters with glowing rims, like decaying nitrate film emulsion, photoreal macro, no text",
            "Black background with mottled golden-brown chemical decay islands: crackled dried-liquid texture with bright edges and dark centers, film decomposition macro, no text",
        ),
    ),
    "copier_streaks": Pack(
        name="copier_streaks",
        desc="Photocopier toner streaks on white — multiply-blended",
        count=4,
        size="1024x1536",
        mode="multiply",
        prompts=(
            "Pure white background with faint vertical gray toner streaks and bands of photocopier roller marks, sparse speckles of toner dust, subtle, photoreal xerox artifact scan, no text",
            "White background with light vertical banding and scattered toner specks like a tired photocopier, very subtle grays, no text",
        ),
    ),
    "glass_glare": Pack(
        name="glass_glare",
        desc="Window/room reflections on black — screen-blended over CRT glass",
        count=6,
        size="1536x1024",
        mode="screen",
        prompts=(
            "Pure black background with a faint soft gray window reflection: a subtle bright parallelogram with dimmer pane divisions, very low contrast, like a room reflected in a turned-on CRT television screen, no text",
            "Black background with soft dim reflections of a living room lamp glow and a curtained window, extremely subtle gray shapes, glass reflection plate, no text",
        ),
    ),
    "lens_dirt": Pack(
        name="lens_dirt",
        desc="Lens dust, smudges and fingerprints on black — screen-blended",
        count=6,
        size="1536x1024",
        mode="screen",
        prompts=(
            "Pure black background with faint gray fingerprint smudges and scattered soft dust bokeh circles of varying sizes, subtle lens contamination plate, photoreal, no text",
            "Black background with dim greasy smear arcs and a few soft out-of-focus dust discs, projector lens dirt overlay, low contrast, no text",
        ),
    ),
    "screen_textures": Pack(
        name="screen_textures",
        desc="Projection screen / glass-bead surface macro (neutral gray) — overlay-blended",
        count=4,
        size="1024x1536",
        mode="gray",
        prompts=(
            "Flat even macro scan of a glass-beaded projection screen surface: neutral mid-gray with fine sparkling bead texture, uniform illumination, no vignette, no text",
            "Neutral gray macro of woven matte projection screen fabric, extremely fine regular weave texture, flat even lighting, no text",
        ),
    ),
    "static_discharge": Pack(
        name="static_discharge",
        desc="Static electricity discharge branches on black — screen-blended",
        count=6,
        size="1024x1536",
        mode="screen",
        prompts=(
            "Pure black background with thin white branching electrostatic discharge streaks: delicate lightning-like tendrils radiating from one edge, sharp fine lines with slight glow, photoreal film static discharge, no text",
            "Black background, a few fine white jagged electric discharge branches with tiny side twigs, like static marks on undeveloped film, high contrast, no text",
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
