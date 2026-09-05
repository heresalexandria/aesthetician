"""Social-family presets: the phone and platform era, 2010 to 2021.

Everything here is a phone sensor or a webcam, an H.264 re-encode owned by a
platform rather than a camera, and AAC. The frame shape is part of the format:
square for the early feed, 9:16 once the app stopped asking you to rotate.
"""

from ..engine.presets import Preset, Variant, register_preset


# nearest: auth-square-social-filter-2013 (lifted blacks, warm early-social fade), first-vertical-2013;
# differs: no filter grade at all, just a 480p square with hard phone auto-exposure and a starved AAC track.
register_preset(Preset(
    id="social-vine-loop-2013",
    name="Six-Second Loop",
    family="social",
    era="2013",
    desc="Six seconds shot square on a phone held sideways: the auto-exposure snapping a full stop every time the camera moves, 480 lines of H.264 at five hundred kilobits, and 64 kbps of mono AAC clipped to the loop point.",
    tagline="Square 480, phone AE snap, loop-ready AAC",
    tags=("10s", "vine", "square", "phone"),
    keywords=("loop", "tens", "six-second", "comedy", "short-form", "480p",
              "twitter", "sketch", "viral"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.05, "knee": 0.88}),
        ("balance", {"warmth": 0.0, "high_tint": "cream", "high_amt": 0.0}),
        ("saturation", {"amount": 1.08, "vibrance": 0.1}),
        ("exposure_auto", {"target": 0.44, "lag": 0.4, "overshoot": 0.2,
                           "max_boost": 3.0, "agc_gain_noise": 0.35,
                           "wb_amount": 0.2, "iris_step": 0.2}),
        ("fade", {"enabled": False, "amount": 0.2, "profile": "neutral",
                  "bloom_whites": 0.25}),
        ("chroma_dv", {"ratio": "4:2:0", "edge_sharpen": 0.3, "dct_blocks": 0.06}),
        ("sharpen", {"amount": 0.2, "radius": 0.9}),
        ("codec_era", {"codec": "h264", "kbps": 520, "crf": -1, "res": "480p",
                       "gop": 30, "passes": 1}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_historical_mic", {"profile": "electret_1985", "amount": 0.6,
                              "self_noise_db": -54.0}),
        ("a_agc", {"target_db": -14.0, "max_gain_db": 14.0,
                   "attack_ms": 25.0, "release_ms": 500.0, "amount": 0.9}),
        ("a_codec_aac", {"kbps": 64, "mono": True}),
        ("a_speaker", {"device": "cellphone_2008", "strength": 0.5}),
    ],
    variants=[
        Variant("reupload-twitter", "Cross-Posted",
                "Pulled off one app and pushed into another, which re-encodes it for the privilege.",
                video={"codec_era.passes": 2, "codec_era.kbps": 340},
                audio={"a_codec_aac.kbps": 48}),
        Variant("filtered-fade", "Filtered",
                "The in-app filter of the year: blacks lifted, whites gone cream, everything warmer.",
                video={"fade.enabled": True, "balance.warmth": 0.15,
                       "balance.high_amt": 0.18, "saturation.amount": 1.0}),
    ],
))


