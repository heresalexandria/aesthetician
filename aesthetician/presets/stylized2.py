"""Stylized-family presets: named internet aesthetics rebuilt from physical stages.

Every look here is assembled out of the same parts the archival families use.
A synthwave frame is a real magenta grade on a real SP tape behind a real
aperture grille; a deep-fried meme is five real JPEG generations. Nothing is a
shader, and each one carries the sound path its era actually had.
"""

from ..engine.presets import Preset, Variant, register_preset


# nearest: vaporwave-vhs-1986; differs: hard magenta/cyan neon instead of dreamy
# teal/pink, aperture-grille CRT, sharper SP tape, stereo cassette dub.
register_preset(Preset(
    id="synthwave-outrun-2015",
    name="Synthwave Outrun",
    family="stylized",
    era="2015",
    desc="The 1984 that never happened, built from real parts: magenta pushed into the shadows and cyan into the highlights, neon halation blooming off an SP tape through an aperture-grille tube, over a stereo cassette dub of the cue.",
    tagline="Magenta-cyan neon, VHS SP, CRT grille",
    tags=("10s", "vhs", "crt", "grade", "nostalgia"),
    keywords=("synthwave", "outrun", "retrowave", "neon", "magenta", "cyan",
              "eighties-revival", "grid", "chrome", "vhs-aesthetic"),
    proc_height=540,
    upscale="soft",
    video=[
        ("tone", {"contrast": 1.15, "lift": 0.02, "knee": 0.8, "pivot": 0.44}),
        ("balance", {"warmth": -0.14, "tint": 0.1, "shadow_tint": "magenta",
                     "shadow_amt": 0.42, "high_tint": "cyan", "high_amt": 0.34}),
        ("saturation", {"amount": 1.35, "vibrance": 0.3}),
        ("halation", {"strength": 0.32, "tint": "red", "radius": 0.09, "threshold": 0.7}),
        ("ntsc", {"strength": 0.5, "phase_noise": 1.5, "rainbow": 0.22,
                  "dot_crawl": 0.28, "chroma_bw": 0.7}),
        ("vhs", {"mode": "sp", "luma_noise": 0.2, "chroma_noise": 0.2, "dropouts": 0.5,
                 "sharpen": 0.5, "head_switch": 0.35, "time_base_error": 0.2,
                 "chroma_delay": 1.4, "flagging": 0.12}),
        ("interlace", {"combing": 0.4, "twitter": 0.25}),
        ("crt", {"phosphor_mask": "grille", "mask_scale": 1.0, "mask_strength": 0.14,
                 "scan_strength": 0.12, "bloom": 0.35, "bloom_radius": 12.0,
                 "curvature": 0.03, "glass_glow": 0.15}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 40.0, "high_hz": 15000.0}),
        ("a_tape_sat", {"drive": 2.5, "bump_db": 4.0, "hf_loss": 0.35}),
        ("a_analog_dub", {"format": "cassette", "generations": 1, "alignment": 0.2,
                          "compression": 0.3, "hiss_db": -52.0}),
        ("a_channel_aging", {"width": 1.3, "crosstalk_db": -38.0, "skew_us": 60.0,
                             "phase_wander": 0.15}),
        ("a_compressor", {"threshold_db": -20.0, "ratio": 3.0, "attack_ms": 6.0,
                          "release_ms": 180.0, "makeup_db": 1.5}),
    ],
    variants=[
        Variant("clean-render", "Clean Render",
                "The artwork before anybody taped it: the grade and the grille, no dropouts and no composite.",
                video={"vhs.enabled": False, "ntsc.enabled": False, "crt.scan_strength": 0.1},
                audio={"a_analog_dub.generations": 0, "a_tape_sat.hf_loss": 0.15}),
        Variant("worn-tape", "Worn Tape",
                "The second-generation dub somebody actually owned: noisier, dropping out, top end gone.",
                video={"vhs.luma_noise": 0.35, "vhs.dropouts": 3.0, "vhs.generation": 2,
                       "vhs.tracking_error": 0.15},
                audio={"a_analog_dub.generations": 2, "a_analog_dub.hiss_db": -44.0,
                       "a_tape_sat.hf_loss": 0.55}),
    ],
))


