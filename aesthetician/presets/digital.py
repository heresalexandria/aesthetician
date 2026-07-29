"""Digital-family presets: the early-digital and surveillance eras, via real codecs."""

from ..engine.presets import Preset, Variant, register_preset

register_preset(Preset(
    id="dvd-2001",
    name="Early DVD",
    family="digital",
    era="2001",
    desc="A first-wave DVD authoring job: real MPEG-2 at modest bitrate — gentle macroblocks in motion, mosquito noise around titles.",
    tagline="Gentle macroblocks, mosquito noise",
    tags=("2000s", "mpeg2", "codec"),
    video=[
        ("tone", {"contrast": 1.05}),
        ("chroma_dv", {"ratio": "4:2:0"}),
        ("codec_era", {"codec": "mpeg2video", "kbps": 3500, "res": "480p", "gop": 15}),
        ("interlace", {"combing": 0.35}),
    ],
    audio=[
        ("a_compressor", {"ratio": 2.5}),
        ("a_codec_mp3", {"kbps": 128}),
    ],
    variants=[
        Variant("bad-author", "Bargain Bin", "Six movies on one disc: bitrate starvation city.",
                video={"codec_era.kbps": 1600}),
    ],
))

register_preset(Preset(
    id="vcd-1997",
    name="Video CD",
    family="digital",
    era="1997",
    desc="The bootleg standard of the 90s: real MPEG-1 at 352 lines and 1150 kbps, blocks blooming on every cut, audio squeezed thin.",
    tagline="352 lines, blocks blooming on cuts",
    tags=("90s", "mpeg1", "bootleg"),
    video=[
        ("tone", {"contrast": 1.04}),
        ("codec_era", {"codec": "mpeg1video", "kbps": 1150, "res": "240p", "gop": 15}),
    ],
    audio=[
        ("a_bandlimit", {"low_hz": 60.0, "high_hz": 10000.0}),
        ("a_codec_mp3", {"kbps": 64, "mono": False}),
    ],
    variants=[
        Variant("night-market", "Night Market Copy", "A camcordered screener pressed to VCD.",
                video={"codec_era.kbps": 800, "codec_era.passes": 2}),
    ],
))

register_preset(Preset(
    id="webvideo-2006",
    name="Early Web Video",
    family="digital",
    era="2006",
    desc="240 lines of dial-up dreams: real FLV/Sorenson-era encoding, double-compressed, with 22 kHz mono MP3 audio. Broadcast yourself.",
    tagline="240p Sorenson mush, 32k mono",
    tags=("2000s", "flv", "youtube"),
    video=[
        ("codec_era", {"codec": "flv1", "kbps": 240, "res": "240p", "passes": 2}),
    ],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_codec_mp3", {"kbps": 32, "mono": True}),
    ],
    variants=[
        Variant("reupload", "Re-upload of a Re-upload", "Three generations deep into the compression mines.",
                video={"codec_era.passes": 3, "codec_era.kbps": 240},
                audio={"a_codec_mp3.kbps": 24}),
    ],
))

register_preset(Preset(
    id="webcam-2004",
    name="MSN Webcam",
    family="digital",
    era="2004",
    desc="A ball-shaped webcam on a CRT bezel: tiny sensor smear, frame stutter, blocky motion and VoIP audio artifacts.",
    tagline="Sensor smear, frame stutter, VoIP crackle",
    tags=("2000s", "webcam", "voip"),
    video=[
        ("exposure_auto", {}),
        ("tone", {"contrast": 0.98, "lift": 0.04}),
        ("cadence", {"pattern": "threes"}),
        ("codec_era", {"codec": "msmpeg4", "kbps": 180, "res": "144p", "gop": 60}),
        ("lcd_screen", {"response_smear": 0.3}),
    ],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_bandlimit", {"low_hz": 200.0, "high_hz": 5500.0}),
        ("a_digital_glitch", {"stutter_rate": 3.0, "mute_rate": 1.0, "crackle_rate": 2.0}),
        ("a_bitcrush", {"bits": 12, "sr_hz": 11025.0}),
        ("a_agc", {"amount": 0.7}),
    ],
))