# nearest: first-vertical-2013 (pillarboxed tall frame, pumping exposure), social-vine-loop-2013;
# differs: a real 9:16 delivery rather than a pillarbox, heavier 480p crush, front-camera softness, 48k mono.
register_preset(Preset(
    id="social-snap-story-2015",
    name="Ephemeral Story",
    family="social",
    era="2015",
    desc="A story posted from the front camera and gone in a day: a soft plastic lens, exposure climbing four stops in a dim room, four hundred kilobits of vertical H.264 with a sixty-frame keyframe gap, and 48 kbps of mono AAC.",
    tagline="Vertical 480p, story crush, front-cam smear",
    tags=("10s", "snapchat", "vertical", "phone"),
    keywords=("story", "tens", "9-16", "front-camera", "ephemeral", "crushed",
              "480p", "selfie", "diary"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.06, "lift": 0.02, "knee": 0.88}),
        ("saturation", {"amount": 1.06}),
        ("exposure_auto", {"target": 0.45, "lag": 0.5, "overshoot": 0.25,
                           "max_boost": 4.0, "agc_gain_noise": 0.5, "wb_amount": 0.3}),
        ("optics", {"soft_focus": 0.15, "corner_softness": 0.15}),
        ("chroma_dv", {"ratio": "4:2:0", "edge_sharpen": 0.2, "dct_blocks": 0.08}),
        ("codec_era", {"codec": "h264", "kbps": 400, "crf": -1, "res": "480p",
                       "gop": 60, "passes": 1, "denoise_pre": 0.2}),
        ("lcd_screen", {"enabled": False, "grid": 0.1, "scale": 3,
                        "response_smear": 0.15, "moire_cam": 0.2,
                        "backlight_bleed": 0.12}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_historical_mic", {"profile": "electret_1985", "amount": 0.6,
                              "self_noise_db": -52.0}),
        ("a_agc", {"target_db": -14.0, "max_gain_db": 16.0,
                   "attack_ms": 20.0, "release_ms": 450.0, "amount": 1.0}),
        ("a_codec_aac", {"kbps": 48, "mono": True}),
        ("a_speaker", {"device": "cellphone_2008", "strength": 0.6}),
    ],
    variants=[
        Variant("rear-camera", "Rear Camera",
                "Flipped to the good lens, which the app rewards with twice the bitrate.",
                video={"optics.soft_focus": 0.02, "optics.corner_softness": 0.05,
                       "codec_era.kbps": 700}),
        Variant("screenshot-recording", "Screen-Recorded",
                "Saved by pointing another phone at the screen before it disappeared.",
                video={"lcd_screen.enabled": True, "codec_era.passes": 2,
                       "codec_era.kbps": 300}),
    ],
))


# nearest: social-snap-story-2015 (2015 crush), auth-square-social-filter-2013;
# differs: 2017 HDR tone-mapping warmth and platform sharpening at twice the bitrate, in stereo.
register_preset(Preset(
    id="social-stories-hd-2017",
    name="Vertical Stories",
    family="social",
    era="2017",
    desc="A vertical story from the year phones learned to tone-map: HDR pulling the shadows up and pushing yellow into the highlights, in-camera sharpening ringing every edge, and 96 kbps of stereo AAC over the room.",
    tagline="9:16 720p, warm phone HDR, boomerang AAC",
    tags=("10s", "instagram", "vertical", "smartphone"),
    keywords=("stories", "tens", "9-16", "720p", "hdr", "influencer", "boomerang",
              "lifestyle", "vlog"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.08, "lift": 0.02, "knee": 0.82}),
        ("balance", {"warmth": 0.1, "high_tint": "yellow", "high_amt": 0.08}),
        ("saturation", {"amount": 1.15, "vibrance": 0.2}),
        ("exposure_auto", {"target": 0.45, "lag": 0.3, "overshoot": 0.12,
                           "max_boost": 2.5, "agc_gain_noise": 0.25, "wb_amount": 0.15}),
        ("sharpen", {"amount": 0.35, "radius": 1.0}),
        ("codec_era", {"codec": "h264", "kbps": 1100, "crf": -1, "res": "native",
                       "gop": 60, "passes": 1}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_historical_mic", {"profile": "electret_1985", "amount": 0.4,
                              "self_noise_db": -58.0}),
        ("a_agc", {"target_db": -15.0, "max_gain_db": 12.0,
                   "attack_ms": 25.0, "release_ms": 600.0, "amount": 0.7}),
        ("a_codec_aac", {"kbps": 96, "mono": False}),
    ],
    variants=[
        Variant("reposted-3rd-time", "Reposted Three Times",
                "Screen-grabbed, cross-posted and reposted until the sharpening eats itself.",
                video={"codec_era.passes": 3, "codec_era.kbps": 700,
                       "sharpen.amount": 0.5}),
        Variant("night-mode", "Night Mode",
                "A dim bar at midnight, with the sensor gained past anything it can support.",
                video={"exposure_auto.max_boost": 5.0,
                       "exposure_auto.agc_gain_noise": 0.6, "tone.lift": 0.05}),
    ],
))