# nearest: digital-green-1999 and minidv-2000; differs: cool blue-silver chrome gloss with
# aperture ghosts on a DV chroma path, no terminal green and no camcorder handling.
register_preset(Preset(
    id="y2k-chrome-2000",
    name="Y2K Chrome",
    family="stylized",
    era="2000",
    desc="Millennium product-video gloss: a cool blue-silver grade with speculars clipped to liquid chrome, aperture ghosts crossing a wide lens, and a DV chroma path sharpened hard at the edges.",
    tagline="Blue-silver chrome, lens ghosts, DV sheen",
    tags=("00s", "dv", "grade", "corporate", "commercial"),
    keywords=("y2k", "chrome", "millennium", "blue", "silver", "gloss", "lens-flare",
              "futuristic", "bubble", "techno"),
    proc_height=600,
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.2, "exposure": 0.08, "lift": 0.01, "knee": 0.6,
                  "pivot": 0.45}),
        ("balance", {"warmth": -0.26, "shadow_tint": "blue", "shadow_amt": 0.4,
                     "high_tint": "cyan", "high_amt": 0.3}),
        ("saturation", {"amount": 0.85, "vibrance": 0.12}),
        ("optics", {"aperture_ghost": 0.35, "veiling_flare": 0.2, "diffusion": 0.1,
                    "bloom_mids": 0.35}),
        ("halation", {"strength": 0.3, "tint": "warm_white", "radius": 0.07,
                      "threshold": 0.7}),
        ("chroma_dv", {"ratio": "4:2:0", "edge_sharpen": 0.4, "dct_blocks": 0.06}),
        ("sharpen", {"amount": 0.2, "radius": 1.0}),
        ("codec_era", {"enabled": False, "codec": "mpeg2video", "kbps": 3000, "gop": 15}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_compressor", {"threshold_db": -18.0, "ratio": 3.0, "attack_ms": 5.0,
                          "release_ms": 160.0, "makeup_db": 1.0}),
        ("a_channel_aging", {"width": 1.3, "crosstalk_db": -40.0, "skew_us": 30.0}),
        ("a_codec_mp3", {"kbps": "128", "mono": False}),
    ],
    variants=[
        Variant("dvd-menu-loop", "DVD Menu Loop",
                "The same twelve seconds behind a disc menu, MPEG-2 at three megabits on a short GOP.",
                video={"codec_era.enabled": True}),
        Variant("ice-white", "Ice White",
                "The press-kit version: a third of a stop brighter with the color drained out of the chrome.",
                video={"tone.exposure": 0.15, "saturation.amount": 0.8}),
    ],
))


# nearest: y2k-chrome-2000 and pastel-pop-2019; differs: glossy blue-green bloom on a
# clean HD H.264 delivery, no blown chrome and no pastel lift.
register_preset(Preset(
    id="frutiger-aero-2007",
    name="Glossy Aero",
    family="stylized",
    era="2007",
    desc="The wallpaper that shipped with the laptop: blue-green sky under a glass gloss, warm-white bloom on every specular edge, delivered as a clean H.264 file with nothing broken in it.",
    tagline="Glass gloss, blue-green bloom, clean HD",
    tags=("00s", "hd", "grade", "desktop", "corporate"),
    keywords=("frutiger-aero", "aero", "aughts", "glossy", "glass", "blue-green",
              "bloom", "clean", "skeuomorphic", "vista"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.05, "lift": 0.02, "knee": 0.86}),
        ("balance", {"warmth": -0.03, "shadow_tint": "teal", "shadow_amt": 0.26,
                     "high_tint": "cyan", "high_amt": 0.24}),
        ("saturation", {"amount": 1.24, "vibrance": 0.28}),
        ("optics", {"diffusion": 0.18, "soft_focus": 0.06, "bloom_mids": 0.3}),
        ("halation", {"strength": 0.3, "tint": "warm_white", "radius": 0.1,
                      "threshold": 0.66}),
        ("sharpen", {"amount": 0.2, "radius": 1.0}),
        ("codec_era", {"codec": "h264", "crf": 20, "gop": 60}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_compressor", {"threshold_db": -20.0, "ratio": 2.5, "attack_ms": 8.0,
                          "release_ms": 200.0, "makeup_db": 1.0}),
        ("a_channel_aging", {"width": 1.3, "crosstalk_db": -48.0}),
        ("a_codec_aac", {"kbps": 128, "mono": False}),
    ],
    variants=[
        Variant("corporate-stock-footage", "Corporate Stock Footage",
                "The library clip version: the same gloss dialed back to something a bank would license.",
                video={"saturation.amount": 1.1, "optics.diffusion": 0.1,
                       "halation.strength": 0.25}),
        Variant("wallpaper-4k", "Wallpaper Crop",
                "Encoded for the desktop rather than the browser: harder edges, far less quantizer.",
                video={"sharpen.amount": 0.35, "codec_era.crf": 16}),
    ],
))


