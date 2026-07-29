"""Digital-family presets, second wave: streaming misery, pocket players and home transfers."""

from ..engine.presets import Preset, Variant, register_preset

register_preset(Preset(
    id="realplayer-1999",
    name="RealPlayer Stream",
    family="digital",
    era="1999",
    desc="Buffering... buffering: a postage stamp of smeared blocks that freezes mid-gesture, snaps forward, and sounds like a phone call from inside an aquarium.",
    tags=("90s", "web", "streaming", "codec"),
    video=[
        ("tone", {"contrast": 1.02}),
        ("codec_era", {"codec": "msmpeg4", "kbps": 80, "res": "144p", "gop": 90}),
        ("codec_glitch", {"codec": "msmpeg4", "amount": 0.05, "drop_p": 0.0, "freeze_p": 0.35,
                          "kbps": 500, "gop": 90}),
    ],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_codec_mp3", {"kbps": 16, "mono": True}),
        ("a_digital_glitch", {"stutter_rate": 4.0, "mute_rate": 2.0, "crackle_rate": 2.0}),
        ("a_speaker", {"device": "pc_speaker_1992", "strength": 0.45}),
    ],
    variants=[
        Variant("modem-56k", "56k Modem", "Someone picked up the phone downstairs.",
                video={"codec_era.kbps": 60, "codec_glitch.freeze_p": 0.6},
                audio={"a_codec_mp3.kbps": 8, "a_digital_glitch.mute_rate": 6.0}),
        Variant("campus-lan", "Campus LAN", "Broadband bragging rights: it only freezes twice.",
                video={"codec_era.kbps": 180, "codec_era.res": "240p",
                       "codec_glitch.freeze_p": 0.12},
                audio={"a_codec_mp3.kbps": 32, "a_digital_glitch.mute_rate": 0.5}),
    ],
))

register_preset(Preset(
    id="psp-ripped-2006",
    name="PSP Rip",
    family="digital",
    era="2006",
    desc="Converted for the bus ride: widescreen crushed to Memory Stick bitrates, edges oversharpened into halos by the rip tool, earbuds doing the mastering.",
    tags=("00s", "handheld", "codec"),
    video=[
        ("tone", {"contrast": 1.06}),
        ("chroma_dv", {"ratio": "4:2:0", "edge_sharpen": 1.0}),
        ("codec_era", {"codec": "mpeg4", "kbps": 300, "res": "240p", "gop": 90}),
        ("framing", {"aspect": "16:9", "mode": "box"}),
    ],
    audio=[
        ("a_codec_mp3", {"kbps": 96, "mono": False}),
        ("a_speaker", {"device": "earbud_2005", "strength": 0.6}),
    ],
    variants=[
        Variant("fits-more", "Fits-More Setting", "The converter's lowest quality tier: 40 movies per stick.",
                video={"codec_era.kbps": 160, "codec_era.res": "144p", "chroma_dv.edge_sharpen": 1.4},
                audio={"a_codec_mp3.kbps": 48, "a_codec_mp3.mono": True}),
    ],
))

register_preset(Preset(
    id="ipod-video-2005",
    name="iPod Video",
    family="digital",
    era="2005",
    desc="The 320-line pocket theater: a clean careful little encode, soft but composed, whole seasons riding to work through white earbuds.",
    tags=("00s", "handheld", "clean"),
    video=[
        ("tone", {"contrast": 1.04, "knee": 0.88}),
        ("chroma_dv", {"ratio": "4:2:0", "edge_sharpen": 0.25}),
        ("codec_era", {"codec": "mpeg4", "kbps": 550, "res": "240p", "gop": 60}),
    ],
    audio=[
        ("a_codec_mp3", {"kbps": 128, "mono": False}),
        ("a_speaker", {"device": "earbud_2005", "strength": 0.5}),
    ],
    variants=[
        Variant("handbrake-night", "Overnight Rip", "Queued at bedtime on default settings.",
                video={"codec_era.kbps": 380, "codec_era.gop": 120}),
    ],
))

