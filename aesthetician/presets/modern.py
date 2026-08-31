"""Modern-family presets: the grades of the multiplex and streaming eras.

These are looks, not damage: color science as art direction, from the
teal-and-orange tentpole to the drained Scandinavian procedural. Most leave
the mix untouched - a grade reached for mid-edit should not rewrite the
sound. Stack an audio preset when the sound should follow.
"""

from ..engine.presets import Preset, Variant, register_preset

register_preset(Preset(
    id="teal-orange-2012",
    name="Teal & Orange",
    family="modern",
    era="2012",
    desc="The tentpole grade: shadows shoved to teal, skin rescued to amber, contrast set to trailer. Somewhere a colorist is doing this to a sunset right now.",
    tagline="Teal shadows, amber skin, trailer punch",
    tags=("modern", "grade", "action", "blockbuster"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.18, "lift": 0.015, "knee": 0.84, "pivot": 0.44}),
        ("balance", {"warmth": 0.15, "shadow_tint": "teal", "shadow_amt": 0.45,
                     "high_tint": "cream", "high_amt": 0.2}),
        ("saturation", {"amount": 1.05, "vibrance": 0.25}),
        ("sharpen", {"amount": 0.3, "radius": 1.0}),
        ("vignette", {"amount": 0.22, "softness": 0.75}),
    ],
    audio=[],
    variants=[
        Variant("poster", "Poster Grade", "Cranked until the thumbnail sells itself.",
                video={"balance.shadow_amt": 0.6, "balance.warmth": 0.22,
                       "tone.contrast": 1.28, "saturation.vibrance": 0.4}),
        Variant("prestige", "Prestige Dial-Back", "The same idea wearing a tasteful coat.",
                video={"balance.shadow_amt": 0.25, "balance.warmth": 0.08,
                       "tone.contrast": 1.1, "saturation.vibrance": 0.12}),
    ],
))

register_preset(Preset(
    id="digital-green-1999",
    name="Terminal Green",
    family="modern",
    era="1999",
    desc="Reality with a rendering problem: green sunk into every midtone, skin gone server-room pale, blacks deep enough to hide the code - the office scenes are the tell.",
    tagline="Green midtones, pale skin, code blacks",
    tags=("modern", "grade", "scifi", "90s"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.22, "lift": 0.01, "knee": 0.82, "pivot": 0.4}),
        ("balance", {"tint": -0.22, "shadow_tint": "green", "shadow_amt": 0.35}),
        ("saturation", {"amount": 0.85, "hue": -4.0}),
        ("grain", {"amount": 0.22, "size": 1.5, "chroma_grain": 0.1, "stock": "fine_35"}),
        ("halation", {"strength": 0.15, "tint": "neutral"}),
        ("vignette", {"amount": 0.3, "softness": 0.65}),
    ],
    audio=[],
    variants=[
        Variant("inside", "Inside the System", "Full immersion: greener, colder, wronger.",
                video={"balance.tint": -0.32, "balance.shadow_amt": 0.5,
                       "saturation.amount": 0.75}),
        Variant("desert-of-the-real", "Desert of the Real", "The other grade: blue-gray truth, no green anywhere.",
                video={"balance.tint": 0.0, "balance.shadow_tint": "blue",
                       "balance.shadow_amt": 0.35, "balance.warmth": -0.12,
                       "saturation.amount": 0.7}),
    ],
))

register_preset(Preset(
    id="border-yellow-2000",
    name="Border Yellow",
    family="modern",
    era="2000",
    desc="The establishing-shot passport stamp: everything south of the cut bathed piss-yellow and heat-hazed, as if the sun filed a location report. Cross back north and the blue returns.",
    tagline="Piss-yellow heat, hazed highlights",
    tags=("modern", "grade", "thriller", "00s"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.14, "lift": 0.03, "knee": 0.8}),
        ("balance", {"warmth": 0.4, "tint": -0.08, "high_tint": "yellow", "high_amt": 0.5}),
        ("saturation", {"amount": 1.08, "vibrance": 0.1}),
        ("optics", {"diffusion": 0.12, "veiling_flare": 0.15}),
        ("grain", {"amount": 0.25, "size": 1.6, "chroma_grain": 0.12}),
        ("vignette", {"amount": 0.25, "softness": 0.7}),
    ],
    audio=[],
    variants=[
        Variant("heat-shimmer", "Heat Shimmer", "Noon: the haze thickens and the sky goes white.",
                video={"optics.diffusion": 0.22, "optics.veiling_flare": 0.3,
                       "tone.exposure": 0.15, "balance.high_amt": 0.6}),
        Variant("north-of-the-line", "North of the Line", "The answering grade: steel blue, no dust.",
                video={"balance.warmth": -0.18, "balance.high_tint": "cyan",
                       "balance.high_amt": 0.25, "saturation.amount": 0.9}),
    ],
))

