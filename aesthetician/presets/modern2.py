"""Modern-family presets: prestige television and contemporary cinema, 1990 on.

Where `modern.py` holds pure grades, these carry the whole delivery path a
show actually had: the gauge it was shot on, the telecine or the sensor, the
carrier it reached the living room through, and a mix that matches the era's
dialogue chain. Photochemical looks keep real grain; video-era looks keep the
composite stage that made them look like television.
"""

from ..engine.presets import Preset, Variant, register_preset


# nearest: super16-indie-1994 and auth-streaming-true-crime-2017; differs: TV-drama Super
# 16 through a 4:3 telecine with a gray naturalist grade, not a blown-up lab print.
register_preset(Preset(
    id="prestige-cable-super16-2002",
    name="Prestige Cable Super 16",
    family="modern",
    era="2002",
    desc="Thirteen episodes shot Super 16 for cable: documentary grain at full size, color pulled toward wet gray asphalt, a pin-registered telecine to 4:3 and a shotgun mic doing all the work.",
    tagline="Super 16 grain, Baltimore gray, wide mono",
    tags=("00s", "16mm", "tv", "usa", "crime"),
    keywords=("prestige", "cable", "aughts", "super-16", "the-wire", "gray",
              "naturalism", "drama", "hbo-era", "street"),
    proc_height=620,
    upscale="soft",
    video=[
        ("stock", {"profile": "vision_90s", "strength": 0.6}),
        ("tone", {"contrast": 1.05, "lift": 0.025, "knee": 0.84}),
        ("balance", {"warmth": -0.05, "shadow_tint": "teal", "shadow_amt": 0.18}),
        ("saturation", {"amount": 0.78, "vibrance": 0.05}),
        ("optics", {"bloom_mids": 0.25}),
        ("grain", {"amount": 0.44, "size": 1.95, "chroma_grain": 0.16, "stock": "doc_16",
                   "layers": "color_neg", "roughness": 0.55}),
        ("halation", {"strength": 0.22, "tint": "red_orange", "radius": 0.05}),
        ("telecine_scan", {"pin_stability": "pin_registered", "hop_px": 0.5}),
        ("codec_era", {"enabled": False, "codec": "mpeg2video", "kbps": 5000, "gop": 15}),
        ("framing", {"aspect": "4:3", "mode": "box"}),
    ],
    audio=[
        ("a_historical_mic", {"profile": "shotgun_1975", "amount": 0.45,
                              "self_noise_db": -66.0, "overload": 0.08}),
        ("a_compressor", {"threshold_db": -22.0, "ratio": 2.5, "attack_ms": 10.0,
                          "release_ms": 260.0}),
        ("a_channel_aging", {"width": 1.05, "crosstalk_db": -50.0}),
        ("a_room", {"mode": "room", "size": 1.4, "decay_s": 0.5, "mix": 0.1, "damp": 0.6}),
    ],
    variants=[
        Variant("hd-remaster-16x9", "HD Remaster",
                "The later rescan opened to widescreen, with the grain regraded a shade finer.",
                video={"framing.aspect": "16:9", "framing.mode": "crop",
                       "grain.amount": 0.4}),
        Variant("dvd-2004", "Season Box Set",
                "The 2004 disc: MPEG-2 at five megabits on a short GOP, softening the grain into mosquito noise.",
                video={"codec_era.enabled": True}),
    ],
))


