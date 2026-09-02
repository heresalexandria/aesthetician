"""Print-family presets, second wave: duplicators, transmission prints and photographs.

Spirit and stencil duplicators, thermal fax, impact printers, wirephoto,
gravure, silkscreen, projected acetate, instant film, screentone and
cyanotype. Chain order is the printing path: grade -> optics -> process
(photocopy / halftone / riso) -> ink and paper colour -> paper surface, with
the exhibition stage last where there is one.
"""

from ..engine.presets import Preset, Variant, register_preset


# nearest: zine-photocopy-1981; differs: a spirit duplicator, not a copier - pale violet
# aniline dye instead of clogged black toner, solvent-soft strokes, almost no contrast.
register_preset(Preset(
    id="spirit-duplicator-1975",
    name="Spirit Duplicator Worksheet",
    family="print",
    era="1975",
    desc="Run off the master on the hand-cranked machine an hour before class: violet aniline dye pulled soft and wet onto absorbent stock, solvent still evaporating off the page.",
    tagline="Purple ditto ink, blurry pull, pale paper",
    tags=("70s", "photocopy", "paper", "educational"),
    keywords=("ditto", "spirit-duplicator", "purple", "worksheet", "seventies", "school",
              "mimeo", "classroom", "handout", "faded"),
    upscale="sharp",
    video=[
        ("photocopy", {"generations": 1, "toner": 0.1, "roller_marks": 0.15, "skew": 0.15,
                       "mono": True}),
        ("optics", {"soft_focus": 0.3, "bloom_mids": 0.15}),
        ("tone", {"contrast": 0.85, "lift": 0.15, "knee": 0.95}),
        # the dye: a magenta cast in the ink with a cool bias, then pushed
        ("balance", {"warmth": -0.15, "tint": 0.7, "shadow_tint": "magenta",
                     "shadow_amt": 0.85}),
        ("saturation", {"amount": 1.8, "vibrance": 0.2}),
        ("paper_texture", {"amount": 0.06, "scale": 1.2}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 100.0, "high_hz": 8000.0}),
        ("a_compressor", {"ratio": 2.5}),
        ("a_bed", {"bed": "fluorescent_office", "level_db": -34.0}),
    ],
    variants=[
        Variant("fresh-master", "First Off The Drum",
                "The first twenty copies, while the master is still wet and dark.",
                video={"tone.contrast": 1.0, "tone.lift": 0.05, "optics.soft_focus": 0.15,
                       "saturation.amount": 2.0}),
        Variant("hundredth-copy", "Copy One Hundred",
                "The end of the run: the master is spent and the class can barely read it.",
                video={"tone.lift": 0.25, "tone.contrast": 0.7, "optics.soft_focus": 0.4,
                       "photocopy.toner": 0.3}),
    ],
))