register_preset(Preset(
    id="nordic-noir-2011",
    name="Nordic Noir",
    family="modern",
    era="2011",
    desc="Procedural weather: slate blue dusk at all hours, color rationed like daylight in December, knitwear and grief in the same drained palette.",
    tagline="Slate dusk, rationed color, cold air",
    tags=("modern", "grade", "crime", "scandinavia"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.06, "lift": 0.05, "knee": 0.86}),
        ("balance", {"warmth": -0.16, "tint": 0.02, "shadow_tint": "blue", "shadow_amt": 0.3}),
        ("saturation", {"amount": 0.72, "vibrance": 0.1}),
        ("optics", {"soft_focus": 0.06}),
        ("grain", {"amount": 0.18, "size": 1.4, "chroma_grain": 0.08}),
        ("vignette", {"amount": 0.28, "softness": 0.7}),
    ],
    audio=[],
    variants=[
        Variant("midnight-sun", "Midnight Sun", "Summer case: pale, sleepless, overexposed.",
                video={"tone.exposure": 0.25, "tone.lift": 0.08, "saturation.amount": 0.65,
                       "balance.warmth": -0.08}),
        Variant("polar-night", "Polar Night", "Winter case: sodium lamps against the dark.",
                video={"tone.exposure": -0.25, "balance.shadow_amt": 0.45,
                       "balance.high_tint": "yellow", "balance.high_amt": 0.25}),
    ],
))

register_preset(Preset(
    id="moonlight-blue-2015",
    name="Moonlight Blue",
    family="modern",
    era="2015",
    desc="Day-for-night, digital edition: two stops under and drowned in blue, highlights held for one impossible moon, faces lit by a darkness you can somehow read by.",
    tagline="Two stops under, drowned in blue",
    tags=("modern", "grade", "night", "dfn"),
    upscale="sharp",
    video=[
        ("tone", {"exposure": -0.5, "contrast": 1.12, "knee": 0.8, "pivot": 0.35}),
        ("balance", {"warmth": -0.3, "tint": 0.05, "shadow_tint": "blue", "shadow_amt": 0.5}),
        ("saturation", {"amount": 0.7}),
        ("optics", {"diffusion": 0.1}),
        ("grain", {"amount": 0.22, "size": 1.5, "chroma_grain": 0.1, "shadow_boost": 0.3}),
        ("vignette", {"amount": 0.35, "softness": 0.6}),
    ],
    audio=[],
    variants=[
        Variant("deep-night", "Deep Night", "Three stops down: shapes, breath, glinting eyes.",
                video={"tone.exposure": -0.85, "saturation.amount": 0.55,
                       "vignette.amount": 0.5}),
        Variant("blue-hour", "Blue Hour", "The honest twenty minutes the fake is imitating.",
                video={"tone.exposure": -0.2, "balance.shadow_amt": 0.35,
                       "saturation.amount": 0.85}),
    ],
))

register_preset(Preset(
    id="moody-crush-2016",
    name="Crushed & Moody",
    family="modern",
    era="2016",
    desc="The music-video midnight: blacks crushed to vinyl, highlights kept on a short leash, one color allowed to survive per scene - texture optional, attitude mandatory.",
    tagline="Vinyl blacks, leashed whites, one color",
    tags=("modern", "grade", "musicvideo", "moody"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.3, "lift": -0.05, "knee": 0.8, "pivot": 0.38}),
        ("balance", {"shadow_tint": "blue", "shadow_amt": 0.2}),
        ("saturation", {"amount": 0.9, "vibrance": 0.3}),
        ("sharpen", {"amount": 0.2, "radius": 1.2}),
        ("grain", {"amount": 0.2, "size": 1.5, "chroma_grain": 0.08, "shadow_boost": 0.25}),
        ("vignette", {"amount": 0.4, "softness": 0.55}),
    ],
    audio=[],
    variants=[
        Variant("smoke-machine", "Smoke Machine", "Haze in the beams, glow on everything bright.",
                video={"tone.lift": -0.02, "vignette.amount": 0.3,
                       "saturation.vibrance": 0.4}),
        Variant("all-the-way-down", "All the Way Down", "Silhouettes and speculars only.",
                video={"tone.lift": -0.1, "tone.contrast": 1.45, "saturation.amount": 0.8,
                       "vignette.amount": 0.55}),
    ],
))

