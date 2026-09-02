"""Process-family presets: what one specific stock, color system or lab
treatment does to a picture, independent of what was shot on it.

Each base is a clean print of the process itself; the variants are the states
that process is actually found in - as struck, dupe, faded, restored, pushed.
"""

from ..engine.presets import Preset, Variant, register_preset


# nearest: kinemacolor-1912 (additive, but temporal scarlet/emerald trails); differs:
# a static three-colour line screen in the emulsion, no motion fringing, muted dyes.
register_preset(Preset(
    id="process-dufaycolor-1936",
    name="Dufaycolor Mosaic",
    family="process",
    era="1936",
    desc="British additive réseau stock: a ruled screen of red, green and blue lines sits under the emulsion, holding the dyes muted and the highlights soft while the mosaic crawls under every pan.",
    tagline="Réseau line mosaic, muted additive dyes, soft",
    tags=("30s", "35mm", "uk", "colour-screen"),
    keywords=("dufaycolor", "reseau", "mosaic", "additive", "thirties", "british",
              "early-color", "screen-process", "muted", "lines", "documentary"),
    upscale="soft",
    video=[
        ("balance", {"warmth": 0.05, "high_tint": "cream", "high_amt": 0.1}),
        ("tone", {"contrast": 0.95, "lift": 0.045, "knee": 0.82}),
        ("saturation", {"amount": 0.85, "hue": 5.0}),
        ("optics", {"soft_focus": 0.2, "corner_softness": 0.18}),
        ("crt", {"phosphor_mask": "dots", "mask_scale": 2.0, "mask_strength": 0.19,
                 "scan_strength": 0.0, "bloom": 0.0}),
        ("grain", {"amount": 0.3, "size": 1.9, "chroma_grain": 0.2,
                   "stock": "fine_35", "layers": "reversal"}),
        ("halation", {"strength": 0.25, "tint": "warm_white", "threshold": 0.74}),
        ("fade", {"amount": 0.05, "profile": "neutral"}),
        ("gate_weave", {"amount": 1.0, "splice_bump": 0.6}),
        ("dust", {"density": 0.25, "hairs": 0.15}),
        ("framing", {"aspect": "1.37", "mode": "box"}),
    ],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_optical_track", {"low_hz": 120.0, "high_hz": 5800.0,
                             "academy_rolloff": "newsreel_1930s",
                             "cell_noise": -45.0, "flutter": 0.5, "drive": 1.5}),
        ("a_compressor", {"threshold_db": -20.0, "ratio": 4.0, "attack_ms": 8.0}),
    ],
    variants=[
        Variant("projected-large", "Projected Large",
                "Thrown big enough in a small hall that the réseau ruling becomes the texture.",
                video={"crt.mask_scale": 3.0, "crt.mask_strength": 0.28}),
        Variant("dupe-print", "Dupe Print",
                "A duplicate struck off the original: the mosaic smears and the dyes start to go.",
                video={"crt.mask_strength": 0.09, "grain.amount": 0.4, "fade.amount": 0.15}),
    ],
))


# nearest: hammer-eastmancolor-1960 (later single-strip, saturated); differs:
# 1942 Agfa monopack dyes read olive-brown with soft magenta skin and low saturation.
register_preset(Preset(
    id="process-agfacolor-1942",
    name="Agfacolor Wartime",
    family="process",
    era="1942",
    desc="Wartime Agfa monopack: brown-olive dye layers, skin drifting magenta under studio arcs, a slow soft-focus optic and a compressed variable-area optical track.",
    tagline="Olive-brown dyes, soft magenta skin, hush",
    tags=("40s", "35mm", "germany", "monopack"),
    keywords=("agfacolor", "forties", "german", "wartime", "ufa", "olive", "muted",
              "early-color", "soft", "reversal-neg"),
    upscale="soft",
    video=[
        ("stock", {"profile": "agfa_60s", "strength": 1.0}),
        ("balance", {"warmth": 0.16, "tint": 0.07,
                     "shadow_tint": "brown", "shadow_amt": 0.34,
                     "high_tint": "yellow", "high_amt": 0.16}),
        ("tone", {"contrast": 1.05, "lift": 0.04, "knee": 0.82}),
        ("saturation", {"amount": 0.7}),
        ("optics", {"soft_focus": 0.12, "veiling_flare": 0.08}),
        ("grain", {"amount": 0.34, "size": 1.9, "chroma_grain": 0.18,
                   "stock": "fine_35", "layers": "print_from_neg"}),
        ("halation", {"strength": 0.25, "tint": "warm_white", "threshold": 0.74}),
        ("fade", {"amount": 0.08, "profile": "neutral"}),
        ("gate_weave", {"amount": 0.8, "splice_bump": 0.5}),
        ("dust", {"density": 0.2, "hairs": 0.12}),
        ("framing", {"aspect": "1.37", "mode": "box"}),
    ],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_optical_track", {"low_hz": 110.0, "high_hz": 6000.0,
                             "academy_rolloff": "feature_1940s",
                             "cell_noise": -47.0, "flutter": 0.42, "drive": 1.4}),
        ("a_compressor", {"threshold_db": -20.0, "ratio": 3.0, "attack_ms": 9.0}),
        ("a_room", {"mode": "chamber", "size": 1.1, "decay_s": 0.6, "mix": 0.1}),
    ],
    variants=[
        Variant("captured-print", "Captured Print",
                "A reel taken east in 1945 and reprinted on Soviet stock: greener shadows, weaker dye.",
                video={"balance.shadow_tint": "green", "balance.shadow_amt": 0.25,
                       "saturation.amount": 0.7}),
        Variant("restored", "Restored Scan",
                "A modern wet-gate scan of the camera negative with the dirt taken out.",
                video={"fade.amount": 0.0, "dust.density": 0.05, "grain.amount": 0.28}),
    ],
))