# nearest: spirit-duplicator-1975; differs: a cut stencil inked black through a roller,
# so the image gains and ghosts instead of fading, on gray stock with no dye colour at all.
register_preset(Preset(
    id="mimeograph-newsletter-1962",
    name="Mimeograph Newsletter",
    family="print",
    era="1962",
    desc="Typed onto a wax stencil and rolled off in the church basement: ink pushing through the cut and spreading into the fibre, a faint second impression from the roller, all of it on gray bond.",
    tagline="Stencil ink bleed, gray paper, roller ghosts",
    tags=("60s", "photocopy", "paper", "bw", "institutional"),
    keywords=("mimeograph", "stencil", "newsletter", "sixties", "church-bulletin",
              "fanzine", "ink-bleed", "gray-paper", "duplicator", "office"),
    upscale="sharp",
    video=[
        ("mono", {"amount": 1.0, "response": "panchromatic"}),
        ("tone", {"exposure": 0.35, "contrast": 0.95, "lift": 0.12, "knee": 0.92}),
        ("optics", {"soft_focus": 0.15}),
        ("photocopy", {"generations": 2, "toner": 0.4, "roller_marks": 0.35, "skew": 0.15,
                       "mono": True}),
        ("balance", {"warmth": -0.06}),
        ("paper_texture", {"amount": 0.06, "scale": 1.3}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 90.0, "high_hz": 7000.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_compressor", {"ratio": 3.0}),
        ("a_bed", {"bed": "fluorescent_office", "level_db": -36.0}),
        ("a_hum", {"hz": "60", "level_db": -52.0, "buzz": 0.25}),
    ],
    variants=[
        Variant("clean-stencil", "Fresh Stencil",
                "Cut this morning, inked properly: the type is actually sharp.",
                video={"photocopy.toner": 0.2, "photocopy.roller_marks": 0.2,
                       "tone.lift": 0.08}),
        Variant("tired-stencil", "Six Hundred Copies In",
                "The stencil has stretched and the ink is going everywhere it should not.",
                video={"photocopy.toner": 0.6, "photocopy.roller_marks": 0.5,
                       "photocopy.generations": 3, "tone.lift": 0.18}),
    ],
))


# nearest: front-page-1946; differs: a fine transmitted dither instead of a coarse press
# screen, dead printhead columns down the page, thermal-yellow stock and telephone audio.
register_preset(Preset(
    id="thermal-fax-1989",
    name="Thermal Fax Page",
    family="print",
    era="1989",
    desc="Arrived overnight on the roll and curled itself shut: a fine transmitted dither burned into thermal stock, a couple of dead printhead elements drawing white lines down the whole page.",
    tagline="Thermal gray, dropout streaks, dither dots",
    tags=("80s", "paper", "bw", "corporate", "halftone"),
    keywords=("fax", "thermal", "eighties", "office", "dither", "curled-paper",
              "transmission", "modem", "facsimile", "dropouts"),
    upscale="sharp",
    video=[
        ("mono", {"amount": 1.0, "response": "modern"}),
        ("tone", {"contrast": 1.3, "lift": 0.03, "knee": 0.85}),
        ("halftone", {"process": "newspaper_bw", "lpi": 90.0, "paper": 0.2,
                      "ink_tone": 1.2, "misregister": 0.0}),
        ("photocopy", {"generations": 1, "toner": 0.15, "roller_marks": 0.1, "skew": 0.1,
                       "mono": True}),
        ("telecine_scan", {"scanner_stripe": 0.9, "hop_px": 0.2}),
        ("balance", {"warmth": 0.1, "high_tint": "cream", "high_amt": 0.15}),
        ("paper_texture", {"amount": 0.04, "scale": 0.9}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 300.0, "high_hz": 3400.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_telephone", {"era": "touchtone_1985", "line_noise_db": -50.0,
                         "exchange_noise": 0.25}),
        ("a_compressor", {"ratio": 4.0}),
        ("a_hum", {"hz": "60", "level_db": -58.0}),
    ],
    variants=[
        Variant("crisp-fax", "Fine Mode",
                "Sent at the slow setting by somebody who cared: more lines, fewer dropouts.",
                video={"telecine_scan.scanner_stripe": 0.2, "halftone.lpi": 110.0,
                       "photocopy.toner": 0.05}),
        Variant("faded-thermal-2003", "Fourteen Years In A Folder",
                "Thermal paper does not keep: the whole page has gone tan and quiet.",
                video={"balance.warmth": 0.25, "tone.contrast": 0.8, "tone.lift": 0.2}),
    ],
))


