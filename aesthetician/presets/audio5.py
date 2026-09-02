"""Audio-only archival presets, fifth wave: capture horns, consumer cassette
culture, sampler converters and the two-way radio band. Every chain here leaves
the picture untouched; the sound path is the whole preset.
"""

from ..engine.presets import Preset, Variant, register_preset


# nearest: audio-wax-cylinder-1905; differs: the horn sits at the capture end, the
# band closes to 250-2500, the wax is fresher, and it is a whole band in the room.
register_preset(Preset(
    id="audio-acoustic-horn-session-1910",
    name="Acoustic Horn Session",
    family="audio",
    era="1910",
    desc="A dance band crowded around one recording horn: 250 to 2500 Hz of brass honk, diaphragm overload on the loud bars and a wax cylinder cut live in the room.",
    tagline="Band in a horn, 250-2500 honk, wax cut",
    tags=("audio-only", "1910s", "acoustic", "cylinder"),
    keywords=("acoustic", "horn-recording", "1910s", "pre-electric", "band",
              "brass", "wax", "honk", "edison", "early-recording"),
    video=[],
    audio=[
        # the recording horn is the microphone: its resonance colours the source
        ("a_speaker", {"device": "gramophone_horn_1915", "strength": 1.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_distortion", {"type": "soft", "drive": 2.0, "tone": 0.1}),
        ("a_disc_medium", {"medium": "wax_cylinder_1905", "wear": 0.35,
                           "surface_db": -44.0, "impacts": 8.0, "wow_cents": 10.0}),
        # the reproducer band: it limits the surface roar as well as the band
        ("a_bandlimit", {"low_hz": 250.0, "high_hz": 2500.0, "order": 6}),
    ],
    variants=[
        Variant("fresh-master", "Fresh Master",
                "The cylinder comes off the machine and is played once, before the shaving man gets to it.",
                audio={"a_disc_medium.wear": 0.15, "a_disc_medium.surface_db": -52.0,
                       "a_disc_medium.impacts": 3.0}),
        Variant("worn-diamond-disc", "Worn Diamond Disc",
                "Years of a heavy reproducer riding the groove have polished the wax down to a roar.",
                audio={"a_disc_medium.wear": 0.7, "a_disc_medium.surface_db": -38.0,
                       "a_disc_medium.impacts": 20.0}),
    ],
))


# nearest: audio-shellac-1935; differs: the wider 1928 electrical band with
# condenser air on top, plus the orthophonic horn as the playback device.
register_preset(Preset(
    id="audio-electrical-78-1928",
    name="Electrical 78",
    family="audio",
    era="1928",
    desc="One of the first Western Electric electrical sides: a condenser stand at the band, 50 to 6000 Hz cut into shellac, light surface crackle and an orthophonic horn on the other end.",
    tagline="Western Electric width, condenser air, hiss",
    tags=("audio-only", "20s", "78", "shellac"),
    keywords=("electrical-recording", "78", "1920s", "western-electric", "condenser",
              "shellac", "wide-band", "jazz-age", "orthophonic", "dance-band"),
    video=[],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_historical_mic", {"profile": "carbon_1925", "amount": 0.4,
                              "proximity": 0.1, "overload": 0.12, "self_noise_db": -62.0}),
        ("a_vinyl_noise", {"crackle": 14.0, "crackle_db": -34.0, "pops": 3.0,
                           "pops_db": -22.0, "frying_db": -38.0, "rumble_db": -43.0,
                           "wear": 0.4, "warp_rpm": "78"}),
        ("a_vinyl_wow", {"rpm": "78", "depth_cents": 6.0}),
        # the reproducing chain: it bounds the shellac noise as well as the music
        ("a_bandlimit", {"low_hz": 50.0, "high_hz": 6000.0, "order": 4}),
        # dormant: the same pressing heard through a 1940 radio play
        ("a_am_radio", {"enabled": False, "hi_hz": 5000.0, "pump": 0.5,
                        "static_db": -50.0, "fade": 0.15, "whistle_db": -64.0}),
        ("a_tube_amp", {"drive": 1.5, "sag": 0.28, "hum_db": -60.0}),
        ("a_speaker", {"device": "gramophone_horn_1915", "strength": 0.4}),
    ],
    variants=[
        Variant("orthophonic-victrola", "Orthophonic Victrola",
                "The record goes back into the folded horn cabinet it was cut for, and loses the top of its band to it.",
                audio={"a_speaker.strength": 0.8, "a_bandlimit.low_hz": 60.0,
                       "a_bandlimit.high_hz": 5000.0}),
        Variant("radio-play", "On The Radio, 1940",
                "The same pressing goes out over a network transmitter and arrives with a carrier behind it.",
                audio={"a_am_radio.enabled": True}),
    ],
))


# nearest: audio-transcription-1938; differs: the whole aircheck path is here,
# studio chamber into an AM carrier and only then onto the lacquer.
register_preset(Preset(
    id="audio-radio-drama-aircheck-1938",
    name="Radio Drama Aircheck",
    family="audio",
    era="1938",
    desc="A studio play caught off the air on a home lacquer: a velocity ribbon into the echo chamber, an AM carrier with a whistle behind it, then once-per-revolution disc swish.",
    tagline="Ribbon studio, AM off-air onto lacquer, swish",
    tags=("audio-only", "30s", "radio", "lacquer"),
    keywords=("radio-drama", "aircheck", "1930s", "am", "lacquer", "ribbon",
              "theater-of-the-mind", "old-time-radio", "off-air", "network"),
    video=[],
    audio=[
        ("a_historical_mic", {"profile": "ribbon_1938", "amount": 0.7,
                              "proximity": 0.2, "overload": 0.14, "self_noise_db": -64.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_room", {"mode": "chamber", "size": 1.4, "decay_s": 0.8, "damp": 0.6,
                    "predelay_ms": 12.0, "mix": 0.15}),
        ("a_am_radio", {"hi_hz": 5000.0, "pump": 0.5, "static_db": -52.0,
                        "fade": 0.1, "whistle_db": -70.0}),
        ("a_transcription_disc", {"band": 1.0, "swish": 0.6, "crackle": 4.0, "wear": 0.35}),
        # the transcription turntable and console the disc comes back through
        ("a_bandlimit", {"low_hz": 50.0, "high_hz": 6000.0, "order": 4}),
    ],
    variants=[
        Variant("network-line-feed", "Network Line Feed",
                "The disc is cut from the wire feed instead of off the air, on a fresh blank.",
                audio={"a_am_radio.enabled": False, "a_transcription_disc.swish": 0.2}),
        Variant("distant-affiliate", "Distant Affiliate",
                "Someone recorded it three states away, and the carrier keeps wandering off under a heterodyne.",
                audio={"a_am_radio.fade": 0.4, "a_am_radio.static_db": -44.0,
                       "a_am_radio.whistle_db": -56.0}),
    ],
))


