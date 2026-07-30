"""Audio-only presets: the video passes through untouched."""

from ..engine.presets import Preset, Variant, register_preset

register_preset(Preset(
    id="audio-gramophone-1915",
    name="Gramophone Horn",
    family="audio",
    era="1915",
    desc="Acoustic-era shellac through a brass horn: a fist of midrange, wow from a hand-wound spring, surface roar like weather.",
    tagline="Midrange fist, deep wow, surface roar",
    tags=("audio-only", "1910s", "shellac"),
    audio=[
        ("a_bandlimit", {"low_hz": 250.0, "high_hz": 3000.0, "order": 6}),
        ("a_mono", {"amount": 1.0}),
        ("a_vinyl_wow", {"rpm": "78", "depth_cents": 25.0}),
        ("a_speaker", {"device": "gramophone_horn_1915", "strength": 0.9}),
        ("a_vinyl_noise", {"crackle": 24.0, "pops": 5.0, "frying_db": -46.0, "wear": 0.8}),
        ("a_distortion", {"type": "soft", "drive": 2.8}),
        ("a_needle", {"drop_at_start": True}),
    ],
))

register_preset(Preset(
    id="audio-shellac-1935",
    name="78 rpm Shellac",
    family="audio",
    era="1935",
    desc="Electrically recorded 78: fuller than the horn era but still boxed in, riding a bed of crackle and turntable rumble.",
    tagline="Boxed-in mids, crackle, table rumble",
    tags=("audio-only", "30s", "vinyl"),
    audio=[
        ("a_bandlimit", {"low_hz": 120.0, "high_hz": 5500.0, "order": 5}),
        ("a_mono", {"amount": 1.0}),
        ("a_vinyl_wow", {"rpm": "78", "depth_cents": 12.0}),
        ("a_vinyl_noise", {"crackle": 16.0, "pops": 3.0, "frying_db": -52.0, "rumble_db": -46.0, "wear": 0.6}),
        ("a_needle", {}),
        ("a_compressor", {"ratio": 3.0}),
    ],
    variants=[
        Variant("junk-shop", "Junk-Shop Copy", "Cracked, worn, loved to death.",
                audio={"a_vinyl_noise.crackle": 40.0, "a_vinyl_noise.pops": 9.0,
                       "a_vinyl_noise.wear": 1.0, "a_needle.skip_rate": 1.0} ),
    ],
))

register_preset(Preset(
    id="audio-vinyl-lp-1965",
    name="Vinyl LP",
    family="audio",
    era="1965",
    desc="A well-played 33⅓ on a decent table: warm and intact, with soft crackle, an off-center breath of wow, needle drop and all.",
    tagline="Warm and wide, soft crackle, needle drop",
    tags=("audio-only", "60s", "vinyl"),
    audio=[
        ("a_bandlimit", {"low_hz": 35.0, "high_hz": 15000.0}),
        ("a_vinyl_wow", {"rpm": "33", "depth_cents": 5.0}),
        ("a_vinyl_noise", {"crackle": 6.0, "pops": 1.5, "frying_db": -60.0, "rumble_db": -50.0, "wear": 0.3}),
        ("a_tape_sat", {"drive": 1.4}),
        ("a_needle", {"drop_at_start": True, "lift_at_end": True}),
    ],
    variants=[
        Variant("mint", "Mint Pressing", "Fresh from the sleeve.",
                audio={"a_vinyl_noise.crackle": 2.0, "a_vinyl_noise.pops": 0.5,
                       "a_needle.drop_at_start": False, "a_needle.lift_at_end": False}),
        Variant("party", "Party Copy", "Beer rings and a skip in the chorus.",
                audio={"a_vinyl_noise.crackle": 18.0, "a_vinyl_noise.pops": 6.0,
                       "a_vinyl_noise.wear": 0.7, "a_needle.skip_rate": 0.8}),
    ],
))