# nearest: social-stories-hd-2017 (warm HDR stories);
# differs: 1080 vertical with beauty smoothing under a much harder platform sharpen, and a loudness-war mix.
register_preset(Preset(
    id="social-short-video-2021",
    name="Vertical Short Video",
    family="social",
    era="2021",
    desc="A 1080 vertical clip through the app's own camera: skin smoothed flat by the beauty pass, the platform's sharpening put right back on top of it, color pushed past anything the sensor saw, and the audio bed limited to a wall.",
    tagline="9:16 1080, over-sharpened, beauty-smooth",
    tags=("20s", "tiktok", "vertical", "smartphone"),
    keywords=("reels", "shorts", "twenties", "9-16", "1080p", "sharpened",
              "beauty-filter", "viral", "dance", "lifestyle"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.1, "lift": 0.015, "knee": 0.84}),
        ("saturation", {"amount": 1.2, "vibrance": 0.25}),
        ("optics", {"soft_focus": 0.12, "bloom_mids": 0.2}),
        ("sharpen", {"amount": 0.5, "radius": 1.0}),
        ("codec_era", {"codec": "h264", "kbps": 2200, "crf": -1, "res": "native",
                       "gop": 60, "passes": 1}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_agc", {"target_db": -12.0, "max_gain_db": 10.0,
                   "attack_ms": 15.0, "release_ms": 400.0, "amount": 0.8}),
        ("a_compressor", {"threshold_db": -22.0, "ratio": 5.0, "attack_ms": 3.0,
                          "release_ms": 120.0, "makeup_db": 3.0}),
        ("a_codec_aac", {"kbps": 128, "mono": False}),
    ],
    variants=[
        Variant("duet-reupload", "Duet Reupload",
                "Recorded off somebody's repost of a repost: three encodes and no original left.",
                video={"codec_era.passes": 3, "codec_era.kbps": 1200,
                       "sharpen.amount": 0.65}),
        Variant("raw-camera-roll", "Straight From The Camera Roll",
                "The file before the app touched it: no smoothing, no sharpening, no limiter.",
                video={"codec_era.crf": 20, "sharpen.amount": 0.15,
                       "optics.soft_focus": 0.0, "saturation.amount": 1.05},
                audio={"a_compressor.ratio": 2.0, "a_compressor.makeup_db": 0.0}),
    ],
))