# nearest: audio-shellac-1935; differs: a quiet vinylite pressing with an 8 kHz
# band instead of shellac crackle, and a field phonograph rather than a console.
register_preset(Preset(
    id="audio-v-disc-1944",
    name="V-Disc",
    family="audio",
    era="1944",
    desc="A wartime pressing on 12-inch vinylite: ribbon studio capture, a wider 8 kHz band than shellac allowed, low pressing noise and a portable phonograph in a canteen.",
    tagline="Vinyl 12-inch, wartime studio, quiet press",
    tags=("audio-only", "40s", "vinyl", "wartime"),
    keywords=("v-disc", "1940s", "wartime", "vinyl", "12-inch", "armed-forces",
              "big-band", "pressing", "morale", "shellac-free"),
    video=[],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_historical_mic", {"profile": "ribbon_1938", "amount": 0.6,
                              "proximity": 0.18, "overload": 0.1, "self_noise_db": -66.0}),
        ("a_tube_amp", {"drive": 1.4, "sag": 0.3, "hum_db": -62.0}),
        ("a_vinyl_noise", {"crackle": 6.0, "crackle_db": -38.0, "pops": 2.0,
                           "pops_db": -26.0, "frying_db": -44.0, "rumble_db": -48.0,
                           "wear": 0.15, "warp_rpm": "78"}),
        ("a_vinyl_wow", {"rpm": "78", "depth_cents": 4.0}),
        # the vinylite band, measured at the pickup rather than at the cutter
        ("a_bandlimit", {"low_hz": 50.0, "high_hz": 8000.0, "order": 4}),
        ("a_speaker", {"device": "gramophone_horn_1915", "strength": 0.3}),
    ],
    variants=[
        Variant("canteen-phonograph", "Canteen Phonograph",
                "A crank portable on a mess table takes the bottom and the top off the pressing.",
                audio={"a_speaker.strength": 0.6, "a_bandlimit.low_hz": 80.0,
                       "a_bandlimit.high_hz": 6000.0}),
        Variant("well-played", "Played To Death",
                "One disc, one company, eighteen months: the groove is grey and every chorus ticks.",
                audio={"a_vinyl_noise.wear": 0.5, "a_vinyl_noise.crackle": 15.0,
                       "a_vinyl_noise.pops": 8.0}),
    ],
))


# nearest: audio-portable-reel-1965; differs: a mains home deck at 7.5 ips with
# quarter-track head crosstalk and print-through instead of a battery portable.
register_preset(Preset(
    id="audio-home-reel-quarter-track-1958",
    name="Home Quarter-Track Reel",
    family="audio",
    era="1958",
    desc="A living-room quarter-track reel at 7.5 ips: modest hiss, mild magnetic compression, a faint print-through echo and the adjacent track bleeding through the head stack.",
    tagline="7.5 ips home reel, mild hiss, track ghost",
    tags=("audio-only", "50s", "reel", "home-recording"),
    keywords=("reel-to-reel", "home-recording", "1950s", "quarter-track", "7.5ips",
              "living-room", "hobbyist", "tape", "hiss", "crosstalk"),
    video=[],
    audio=[
        # the deck's own record amplifier, ahead of the head it feeds
        ("a_tube_amp", {"drive": 1.5, "sag": 0.3, "hum_db": -62.0}),
        ("a_analog_dub", {"format": "reel_75ips", "generations": 1,
                          "alignment": 0.12, "compression": 0.25, "hiss_db": -54.0}),
        ("a_channel_aging", {"width": 0.9, "imbalance_db": -1.0, "crosstalk_db": -30.0,
                             "skew_us": 25.0, "phase_wander": 0.12, "mono_bass_hz": 90.0}),
        ("a_wow_flutter", {"wow_depth": 4.0, "flutter_depth": 3.0,
                           "cogging": 0.1, "cogging_hz": 60.0}),
        ("a_print_through", {"delay_s": 0.9, "pre_echo_db": -56.0,
                             "post_echo_db": -60.0, "layers": 1, "softness": 0.5}),
    ],
    variants=[
        Variant("economy-half-speed", "Economy At 3.75",
                "Two hours a reel instead of one, paid for in hiss and a duller top.",
                audio={"a_analog_dub.format": "reel_375ips", "a_analog_dub.hiss_db": -50.0,
                       "a_analog_dub.alignment": 0.3}),
        Variant("fresh-tape", "Fresh Tape",
                "A new reel on a just-aligned head stack, with the other pair of tracks blank.",
                audio={"a_analog_dub.hiss_db": -58.0, "a_channel_aging.crosstalk_db": -45.0}),
    ],
))