register_preset(Preset(
    id="myspace-2006",
    name="MySpace Clip",
    family="digital",
    era="2006",
    desc="Embedded in a glitter profile: FLV re-crunched from someone else's re-upload, gradients collapsing into contour bands, 32 kbps mono doing the vocals.",
    tags=("00s", "web", "generation-loss"),
    video=[
        ("tone", {"contrast": 1.08}),
        ("saturation", {"amount": 1.08}),
        ("codec_era", {"codec": "flv1", "kbps": 168, "res": "144p", "gop": 120}),
        ("upload_gen", {"gens": 2, "deband_loss": 0.4, "qscale": 8}),
    ],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_codec_mp3", {"kbps": 32, "mono": True}),
        ("a_digital_glitch", {"stutter_rate": 1.0, "mute_rate": 0.5, "crackle_rate": 1.0}),
    ],
    variants=[
        Variant("profile-song", "Autoplay Song", "The audio arrives before the page does.",
                audio={"a_codec_mp3.kbps": 24, "a_digital_glitch.stutter_rate": 3.0}),
        Variant("third-hand", "Third-Hand Repost", "Ripped from a rip of a rip.",
                video={"upload_gen.gens": 4, "upload_gen.deband_loss": 0.6,
                       "codec_era.kbps": 140}),
    ],
))

register_preset(Preset(
    id="hd-1080i-2008",
    name="Early 1080i",
    family="digital",
    era="2008",
    desc="HD at last, interlaced anyway: razor edges and pumped broadcast color, weave combs surviving every pan, the encoder's denoiser waxing the fine detail.",
    tags=("00s", "hd", "broadcast", "interlaced"),
    video=[
        ("tone", {"contrast": 1.1, "knee": 0.86}),
        ("saturation", {"amount": 1.2, "vibrance": 0.2}),
        ("chroma_dv", {"ratio": "4:2:0", "edge_sharpen": 0.7}),
        ("codec_era", {"codec": "mpeg2video", "kbps": 5500, "gop": 15,
                       "field_mode": "interlaced_tff", "denoise_pre": 0.45}),
        ("deinterlace_artifact", {"mode": "weave_comb", "amount": 0.5}),
    ],
    audio=[
        ("a_compressor", {"ratio": 5.0, "threshold_db": -20.0, "makeup_db": 3.0}),
        ("a_codec_mp3", {"kbps": 128, "mono": False}),
    ],
    variants=[
        Variant("sports-mode", "Sports Feed", "Sharper, louder, oranger.",
                video={"chroma_dv.edge_sharpen": 1.1, "saturation.amount": 1.3,
                       "codec_era.kbps": 4000},
                audio={"a_compressor.ratio": 7.0}),
        Variant("cheap-box", "Bargain Cable Box", "The bitrate the franchise could afford.",
                video={"codec_era.kbps": 2800, "codec_era.denoise_pre": 0.6,
                       "deinterlace_artifact.amount": 0.7}),
    ],
))

register_preset(Preset(
    id="dvdr-home-transfer-2005",
    name="Tapes-to-DVD",
    family="digital",
    era="2005",
    desc="Dad's VHS archive 'digitized': the noise reducer wipes away the tape grain and half of every face with it — waxy skin, ghost trails, a menu with beach clip-art.",
    tags=("00s", "vhs", "dvnr", "transfer"),
    proc_height=540,
    upscale="soft",
    video=[
        ("tone", {"contrast": 1.05, "lift": 0.02}),
        ("stock", {"profile": "tube_80s", "strength": 0.5}),
        ("ntsc", {"strength": 0.8, "phase_noise": 2.0, "rainbow": 0.25, "dot_crawl": 0.25}),
        ("vhs", {"mode": "sp", "luma_noise": 0.4, "chroma_noise": 0.4, "head_switch": 0.55,
                 "time_base_error": 0.35, "flagging": 0.25, "dropouts": 0.8, "sharpen": 0.5}),
        ("dvnr", {"strength": 0.6, "wax": 0.55}),
        ("codec_era", {"codec": "mpeg2video", "kbps": 4200, "res": "480p", "gop": 15,
                       "field_mode": "interlaced_tff"}),
        ("interlace", {"combing": 0.4}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 80.0, "high_hz": 10000.0}),
        ("a_wow_flutter", {"wow_depth": 5.0, "flutter_depth": 4.0}),
        ("a_tape_hiss", {"level_db": -46.0}),
        ("a_codec_mp3", {"kbps": 128, "mono": False}),
    ],
    variants=[
        Variant("six-hour-disc", "Six Hours One Disc", "Every birthday 1989-1996, one DVD-R.",
                video={"codec_era.kbps": 2000, "dvnr.strength": 0.75, "dvnr.wax": 0.7},
                audio={"a_codec_mp3.kbps": 64}),
        Variant("gentle-pass", "Gentle Pass", "The one shop in town that respected the grain.",
                video={"dvnr.strength": 0.3, "dvnr.wax": 0.25, "codec_era.kbps": 6500}),
    ],
))