# nearest: thermal-fax-1989; differs: coarse impact-ribbon dots at 60 lines, banding from
# the carriage passes, warm fanfold stock, and a PC speaker instead of a phone line.
register_preset(Preset(
    id="dot-matrix-printout-1985",
    name="Dot-Matrix Printout",
    family="print",
    era="1985",
    desc="Nine pins hammering a tired ribbon onto continuous fanfold: coarse gray dots, a visible seam where each carriage pass ends, beige stock with the tractor holes still on.",
    tagline="Ribbon-gray dots, feed bands, fanfold beige",
    tags=("80s", "paper", "bw", "computing", "corporate"),
    keywords=("dot-matrix", "printout", "eighties", "tractor-feed", "fanfold", "ribbon",
              "computer", "ascii", "banner", "office"),
    upscale="sharp",
    video=[
        ("mono", {"amount": 1.0, "response": "modern"}),
        ("tone", {"exposure": 0.25, "contrast": 1.1, "lift": 0.05, "knee": 0.9}),
        ("halftone", {"process": "newspaper_bw", "lpi": 60.0, "paper": 0.3,
                      "ink_tone": 1.1, "misregister": 0.0}),
        ("photocopy", {"generations": 1, "toner": 0.2, "roller_marks": 0.5, "skew": 0.06,
                       "mono": True}),
        ("balance", {"warmth": 0.15, "high_tint": "cream", "high_amt": 0.18}),
        ("paper_texture", {"amount": 0.05, "scale": 1.1}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 200.0, "high_hz": 6000.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_compressor", {"ratio": 3.5}),
        ("a_speaker", {"device": "pc_speaker_1992", "strength": 0.5}),
        ("a_bed", {"bed": "fluorescent_office", "level_db": -34.0}),
    ],
    variants=[
        Variant("fresh-ribbon", "New Ribbon",
                "Somebody finally changed the cartridge: the dots land black.",
                video={"halftone.ink_tone": 1.35, "photocopy.toner": 0.05,
                       "tone.contrast": 1.25}),
        Variant("worn-ribbon", "Ribbon On Its Last Pass",
                "Printed anyway, because the deadline was not moving.",
                video={"halftone.ink_tone": 0.7, "tone.lift": 0.15,
                       "photocopy.toner": 0.4}),
    ],
))


# nearest: microfilm-morgue-1958; differs: the transmission itself - line noise and column
# streaks from a phone circuit, then a press screen over it, not a library reader.
register_preset(Preset(
    id="wirephoto-1960",
    name="Wirephoto Transmission",
    family="print",
    era="1960",
    desc="Eight minutes down a leased telephone circuit to the newsroom drum: soft press-photo grays, line noise ticking through the scan, then a coarse screen for the morning edition.",
    tagline="Line-scan gray, phone-line streaks, AP grain",
    tags=("60s", "bw", "news", "halftone", "paper"),
    keywords=("wirephoto", "ap", "newsphoto", "sixties", "line-scan", "transmission",
              "telephoto", "press", "gray", "archive"),
    upscale="soft",
    video=[
        ("mono", {"amount": 1.0, "response": "panchromatic", "tint": "silver",
                  "tint_amt": 0.12}),
        ("tone", {"contrast": 0.95, "lift": 0.08, "knee": 0.9}),
        ("optics", {"soft_focus": 0.25}),
        ("grain", {"amount": 0.3, "size": 2.0, "chroma_grain": 0.0,
                   "stock": "newsreel_35", "layers": "mono"}),
        ("signal_rf", {"snow": 0.06, "sparkle": 2.0, "ghost_n": 0, "impulse_noise": 3.0}),
        ("telecine_scan", {"scanner_stripe": 0.5, "hop_px": 0.3}),
        ("halftone", {"process": "newspaper_bw", "lpi": 80.0, "paper": 0.15,
                      "ink_tone": 1.05, "misregister": 0.0}),
        ("paper_texture", {"amount": 0.04, "scale": 1.1}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 300.0, "high_hz": 3400.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_telephone", {"era": "rotary_1955", "line_noise_db": -50.0,
                         "exchange_noise": 0.3}),
        ("a_compressor", {"ratio": 3.5}),
        ("a_hum", {"hz": "60", "level_db": -55.0}),
    ],
    variants=[
        Variant("clean-receive", "Clean Circuit",
                "A good line for once: the drum finishes without a single tick.",
                video={"signal_rf.snow": 0.02, "signal_rf.impulse_noise": 0.5,
                       "telecine_scan.scanner_stripe": 0.2}),
        Variant("storm-line", "Storm On The Line",
                "Weather somewhere between here and there, and the deadline is in an hour.",
                video={"signal_rf.snow": 0.15, "signal_rf.impulse_noise": 8.0,
                       "telecine_scan.scanner_stripe": 0.8}),
    ],
))