# nearest: audio-45-worn; differs: the cabinet and the tiled room are in the
# chain, and a sagging tube amplifier sits between the stylus and the grille.
register_preset(Preset(
    id="audio-jukebox-diner-1958",
    name="Diner Jukebox",
    family="audio",
    era="1958",
    desc="A 45 that has played all summer inside a lit cabinet: groove wear and crackle, tube amplifier sag, the jukebox box boom and a tiled room throwing it back.",
    tagline="Worn 45, jukebox cabinet boom, tile room",
    tags=("audio-only", "50s", "45", "jukebox"),
    keywords=("jukebox", "diner", "1950s", "45", "rock-and-roll", "cabinet",
              "wurlitzer", "malt-shop", "boom", "tile"),
    video=[],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_vinyl_noise", {"crackle": 8.0, "crackle_db": -36.0, "pops": 4.0,
                           "pops_db": -20.0, "frying_db": -50.0, "rumble_db": -46.0,
                           "wear": 0.35, "warp_rpm": "45"}),
        ("a_vinyl_wow", {"rpm": "45", "depth_cents": 6.0}),
        ("a_tube_amp", {"drive": 2.2, "sag": 0.5, "microphonics": 0.1, "hum_db": -56.0}),
        ("a_speaker", {"device": "jukebox_1955", "strength": 1.0, "cabinet_knock": 0.5}),
        ("a_room", {"mode": "room", "size": 1.6, "decay_s": 0.7, "damp": 0.3,
                    "predelay_ms": 10.0, "mix": 0.25}),
    ],
    variants=[
        Variant("fresh-45", "Fresh 45",
                "A new single loaded this morning, before three hundred plays flatten the groove.",
                audio={"a_vinyl_noise.wear": 0.1, "a_vinyl_noise.crackle": 2.0}),
        Variant("empty-diner-night", "Empty At Closing",
                "Chairs on the tables, nobody in the booths, and the room answering every note.",
                audio={"a_room.mix": 0.4, "a_room.decay_s": 1.0}),
    ],
))


# nearest: audio-am-1948; differs: a two-inch pocket speaker, thumbwheel tuning
# drift and the next station bleeding in, rather than a mantel console.
register_preset(Preset(
    id="audio-transistor-pocket-radio-1965",
    name="Pocket Transistor Radio",
    family="audio",
    era="1965",
    desc="A shirt-pocket six-transistor set at the shore: 4.2 kHz of AM, static breathing under the top forty, the thumbwheel drifting off station and a two-inch speaker.",
    tagline="Tiny speaker AM, beach static, dial drift",
    tags=("audio-only", "60s", "radio", "am", "transistor"),
    keywords=("transistor", "pocket-radio", "1960s", "am", "tiny-speaker", "beach",
              "top-40", "drift", "battery", "teenager"),
    video=[],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_am_radio", {"hi_hz": 4200.0, "pump": 0.6, "static_db": -46.0, "fade": 0.15,
                        "whistle_db": -62.0, "tune_drift": 2.0, "adjacent_channel": 0.2}),
        # dormant: the output stage starts clipping when the 9-volt goes flat
        ("a_distortion", {"enabled": False, "type": "asym", "drive": 2.6, "tone": 0.2}),
        ("a_speaker", {"device": "transistor_pocket_1965", "strength": 1.0}),
    ],
    variants=[
        Variant("fresh-battery", "Fresh Battery",
                "A new nine-volt, a strong local signal and a hand steady on the thumbwheel.",
                audio={"a_am_radio.static_db": -52.0, "a_am_radio.tune_drift": 0.0,
                       "a_am_radio.adjacent_channel": 0.0}),
        Variant("dying-battery", "Dying Battery",
                "The last of the cell: the output stage clips on every chorus and the noise comes up to meet it.",
                audio={"a_distortion.enabled": True, "a_am_radio.static_db": -40.0,
                       "a_am_radio.pump": 0.9}),
    ],
))


# nearest: audio-transistor-pocket-radio-1965; differs: a dash cone with cabinet
# knock, ignition buzz and overpass fades instead of a pocket speaker and drift.
register_preset(Preset(
    id="audio-car-am-radio-1968",
    name="Car AM Radio",
    family="audio",
    era="1968",
    desc="The dashboard set on a night drive: compressed AM with the ignition and alternator buzzing behind it, the signal dropping under an overpass, one paper cone in the dash.",
    tagline="Dash speaker, ignition buzz, tunnel fade",
    tags=("audio-only", "60s", "radio", "am", "car"),
    keywords=("car-radio", "dashboard", "1960s", "am", "ignition", "tunnel",
              "road", "drive", "muscle-car", "night-drive"),
    video=[],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_am_radio", {"hi_hz": 4800.0, "pump": 0.5, "static_db": -50.0, "fade": 0.2,
                        "whistle_db": -68.0, "tune_drift": 0.5, "power_line": 0.3}),
        ("a_speaker", {"device": "car_dash_1978", "strength": 1.0, "cabinet_knock": 0.3}),
        ("a_hum", {"hz": "60", "level_db": -50.0, "buzz": 0.6}),
    ],
    variants=[
        Variant("highway-clear", "Open Highway",
                "Flat country, a strong transmitter and an engine that has just been tuned.",
                audio={"a_am_radio.fade": 0.05, "a_am_radio.static_db": -56.0,
                       "a_hum.level_db": -62.0}),
        Variant("under-the-bridge", "Under The Bridge",
                "Concrete overhead takes the station away and hands back a lapful of noise.",
                audio={"a_am_radio.fade": 0.6, "a_am_radio.static_db": -42.0}),
    ],
))


# nearest: audio-cassette-1984; differs: chrome tape, a Dolby switch left off so
# the top is bright rather than azimuth-dulled, and headphone-level noise.
register_preset(Preset(
    id="audio-walkman-chrome-1983",
    name="Walkman Chrome Tape",
    family="audio",
    era="1983",
    desc="A Type II chrome cassette in a personal stereo: bright extended top with the Dolby switch left off, a small head bump, light capstan flutter and headphone-level hiss.",
    tagline="Type II chrome, Dolby-off top, headphone hiss",
    tags=("audio-only", "80s", "cassette", "walkman"),
    keywords=("walkman", "1980s", "cassette", "chrome", "type-ii", "headphones",
              "dolby", "personal-stereo", "mixtape-era", "jog"),
    video=[],
    audio=[
        ("a_bandlimit", {"low_hz": 30.0, "high_hz": 15000.0, "order": 4}),
        ("a_analog_dub", {"format": "cassette", "generations": 1,
                          "alignment": 0.1, "compression": 0.2, "hiss_db": -50.0}),
        ("a_tape_sat", {"drive": 1.8, "bump_db": 1.5, "hf_loss": 0.22,
                        "eq_era": "modern", "dolby_mistrack": 0.3}),
        ("a_wow_flutter", {"wow_depth": 5.0, "flutter_depth": 4.0,
                           "cogging": 0.12, "cogging_hz": 50.0}),
        ("a_channel_aging", {"width": 1.0, "imbalance_db": -0.8, "crosstalk_db": -40.0,
                             "skew_us": 20.0, "phase_wander": 0.1, "mono_bass_hz": 90.0}),
    ],
    variants=[
        Variant("dolby-on", "Dolby Switched On",
                "The switch is where it should be, so the top sits flat and the floor drops away.",
                audio={"a_tape_sat.dolby_mistrack": 0.0, "a_analog_dub.hiss_db": -58.0}),
        Variant("worn-mechanism", "Worn Mechanism",
                "Two years in a pocket: the belt has stretched and one channel is quietly losing.",
                audio={"a_wow_flutter.wow_depth": 12.0, "a_wow_flutter.flutter_depth": 8.0,
                       "a_channel_aging.imbalance_db": -2.0}),
    ],
))


