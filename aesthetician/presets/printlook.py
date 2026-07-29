"""Print-family presets: the moving image pretending to be ink on paper —
halftone screens, toner, microfilm and duplicator inks."""

from ..engine.presets import Preset, Variant, register_preset

register_preset(Preset(
    id="front-page-1946",
    name="Front Page",
    family="print",
    era="1946",
    desc="Above the fold: one coarse 45-degree screen, ink gaining into gray newsprint, contrast pushed until the photo shouts as loud as the headline.",
    tags=("40s", "newspaper", "halftone", "bw"),
    upscale="sharp",
    video=[
        ("mono", {"response": "panchromatic"}),
        ("tone", {"contrast": 1.35, "lift": 0.02, "knee": 0.8}),
        ("halftone", {"process": "newspaper_bw", "lpi": 30.0, "paper": 0.5, "ink_tone": 1.15}),
        ("paper_texture", {"amount": 0.05, "scale": 1.2}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 120.0, "high_hz": 5000.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_transcription_disc", {"band": 1.0, "swish": 0.5, "crackle": 4.0, "wear": 0.4}),
        ("a_tube_amp", {"drive": 1.8, "sag": 0.4, "hum_db": -54.0}),
        ("a_compressor", {"ratio": 4.0}),
    ],
    variants=[
        Variant("late-edition", "Late Edition", "The presses in a hurry: coarser screen, heavier ink.",
                video={"halftone.lpi": 24.0, "halftone.ink_tone": 1.3, "halftone.paper": 0.6}),
        Variant("wirephoto", "Wirephoto", "Transmitted overnight: crunchy contrast under the screen.",
                video={"tone.contrast": 1.6, "halftone.lpi": 38.0}),
    ],
))

register_preset(Preset(
    id="sunday-comics-1972",
    name="Sunday Funnies",
    family="print",
    era="1972",
    desc="Four fat rosettes of CMYK on butcher-grade paper: the yellow plate a hair east of the others, colors louder than the sermon you skipped.",
    tags=("70s", "comics", "halftone", "cmyk"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.15, "lift": 0.03}),
        ("saturation", {"amount": 1.25, "vibrance": 0.2}),
        ("halftone", {"process": "comic_cmyk", "lpi": 32.0, "paper": 0.55, "misregister": 1.4,
                      "ink_tone": 1.05}),
        ("paper_texture", {"amount": 0.05, "scale": 1.2}),
    ],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_am_radio", {"static_db": -50.0, "pump": 0.4}),
        ("a_speaker", {"device": "portable_radio_1975", "strength": 0.6}),
        ("a_hum", {"hz": 60, "level_db": -52.0}),
    ],
    variants=[
        Variant("pulp-cheap", "Pulp Cheap", "The syndicate's economy run: chunkier dots, wilder plates.",
                video={"halftone.lpi": 26.0, "halftone.misregister": 2.0, "halftone.paper": 0.7}),
        Variant("file-copy", "File Copy", "The engraver's proof: tight register, cleaner stock.",
                video={"halftone.misregister": 0.5, "halftone.paper": 0.35}),
    ],
))

register_preset(Preset(
    id="zine-photocopy-1981",
    name="Xerox Zine",
    family="print",
    era="1981",
    desc="Fourth-generation Xerox gospel: detail clogged to pure black and white, toner starving in streaks, the page always a few degrees off square.",
    tags=("80s", "zine", "photocopy", "punk", "bw"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.15, "lift": 0.05, "exposure": 0.35}),
        ("photocopy", {"generations": 4, "toner": 0.3, "roller_marks": 0.15, "skew": 0.35,
                       "mono": True}),
        ("plate", {"pack": "copier_streaks", "opacity": 0.15, "blend": "multiply", "cycle": "hold",
                   "mono": True}),
        ("paper_texture", {"amount": 0.06, "scale": 1.3}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 60.0, "high_hz": 9000.0}),
        ("a_tape_sat", {"drive": 3.0, "bump_db": 3.5}),
        ("a_wow_flutter", {"wow_depth": 8.0, "flutter_depth": 6.0}),
        ("a_distortion", {"type": "soft", "drive": 1.8}),
        ("a_tape_hiss", {"level_db": -38.0, "type": "cassette"}),
        ("a_compressor", {"ratio": 4.0}),
    ],
    variants=[
        Variant("master", "The Master", "First pass off the original paste-up: merely gritty.",
                video={"photocopy.generations": 2, "photocopy.toner": 0.3, "plate.opacity": 0.06}),
        Variant("tenth-gen", "Tenth Generation", "Copied from a copy from a friend of a copy.",
                video={"photocopy.generations": 6, "photocopy.toner": 0.7, "plate.opacity": 0.28}),
    ],
))

