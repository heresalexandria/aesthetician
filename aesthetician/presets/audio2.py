"""Audio-only presets, second wave: wires, carts, carriers and public address.

Video passes through untouched (family convention). Chains follow the audio
signal path: source tone -> medium -> transmission -> device -> room -> beds.
"""

from ..engine.presets import Preset, Variant, register_preset

register_preset(Preset(
    id="audio-wire-1945",
    name="Wire Recorder",
    family="audio",
    era="1945",
    desc="A memo on a spool of steel: highs shimmering underwater, the wire's 2.8 kHz twang, kinks punching quick holes in the voice.",
    tags=("audio-only", "40s", "wire"),
    audio=[
        ("a_wire_recorder", {"flutter": 0.7, "watery": 0.7, "twang": 0.55,
                             "dropout_rate": 30.0, "hiss_db": -41.0}),
        ("a_tube_amp", {"drive": 1.7, "sag": 0.35, "hum_db": -52.0}),
        ("a_compressor", {"ratio": 3.0}),
    ],
    variants=[
        Variant("archive", "Museum Transfer", "The wire on its best behavior, played once for posterity.",
                audio={"a_wire_recorder.flutter": 0.45, "a_wire_recorder.watery": 0.4,
                       "a_wire_recorder.dropout_rate": 8.0, "a_wire_recorder.hiss_db": -46.0}),
        Variant("kinked", "Kinked Spool", "Decades wound too tight: the wire fights every inch.",
                audio={"a_wire_recorder.dropout_rate": 80.0, "a_wire_recorder.flutter": 0.9,
                       "a_wire_recorder.hiss_db": -37.0}),
    ],
))

register_preset(Preset(
    id="audio-transcription-1938",
    name="Transcription Disc",
    family="audio",
    era="1938",
    desc="Sixteen inches of lacquer at 33⅓: wider and calmer than any 78, the surface breathing a soft swish once per revolution.",
    tags=("audio-only", "30s", "radio", "disc"),
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_transcription_disc", {"band": 1.0, "swish": 0.7, "crackle": 3.5, "wear": 0.35}),
        ("a_vinyl_wow", {"rpm": "33", "depth_cents": 5.0}),
        ("a_tube_amp", {"drive": 1.6, "sag": 0.3, "hum_db": -54.0}),
        ("a_compressor", {"ratio": 3.0}),
    ],
    variants=[
        Variant("fresh-cut", "Fresh Lacquer", "Cut an hour ago for the network feed.",
                audio={"a_transcription_disc.wear": 0.05, "a_transcription_disc.crackle": 1.0,
                       "a_transcription_disc.swish": 0.4}),
        Variant("station-copy", "Station Copy", "Aired every week since the fall season: crazed and dull.",
                audio={"a_transcription_disc.wear": 0.85, "a_transcription_disc.crackle": 8.0,
                       "a_transcription_disc.swish": 0.9}),
    ],
))

register_preset(Preset(
    id="audio-8track-1974",
    name="8-Track Cartridge",
    family="audio",
    era="1974",
    desc="Stereo 8 in the dashboard: syrupy wow, the next program ghosting up from under the floor, and the ker-CHUNK that always lands mid-solo.",
    tags=("audio-only", "70s", "tape", "car"),
    audio=[
        ("a_tape_sat", {"drive": 2.2, "bump_db": 1.5}),
        ("a_8track", {"wow": 0.6, "crosstalk_db": -24.0, "program_clunk": True,
                      "clunk_at_s": 4.0, "hiss_db": -42.0}),
        ("a_speaker", {"device": "car_dash_1978", "strength": 0.55}),
    ],
    variants=[
        Variant("den", "Quad Deck In The Den", "The wood-grain home unit: steadier, quieter, still a cartridge.",
                audio={"a_8track.wow": 0.35, "a_8track.crosstalk_db": -32.0,
                       "a_8track.hiss_db": -46.0, "a_speaker.strength": 0.0}),
        Variant("worn-cart", "Hundredth Loop", "The pinch roller is going and the other program isn't shy anymore.",
                audio={"a_8track.wow": 0.9, "a_8track.crosstalk_db": -20.0,
                       "a_8track.hiss_db": -38.0}),
    ],
))