# nearest: audio-dolby-mistrack-1979; differs: C-type over-decoding, which goes
# dull and pumps upward, against B-type under-decoding, which goes bright.
register_preset(Preset(
    id="audio-dolby-c-cassette-1986",
    name="Dolby C Cassette",
    family="audio",
    era="1986",
    desc="A Dolby C recording decoded on the wrong deck: encoder and decoder disagree by several decibels, so quiet passages go dull and the top end pumps above a very low tape floor.",
    tagline="Over-decoded dull, pumping top, quiet floor",
    tags=("audio-only", "80s", "cassette", "dolby"),
    keywords=("dolby-c", "cassette", "1980s", "noise-reduction", "over-decoded",
              "pumping", "dull", "hi-fi-deck", "home-taping", "compander"),
    video=[],
    audio=[
        ("a_bandlimit", {"low_hz": 30.0, "high_hz": 14000.0, "order": 4}),
        ("a_analog_dub", {"format": "cassette", "generations": 1,
                          "alignment": 0.15, "compression": 0.3, "hiss_db": -66.0}),
        # C-type buys about 20 dB, so the floor sits far below the house range
        ("a_noise_reduction", {"system": "dolby_c", "decode_error": 0.55,
                               "threshold_db": -34.0, "pumping": 0.35, "hiss_db": -68.0}),
        ("a_wow_flutter", {"wow_depth": 4.0, "flutter_depth": 3.0}),
    ],
    variants=[
        Variant("matched-decks", "Matched Decks",
                "Recorded and played on the same calibrated machine, which is the only way C ever worked.",
                audio={"a_noise_reduction.decode_error": 0.05,
                       "a_noise_reduction.pumping": 0.05}),
        Variant("dbx-on-dolby-deck", "dbx Tape On A Dolby Deck",
                "A two-to-one companded tape decoded by the wrong system entirely, breathing on every entry.",
                audio={"a_noise_reduction.system": "dbx",
                       "a_noise_reduction.decode_error": -0.6,
                       "a_noise_reduction.pumping": 0.6}),
    ],
))


# nearest: audio-walkman-chrome-1983; differs: saturation-led rather than
# transport-led, with an 18 kHz top and a floor thirteen decibels lower.
register_preset(Preset(
    id="audio-metal-tape-hot-1988",
    name="Metal Tape, Hot Levels",
    family="audio",
    era="1988",
    desc="A Type IV metal cassette recorded past the meters: magnetic saturation on every peak, an 18 kHz top edge, almost no head-bump loss and the lowest noise floor cassette ever managed.",
    tagline="Type IV saturation, bright top, +6 dB peaks",
    tags=("audio-only", "80s", "cassette", "hifi"),
    keywords=("metal-tape", "type-iv", "1980s", "hot-levels", "saturation",
              "bright", "hi-fi", "cassette", "mastering", "headroom"),
    video=[],
    audio=[
        ("a_bandlimit", {"low_hz": 25.0, "high_hz": 18000.0, "order": 4}),
        ("a_analog_dub", {"format": "cassette", "generations": 1,
                          "alignment": 0.05, "compression": 0.4, "hiss_db": -63.0}),
        ("a_tape_sat", {"drive": 4.8, "bump_db": 2.0, "hf_loss": 0.02,
                        "eq_era": "modern"}),
        ("a_wow_flutter", {"wow_depth": 3.0, "flutter_depth": 2.0}),
    ],
    variants=[
        Variant("conservative-levels", "Conservative Levels",
                "The needles stay out of the red and the tape stops adding anything of its own.",
                audio={"a_tape_sat.drive": 1.8}),
        Variant("smashed", "Smashed",
                "Recorded at plus eight because metal can take it, until the cymbals stop being cymbals.",
                audio={"a_tape_sat.drive": 7.0, "a_tape_sat.hf_loss": 0.2}),
    ],
))


# nearest: audio-8track-1974; differs: a chewed cassette with azimuth flips and
# oxide dropouts instead of a cartridge with program clunks and crosstalk.
register_preset(Preset(
    id="audio-car-cassette-chewed-1985",
    name="Chewed Car Cassette",
    family="audio",
    era="1985",
    desc="A cassette the auto-reverse deck has eaten twice: crinkled oxide dropouts, azimuth flipping from side to side, a dragging capstan and the dash cone underneath it.",
    tagline="Azimuth flip, crinkled dropouts, dash boom",
    tags=("audio-only", "80s", "cassette", "car"),
    keywords=("car-cassette", "1980s", "auto-reverse", "chewed", "azimuth", "dropouts",
              "dashboard", "road-trip", "tape-eater", "wow"),
    video=[],
    audio=[
        ("a_analog_dub", {"format": "cassette", "generations": 2,
                          "alignment": 0.45, "compression": 0.3, "hiss_db": -50.0}),
        ("a_tape_dropouts", {"rate": 18.0, "depth_db": 28.0, "azimuth": 0.5}),
        ("a_wow_flutter", {"wow_depth": 12.0, "flutter_depth": 7.0,
                           "drift_long": 0.4, "speed_pct": -1.0}),
        ("a_speaker", {"device": "car_dash_1978", "strength": 1.0, "cabinet_knock": 0.3}),
        ("a_hum", {"hz": "60", "level_db": -56.0, "buzz": 0.4}),
    ],
    variants=[
        Variant("good-side", "The Good Side",
                "Side one never went through the pinch roller, so it only sounds like a car.",
                audio={"a_tape_dropouts.rate": 3.0, "a_tape_dropouts.azimuth": 0.15,
                       "a_wow_flutter.wow_depth": 5.0}),
        Variant("eaten-then-rewound", "Eaten, Then Rewound With A Pencil",
                "Forty feet of tape came out of the deck and went back in with a crease every turn.",
                audio={"a_tape_dropouts.rate": 40.0, "a_tape_dropouts.azimuth": 0.8,
                       "a_wow_flutter.wow_depth": 20.0}),
    ],
))