register_preset(Preset(
    id="neon-noir-2018",
    name="Neon Noir",
    family="modern",
    era="2018",
    desc="Rain-slick synthetic night: magenta soaking the shadows, cyan burning the edges, every wet surface a second screen - the city as an arcade cabinet.",
    tagline="Magenta shadows, cyan burn, wet glow",
    tags=("modern", "grade", "neon", "night"),
    upscale="sharp",
    video=[
        ("tone", {"exposure": -0.1, "contrast": 1.2, "lift": 0.01, "knee": 0.8, "pivot": 0.4}),
        ("balance", {"shadow_tint": "magenta", "shadow_amt": 0.45,
                     "high_tint": "cyan", "high_amt": 0.35}),
        ("saturation", {"amount": 1.25, "vibrance": 0.2}),
        ("optics", {"diffusion": 0.18}),
        ("crt", {"bloom": 0.3, "bloom_radius": 16.0, "glass_glow": 0.15}),
        ("grain", {"amount": 0.2, "size": 1.4, "chroma_grain": 0.1, "shadow_boost": 0.25}),
        ("vignette", {"amount": 0.35, "softness": 0.6}),
    ],
    audio=[],
    variants=[
        Variant("arcade", "Arcade Floor", "More glow, more color, less restraint.",
                video={"crt.bloom": 0.45, "saturation.amount": 1.4,
                       "balance.shadow_amt": 0.6}),
        Variant("last-call", "Last Call", "The neon dying: dimmer, sadder, almost mono.",
                video={"tone.exposure": -0.3, "saturation.amount": 0.95,
                       "balance.high_amt": 0.2, "crt.bloom": 0.2}),
    ],
))

register_preset(Preset(
    id="pastel-pop-2019",
    name="Pastel Pop",
    family="modern",
    era="2019",
    desc="The brand-safe daydream: blacks lifted to charcoal-never, pinks and mints in gentle agreement, light with no opinions - a grade you could serve with oat milk.",
    tagline="Lifted blacks, mint-pink calm, soft light",
    tags=("modern", "grade", "pastel", "social"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 0.94, "lift": 0.09, "knee": 0.9, "gamma": 0.96}),
        ("balance", {"warmth": 0.06, "tint": 0.06, "high_tint": "pink", "high_amt": 0.25}),
        ("saturation", {"amount": 1.08, "vibrance": 0.2}),
        ("optics", {"diffusion": 0.1, "bloom_mids": 0.15}),
        ("vignette", {"amount": 0.12, "softness": 0.8}),
    ],
    audio=[],
    variants=[
        Variant("sunroom", "Sunroom", "Warmer and brighter, plants thriving just off frame.",
                video={"tone.exposure": 0.2, "balance.warmth": 0.14,
                       "balance.high_tint": "cream"}),
        Variant("mall-mint", "Mall Mint", "The cool half of the palette takes over.",
                video={"balance.tint": -0.06, "balance.warmth": -0.06,
                       "balance.high_tint": "cyan", "balance.high_amt": 0.18}),
    ],
))

register_preset(Preset(
    id="streaming-filmic-2021",
    name="Streaming Filmic",
    family="modern",
    era="2021",
    desc="Prestige-drama house style: a gentle S-curve, warm-neutral skin, a breath of synthetic grain and halation so the 8K sensor can pretend it went to film school.",
    tagline="Soft S-curve, faux grain, sensor cosplay",
    tags=("modern", "grade", "prestige", "streaming"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.1, "lift": 0.025, "knee": 0.85, "pivot": 0.43}),
        ("balance", {"warmth": 0.06, "shadow_tint": "teal", "shadow_amt": 0.15,
                     "high_tint": "cream", "high_amt": 0.15}),
        ("saturation", {"amount": 0.98, "vibrance": 0.12}),
        ("grain", {"amount": 0.22, "size": 1.4, "chroma_grain": 0.1, "stock": "fine_35",
                   "layers": "color_neg"}),
        ("halation", {"strength": 0.15, "tint": "red_orange", "threshold": 0.78}),
        ("vignette", {"amount": 0.18, "softness": 0.8}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[],
    variants=[
        Variant("limited-series", "Limited Series", "Darker and tealer: someone is hiding something.",
                video={"tone.exposure": -0.15, "balance.shadow_amt": 0.28,
                       "saturation.amount": 0.9}),
        Variant("full-frame", "Full Frame", "The same grade without the letterbox costume.",
                video={"framing.aspect": "none"}),
    ],
))