# nearest: front-page-1946; differs: a fine sepia gravure cell structure with velvet mid
# tones rather than a coarse black letterpress screen, and a 1925 parlor sound path.
register_preset(Preset(
    id="rotogravure-supplement-1925",
    name="Rotogravure Supplement",
    family="print",
    era="1925",
    desc="The brown-ink picture section that came folded inside Sunday's paper: etched gravure cells holding velvet middle tones no letterpress screen could manage, printed warm on coarse stock.",
    tagline="Sepia gravure, velvet tones, coarse newsprint",
    tags=("20s", "paper", "halftone", "press", "tinted"),
    keywords=("rotogravure", "twenties", "sunday-supplement", "sepia", "brown-ink",
              "gravure", "newspaper", "velvet", "society-page", "photogravure"),
    upscale="sharp",
    video=[
        ("mono", {"amount": 1.0, "response": "orthochromatic", "tint": "sepia",
                  "tint_amt": 0.6}),
        ("tone", {"exposure": -0.12, "contrast": 1.0, "lift": 0.05, "knee": 0.9}),
        ("optics", {"soft_focus": 0.1}),
        ("halftone", {"process": "newspaper_bw", "lpi": 100.0, "paper": 0.4,
                      "ink_tone": 1.15, "misregister": 0.0}),
        # the screen prints in neutral ink, so the brown goes on after it
        ("mono", {"amount": 1.0, "response": "modern", "tint": "sepia",
                  "tint_amt": 1.0}),
        ("balance", {"warmth": 0.1, "tint": 0.18}),
        ("saturation", {"amount": 1.35, "vibrance": 0.1}),
        ("paper_texture", {"amount": 0.06, "scale": 1.2}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 200.0, "high_hz": 4500.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_compressor", {"ratio": 3.0}),
        ("a_speaker", {"device": "gramophone_horn_1915", "strength": 0.5}),
        ("a_bed", {"bed": "record_surface_loop", "level_db": -30.0}),
    ],
    variants=[
        Variant("society-page-clean", "Society Page",
                "The front of the section, printed on the good stock while the press was fresh.",
                video={"halftone.lpi": 120.0, "halftone.paper": 0.3,
                       "saturation.amount": 1.2}),
        Variant("yellowed-attic-copy", "Attic Copy",
                "Ninety years folded in a trunk: the paper has taken over the picture.",
                video={"halftone.paper": 0.6, "saturation.amount": 1.8, "tone.lift": 0.15}),
    ],
))


# nearest: riso-flyer-1985; differs: hard six-level posterization before the ink stage and
# a much wider hand-pulled misregistration, with fluorescent stock ink instead of a duplicator.
register_preset(Preset(
    id="screen-print-poster-1968",
    name="Screen-Print Poster",
    family="print",
    era="1968",
    desc="Photographed, posterized to a handful of flat shapes and pulled one screen at a time: fluorescent ink sitting proud of the sheet, the second pull landing wherever the registration pins felt like.",
    tagline="Flat inks, posterized edges, loose register",
    tags=("60s", "paper", "music", "riso", "color"),
    keywords=("screen-print", "silkscreen", "poster", "sixties", "psychedelic",
              "concert-poster", "flat-ink", "posterized", "misregistration", "fillmore"),
    upscale="sharp",
    video=[
        ("cel_flatten", {"smooth": 0.5, "levels": 6, "flatness": 0.75, "sat_snap": 0.6,
                         "protect_gradients": False}),
        ("tone", {"contrast": 1.15, "lift": 0.02}),
        ("saturation", {"amount": 1.5, "vibrance": 0.2, "hue": 10.0}),
        ("riso_print", {"inks": "black_fluor_pink", "misregister": 2.5, "grain_ink": 0.5,
                        "paper": 0.5}),
        ("paper_texture", {"amount": 0.05, "scale": 1.2}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 80.0, "high_hz": 9000.0}),
        ("a_compressor", {"ratio": 3.0}),
        ("a_room", {"mode": "plate1960", "size": 1.2, "decay_s": 1.0, "mix": 0.15}),
    ],
    variants=[
        Variant("tight-registration", "Careful Pull",
                "The printer took their time: the second colour lands where it was drawn.",
                video={"riso_print.misregister": 0.8}),
        Variant("day-glo-orange", "Day-Glo Run",
                "Teal and orange on the second night of the run, because the pink ran out.",
                video={"riso_print.inks": "teal_orange", "saturation.hue": -10.0}),
    ],
))