# nearest: webcam-stream-2012 (late webcam, pumping white balance, blocks), webcam-2004;
# differs: a 2020 conference call, so the picture freeze-holds on bandwidth drops and comes out of a laptop.
register_preset(Preset(
    id="social-video-call-2020",
    name="Video Call",
    family="social",
    era="2020",
    desc="A meeting held through a laptop camera: 360 lines at two hundred kilobits with a keyframe every eight seconds, the picture freezing and catching up whenever somebody else unmutes, and speech band-limited to seven kilohertz out of the laptop speaker.",
    tagline="360p bandwidth drop, freeze-hold, thin voice",
    tags=("20s", "video-call", "webcam", "meeting"),
    keywords=("zoom", "twenties", "360p", "freeze", "bandwidth", "lockdown",
              "laptop", "remote-work", "corporate"),
    upscale="soft",
    video=[
        ("tone", {"contrast": 1.04, "lift": 0.02, "knee": 0.9}),
        ("saturation", {"amount": 0.98}),
        ("exposure_auto", {"target": 0.45, "lag": 1.0, "overshoot": 0.2,
                           "max_boost": 3.0, "agc_gain_noise": 0.4, "wb_amount": 0.35}),
        ("optics", {"soft_focus": 0.1, "corner_softness": 0.1}),
        ("chroma_dv", {"ratio": "4:2:0", "edge_sharpen": 0.15, "dct_blocks": 0.1}),
        ("codec_era", {"codec": "h264", "kbps": 200, "crf": -1, "res": "360p",
                       "gop": 250, "passes": 1, "denoise_pre": 0.35}),
        ("codec_glitch", {"codec": "mpeg4", "amount": 0.04, "drop_p": 0.0,
                          "freeze_p": 0.22, "kbps": 900, "gop": 250}),
        ("lcd_screen", {"grid": 0.04, "scale": 3, "response_smear": 0.1,
                        "backlight_bleed": 0.1, "viewing_angle": 0.08}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 100.0, "high_hz": 7000.0, "order": 4}),
        ("a_codec_aac", {"kbps": 32, "mono": True}),
        ("a_digital_glitch", {"stutter_rate": 2.0, "mute_rate": 5.0, "crackle_rate": 0.0}),
        ("a_speaker", {"device": "laptop_2006", "strength": 0.7}),
    ],
    variants=[
        Variant("good-connection", "Good Connection",
                "Somebody finally plugged into the router and the call behaves for a whole hour.",
                video={"codec_era.kbps": 900, "codec_era.res": "480p",
                       "codec_era.denoise_pre": 0.1, "codec_glitch.freeze_p": 0.03},
                audio={"a_digital_glitch.mute_rate": 0.5, "a_codec_aac.kbps": 48}),
        Variant("phone-hotspot", "Phone Hotspot",
                "One bar in a parked car: 240 lines, and the audio drops out mid-sentence.",
                video={"codec_era.kbps": 70, "codec_era.res": "240p",
                       "codec_glitch.freeze_p": 0.4},
                audio={"a_digital_glitch.mute_rate": 12.0}),
    ],
))


# nearest: social-video-call-2020 (the call itself), auth-live-truck-local-news-2004;
# differs: the same call re-broadcast, so a station upscaler sharpens it, interlaces it and limits the audio.
register_preset(Preset(
    id="social-news-guest-2020",
    name="Remote News Guest",
    family="social",
    era="2020",
    desc="A pundit joining the panel from a spare room: a ring light veiling the lens, 360 lines of call video pushed through a station upscaler into a 1080i frame, and the broadcast limiter flattening seven kilohertz of laptop microphone.",
    tagline="Zoom guest in a broadcast frame, ring glare",
    tags=("20s", "news", "video-call", "broadcast"),
    keywords=("remote-guest", "twenties", "ring-light", "lockdown", "pundit",
              "bookshelf", "hybrid", "panel", "cable-news"),
    upscale="soft",
    video=[
        ("tone", {"contrast": 1.05, "lift": 0.025, "knee": 0.88}),
        ("saturation", {"amount": 1.02}),
        ("exposure_auto", {"target": 0.46, "lag": 0.8, "overshoot": 0.15,
                           "max_boost": 2.5, "agc_gain_noise": 0.35, "wb_amount": 0.25}),
        ("optics", {"veiling_flare": 0.15, "soft_focus": 0.06}),
        ("codec_era", {"codec": "h264", "kbps": 320, "crf": -1, "res": "360p",
                       "gop": 120, "passes": 1, "denoise_pre": 0.3}),
        ("codec_glitch", {"enabled": False, "codec": "mpeg4", "amount": 0.06,
                          "drop_p": 0.05, "freeze_p": 0.3, "kbps": 900, "gop": 120}),
        ("sharpen", {"amount": 0.3, "radius": 1.1}),
        ("interlace", {"combing": 0.3, "twitter": 0.2}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 100.0, "high_hz": 7000.0, "order": 4}),
        ("a_codec_aac", {"kbps": 32, "mono": True}),
        ("a_compressor", {"threshold_db": -20.0, "ratio": 4.0, "attack_ms": 5.0,
                          "release_ms": 180.0, "makeup_db": 2.0}),
        ("a_speaker", {"device": "tv_mono_1985", "strength": 0.5}),
    ],
    variants=[
        Variant("in-studio-guest", "In-Studio Guest",
                "The guest who could actually travel, on a proper camera down the hall.",
                video={"codec_era.enabled": False, "exposure_auto.agc_gain_noise": 0.1,
                       "optics.veiling_flare": 0.05},
                audio={"a_bandlimit.high_hz": 14000.0, "a_codec_aac.kbps": 96}),
        Variant("bad-connection-on-air", "Bad Connection On Air",
                "Live, and the guest's face is now four rectangles the anchor has to talk over.",
                video={"codec_era.kbps": 140, "codec_era.res": "240p",
                       "codec_glitch.enabled": True}),
    ],
))


