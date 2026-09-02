"""Digital-family presets, third wave: DV and digital cinema cameras, and computer graphics eras.

Two shelves in one module: what people shot on between the DV revolution and the
first cheap raw cameras, and what a home computer or PC put on a screen before
anything was recorded at all.
"""

from ..engine.presets import Preset, Variant, register_preset


# nearest: minidv-2000 (interlaced handycam), auth-dslr-indie-naturalism-2012;
# differs: 2003 prosumer 24p with a cine-gamma shoulder, anamorphic 16:9 and a real progressive cadence.
register_preset(Preset(
    id="indie-dv-24p-2003",
    name="Indie DV 24p",
    family="digital",
    era="2003",
    desc="The festival camera of its moment: 24p advanced pulldown on MiniDV, a cine-gamma curve rolling the highlights early, 4:1:1 chroma stepping across skin, and a shotgun mic on a boom two feet out of frame.",
    tagline="DVX 24p cadence, film-mode gamma, 4:1:1",
    tags=("00s", "dv", "24p", "indie"),
    keywords=("dvx100", "aughts", "film-mode", "cine-gamma", "festival",
              "mumblecore", "prosumer", "no-budget", "digital-video"),
    upscale="soft",
    video=[
        ("tone", {"contrast": 0.98, "lift": 0.045, "knee": 0.66}),
        ("saturation", {"amount": 0.9, "vibrance": -0.08}),
        ("optics", {"soft_focus": 0.05}),
        ("grain", {"amount": 0.2, "size": 1.0, "chroma_grain": 0.18,
                   "roughness": 0.9, "stock": "fine_35", "layers": "color_neg"}),
        ("cadence", {"pattern": "pulldown_judder", "field_blend": 0.2}),
        ("chroma_dv", {"ratio": "4:1:1", "edge_sharpen": 0.3, "dct_blocks": 0.1}),
        ("codec_era", {"enabled": False, "codec": "mpeg2video", "kbps": 3500,
                       "res": "480p", "gop": 30, "passes": 1}),
        ("framing", {"aspect": "16:9", "mode": "box"}),
    ],
    audio=[
        ("a_historical_mic", {"profile": "shotgun_1975", "amount": 0.5,
                              "self_noise_db": -60.0}),
        ("a_compressor", {"threshold_db": -20.0, "ratio": 2.5,
                          "attack_ms": 12.0, "release_ms": 240.0}),
        ("a_room", {"mode": "room", "size": 0.8, "decay_s": 0.3, "mix": 0.06}),
    ],
    variants=[
        Variant("standard-lens-4x3", "Standard Lens, 4:3",
                "The anamorphic adapter stayed in the bag, so the frame comes back square.",
                video={"framing.aspect": "4:3", "chroma_dv.edge_sharpen": 0.4}),
        Variant("dvd-festival-screener", "Festival Screener",
                "Burned to a DVD-R at three in the morning and mailed to twelve programmers.",
                video={"codec_era.enabled": True, "chroma_dv.dct_blocks": 0.16}),
    ],
))