# nearest: liminal-cctv-2002 and webcore-2007; differs: oversaturated warm haze through
# three upload generations, not drained fluorescent CCTV and not amber FLV blocking.
register_preset(Preset(
    id="dreamcore-2021",
    name="Dreamcore",
    family="stylized",
    era="2021",
    desc="A photograph of a photograph of a hallway: warm haze pushed past the saturation the camera saw, three JPEG generations of banding, banded down to 240p with the room recorded from the far end.",
    tagline="Low-res upload mush, warm haze, wrong hue",
    tags=("2020s", "web", "240p", "grade", "surreal"),
    keywords=("dreamcore", "weirdcore", "twenties", "low-res", "oversaturated", "haze",
              "uncanny", "nostalgia", "jpeg", "liminal-adjacent"),
    upscale="soft",
    video=[
        ("tone", {"contrast": 0.9, "lift": 0.08, "knee": 0.88}),
        ("balance", {"warmth": 0.15, "shadow_tint": "magenta", "shadow_amt": 0.15,
                     "high_tint": "yellow", "high_amt": 0.2}),
        ("saturation", {"amount": 1.4, "vibrance": 0.3}),
        ("optics", {"diffusion": 0.34, "soft_focus": 0.22, "veiling_flare": 0.28,
                    "bloom_mids": 0.35}),
        ("halation", {"strength": 0.4, "tint": "warm_white", "radius": 0.12,
                      "threshold": 0.66}),
        ("upload_gen", {"gens": 3, "deband_loss": 0.6, "qscale": 8}),
        ("codec_era", {"codec": "h264", "res": "240p", "kbps": 240, "crf": -1, "gop": 60}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 80.0, "high_hz": 6000.0}),
        ("a_room", {"mode": "room", "size": 2.0, "decay_s": 1.5, "mix": 0.3, "damp": 0.6,
                    "predelay_ms": 22.0}),
        ("a_codec_mp3", {"kbps": "24", "mono": True}),
    ],
    variants=[
        Variant("weirdcore-hard", "Weirdcore",
                "Pushed until the color separates and the quantizer gives up on the walls.",
                video={"saturation.amount": 1.7, "tone.contrast": 1.1,
                       "upload_gen.qscale": 14}),
        Variant("soft-nostalgia", "Soft Nostalgia",
                "One upload instead of three: still hazy, still wrong, but no longer eating itself.",
                video={"saturation.amount": 1.2, "upload_gen.gens": 1,
                       "upload_gen.deband_loss": 0.35}),
    ],
))


# nearest: golden-reverie-1978 and pastel-pop-2019; differs: 2020 digital-film cosplay
# with camera-side leaks and social crops rather than a real seventies negative.
register_preset(Preset(
    id="cottagecore-film-2020",
    name="Cottagecore Film",
    family="stylized",
    era="2020",
    desc="Sunday morning dressed as a period costume: a half-strength Vision-stock grade with cream highlights, a soft diffusion filter, and edge leaks from a camera that never held film.",
    tagline="Warm 35 mm cosplay, golden haze, soft leaks",
    tags=("2020s", "35mm", "grade", "social", "lifestyle"),
    keywords=("cottagecore", "twenties", "warm", "golden", "soft", "pastoral", "meadow",
              "linen", "film-look", "gentle"),
    upscale="soft",
    video=[
        ("stock", {"profile": "vision_90s", "strength": 0.5}),
        ("tone", {"contrast": 1.0, "lift": 0.04, "knee": 0.7}),
        ("balance", {"warmth": 0.26, "high_tint": "cream", "high_amt": 0.32}),
        ("saturation", {"amount": 1.0, "vibrance": 0.12}),
        ("optics", {"diffusion": 0.24, "soft_focus": 0.1, "veiling_flare": 0.26,
                    "bloom_mids": 0.32}),
        ("grain", {"amount": 0.28, "size": 1.8, "chroma_grain": 0.12, "stock": "fine_35",
                   "layers": "color_neg", "roughness": 0.45}),
        ("halation", {"strength": 0.42, "tint": "warm_white", "radius": 0.09,
                      "threshold": 0.66}),
        ("light_leak", {"amount": 0.16, "hue": "warm", "frequency": 0.6, "constant": 0.07}),
        ("gate_weave", {"enabled": False, "amount": 1.1, "hz": 0.7, "rotation": 0.05,
                        "splice_bump": 0.0}),
        ("codec_era", {"enabled": False, "codec": "h264", "kbps": 2000, "crf": -1,
                       "gop": 60}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_compressor", {"threshold_db": -22.0, "ratio": 2.0, "attack_ms": 12.0,
                          "release_ms": 300.0}),
        ("a_channel_aging", {"width": 1.2, "crosstalk_db": -46.0}),
        ("a_room", {"mode": "room", "size": 1.8, "decay_s": 0.7, "mix": 0.12, "damp": 0.6}),
    ],
    variants=[
        Variant("super-8-cosplay", "Super 8 Cosplay",
                "The same grade with the gauge faked all the way down: coarse reversal grain, an unsteady gate, a boxier frame.",
                video={"grain.amount": 0.45, "grain.size": 2.4, "grain.stock": "super8",
                       "grain.layers": "reversal", "gate_weave.enabled": True,
                       "light_leak.amount": 0.22, "framing.aspect": "source"},
                audio={"a_channel_aging.width": 0.6}),
        Variant("instagram-square", "Square Upload",
                "Cropped to a square and squeezed through a two-megabit upload before anybody sees it.",
                video={"framing.aspect": "source", "codec_era.enabled": True},
                audio={"a_compressor.ratio": 3.0}),
    ],
))