register_preset(Preset(
    id="audio-45-worn",
    name="Worn 45",
    family="audio",
    era="1972",
    desc="A jukebox single that earned its keep: groove-worn brightness loss, steady crackle, the 45's quicker wow.",
    tagline="Dull highs, steady crackle, quick wow",
    tags=("audio-only", "70s", "vinyl"),
    audio=[
        ("a_bandlimit", {"low_hz": 55.0, "high_hz": 11000.0}),
        ("a_vinyl_wow", {"rpm": "45", "depth_cents": 8.0}),
        ("a_vinyl_noise", {"crackle": 14.0, "pops": 4.0, "frying_db": -52.0, "wear": 0.7}),
        ("a_speaker", {"device": "jukebox_1955", "strength": 0.5}),
        ("a_compressor", {"ratio": 2.5}),
    ],
))

register_preset(Preset(
    id="audio-am-1948",
    name="AM Radio",
    family="audio",
    era="1948",
    desc="The wireless after dinner: narrow, compressed, atmospheric static breathing with the ionosphere, a faraway whistle riding the carrier.",
    tagline="Narrow, pumping, atmospheric static",
    tags=("audio-only", "40s", "radio"),
    audio=[
        ("a_am_radio", {"static_db": -42.0, "fade": 0.4, "whistle_db": -56.0, "pump": 0.5}),
        ("a_speaker", {"device": "portable_radio_1975" , "strength": 0.7}),
        ("a_hum", {"hz": 60, "level_db": -48.0}),
    ],
    variants=[
        Variant("storm", "Distant Station", "Fading in and out through summer static.",
                audio={"a_am_radio.static_db": -33.0, "a_am_radio.fade": 0.8, "a_am_radio.tune_drift": 1.0}),
    ],
))

register_preset(Preset(
    id="audio-fm-1978",
    name="FM Late Night",
    family="audio",
    era="1978",
    desc="Album-rock FM with the lights off: full-range but compressed to velvet, pilot hiss under the quiet parts, a passing multipath flutter.",
    tagline="Velvet compression, pilot hiss, multipath",
    tags=("audio-only", "70s", "radio"),
    audio=[
        ("a_fm_radio", {"hiss_db": -46.0, "multipath": 0.4}),
        ("a_compressor", {"ratio": 3.5}),
        ("a_speaker", {"device": "car_dash_1978", "strength": 0.45}),
    ],
))

register_preset(Preset(
    id="audio-cassette-1984",
    name="Cassette",
    family="audio",
    era="1984",
    desc="A Type I mixtape, dubbed with love: head-bump warmth, honest hiss, azimuth smear on the highs and a wobble you can lean on.",
    tagline="Head bump, hiss, azimuth-dulled highs",
    tags=("audio-only", "80s", "tape"),
    audio=[
        ("a_bandlimit", {"low_hz": 40.0, "high_hz": 13000.0}),
        ("a_wow_flutter", {"wow_depth": 7.0, "flutter_depth": 5.0}),
        ("a_tape_sat", {"drive": 2.0, "bump_db": 2.5}),
        ("a_tape_hiss", {"level_db": -44.0, "type": "cassette"}),
        ("a_tape_dropouts", {"rate": 1.0, "azimuth": 0.4}),
    ],
    variants=[
        Variant("walkman", "Dying Walkman", "Batteries at 20%: the wobble becomes seasick.",
                audio={"a_wow_flutter.wow_depth": 22.0, "a_wow_flutter.flutter_depth": 12.0,
                       "a_wow_flutter.speed_pct": -1.5}),
        Variant("chrome", "Chrome + Dolby", "Type II pretensions: quieter, brighter.",
                audio={"a_tape_hiss.level_db": -52.0, "a_bandlimit.high_hz": 15000.0}),
    ],
))

register_preset(Preset(
    id="audio-telephone-1955",
    name="Telephone",
    family="audio",
    era="1955",
    desc="A rotary line call: 300–3400 Hz of Bakelite intimacy, carbon-mic grit, the hum of copper miles.",
    tagline="300-3400 Hz carbon grit and line hum",
    tags=("audio-only", "50s", "phone"),
    audio=[
        ("a_telephone", {"era": "rotary_1955", "line_noise_db": -46.0}),
    ],
    variants=[
        Variant("candlestick", "1915 Candlestick", "Shouting down a wire across town.",
                audio={"a_telephone.era": "candlestick_1915"}),
        Variant("cordless", "1992 Cordless", "FM hiss and the occasional static spray.",
                audio={"a_telephone.era": "cordless_1992"}),
        Variant("cell", "2003 Cellular", "A real speech codec doing its worst.",
                audio={"a_telephone.era": "cell_2003"}),
    ],
))

