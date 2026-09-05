"""Exhibition-family presets, second house: the screens themselves. Pocket
tubes, cabinet sets, flat panels, projectors, stadium walls, coin-op glass and
a peep-show hood. Not the programme, the thing you watched it on.
"""

from ..engine.presets import Preset, Variant, register_preset


# nearest: portable-bw-1963 (swimming snow, roofline ghost, tiny speaker); differs:
# a two-inch 1984 flat tube: a quarter the resolution, hard scanlines, earphone tin.
register_preset(Preset(
    id="watchman-pocket-tv-1984",
    name="Pocket Flat-Tube TV",
    family="exhibition",
    era="1984",
    desc="A two-inch flat picture tube held at arm's length off a telescopic aerial: a 240-line raster with visible scan gaps, snow and one hard building ghost, all of it through a single earphone.",
    tagline="Two-inch flat tube, RF snow, earphone tin",
    tags=("80s", "crt", "flat-tube", "monochrome"),
    keywords=("watchman", "pocket-tv", "eighties", "portable", "bw", "two-inch",
              "handheld", "antenna", "snow", "earphone", "sports"),
    proc_height=240,
    upscale="soft",
    video=[
        ("mono", {"amount": 1.0, "response": "panchromatic",
                  "tint": "silver", "tint_amt": 0.12}),
        ("tone", {"contrast": 1.15, "lift": 0.06, "knee": 0.78}),
        ("signal_rf", {"snow": 0.12, "sparkle": 2.0, "ghost_n": 1, "ghost_px": 8.0,
                       "ghost_alpha": 0.15, "impulse_noise": 1.0}),
        ("crt", {"scan_strength": 0.3, "bloom": 0.4, "curvature": 0.02,
                 "glass_glow": 0.15, "vignette_crt": 0.2}),
        ("framing", {"aspect": "source", "mode": "box", "corner_radius": 0.06}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 250.0, "high_hz": 6000.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_tv_sound", {"hz": "60", "buzz_db": -50.0, "hum_db": -54.0, "comp": 0.55}),
        ("a_speaker", {"device": "transistor_pocket_1965", "strength": 0.9}),
    ],
    variants=[
        Variant("good-signal", "Good Signal",
                "Standing in the right spot with the aerial out: the picture is small but clean.",
                video={"signal_rf.snow": 0.03, "signal_rf.ghost_n": 0,
                       "signal_rf.impulse_noise": 0.0}),
        Variant("earphone", "Single Earphone",
                "The bundled mono earpiece rather than the pinhole speaker: thinner and closer.",
                audio={"a_speaker.device": "earbud_2005", "a_speaker.strength": 0.7,
                       "a_bandlimit.high_hz": 7000.0}),
    ],
))


# nearest: watchman-pocket-tv-1984 (the same pocket habit, a tube); differs: a colour
# passive-matrix panel that smears every movement and washes the picture flat.
register_preset(Preset(
    id="handheld-lcd-tv-1993",
    name="Handheld LCD TV",
    family="exhibition",
    era="1993",
    desc="An early colour pocket television with a passive-matrix panel: every moving edge dragging a grey tail behind it, blacks lifting to slate, and the aerial still pulling snow off the air.",
    tagline="Passive-matrix smear, washed color, RF",
    tags=("90s", "lcd", "portable-tv", "aerial"),
    keywords=("handheld-tv", "lcd", "nineties", "passive-matrix", "casio", "smear",
              "washed", "portable", "antenna", "pocket-color", "news"),
    proc_height=240,
    upscale="soft",
    video=[
        ("tone", {"contrast": 0.85, "lift": 0.1, "knee": 0.9}),
        ("saturation", {"amount": 0.8}),
        ("signal_rf", {"snow": 0.08, "sparkle": 2.0, "ghost_n": 1, "ghost_px": 6.0,
                       "ghost_alpha": 0.18}),
        ("lcd_screen", {"grid": 0.3, "scale": 2, "response_smear": 0.7,
                        "backlight_bleed": 0.3, "viewing_angle": 0.4,
                        "subpixel": "none"}),
        ("framing", {"aspect": "source", "mode": "box", "corner_radius": 0.05}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 300.0, "high_hz": 6000.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_tv_sound", {"hz": "60", "buzz_db": -50.0, "hum_db": -56.0, "comp": 0.5}),
        ("a_speaker", {"device": "transistor_pocket_1965", "strength": 0.8}),
    ],
    variants=[
        Variant("good-signal", "Good Signal",
                "Near the transmitter: the snow goes, the smear stays exactly where it was.",
                video={"signal_rf.snow": 0.02, "signal_rf.ghost_n": 0}),
        Variant("dim-backlight", "Dim Backlight",
                "Four AA cells nearly out: the backlight gives up and the panel goes grey on grey.",
                video={"lcd_screen.backlight_bleed": 0.08, "tone.lift": 0.02,
                       "tone.exposure": -0.3}),
    ],
))


# nearest: mall-tv-wall-1989 (grille stripes, beam bloom, hot chroma); differs:
# one well-adjusted living-room set on a clean feed, sharp rather than blown out.
register_preset(Preset(
    id="trinitron-living-room-1990",
    name="Living-Room Trinitron",
    family="exhibition",
    era="1990",
    desc="A twenty-seven inch aperture-grille set in the corner of a living room: vertical phosphor stripes, two damper wires, bright beam bloom on titles and a clean comb-filtered composite feed.",
    tagline="Aperture-grille sharpness, bright bloom",
    tags=("90s", "tube-tv", "ntsc", "home-viewing"),
    keywords=("trinitron", "sony", "nineties", "living-room", "aperture-grille",
              "bright", "sharp", "crt", "console", "damper-wire", "primetime"),
    proc_height=580,
    upscale="soft",
    video=[
        ("stock", {"profile": "tube_80s", "strength": 0.35}),
        ("tone", {"contrast": 1.08, "lift": 0.02, "knee": 0.84}),
        ("saturation", {"amount": 1.1, "vibrance": 0.1}),
        ("ntsc", {"strength": 0.45, "luma_bw": 4.2, "chroma_bw": 1.2, "comb": 0.7,
                  "comb_mode": "comb_1line", "phase_noise": 1.2, "dot_crawl": 0.15,
                  "rainbow": 0.15}),
        ("signal_rf", {"enabled": False, "snow": 0.03, "ghost_n": 1, "ghost_px": 12.0,
                       "ghost_alpha": 0.12}),
        ("interlace", {"field_order": "tff", "combing": 0.5, "twitter": 0.3}),
        ("crt", {"phosphor_mask": "grille", "mask_scale": 1.0, "mask_strength": 0.16,
                 "scan_strength": 0.18, "bloom": 0.3, "beam_bloom": 0.2,
                 "glass_glow": 0.08, "curvature": 0.01, "misconvergence": 0.3}),
        ("framing", {"aspect": "source", "mode": "box", "corner_radius": 0.02}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 60.0, "high_hz": 13000.0}),
        ("a_tv_sound", {"hz": "60", "buzz_db": -64.0, "hum_db": -66.0, "comp": 0.45}),
        ("a_channel_aging", {"width": 1.05, "crosstalk_db": -32.0, "mono_bass_hz": 150.0}),
        ("a_speaker", {"device": "tv_mono_1985", "strength": 0.7}),
    ],
    variants=[
        Variant("s-video-input", "S-Video Input",
                "Luma and chroma kept apart all the way from the laserdisc: no dot crawl left to find.",
                video={"ntsc.enabled": False, "crt.mask_strength": 0.15}),
        Variant("rf-input-cable", "RF Input",
                "Cable box on channel three: everything back through one modulated carrier.",
                video={"ntsc.strength": 0.75, "ntsc.luma_bw": 3.4, "ntsc.dot_crawl": 0.35,
                       "signal_rf.enabled": True}),
    ],
))


# nearest: portable-bw-1963 (the small set as an object); differs: a big colour
# console in 1972 - curved glass with a window in it, corner misconvergence, cabinet boom.
register_preset(Preset(
    id="console-tv-curved-1972",
    name="Curved Console TV",
    family="exhibition",
    era="1972",
    desc="A wood-cabinet colour console under a window: the afternoon reflected off deeply curved glass, red and blue drifting apart in the corners, and the whole cabinet booming under the speaker.",
    tagline="Curved glare, misconverged corners, boom",
    tags=("70s", "tube-tv", "ntsc", "cabinet-set"),
    keywords=("console-tv", "seventies", "curved", "glare", "wood-cabinet",
              "living-room", "crt", "misconvergence", "rabbit-ears", "family-room"),
    proc_height=520,
    upscale="soft",
    video=[
        ("stock", {"profile": "tube_70s", "strength": 0.4}),
        ("tone", {"contrast": 1.06, "lift": 0.03, "knee": 0.82}),
        ("saturation", {"amount": 1.02}),
        ("ntsc", {"strength": 0.8, "luma_bw": 3.3, "chroma_bw": 0.7, "phase_noise": 2.8,
                  "setup_level": 0.06, "chroma_agc": 0.15, "dot_crawl": 0.3,
                  "rainbow": 0.25}),
        ("signal_rf", {"snow": 0.04, "sparkle": 2.0, "ghost_n": 1, "ghost_px": 16.0,
                       "ghost_alpha": 0.12, "hum_bar": 0.0}),
        ("interlace", {"field_order": "tff", "combing": 0.55, "twitter": 0.3}),
        ("crt", {"scan_strength": 0.14, "phosphor_mask": "dots", "mask_scale": 2.0,
                 "mask_strength": 0.18, "curvature": 0.12, "glare": 0.35,
                 "glare_pos": "tr", "misconvergence": 1.2, "bloom": 0.4,
                 "beam_bloom": 0.35, "vignette_crt": 0.25, "deflection_pin": 0.3}),
        ("framing", {"aspect": "source", "mode": "box", "corner_radius": 0.08}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 90.0, "high_hz": 8000.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_tv_sound", {"hz": "60", "buzz_db": -54.0, "hum_db": -52.0, "comp": 0.5}),
        ("a_speaker", {"device": "tv_console_1972", "strength": 0.8, "cabinet_knock": 0.4}),
    ],
    variants=[
        Variant("dealer-showroom", "Dealer Showroom",
                "The floor model with the blinds down and a service technician just finished with it.",
                video={"crt.glare": 0.0, "crt.misconvergence": 0.5, "signal_rf.snow": 0.0,
                       "ntsc.phase_noise": 1.2}),
        Variant("late-night-1979", "Late Night",
                "Well past midnight on a tired set: a hum bar crawling up and the signal drifting off.",
                video={"signal_rf.hum_bar": 0.2, "signal_rf.snow": 0.08,
                       "tone.exposure": -0.1, "crt.glare": 0.1}),
    ],
))


# nearest: watchman-pocket-tv-1984 (a tiny tube fed a rough signal); differs: cabin
# analog distribution to a seatback in 1995, pan-and-scan crop and pneumatic headphones.
register_preset(Preset(
    id="airline-seatback-crt-1995",
    name="Airline Seatback CRT",
    family="exhibition",
    era="1995",
    desc="A five-inch tube in the seat in front, at the far end of a cabin distribution amplifier: chroma bandwidth almost gone, the feature cropped to fit, and the sound down two pneumatic tubes.",
    tagline="Tiny cabin tube, smeared feed, headphones",
    tags=("90s", "crt", "airliner", "pan-and-scan"),
    keywords=("airline", "seatback", "in-flight", "nineties", "cabin", "tiny-crt",
              "distribution", "headphones", "movie", "economy", "travel"),
    proc_height=300,
    upscale="soft",
    video=[
        ("tone", {"contrast": 1.04, "lift": 0.05, "knee": 0.86}),
        ("saturation", {"amount": 0.95}),
        ("ntsc", {"strength": 0.85, "luma_bw": 2.6, "chroma_bw": 0.5, "phase_noise": 3.0,
                  "dot_crawl": 0.25, "rainbow": 0.2, "chroma_agc": 0.2}),
        ("codec_era", {"enabled": False, "codec": "mpeg4", "kbps": 600, "res": "240p",
                       "gop": 60}),
        ("interlace", {"field_order": "tff", "combing": 0.5, "twitter": 0.25}),
        ("crt", {"scan_strength": 0.25, "bloom": 0.4, "curvature": 0.09, "glare": 0.2,
                 "glare_pos": "tc", "glass_glow": 0.18, "vignette_crt": 0.3}),
        ("framing", {"aspect": "source", "mode": "box", "zoom": 0.1}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 200.0, "high_hz": 7000.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_tape_hiss", {"level_db": -40.0, "type": "cassette"}),
        ("a_compressor", {"threshold_db": -20.0, "ratio": 4.0, "attack_ms": 8.0}),
        ("a_speaker", {"device": "earbud_2005", "strength": 0.6}),
        ("a_hum", {"hz": "60", "level_db": -52.0, "buzz": 0.5}),
    ],
    variants=[
        Variant("overhead-cabin-monitor", "Overhead Monitor",
                "The drop-down monitor over the aisle instead: further away, brighter, more glass.",
                video={"crt.curvature": 0.14, "crt.glare": 0.4, "crt.scan_strength": 0.15,
                       "crt.bloom": 0.5}),
        Variant("digital-seatback-2005", "Digital Seatback",
                "The same seat ten years later: a low-bitrate file on demand instead of a cabin loop.",
                video={"codec_era.enabled": True, "ntsc.enabled": False,
                       "crt.scan_strength": 0.12}),
    ],
))


# nearest: hd-1080i-2008 (early HD broadcast, waxed detail); differs: the panel
# itself - plasma dither noise living in the shadows, coarse cell grid, warm bias.
register_preset(Preset(
    id="early-plasma-2001",
    name="Early Plasma Panel",
    family="exhibition",
    era="2001",
    desc="A first-generation plasma panel driving eight bits of brightness out of pulse counting: dither noise crawling in every shadow, a coarse cell grid, and a red-orange bias baked into the phosphor mix.",
    tagline="Dither-noise shadows, orange-red glow",
    tags=("00s", "flat-panel", "hdtv", "interlaced"),
    keywords=("plasma", "aughts", "panel", "dither", "burn-in", "flat-screen",
              "early-hdtv", "orange-red", "showroom", "demo-reel"),
    upscale="sharp",
    video=[
        ("balance", {"warmth": 0.05, "high_tint": "yellow", "high_amt": 0.08}),
        ("tone", {"contrast": 1.06, "lift": 0.03, "knee": 0.88}),
        ("saturation", {"amount": 1.1}),
        ("interlace", {"field_order": "tff", "combing": 0.4, "twitter": 0.25}),
        ("grain", {"amount": 0.3, "size": 1.0, "roughness": 1.0, "chroma_grain": 0.08,
                   "stock": "fine_35", "layers": "mono", "shadow_boost": 0.95}),
        ("lcd_screen", {"grid": 0.12, "scale": 4, "response_smear": 0.05,
                        "backlight_bleed": 0.05, "subpixel": "none"}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 40.0, "high_hz": 16000.0}),
        ("a_compressor", {"threshold_db": -18.0, "ratio": 3.0, "attack_ms": 10.0}),
        ("a_speaker", {"device": "tv_mono_1985", "strength": 0.6}),
    ],
    variants=[
        Variant("showroom-torch-mode", "Showroom Torch Mode",
                "Set to sell itself under retail lighting: everything two stops too bright and too red.",
                video={"tone.exposure": 0.2, "tone.contrast": 1.14,
                       "saturation.amount": 1.35}),
        Variant("aged-panel-2008", "Aged Panel",
                "Seven years on: the cells are dimmer, warmer, and noisier than they started.",
                video={"tone.exposure": -0.15, "balance.warmth": 0.14, "grain.amount": 0.4}),
    ],
))


# nearest: early-plasma-2001 (the other flat panel of the decade); differs: LCD
# response smear, edge backlight bleed, blue-grey blacks and a bob-deinterlaced feed.
register_preset(Preset(
    id="early-lcd-tv-2005",
    name="Early LCD TV",
    family="exhibition",
    era="2005",
    desc="A 2005 edge-lit LCD with the factory picture mode left on: eight milliseconds of smear behind everything that moves, blacks sitting blue-grey, backlight pooling in the corners and sharpening cranked.",
    tagline="Motion smear, blue-gray blacks, edge bleed",
    tags=("00s", "flat-panel", "widescreen", "edge-lit"),
    keywords=("lcd", "aughts", "flat-screen", "motion-blur", "blue-blacks",
              "backlight-bleed", "720p", "hdtv", "living-room", "samsung-era", "sports"),
    upscale="sharp",
    video=[
        ("balance", {"shadow_tint": "blue", "shadow_amt": 0.2}),
        ("tone", {"contrast": 1.02, "lift": 0.08, "knee": 0.9}),
        ("saturation", {"amount": 1.05}),
        ("interlace", {"field_order": "tff", "combing": 0.35, "twitter": 0.2}),
        ("deinterlace_artifact", {"mode": "bob_shimmer", "amount": 0.3}),
        ("sharpen", {"amount": 0.3, "radius": 1.0}),
        ("lcd_screen", {"grid": 0.12, "scale": 3, "response_smear": 0.5,
                        "backlight_bleed": 0.35, "viewing_angle": 0.2,
                        "subpixel": "none"}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 60.0, "high_hz": 15000.0}),
        ("a_compressor", {"threshold_db": -18.0, "ratio": 3.0, "attack_ms": 10.0}),
        ("a_speaker", {"device": "laptop_2006", "strength": 0.5}),
    ],
    variants=[
        Variant("dynamic-mode", "Dynamic Mode",
                "The mode it shipped in: edge enhancement halos and colour pushed past the panel.",
                video={"sharpen.amount": 0.6, "saturation.amount": 1.3,
                       "tone.contrast": 1.12}),
        Variant("game-mode-2010", "Game Mode",
                "Five years and one panel generation later, with the processing switched off.",
                video={"lcd_screen.response_smear": 0.2, "tone.lift": 0.04,
                       "sharpen.amount": 0.1}),
    ],
))


# nearest: rptv-superbowl-1993 (three-gun rear projection, hotspot and louvres); differs:
# a single-chip DLP in 2003 - colour-wheel fringing rather than convergence error.
register_preset(Preset(
    id="dlp-projector-rainbow-2003",
    name="DLP Projector",
    family="exhibition",
    era="2003",
    desc="A single-chip DLP throwing onto a matte screen in a finished basement: the colour wheel splitting fast edges into red and blue, blacks never darker than the room, and a fan running the whole time.",
    tagline="Color-wheel fringes, gray blacks, fan hum",
    tags=("00s", "projection", "single-chip", "widescreen"),
    keywords=("dlp", "projector", "aughts", "rainbow-effect", "color-wheel",
              "home-theater", "gray-blacks", "fan", "screen", "basement", "blockbuster"),
    upscale="soft",
    video=[
        ("tone", {"contrast": 0.95, "lift": 0.1, "knee": 0.9}),
        ("saturation", {"amount": 1.05}),
        ("crt", {"scan_strength": 0.0, "bloom": 0.1, "curvature": 0.0,
                 "misconvergence": 2.2, "mask_misalign": 0.7}),
        ("screen", {"surface": "matte_white", "hotspot": 0.25, "room_spill": 0.1,
                    "keystone_v": 0.0, "shake_event": 0.0}),
        ("projection", {"shutter_flicker": 0.1, "keystone": 0.03, "ambient_lift": 0.06,
                        "screen_gain_falloff": 0.3}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 40.0, "high_hz": 16000.0}),
        ("a_compressor", {"threshold_db": -17.0, "ratio": 2.5, "attack_ms": 12.0}),
        ("a_room", {"mode": "room", "size": 1.6, "decay_s": 0.5, "mix": 0.15}),
        ("a_bed", {"bed": "air_handler_hall", "level_db": -38.0, "duck": 0.1}),
    ],
    variants=[
        Variant("high-brightness-mode", "High Brightness",
                "The lamp wound up so the room lights can stay on: blacks go from grey to pale grey.",
                video={"tone.lift": 0.14, "saturation.amount": 0.9,
                       "projection.ambient_lift": 0.1}),
        Variant("three-chip-cinema", "Three-Chip",
                "No wheel at all: three chips, one pass, and the fringes disappear.",
                video={"crt.misconvergence": 0.25, "crt.mask_misalign": 0.0,
                       "tone.lift": 0.04}),
    ],
))