# nearest: prestige-cable-super16-2002 and golden-reverie-1978; differs: warm brown 35 mm
# for a 4:3 network-era TV frame, finer grain and a wider unhurried mix.
register_preset(Preset(
    id="prestige-cable-35mm-1999",
    name="Prestige Cable 35 mm",
    family="modern",
    era="1999",
    desc="A cable drama shot 35 mm in New Jersey: warm negative with brown weighted into the shadows and cream on the skin, telecined pin-registered to 4:3 and mixed unhurried and wide.",
    tagline="Warm 35 mm brown, unhurried Dolby mix",
    tags=("90s", "35mm", "tv", "crime", "usa"),
    keywords=("prestige", "cable", "nineties", "sopranos", "warm", "brown", "35mm",
              "mob-drama", "suburban", "hbo-era"),
    upscale="soft",
    video=[
        ("stock", {"profile": "vision_90s", "strength": 0.8}),
        ("tone", {"contrast": 1.1, "lift": 0.015, "knee": 0.84}),
        ("balance", {"warmth": 0.15, "shadow_tint": "brown", "shadow_amt": 0.2,
                     "high_tint": "cream", "high_amt": 0.12}),
        ("saturation", {"amount": 1.0, "vibrance": 0.08}),
        ("optics", {"bloom_mids": 0.28, "veiling_flare": 0.08}),
        ("grain", {"amount": 0.3, "size": 1.9, "chroma_grain": 0.15, "stock": "fine_35",
                   "layers": "color_neg"}),
        ("halation", {"strength": 0.28, "tint": "red_orange", "radius": 0.06}),
        ("telecine_scan", {"pin_stability": "pin_registered", "hop_px": 0.4}),
        ("vhs", {"enabled": False, "mode": "sp", "luma_noise": 0.24, "chroma_noise": 0.24,
                 "dropouts": 1.5, "sharpen": 0.4, "head_switch": 0.5,
                 "time_base_error": 0.3, "tracking_error": 0.12}),
        ("framing", {"aspect": "4:3", "mode": "box"}),
    ],
    audio=[
        ("a_compressor", {"threshold_db": -22.0, "ratio": 2.5, "attack_ms": 12.0,
                          "release_ms": 280.0}),
        ("a_channel_aging", {"width": 1.15, "crosstalk_db": -50.0}),
        ("a_room", {"mode": "room", "size": 0.8, "decay_s": 0.35, "mix": 0.08,
                    "damp": 0.65}),
    ],
    variants=[
        Variant("hd-remaster", "HD Remaster",
                "Rescanned and opened to widescreen for the streaming catalog, grain and warmth intact.",
                video={"framing.aspect": "16:9", "framing.mode": "crop"}),
        Variant("vhs-screener", "Awards Screener",
                "The tape that went out to voters: an SP dub with head-switch noise across the bottom.",
                video={"vhs.enabled": True},
                audio={"a_channel_aging.width": 0.9}),
    ],
))


# nearest: prestige-cable-35mm-1999 and teal-orange-2012; differs: a retro-warm saturated
# grade with cigarette haze on a clean 35 mm HD master, not a period negative or a tentpole.
register_preset(Preset(
    id="period-ad-agency-2007",
    name="Period Ad-Agency Drama",
    family="modern",
    era="2007",
    desc="A 2007 series dressed as 1962: modern 35 mm graded warm and saturated the way the era's ads printed, with veiling cigarette haze in every conference room and a plate reverb on the score.",
    tagline="Sixties-styled 35 mm, smoke haze, HD",
    tags=("00s", "35mm", "tv", "drama", "advertising"),
    keywords=("mad-men", "aughts", "period", "sixties-style", "warm", "saturated",
              "smoke", "agency", "prestige", "retro-styled"),
    upscale="sharp",
    video=[
        ("stock", {"profile": "vision_90s", "strength": 0.8}),
        ("tone", {"contrast": 1.12, "lift": 0.02, "knee": 0.82}),
        ("balance", {"warmth": 0.2, "high_tint": "yellow", "high_amt": 0.24}),
        ("saturation", {"amount": 1.24, "vibrance": 0.18}),
        ("optics", {"veiling_flare": 0.3, "diffusion": 0.1, "bloom_mids": 0.32}),
        ("grain", {"amount": 0.26, "size": 1.8, "chroma_grain": 0.14, "stock": "fine_35",
                   "layers": "color_neg"}),
        ("halation", {"strength": 0.34, "tint": "warm_white", "radius": 0.07,
                      "threshold": 0.68}),
        ("vignette", {"amount": 0.2, "softness": 0.8, "radius": 0.95}),
        ("interlace", {"enabled": False, "combing": 0.4, "twitter": 0.25}),
        ("framing", {"aspect": "16:9", "mode": "box"}),
    ],
    audio=[
        ("a_compressor", {"threshold_db": -22.0, "ratio": 2.5, "attack_ms": 10.0,
                          "release_ms": 260.0}),
        ("a_channel_aging", {"width": 1.2, "crosstalk_db": -50.0}),
        ("a_room", {"mode": "plate1960", "size": 1.2, "decay_s": 0.8, "mix": 0.08}),
    ],
    variants=[
        Variant("bluray", "Disc Master",
                "The disc transfer: the same grade with the grain resolved a stop finer.",
                video={"grain.amount": 0.22, "grain.chroma_grain": 0.1}),
        Variant("sd-broadcast-2007", "SD Simulcast",
                "The standard-definition feed of the same episode, cropped to 4:3 and interlaced.",
                video={"interlace.enabled": True, "framing.aspect": "4:3",
                       "framing.mode": "crop"}),
    ],
))