# nearest: moody-crush-2016 and nordic-noir-2011; differs: warm amber/brown crush with a
# dust-veiled lens and a stone chamber on the mix, not a cold single-color grade.
register_preset(Preset(
    id="dark-academia-2019",
    name="Dark Academia",
    family="stylized",
    era="2019",
    desc="Library light in October: exposure pulled down a sixth of a stop, brown packed into the shadows, saturation rationed, and a veiling haze of dust across a scope frame.",
    tagline="Desaturated amber, brown shadows, dust haze",
    tags=("10s", "35mm", "grade", "literary", "scope"),
    keywords=("dark-academia", "tens", "amber", "brown", "desaturated", "library",
              "tweed", "moody", "candle", "autumn"),
    upscale="soft",
    video=[
        ("tone", {"exposure": -0.11, "contrast": 1.15, "lift": 0.025, "knee": 0.85,
                  "pivot": 0.42}),
        ("balance", {"warmth": 0.18, "shadow_tint": "brown", "shadow_amt": 0.35,
                     "high_tint": "yellow", "high_amt": 0.15}),
        ("saturation", {"amount": 0.75, "vibrance": 0.08}),
        ("optics", {"veiling_flare": 0.2, "diffusion": 0.1, "bloom_mids": 0.25}),
        ("grain", {"amount": 0.3, "size": 1.7, "chroma_grain": 0.1, "stock": "fine_35",
                   "layers": "color_neg", "shadow_boost": 0.3}),
        ("halation", {"strength": 0.3, "tint": "orange", "radius": 0.07,
                      "threshold": 0.74}),
        ("vignette", {"amount": 0.3, "softness": 0.72, "radius": 0.88}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_compressor", {"threshold_db": -22.0, "ratio": 2.0, "attack_ms": 15.0,
                          "release_ms": 320.0}),
        ("a_channel_aging", {"width": 1.15, "crosstalk_db": -48.0}),
        ("a_room", {"mode": "chamber", "size": 1.6, "decay_s": 1.0, "mix": 0.15,
                    "damp": 0.5}),
    ],
    variants=[
        Variant("candlelight", "Candlelight",
                "The reading-lamp cut: another sixth of a stop down and the amber let all the way in.",
                video={"tone.exposure": -0.3, "balance.warmth": 0.28,
                       "halation.strength": 0.45}),
        Variant("overcast-quad", "Overcast Quad",
                "Outside instead of inside: the warmth mostly gone, the blacks lifted by weather.",
                video={"balance.warmth": 0.08, "balance.shadow_amt": 0.2,
                       "saturation.amount": 0.7, "tone.lift": 0.03}),
    ],
))


# nearest: vaporwave-vhs-1986 and cartoon-anime-fansub-1992; differs: gentle warm
# illustration flattening on a soft SP tape with a twelve-bit sampler doing the sound.
register_preset(Preset(
    id="lofi-study-loop-2018",
    name="Lo-Fi Study Loop",
    family="stylized",
    era="2018",
    desc="The girl studying at the window, on loop: flattened toward illustration and warmed to cream, a soft SP tape and CRT bloom under it, and a twelve-bit sampler doing the rain.",
    tagline="Warm anime VHS loop, tape hiss, 12-bit beat",
    tags=("10s", "vhs", "crt", "anime", "music"),
    keywords=("lofi", "lo-fi", "study", "beats", "tens", "anime-loop", "vhs-warm",
              "hiss", "rain", "chill"),
    proc_height=540,
    upscale="soft",
    video=[
        ("tone", {"contrast": 0.95, "lift": 0.05, "knee": 0.85}),
        ("balance", {"warmth": 0.15, "shadow_tint": "magenta", "shadow_amt": 0.15,
                     "high_tint": "cream", "high_amt": 0.15}),
        ("saturation", {"amount": 0.9, "vibrance": 0.05}),
        ("cel_flatten", {"smooth": 0.3, "levels": 14, "flatness": 0.3, "sat_snap": 0.15,
                         "protect_gradients": True}),
        ("optics", {"diffusion": 0.15, "soft_focus": 0.1, "bloom_mids": 0.28}),
        ("vhs", {"mode": "sp", "luma_noise": 0.18, "chroma_noise": 0.2, "dropouts": 0.3,
                 "sharpen": 0.2, "head_switch": 0.25, "time_base_error": 0.2,
                 "chroma_delay": 1.4}),
        ("interlace", {"combing": 0.3, "twitter": 0.2}),
        ("crt", {"bloom": 0.25, "scan_strength": 0.1, "glass_glow": 0.12,
                 "curvature": 0.02}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 40.0, "high_hz": 11000.0}),
        ("a_bitcrush", {"bits": 12, "sr_hz": 26000.0, "antialias": False, "mix": 1.0}),
        ("a_tape_sat", {"drive": 3.0, "bump_db": 4.0, "hf_loss": 0.5}),
        ("a_wow_flutter", {"wow_depth": 6.0, "flutter_depth": 3.0}),
        ("a_tape_hiss", {"level_db": -42.0, "type": "cassette"}),
        ("a_channel_aging", {"width": 1.1, "crosstalk_db": -44.0}),
    ],
    variants=[
        Variant("rainy-night", "Rainy Night",
                "The two-in-the-morning version of the same loop: darker, hazier, further from the lamp.",
                video={"tone.exposure": -0.2, "balance.shadow_amt": 0.25,
                       "optics.diffusion": 0.25}),
        Variant("clean-loop", "Clean Loop",
                "Straight off the render, before the tape and the tube: the illustration and nothing else.",
                video={"vhs.enabled": False, "crt.enabled": False},
                audio={"a_tape_hiss.level_db": -52.0, "a_wow_flutter.wow_depth": 2.0}),
    ],
))