register_preset(Preset(
    id="audio-answering-machine-1988",
    name="Answering Machine",
    family="audio",
    era="1988",
    desc="Microcassette memo of a missed call: telephone band squeezed onto slow tape, warbly and thin. Leave a message after the beep.",
    tagline="Thin phone band on warbling slow tape",
    tags=("audio-only", "80s", "phone", "tape"),
    audio=[
        ("a_telephone", {"era": "touchtone_1985", "line_noise_db": -44.0}),
        ("a_wow_flutter", {"wow_depth": 14.0, "flutter_depth": 9.0}),
        ("a_tape_hiss", {"level_db": -38.0, "type": "dictaphone"}),
        ("a_tape_sat", {"drive": 2.2}),
        ("a_speaker", {"device": "clock_radio_1988", "strength": 0.6}),
    ],
))

register_preset(Preset(
    id="audio-pa-1970",
    name="PA Announcement",
    family="audio",
    era="1970",
    desc="Attention, shoppers: horn-loaded midrange, gentle clipping, a slap of room echo off hard floors.",
    tagline="Bullhorn mids, clipping, one hard slap",
    tags=("audio-only", "70s", "pa"),
    audio=[
        ("a_pa_bullhorn", {"device": "pa_hall", "drive": 2.5, "slap_ms": 140.0, "slap_gain_db": -14.0, "slap_repeats": 1}),
        ("a_hum", {"hz": 60, "level_db": -46.0}),
    ],
    variants=[
        Variant("bullhorn", "Bullhorn", "Protest-grade narrowband bark.",
                audio={"a_pa_bullhorn.device": "bullhorn", "a_pa_bullhorn.drive": 4.5}),
        Variant("stadium", "Stadium Echo", "The announcement arrives twice.",
                audio={"a_pa_bullhorn.device": "pa_stadium", "a_pa_bullhorn.slap_ms": 260.0,
                       "a_pa_bullhorn.slap_gain_db": -10.0, "a_pa_bullhorn.slap_repeats": 2}),
    ],
))

register_preset(Preset(
    id="audio-tv-speaker-1975",
    name="TV Speaker",
    family="audio",
    era="1975",
    desc="The sound of television before soundbars: one paper cone in a particleboard cabinet, intercarrier buzz included.",
    tagline="One paper cone, cabinet boom, buzz",
    tags=("audio-only", "70s", "tv"),
    audio=[
        ("a_tv_sound", {"buzz_db": -42.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_speaker", {"device": "tv_mono_1965", "strength": 0.7}),
        ("a_room", {"size": 0.75, "decay_s": 0.4, "mix": 0.18}),
    ],
))

register_preset(Preset(
    id="audio-mp3-2002",
    name="Napster MP3",
    family="audio",
    era="2002",
    desc="A 56k trophy: real low-bitrate MP3 swirl, cymbals turned to watercolor, stereo folded into suggestion.",
    tagline="48k swirl, watercolor cymbals",
    tags=("audio-only", "2000s", "codec"),
    audio=[
        ("a_codec_mp3", {"kbps": 48}),
    ],
    variants=[
        Variant("worse", "The 32 kbps One", "Labeled wrong, sounds like a seashell.",
                audio={"a_codec_mp3.kbps": 24}),
    ],
))

register_preset(Preset(
    id="audio-optical-1942",
    name="Optical Soundtrack",
    family="audio",
    era="1942",
    desc="Variable-area film sound on its own: academy rolloff, cell-noise crackle, sprocket flutter - the voice of the newsreel.",
    tagline="Academy rolloff, cell crackle, flutter",
    tags=("audio-only", "40s", "film"),
    audio=[
        ("a_optical_track", {"cell_noise": -45.0, "academy_rolloff": "newsreel_1930s", "drive": 1.8}),
        ("a_mono", {"amount": 1.0}),
        ("a_compressor", {"ratio": 4.0}),
    ],
))