register_preset(Preset(
    id="audio-microcassette-1986",
    name="Microcassette Memo",
    family="audio",
    era="1986",
    desc="Note to self at 2.4 centimeters per second: the AGC gulping air between words, flutter on every syllable, hiss like rain on a tin roof.",
    tags=("audio-only", "80s", "tape", "dictation"),
    audio=[
        ("a_microcassette", {"flutter": 0.75, "agc": 0.85, "hiss_db": -37.0}),
        ("a_wow_flutter", {"wow_depth": 5.0, "flutter_depth": 0.0, "drift_long": 0.3}),
        ("a_tape_sat", {"drive": 2.2, "bump_db": 0.0, "hf_loss": 0.5}),
        ("a_speaker", {"device": "clock_radio_1988", "strength": 0.65}),
    ],
    variants=[
        Variant("dying-batteries", "Dying Batteries", "The motor loses the argument: everything slides flat.",
                audio={"a_wow_flutter.wow_depth": 18.0, "a_wow_flutter.speed_pct": -2.0,
                       "a_microcassette.flutter": 1.0}),
        Variant("fresh", "Fresh Tape, Good Desk", "A careful dictation on new cells.",
                audio={"a_microcassette.flutter": 0.5, "a_microcassette.agc": 0.6,
                       "a_microcassette.hiss_db": -42.0}),
    ],
))

register_preset(Preset(
    id="audio-shortwave-1962",
    name="Shortwave",
    family="audio",
    era="1962",
    desc="Somewhere east of the dial: the signal breathes away mid-word, RTTY chatters under a drifting whistle, lightning slaps from a storm a thousand miles off.",
    tags=("audio-only", "60s", "radio", "shortwave"),
    audio=[
        ("a_shortwave", {"hi_hz": 3000.0, "fade": 0.75, "het_db": -44.0,
                         "utility_qrm": 0.6, "sferics": 0.7, "static_db": -40.0}),
        ("a_speaker", {"device": "portable_radio_1975", "strength": 0.7}),
        ("a_hum", {"hz": "50", "level_db": -54.0}),
    ],
    variants=[
        Variant("good-night", "Good Propagation", "One of those nights the ionosphere cooperates: almost local.",
                audio={"a_shortwave.fade": 0.35, "a_shortwave.static_db": -50.0,
                       "a_shortwave.sferics": 0.3, "a_shortwave.utility_qrm": 0.25,
                       "a_shortwave.het_db": -54.0}),
        Variant("storm-front", "Storm Front", "The band is a weather report: crashes wall to wall.",
                audio={"a_shortwave.sferics": 1.0, "a_shortwave.static_db": -34.0,
                       "a_shortwave.fade": 0.9}),
    ],
))

register_preset(Preset(
    id="audio-cb-1977",
    name="CB Radio",
    family="audio",
    era="1977",
    desc="Breaker one-nine on a wound-up mic: clipped to a bark, squelch kshhh-chk on both ends, the next channel bleeding through the floor.",
    tags=("audio-only", "70s", "radio", "cb"),
    audio=[
        ("a_cb_radio", {"drive": 5.0, "squelch_tails": True, "bleed": 0.45,
                        "het_db": -48.0, "hiss_db": -40.0}),
        ("a_speaker", {"device": "transistor_pocket_1965", "strength": 0.5}),
    ],
    variants=[
        Variant("base-station", "Base Station", "The big antenna at home: cleaner carrier, calmer mic.",
                audio={"a_cb_radio.drive": 3.0, "a_cb_radio.bleed": 0.2,
                       "a_cb_radio.hiss_db": -46.0}),
        Variant("skip-land", "Skip Land", "The band is open and every county in America is on channel 19.",
                audio={"a_cb_radio.het_db": -38.0, "a_cb_radio.bleed": 0.7}),
    ],
))