# nearest: super8-1974 and cottagecore-film-2020; differs: blown-out pink washed reversal
# with sprocket-side leaks and a two-generation cassette dub, not a clean warm grade.
register_preset(Preset(
    id="chillwave-super8-2010",
    name="Chillwave Summer",
    family="stylized",
    era="2010",
    desc="A summer that only exists on a cassette J-card: washed reversal Super 8 blown out at the sun, pink leaks crossing the gate, projector weave and flicker over a twice-dubbed track.",
    tagline="Washed Super 8, pink leaks, blown sun",
    tags=("10s", "8mm", "reversal", "music", "grade"),
    keywords=("chillwave", "glo-fi", "tens", "super-8", "washed", "pink", "leaks",
              "summer", "beach", "hazy"),
    proc_height=520,
    upscale="soft",
    video=[
        ("tone", {"exposure": 0.12, "contrast": 1.0, "lift": 0.06, "knee": 0.78}),
        ("balance", {"warmth": 0.2, "shadow_tint": "magenta", "shadow_amt": 0.22,
                     "high_tint": "pink", "high_amt": 0.38}),
        ("saturation", {"amount": 0.88, "vibrance": 0.05}),
        ("optics", {"soft_focus": 0.07, "corner_softness": 0.3, "focus_drift": 0.12,
                    "veiling_flare": 0.18, "bloom_mids": 0.3}),
        ("grain", {"amount": 0.36, "size": 2.0, "chroma_grain": 0.15, "stock": "super8",
                   "layers": "reversal", "roughness": 0.55}),
        ("halation", {"strength": 0.35, "tint": "warm_white", "radius": 0.09,
                      "threshold": 0.66}),
        ("light_leak", {"amount": 0.3, "hue": "warm", "frequency": 2.0, "constant": 0.15,
                        "sprocket_side": 0.3}),
        ("gate_weave", {"amount": 1.2, "hz": 0.8, "rotation": 0.06, "splice_bump": 1.0}),
        ("flicker", {"amount": 0.15, "character": "projector", "color_flicker": 0.1,
                     "spatial": 0.2}),
        ("vhs", {"enabled": False, "mode": "sp", "luma_noise": 0.22, "chroma_noise": 0.22,
                 "dropouts": 1.0, "sharpen": 0.35, "head_switch": 0.4,
                 "time_base_error": 0.3}),
        ("interlace", {"enabled": False, "combing": 0.4, "twitter": 0.25}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 60.0, "high_hz": 9000.0}),
        ("a_tape_sat", {"drive": 2.5, "bump_db": 3.0, "hf_loss": 0.45}),
        ("a_analog_dub", {"format": "cassette", "generations": 2, "alignment": 0.4,
                          "compression": 0.35, "hiss_db": -46.0}),
        ("a_wow_flutter", {"wow_depth": 10.0, "flutter_depth": 5.0, "drift_long": 0.4}),
        ("a_channel_aging", {"width": 1.1, "crosstalk_db": -40.0}),
    ],
    variants=[
        Variant("vhs-rip-of-it", "Tape Rip",
                "Somebody pointed a camcorder at the projection and the tape signature lands on top of the film one.",
                video={"vhs.enabled": True, "interlace.enabled": True},
                audio={"a_analog_dub.generations": 3}),
        Variant("night-glow", "Night Glow",
                "The last reel after sundown: exposure back down, leaks and halation carrying the light.",
                video={"tone.exposure": -0.1, "light_leak.amount": 0.4,
                       "halation.strength": 0.5}),
    ],
))