# nearest: process-agfacolor-1942 (same dye family, warm and olive); differs:
# 1955 Belgian Geva runs cool and cyan, and fades from the edges of the reel in.
register_preset(Preset(
    id="process-gevacolor-1955",
    name="Gevacolor Fugitive",
    family="process",
    era="1955",
    desc="Belgian Gevaert positive: cyan-weighted skies, cool shadows and the fugitive dye set that let continental features go pale from the reel edge inward.",
    tagline="Cool Belgian dyes, cyan skies, fading edges",
    tags=("50s", "35mm", "belgium", "dye-fade"),
    keywords=("gevacolor", "fifties", "belgian", "european", "fugitive", "cool",
              "cyan", "faded", "agfa-lineage", "continental", "period"),
    upscale="soft",
    video=[
        ("stock", {"profile": "agfa_60s", "strength": 0.8}),
        ("balance", {"warmth": -0.16, "tint": -0.04, "shadow_tint": "teal",
                     "shadow_amt": 0.26, "high_tint": "cyan", "high_amt": 0.22}),
        ("tone", {"contrast": 1.05, "lift": 0.03, "knee": 0.8}),
        ("saturation", {"amount": 0.85}),
        ("optics", {"soft_focus": 0.06}),
        ("grain", {"amount": 0.34, "size": 1.95, "chroma_grain": 0.18,
                   "stock": "fine_35", "layers": "print_from_neg"}),
        ("halation", {"strength": 0.25, "tint": "neutral", "threshold": 0.76}),
        ("fade", {"amount": 0.12, "profile": "neutral", "bloom_whites": 0.2}),
        ("gate_weave", {"amount": 0.8, "splice_bump": 0.5}),
        ("dust", {"density": 0.25, "hairs": 0.15}),
        ("vignette", {"amount": 0.2, "softness": 0.6}),
        ("framing", {"aspect": "1.37", "mode": "box"}),
    ],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_optical_track", {"low_hz": 100.0, "high_hz": 6400.0,
                             "academy_rolloff": "feature_1940s",
                             "cell_noise": -47.0, "flutter": 0.4, "drive": 1.35}),
        ("a_compressor", {"threshold_db": -20.0, "ratio": 3.0, "attack_ms": 9.0}),
    ],
    variants=[
        Variant("fresh-print", "Fresh Print",
                "Straight from the Mortsel lab in 1955, before anything had a chance to leave.",
                video={"fade.amount": 0.0, "vignette.amount": 0.05, "saturation.amount": 0.98}),
        Variant("heavily-faded", "Heavily Faded",
                "The same reel in 1980: dye gone thin, contrast gone with it.",
                video={"fade.amount": 0.4, "saturation.amount": 0.7, "tone.contrast": 0.95}),
    ],
))


# nearest: auth-italian-peplum-spectacle-1959 (sun-baked Eastman, dubbed); differs:
# this is the 1954 Ferrania emulsion itself - warm, soft in the reds, no genre grade.
register_preset(Preset(
    id="process-ferraniacolor-1954",
    name="Ferraniacolor Reel",
    family="process",
    era="1954",
    desc="Italian Ferrania positive: warm yellow highlights, reds that spread rather than bite, a sunlit grain structure and a chamber-reverbed Italian optical track.",
    tagline="Warm Italian dye, soft reds, sunlit grain",
    tags=("50s", "35mm", "italy", "ferrania"),
    keywords=("ferraniacolor", "fifties", "italian", "warm", "soft-red", "sunlit",
              "early-color", "continental", "cinecitta", "pastel"),
    upscale="soft",
    video=[
        ("stock", {"profile": "eastman_60s", "strength": 0.7}),
        ("balance", {"warmth": 0.15, "shadow_tint": "brown", "shadow_amt": 0.1,
                     "high_tint": "yellow", "high_amt": 0.15}),
        ("tone", {"contrast": 1.08, "lift": 0.03, "knee": 0.8}),
        ("saturation", {"amount": 1.0, "vibrance": 0.08, "hue": -3.0}),
        ("optics", {"soft_focus": 0.1, "veiling_flare": 0.1}),
        ("grain", {"amount": 0.36, "size": 2.0, "chroma_grain": 0.2,
                   "stock": "fine_35", "layers": "print_from_neg"}),
        ("halation", {"strength": 0.3, "tint": "red_orange", "threshold": 0.7}),
        ("fade", {"amount": 0.08, "profile": "eastman_pink"}),
        ("gate_weave", {"amount": 0.9, "splice_bump": 0.5}),
        ("dust", {"density": 0.25, "hairs": 0.15}),
        ("framing", {"aspect": "1.37", "mode": "box"}),
    ],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_optical_track", {"low_hz": 100.0, "high_hz": 6200.0,
                             "academy_rolloff": "feature_1940s",
                             "cell_noise": -46.0, "flutter": 0.45, "drive": 1.45}),
        ("a_compressor", {"threshold_db": -19.0, "ratio": 3.2, "attack_ms": 8.0}),
        ("a_room", {"mode": "chamber", "size": 1.2, "decay_s": 0.7, "mix": 0.12}),
    ],
    variants=[
        Variant("dubbed-export", "Dubbed Export",
                "The export print: post-synched voices sitting up in the dubbing stage, dye already turning.",
                video={"fade.amount": 0.2},
                audio={"a_room.mix": 0.25, "a_room.decay_s": 0.95}),
        Variant("restored", "Restored",
                "A clean scan from the surviving separation elements.",
                video={"fade.amount": 0.0, "dust.density": 0.08}),
    ],
))