# nearest: teal-orange-2012 and neo-western-2017; differs: a yellow/cyan location split
# carried on real 35 mm grain for a 16:9 television frame, not a digital tentpole grade.
register_preset(Preset(
    id="desert-crime-35mm-2008",
    name="Desert Crime 35 mm",
    family="modern",
    era="2008",
    desc="High-desert crime on 35 mm: exteriors filtered to hot yellow sun, interiors held cyan and cold, contrast set hard and the negative grain left where the scanner found it.",
    tagline="Yellow desert sun, cyan interiors, HD",
    tags=("00s", "35mm", "tv", "thriller", "usa"),
    keywords=("breaking-bad", "aughts", "desert", "yellow", "cyan", "crime",
              "albuquerque", "35mm", "prestige", "contrast"),
    upscale="sharp",
    video=[
        ("stock", {"profile": "vision_90s", "strength": 0.8}),
        ("tone", {"contrast": 1.2, "lift": 0.005, "knee": 0.84}),
        ("balance", {"warmth": 0.1, "shadow_tint": "teal", "shadow_amt": 0.3,
                     "high_tint": "yellow", "high_amt": 0.34}),
        ("saturation", {"amount": 1.05, "vibrance": 0.12}),
        ("optics", {"veiling_flare": 0.15, "bloom_mids": 0.28}),
        ("grain", {"amount": 0.28, "size": 1.8, "chroma_grain": 0.14, "stock": "fine_35",
                   "layers": "color_neg"}),
        ("halation", {"strength": 0.25, "tint": "orange", "radius": 0.06}),
        ("sharpen", {"amount": 0.15, "radius": 1.0}),
        ("framing", {"aspect": "16:9", "mode": "box"}),
    ],
    audio=[
        ("a_compressor", {"threshold_db": -20.0, "ratio": 2.5, "attack_ms": 8.0,
                          "release_ms": 240.0}),
        ("a_channel_aging", {"width": 1.25, "crosstalk_db": -52.0}),
        ("a_room", {"mode": "room", "size": 0.7, "decay_s": 0.3, "mix": 0.06,
                    "damp": 0.7}),
    ],
    variants=[
        Variant("mexico-yellow", "South of the Border",
                "The location filter cranked the way the show announces a border crossing.",
                video={"balance.warmth": 0.25, "balance.high_amt": 0.4,
                       "saturation.amount": 1.0}),
        Variant("night-cyan", "Night Cyan",
                "The other half of the split: two thirds of a stop down with the warmth taken out.",
                video={"tone.exposure": -0.2, "balance.warmth": 0.0,
                       "balance.shadow_amt": 0.3}),
    ],
))