# nearest: audio-boombox-dub-1983; differs: the source is an FM broadcast, not a
# second deck, and the damage is pause-button gaps rather than three generations.
register_preset(Preset(
    id="audio-radio-mixtape-1989",
    name="Radio-Recorded Mixtape",
    family="audio",
    era="1989",
    desc="Top forty taped off the FM dial: broadcast compression and a flutter of multipath, Type I hiss, the pause button clipping the ends off songs, played back on a boombox.",
    tagline="FM off-air to Type I, pause-button gaps",
    tags=("audio-only", "80s", "cassette", "fm", "mixtape"),
    keywords=("mixtape", "1980s", "radio", "fm", "off-air", "cassette", "dj",
              "pause-button", "home-taping", "top-40"),
    video=[],
    audio=[
        ("a_fm_radio", {"hiss_db": -56.0, "comp": 0.7, "multipath": 1.0}),
        ("a_analog_dub", {"format": "cassette", "generations": 1,
                          "alignment": 0.2, "compression": 0.35, "hiss_db": -50.0}),
        ("a_tape_sat", {"drive": 2.0, "bump_db": 2.0, "hf_loss": 0.3}),
        ("a_wow_flutter", {"wow_depth": 6.0, "flutter_depth": 4.0, "start_wobble": True}),
        ("a_tape_dropouts", {"rate": 4.0, "depth_db": 12.0, "azimuth": 0.1}),
        ("a_speaker", {"device": "boombox_1985", "strength": 0.6}),
    ],
    variants=[
        Variant("clean-line-dub", "Line Dub",
                "Somebody with a cable took it off the station feed instead, and the FM stage never happens.",
                audio={"a_fm_radio.enabled": False, "a_analog_dub.hiss_db": -56.0}),
        Variant("third-copy", "Third Copy For A Friend",
                "Copied twice more at the back of a study hall, each pass shaving another kilohertz off.",
                audio={"a_analog_dub.generations": 3, "a_analog_dub.alignment": 0.5}),
    ],
))


# nearest: audio-cassette-1984; differs: a duplicating-plant tape, dull from
# high-speed loading and loud with print-through, not a home recording.
register_preset(Preset(
    id="audio-prerecorded-cassette-1980",
    name="Prerecorded Cassette",
    family="audio",
    era="1980",
    desc="A commercial album cassette run off at sixty-four times speed: dull duplicated top end, high hiss for a factory tape and print-through announcing each entry a second early.",
    tagline="High-speed dup, dull top, print-through echo",
    tags=("audio-only", "80s", "cassette", "album"),
    keywords=("prerecorded", "cassette", "1980s", "high-speed-dup", "dull",
              "print-through", "record-store", "ferric", "album-tape", "budget"),
    video=[],
    audio=[
        ("a_bandlimit", {"low_hz": 40.0, "high_hz": 11000.0, "order": 4}),
        ("a_analog_dub", {"format": "cassette", "generations": 2,
                          "alignment": 0.3, "compression": 0.35, "hiss_db": -49.0}),
        ("a_tape_sat", {"drive": 2.2, "bump_db": 2.0, "hf_loss": 0.62}),
        ("a_print_through", {"delay_s": 1.2, "pre_echo_db": -46.0,
                             "post_echo_db": -52.0, "layers": 2, "softness": 0.6}),
        ("a_wow_flutter", {"wow_depth": 5.0, "flutter_depth": 4.0}),
    ],
    variants=[
        Variant("chrome-xdr", "Chrome XDR, 1988",
                "The label finally pays for chrome stock and a slower loader, and the top comes back.",
                audio={"a_tape_sat.hf_loss": 0.2, "a_analog_dub.hiss_db": -55.0,
                       "a_print_through.pre_echo_db": -56.0}),
        Variant("bargain-bin-ferric", "Bargain Bin Ferric",
                "Two ninety-nine at a truck stop, wound tight on the cheapest oxide going.",
                audio={"a_tape_sat.hf_loss": 0.82, "a_analog_dub.hiss_db": -44.0,
                       "a_print_through.pre_echo_db": -40.0}),
    ],
))


# nearest: audio-mp3-2002; differs: a cleaner mid-rate perceptual swirl on a
# silent digital floor with a shock-buffer skip, heard on stock earbuds.
register_preset(Preset(
    id="audio-minidisc-lp2-1998",
    name="MiniDisc LP2",
    family="audio",
    era="1998",
    desc="A MiniDisc filled up in LP2 mode: perceptual coding swirl on cymbals at half the disc's usual rate, a silent floor between tracks, one shock-buffer skip and stock earbuds.",
    tagline="ATRAC-style swirl at 132 kbps, clean floor",
    tags=("audio-only", "90s", "minidisc", "digital"),
    keywords=("minidisc", "1990s", "atrac", "lp2", "portable", "digital",
              "swirl", "clean", "net-md", "sony"),
    video=[],
    audio=[
        ("a_bandlimit", {"low_hz": 20.0, "high_hz": 16000.0, "order": 4}),
        ("a_codec_mp3", {"kbps": "96", "mono": False}),
        ("a_digital_glitch", {"stutter_rate": 0.0, "mute_rate": 0.5, "crackle_rate": 0.0}),
        ("a_speaker", {"device": "earbud_2005", "strength": 0.4}),
    ],
    variants=[
        Variant("sp-mode", "SP Mode",
                "Seventy-four minutes at the disc's own rate, and the coder stops showing its work.",
                audio={"a_codec_mp3.kbps": "128", "a_digital_glitch.mute_rate": 0.0}),
        Variant("lp4", "LP4, Four Hours",
                "Two hundred and ninety minutes on one disc, joint-coded down to a wash.",
                audio={"a_codec_mp3.kbps": "48", "a_codec_mp3.mono": True}),
    ],
))