# nearest: mall-tv-wall-1989 (a wall of grille tubes indoors); differs: 1992 CRT
# modules the size of televisions, seen across an open stadium in flat daylight.
register_preset(Preset(
    id="jumbotron-stadium-1992",
    name="Stadium Jumbotron",
    family="exhibition",
    era="1992",
    desc="A replay board built out of tube modules the size of washing machines: picture information down to a couple of hundred blocks across, washed out by open daylight, with the house PA a beat behind it.",
    tagline="Giant module blocks, daylight washout, PA",
    tags=("90s", "video-wall", "outdoor", "daytime"),
    keywords=("jumbotron", "stadium", "nineties", "big-screen", "modules", "blocks",
              "daylight", "replay", "arena", "pa"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 0.85, "lift": 0.15, "knee": 0.92}),
        ("saturation", {"amount": 1.2, "vibrance": 0.15}),
        ("pixel_era", {"res_h": 120, "palette": "none", "dither": "none",
                       "contrast_snap": 0.15, "pixel_aspect": 1.0}),
        ("lcd_screen", {"grid": 0.5, "scale": 6, "response_smear": 0.1,
                        "backlight_bleed": 0.0, "subpixel": "none"}),
        ("crt", {"phosphor_mask": "dots", "mask_scale": 3.0, "mask_strength": 0.13,
                 "scan_strength": 0.0, "bloom": 0.12, "beam_bloom": 0.2}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 100.0, "high_hz": 8000.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_compressor", {"threshold_db": -20.0, "ratio": 4.0, "attack_ms": 6.0}),
        ("a_pa_bullhorn", {"device": "pa_stadium", "drive": 2.0, "slap_repeats": -1}),
    ],
    variants=[
        Variant("night-game", "Night Game",
                "Under the lights instead of the sun: the board finally has some black in it.",
                video={"tone.lift": 0.03, "tone.contrast": 1.05, "saturation.amount": 1.3}),
        Variant("zoomed-close", "Zoomed Close",
                "Shot on a long lens from the lower bowl: the modules become the subject.",
                video={"pixel_era.res_h": 80, "lcd_screen.grid": 0.6, "lcd_screen.scale": 8,
                       "crt.mask_scale": 4.0}),
    ],
))