# nearest: screen-recording-2009 (filmed off a monitor), social-video-call-2020;
# differs: a live x264 encode starving in motion, with a close condenser on the streamer's face-cam.
register_preset(Preset(
    id="social-twitch-stream-2016",
    name="Game Livestream",
    family="social",
    era="2016",
    desc="A game stream at 720p on a single starved megabit: the encoder holding up until something moves fast and then giving the whole frame away to blocks, a corner face-cam smearing, and a close condenser mic over the chair.",
    tagline="720p x264 starve, face-cam smear",
    tags=("10s", "twitch", "livestream", "gaming"),
    keywords=("tens", "face-cam", "720p", "x264", "bitrate", "streamer", "chat",
              "esports", "commentary"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.1, "knee": 0.88}),
        ("saturation", {"amount": 1.12, "vibrance": 0.08}),
        ("sharpen", {"amount": 0.28, "radius": 0.9}),
        ("codec_era", {"codec": "h264", "kbps": 1100, "crf": -1, "res": "native",
                       "gop": 120, "passes": 1}),
        ("lcd_screen", {"grid": 0.045, "scale": 3, "response_smear": 0.18,
                        "backlight_bleed": 0.14, "viewing_angle": 0.12}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_historical_mic", {"profile": "electret_1985", "amount": 0.5,
                              "proximity": 0.4, "self_noise_db": -60.0}),
        ("a_compressor", {"threshold_db": -20.0, "ratio": 4.0, "attack_ms": 6.0,
                          "release_ms": 180.0, "makeup_db": 2.0}),
        ("a_codec_aac", {"kbps": 160, "mono": False}),
        ("a_speaker", {"device": "laptop_2006", "strength": 0.4}),
    ],
    variants=[
        Variant("partner-1080p60", "Partner Bitrate",
                "Four megabits and a short keyframe interval: what the affiliate button pays for.",
                video={"codec_era.kbps": 4000, "codec_era.gop": 60,
                       "sharpen.amount": 0.15}),
        Variant("mobile-viewer-360p", "Watched On A Phone",
                "The transcode nobody chooses on purpose, on the bus, at 360 lines.",
                video={"codec_era.kbps": 300, "codec_era.res": "360p"},
                audio={"a_codec_aac.kbps": 64, "a_speaker.device": "cellphone_2008",
                       "a_speaker.strength": 0.6}),
    ],
))