# nearest: none (no sampler-converter preset exists); closest in spirit is
# audio-mp3-2002, which is a lossy codec rather than a converter.
register_preset(Preset(
    id="audio-sampler-12bit-1988",
    name="12-Bit Sampler",
    family="audio",
    era="1988",
    desc="Records sampled into a 12-bit drum machine at 26 kHz: quantization crunch under every tail, a hard 11 kHz output filter, a low-mid bump and a compressor squeezing the knock.",
    tagline="26 kHz 12-bit crunch, filtered top, knock",
    tags=("audio-only", "80s", "sampler", "digital"),
    keywords=("sampler", "12-bit", "sp-1200", "1980s", "hip-hop", "26khz",
              "drum-machine", "boom-bap", "lo-fi-beats"),
    video=[],
    audio=[
        ("a_bitcrush", {"bits": 12, "dither": False, "sr_hz": 26040.0,
                        "antialias": False, "mix": 1.0}),
        ("a_tape_sat", {"drive": 2.0, "bump_db": 3.5, "hf_loss": 0.2}),
        ("a_compressor", {"threshold_db": -18.0, "ratio": 4.0, "attack_ms": 2.0,
                          "release_ms": 120.0, "makeup_db": 2.0}),
        # the machine's output reconstruction filter: last analog stage, hard top
        ("a_bandlimit", {"low_hz": 30.0, "high_hz": 11000.0, "order": 6}),
    ],
    variants=[
        Variant("pitched-down", "Pitched Down To 45",
                "The same record sampled slow and played back slower, dragging the converter down with it.",
                audio={"a_bitcrush.sr_hz": 18000.0, "a_bandlimit.high_hz": 8000.0}),
        Variant("clean-sixteen-bit", "Clean 16-Bit",
                "The same chain on a proper converter, so only the compressor and the bump remain.",
                audio={"a_bitcrush.bits": 16, "a_bitcrush.sr_hz": 44100.0}),
    ],
))


# nearest: audio-sampler-12bit-1988; differs: four fewer bits and no low-mid
# bump, so the grit is aliasing on top rather than crunch underneath.
register_preset(Preset(
    id="audio-sampler-8bit-1986",
    name="8-Bit Sampler",
    family="audio",
    era="1986",
    desc="An 8-bit keyboard sampler at 22 kHz with no anti-alias filter: aliasing grit folded back over the program, coarse quantization on every decay and a 10 kHz ceiling.",
    tagline="8-bit aliasing grit, 22 kHz, orchestra hit",
    tags=("audio-only", "80s", "sampler", "keyboard"),
    keywords=("sampler", "8-bit", "1980s", "fairlight", "mirage", "aliasing",
              "orchestra-hit", "grit", "synth-pop", "lo-fi"),
    video=[],
    audio=[
        ("a_bitcrush", {"bits": 8, "dither": False, "sr_hz": 22050.0,
                        "antialias": False, "mix": 1.0}),
        ("a_compressor", {"threshold_db": -20.0, "ratio": 3.0, "attack_ms": 5.0,
                          "release_ms": 150.0}),
        # output reconstruction filter, well below the converter's own Nyquist
        ("a_bandlimit", {"low_hz": 30.0, "high_hz": 10000.0, "order": 6}),
    ],
    variants=[
        Variant("mirage-33k", "33 kHz Upper Octave",
                "The instrument's short-sample rate: brighter, and the aliasing climbs out of the way.",
                audio={"a_bitcrush.sr_hz": 33000.0, "a_bandlimit.high_hz": 13000.0}),
        Variant("ensoniq-16k", "16 kHz Long Sample",
                "Fitting the whole break into memory costs half the bandwidth and doubles the grit.",
                audio={"a_bitcrush.sr_hz": 16000.0, "a_bandlimit.high_hz": 7000.0}),
    ],
))


# nearest: audio-sampler-8bit-1986; differs: the converter runs at 11 kHz and
# leaves through a television speaker with intercarrier buzz on it.
register_preset(Preset(
    id="audio-console-pcm-1991",
    name="Console Sample Audio",
    family="audio",
    era="1991",
    desc="Cartridge audio from a 16-bit console: 8-bit PCM samples clocked at 11 kHz, out through a small television speaker with buzz riding the sound subcarrier.",
    tagline="8-bit PCM at 11 kHz, TV speaker, ROM crunch",
    tags=("audio-only", "90s", "console", "digital"),
    keywords=("console", "16-bit-era", "1990s", "pcm", "8-bit-samples", "tv-speaker",
              "snes", "genesis", "video-game", "chiptune-adjacent"),
    video=[],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_bitcrush", {"bits": 8, "dither": False, "sr_hz": 11025.0,
                        "antialias": False, "mix": 1.0}),
        ("a_bandlimit", {"low_hz": 60.0, "high_hz": 5500.0, "order": 4}),
        ("a_tv_sound", {"hz": "60", "buzz_db": -60.0, "hum_db": -66.0, "comp": 0.3}),
        ("a_speaker", {"device": "tv_mono_1985", "strength": 0.8}),
        # dormant: the RF modulator box that came in the console carton
        ("a_hum", {"enabled": False, "hz": "60", "level_db": -52.0, "buzz": 0.4}),
    ],
    variants=[
        Variant("rf-adapter", "RF Adapter On Channel 3",
                "The console goes in through the aerial screws, and the whole set starts buzzing along.",
                audio={"a_tv_sound.buzz_db": -48.0, "a_hum.enabled": True}),
        Variant("av-cable", "Stereo AV Cable",
                "Somebody bought the proper lead: two channels, no subcarrier and a much politer speaker.",
                audio={"a_mono.amount": 0.0, "a_speaker.strength": 0.5,
                       "a_tv_sound.buzz_db": -70.0}),
    ],
))