# nearest: jumbotron-stadium-1992 (the same job, twenty years earlier); differs:
# a fine LED pitch in 16:9, blazing saturation, and camera moire off the dot matrix.
register_preset(Preset(
    id="led-wall-stadium-2012",
    name="LED Stadium Screen",
    family="exhibition",
    era="2012",
    desc="A modern LED wall shot on a camera that cannot agree with its dot pitch: a fine emissive matrix, moire crawling across it, saturation and brightness pushed to carry across an open arena.",
    tagline="Fine LED dot matrix, blazing color, moire",
    tags=("10s", "dot-pitch", "outdoor", "widescreen"),
    keywords=("led-wall", "stadium", "tens", "led", "dot-matrix", "bright", "saturated",
              "moire", "concert", "big-screen"),
    upscale="sharp",
    video=[
        ("tone", {"exposure": 0.15, "contrast": 1.15, "knee": 0.88}),
        ("saturation", {"amount": 1.35, "vibrance": 0.25}),
        ("lcd_screen", {"grid": 0.35, "scale": 3, "response_smear": 0.05,
                        "backlight_bleed": 0.0, "subpixel": "none",
                        "moire_cam": 0.45}),
        ("sharpen", {"amount": 0.3, "radius": 1.0}),
        ("codec_era", {"enabled": False, "codec": "h264", "crf": 26, "gop": 60}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 40.0, "high_hz": 14000.0}),
        ("a_compressor", {"threshold_db": -18.0, "ratio": 3.0, "attack_ms": 8.0}),
        ("a_pa_bullhorn", {"device": "pa_stadium", "drive": 1.5, "slap_repeats": -1}),
        ("a_room", {"mode": "chamber", "size": 3.0, "decay_s": 1.5, "mix": 0.2,
                    "damp": 0.5, "predelay_ms": 30.0}),
    ],
    variants=[
        Variant("concert-close", "Concert Close",
                "Ten rows back with the wall filling the frame: the moire takes over completely.",
                video={"lcd_screen.moire_cam": 0.75, "lcd_screen.grid": 0.5,
                       "lcd_screen.scale": 5, "saturation.amount": 1.45}),
        Variant("broadcast-of-the-screen", "Broadcast Of The Screen",
                "The wall as it reached the world feed: re-encoded once more on the way out.",
                video={"lcd_screen.moire_cam": 0.2, "codec_era.enabled": True}),
    ],
))