register_preset(Preset(
    id="webcam-stream-2012",
    name="Late Webcam",
    family="digital",
    era="2012",
    desc="The laptop lid's eye: sharper than the ball-cam era but pumping white balance at every lamp, motion collapsing into blocks, one subpixel stuck on red.",
    tags=("10s", "webcam", "streaming"),
    video=[
        ("exposure_auto", {"lag": 0.9, "overshoot": 0.2, "agc_gain_noise": 0.4,
                           "flicker_60hz": 0.2}),
        ("auto_color", {"wb_pump": 0.5, "level_pump": 0.4, "lag_s": 1.0}),
        ("tone", {"contrast": 1.02, "lift": 0.03}),
        ("lcd_screen", {"grid": 0.0, "response_smear": 0.0, "backlight_bleed": 0.0,
                        "viewing_angle": 0.0, "dead_pixels": 2}),
        ("codec_era", {"codec": "mpeg4", "kbps": 420, "res": "360p", "gop": 120}),
    ],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_bandlimit", {"low_hz": 120.0, "high_hz": 7500.0}),
        ("a_agc", {"amount": 0.6}),
        ("a_digital_glitch", {"stutter_rate": 1.5, "mute_rate": 0.5, "crackle_rate": 1.0}),
        ("a_room", {"size": 0.7, "decay_s": 0.35, "mix": 0.18}),
    ],
    variants=[
        Variant("potato", "Potato Quality", "The stream the chat complains about.",
                video={"codec_era.kbps": 180, "codec_era.res": "240p",
                       "auto_color.wb_pump": 0.7},
                audio={"a_digital_glitch.stutter_rate": 5.0, "a_digital_glitch.mute_rate": 2.0}),
    ],
))

register_preset(Preset(
    id="screen-recording-2009",
    name="Filmed Off the Monitor",
    family="digital",
    era="2009",
    desc="No capture card, no problem: a camera aimed at an LCD — moiré bands breathing over the subpixel stripes, backlight blooming in the corners, room tone on the mic.",
    tags=("00s", "lcd", "bootleg", "meta"),
    video=[
        ("exposure_auto", {"lag": 0.8, "overshoot": 0.25, "wb_amount": 0.15}),
        ("optics", {"corner_softness": 0.25, "distortion": 0.06}),
        ("tone", {"contrast": 1.04, "lift": 0.04}),
        ("lcd_screen", {"grid": 0.25, "scale": 3, "subpixel": "rgb_stripe_lcd",
                        "response_smear": 0.35, "backlight_bleed": 0.25, "viewing_angle": 0.12,
                        "moire_cam": 0.3}),
        ("codec_era", {"codec": "mpeg4", "kbps": 500, "res": "360p", "gop": 90}),
    ],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_bandlimit", {"low_hz": 150.0, "high_hz": 8000.0}),
        ("a_agc", {"amount": 0.7}),
        ("a_speaker", {"device": "laptop_2006", "strength": 0.55}),
        ("a_room", {"size": 0.8, "decay_s": 0.4, "mix": 0.25}),
        ("a_hum", {"hz": 60, "level_db": -52.0}),
    ],
    variants=[
        Variant("leaning-in", "Leaning In", "Close enough to count the subpixels.",
                video={"lcd_screen.grid": 0.4, "lcd_screen.scale": 5, "lcd_screen.moire_cam": 0.15,
                       "optics.distortion": 0.1}),
        Variant("handheld", "Handheld Phone", "Filmed standing up, arm slowly dying.",
                video={"lcd_screen.moire_cam": 0.5, "codec_era.kbps": 300,
                       "codec_era.res": "240p", "exposure_auto.wb_amount": 0.3}),
    ],
))