# nearest: indie-dv-24p-2003 (progressive cine gamma), wedding-master-1991 (S-VHS pro-mist);
# differs: interlaced DV with frame-movie blend ghosting and an autofocus that never settles.
register_preset(Preset(
    id="prosumer-dv-xl1-1998",
    name="Prosumer DV Camera",
    family="digital",
    era="1998",
    desc="The interchangeable-lens DV body that every wedding and short film went through: interlaced fields, frame-movie mode blending motion into ghosts, autofocus hunting past the subject and back, and a hot electret on the handle.",
    tagline="Interlaced DV, frame-mode blur, AF hunt",
    tags=("90s", "dv", "camcorder", "wedding"),
    keywords=("xl1", "prosumer", "nineties", "interlaced", "frame-mode", "autofocus",
              "indie", "4-1-1", "event-video"),
    upscale="soft",
    video=[
        ("tone", {"contrast": 1.04, "knee": 0.86}),
        ("saturation", {"amount": 1.05}),
        ("exposure_auto", {"target": 0.43, "lag": 0.6, "overshoot": 0.2,
                           "max_boost": 2.5, "agc_gain_noise": 0.3, "wb_amount": 0.25}),
        ("optics", {"focus_drift": 0.1, "hunt_rate": 2.0, "soft_focus": 0.04}),
        ("chroma_dv", {"ratio": "4:1:1", "edge_sharpen": 0.55, "dct_blocks": 0.12}),
        ("deinterlace_artifact", {"mode": "blend_ghost", "amount": 0.35}),
        ("vhs", {"enabled": False, "mode": "sp", "luma_bw": 2.6, "chroma_bw": 0.35,
                 "chroma_delay": 2.0, "sharpen": 0.25, "luma_noise": 0.35,
                 "chroma_noise": 0.4, "head_switch": 0.7, "dropouts": 2.5,
                 "time_base_error": 0.28, "flagging": 0.2, "generation": 2}),
        ("interlace", {"combing": 0.4, "twitter": 0.28}),
        ("framing", {"aspect": "4:3", "mode": "box"}),
    ],
    audio=[
        ("a_historical_mic", {"profile": "electret_1985", "amount": 0.6,
                              "handling": 0.12, "self_noise_db": -56.0}),
        ("a_mono", {"amount": 0.3}),
        ("a_agc", {"target_db": -15.0, "max_gain_db": 12.0,
                   "attack_ms": 25.0, "release_ms": 700.0, "amount": 0.8}),
        ("a_speaker", {"device": "tv_mono_1985", "strength": 0.5}),
    ],
    variants=[
        Variant("manual-focus-tripod", "Manual Focus, Tripod",
                "Somebody read the manual: focus locked, gain pegged, the camera finally behaving.",
                video={"optics.hunt_rate": 0.0, "optics.focus_drift": 0.0,
                       "exposure_auto.agc_gain_noise": 0.15},
                audio={"a_agc.amount": 0.3}),
        Variant("vhs-client-copy", "VHS Client Copy",
                "The tape the couple actually watched, dubbed while the camera charged.",
                video={"vhs.enabled": True, "chroma_dv.edge_sharpen": 0.4},
                audio={"a_speaker.strength": 0.7}),
    ],
))


# nearest: hd-1080i-2008 (broadcast interlaced HD), genre-digital-night-thriller-2004;
# differs: 2001 progressive digital cinema with a hard video shoulder clipping cyan, no interlace at all.
register_preset(Preset(
    id="early-hdcam-2001",
    name="Early HDCAM 24p",
    family="digital",
    era="2001",
    desc="The first generation of 24p HD cinema cameras: a clean 1080 image with a hard video shoulder, highlights clipping toward cyan, chroma sampled thin enough to see on a red coat, and nothing resembling film grain anywhere.",
    tagline="Clean 1080 video shoulder, cyan clip",
    tags=("00s", "hdcam", "digital-cinema", "early-hd"),
    keywords=("f900", "aughts", "24p", "video-gamma", "cyan-clip", "crisp",
              "scifi", "prequel", "sony-hdw"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.14, "knee": 0.72}),
        ("balance", {"high_tint": "cyan", "high_amt": 0.2, "tint": -0.03}),
        ("saturation", {"amount": 0.98}),
        ("grain", {"amount": 0.12, "size": 1.0, "chroma_grain": 0.15,
                   "roughness": 1.0, "stock": "fine_35", "layers": "color_neg"}),
        ("halation", {"enabled": False, "strength": 0.2, "threshold": 0.78,
                      "radius": 0.05, "tint": "red_orange"}),
        ("chroma_dv", {"ratio": "4:2:0", "edge_sharpen": 0.35, "dct_blocks": 0.05}),
        ("sharpen", {"amount": 0.2, "radius": 0.9}),
        ("codec_era", {"enabled": False, "codec": "mpeg2video", "kbps": 5000,
                       "res": "480p", "gop": 15, "passes": 2}),
        ("framing", {"aspect": "16:9", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 20.0, "high_hz": 20000.0, "order": 4}),
        ("a_compressor", {"threshold_db": -18.0, "ratio": 2.2,
                          "attack_ms": 15.0, "release_ms": 280.0}),
    ],
    variants=[
        Variant("theatrical-film-out", "Theatrical Film-Out",
                "Recorded back to 35 mm for release, which finally gives the digital image some grain and glow.",
                video={"grain.amount": 0.32, "grain.size": 1.6,
                       "grain.stock": "print_dupe", "grain.layers": "print_from_neg",
                       "grain.roughness": 0.7, "halation.enabled": True,
                       "framing.aspect": "2.35", "framing.mode": "crop",
                       "sharpen.amount": 0.1}),
        Variant("dvd-2002", "DVD Transfer",
                "Downconverted and squeezed onto a disc, mosquito noise crawling around the titles.",
                video={"codec_era.enabled": True}),
    ],
))