# nearest: audio-answering-machine-1988; differs: a cellular speech coder rather
# than microcassette tape, and a plastic handset instead of a clock radio.
register_preset(Preset(
    id="audio-cellphone-voicemail-2004",
    name="Cellphone Voicemail",
    family="audio",
    era="2004",
    desc="A message left from one bar of signal: a 2003 handset into a 4.75 kbps speech coder, vowels turning robotic, line noise behind them and a plastic earpiece on playback.",
    tagline="AMR one-bar robot, sidetone tick, handset tin",
    tags=("audio-only", "2000s", "phone", "voicemail"),
    keywords=("voicemail", "cellphone", "2000s", "amr", "one-bar", "robotic",
              "handset", "message", "missed-call", "flip-phone"),
    video=[],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_telephone", {"era": "cell_2003", "line_noise_db": -46.0,
                         "sidetone_click": True, "exchange_noise": 0.2}),
        ("a_codec_speech", {"codec": "amr_475"}),
        ("a_speaker", {"device": "cellphone_2008", "strength": 0.9}),
    ],
    variants=[
        Variant("full-bars", "Full Bars",
                "The caller steps outside, the coder picks its highest rate and the words come back.",
                audio={"a_codec_speech.codec": "amr_122", "a_speaker.strength": 0.6}),
        Variant("gsm-2001", "GSM, 2001",
                "An older network and an older codec, warbling under a noisier line.",
                audio={"a_codec_speech.codec": "gsm", "a_telephone.line_noise_db": -40.0}),
    ],
))


# nearest: audio-cellphone-voicemail-2004; differs: packet loss and ADPCM grit
# over a home connection, arriving at a laptop rather than a handset.
register_preset(Preset(
    id="audio-voip-call-2006",
    name="VoIP Call",
    family="audio",
    era="2006",
    desc="An internet call over a home connection: 24 kbps ADPCM grit inside a 200 to 3600 Hz band, packets vanishing mid-word and a laptop speaker at the far end.",
    tagline="Packet-loss holes, G.726 grit, laptop speaker",
    tags=("audio-only", "2000s", "voip", "codec"),
    keywords=("voip", "skype", "2000s", "packet-loss", "g726", "laptop",
              "internet-call", "dropouts", "headset", "long-distance"),
    video=[],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_bandlimit", {"low_hz": 200.0, "high_hz": 3600.0, "order": 4}),
        ("a_codec_speech", {"codec": "g726_24"}),
        ("a_digital_glitch", {"stutter_rate": 3.0, "mute_rate": 13.0, "crackle_rate": 7.0}),
        ("a_speaker", {"device": "laptop_2006", "strength": 0.8}),
    ],
    variants=[
        Variant("good-broadband", "Good Broadband",
                "Cable at both ends: the coder runs at its top rate and almost nothing goes missing.",
                audio={"a_codec_speech.codec": "g726_40", "a_digital_glitch.mute_rate": 1.0,
                       "a_digital_glitch.stutter_rate": 0.0}),
        Variant("dial-up", "Over Dial-Up",
                "A modem trying to carry a conversation: half the syllables never arrive at all.",
                audio={"a_codec_speech.codec": "g726_16", "a_digital_glitch.mute_rate": 25.0,
                       "a_digital_glitch.stutter_rate": 8.0}),
    ],
))


# nearest: audio-cb-1977; differs: a low-power handheld with no channel bleed and
# far less drive, into a one-inch speaker rather than a wound-up mobile rig.
register_preset(Preset(
    id="audio-walkie-talkie-1990",
    name="Walkie-Talkie",
    family="audio",
    era="1990",
    desc="A pair of handheld two-way sets across a backyard: 300 to 3000 Hz of FM speech, a squelch tail on every key release and a one-inch speaker behind a plastic grille.",
    tagline="300-3000 FM squelch, key clicks, toy hiss",
    tags=("audio-only", "90s", "radio", "two-way"),
    keywords=("walkie-talkie", "1990s", "two-way", "squelch", "handheld", "frs",
              "toy", "kids", "backyard", "over"),
    video=[],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_bandlimit", {"low_hz": 300.0, "high_hz": 3000.0, "order": 6}),
        ("a_cb_radio", {"drive": 2.5, "squelch_tails": True, "bleed": 0.05,
                        "het_db": -70.0, "hiss_db": -40.0}),
        # dormant: the other set walks past the end of the block
        ("a_am_radio", {"enabled": False, "hi_hz": 3000.0, "pump": 0.4,
                        "static_db": -44.0, "fade": 0.6, "whistle_db": -70.0}),
        ("a_speaker", {"device": "transistor_pocket_1965", "strength": 0.9}),
    ],
    variants=[
        Variant("frs-clean", "FRS Handheld, 2005",
                "A licensed band and fifteen years of better parts: quieter, cleaner, still tiny.",
                audio={"a_cb_radio.drive": 1.5, "a_cb_radio.hiss_db": -48.0}),
        Variant("out-of-range", "Out Of Range",
                "One of them has walked too far, and the signal starts breathing in and out of the noise.",
                audio={"a_cb_radio.hiss_db": -32.0, "a_am_radio.enabled": True}),
    ],
))


# nearest: audio-atc-1969; differs: scanner AGC pumping hard between calls, a
# neighbouring channel bleeding in, and a bedside clock-radio speaker.
register_preset(Preset(
    id="audio-police-scanner-1985",
    name="Police Scanner",
    family="audio",
    era="1985",
    desc="A dispatch band scanner on a bedside table: narrow transmissions flattened by scanner AGC, squelch bursts between calls, adjacent traffic leaking and a clock-radio speaker.",
    tagline="Dispatch band, squelch pops, clock radio",
    tags=("audio-only", "80s", "radio", "scanner"),
    keywords=("police-scanner", "dispatch", "1980s", "scanner", "squelch", "two-way",
              "radio-hobby", "night", "chatter", "bearcat"),
    video=[],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_bandlimit", {"low_hz": 300.0, "high_hz": 3200.0, "order": 6}),
        ("a_cb_radio", {"drive": 2.0, "squelch_tails": True, "bleed": 0.1,
                        "het_db": -60.0, "hiss_db": -47.0}),
        ("a_agc", {"target_db": -17.0, "max_gain_db": 11.0, "attack_ms": 5.0,
                   "release_ms": 300.0, "amount": 0.9}),
        ("a_speaker", {"device": "clock_radio_1988", "strength": 0.9}),
    ],
    variants=[
        Variant("weak-repeater", "Weak Repeater",
                "The far side of the county comes in under the noise with a carrier whistling on it.",
                audio={"a_cb_radio.hiss_db": -38.0, "a_cb_radio.het_db": -48.0}),
        Variant("base-station-speaker", "Base Station Speaker",
                "The scanner is patched into a bigger extension cabinet on a shelf in the garage.",
                audio={"a_speaker.device": "portable_radio_1975", "a_speaker.strength": 0.7}),
    ],
))