# nearest: pixel-1990 (fat VGA pixels, ordered dither); differs: an arcade raster
# tube in a cabinet - scan gaps, dot mask, glass glare and the noise of a room of them.
register_preset(Preset(
    id="arcade-cabinet-1983",
    name="Arcade Cabinet Tube",
    family="exhibition",
    era="1983",
    desc="A 15 kHz raster monitor behind smoked cabinet glass: 240 lines with black between every one of them, a shadow mask under the phosphor, ceiling light lying across the bezel and the room full of other cabinets.",
    tagline="Bright glass, scanline gaps, cabinet glare",
    tags=("80s", "crt", "raster", "amusements"),
    keywords=("arcade", "cabinet", "eighties", "coin-op", "crt", "scanlines", "glare",
              "quarters", "attract-mode", "joystick", "retro"),
    proc_height=480,
    upscale="soft",
    video=[
        ("tone", {"exposure": 0.38, "contrast": 1.12, "lift": 0.02, "knee": 0.82}),
        ("saturation", {"amount": 1.25}),
        ("pixel_era", {"res_h": 240, "palette": "none", "dither": "none",
                       "contrast_snap": 0.25, "pixel_aspect": 1.2}),
        ("phosphor_decay", {"decay": 0.3, "mode": "p22"}),
        ("crt", {"scan_strength": 0.35, "phosphor_mask": "dots", "mask_scale": 2.0,
                 "mask_strength": 0.3, "bloom": 0.45, "beam_bloom": 0.3,
                 "glass_glow": 0.15, "curvature": 0.06, "glare": 0.3,
                 "glare_pos": "tc"}),
        ("framing", {"aspect": "source", "mode": "box", "corner_radius": 0.03}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 200.0, "high_hz": 8000.0}),
        ("a_bitcrush", {"bits": 8, "sr_hz": 22050.0, "antialias": False}),
        ("a_speaker", {"device": "portable_radio_1975", "strength": 0.8,
                       "cabinet_knock": 0.4}),
        ("a_bed", {"bed": "tv_shop_wall", "level_db": -36.0, "duck": 0.3}),
    ],
    variants=[
        Variant("vertical-cabinet", "Vertical Cabinet",
                "The tube turned on its side for a vertical game: taller pixels, deeper scan gaps.",
                video={"pixel_era.pixel_aspect": 0.9, "crt.scan_strength": 0.4}),
        Variant("dying-monitor", "Dying Monitor",
                "The cabinet at the back nobody fixes: blooming, bent, and half a colour out.",
                video={"crt.bloom": 0.6, "crt.misconvergence": 1.5, "crt.curvature": 0.1,
                       "crt.glare": 0.45}),
    ],
))