# nearest: early-hdcam-2001 (video-shoulder HD), streaming-filmic-2021 (faux grain grade);
# differs: 4K raw with a magenta sensor bias and hard capture sharpening, no film cosplay at all.
register_preset(Preset(
    id="red-one-raw-2008",
    name="RED ONE 4K Raw",
    family="digital",
    era="2008",
    desc="The first cheap 4K raw camera on an indie feature: an ultra-clean image biased magenta out of the debayer, chroma sharp enough to cut, thin waxy skin, and the faintest sensor grain in the shadows.",
    tagline="Ultra-clean 4K, magenta bias, thin skin",
    tags=("00s", "red-one", "4k", "digital-cinema"),
    keywords=("aughts", "raw", "magenta", "sharp", "mysterium", "indie-feature",
              "early-red", "debayer", "drama"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.1, "knee": 0.84}),
        ("balance", {"warmth": -0.05, "tint": 0.13}),
        ("saturation", {"amount": 1.05}),
        ("grain", {"amount": 0.08, "size": 1.0, "chroma_grain": 0.1,
                   "roughness": 1.0, "stock": "fine_35", "layers": "color_neg"}),
        ("sharpen", {"amount": 0.3, "radius": 0.8}),
        ("codec_era", {"enabled": False, "codec": "h264", "kbps": 900, "crf": 26,
                       "res": "480p", "gop": 60, "passes": 1}),
        ("framing", {"aspect": "2.35", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 20.0, "high_hz": 20000.0, "order": 4}),
        ("a_compressor", {"threshold_db": -18.0, "ratio": 2.0,
                          "attack_ms": 15.0, "release_ms": 300.0}),
    ],
    variants=[
        Variant("film-emulation-lut", "Film Emulation LUT",
                "The colorist's rescue pass: magenta pulled out, warmth in, grain painted back on.",
                video={"balance.tint": 0.0, "balance.warmth": 0.05,
                       "grain.amount": 0.26, "grain.size": 1.4, "sharpen.amount": 0.15}),
        Variant("web-trailer", "Web Trailer Encode",
                "The teaser as anyone actually saw it in 2008: downscaled and handed to H.264.",
                video={"codec_era.enabled": True, "sharpen.amount": 0.4}),
    ],
))


# nearest: process-vision3-2010 (real film latitude), auth-dslr-indie-naturalism-2012 (H.264 DSLR);
# differs: digital neutrality with a soft shoulder and ultra-fine sensor grain, no codec mush.
register_preset(Preset(
    id="digital-cinema-alexa-2012",
    name="Digital Cinema Alexa",
    family="digital",
    era="2012",
    desc="The camera that made prestige drama look expensive: highlights rolling off for a stop and a half past white, skin neutral to the point of boredom, ultra-fine sensor grain, and a little lens halation on practicals.",
    tagline="Wide latitude, soft rolloff, neutral skin",
    tags=("10s", "alexa", "digital-cinema", "prestige"),
    keywords=("arri", "tens", "latitude", "soft-rolloff", "neutral", "log-c",
              "clean", "drama", "feature"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.05, "knee": 0.62, "lift": 0.008}),
        ("balance", {"warmth": 0.03}),
        ("saturation", {"amount": 1.0, "vibrance": 0.04}),
        ("optics", {"bloom_mids": 0.12}),
        ("vignette", {"amount": 0.12, "radius": 1.05, "softness": 0.65, "roundness": 1.0}),
        ("grain", {"amount": 0.14, "size": 1.0, "chroma_grain": 0.08,
                   "roughness": 0.95, "stock": "fine_35", "layers": "color_neg"}),
        ("halation", {"strength": 0.1, "threshold": 0.8, "radius": 0.045,
                      "tint": "warm_white"}),
        ("framing", {"aspect": "2.35", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 20.0, "high_hz": 20000.0, "order": 4}),
        ("a_compressor", {"threshold_db": -18.0, "ratio": 2.0,
                          "attack_ms": 20.0, "release_ms": 320.0}),
    ],
    variants=[
        Variant("tv-drama-16x9", "TV Drama 16:9",
                "The same body on a premium cable series, delivered flat to the broadcaster.",
                video={"framing.aspect": "16:9", "tone.contrast": 1.02,
                       "halation.strength": 0.06}),
        Variant("anamorphic-2x", "Anamorphic 2x",
                "Old scope glass on the front: oval vignette, a ghost off the aperture, flare for days.",
                video={"optics.aperture_ghost": 0.3, "optics.bloom_mids": 0.2,
                       "vignette.roundness": 0.6, "vignette.amount": 0.28,
                       "halation.strength": 0.2}),
    ],
))