register_preset(Preset(
    id="audio-atc-1969",
    name="Air Traffic Radio",
    family="audio",
    era="1969",
    desc="Cleared to land two-niner: a tight 300–2500 carrier, AGC riding every syllable up to the same calm level, empty hiss between transmissions.",
    tags=("audio-only", "60s", "radio", "aviation"),
    audio=[
        ("a_bandlimit", {"low_hz": 300.0, "high_hz": 2500.0, "order": 6}),
        ("a_agc", {"target_db": -16.0, "attack_ms": 15.0, "release_ms": 250.0, "amount": 1.0}),
        ("a_cb_radio", {"drive": 2.6, "squelch_tails": True, "bleed": 0.0,
                        "het_db": -66.0, "hiss_db": -46.0}),
    ],
    variants=[
        Variant("weak-signal", "Weak Readback", "A single-engine handheld from thirty miles out.",
                audio={"a_cb_radio.hiss_db": -38.0, "a_cb_radio.drive": 3.6}),
    ],
))

register_preset(Preset(
    id="audio-tube-console-1948",
    name="Tube Console",
    family="audio",
    era="1948",
    desc="The good radiogram after supper: tubes warm as toast, the transformer sagging on the loud notes, a soft 60-cycle heartbeat under the room.",
    tags=("audio-only", "40s", "tube", "hifi"),
    audio=[
        ("a_bandlimit", {"low_hz": 70.0, "high_hz": 7500.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_tube_amp", {"drive": 2.4, "sag": 0.6, "microphonics": 0.25, "hum_db": -46.0}),
        ("a_speaker", {"device": "tv_console_1972", "strength": 0.7, "cabinet_knock": 0.3}),
        ("a_room", {"size": 1.1, "decay_s": 0.5, "mix": 0.16, "damp": 0.6}),
    ],
    variants=[
        Variant("pushed", "Volume At Seven", "Fight night: the output stage gives up its dignity.",
                audio={"a_tube_amp.drive": 4.0, "a_tube_amp.sag": 0.85,
                       "a_tube_amp.microphonics": 0.45}),
    ],
))

register_preset(Preset(
    id="audio-dat-1994",
    name="DAT Dropout",
    family="audio",
    era="1994",
    desc="The demo master, digital and dying: pristine audio that freezes for a heartbeat, then a hard blink of nothing where the helical scan gave up.",
    tags=("audio-only", "90s", "digital", "tape"),
    audio=[
        ("a_compressor", {"ratio": 2.0}),
        ("a_dat_error", {"error_rate": 30.0, "mute_rate": 4.0}),
    ],
    variants=[
        Variant("first-signs", "First Signs", "One glitch you almost convince yourself you imagined.",
                audio={"a_dat_error.error_rate": 8.0, "a_dat_error.mute_rate": 0.5}),
        Variant("last-pass", "Last Pass", "The archive transfer you only get one shot at, failing during it.",
                audio={"a_dat_error.error_rate": 90.0, "a_dat_error.mute_rate": 12.0}),
    ],
))

register_preset(Preset(
    id="audio-cd-skip-1999",
    name="Discman Skip",
    family="audio",
    era="1999",
    desc="Anti-shock in name only: forty milliseconds of the chorus, six times in a row, then suddenly it's later in the song. The bus didn't care.",
    tags=("audio-only", "90s", "digital", "cd"),
    audio=[
        ("a_cd_skip", {"rate": 12.0}),
        ("a_speaker", {"device": "earbud_2005", "strength": 0.45}),
    ],
    variants=[
        Variant("pothole", "Pothole Season", "Every seam in the road, on the record.",
                audio={"a_cd_skip.rate": 25.0}),
        Variant("smooth-ride", "Smooth Ride", "Only the occasional stumble.",
                audio={"a_cd_skip.rate": 4.0}),
    ],
))

register_preset(Preset(
    id="audio-drive-thru-1988",
    name="Drive-Thru Speaker",
    family="audio",
    era="1988",
    desc="Would you like fries with the distortion? Phone-grade wiring into a gravel-lot squawk box, clipping on every consonant, the line buzzing behind it.",
    tags=("audio-only", "80s", "pa", "intercom"),
    audio=[
        ("a_telephone", {"era": "touchtone_1985", "line_noise_db": -42.0, "exchange_noise": 0.5}),
        ("a_distortion", {"type": "hard", "drive": 2.4}),
        ("a_pa_bullhorn", {"device": "drive_thru", "drive": 3.0}),
        ("a_hum", {"hz": "60", "level_db": -44.0, "buzz": 0.5}),
    ],
    variants=[
        Variant("feedback", "Mic Keyed Too Long", "The headset and the horn find each other.",
                audio={"a_pa_bullhorn.feedback_squeal": 2.0}),
        Variant("new-franchise", "New Franchise", "They actually fixed the speaker. Mostly.",
                audio={"a_distortion.drive": 1.5, "a_pa_bullhorn.drive": 2.0,
                       "a_telephone.line_noise_db": -48.0, "a_telephone.exchange_noise": 0.2}),
    ],
))

register_preset(Preset(
    id="audio-church-pa-1972",
    name="Church PA",
    family="audio",
    era="1972",
    desc="A column speaker bolted to limestone: horn midrange arriving twice, three seconds of stone tail on every pause, the amplifier humming through the sermon.",
    tags=("audio-only", "70s", "pa", "reverb"),
    audio=[
        ("a_bandlimit", {"low_hz": 130.0, "high_hz": 5500.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_pa_bullhorn", {"device": "pa_hall", "drive": 2.2}),
        ("a_room", {"mode": "chamber", "size": 1.8, "decay_s": 2.6, "mix": 0.38,
                    "damp": 0.55, "predelay_ms": 25.0}),
        ("a_hum", {"hz": "60", "level_db": -44.0, "buzz": 0.35}),
    ],
    variants=[
        Variant("cathedral", "Cathedral", "The words arrive; the meaning follows four seconds later.",
                audio={"a_room.decay_s": 4.2, "a_room.mix": 0.46, "a_room.size": 2.2}),
        Variant("chapel", "Side Chapel", "Small stone room, short honest tail.",
                audio={"a_room.decay_s": 1.2, "a_room.mix": 0.25, "a_room.size": 1.0}),
    ],
))

register_preset(Preset(
    id="audio-karaoke-1989",
    name="Karaoke Night",
    family="audio",
    era="1989",
    desc="Cassette backing track with the echo knob at maximum: every line answered by itself through a boingy spring and a boxy little PA.",
    tags=("audio-only", "80s", "tape", "pa"),
    audio=[
        ("a_bandlimit", {"low_hz": 70.0, "high_hz": 9000.0}),
        ("a_wow_flutter", {"wow_depth": 8.0, "flutter_depth": 6.0}),
        ("a_tape_sat", {"drive": 2.2, "bump_db": 2.0}),
        ("a_tape_hiss", {"level_db": -42.0, "type": "cassette"}),
        ("a_slap", {"delay_ms": 175.0, "gain_db": -7.0, "repeats": 3, "damp": 0.6}),
        ("a_room", {"mode": "spring_amp", "size": 0.9, "decay_s": 1.1, "mix": 0.4}),
        ("a_speaker", {"device": "boombox_1985", "strength": 0.55}),
    ],
    variants=[
        Variant("echo-eleven", "Echo At Eleven", "The host likes the knob. The knob likes the host.",
                audio={"a_slap.gain_db": -4.0, "a_slap.repeats": 5, "a_room.mix": 0.5}),
        Variant("last-song", "Last Song", "Echo eased off for the ballad. Almost dignified.",
                audio={"a_slap.gain_db": -12.0, "a_slap.repeats": 1, "a_room.mix": 0.22}),
    ],
))

register_preset(Preset(
    id="audio-subway-pa-1975",
    name="Subway PA",
    family="audio",
    era="1975",
    desc="The next-train announcement, shredded by horn speakers and flung down a tiled tube — arriving as reverb with a rumor of words inside.",
    tags=("audio-only", "70s", "pa", "transit"),
    audio=[
        ("a_bandlimit", {"low_hz": 300.0, "high_hz": 3400.0, "order": 5}),
        ("a_mono", {"amount": 1.0}),
        ("a_distortion", {"type": "hard", "drive": 2.4}),
        ("a_pa_bullhorn", {"device": "pa_hall", "drive": 3.2, "slap_ms": 300.0,
                           "slap_gain_db": -9.0, "slap_repeats": 2}),
        ("a_room", {"mode": "chamber", "size": 2.0, "decay_s": 3.2, "mix": 0.42,
                    "damp": 0.7, "predelay_ms": 40.0}),
        ("a_bed", {"bed": "air_handler_hall", "level_db": -27.0, "duck": 0.35}),
    ],
    variants=[
        Variant("far-platform", "Far Platform", "You hear the announcement happen to someone else.",
                audio={"a_room.mix": 0.55, "a_pa_bullhorn.drive": 4.0}),
        Variant("new-speakers", "Refurbished Station", "The 1975 hardware after its 1974 repair.",
                audio={"a_distortion.drive": 1.5, "a_room.mix": 0.3}),
    ],
))

register_preset(Preset(
    id="audio-hold-music-1993",
    name="On Hold",
    family="audio",
    era="1993",
    desc="Your call is important: a worn tape loop wandering flat and sharp under phone-band gauze, the exchange clicking through other people's afternoons.",
    tags=("audio-only", "90s", "phone", "tape"),
    audio=[
        ("a_wow_flutter", {"wow_depth": 10.0, "flutter_depth": 4.0, "drift_long": 0.8}),
        ("a_tape_sat", {"drive": 2.4, "hf_loss": 0.6}),
        ("a_tape_hiss", {"level_db": -42.0, "type": "cassette"}),
        ("a_telephone", {"era": "touchtone_1985", "line_noise_db": -44.0, "exchange_noise": 0.6}),
    ],
    variants=[
        Variant("hour-two", "Hour Two", "The loop is dying and so are you.",
                audio={"a_wow_flutter.drift_long": 1.0, "a_wow_flutter.wow_depth": 16.0,
                       "a_tape_sat.hf_loss": 0.8}),
        Variant("speakerphone", "On Speaker", "Both hands free to not work.",
                audio={"a_telephone.era": "speakerphone_1995"}),
    ],
))

register_preset(Preset(
    id="audio-dolby-mistrack-1979",
    name="Dolby Mistrack",
    family="audio",
    era="1979",
    desc="Recorded with Dolby, played without: quiet passages hiss bright, loud ones dull down — the whole top end breathes with the music, and the borrowed deck's EQ never matched anyway.",
    tags=("audio-only", "70s", "tape", "nerd"),
    audio=[
        ("a_bandlimit", {"low_hz": 40.0, "high_hz": 14000.0}),
        ("a_wow_flutter", {"wow_depth": 6.0, "flutter_depth": 4.0}),
        ("a_tape_sat", {"drive": 1.8, "bump_db": 2.0, "eq_era": "nab_mismatch",
                        "dolby_mistrack": 0.85}),
        ("a_tape_hiss", {"level_db": -48.0, "type": "cassette"}),
    ],
    variants=[
        Variant("worse-deck", "Even Wronger Deck", "IEC tape, NAB machine, no Dolby, no shame.",
                audio={"a_tape_sat.eq_era": "iec_mismatch", "a_tape_sat.dolby_mistrack": 1.0}),
        Variant("subtle", "Almost Right", "You'd only notice on headphones. You're on headphones.",
                audio={"a_tape_sat.dolby_mistrack": 0.45, "a_tape_sat.eq_era": "modern"}),
    ],
))