# nearest: pixel-1990 (a coarse computer raster); differs: four shades of green
# reflected off a passive panel with no backlight and enormous ghosting.
register_preset(Preset(
    id="gameboy-screen-1989",
    name="Game Boy Screen",
    family="exhibition",
    era="1989",
    desc="A reflective dot-matrix panel with four shades of pea-green and no light of its own: 144 lines of it, every moving sprite dragging a ghost, and one piezo speaker doing the rest.",
    tagline="Four-green DMG, ghosting smear, no light",
    tags=("80s", "lcd", "portable-console", "reflective"),
    keywords=("game-boy", "dmg", "eighties", "handheld", "green", "lcd", "ghosting",
              "nintendo", "four-shades", "pea-soup", "nostalgia"),
    upscale="sharp",
    video=[
        ("tone", {"exposure": -0.18, "contrast": 1.3, "pivot": 0.46, "gamma": 1.05}),
        ("pixel_era", {"res_h": 144, "palette": "gameboy_dmg", "dither": "bayer2",
                       "contrast_snap": 0.35, "pixel_aspect": 1.0}),
        ("lcd_screen", {"grid": 0.35, "scale": 5, "response_smear": 0.75,
                        "backlight_bleed": 0.0, "viewing_angle": 0.3,
                        "subpixel": "none"}),
        ("framing", {"aspect": "source", "mode": "box", "corner_radius": 0.03}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 300.0, "high_hz": 4000.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_bitcrush", {"bits": 4, "sr_hz": 8192.0, "antialias": True}),
        ("a_speaker", {"device": "transistor_pocket_1965", "strength": 0.9}),
    ],
    variants=[
        Variant("worm-light", "Worm Light",
                "The clip-on lamp bent over the top of the screen: green, but at least visible.",
                video={"tone.exposure": 0.02, "lcd_screen.backlight_bleed": 0.15}),
        Variant("pocket-1996", "Pocket",
                "The smaller 1996 revision: a faster panel and better contrast in the same four greens.",
                video={"lcd_screen.grid": 0.3, "lcd_screen.response_smear": 0.5,
                       "pixel_era.contrast_snap": 0.45}),
    ],
))


# nearest: stag-loop-1959 (a hooded arcade viewer, lacework scratches); differs:
# 1905 photographic flip cards, not film - sepia paper, card-flip bounce, a crank.
register_preset(Preset(
    id="mutoscope-flip-card-1905",
    name="Mutoscope Flip-Card",
    family="exhibition",
    era="1905",
    desc="Eight hundred photographic cards on a drum, flipped past a slot by a hand crank: sepia paper stock instead of film, a hard hood around the eyepiece, and the picture bouncing every time a card lets go.",
    tagline="Sepia card flicker, hood vignette, stutter",
    tags=("1900s", "card-reel", "silent-era", "hand-cranked"),
    keywords=("mutoscope", "flip-card", "1900s", "peep-show", "arcade", "sepia",
              "hand-crank", "penny", "hooded", "cards", "actuality"),
    proc_height=520,
    upscale="soft",
    video=[
        ("mono", {"amount": 1.0, "response": "orthochromatic", "tint": "sepia",
                  "tint_amt": 0.9}),
        ("tone", {"contrast": 1.25, "lift": 0.05, "knee": 0.75}),
        ("optics", {"soft_focus": 0.15, "corner_softness": 0.3}),
        ("grain", {"amount": 0.45, "size": 1.9, "chroma_grain": 0.0, "stock": "print_dupe",
                   "layers": "mono", "intermittent": 0.3, "mottle": 0.25}),
        ("cadence", {"pattern": "silent_irregular", "speed": "silent_16fps_in_24"}),
        ("flicker", {"amount": 0.4, "character": "hand_cranked", "spatial": 0.3}),
        ("gate_weave", {"amount": 2.0, "splice_bump": 1.0, "rotation": 0.1}),
        ("dust", {"density": 0.3, "hairs": 0.15}),
        ("plate", {"pack": "paper_textures", "opacity": 0.14, "blend": "multiply",
                   "cycle": "hold"}),
        ("vignette", {"amount": 0.6, "radius": 0.6, "softness": 0.4, "roundness": 1.0}),
        ("framing", {"aspect": "source", "mode": "box", "corner_radius": 0.03}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 200.0, "high_hz": 4000.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_speaker", {"device": "gramophone_horn_1915", "strength": 0.6}),
        ("a_bed", {"bed": "air_handler_hall", "level_db": -38.0, "duck": 0.2}),
    ],
    variants=[
        Variant("fresh-reel", "Fresh Reel",
                "A new card set in a serviced machine: the crank runs even and the cards stay put.",
                video={"dust.density": 0.1, "gate_weave.amount": 1.2, "flicker.amount": 0.26,
                       "grain.mottle": 0.12}),
        Variant("worn-cards", "Worn Cards",
                "Twenty years of pennies: corners rounded, paper showing through, cards catching.",
                video={"dust.density": 0.6, "flicker.amount": 0.5, "plate.opacity": 0.24,
                       "grain.mottle": 0.4}),
    ],
))


# nearest: none (no headset look exists in the library); the closest relatives are
# the flat-panel presets and gopro barrel warp, neither of which has a screen door.
register_preset(Preset(
    id="vr-headset-screen-door-2016",
    name="VR Headset Screen-Door",
    family="exhibition",
    era="2016",
    desc="One eye of a 2016 consumer headset: an OLED panel close enough that the gaps between subpixels become a mesh, pre-warped for the lens and fringing chromatically toward the edges.",
    tagline="Screen-door grid, chromatic edge, barrel",
    tags=("10s", "hmd", "stereo", "per-eye"),
    keywords=("vr", "headset", "tens", "screen-door", "oculus", "subpixel",
              "barrel-distortion", "chromatic-aberration", "oled", "immersive", "scifi"),
    upscale="sharp",
    video=[
        ("tone", {"exposure": -0.05, "contrast": 1.05, "knee": 0.9}),
        ("saturation", {"amount": 1.05}),
        ("optics", {"distortion": 0.18, "chromatic_aberration": 3.5,
                    "corner_softness": 0.35}),
        ("lcd_screen", {"grid": 0.5, "scale": 3, "response_smear": 0.05,
                        "backlight_bleed": 0.0, "subpixel": "none"}),
        ("vignette", {"amount": 0.35, "radius": 0.8, "softness": 0.5}),
        ("framing", {"aspect": "source", "mode": "box", "corner_radius": 0.25}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 40.0, "high_hz": 16000.0}),
        ("a_codec_aac", {"kbps": 96, "mono": False}),
        ("a_speaker", {"device": "earbud_2005", "strength": 0.5}),
    ],
    variants=[
        Variant("pentile-oled", "PenTile OLED",
                "A pentile subpixel layout: fewer subpixels, more mesh, the same panel size.",
                video={"lcd_screen.grid": 0.62, "lcd_screen.scale": 4,
                       "optics.chromatic_aberration": 4.0}),
        Variant("high-res-2020", "High-Res 2020",
                "Four years of pixel density later: the door is nearly shut and the lenses are better.",
                video={"lcd_screen.grid": 0.22, "lcd_screen.scale": 2,
                       "optics.chromatic_aberration": 1.5, "optics.distortion": 0.12}),
    ],
))