# nearest: digital-cinema-alexa-2012 (clean latitude), red-one-raw-2008;
# differs: a Super 16 sized sensor with noisy shadows and fixed-pattern columns, and a cheap onboard mic.
register_preset(Preset(
    id="pocket-cinema-raw-2014",
    name="Pocket Cinema Camera",
    family="digital",
    era="2014",
    desc="A palm-sized raw camera with a Super 16 sensor: shadows full of chroma noise the moment you lift them, fixed-pattern columns down the dark side of the frame, decent latitude, and an onboard microphone hissing louder than the room.",
    tagline="Super 16 sensor noise, column pattern",
    tags=("10s", "blackmagic", "raw", "indie"),
    keywords=("pocket", "tens", "super16-sensor", "fixed-pattern", "1080p",
              "cinema-dng", "shadow-noise", "short-film", "drama"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.05, "knee": 0.68, "lift": 0.012}),
        ("saturation", {"amount": 1.0}),
        ("grain", {"amount": 0.22, "size": 0.9, "chroma_grain": 0.2,
                   "roughness": 1.0, "stock": "fine_35", "layers": "color_neg",
                   "shadow_boost": 0.85}),
        ("halation", {"strength": 0.1, "threshold": 0.8, "radius": 0.05,
                      "tint": "warm_white"}),
        ("telecine_scan", {"pin_stability": "pin_registered", "hop_px": 0.2,
                           "scanner_stripe": 0.15, "frame_edge_crop": 0.0}),
        ("framing", {"aspect": "16:9", "mode": "box"}),
    ],
    audio=[
        ("a_historical_mic", {"profile": "electret_1985", "amount": 0.5,
                              "self_noise_db": -50.0}),
        ("a_compressor", {"threshold_db": -20.0, "ratio": 2.5,
                          "attack_ms": 15.0, "release_ms": 260.0}),
    ],
    variants=[
        Variant("graded-clean", "Graded And Cleaned",
                "Noise reduction and a column fix in post, which is what the footage was always for.",
                video={"grain.amount": 0.12, "grain.shadow_boost": 0.35,
                       "telecine_scan.scanner_stripe": 0.05},
                audio={"a_historical_mic.enabled": False}),
        Variant("iso-1600-night", "ISO 1600 Night",
                "Pushed past where the sensor wants to go, and the shadows start crawling.",
                video={"grain.amount": 0.4, "grain.shadow_boost": 0.95,
                       "telecine_scan.scanner_stripe": 0.25, "tone.lift": 0.05}),
    ],
))


# nearest: auth-first-wave-action-camera-2014 (barrel warp, hard H.264), red-one-raw-2008;
# differs: aerial gimbal footage with in-camera sharpening halos, a real-estate grade and prop-shadow flicker.
register_preset(Preset(
    id="drone-aerial-2016",
    name="Consumer Drone Aerial",
    family="digital",
    era="2016",
    desc="Four kilos of plastic holding a wide lens above a field: in-camera sharpening ringing every roofline, saturated listing-photo color, 4K starved down to a bitrate it cannot hold, and the prop shadow flickering across the frame.",
    tagline="Sharpen halos, 4K H.264 mush, prop flicker",
    tags=("10s", "drone", "4k", "aerial"),
    keywords=("tens", "wide-lens", "sharpening", "h264", "real-estate",
              "landscape", "gimbal", "documentary", "travel"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.1, "knee": 0.85}),
        ("saturation", {"amount": 1.2, "vibrance": 0.2}),
        ("optics", {"distortion": 0.06, "corner_softness": 0.1}),
        ("flicker", {"amount": 0.08, "character": "slow_drift",
                     "color_flicker": 0.02, "spatial": 0.6}),
        ("sharpen", {"amount": 0.5, "radius": 1.2}),
        ("codec_era", {"codec": "h264", "kbps": 2800, "crf": -1,
                       "res": "native", "gop": 60, "passes": 1}),
        ("framing", {"aspect": "16:9", "mode": "box"}),
    ],
    audio=[
        ("a_codec_aac", {"kbps": 128, "mono": False}),
        ("a_bed", {"bed": "air_handler_hall", "level_db": -40.0,
                   "duck": 0.15, "loop_jitter": 0.3}),
    ],
    variants=[
        Variant("log-flat", "Flat Log Profile",
                "Shot for grading: sharpening off, saturation down, everything grey and useful.",
                video={"saturation.amount": 0.8, "saturation.vibrance": 0.0,
                       "sharpen.amount": 0.2, "tone.contrast": 0.95}),
        Variant("square-social-crop", "Square Social Crop",
                "Cropped to a square and pushed through the app's encoder for the feed.",
                video={"framing.aspect": "1:1", "codec_era.crf": 28,
                       "codec_era.res": "480p"},
                audio={"a_codec_aac.kbps": 64}),
    ],
))