# nearest: soap-opera-1982 and golden-reverie-1978; differs: 1990 network film telecine with
# heavy warm diffusion and a surreal set hum, not a videotape studio or a seventies negative.
register_preset(Preset(
    id="dreamy-small-town-1990",
    name="Dreamy Small-Town Drama",
    family="modern",
    era="1990",
    desc="Network mystery from a town with too many pines: eighties Kodak negative shot through heavy diffusion, warm wood everywhere, telecined to composite 4:3 with a low hum sitting under the room.",
    tagline="Soft 35 mm, warm wood, network hum",
    tags=("90s", "35mm", "tv", "drama", "usa"),
    keywords=("twin-peaks", "nineties", "dreamy", "small-town", "soft", "warm-wood",
              "mystery", "soap-surreal", "diner", "pine"),
    proc_height=560,
    upscale="soft",
    video=[
        ("stock", {"profile": "kodak_80s", "strength": 0.8}),
        ("tone", {"contrast": 1.05, "lift": 0.02, "knee": 0.8}),
        ("balance", {"warmth": 0.15, "shadow_tint": "brown", "shadow_amt": 0.15,
                     "high_tint": "cream", "high_amt": 0.2}),
        ("saturation", {"amount": 1.05, "vibrance": 0.1}),
        ("optics", {"diffusion": 0.25, "soft_focus": 0.15, "bloom_mids": 0.3}),
        ("grain", {"amount": 0.3, "size": 1.7, "chroma_grain": 0.15, "stock": "fine_35",
                   "layers": "color_neg"}),
        ("halation", {"strength": 0.35, "tint": "warm_white", "radius": 0.09,
                      "threshold": 0.7}),
        ("telecine_scan", {"pin_stability": "pin_registered", "hop_px": 0.5}),
        ("ntsc", {"strength": 0.4, "luma_bw": 4.2, "chroma_bw": 1.2, "phase_noise": 1.0,
                  "rainbow": 0.15, "dot_crawl": 0.18}),
        ("vhs", {"enabled": False, "mode": "sp", "luma_noise": 0.2, "chroma_noise": 0.2,
                 "dropouts": 1.0, "sharpen": 0.4, "head_switch": 0.5,
                 "time_base_error": 0.3}),
        ("interlace", {"combing": 0.45, "twitter": 0.25}),
        ("crt", {"bloom": 0.28, "scan_strength": 0.1, "glass_glow": 0.12,
                 "curvature": 0.02}),
        ("framing", {"aspect": "4:3", "mode": "box"}),
    ],
    audio=[
        ("a_compressor", {"threshold_db": -22.0, "ratio": 2.5, "attack_ms": 10.0,
                          "release_ms": 280.0}),
        ("a_channel_aging", {"width": 1.1, "crosstalk_db": -48.0}),
        ("a_room", {"mode": "plate1960", "size": 1.3, "decay_s": 0.9, "mix": 0.1}),
        ("a_tv_sound", {"hz": "60", "buzz_db": -64.0, "hum_db": -66.0, "comp": 0.45}),
        ("a_hum", {"hz": "60", "level_db": -60.0, "buzz": 0.2}),
    ],
    variants=[
        Variant("studio-master", "Studio Master",
                "The film-to-tape master before the network chain: composite mostly out of the way.",
                video={"ntsc.strength": 0.2, "crt.bloom": 0.2, "interlace.twitter": 0.15},
                audio={"a_tv_sound.buzz_db": -72.0, "a_hum.level_db": -70.0}),
        Variant("vhs-timer", "Off the Timer",
                "Somebody's VCR caught it at ten o'clock: an SP dub with the head switch showing.",
                video={"vhs.enabled": True},
                audio={"a_tv_sound.buzz_db": -54.0}),
    ],
))