# nearest: cinecolor-travel-print-1948 (brick red, cyan-green sky, duplitized); differs:
# 1949 Republic Trucolor holds registration, pushes skin brown-red and prints harder.
register_preset(Preset(
    id="process-trucolor-1949",
    name="Trucolor Two-Color",
    family="process",
    era="1949",
    desc="Republic's two-color answer to Technicolor: orange and cyan carrying the whole spectrum, faces baked to brown-red, greens gone teal, printed hard for the Saturday houses.",
    tagline="Orange-cyan dyes, brown-red skin, Republic",
    tags=("40s", "35mm", "usa", "duplitized"),
    keywords=("trucolor", "republic", "forties", "two-color", "orange", "cyan",
              "western-color", "consolidated", "cheap-color", "b-western"),
    upscale="soft",
    video=[
        ("stock", {"profile": "technicolor2", "strength": 0.9}),
        ("balance", {"warmth": 0.18, "shadow_tint": "teal", "shadow_amt": 0.24,
                     "high_tint": "yellow", "high_amt": 0.12}),
        ("tone", {"contrast": 1.12, "lift": 0.03, "knee": 0.76}),
        ("saturation", {"amount": 1.04, "hue": -2.0}),
        ("optics", {"soft_focus": 0.08, "corner_softness": 0.1}),
        ("grain", {"amount": 0.36, "size": 1.95, "chroma_grain": 0.15,
                   "stock": "fine_35", "layers": "print_from_neg"}),
        ("halation", {"strength": 0.3, "tint": "orange", "threshold": 0.72}),
        ("print_char", {"contrast_buildup": 1, "dmax_breath": 0.2, "acutance": 0.2}),
        ("fade", {"amount": 0.0, "profile": "eastman_pink"}),
        ("gate_weave", {"amount": 0.9, "splice_bump": 0.6}),
        ("dust", {"density": 0.3, "hairs": 0.18}),
        ("framing", {"aspect": "1.37", "mode": "box"}),
    ],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_optical_track", {"low_hz": 110.0, "high_hz": 6000.0,
                             "academy_rolloff": "feature_1940s",
                             "cell_noise": -45.0, "flutter": 0.5, "drive": 1.5}),
        ("a_compressor", {"threshold_db": -20.0, "ratio": 3.5, "attack_ms": 7.0}),
    ],
    variants=[
        Variant("worn-tv-print", "Worn TV Print",
                "The 16 mm reduction that circulated to television for twenty years.",
                video={"fade.amount": 0.2, "dust.density": 0.6,
                       "print_char.contrast_buildup": 2, "grain.amount": 0.44}),
        Variant("fresh-release", "Fresh Release",
                "A first-run release print with the dye still at full strength.",
                video={"dust.density": 0.1, "saturation.amount": 1.14}),
    ],
))


# nearest: process-trucolor-1949 (the same duplitized family, orange and cyan); differs:
# the three-color SuperCinecolor set puts lilac in the shadows and lime in the greens.
register_preset(Preset(
    id="process-supercinecolor-1952",
    name="SuperCineColor Three-Color",
    family="process",
    era="1952",
    desc="Cinecolor's third dye laid over a duplitized two-color base: brick-orange skin, lime greens, lilac shadows and a coarse dupe grain that never quite resolved.",
    tagline="Brick-orange, lime-green, lilac shadows",
    tags=("50s", "35mm", "usa", "poverty-row"),
    keywords=("supercinecolor", "cinecolor", "fifties", "three-color", "brick",
              "lime", "lilac", "cheap-color", "b-picture", "sci-fi"),
    upscale="soft",
    video=[
        ("stock", {"profile": "technicolor2", "strength": 0.45}),
        ("balance", {"warmth": -0.02, "tint": 0.14, "shadow_tint": "magenta",
                     "shadow_amt": 0.26, "high_tint": "yellow", "high_amt": 0.08}),
        ("tone", {"contrast": 1.1, "lift": 0.055, "knee": 0.78}),
        ("saturation", {"amount": 0.96, "vibrance": 0.15, "hue": 13.0}),
        ("optics", {"soft_focus": 0.1, "corner_softness": 0.12}),
        ("grain", {"amount": 0.42, "size": 2.1, "chroma_grain": 0.22,
                   "stock": "print_dupe", "layers": "print_from_neg", "mottle": 0.07}),
        ("halation", {"strength": 0.3, "tint": "orange", "threshold": 0.72}),
        ("fade", {"amount": 0.0, "profile": "eastman_pink"}),
        ("gate_weave", {"amount": 1.0, "splice_bump": 0.7}),
        ("dust", {"density": 0.3, "hairs": 0.2}),
        ("framing", {"aspect": "1.37", "mode": "box"}),
    ],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_optical_track", {"low_hz": 110.0, "high_hz": 6200.0,
                             "academy_rolloff": "feature_1940s",
                             "cell_noise": -44.0, "flutter": 0.5, "drive": 1.55}),
        ("a_compressor", {"threshold_db": -20.0, "ratio": 3.5, "attack_ms": 7.0}),
    ],
    variants=[
        Variant("faded-1975", "Faded 1975",
                "Two decades in a distributor's vault: the third dye is the first to leave.",
                video={"fade.amount": 0.3, "saturation.amount": 0.8}),
        Variant("fresh", "Fresh Print",
                "As delivered to the double bill, mosaic dyes at full weight.",
                video={"dust.density": 0.1, "grain.amount": 0.36, "saturation.amount": 1.06}),
    ],
))