# nearest: moody-crush-2016 and dark-academia-2019; differs: blue-black crush under a
# heavy synthetic grain and a hard vignette rather than warm amber or clean vinyl blacks.
register_preset(Preset(
    id="tumblr-grainy-2011",
    name="Tumblr Grainy",
    family="stylized",
    era="2011",
    desc="Reblogged at two in the morning: exposure a fifth of a stop down, blue sunk into the blacks, a heavy synthetic grain laid over everything and the corners pulled shut.",
    tagline="Blue-black crush, heavy grain, hard vignette",
    tags=("10s", "web", "grade", "photo", "night"),
    keywords=("tumblr", "tens", "grainy", "dark", "blue", "crushed", "sad", "indie",
              "soft-grunge", "nighttime"),
    upscale="sharp",
    video=[
        ("tone", {"exposure": -0.22, "contrast": 1.24, "lift": -0.02, "knee": 0.88,
                  "pivot": 0.4}),
        ("balance", {"warmth": -0.18, "shadow_tint": "blue", "shadow_amt": 0.42}),
        ("saturation", {"amount": 0.7, "vibrance": 0.05}),
        ("mono", {"enabled": False, "amount": 1.0, "response": "modern",
                  "tint": "silver", "tint_amt": 0.1}),
        ("optics", {"soft_focus": 0.05, "bloom_mids": 0.22}),
        ("grain", {"amount": 0.36, "size": 2.1, "chroma_grain": 0.04,
                   "roughness": 0.65, "stock": "push_process", "layers": "mono",
                   "shadow_boost": 0.35}),
        ("fade", {"enabled": False, "amount": 0.2, "profile": "neutral",
                  "bloom_whites": 0.15}),
        ("vignette", {"amount": 0.4, "softness": 0.6, "radius": 0.82}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 40.0, "high_hz": 12000.0}),
        ("a_tape_hiss", {"level_db": -46.0, "type": "cassette"}),
        ("a_channel_aging", {"width": 1.0, "crosstalk_db": -50.0}),
        ("a_compressor", {"threshold_db": -22.0, "ratio": 2.5, "attack_ms": 10.0,
                          "release_ms": 250.0}),
    ],
    variants=[
        Variant("black-and-white-mode", "Monochrome Reblog",
                "The same post desaturated all the way: silver-toned, and the grain stops being color.",
                video={"mono.enabled": True, "grain.chroma_grain": 0.0,
                       "vignette.amount": 0.45}),
        Variant("polaroid-scan", "Polaroid Scan",
                "Squared off and faded like an instant print that lived in a wallet.",
                video={"fade.enabled": True, "framing.aspect": "source",
                       "balance.warmth": 0.1, "tone.exposure": -0.1}),
    ],
))


# nearest: auth-square-social-filter-2013 and pastel-pop-2019; differs: matte green-shadow
# film emulation sitting on top of visible phone sharpening rather than a warm square fade.
register_preset(Preset(
    id="vsco-faded-film-2016",
    name="Faded Film App",
    family="stylized",
    era="2016",
    desc="The preset everybody used in 2016: blacks lifted off the floor, a green cast in the shadows, a matte fade over the highlights, and the phone's own sharpening still visible underneath.",
    tagline="Lifted blacks, muted green, sharp phone",
    tags=("10s", "smartphone", "grade", "social", "filter"),
    keywords=("vsco", "tens", "faded", "lifted-blacks", "muted", "film-emulation",
              "app-filter", "phone", "preset", "matte"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 0.95, "lift": 0.1, "knee": 0.75}),
        ("balance", {"warmth": 0.1, "shadow_tint": "green", "shadow_amt": 0.12,
                     "high_tint": "cream", "high_amt": 0.15}),
        ("saturation", {"amount": 0.85, "vibrance": 0.05}),
        ("sharpen", {"amount": 0.25, "radius": 0.9}),
        ("grain", {"amount": 0.2, "size": 1.0, "chroma_grain": 0.05, "stock": "fine_35",
                   "layers": "color_neg"}),
        ("fade", {"amount": 0.15, "profile": "neutral", "bloom_whites": 0.1}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_compressor", {"threshold_db": -20.0, "ratio": 2.0, "attack_ms": 10.0,
                          "release_ms": 220.0}),
        ("a_codec_aac", {"kbps": 128, "mono": False}),
    ],
    variants=[
        Variant("a6-preset", "Warm Slot",
                "The warm slot in the pack: more amber in the mids, a little of the color handed back.",
                video={"balance.warmth": 0.2, "saturation.amount": 0.9,
                       "fade.amount": 0.12}),
        Variant("hb2-preset", "Cool Slot",
                "The cool slot: blue in the shadows instead of green, and the saturation cut further.",
                video={"balance.warmth": -0.05, "balance.shadow_tint": "blue",
                       "balance.shadow_amt": 0.15, "saturation.amount": 0.8}),
    ],
))