# nearest: webvideo-2006 (240p Sorenson, 32k mono), auth-early-video-sharing-webcam-2006 (FLV webcam);
# differs: 2010 H.264 at 360 lines with the site's own upload sharpening and a tinny 96 kbps AAC track.
register_preset(Preset(
    id="social-youtube-360p-2010",
    name="YouTube 360p",
    family="social",
    era="2010",
    desc="An upload from the year the site quietly switched to H.264: 360 lines at three hundred kilobits, the ingest pipeline sharpening everything it just softened, a laptop panel over the top, and 96 kbps of thin stereo AAC.",
    tagline="360p H.264 mush, upload sharpen, tinny AAC",
    tags=("10s", "youtube", "upload", "web-video"),
    keywords=("tens", "360p", "h264", "mush", "viral", "embed", "buffering",
              "vlog", "commentary"),
    upscale="soft",
    video=[
        ("tone", {"contrast": 1.04, "knee": 0.9}),
        ("saturation", {"amount": 1.03}),
        ("codec_era", {"codec": "h264", "kbps": 300, "crf": -1, "res": "360p",
                       "gop": 60, "passes": 1, "denoise_pre": 0.2}),
        ("sharpen", {"amount": 0.38, "radius": 1.1}),
        ("lcd_screen", {"grid": 0.05, "scale": 3, "response_smear": 0.15,
                        "backlight_bleed": 0.1}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_codec_aac", {"kbps": 96, "mono": False}),
        ("a_speaker", {"device": "laptop_2006", "strength": 0.5}),
    ],
    variants=[
        Variant("480p-option", "480p Option",
                "The quality selector's other setting, for people with the patience to buffer.",
                video={"codec_era.res": "480p", "codec_era.kbps": 560},
                audio={"a_codec_aac.kbps": 128}),
        Variant("reupload-2013", "Reuploaded Three Years Later",
                "Ripped, re-encoded and posted again by a channel that did not make it.",
                video={"codec_era.passes": 3, "codec_era.kbps": 220,
                       "sharpen.amount": 0.55}),
    ],
))


# nearest: social-youtube-360p-2010 (the same site four years earlier), streaming-filmic-2021;
# differs: a 1080 delivery whose only damage is banding in gradients and a mild motion starve.
register_preset(Preset(
    id="social-youtube-1080p-2015",
    name="YouTube 1080p",
    family="social",
    era="2015",
    desc="A 1080 upload at the bitrate the site actually gives you: sharp enough in stills, banding creeping into every sky and wall as the transcode throws away the dither, and a clean 128 kbps AAC track.",
    tagline="1080 compression, banding skies, clean AAC",
    tags=("10s", "youtube", "upload", "1080p"),
    keywords=("tens", "compression", "banding", "gradient", "vlog", "clean",
              "hd", "channel", "commentary"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.03, "knee": 0.9}),
        ("saturation", {"amount": 1.05}),
        ("sharpen", {"amount": 0.15, "radius": 0.9}),
        ("upload_gen", {"gens": 2, "deband_loss": 0.8, "qscale": 5}),
        ("codec_era", {"codec": "h264", "kbps": 1600, "crf": -1, "res": "native",
                       "gop": 120, "passes": 1}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_codec_aac", {"kbps": 128, "mono": False}),
        ("a_speaker", {"device": "laptop_2006", "strength": 0.3}),
    ],
    variants=[
        Variant("4k-downscaled", "Uploaded In 4K",
                "The trick everybody learned: upload bigger than you deliver and keep more of the bitrate.",
                video={"codec_era.kbps": 4500, "upload_gen.deband_loss": 0.25,
                       "upload_gen.qscale": 2, "upload_gen.gens": 1}),
        Variant("mobile-data-480p", "On Mobile Data",
                "The player quietly drops to 480 lines and hopes nobody looks at the sky.",
                video={"codec_era.res": "480p", "codec_era.kbps": 420,
                       "upload_gen.deband_loss": 0.9},
                audio={"a_codec_aac.kbps": 64, "a_speaker.device": "cellphone_2008"}),
    ],
))