# nearest: microfilm-morgue-1958; differs: a colour-copier acetate thrown by an overhead
# lamp onto a painted lecture wall - hot centre, keystone and room spill, not a reader hood.
register_preset(Preset(
    id="overhead-transparency-1988",
    name="Overhead Transparency",
    family="print",
    era="1988",
    desc="Copied onto acetate for the ten o'clock lecture and thrown up by a fan-cooled overhead: washed misregistered colour, the lamp burning a bright patch through the middle, the whole frame leaning.",
    tagline="Acetate copier art, hot lamp, keystone",
    tags=("80s", "projection", "paper", "educational", "washed"),
    keywords=("overhead", "transparency", "acetate", "eighties", "classroom", "projector",
              "color-copier", "lecture", "keystone", "washed"),
    upscale="soft",
    video=[
        ("photocopy", {"generations": 1, "toner": 0.15, "roller_marks": 0.1, "skew": 0.06,
                       "mono": False}),
        ("tone", {"contrast": 0.9, "lift": 0.1, "knee": 0.92}),
        ("saturation", {"amount": 0.85, "vibrance": -0.1}),
        ("scratches", {"enabled": False, "count": 2, "strength": 0.35,
                       "transient_rate": 0.0, "wander": 0.3}),
        ("vignette", {"amount": 0.0, "hot_center": 0.5, "radius": 0.9, "softness": 0.9}),
        ("projection", {"shutter_flicker": 0.0, "keystone": 0.08, "ambient_lift": 0.12,
                        "screen_gain_falloff": 0.3}),
        ("screen", {"surface": "wall_paint", "hotspot": 0.4, "room_spill": 0.2,
                    "shake_event": 0.0}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 80.0, "high_hz": 9000.0}),
        ("a_compressor", {"ratio": 3.0}),
        ("a_room", {"mode": "room", "size": 1.8, "decay_s": 1.1, "mix": 0.2}),
        ("a_bed", {"bed": "air_handler_hall", "level_db": -36.0}),
    ],
    variants=[
        Variant("fresh-acetate", "Fresh Acetate",
                "Copied this morning, still in its paper sleeve: clean and almost saturated.",
                video={"photocopy.toner": 0.05, "tone.lift": 0.04,
                       "saturation.amount": 0.95}),
        Variant("scratched-acetate", "Fourth Semester",
                "The same sheet, taught from twice a week, wiped with whatever was around.",
                video={"scratches.enabled": True, "photocopy.toner": 0.3}),
    ],
))