# nearest: cross-process-1996 and vsco-faded-film-2016; differs: square app crop with a
# plastic-lens vignette and red edge leaks, not a lab cross-process or a matte fade.
register_preset(Preset(
    id="hipstamatic-toy-2010",
    name="Toy-Camera App",
    family="stylized",
    era="2010",
    desc="A plastic lens written in software: a square crop with the corners gone soft and dark, cross-processed reds against teal shadows, one red leak down an edge and 64 kbps of phone microphone.",
    tagline="Square crop, hard vignette, plastic lens",
    tags=("10s", "smartphone", "grade", "photo", "social"),
    keywords=("hipstamatic", "toy-camera", "tens", "square", "vignette", "cross-process",
              "plastic-lens", "lomo", "holga", "app"),
    upscale="soft",
    video=[
        ("tone", {"contrast": 1.25, "lift": 0.02, "knee": 0.8}),
        ("balance", {"warmth": 0.15, "shadow_tint": "teal", "shadow_amt": 0.2,
                     "high_tint": "yellow", "high_amt": 0.2}),
        ("saturation", {"amount": 1.3, "vibrance": 0.2, "hue": -5.0}),
        ("optics", {"soft_focus": 0.25, "corner_softness": 0.4, "distortion": 0.05,
                    "bloom_mids": 0.3}),
        ("light_leak", {"amount": 0.15, "hue": "red", "frequency": 1.0, "constant": 0.08}),
        ("fade", {"amount": 0.05, "profile": "neutral", "bloom_whites": 0.1}),
        ("vignette", {"amount": 0.6, "radius": 0.7, "softness": 0.6}),
        ("framing", {"aspect": "source", "mode": "box", "matte_gray": 0.05}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 100.0, "high_hz": 9000.0}),
        ("a_codec_aac", {"kbps": 64, "mono": True}),
    ],
    variants=[
        Variant("john-s-lens", "Contrast Lens",
                "The high-contrast lens in the pack: colder shadows, less color, more bite.",
                video={"tone.contrast": 1.4, "saturation.amount": 1.1,
                       "balance.shadow_tint": "blue", "balance.shadow_amt": 0.3}),
        Variant("kodot-film", "Hot Film Pack",
                "The warm film in the pack, wound tighter: more amber, more chroma, a deeper hole in the corners.",
                video={"balance.warmth": 0.3, "saturation.amount": 1.5,
                       "vignette.amount": 0.7}),
    ],
))


# nearest: myspace-2006 and deep-fried-meme-2018; differs: flash blowout with a two-way
# white-balance error through five upload generations to 240p, short of the fryer.
register_preset(Preset(
    id="cursed-image-2017",
    name="Cursed Image",
    family="stylized",
    era="2017",
    desc="Somebody's flash photograph of a room, saved from a screenshot of a repost: white balance wrong in two directions, five JPEG generations of banding, sharpened at every stop and finally 240p.",
    tagline="Flash blowout, wrong white, five re-ups",
    tags=("10s", "web", "240p", "grade", "phone"),
    keywords=("cursed", "meme", "tens", "jpeg", "flash", "re-upload",
              "wrong-white-balance", "uncanny", "low-res", "deep-fried-lite"),
    upscale="sharp",
    video=[
        ("tone", {"exposure": 0.32, "contrast": 1.2, "lift": 0.02, "knee": 0.62}),
        ("balance", {"warmth": -0.3, "tint": 0.38}),
        ("saturation", {"amount": 1.12, "vibrance": 0.1}),
        ("optics", {"corner_softness": 0.2, "bloom_mids": 0.3}),
        ("vignette", {"amount": 0.42, "radius": 0.9, "softness": 0.5,
                      "hot_center": 0.55}),
        ("upload_gen", {"gens": 5, "deband_loss": 0.85, "qscale": 13}),
        ("sharpen", {"amount": 0.4, "radius": 1.2}),
        ("codec_era", {"codec": "h264", "res": "240p", "kbps": 250, "crf": -1, "gop": 60}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_bitcrush", {"bits": 8, "sr_hz": 11025.0, "mix": 1.0}),
        ("a_codec_mp3", {"kbps": "16", "mono": True}),
        ("a_speaker", {"device": "cellphone_2008", "strength": 0.8}),
    ],
    variants=[
        Variant("mildly-cursed", "Mildly Cursed",
                "Two uploads instead of five and enough resolution left to tell what the room is.",
                video={"upload_gen.gens": 2, "upload_gen.qscale": 6,
                       "codec_era.res": "480p", "codec_era.kbps": 700}),
        Variant("nightmare", "Nightmare Repost",
                "The version that has been through every group chat: the green cast doubles and the banding wins.",
                video={"upload_gen.qscale": 18, "balance.tint": 0.4,
                       "sharpen.amount": 0.6}),
    ],
))


# nearest: cursed-image-2017 and datamosh; differs: saturation, sharpening and
# clipping deliberately past taste through MJPEG rather than block-drag corruption.
register_preset(Preset(
    id="deep-fried-meme-2018",
    name="Deep-Fried Meme",
    family="stylized",
    era="2018",
    desc="Run through the fryer: saturation past the rails, unsharp halos on every edge, five generations of JPEG into a quarter-scale MJPEG, and eight kbps of mono clipped into a phone speaker.",
    tagline="Saturation nuked, sharpen halos, earrape",
    tags=("10s", "web", "240p", "mjpeg", "humor"),
    keywords=("deep-fried", "meme", "tens", "saturation", "sharpen", "jpeg", "earrape",
              "red", "crunchy", "ironic"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.5, "gamma": 0.85, "knee": 0.95, "pivot": 0.45}),
        ("balance", {"warmth": 0.3, "tint": 0.2}),
        ("saturation", {"amount": 2.4, "vibrance": 0.5, "hue": 5.0}),
        ("sharpen", {"amount": 2.0, "radius": 1.5}),
        ("upload_gen", {"gens": 5, "deband_loss": 1.0, "qscale": 20}),
        ("codec_era", {"codec": "mjpeg", "qscale": 25, "res": "240p"}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_distortion", {"type": "hard", "drive": 12.0, "tone": 0.5}),
        ("a_bitcrush", {"bits": 6, "sr_hz": 8000.0, "mix": 1.0}),
        ("a_codec_mp3", {"kbps": "8", "mono": True}),
        ("a_speaker", {"device": "cellphone_2008", "strength": 1.0}),
    ],
    variants=[
        Variant("lightly-fried", "Lightly Fried",
                "One pass through the oil: loud, but the picture underneath still survives it.",
                video={"saturation.amount": 1.6, "sharpen.amount": 0.8,
                       "upload_gen.qscale": 8, "tone.contrast": 1.25},
                audio={"a_distortion.drive": 4.0, "a_bitcrush.bits": 10}),
        Variant("nuclear", "Nuclear",
                "The bottom of the thread: chroma welded shut, quantizer at the stop, audio down to four kilohertz.",
                video={"saturation.amount": 2.5, "tone.contrast": 2.0,
                       "codec_era.qscale": 31},
                audio={"a_bitcrush.sr_hz": 4000.0, "a_bitcrush.bits": 4}),
    ],
))