# nearest: eastman-faded-1979 (terminal magenta, cyan dye gone); differs:
# a moderate 1955 drift shown as the process itself, in 1.85 with halation intact.
register_preset(Preset(
    id="process-eastmancolor-first-1955",
    name="First-Generation Eastmancolor",
    family="process",
    era="1955",
    desc="The single-strip monopack that ended three-strip printing: warm mid-fifties dye, generous halation off practical lamps, and the pink drift already showing in the first decade.",
    tagline="Single-strip dye, pink drift, soft edges",
    tags=("50s", "35mm", "usa", "monopack"),
    keywords=("eastmancolor", "fifties", "single-strip", "pink", "faded", "dye-fade",
              "early-eastman", "technicolor-replacement", "drift", "warm", "filmic"),
    upscale="soft",
    video=[
        ("stock", {"profile": "eastman_60s", "strength": 0.85}),
        ("balance", {"warmth": 0.1, "high_tint": "cream", "high_amt": 0.08}),
        ("tone", {"contrast": 1.08, "lift": 0.02, "knee": 0.82}),
        ("saturation", {"amount": 1.05}),
        ("optics", {"soft_focus": 0.06, "veiling_flare": 0.08}),
        ("grain", {"amount": 0.34, "size": 1.95, "chroma_grain": 0.18,
                   "stock": "fine_35", "layers": "print_from_neg"}),
        ("halation", {"strength": 0.3, "tint": "red_orange", "threshold": 0.7}),
        ("fade", {"amount": 0.28, "profile": "eastman_pink", "bloom_whites": 0.22}),
        ("gate_weave", {"amount": 0.7, "splice_bump": 0.4}),
        ("dust", {"density": 0.25, "hairs": 0.14}),
        ("framing", {"aspect": "1.85", "mode": "box"}),
    ],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_optical_track", {"low_hz": 70.0, "high_hz": 8000.0,
                             "academy_rolloff": "none",
                             "cell_noise": -49.0, "flutter": 0.4, "drive": 1.35}),
        ("a_compressor", {"threshold_db": -19.0, "ratio": 3.0, "attack_ms": 8.0}),
    ],
    variants=[
        Variant("as-struck-1955", "As Struck",
                "The print the way the lab delivered it, before any dye had gone anywhere.",
                video={"fade.amount": 0.0, "dust.density": 0.1}),
        Variant("vault-red-1985", "Vault Red",
                "Thirty years on a warm shelf: cyan and yellow gone, the whole reel one colour.",
                video={"fade.amount": 0.5, "saturation.amount": 0.9}),
    ],
))