# nearest: auth-square-social-filter-2013; differs: real SX-70 chemistry - cyan shadows,
# cream highlights, integral-print corner softness and a white square border, not a filter.
register_preset(Preset(
    id="instant-print-sx70-1975",
    name="Instant Print SX-70",
    family="print",
    era="1975",
    desc="Ejected humming from the folding camera and developed in your hand across a minute: shadows drifting cyan, highlights settling toward cream, the corners never quite as sharp as the middle.",
    tagline="Cyan shadows, warm fade, square white border",
    tags=("70s", "photo", "paper", "home-movie", "instant-film"),
    keywords=("polaroid", "instant", "seventies", "sx-70", "square", "cyan-shadows",
              "faded", "snapshot", "party", "vintage-photo"),
    upscale="soft",
    video=[
        ("balance", {"warmth": 0.16, "shadow_tint": "blue", "shadow_amt": 0.45,
                     "high_tint": "cream", "high_amt": 0.35}),
        ("tone", {"contrast": 0.88, "lift": 0.09, "knee": 0.68}),
        ("saturation", {"amount": 0.85, "vibrance": -0.12}),
        ("optics", {"soft_focus": 0.24, "corner_softness": 0.25, "bloom_mids": 0.35}),
        ("fade", {"amount": 0.16, "profile": "neutral", "bloom_whites": 0.35}),
        ("vignette", {"amount": 0.3, "softness": 0.8, "radius": 0.95}),
        ("paper_texture", {"amount": 0.03, "scale": 0.9}),
        ("framing", {"aspect": "1:1", "mode": "box", "matte_gray": 0.25,
                     "edge_soft": 0.002}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 60.0, "high_hz": 9000.0}),
        ("a_compressor", {"ratio": 2.5}),
        ("a_bed", {"bed": "record_surface_loop", "level_db": -34.0}),
    ],
    variants=[
        Variant("fresh-from-camera", "Just Developed",
                "Held under a jacket for sixty seconds and looked at immediately.",
                video={"fade.amount": 0.0, "balance.warmth": 0.08, "vignette.amount": 0.2}),
        Variant("drawer-faded-2005", "Kitchen Drawer, 2005",
                "Thirty years face-up under the takeaway menus.",
                video={"fade.amount": 0.3, "balance.warmth": 0.3, "balance.shadow_amt": 0.15,
                       "saturation.amount": 0.75}),
    ],
))


# nearest: instant-print-sx70-1975; differs: a hard on-camera flash - blown knee, fast
# falloff into teal shadows and a glossy contrasty stock instead of soft warm chemistry.
register_preset(Preset(
    id="instant-print-600-1988",
    name="Instant Print 600 Flash",
    family="print",
    era="1988",
    desc="Point-and-shoot with the flash bar firing every time: whoever stood closest is blown out, the room three feet behind them falls straight into teal, and the print comes out glossy.",
    tagline="Hard flash falloff, teal shadows, glossy",
    tags=("80s", "photo", "paper", "home-movie", "night-flash"),
    keywords=("polaroid", "instant", "eighties", "flash", "party", "snapshot", "glossy",
              "hard-light", "square", "night"),
    upscale="soft",
    video=[
        ("tone", {"exposure": 0.2, "contrast": 1.3, "knee": 0.72, "lift": 0.01}),
        ("balance", {"warmth": 0.05, "shadow_tint": "teal", "shadow_amt": 0.3}),
        ("saturation", {"amount": 1.05}),
        ("optics", {"corner_softness": 0.15, "veiling_flare": 0.1}),
        ("grain", {"enabled": False, "amount": 0.4, "size": 2.0, "chroma_grain": 0.22,
                   "stock": "push_process", "layers": "color_neg"}),
        ("fade", {"amount": 0.05, "profile": "neutral", "bloom_whites": 0.2}),
        ("vignette", {"amount": 0.48, "radius": 0.66, "softness": 0.55}),
        ("framing", {"aspect": "1:1", "mode": "box", "matte_gray": 0.25,
                     "edge_soft": 0.002}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 60.0, "high_hz": 10000.0}),
        ("a_compressor", {"ratio": 2.5}),
        ("a_bed", {"bed": "tape_deck_room", "level_db": -34.0}),
    ],
    variants=[
        Variant("disposable-camera-1998", "Disposable Camera",
                "The cardboard one from the chemist: grainier, greener, and not square.",
                video={"grain.enabled": True, "saturation.amount": 1.15,
                       "balance.warmth": -0.05, "framing.aspect": "1.85"}),
        Variant("flash-failed", "Flash Did Not Fire",
                "Nine dark squares out of ten, and one of them is somehow the good one.",
                video={"tone.exposure": -0.5, "vignette.amount": 0.55,
                       "balance.shadow_amt": 0.4}),
    ],
))