# nearest: datamosh and deep-fried-meme-2018; differs: candy-pink saturation on a
# clean vertical phone frame with brief mosh bursts and a stuttered AAC bounce.
register_preset(Preset(
    id="hyperpop-glitch-2020",
    name="Hyperpop Glitch",
    family="stylized",
    era="2020",
    desc="Candy-plastic saturation on a vertical crop, an MPEG-4 carrier damaged into dragging blocks and sheared slices, a flat-panel pixel grid under all of it and the bounce stuttered twelve times a second.",
    tagline="Candy saturation, datamosh, stutter",
    tags=("2020s", "vertical", "lcd", "music", "grade"),
    keywords=("hyperpop", "twenties", "candy", "saturated", "glitch", "digital",
              "datamosh", "pink", "plastic", "maximal"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.2, "lift": 0.02, "knee": 0.85}),
        ("balance", {"warmth": 0.05, "shadow_tint": "magenta", "shadow_amt": 0.26,
                     "high_tint": "pink", "high_amt": 0.4}),
        ("saturation", {"amount": 1.62, "vibrance": 0.45}),
        ("sharpen", {"amount": 0.4, "radius": 1.0}),
        ("codec_glitch", {"codec": "mpeg4", "amount": 0.3, "drop_p": 0.08,
                          "keyframes": True, "kbps": 3000, "gop": 60,
                          "slice_shift": 0.18}),
        ("lcd_screen", {"grid": 0.18, "scale": 3, "subpixel": "none",
                        "response_smear": 0.28, "backlight_bleed": 0.18,
                        "viewing_angle": 0.12, "moire_cam": 0.0}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_bitcrush", {"bits": 10, "sr_hz": 32000.0, "mix": 1.0}),
        ("a_distortion", {"type": "soft", "drive": 3.0, "tone": 0.4}),
        ("a_compressor", {"threshold_db": -22.0, "ratio": 6.0, "attack_ms": 3.0,
                          "release_ms": 120.0, "makeup_db": 4.0}),
        ("a_digital_glitch", {"stutter_rate": 12.0, "mute_rate": 0.0,
                              "crackle_rate": 6.0}),
        ("a_codec_aac", {"kbps": 96, "mono": False}),
    ],
    variants=[
        Variant("clean-candy", "Clean Candy",
                "The colorway with none of the damage: the same plastic pink, delivered intact.",
                video={"codec_glitch.enabled": False},
                audio={"a_digital_glitch.stutter_rate": 0.0,
                       "a_digital_glitch.crackle_rate": 0.0}),
        Variant("melted", "Melted",
                "Keyframes left unprotected, so motion drags stale imagery and the vocal stutters flat out.",
                video={"codec_glitch.amount": 0.65, "codec_glitch.drop_p": 0.2,
                       "codec_glitch.keyframes": False},
                audio={"a_digital_glitch.stutter_rate": 30.0}),
    ],
))