register_preset(Preset(
    id="microfilm-morgue-1958",
    name="Microfilm Morgue",
    family="print",
    era="1958",
    desc="The newspaper morgue at reading speed: red-blind document film, a glare blob wandering the reader screen, roller scratches shimmering through fifty years of Tuesdays.",
    tags=("50s", "microfilm", "library", "bw"),
    proc_height=600,
    upscale="soft",
    video=[
        ("tone", {"contrast": 1.05, "lift": 0.05, "exposure": 0.55}),
        ("microfilm", {"contrast": 0.45, "reader_glare": 0.4, "scratches_scan": 0.45,
                       "frame_border": 0.55}),
        ("flicker", {"amount": 0.1, "character": "slow_drift"}),
        ("dust", {"density": 0.3}),
    ],
    audio=[
        ("a_gain", {"db": -60.0}),
        ("a_bed", {"bed": "fluorescent_office", "level_db": -30.0}),
        ("a_hum", {"hz": 60, "level_db": -46.0, "buzz": 0.3}),
    ],
    variants=[
        Variant("keep-sound", "Keep Sound", "Retain the (treated) original audio under the reading room.",
                audio={"a_gain.db": -6.0}),
        Variant("duped-reel", "Duped Reel", "A copy of the master fiche: harder blacks, more scratches.",
                video={"microfilm.contrast": 0.65, "microfilm.scratches_scan": 0.7}),
    ],
))

register_preset(Preset(
    id="riso-flyer-1985",
    name="Riso Gig Flyer",
    family="print",
    era="1985",
    desc="Two drums, one basement: blue doing the drawing, red arriving two pixels late, stencil grain chewing the midtones. Doors at eight, bring earplugs.",
    tags=("80s", "risograph", "flyer", "diy"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.18, "lift": 0.02}),
        ("riso_print", {"inks": "blue_red", "misregister": 2.4, "grain_ink": 0.55, "paper": 0.7}),
        ("paper_texture", {"amount": 0.06, "scale": 1.3}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 70.0, "high_hz": 10000.0}),
        ("a_tape_sat", {"drive": 2.2, "bump_db": 3.0}),
        ("a_wow_flutter", {"wow_depth": 6.0, "flutter_depth": 5.0}),
        ("a_tape_hiss", {"level_db": -44.0}),
        ("a_speaker", {"device": "boombox_1985", "strength": 0.6}),
    ],
    variants=[
        Variant("hot-pink", "Fluor Pink Run", "The zine drum pair: black ink, fluorescent pink.",
                video={"riso_print.inks": "black_fluor_pink"}),
        Variant("art-school", "Art-School Pass", "Teal and orange, registration almost intentional.",
                video={"riso_print.inks": "teal_orange", "riso_print.misregister": 1.2}),
    ],
))

register_preset(Preset(
    id="magazine-gloss-1967",
    name="Glossy Spread",
    family="print",
    era="1967",
    desc="Coated-stock confidence: a fine rosette you need a loupe to catch, colors rich as the advertised cocktail, highlights rolling off like lacquer.",
    tags=("60s", "magazine", "halftone", "gloss"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.12, "lift": 0.01, "knee": 0.72}),
        ("balance", {"warmth": 0.08, "high_tint": "cream", "high_amt": 0.2}),
        ("saturation", {"amount": 1.18, "vibrance": 0.25}),
        ("optics", {"diffusion": 0.15}),
        ("halftone", {"process": "magazine_fine", "lpi": 95.0, "paper": 0.22, "misregister": 0.35,
                      "ink_tone": 1.0}),
        ("paper_texture", {"amount": 0.03, "scale": 0.8}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 40.0, "high_hz": 15000.0}),
        ("a_vinyl_wow", {"rpm": 33, "depth_cents": 4.0}),
        ("a_vinyl_noise", {"crackle": 5.0, "pops": 1.0, "frying_db": -60.0, "wear": 0.2}),
        ("a_tube_amp", {"drive": 1.5, "sag": 0.3, "hum_db": -60.0}),
        ("a_compressor", {"ratio": 2.5}),
    ],
    variants=[
        Variant("newsstand", "Newsstand Grade", "The cheaper book: looser screen, duller stock.",
                video={"halftone.lpi": 70.0, "halftone.paper": 0.4, "halftone.misregister": 0.8}),
        Variant("ad-page", "The Ad Page", "Color by committee: saturation cranked past taste.",
                video={"saturation.amount": 1.4, "tone.contrast": 1.2}),
    ],
))