# nearest: audio-cb-1977; differs: no channel bleed at all, an alternator buzz
# under everything and a horn speaker bolted in a cockpit.
register_preset(Preset(
    id="audio-marine-vhf-1975",
    name="Marine VHF Radio",
    family="audio",
    era="1975",
    desc="Channel 16 from a cockpit set: narrow FM speech with the alternator buzzing under it, a horn speaker over the transom and static crashes off the weather.",
    tagline="Salt-air FM, engine buzz, cockpit speaker",
    tags=("audio-only", "70s", "radio", "marine"),
    keywords=("marine", "vhf", "1970s", "boat", "coast-guard", "cockpit",
              "engine", "static", "harbor", "mayday"),
    video=[],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_bandlimit", {"low_hz": 300.0, "high_hz": 3000.0, "order": 5}),
        ("a_cb_radio", {"drive": 2.2, "squelch_tails": True, "bleed": 0.0,
                        "het_db": -58.0, "hiss_db": -42.0}),
        # dormant: the weather comes in and the band fills with lightning
        ("a_shortwave", {"enabled": False, "hi_hz": 3000.0, "fade": 0.1,
                         "het_db": -72.0, "utility_qrm": 0.0, "sferics": 0.7,
                         "static_db": -60.0}),
        ("a_speaker", {"device": "intercom_horn_1950", "strength": 0.8}),
        ("a_hum", {"hz": "60", "level_db": -50.0, "buzz": 0.7}),
    ],
    variants=[
        Variant("calm-harbor", "Calm Harbor",
                "Engine off, tied up, and the set finally sounds like a radio instead of a machine.",
                audio={"a_hum.level_db": -62.0, "a_cb_radio.hiss_db": -50.0}),
        Variant("storm", "Storm Offshore",
                "Lightning within thirty miles puts a crash between every second word.",
                audio={"a_cb_radio.hiss_db": -34.0, "a_shortwave.enabled": True}),
    ],
))


# nearest: audio-police-scanner-1985; differs: a carbon microphone and an AM
# mobile carrier into a tube receiver, thirty years before scanner AGC.
register_preset(Preset(
    id="audio-two-way-police-1955",
    name="Two-Way Police Radio",
    family="audio",
    era="1955",
    desc="A patrol call in the Dragnet years: a carbon microphone into an AM mobile transmitter, a tube receiver sagging on the loud words and a horn speaker under the dash.",
    tagline="Carbon dispatch, tube set, cruiser horn",
    tags=("audio-only", "50s", "radio", "dispatch"),
    keywords=("police-radio", "two-way", "1950s", "dispatch", "carbon", "tube",
              "cruiser", "dragnet", "ten-four", "am-mobile"),
    video=[],
    audio=[
        ("a_historical_mic", {"profile": "carbon_1925", "amount": 0.7,
                              "overload": 0.4, "self_noise_db": -55.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_bandlimit", {"low_hz": 300.0, "high_hz": 2800.0, "order": 6}),
        ("a_am_radio", {"hi_hz": 2800.0, "pump": 0.6, "static_db": -43.0,
                        "fade": 0.1, "whistle_db": -70.0}),
        ("a_tube_amp", {"drive": 2.0, "sag": 0.45, "microphonics": 0.15, "hum_db": -56.0}),
        ("a_speaker", {"device": "intercom_horn_1950", "strength": 0.9}),
    ],
    variants=[
        Variant("base-station", "Base Station",
                "Dispatch talking from the building instead of a car, with a proper microphone and a strong carrier.",
                audio={"a_am_radio.static_db": -54.0, "a_historical_mic.overload": 0.2}),
        Variant("edge-of-range", "Edge Of The District",
                "Out past the county line the carrier keeps giving up mid-sentence.",
                audio={"a_am_radio.static_db": -38.0, "a_am_radio.pump": 0.9,
                       "a_am_radio.fade": 0.4}),
    ],
))


# nearest: audio-drive-thru-1988; differs: a ceiling intercom horn in a hard
# classroom with tube-era mains hum, not a phone-grade squawk box in a lot.
register_preset(Preset(
    id="audio-school-intercom-1962",
    name="School Intercom",
    family="audio",
    era="1962",
    desc="Morning announcements from the office to every homeroom: a dynamic desk microphone, an intercom horn in the ceiling tile, a hard classroom and 60-cycle tube hum.",
    tagline="Ceiling horn, announcements, 60-cycle buzz",
    tags=("audio-only", "60s", "pa", "intercom"),
    keywords=("school", "intercom", "1960s", "announcements", "ceiling-speaker",
              "principal", "homeroom", "buzz", "hallway", "tube-pa"),
    video=[],
    audio=[
        ("a_historical_mic", {"profile": "broadcast_dynamic_1955", "amount": 0.6,
                              "proximity": 0.4, "overload": 0.2, "self_noise_db": -58.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_pa_bullhorn", {"device": "intercom", "drive": 2.0, "slap_ms": -1.0,
                           "slap_gain_db": -14.0, "slap_repeats": 0}),
        ("a_room", {"mode": "room", "size": 1.4, "decay_s": 0.5, "damp": 0.5,
                    "predelay_ms": 6.0, "mix": 0.2}),
        ("a_hum", {"hz": "60", "level_db": -46.0, "buzz": 0.5}),
    ],
    variants=[
        Variant("gymnasium-assembly", "Gymnasium Assembly",
                "The same horn circuit fed into the gym, where every word arrives twice.",
                audio={"a_room.size": 2.8, "a_room.decay_s": 2.0, "a_room.mix": 0.35}),
        Variant("office-mic-clean", "Office Microphone, Clean",
                "The secretary sits back from the microphone and somebody has replaced the filter capacitor.",
                audio={"a_pa_bullhorn.drive": 1.3, "a_hum.level_db": -58.0}),
    ],
))