# nearest: sitcom-1993 and auth-dslr-indie-naturalism-2012; differs: flat green fluorescent
# HD with a hunting long-lens zoom and an office room bed, no laugh track and no film stage.
register_preset(Preset(
    id="mockumentary-office-2005",
    name="Single-Camera Mockumentary",
    family="modern",
    era="2005",
    desc="Shot like a documentary crew got permission: flat fluorescent HD with green in the shadows, a long lens hunting focus into every reaction, and the ceiling tubes buzzing under the dialogue.",
    tagline="Flat fluorescent HD, zoom snaps, hush",
    tags=("00s", "1080i", "comedy", "workplace", "usa"),
    keywords=("mockumentary", "the-office", "aughts", "single-camera", "fluorescent",
              "flat", "zoom", "talking-head", "sitcom", "hd"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.0, "lift": 0.03, "knee": 0.88}),
        ("balance", {"tint": -0.08, "shadow_tint": "green", "shadow_amt": 0.15}),
        ("saturation", {"amount": 0.9, "vibrance": 0.05}),
        ("optics", {"hunt_rate": 1.5, "focus_drift": 0.06, "bloom_mids": 0.25}),
        ("flicker", {"amount": 0.04, "character": "slow_drift", "color_flicker": 0.05,
                     "spatial": 0.1}),
        ("sharpen", {"amount": 0.25, "radius": 1.0}),
        ("ntsc", {"enabled": False, "strength": 0.4, "luma_bw": 4.0, "chroma_bw": 1.0,
                  "phase_noise": 1.2, "dot_crawl": 0.2}),
        ("interlace", {"combing": 0.35, "twitter": 0.22}),
        ("framing", {"aspect": "16:9", "mode": "box"}),
    ],
    audio=[
        ("a_historical_mic", {"profile": "shotgun_1975", "amount": 0.5,
                              "self_noise_db": -64.0, "overload": 0.08}),
        ("a_compressor", {"threshold_db": -20.0, "ratio": 3.0, "attack_ms": 8.0,
                          "release_ms": 220.0}),
        ("a_channel_aging", {"width": 1.0, "crosstalk_db": -52.0}),
        ("a_bed", {"bed": "fluorescent_office", "level_db": -40.0, "duck": 0.35}),
    ],
    variants=[
        Variant("sd-4x3-2005", "SD Simulcast",
                "The standard-definition feed: cropped to 4:3 and put back through the composite chain.",
                video={"framing.aspect": "4:3", "framing.mode": "crop",
                       "ntsc.enabled": True}),
        Variant("bluray-remaster", "Progressive Remaster",
                "The later progressive master: fields gone, edge sharpening backed off, tubes steady.",
                video={"sharpen.amount": 0.1, "interlace.enabled": False,
                       "flicker.amount": 0.0}),
    ],
))


# nearest: neon-noir-2018 and teal-orange-2012; differs: a 2019 promo built on anamorphic
# ghosting and an oval vignette at 2.35 with a loud AAC bounce, not a flat color grade.
register_preset(Preset(
    id="neon-anamorphic-music-video-2019",
    name="Neon Anamorphic Music Video",
    family="modern",
    era="2019",
    desc="A one-night promo on an anamorphic set: aperture ghosts streaking off every practical, red halation around the signage, an oval falloff in the corners and a bounce mastered loud.",
    tagline="Anamorphic streaks, neon halation, oval",
    tags=("10s", "digital-cinema", "scope", "promo", "club"),
    keywords=("music-video", "tens", "anamorphic", "neon", "streaks", "halation",
              "alexa", "pop", "night", "cinematic"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.15, "lift": 0.02, "knee": 0.86}),
        ("balance", {"warmth": -0.05, "shadow_tint": "blue", "shadow_amt": 0.38,
                     "high_tint": "pink", "high_amt": 0.24}),
        ("saturation", {"amount": 1.3, "vibrance": 0.28}),
        ("optics", {"aperture_ghost": 0.45, "veiling_flare": 0.25, "bokeh_swirl": 0.2,
                    "bloom_mids": 0.3}),
        ("grain", {"amount": 0.18, "size": 1.5, "chroma_grain": 0.1, "stock": "fine_35",
                   "layers": "color_neg"}),
        ("halation", {"strength": 0.45, "tint": "red", "radius": 0.1, "threshold": 0.66}),
        ("vhs", {"enabled": False, "mode": "sp", "luma_noise": 0.25, "chroma_noise": 0.25,
                 "dropouts": 2.0, "sharpen": 0.45, "head_switch": 0.6,
                 "time_base_error": 0.35}),
        ("interlace", {"enabled": False, "combing": 0.45, "twitter": 0.3}),
        ("vignette", {"amount": 0.25, "roundness": 0.55, "softness": 0.7, "radius": 0.9}),
        ("framing", {"aspect": "2.35", "mode": "box"}),
    ],
    audio=[
        ("a_compressor", {"threshold_db": -18.0, "ratio": 4.0, "attack_ms": 5.0,
                          "release_ms": 140.0, "makeup_db": 2.0}),
        ("a_channel_aging", {"width": 1.35, "crosstalk_db": -50.0}),
        ("a_codec_aac", {"kbps": 192, "mono": False}),
    ],
    variants=[
        Variant("vhs-insert", "Tape Insert",
                "The cutaway that pretends to be a home tape: SP noise, fields back on, boxed to 4:3.",
                video={"vhs.enabled": True, "interlace.enabled": True,
                       "framing.aspect": "4:3"},
                audio={"a_codec_aac.kbps": 96}),
        Variant("daylight-cut", "Daylight Cut",
                "The rooftop half of the same promo: less blue in the blacks and the neon turned down.",
                video={"balance.shadow_amt": 0.14, "saturation.amount": 1.1,
                       "halation.strength": 0.25}),
    ],
))