# nearest: doc-16mm-1968 (16 mm documentary grain); differs: the clean 35 mm 5247
# negative baseline of the New Hollywood years, natural-light grade, no gauge cost.
register_preset(Preset(
    id="process-kodak-5247-1975",
    name="Kodak 5247 New Hollywood",
    family="process",
    era="1975",
    desc="The 100T negative every seventies picture was shot on: fine even grain, honest neutral dye, a soft printed shoulder and a little veiling flare off uncoated practicals.",
    tagline="Fine 100T grain, honest color, natural light",
    tags=("70s", "35mm", "usa", "negative"),
    keywords=("kodak", "5247", "seventies", "new-hollywood", "100t", "fine-grain",
              "natural", "honest", "flat", "gordon-willis", "drama"),
    upscale="soft",
    video=[
        ("stock", {"profile": "eastman_70s", "strength": 0.8}),
        ("balance", {"warmth": 0.06}),
        ("tone", {"contrast": 1.06, "lift": 0.02, "knee": 0.86}),
        ("saturation", {"amount": 0.98}),
        ("optics", {"veiling_flare": 0.1}),
        ("grain", {"amount": 0.3, "size": 1.9, "chroma_grain": 0.16,
                   "stock": "fine_35", "layers": "color_neg"}),
        ("halation", {"strength": 0.25, "tint": "red_orange", "threshold": 0.76}),
        ("print_char", {"acutance": 0.25, "contrast_buildup": 1, "dmax_breath": 0.08}),
        ("fade", {"amount": 0.0, "profile": "eastman_pink"}),
        ("gate_weave", {"amount": 0.5, "splice_bump": 0.3}),
        ("dust", {"density": 0.15, "hairs": 0.08}),
        ("framing", {"aspect": "1.85", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 50.0, "high_hz": 10000.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_compressor", {"threshold_db": -18.0, "ratio": 2.5, "attack_ms": 12.0}),
    ],
    variants=[
        Variant("pushed-one-stop", "Pushed One Stop",
                "Rated at 200 and pushed in the bath: grain up, shadows opening.",
                video={"grain.amount": 0.42, "grain.shadow_boost": 0.3, "tone.contrast": 1.14}),
        Variant("faded-release-print", "Faded Release Print",
                "Not the negative but the thousandth answer print, gone pink in a library.",
                video={"fade.amount": 0.25, "dust.density": 0.3, "grain.amount": 0.4}),
    ],
))


# nearest: process-kodak-5247-1975 (the fine-grain 100T baseline); differs:
# 250T trades grain for speed: visible clumping, warm open shadows, hot lamp halation.
register_preset(Preset(
    id="process-kodak-5293-1983",
    name="Kodak 5293 High-Speed",
    family="process",
    era="1983",
    desc="The 250T stock that let eighties units shoot streets at night: grain blooming in the open shadows, warm brown blacks and lamp halation spreading off every practical.",
    tagline="250T grain bloom, warm shadows, lamp halos",
    tags=("80s", "35mm", "usa", "low-light"),
    keywords=("kodak", "5293", "eighties", "high-speed", "250t", "grainy",
              "warm-shadows", "night-shooting", "tungsten", "halation", "thriller"),
    upscale="soft",
    video=[
        ("stock", {"profile": "kodak_80s", "strength": 0.85}),
        ("balance", {"warmth": 0.13, "shadow_tint": "brown", "shadow_amt": 0.18}),
        ("tone", {"contrast": 1.1, "lift": 0.03, "knee": 0.84}),
        ("saturation", {"amount": 1.0}),
        ("optics", {"veiling_flare": 0.08}),
        ("grain", {"amount": 0.42, "size": 2.0, "chroma_grain": 0.2,
                   "stock": "fine_35", "layers": "color_neg", "shadow_boost": 0.25}),
        ("halation", {"strength": 0.4, "tint": "red_orange", "threshold": 0.68,
                      "radius": 0.07}),
        ("print_char", {"acutance": 0.2, "contrast_buildup": 1}),
        ("gate_weave", {"amount": 0.55, "splice_bump": 0.3}),
        ("dust", {"density": 0.15, "hairs": 0.08}),
        ("framing", {"aspect": "1.85", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 40.0, "high_hz": 12000.0}),
        ("a_channel_aging", {"width": 1.1, "crosstalk_db": -48.0, "skew_us": 10.0}),
        ("a_compressor", {"threshold_db": -18.0, "ratio": 2.5, "attack_ms": 10.0}),
    ],
    variants=[
        Variant("pushed-two-stops", "Pushed Two Stops",
                "Rated at 1000 for a street the unit could not light: grain everywhere.",
                video={"grain.amount": 0.55, "grain.shadow_boost": 0.5, "tone.lift": 0.05}),
        Variant("fine-grain-intermediate", "Fine-Grain Intermediate",
                "Printed down to an interpositive: the clumping smooths, the halos stay.",
                video={"grain.amount": 0.32, "halation.strength": 0.28}),
    ],
))


# nearest: process-kodak-5293-1983 (same years, Kodak tungsten); differs: Fuji's
# cyan-green shadow bias and pale magenta skin, softer grain, cooler overall.
register_preset(Preset(
    id="process-fuji-8510-1985",
    name="Fuji 8510 Cyan-Green",
    family="process",
    era="1985",
    desc="Fuji's eighties negative as the Hong Kong and Japanese labs printed it: cyan-green in every shadow, skin drifting pale magenta, grain softer and rounder than Kodak's.",
    tagline="Cyan-green shadows, pale magenta skin, soft",
    tags=("80s", "35mm", "japan", "negative"),
    keywords=("fuji", "8510", "eighties", "japanese-stock", "cyan-green", "magenta-skin",
              "soft-grain", "pastel", "hong-kong-stock", "cool"),
    upscale="soft",
    video=[
        ("stock", {"profile": "kodak_80s", "strength": 0.5}),
        ("balance", {"warmth": -0.04, "tint": 0.04, "shadow_tint": "teal",
                     "shadow_amt": 0.28, "high_tint": "pink", "high_amt": 0.12}),
        ("tone", {"contrast": 1.05, "lift": 0.025, "knee": 0.86}),
        ("saturation", {"amount": 0.98}),
        ("optics", {"soft_focus": 0.05}),
        ("grain", {"amount": 0.36, "size": 2.0, "roughness": 0.35, "chroma_grain": 0.2,
                   "stock": "fine_35", "layers": "color_neg"}),
        ("halation", {"strength": 0.28, "tint": "warm_white", "threshold": 0.74}),
        ("fade", {"amount": 0.0, "profile": "eastman_pink"}),
        ("gate_weave", {"amount": 0.55, "splice_bump": 0.3}),
        ("dust", {"density": 0.15, "hairs": 0.08}),
        ("framing", {"aspect": "1.85", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 40.0, "high_hz": 12000.0}),
        ("a_channel_aging", {"width": 1.05, "crosstalk_db": -44.0}),
        ("a_compressor", {"threshold_db": -18.0, "ratio": 2.5, "attack_ms": 10.0}),
    ],
    variants=[
        Variant("hk-lab-print", "Hong Kong Lab Print",
                "Timed hot in a Kowloon lab for a fast turnaround: saturation up, dye already going.",
                video={"saturation.amount": 1.12, "fade.amount": 0.08,
                       "tone.contrast": 1.1}),
        Variant("restored", "Restored Scan",
                "A modern grade pulling the green back out of the shadows.",
                video={"balance.shadow_amt": 0.2, "dust.density": 0.05,
                       "grain.amount": 0.3}),
    ],
))


# nearest: process-kodak-5293-1983 (the grainy 250T it replaced); differs: Vision
# holds tight grain at the same speed, blacks stay clean, sound goes wide and digital.
register_preset(Preset(
    id="process-vision-500t-1996",
    name="Kodak Vision 500T",
    family="process",
    era="1996",
    desc="The stock that made fast tungsten clean: tight fine grain at 500 ASA, unbroken blacks, restrained halation and a wide digitally-mixed track behind it.",
    tagline="Clean fast tungsten, tight grain, deep blacks",
    tags=("90s", "35mm", "usa", "modern-stock"),
    keywords=("vision", "500t", "nineties", "kodak", "tungsten", "clean", "fast-stock",
              "night", "modern-negative", "tight-grain", "filmic"),
    upscale="soft",
    video=[
        ("stock", {"profile": "vision_90s", "strength": 0.9}),
        ("balance", {"warmth": 0.04}),
        ("tone", {"contrast": 1.1, "lift": 0.0, "knee": 0.88}),
        ("saturation", {"amount": 1.0}),
        ("grain", {"amount": 0.28, "size": 1.8, "roughness": 0.6, "chroma_grain": 0.14,
                   "stock": "fine_35", "layers": "color_neg"}),
        ("halation", {"strength": 0.25, "tint": "red_orange", "threshold": 0.78}),
        ("print_char", {"acutance": 0.28, "contrast_buildup": 1}),
        ("gate_weave", {"amount": 0.35, "splice_bump": 0.2}),
        ("dust", {"density": 0.1, "hairs": 0.05}),
        ("dvnr", {"enabled": False, "strength": 0.2, "wax": 0.2}),
        ("sharpen", {"enabled": False, "amount": 0.25, "radius": 1.0}),
        ("framing", {"aspect": "1.85", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 20.0, "high_hz": 18000.0}),
        ("a_channel_aging", {"width": 1.2, "crosstalk_db": -56.0, "skew_us": 6.0}),
        ("a_compressor", {"threshold_db": -16.0, "ratio": 2.0, "attack_ms": 14.0}),
    ],
    variants=[
        Variant("pushed-500t", "Pushed 500T",
                "One stop under and pushed: the grain finally shows in the shadows.",
                video={"grain.amount": 0.4, "grain.shadow_boost": 0.35, "tone.lift": 0.03}),
        Variant("telecine-hd-2000", "HD Telecine",
                "Run through a turn-of-the-century HD telecine with noise reduction and edge enhancement on.",
                video={"dvnr.enabled": True, "sharpen.enabled": True, "grain.amount": 0.22}),
    ],
))


# nearest: streaming-filmic-2021 (faux grain over a sensor image); differs: real
# Vision3 latitude - a genuinely soft highlight shoulder with gentle organic grain.
register_preset(Preset(
    id="process-vision3-2010",
    name="Kodak Vision3 Latitude",
    family="process",
    era="2010",
    desc="Late film-era negative scanned to a digital intermediate: highlights rolling off for stops past clipping, neutral skin, and a fine even grain that never clumps.",
    tagline="Huge highlight latitude, gentle grain",
    tags=("10s", "35mm", "usa", "scan"),
    keywords=("vision3", "tens", "kodak", "latitude", "5219", "modern-film", "neutral",
              "gentle-grain", "digital-intermediate", "clean-film", "filmic"),
    upscale="soft",
    video=[
        ("stock", {"profile": "vision_90s", "strength": 0.6}),
        ("balance", {"warmth": 0.02}),
        ("tone", {"contrast": 1.05, "knee": 0.6, "lift": 0.005}),
        ("saturation", {"amount": 1.0, "vibrance": 0.06}),
        ("grain", {"amount": 0.24, "size": 1.7, "roughness": 0.7, "chroma_grain": 0.12,
                   "stock": "fine_35", "layers": "color_neg"}),
        ("halation", {"strength": 0.22, "tint": "warm_white", "threshold": 0.8}),
        ("gate_weave", {"amount": 0.3, "splice_bump": 0.15}),
        ("framing", {"aspect": "2.35", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 20.0, "high_hz": 20000.0}),
        ("a_channel_aging", {"width": 1.3, "crosstalk_db": -60.0, "skew_us": 4.0}),
        ("a_compressor", {"threshold_db": -16.0, "ratio": 2.0, "attack_ms": 15.0}),
    ],
    variants=[
        Variant("4k-di", "4K Intermediate",
                "Scanned at 4K and finished clean: the grain drops almost out of sight.",
                video={"grain.amount": 0.2, "grain.size": 1.5, "halation.strength": 0.18}),
        Variant("super16-vision3", "Super 16 Vision3",
                "The same emulsion on 16 mm and blown up: the latitude survives, the grain does not stay quiet.",
                video={"grain.stock": "doc_16", "grain.amount": 0.44, "grain.size": 2.2,
                       "grain.roughness": 0.5}),
    ],
))


# nearest: bleach-bypass-1998 (chrome highlights, crushed gray shadows); differs:
# ENR is the partial version - deeper blacks and retained midtone color, highlights unclipped.
register_preset(Preset(
    id="process-enr-silver-retention-1995",
    name="ENR Silver Retention",
    family="process",
    era="1995",
    desc="The Technicolor Rome silver-retention bath at partial strength: retained metal in the blacks, colour drained but not gone, grain gathering in the shadows, highlights left unclipped.",
    tagline="Retained silver blacks, muted metallic color",
    tags=("90s", "35mm", "italy", "lab-process"),
    keywords=("enr", "silver-retention", "nineties", "technicolor-rome", "muted",
              "metallic", "deep-black", "skip-bleach-lite", "desaturated", "prestige"),
    upscale="soft",
    video=[
        ("stock", {"profile": "vision_90s", "strength": 0.7}),
        ("balance", {"warmth": 0.02}),
        ("tone", {"contrast": 1.28, "lift": -0.02, "knee": 0.85, "pivot": 0.45}),
        ("saturation", {"amount": 0.72}),
        ("grain", {"amount": 0.34, "size": 1.8, "chroma_grain": 0.1,
                   "stock": "fine_35", "layers": "color_neg", "shadow_boost": 0.3}),
        ("halation", {"strength": 0.2, "tint": "warm_white", "threshold": 0.8}),
        ("print_char", {"acutance": 0.3, "contrast_buildup": 1, "dmax_breath": 0.06}),
        ("gate_weave", {"amount": 0.35, "splice_bump": 0.2}),
        ("framing", {"aspect": "2.35", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 20.0, "high_hz": 18000.0}),
        ("a_channel_aging", {"width": 1.2, "crosstalk_db": -55.0, "skew_us": 6.0}),
        ("a_compressor", {"threshold_db": -17.0, "ratio": 2.5, "attack_ms": 12.0}),
    ],
    variants=[
        Variant("light-enr", "Light ENR",
                "The lab dialled to a quarter: blacks firm up, the colour mostly survives.",
                video={"tone.contrast": 1.15, "saturation.amount": 0.85,
                       "grain.shadow_boost": 0.2}),
        Variant("full-bleach-bypass", "Full Bleach Bypass",
                "The bleach skipped altogether: chrome highlights, colour nearly gone.",
                video={"tone.contrast": 1.4, "tone.knee": 0.7, "saturation.amount": 0.55}),
    ],
))


# nearest: golden-reverie-1978 (backlit wheat and halation); differs: flashing is
# a lab step, not a light - shadows lift milky and even, with no source behind them.
register_preset(Preset(
    id="process-flashed-negative-1971",
    name="Flashed Negative Haze",
    family="process",
    era="1971",
    desc="Negative pre-fogged in the lab before it was ever exposed: shadows lifted to a flat milk, contrast collapsed, dye desaturated, with heavy veiling flare over the whole frame.",
    tagline="Pre-fogged shadows, milky lows, soft dye",
    tags=("70s", "35mm", "usa", "pre-exposed"),
    keywords=("flashing", "flashed", "pre-fog", "seventies", "mccabe", "milky",
              "low-contrast", "haze", "altman", "zsigmond", "revisionist"),
    upscale="soft",
    video=[
        ("stock", {"profile": "eastman_70s", "strength": 0.75}),
        ("balance", {"warmth": 0.1, "high_tint": "yellow", "high_amt": 0.12}),
        ("tone", {"contrast": 0.85, "lift": 0.12, "knee": 0.75}),
        ("saturation", {"amount": 0.85}),
        ("optics", {"veiling_flare": 0.3, "diffusion": 0.15}),
        ("grain", {"amount": 0.4, "size": 2.0, "chroma_grain": 0.2,
                   "stock": "fine_35", "layers": "color_neg"}),
        ("halation", {"strength": 0.3, "tint": "warm_white", "threshold": 0.7}),
        ("fade", {"amount": 0.1, "profile": "neutral"}),
        ("gate_weave", {"amount": 0.6, "splice_bump": 0.35}),
        ("dust", {"density": 0.2, "hairs": 0.12}),
        ("framing", {"aspect": "1.85", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 50.0, "high_hz": 9500.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_compressor", {"threshold_db": -19.0, "ratio": 2.5, "attack_ms": 12.0}),
    ],
    variants=[
        Variant("heavy-flash", "Heavy Flash",
                "Flashed twice as far: the blacks never get below a warm gray.",
                video={"tone.lift": 0.18, "tone.contrast": 0.78, "optics.veiling_flare": 0.4}),
        Variant("print-down", "Printed Down",
                "The timer fought it back in the print: some shadow returns, the haze stays.",
                video={"tone.lift": 0.06, "tone.contrast": 0.95, "optics.veiling_flare": 0.2}),
    ],
))


# nearest: moonlight-blue-2015 (two stops under, drowned in blue, modern grade); differs:
# the 1955 filter version keeps blown skies and warm sun edges under the blue.
register_preset(Preset(
    id="process-day-for-night-1955",
    name="Day-for-Night Blue",
    family="process",
    era="1955",
    desc="Noon shot through a blue filter and printed down two stops: skies still blown white where the lie shows, sun edges still warm, grain lifted by the underexposure.",
    tagline="Underexposed sun, blue filter, hard skies",
    tags=("50s", "35mm", "usa", "night-effect"),
    keywords=("day-for-night", "blue", "fifties", "underexposed", "filter", "night-scene",
              "western-night", "moonlight", "technique", "fake-night"),
    upscale="soft",
    video=[
        ("tone", {"exposure": -0.85, "contrast": 1.2, "knee": 0.8, "pivot": 0.38,
                  "lift": 0.02}),
        ("balance", {"warmth": -0.35, "tint": -0.05, "shadow_tint": "blue",
                     "shadow_amt": 0.4}),
        ("saturation", {"amount": 0.7}),
        ("mono", {"enabled": False, "amount": 1.0, "response": "panchromatic",
                  "tint": "neutral", "tint_amt": 0.1}),
        ("optics", {"veiling_flare": 0.06}),
        ("grain", {"amount": 0.34, "size": 1.95, "chroma_grain": 0.15,
                   "stock": "fine_35", "layers": "print_from_neg", "shadow_boost": 0.25}),
        ("halation", {"strength": 0.15, "tint": "neutral", "threshold": 0.7}),
        ("gate_weave", {"amount": 0.7, "splice_bump": 0.4}),
        ("dust", {"density": 0.2, "hairs": 0.12}),
        ("framing", {"aspect": "1.85", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 60.0, "high_hz": 9000.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_compressor", {"threshold_db": -20.0, "ratio": 3.0, "attack_ms": 9.0}),
    ],
    variants=[
        Variant("seventies-graded-blue", "Seventies Graded Blue",
                "The same trick twenty years on, pulled back in the timing: softer, less blue, still a lie.",
                video={"tone.exposure": -0.7, "tone.contrast": 1.1,
                       "balance.warmth": -0.25, "saturation.amount": 0.8}),
        Variant("bw-day-for-night", "Black-and-White Night",
                "Shot on panchromatic through a red filter: the sky goes to slate and the lie holds better.",
                video={"mono.enabled": True, "tone.exposure": -1.0, "tone.contrast": 1.32,
                       "saturation.amount": 1.0}),
    ],
))


# nearest: silent-1918 (ink lips, milk skies, violent flicker, untinted); differs:
# a dye-bath blue night base with an amber day variant and a much calmer crank.
register_preset(Preset(
    id="process-tinted-toned-nitrate-1921",
    name="Tinted and Toned Nitrate",
    family="process",
    era="1921",
    desc="A silent release print coloured in the bath rather than the camera: the whole reel dipped blue for night, orthochromatic skies gone white, crank speed wandering under a steady dye.",
    tagline="Blue-night tint, amber day, silent flicker",
    tags=("20s", "35mm", "silent-era", "tinting"),
    keywords=("tinted", "toned", "nitrate", "twenties", "silent", "blue-tint", "amber",
              "hand-toned", "dye-bath", "archival"),
    proc_height=640,
    upscale="soft",
    video=[
        ("mono", {"amount": 1.0, "response": "orthochromatic",
                  "tint": "cyanotype", "tint_amt": 0.75}),
        ("balance", {"warmth": -0.3, "tint": -0.04, "shadow_tint": "blue",
                     "shadow_amt": 0.25}),
        ("tone", {"contrast": 1.2, "lift": 0.04, "knee": 0.74}),
        ("optics", {"soft_focus": 0.15, "corner_softness": 0.28}),
        ("grain", {"amount": 0.4, "size": 2.0, "chroma_grain": 0.0,
                   "stock": "newsreel_35", "layers": "mono", "intermittent": 0.25}),
        ("halation", {"strength": 0.2, "tint": "neutral", "threshold": 0.72}),
        ("cadence", {"pattern": "silent_irregular", "speed": "silent_16fps_in_24"}),
        ("flicker", {"amount": 0.25, "character": "hand_cranked", "spatial": 0.25}),
        ("gate_weave", {"amount": 1.4, "splice_bump": 1.2}),
        ("scratches", {"count": 2, "transient_rate": 1.2}),
        ("dust", {"density": 0.4, "hairs": 0.3}),
        ("vignette", {"amount": 0.35, "softness": 0.6}),
        ("framing", {"aspect": "1.37", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 150.0, "high_hz": 5000.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_speaker", {"device": "gramophone_horn_1915", "strength": 0.4}),
        ("a_bed", {"bed": "record_surface_loop", "level_db": -30.0, "duck": 0.25}),
    ],
    variants=[
        Variant("amber-daylight", "Amber Daylight",
                "The daylight reel out of the same lab: an amber bath instead of the blue one.",
                video={"mono.tint": "nitrate_warm", "mono.tint_amt": 0.9,
                       "balance.warmth": 0.3, "balance.shadow_tint": "brown"}),
        Variant("red-fire-tint", "Red Fire Tint",
                "The burning-building reel, dipped in a red-orange bath the projectionist could smell.",
                video={"mono.tint": "sepia", "mono.tint_amt": 1.0,
                       "balance.tint": 0.35, "balance.warmth": 0.55,
                       "balance.shadow_tint": "brown", "balance.shadow_amt": 0.3}),
    ],
))


# nearest: process-dufaycolor-1936 (the theatrical réseau); differs: a home-movie
# 16 mm lenticular with coarse vertical lenticules, very faint colour and a projector.
register_preset(Preset(
    id="process-lenticular-kodacolor-1928",
    name="Lenticular Kodacolor",
    family="process",
    era="1928",
    desc="Amateur 16 mm colour before dyes: vertical lenticules embossed into the base and a banded taking filter, giving faint pastel colour on a black-and-white silver image.",
    tagline="Vertical lens stripes, faint pastel color",
    tags=("20s", "16mm", "usa", "lenticule"),
    keywords=("kodacolor", "lenticular", "twenties", "home-movie", "stripes", "pastel",
              "additive", "16mm", "early-color", "amateur"),
    proc_height=600,
    upscale="soft",
    video=[
        ("balance", {"warmth": 0.05}),
        ("tone", {"exposure": 0.2, "contrast": 0.95, "lift": 0.05, "knee": 0.82}),
        ("saturation", {"amount": 0.6}),
        ("optics", {"soft_focus": 0.22, "corner_softness": 0.2}),
        ("crt", {"phosphor_mask": "grille", "mask_scale": 2.0, "mask_strength": 0.11,
                 "scan_strength": 0.0, "bloom": 0.0}),
        ("grain", {"amount": 0.34, "size": 1.95, "roughness": 0.6, "chroma_grain": 0.15,
                   "stock": "doc_16", "layers": "reversal", "mottle": 0.05}),
        ("halation", {"strength": 0.2, "tint": "warm_white", "threshold": 0.74}),
        ("cadence", {"pattern": "silent_irregular", "speed": "silent_16fps_in_24"}),
        ("flicker", {"amount": 0.2, "character": "projector"}),
        ("gate_weave", {"amount": 1.4, "splice_bump": 1.0}),
        ("dust", {"density": 0.3, "hairs": 0.2}),
        ("vignette", {"amount": 0.22, "softness": 0.6}),
        ("framing", {"aspect": "4:3", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 150.0, "high_hz": 6000.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_projector", {"machine": "proj_16mm", "level_db": -30.0}),
    ],
    variants=[
        Variant("filter-misaligned", "Filter Misaligned",
                "The banded filter off its register: colour drops away and what is left is wrong.",
                video={"saturation.amount": 0.3, "saturation.hue": 15.0,
                       "crt.mask_strength": 0.18, "crt.mask_misalign": 0.5}),
        Variant("good-projection", "Good Projection",
                "A properly banded projector lens: the lenticules recede and the colour comes up.",
                video={"crt.mask_strength": 0.06, "saturation.amount": 0.72}),
    ],
))


# nearest: techniscope-blowup-1966 (two-perf 60s blowup, printer softness); differs:
# a 90s Super 35 optical blowup - grainier scope with no anamorphic flare or squeeze.
register_preset(Preset(
    id="process-super35-blowup-1995",
    name="Super 35 Anamorphic Blowup",
    family="process",
    era="1995",
    desc="Spherical Super 35 negative optically squeezed to a scope release print: a whole extra generation of grain and softness at the corners, and none of the anamorphic flare.",
    tagline="Blown-up scope grain, soft edges, no flare",
    tags=("90s", "35mm", "usa", "blow-up"),
    keywords=("super-35", "blowup", "nineties", "spherical", "scope", "grainier",
              "soft-edges", "anamorphic-print", "optical-blowup", "2.35", "blockbuster"),
    upscale="soft",
    video=[
        ("stock", {"profile": "vision_90s", "strength": 0.8}),
        ("balance", {"warmth": 0.05, "shadow_tint": "blue", "shadow_amt": 0.1}),
        ("tone", {"contrast": 1.12, "lift": 0.02, "knee": 0.84}),
        ("saturation", {"amount": 1.05}),
        ("optics", {"corner_softness": 0.12, "soft_focus": 0.06}),
        ("optical_composite", {"softness": 0.12, "registration": 0.06,
                               "layer_haze": 0.04, "density_breath": 0.1}),
        ("grain", {"amount": 0.4, "size": 2.1, "chroma_grain": 0.16,
                   "stock": "fine_35", "layers": "print_from_neg"}),
        ("halation", {"strength": 0.25, "tint": "red_orange", "threshold": 0.74}),
        ("print_char", {"contrast_buildup": 1, "acutance": 0.12, "dmax_breath": 0.1}),
        ("gate_weave", {"amount": 0.5, "splice_bump": 0.3}),
        ("dust", {"density": 0.15, "hairs": 0.08}),
        ("framing", {"aspect": "2.35", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 20.0, "high_hz": 18000.0}),
        ("a_channel_aging", {"width": 1.3, "crosstalk_db": -52.0, "skew_us": 8.0}),
        ("a_compressor", {"threshold_db": -17.0, "ratio": 2.5, "attack_ms": 12.0}),
    ],
    variants=[
        Variant("digital-intermediate-2001", "Digital Intermediate",
                "The optical stage replaced by a scan and a record-out: the extra generation disappears.",
                video={"optical_composite.enabled": False, "grain.amount": 0.3,
                       "grain.size": 1.8, "optics.corner_softness": 0.05}),
        Variant("two-perf-blowup", "Two-Perf Blowup",
                "Half the negative area to start with: the same optical stage, twice the grain.",
                video={"grain.amount": 0.48, "grain.size": 2.3,
                       "optical_composite.softness": 0.2}),
    ],
))