register_preset(Preset(
    id="cameraphone-2007",
    name="Flip Phone Clip",
    family="digital",
    era="2007",
    desc="176×144 of pure memory: real 3GP-era encoding, smeared blocks, and speech-codec audio that turns concerts into soup.",
    tagline="176x144 blocks, speech-codec soup",
    tags=("2000s", "3gp", "phone"),
    video=[
        ("exposure_auto", {}),
        ("codec_era", {"codec": "mpeg4", "kbps": 96, "res": "144p", "gop": 50}),
    ],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_codec_speech", {}),
        ("a_agc", {"amount": 0.8}),
    ],
))

register_preset(Preset(
    id="minidv-2000",
    name="MiniDV Handycam",
    family="digital",
    era="2000",
    desc="The millennium home format: crisp but over-sharpened edges, 4:1:1 chroma stair-steps, interlace combing on every pan.",
    tagline="Over-sharp edges, 4:1:1 chroma steps",
    tags=("2000s", "dv", "camcorder"),
    proc_height=640,
    video=[
        ("exposure_auto", {}),
        ("tone", {"contrast": 1.06, "knee": 0.86}),
        ("chroma_dv", {"ratio": "4:1:1", "edge_sharpen": 0.6}),
        ("interlace", {"combing": 0.6, "twitter": 0.3}),
        ("timestamp", {"style": "lcd_gray", "corner": "br", "date_format": "yyyy-mm-dd",
                       "start": "2000-06-17 14:22:05", "opacity": 0.0}),
    ],
    audio=[
        ("a_compressor", {"ratio": 2.0}),
        ("a_agc", {"amount": 0.4}),
    ],
    variants=[
        Variant("stamped", "With Timestamp", "LCD date burned in.",
                video={"timestamp.opacity": 0.9}),
    ],
))

register_preset(Preset(
    id="datamosh",
    name="Datamosh",
    family="digital",
    era="2009",
    desc="Real bitstream corruption, decoded with error concealment: motion drags the world apart in smeared prediction blocks. Chaos, curated.",
    tagline="Motion smearing into prediction blocks",
    tags=("glitch", "corruption", "experimental"),
    video=[
        ("codec_glitch", {"amount": 0.5, "drop_p": 0.3}),
    ],
    audio=[
        ("a_digital_glitch", {"stutter_rate": 6.0, "mute_rate": 2.0, "crackle_rate": 4.0}),
        ("a_bitcrush", {"bits": 10, "sr_hz": 22050.0}),
    ],
    variants=[
        Variant("mild", "Light Corruption", "Occasional shudders and block slips.",
                video={"codec_glitch.amount": 0.25, "codec_glitch.drop_p": 0.1},
                audio={"a_digital_glitch.stutter_rate": 2.0}),
        Variant("meltdown", "Full Meltdown", "The file is dissolving in real time.",
                video={"codec_glitch.amount": 0.85, "codec_glitch.drop_p": 0.6},
                audio={"a_digital_glitch.stutter_rate": 12.0, "a_digital_glitch.mute_rate": 4.0}),
    ],
))