# nearest: webcam-2004 (MSN sensor smear, VoIP crackle), social-video-call-2020;
# differs: 2012 phone front camera at 640 by 480, warm white-balance pumping, heard through a phone speaker.
register_preset(Preset(
    id="social-facetime-2012",
    name="Front-Camera Video Call",
    family="social",
    era="2012",
    desc="A call to a relative on a phone held at arm's length: a 640 by 480 front sensor behind soft plastic, white balance swinging warm every time the arm moves, 240 kilobits of H.264, and the whole thing out of the earpiece speaker.",
    tagline="640x480 front cam, wb pump, soft lens",
    tags=("10s", "facetime", "video-call", "iphone"),
    keywords=("tens", "front-camera", "480p", "wb-pump", "soft-lens", "wifi",
              "family-call", "smartphone", "kitchen"),
    upscale="soft",
    video=[
        ("tone", {"contrast": 1.04, "lift": 0.025, "knee": 0.9}),
        ("saturation", {"amount": 1.02}),
        ("exposure_auto", {"target": 0.45, "lag": 0.6, "overshoot": 0.2,
                           "max_boost": 4.0, "agc_gain_noise": 0.55, "wb_amount": 0.45}),
        ("optics", {"soft_focus": 0.2, "corner_softness": 0.25}),
        ("chroma_dv", {"ratio": "4:2:0", "edge_sharpen": 0.2, "dct_blocks": 0.1}),
        ("codec_era", {"codec": "h264", "kbps": 240, "crf": -1, "res": "480p",
                       "gop": 60, "passes": 1, "denoise_pre": 0.25}),
        ("codec_glitch", {"enabled": False, "codec": "mpeg4", "amount": 0.08,
                          "drop_p": 0.06, "freeze_p": 0.25, "kbps": 900, "gop": 60}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 100.0, "high_hz": 8000.0, "order": 4}),
        ("a_codec_aac", {"kbps": 48, "mono": True}),
        ("a_speaker", {"device": "cellphone_2008", "strength": 0.7}),
    ],
    variants=[
        Variant("wifi-good", "Good Wi-Fi",
                "Both ends on home broadband, so the picture stops breathing quite so hard.",
                video={"codec_era.kbps": 520, "exposure_auto.agc_gain_noise": 0.3},
                audio={"a_codec_aac.kbps": 64}),
        Variant("3g-call", "On 3G",
                "Placed from a train platform, where the call is mostly a slideshow.",
                video={"codec_era.kbps": 80, "codec_era.res": "240p",
                       "codec_glitch.enabled": True}),
    ],
))


# nearest: social-snap-story-2015 (recorded vertical), social-video-call-2020 (16:9 laptop call);
# differs: a vertical live broadcast at 250 kilobits, freezing in public, heard on a phone speaker.
register_preset(Preset(
    id="social-periscope-live-2015",
    name="Vertical Livestream",
    family="social",
    era="2015",
    desc="Going live from a phone over cellular: 150 kilobits of vertical H.264 with a keyframe every eight seconds, the picture freezing whenever the signal dips, exposure hunting outdoors, and the audio cutting out mid-word.",
    tagline="9:16 phone live, 150k starve, freeze",
    tags=("10s", "periscope", "livestream", "vertical"),
    keywords=("tens", "9-16", "phone", "live", "low-bitrate", "freeze", "meerkat",
              "street", "reportage"),
    upscale="soft",
    video=[
        ("tone", {"contrast": 1.05, "knee": 0.88}),
        ("saturation", {"amount": 1.04}),
        ("exposure_auto", {"target": 0.44, "lag": 0.5, "overshoot": 0.25,
                           "max_boost": 3.5, "agc_gain_noise": 0.45, "wb_amount": 0.3}),
        ("chroma_dv", {"ratio": "4:2:0", "edge_sharpen": 0.2, "dct_blocks": 0.12}),
        ("codec_era", {"codec": "h264", "kbps": 150, "crf": -1, "res": "360p",
                       "gop": 250, "passes": 1, "denoise_pre": 0.3}),
        ("codec_glitch", {"codec": "mpeg4", "amount": 0.02, "drop_p": 0.0,
                          "freeze_p": 0.3, "kbps": 900, "gop": 250}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_historical_mic", {"profile": "electret_1985", "amount": 0.5,
                              "handling": 0.2, "self_noise_db": -54.0}),
        ("a_agc", {"target_db": -14.0, "max_gain_db": 14.0,
                   "attack_ms": 25.0, "release_ms": 500.0, "amount": 0.9}),
        ("a_codec_aac", {"kbps": 32, "mono": True}),
        ("a_digital_glitch", {"stutter_rate": 0.0, "mute_rate": 4.0, "crackle_rate": 0.0}),
        ("a_speaker", {"device": "cellphone_2008", "strength": 0.6}),
    ],
    variants=[
        Variant("wifi-clean", "On Wi-Fi",
                "Broadcasting from the kitchen instead of the street, and it almost looks fine.",
                video={"codec_era.kbps": 500, "codec_era.denoise_pre": 0.1,
                       "codec_glitch.enabled": False},
                audio={"a_digital_glitch.mute_rate": 0.0, "a_codec_aac.kbps": 64}),
        Variant("replay-reupload", "Saved Replay",
                "The archived replay, re-encoded once more on its way into the timeline.",
                video={"codec_era.passes": 2, "codec_era.kbps": 180,
                       "codec_glitch.freeze_p": 0.12}),
    ],
))