register_preset(Preset(
    id="first-vertical-2013",
    name="First Vertical",
    family="digital",
    era="2013",
    desc="Shot tall on a phone before that was allowed: pillarboxed 9:16, exposure pumping at every window, a nervous little stabilizer wobble it can't quite hide.",
    tags=("10s", "phone", "vertical"),
    video=[
        ("exposure_auto", {"lag": 0.5, "overshoot": 0.35, "agc_gain_noise": 0.35,
                           "wb_amount": 0.35, "iris_step": 0.3}),
        ("tone", {"contrast": 1.05, "knee": 0.88}),
        ("gate_weave", {"amount": 0.6, "hz": 1.4, "rotation": 0.03, "splice_bump": 0.0}),
        ("chroma_dv", {"ratio": "4:2:0", "edge_sharpen": 0.4}),
        ("codec_era", {"codec": "mpeg4", "kbps": 1400, "res": "480p", "gop": 60}),
        ("framing", {"aspect": "9:16", "mode": "box"}),
    ],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_bandlimit", {"low_hz": 150.0, "high_hz": 11000.0}),
        ("a_agc", {"amount": 0.65}),
        ("a_compressor", {"ratio": 2.5}),
    ],
    variants=[
        Variant("front-camera", "Front Camera", "The lesser lens, gained up and proud.",
                video={"codec_era.kbps": 700, "codec_era.res": "360p",
                       "exposure_auto.agc_gain_noise": 0.6}),
    ],
))

register_preset(Preset(
    id="bootleg-vcd-mall-1998",
    name="Mall VCD",
    family="digital",
    era="1998",
    desc="A camcorder smuggled past the usher, pressed to shiny silver discs: hot screen center, keystone lean, MPEG-1 blocks blooming on every cut, the multiplex air conditioning on the soundtrack.",
    tags=("90s", "bootleg", "vcd", "cinema"),
    video=[
        ("tone", {"contrast": 1.08, "lift": 0.05, "knee": 0.8}),
        ("screen", {"surface": "matte_white", "hotspot": 0.5, "keystone_v": 0.06,
                    "room_spill": 0.2, "shake_event": 1.0}),
        ("exposure_auto", {"lag": 1.0, "overshoot": 0.2, "max_boost": 4.0,
                           "agc_gain_noise": 0.5}),
        ("gate_weave", {"amount": 0.8, "hz": 0.9, "rotation": 0.04, "splice_bump": 0.0}),
        ("codec_era", {"codec": "mpeg1video", "kbps": 1150, "res": "240p", "gop": 15}),
    ],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_bandlimit", {"low_hz": 150.0, "high_hz": 6000.0}),
        ("a_agc", {"amount": 0.7}),
        ("a_room", {"size": 1.4, "decay_s": 1.1, "mix": 0.3, "mode": "chamber"}),
        ("a_codec_mp3", {"kbps": 64, "mono": True}),
        ("a_bed", {"bed": "air_handler_hall", "level_db": -34.0, "duck": 0.3}),
    ],
    variants=[
        Variant("back-row", "Back Row Seat", "Steeper angle, deeper murk, braver usher.",
                video={"screen.keystone_v": 0.12, "screen.hotspot": 0.65, "tone.lift": 0.08,
                       "gate_weave.amount": 1.4}),
        Variant("disc-two", "Disc Two of Two", "The second act fared worse in the press run.",
                video={"codec_era.kbps": 900},
                audio={"a_codec_mp3.kbps": 48}),
    ],
))