# nearest: sunday-comics-1972; differs: a single black plate with dot screentone laid on
# the mid tones and a brush-inked line, on Japanese paper stock - no CMYK rosettes at all.
register_preset(Preset(
    id="manga-screentone-1985",
    name="Manga Screentone Page",
    family="print",
    era="1985",
    desc="Brush-inked line art with adhesive dot tone cut and burnished over every mid tone, printed one plate black on the cheap paper the weekly ran on.",
    tagline="Ink line, dot screentones, grayscale paper",
    tags=("80s", "paper", "japan", "halftone", "monochrome"),
    keywords=("manga", "screentone", "eighties", "ink", "comic", "japanese-comic", "dots",
              "black-and-white", "tankobon", "panel"),
    upscale="sharp",
    video=[
        ("mono", {"amount": 1.0, "response": "panchromatic"}),
        ("cel_flatten", {"smooth": 0.4, "levels": 6, "flatness": 0.5,
                         "protect_gradients": False}),
        ("ink_line", {"weight": 0.5, "xerox_grit": 0.1, "line_wobble": 0.1}),
        ("tone", {"contrast": 1.2, "lift": 0.03, "knee": 0.88}),
        ("halftone", {"process": "newspaper_bw", "lpi": 70.0, "paper": 0.15,
                      "ink_tone": 1.1, "misregister": 0.0}),
        ("paper_texture", {"amount": 0.05, "scale": 1.1}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 60.0, "high_hz": 10000.0}),
        ("a_compressor", {"ratio": 2.5}),
        ("a_room", {"mode": "room", "size": 0.6, "decay_s": 0.2, "mix": 0.05}),
    ],
    variants=[
        Variant("tankobon-print", "Collected Edition",
                "The volume reprint on better stock: finer tone, whiter page.",
                video={"halftone.lpi": 85.0, "halftone.paper": 0.25}),
        Variant("weekly-newsprint", "Weekly Anthology",
                "Four hundred pages of newsprint tinted whatever colour was cheap that week.",
                video={"halftone.lpi": 55.0, "halftone.paper": 0.45, "tone.lift": 0.1}),
    ],
))


# nearest: none; differs: no blue-print process exists in the library - Prussian blue
# paper, negative white specks and sun-fade edges instead of a photographic gray scale.
register_preset(Preset(
    id="cyanotype-blueprint-1910",
    name="Cyanotype Blueprint",
    family="print",
    era="1910",
    desc="Coated by hand, laid under glass and put out in the yard until the iron salts turned: Prussian blue everywhere the light got through, white where the drawing sat, edges lighter than the middle.",
    tagline="Prussian-blue paper, white line, sun-fade",
    tags=("1910s", "paper", "tinted", "architecture", "contact-print"),
    keywords=("cyanotype", "blueprint", "blue", "edwardian", "architectural", "sun-print",
              "prussian-blue", "archive", "paper", "1910s"),
    upscale="soft",
    video=[
        ("mono", {"amount": 1.0, "response": "orthochromatic", "tint": "cyanotype",
                  "tint_amt": 1.0}),
        ("balance", {"warmth": -0.35, "shadow_tint": "blue", "shadow_amt": 0.7,
                     "high_tint": "cyan", "high_amt": 0.35}),
        ("saturation", {"amount": 2.2, "vibrance": 0.3}),
        ("tone", {"contrast": 1.15, "gamma": 1.1, "lift": 0.03, "knee": 0.9}),
        ("optics", {"soft_focus": 0.1}),
        ("dust", {"density": 0.15, "polarity": "negative", "hairs": 0.2, "size": 1.1}),
        ("paper_texture", {"amount": 0.07, "scale": 1.3}),
        ("vignette", {"amount": 0.25, "softness": 0.9, "radius": 0.95}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 150.0, "high_hz": 5000.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_compressor", {"ratio": 3.0}),
        ("a_speaker", {"device": "gramophone_horn_1915", "strength": 0.4}),
        ("a_bed", {"bed": "record_surface_loop", "level_db": -34.0}),
    ],
    variants=[
        Variant("fresh-print", "Fresh From The Frame",
                "Washed and hung this afternoon: even blue, corner to corner.",
                video={"vignette.amount": 0.1, "dust.density": 0.05}),
        Variant("sun-faded", "Left In The Window",
                "A century on a drawing-office wall has taken most of the iron out of it.",
                video={"saturation.amount": 1.5, "tone.lift": 0.15, "tone.contrast": 0.9,
                       "vignette.amount": 0.35}),
    ],
))