register_preset(Preset(
    id="security-vcr-1994",
    name="Security VCR",
    family="digital",
    era="1994",
    desc="Camera 3, aisle 5: cool drained color, time-lapse stutter, phosphor smear on movement and a white timestamp that never blinks.",
    tagline="Drained color, 3-frame stutter, timestamp",
    tags=("90s", "cctv", "surveillance", "timestamp"),
    proc_height=480,
    upscale="soft",
    video=[
        ("tone", {"contrast": 0.96, "lift": 0.06, "knee": 0.8}),
        ("saturation", {"amount": 0.55}),
        ("balance", {"warmth": -0.15, "tint": -0.1}),
        ("optics", {"distortion": 0.18, "corner_softness": 0.35}),
        ("cadence", {"pattern": "threes"}),
        ("phosphor_decay", {"decay": 0.35}),
        ("vhs", {"mode": "ep", "luma_noise": 0.22, "chroma_noise": 0.16, "head_switch": 0.4,
                 "time_base_error": 0.3, "dropouts": 0.5, "sharpen": 0.3}),
        ("interlace", {"combing": 0.5}),
        ("timestamp", {"style": "security_white", "corner": "tl",
                       "date_format": "dow_dmy_hms", "start": "1994-11-08 03:12:45"}),
        ("crt", {"scan_strength": 0.15, "bloom": 0.2}),
    ],
    audio=[
        ("a_gain", {"db": -60.0}),
        ("a_hum", {"hz": 60, "buzz": 0.3, "level_db": -40.0}),
        ("a_tape_hiss", {"level_db": -38.0, "type": "dictaphone"}),
    ],
    variants=[
        Variant("mono-ir", "Night IR", "Infrared floodlight mono with hot blooms.",
                video={"saturation.amount": 0.0, "tone.lift": 0.1, "crt.bloom": 0.5}),
        Variant("keep-sound", "Keep Audio", "Retain muffled room audio.",
                audio={"a_gain.db": -14.0}),
    ],
))

register_preset(Preset(
    id="nightshot-2001",
    name="Camcorder NightShot",
    family="digital",
    era="2001",
    desc="Infrared home video: phosphor-green faces with glowing eyes, blooming highlights, gained-up noise crawling in the dark.",
    tagline="IR green, glowing eyes, crawling noise",
    tags=("2000s", "infrared", "camcorder"),
    proc_height=560,
    video=[
        ("mono", {"response": "modern", "tint": "phosphor_green", "tint_amt": 0.85}),
        ("tone", {"contrast": 1.08, "lift": 0.09, "knee": 0.7, "exposure": 0.4}),
        ("crt", {"bloom": 0.55}),
        ("vhs", {"mode": "sp", "luma_noise": 0.65, "chroma_noise": 0.0, "head_switch": 0.4,
                 "time_base_error": 0.25, "sharpen": 0.5}),
        ("interlace", {"combing": 0.5}),
        ("timestamp", {"style": "lcd_gray", "corner": "br", "date_format": "yyyy-mm-dd",
                       "start": "2001-10-31 23:58:01"}),
    ],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_agc", {"amount": 0.85}),
        ("a_tape_hiss", {"level_db": -38.0}),
        ("a_bandlimit", {"low_hz": 120.0, "high_hz": 8000.0}),
    ],
))

register_preset(Preset(
    id="pixel-1990",
    name="PC Game Capture",
    family="digital",
    era="1990",
    desc="256 colors if you were lucky: fat pixels, ordered dither shimmer, palette-snapped hues straight off a CRT monitor.",
    tagline="Fat VGA pixels, ordered dither shimmer",
    tags=("retro", "pixel", "games"),
    video=[
        ("tone", {"contrast": 1.1}),
        ("pixel_era", {"res_h": 200, "palette": "vga256", "dither": "bayer4"}),
        ("crt", {"scan_strength": 0.35, "curvature": 0.1, "bloom": 0.25}),
    ],
    audio=[
        ("a_bitcrush", {"bits": 8, "sr_hz": 11025.0, "antialias": False}),
        ("a_speaker", {"device": "clock_radio_1988", "strength": 0.6}),
    ],
    variants=[
        Variant("ega", "EGA 16-Color", "The 16 colors of 1987.",
                video={"pixel_era.palette": "ega16", "pixel_era.res_h": 175}),
        Variant("gameboy", "Handheld LCD", "Four shades of pea soup.",
                video={"pixel_era.palette": "gameboy_dmg", "pixel_era.res_h": 144,
                       "crt.scan_strength": 0.0}),
    ],
))