# nearest: pixel-1990 (fat VGA pixels, ordered dither), auth-early-cgi-demo-reel-1988;
# differs: the four-color CGA palette at 200 lines and a one-bit PC speaker instead of a sound card.
register_preset(Preset(
    id="cga-pc-1984",
    name="CGA Four-Color PC",
    family="digital",
    era="1984",
    desc="An IBM PC putting 320 by 200 on a composite monitor: cyan, magenta, white and black, ordered dither standing in for everything else, tall pixels, and a one-bit speaker beeping through the case.",
    tagline="Cyan-magenta-white, 200-line dither, beep",
    tags=("80s", "cga", "ibm-pc", "dos"),
    keywords=("four-color", "cyan-magenta", "320x200", "dither", "pc-speaker",
              "composite-monitor", "eighties", "games", "adventure-game"),
    upscale="sharp",
    video=[
        ("mono", {"enabled": False, "amount": 1.0, "response": "modern",
                  "tint": "phosphor_green", "tint_amt": 0.85}),
        ("pixel_era", {"res_h": 200, "palette": "cga", "dither": "bayer4",
                       "contrast_snap": 0.5, "pixel_aspect": 1.2}),
        ("ntsc", {"enabled": False, "strength": 0.9, "luma_bw": 2.6, "chroma_bw": 0.6,
                  "rainbow": 0.8, "dot_crawl": 0.5, "phase_noise": 2.0}),
        ("crt", {"scan_strength": 0.25, "bloom": 0.3, "curvature": 0.05,
                 "glare": 0.15, "glare_pos": "tr"}),
        ("framing", {"aspect": "4:3", "mode": "box"}),
    ],
    audio=[
        ("a_bitcrush", {"bits": 3, "sr_hz": 6000.0, "antialias": False, "mix": 1.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_speaker", {"device": "pc_speaker_1992", "strength": 1.0}),
    ],
    variants=[
        Variant("composite-artifact-color", "Composite Artifact Color",
                "The same four registers on a composite TV, where the dither smears into extra colors.",
                video={"ntsc.enabled": True, "crt.bloom": 0.4}),
        Variant("monochrome-monitor", "Monochrome Monitor",
                "Plugged into the green screen instead, which is what most offices actually had.",
                video={"mono.enabled": True, "pixel_era.palette": "none",
                       "pixel_era.contrast_snap": 0.7}),
    ],
))


# nearest: cga-pc-1984 (four-color PC), pixel-1990 (VGA 256);
# differs: the C64 sixteen-color palette pushed through an RF modulator into a family television.
register_preset(Preset(
    id="c64-home-computer-1985",
    name="Home Computer",
    family="digital",
    era="1985",
    desc="A breadbin home computer wired into the family television through an RF modulator: sixteen muddy registers, dot crawl and rainbow across every sprite edge, TV-out blur softening the text, and the sound chip crunching under it.",
    tagline="16-color VIC palette, TV-out blur, SID",
    tags=("80s", "c64", "commodore", "home-computer"),
    keywords=("16-color", "tv-out", "sid", "loading", "cassette-loader",
              "bedroom", "eighties", "action-game", "arcade"),
    upscale="sharp",
    video=[
        ("pixel_era", {"res_h": 200, "palette": "c64", "dither": "bayer2",
                       "contrast_snap": 0.45, "pixel_aspect": 1.1}),
        ("ntsc", {"strength": 0.7, "luma_bw": 3.0, "chroma_bw": 0.6, "rainbow": 0.4,
                  "dot_crawl": 0.4, "phase_noise": 1.6}),
        ("crt", {"scan_strength": 0.2, "bloom": 0.35, "curvature": 0.05,
                 "misconvergence": 0.5}),
        ("framing", {"aspect": "4:3", "mode": "box"}),
    ],
    audio=[
        ("a_bitcrush", {"bits": 8, "sr_hz": 11025.0, "antialias": False, "mix": 1.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_tv_sound", {"hz": "60", "buzz_db": -50.0, "hum_db": -58.0, "comp": 0.4}),
        ("a_speaker", {"device": "tv_mono_1985", "strength": 0.8}),
    ],
    variants=[
        Variant("s-video-monitor", "Monitor Cable",
                "The dedicated monitor your friend's dad bought, with none of the RF mess.",
                video={"ntsc.enabled": False, "crt.scan_strength": 0.25,
                       "crt.misconvergence": 0.25}),
        Variant("pal-europe", "PAL Europe",
                "The same machine on a 50 Hz set, with more lines and steadier hue.",
                video={"ntsc.system": "pal", "ntsc.luma_bw": 3.4, "ntsc.rainbow": 0.25},
                audio={"a_tv_sound.hz": "50"}),
    ],
))


# nearest: c64-home-computer-1985 (16 colors via RF), cga-pc-1984;
# differs: an eight-color attribute-clash palette with no dither at all, PAL RF and a one-bit beeper.
register_preset(Preset(
    id="zx-spectrum-1983",
    name="Rubber-Key Micro",
    family="digital",
    era="1983",
    desc="A rubber-keyed British micro on a portable PAL set: eight colors in bright and dark, attribute clash smearing whole character cells when sprites overlap, RF crawl over the border, and a beeper doing the music.",
    tagline="Attribute clash, 8 colors, tape shriek",
    tags=("80s", "zx-spectrum", "sinclair", "uk"),
    keywords=("micro", "attribute-clash", "8-color", "tape-loading", "bedroom-coder",
              "rubber-keys", "eighties", "arcade-adventure", "platform-game"),
    upscale="sharp",
    video=[
        ("pixel_era", {"res_h": 192, "palette": "zx_spectrum", "dither": "none",
                       "contrast_snap": 0.6, "pixel_aspect": 1.0}),
        ("ntsc", {"system": "pal", "strength": 0.7, "luma_bw": 3.0, "chroma_bw": 0.6,
                  "rainbow": 0.35, "dot_crawl": 0.3, "phase_noise": 1.2}),
        ("crt", {"scan_strength": 0.22, "bloom": 0.35, "curvature": 0.05,
                 "vignette_crt": 0.15}),
        ("framing", {"aspect": "4:3", "mode": "box"}),
    ],
    audio=[
        ("a_bitcrush", {"bits": 3, "sr_hz": 8000.0, "antialias": False, "mix": 1.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_tv_sound", {"hz": "50", "buzz_db": -50.0, "hum_db": -58.0, "comp": 0.4}),
        ("a_speaker", {"device": "tv_mono_1965", "strength": 0.9}),
    ],
    variants=[
        Variant("monitor-scart", "Direct Video",
                "Wired straight to the set's video input, so the colors stop crawling.",
                video={"ntsc.enabled": False, "crt.scan_strength": 0.26}),
        Variant("loading-screen", "Loading Screen",
                "Four minutes of stripes off a cassette while the beeper screams at you.",
                video={"crt.bloom": 0.5, "ntsc.rainbow": 0.6, "ntsc.strength": 0.85},
                audio={"a_bitcrush.bits": 4, "a_speaker.strength": 1.0}),
    ],
))


# nearest: cga-pc-1984 (four colors at 200 lines), pixel-1990;
# differs: sixteen colors over 350 crisp lines with a narrow-banded FM sound card instead of a beeper.
register_preset(Preset(
    id="ega-pc-adventure-1987",
    name="EGA PC Adventure",
    family="digital",
    era="1987",
    desc="A 1987 adventure game at 640 by 350 on an EGA monitor: sixteen colors with no smearing at all, tall crisp pixels, glass glare off the office lights, and a thin FM sound card doing the score.",
    tagline="Sixteen-color EGA, 350-line crisp, AdLib",
    tags=("80s", "ega", "pc", "dos"),
    keywords=("16-color", "adventure-game", "sierra", "640x350", "crisp", "adlib",
              "eighties", "games", "point-and-click"),
    upscale="sharp",
    video=[
        ("pixel_era", {"res_h": 350, "palette": "ega16", "dither": "bayer2",
                       "contrast_snap": 0.5, "pixel_aspect": 1.35}),
        ("ntsc", {"enabled": False, "strength": 0.7, "luma_bw": 3.0, "chroma_bw": 0.6,
                  "rainbow": 0.35, "dot_crawl": 0.35, "phase_noise": 1.5}),
        ("crt", {"scan_strength": 0.22, "bloom": 0.25, "curvature": 0.04,
                 "glare": 0.12, "glare_pos": "tl"}),
        ("framing", {"aspect": "4:3", "mode": "box"}),
    ],
    audio=[
        ("a_bitcrush", {"bits": 8, "sr_hz": 11025.0, "antialias": True, "mix": 1.0}),
        ("a_bandlimit", {"low_hz": 150.0, "high_hz": 8000.0, "order": 4}),
        ("a_mono", {"amount": 0.8}),
        ("a_speaker", {"device": "pc_speaker_1992", "strength": 0.6}),
    ],
    variants=[
        Variant("tandy-tv-out", "Tandy On A TV",
                "The same game on the machine in the den, wired into a television that hates it.",
                video={"ntsc.enabled": True, "crt.bloom": 0.35}),
        Variant("vga-upgrade-1990", "VGA Upgrade",
                "Three years and one expansion card later: 256 colors, half the vertical lines.",
                video={"pixel_era.palette": "vga256", "pixel_era.res_h": 200,
                       "pixel_era.pixel_aspect": 1.2, "pixel_era.dither": "bayer4"}),
    ],
))


# nearest: realplayer-1999 (postage-stamp blocks, freeze and snap), webvideo-2006 (FLV 240p);
# differs: 2001 MS-MPEG4 at 320 by 240 watched in a window on an early flat panel, with a swirly 32k stereo track.
register_preset(Preset(
    id="windows-media-stream-2001",
    name="Windows Media Stream",
    family="digital",
    era="2001",
    desc="A corporate webcast in a media player window: 320 by 240 of MS-MPEG4 smear, the buffer stalling and catching up, a flat panel's grid over the top, and a 32 kbps stereo track swirling like a bad phase effect.",
    tagline="WMV 320-line smear, buffering, 32k swirl",
    tags=("00s", "wmv", "streaming", "corporate"),
    keywords=("windows-media", "aughts", "buffering", "320x240", "swirl",
              "dial-up", "webcast", "intranet", "presentation"),
    upscale="soft",
    video=[
        ("tone", {"contrast": 1.03, "knee": 0.9}),
        ("codec_era", {"codec": "msmpeg4", "kbps": 220, "res": "240p",
                       "gop": 300, "passes": 1}),
        ("codec_glitch", {"enabled": False, "codec": "msmpeg4", "amount": 0.06,
                          "drop_p": 0.0, "freeze_p": 0.3, "kbps": 500, "gop": 120}),
        ("lcd_screen", {"grid": 0.08, "scale": 3, "response_smear": 0.3,
                        "backlight_bleed": 0.12, "viewing_angle": 0.1}),
        ("framing", {"aspect": "4:3", "mode": "box"}),
    ],
    audio=[
        ("a_codec_mp3", {"kbps": "32", "mono": False}),
        ("a_digital_glitch", {"stutter_rate": 3.0, "mute_rate": 4.0, "crackle_rate": 0.0}),
        ("a_speaker", {"device": "laptop_2006", "strength": 0.6}),
    ],
    variants=[
        Variant("broadband-2003", "Broadband 2003",
                "Two years and a DSL line later, the stream almost keeps up with the speaker.",
                video={"codec_era.kbps": 500, "codec_era.res": "360p"},
                audio={"a_codec_mp3.kbps": "64", "a_digital_glitch.mute_rate": 1.0}),
        Variant("dial-up-2001", "Dial-Up",
                "Twenty-eight kilobits of company town hall, freezing on every gesture.",
                video={"codec_era.kbps": 100, "codec_era.res": "144p",
                       "codec_glitch.enabled": True},
                audio={"a_codec_mp3.kbps": "16", "a_codec_mp3.mono": True,
                       "a_digital_glitch.mute_rate": 8.0}),
    ],
))