# nearest: social-youtube-1080p-2015 (upload pipeline only), auth-dslr-indie-naturalism-2012;
# differs: a real compact camera in front of the face: warm sharp glass, face-track AF hunting, onboard mic.
register_preset(Preset(
    id="social-vlog-camera-2017",
    name="Daily Vlog Camera",
    family="social",
    era="2017",
    desc="A flip-screen compact held at arm's length down a street: warm punchy color straight out of the camera, in-body sharpening on every edge, face-tracking autofocus breathing in and out, and an onboard mic hearing mostly hand.",
    tagline="Flip-screen compact, warm sharp, face AF",
    tags=("10s", "vlog", "compact-camera", "youtube"),
    keywords=("tens", "g7x", "flip-screen", "warm", "daily-vlog", "talking-head",
              "travel", "channel", "handheld"),
    upscale="sharp",
    video=[
        ("tone", {"contrast": 1.08, "knee": 0.86}),
        ("balance", {"warmth": 0.1}),
        ("saturation", {"amount": 1.12, "vibrance": 0.1}),
        ("exposure_auto", {"enabled": False, "target": 0.45, "lag": 0.5,
                           "overshoot": 0.2, "max_boost": 3.0,
                           "agc_gain_noise": 0.4, "wb_amount": 0.3}),
        ("optics", {"hunt_rate": 1.0, "focus_drift": 0.05}),
        ("sharpen", {"amount": 0.35, "radius": 1.0}),
        ("codec_era", {"codec": "h264", "kbps": 1900, "crf": -1, "res": "native",
                       "gop": 60, "passes": 2}),
        ("framing", {"aspect": "source", "mode": "box"}),
    ],
    audio=[
        ("a_historical_mic", {"profile": "electret_1985", "amount": 0.6,
                              "handling": 0.15, "self_noise_db": -56.0}),
        ("a_compressor", {"threshold_db": -20.0, "ratio": 3.0, "attack_ms": 8.0,
                          "release_ms": 220.0, "makeup_db": 1.5}),
        ("a_codec_aac", {"kbps": 128, "mono": False}),
        ("a_speaker", {"device": "laptop_2006", "strength": 0.3}),
    ],
    variants=[
        Variant("rode-mic-upgrade", "Shotgun On The Hot Shoe",
                "The microphone everybody bought in 2017, which finally kills the handling noise.",
                audio={"a_historical_mic.profile": "shotgun_1975",
                       "a_historical_mic.amount": 0.4,
                       "a_historical_mic.handling": 0.0}),
        Variant("phone-vlog-2019", "Switched To A Phone",
                "Two years on, shot on the phone instead: harder sharpening and no exposure lock.",
                video={"exposure_auto.enabled": True, "sharpen.amount": 0.5,
                       "optics.hunt_rate": 0.0},
                audio={"a_historical_mic.self_noise_db": -50.0}),
    ],
))