# nearest: drone-aerial-2016 and frutiger-aero-2007; differs: an interior HDR bracket
# flattened with glowing window pulls and a wide-lens warp, not an aerial or a glass gloss.
register_preset(Preset(
    id="real-estate-hdr-2019",
    name="Real-Estate HDR Tour",
    family="modern",
    era="2019",
    desc="A listing walkthrough shot in brackets and blended flat: contrast squeezed out of the middle, every window pulled back to cyan daylight and glowing, on a lens wide enough to bend the walls.",
    tagline="HDR flatten, glowing windows, wide warp",
    tags=("10s", "hd", "interior", "commercial", "wide-angle"),
    keywords=("real-estate", "tens", "hdr", "oversaturated", "windows", "wide-lens",
              "listing", "tour", "glowing", "unreal"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 0.9, "lift": 0.06, "knee": 0.6}),
        ("balance", {"warmth": 0.1, "high_tint": "cyan", "high_amt": 0.15}),
        ("saturation", {"amount": 1.35, "vibrance": 0.35}),
        ("optics", {"distortion": 0.08, "corner_softness": 0.05, "aperture_ghost": 0.1,
                    "bloom_mids": 0.3}),
        ("halation", {"strength": 0.3, "tint": "warm_white", "radius": 0.1,
                      "threshold": 0.62}),
        ("sharpen", {"amount": 0.45, "radius": 1.1}),
        ("codec_era", {"codec": "h264", "crf": 22, "gop": 60}),
        ("framing", {"aspect": "16:9", "mode": "box"}),
    ],
    audio=[
        ("a_compressor", {"threshold_db": -20.0, "ratio": 3.0, "attack_ms": 8.0,
                          "release_ms": 200.0}),
        ("a_codec_aac", {"kbps": 128, "mono": False}),
        ("a_bed", {"bed": "air_handler_hall", "level_db": -44.0, "duck": 0.3}),
    ],
    variants=[
        Variant("natural-grade", "Natural Grade",
                "The version an agent with taste asked for: contrast returned, halos off the trim.",
                video={"saturation.amount": 1.05, "tone.contrast": 1.05,
                       "sharpen.amount": 0.15}),
        Variant("twilight-shoot", "Twilight Shoot",
                "The dusk exterior in the same package: a third of a stop under with the windows burning.",
                video={"tone.exposure": -0.3, "balance.shadow_tint": "blue",
                       "balance.shadow_amt": 0.3, "halation.strength": 0.45,
                       "saturation.amount": 1.2}),
    ],
))
