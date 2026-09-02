"""Audio-only archival presets, sixth wave: public address, broadcast paths,
playback rooms and small modern speakers.

Every preset here leaves the picture untouched (``video=[]``); the chain is the
sound path only, ordered source tone -> medium -> transmission -> device ->
room -> beds. Where an a_bandlimit follows a horn, a receiver or a driver it is
that device's own response, so it also filters what the device's own distortion
adds: putting it earlier leaves harmonics ringing above a band the hardware
never reproduced.
"""

from ..engine.presets import Preset, Variant, register_preset


# nearest: audio-pa-1970; differs: open-air stadium horn stacks with three
# shrinking slap returns and a long grandstand tail instead of one hard slap.
register_preset(Preset(
    id="audio-stadium-pa-1975",
    name="Stadium PA",
    family="audio",
    era="1975",
    desc="Horn stacks on a ballpark light tower: clipped announcer midrange thrown across the field, three shrinking returns off the far grandstand and a long open-air tail behind every name.",
    tagline="Horn stacks, triple slap, crowd-hall decay",
    tags=("audio-only", "70s", "pa", "stadium"),
    keywords=("stadium", "pa", "1970s", "horns", "slap", "crowd", "ballpark",
              "announcer", "echo", "bleachers"),
    video=[],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_pa_bullhorn", {"device": "pa_stadium", "drive": 2.9, "slap_ms": 280.0,
                           "slap_gain_db": -8.0, "slap_repeats": 3}),
        ("a_bandlimit", {"low_hz": 100.0, "high_hz": 6000.0, "order": 5}),
        ("a_room", {"mode": "chamber", "size": 3.5, "decay_s": 2.2, "damp": 0.6,
                    "predelay_ms": 35.0, "mix": 0.25}),
    ],
    variants=[
        Variant("empty-stadium", "Empty Stadium", "Nobody in the seats to absorb it, so the bowl keeps the announcement for three seconds.",
                audio={"a_room.mix": 0.4, "a_room.decay_s": 3.0,
                       "a_pa_bullhorn.slap_gain_db": -6.0}),
        Variant("press-box-line", "Press Box Line", "The same voice taken off the announce feed before it ever reaches a horn.",
                audio={"a_pa_bullhorn.slap_repeats": 0, "a_pa_bullhorn.drive": 1.4,
                       "a_room.mix": 0.05}),
    ],
))


# nearest: audio-subway-pa-1975; differs: clean 1985 terminal paging, glass hall
# instead of tile tube, wider band and a constant air-handler bed.
register_preset(Preset(
    id="audio-airport-pa-1985",
    name="Airport PA",
    family="audio",
    era="1985",
    desc="A 1985 terminal paging system: one soft slap off a glass curtain wall, two and a half seconds of concourse tail and the air handlers running under every gate call.",
    tagline="Terminal hall, clean band, HVAC bed",
    tags=("audio-only", "80s", "pa", "airport"),
    keywords=("airport", "pa", "1980s", "terminal", "announcement", "gate",
              "hall", "hvac", "boarding", "travel"),
    video=[],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_pa_bullhorn", {"device": "pa_hall", "drive": 1.4, "slap_ms": 180.0,
                           "slap_gain_db": -12.0, "slap_repeats": 1}),
        ("a_bandlimit", {"low_hz": 180.0, "high_hz": 8000.0, "order": 4}),
        ("a_room", {"mode": "chamber", "size": 4.0, "decay_s": 2.5, "damp": 0.5,
                    "predelay_ms": 30.0, "mix": 0.3}),
        ("a_bed", {"bed": "air_handler_hall", "level_db": -30.0, "duck": 0.3}),
    ],
    variants=[
        Variant("small-regional-terminal", "Regional Terminal", "One gate, a low ceiling and a page that dies before it crosses the room.",
                audio={"a_room.size": 2.0, "a_room.decay_s": 1.2, "a_room.mix": 0.2,
                       "a_bed.level_db": -36.0}),
        Variant("late-night-empty", "Last Flight", "Nothing left in the concourse but the ducts and a paging chime.",
                audio={"a_room.mix": 0.45, "a_room.decay_s": 3.2, "a_bed.level_db": -26.0}),
    ],
))


# nearest: audio-airport-pa-1985; differs: 1938 carbon microphone, 250-4000 Hz
# platform horns, iron-roof double return and 50 Hz mains buzz.
register_preset(Preset(
    id="audio-railway-station-tannoy-1938",
    name="Railway Station Tannoy",
    family="audio",
    era="1938",
    desc="A pre-war British station tannoy: a carbon microphone into platform horns, two long returns off an iron train-shed roof and 50 Hz mains buzz sitting in the amplifier.",
    tagline="Carbon horn, iron-roof echo, 50 Hz mains",
    tags=("audio-only", "30s", "pa", "railway", "uk"),
    keywords=("tannoy", "railway", "station", "1930s", "british", "horn",
              "platform", "echo", "steam", "announcement"),
    video=[],
    audio=[
        ("a_historical_mic", {"profile": "carbon_1925", "amount": 0.6,
                              "proximity": 0.25, "overload": 0.3, "self_noise_db": -52.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_pa_bullhorn", {"device": "pa_hall", "drive": 2.5, "slap_ms": 420.0,
                           "slap_gain_db": -9.0, "slap_repeats": 2}),
        ("a_bandlimit", {"low_hz": 250.0, "high_hz": 4000.0, "order": 5}),
        ("a_room", {"mode": "chamber", "size": 4.0, "decay_s": 3.0, "damp": 0.4,
                    "predelay_ms": 45.0, "mix": 0.3}),
        ("a_hum", {"hz": "50", "level_db": -44.0, "buzz": 0.5}),
    ],
    variants=[
        Variant("small-halt", "Country Halt", "Two platforms, one horn and a roof too short to answer back.",
                audio={"a_room.size": 2.0, "a_room.decay_s": 1.5, "a_room.mix": 0.22,
                       "a_pa_bullhorn.slap_repeats": 1}),
        Variant("concourse-rush", "Concourse At Six", "The announcer leans in, the amplifier hums harder and the shed keeps all of it.",
                audio={"a_room.mix": 0.4, "a_hum.level_db": -40.0,
                       "a_pa_bullhorn.drive": 3.2, "a_historical_mic.overload": 0.5}),
    ],
))


# nearest: audio-am-1948; differs: a close booth dynamic and a fast station
# limiter ahead of the carrier, played back on a kitchen portable.
register_preset(Preset(
    id="audio-ballpark-radio-1950",
    name="Ballpark Radio Call",
    family="audio",
    era="1950",
    desc="A summer afternoon game off the network: a booth dynamic microphone worked close, a fast station limiter riding every call and AM carrier hiss arriving through a kitchen portable.",
    tagline="AM play-by-play, crowd wash, booth-mic pop",
    tags=("audio-only", "50s", "radio", "am", "sports"),
    keywords=("baseball", "radio", "1950s", "play-by-play", "am", "crowd",
              "booth", "announcer", "ballpark", "summer"),
    video=[],
    audio=[
        ("a_historical_mic", {"profile": "broadcast_dynamic_1955", "amount": 0.6,
                              "proximity": 0.4, "overload": 0.3, "self_noise_db": -56.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_compressor", {"threshold_db": -18.0, "ratio": 4.0, "attack_ms": 5.0,
                          "release_ms": 250.0, "knee_db": 4.0, "makeup_db": 2.0}),
        ("a_am_radio", {"hi_hz": 4800.0, "pump": 0.5, "static_db": -50.0,
                        "fade": 0.08, "whistle_db": -66.0}),
        ("a_bandlimit", {"low_hz": 120.0, "high_hz": 5500.0, "order": 4}),
        ("a_speaker", {"device": "portable_radio_1975", "strength": 1.0}),
    ],
    variants=[
        Variant("kitchen-console", "Kitchen Console", "The same game out of the big cabinet set in the next room.",
                audio={"a_speaker.device": "tv_console_1972", "a_speaker.strength": 0.7,
                       "a_am_radio.static_db": -54.0}),
        Variant("night-game-fade", "Night Game", "After dark the carrier starts sliding and another station leans on the channel.",
                audio={"a_am_radio.fade": 0.35, "a_am_radio.static_db": -44.0,
                       "a_am_radio.whistle_db": -56.0}),
    ],
))


# nearest: audio-shortwave-1962; differs: heavier jamming and utility QRM, a
# microphonic tube receiver and a console cabinet instead of a portable.
register_preset(Preset(
    id="audio-wartime-shortwave-1942",
    name="Wartime Shortwave",
    family="audio",
    era="1942",
    desc="A 1942 service crossing an ocean on 49 metres: deep selective fades, a jammer heterodyne parked on the carrier, morse and teleprinters crawling through the passband and a tube console reproducing what is left.",
    tagline="Jammed HF, sferics, distant morse bleed",
    tags=("audio-only", "40s", "radio", "shortwave"),
    keywords=("shortwave", "wartime", "1940s", "bbc", "propaganda", "jamming",
              "morse", "hf", "distant", "resistance"),
    video=[],
    audio=[
        ("a_shortwave", {"hi_hz": 3000.0, "fade": 0.6, "het_db": -44.0,
                         "utility_qrm": 0.5, "sferics": 0.6, "static_db": -42.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_tube_amp", {"drive": 1.6, "sag": 0.35, "microphonics": 0.15, "hum_db": -56.0}),
        ("a_bandlimit", {"low_hz": 200.0, "high_hz": 3200.0, "order": 6}),
        ("a_speaker", {"device": "tv_console_1972", "strength": 0.7}),
    ],
    variants=[
        Variant("clear-night", "Clear Night", "The band opens, the jammer drifts off frequency and the announcer holds still for a minute.",
                audio={"a_shortwave.fade": 0.3, "a_shortwave.utility_qrm": 0.1,
                       "a_shortwave.static_db": -50.0, "a_shortwave.het_db": -56.0}),
        Variant("heavy-jamming", "Jammed", "Somebody is sitting on the channel and the words come through in pieces.",
                audio={"a_shortwave.utility_qrm": 0.9, "a_shortwave.het_db": -34.0,
                       "a_shortwave.fade": 0.8, "a_shortwave.static_db": -36.0}),
    ],
))


# nearest: audio-am-1948; differs: hard pirate limiting, adjacent-channel bleed
# and sea-path fade into a teenager's pocket transistor.
register_preset(Preset(
    id="audio-pirate-offshore-am-1966",
    name="Pirate Offshore AM",
    family="audio",
    era="1966",
    desc="A transmitter bolted into a North Sea ship: heavy pirate limiting, medium-wave fade as the hull rolls, the adjacent channel bleeding through and a pocket transistor at the far end.",
    tagline="Ship AM, sea-path fade, adjacent bleed",
    tags=("audio-only", "60s", "radio", "am", "uk"),
    keywords=("pirate-radio", "offshore", "1960s", "am", "ship", "caroline",
              "fade", "top-40", "medium-wave", "north-sea"),
    video=[],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_compressor", {"threshold_db": -16.0, "ratio": 5.0, "attack_ms": 3.0,
                          "release_ms": 180.0, "knee_db": 3.0, "makeup_db": 4.0}),
        ("a_am_radio", {"hi_hz": 4500.0, "pump": 0.7, "static_db": -48.0,
                        "fade": 0.3, "whistle_db": -60.0, "adjacent_channel": 0.4,
                        "tune_drift": 0.4}),
        ("a_speaker", {"device": "transistor_pocket_1965", "strength": 1.0}),
    ],
    variants=[
        Variant("good-signal-coast", "On The Coast", "Close enough to the ship that the signal simply stays put.",
                audio={"a_am_radio.fade": 0.1, "a_am_radio.adjacent_channel": 0.1,
                       "a_am_radio.static_db": -56.0, "a_am_radio.tune_drift": 0.0}),
        Variant("night-skywave", "Night Skywave", "After sunset the ground wave gives up and everything else on the band arrives instead.",
                audio={"a_am_radio.fade": 0.6, "a_am_radio.whistle_db": -48.0,
                       "a_am_radio.adjacent_channel": 0.7}),
    ],
))


# nearest: audio-fm-1978; differs: a ten-watt campus transmitter with loud pilot
# hiss and hard multipath, a cart machine ahead of it and a clock radio after.
register_preset(Preset(
    id="audio-college-fm-1988",
    name="College FM",
    family="audio",
    era="1988",
    desc="Ten watts out of a campus basement: a cart machine settling on its first turn, low-power FM hiss and multipath flutter, landing in a bedside clock radio across the quad.",
    tagline="Low-power FM hiss, multipath, cart clunk",
    tags=("audio-only", "80s", "radio", "fm", "cart"),
    keywords=("college-radio", "fm", "1980s", "low-power", "hiss", "multipath",
              "indie", "cart", "dj", "campus"),
    video=[],
    audio=[
        ("a_analog_dub", {"format": "broadcast_cart", "generations": 1,
                          "alignment": 0.2, "compression": 0.35, "hiss_db": -52.0}),
        ("a_wow_flutter", {"wow_depth": 5.0, "flutter_depth": 3.0,
                           "start_wobble": True, "cogging": 0.15, "cogging_hz": 30.0}),
        ("a_fm_radio", {"hiss_db": -46.0, "comp": 0.3, "multipath": 4.0}),
        ("a_bandlimit", {"low_hz": 120.0, "high_hz": 8000.0, "order": 4}),
        ("a_speaker", {"device": "clock_radio_1988", "strength": 0.9}),
    ],
    variants=[
        Variant("dorm-boombox", "Dorm Boombox", "Same ten watts, but somebody has it on the good speakers.",
                audio={"a_speaker.device": "boombox_1985", "a_speaker.strength": 0.7,
                       "a_fm_radio.hiss_db": -50.0}),
        Variant("fringe-of-campus", "Edge Of Coverage", "Two miles out the pilot hiss wins and the buildings answer the signal twice.",
                audio={"a_fm_radio.hiss_db": -38.0, "a_fm_radio.multipath": 10.0}),
    ],
))


# nearest: audio-am-1948; differs: an 8:1 tube limiter and transmitter sag on a
# 200-5000 Hz test feed, reproduced by a living-room console.
register_preset(Preset(
    id="audio-emergency-broadcast-test-1965",
    name="Emergency Broadcast Test",
    family="audio",
    era="1965",
    desc="The one-minute test: a hard tube limiter clamped on a narrow 200 to 5000 Hz feed, supply sag under the attention tone and a living-room console reproducing all of it.",
    tagline="Attention-signal band, tube limiter, hum",
    tags=("audio-only", "60s", "radio", "broadcast", "am"),
    keywords=("emergency-broadcast", "ebs", "1960s", "test", "attention-signal",
              "civil-defense", "conelrad", "tube", "alert", "this-is-a-test"),
    video=[],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_compressor", {"threshold_db": -14.0, "ratio": 8.0, "attack_ms": 1.0,
                          "release_ms": 400.0, "knee_db": 2.0, "makeup_db": 3.0}),
        ("a_tube_amp", {"drive": 2.2, "sag": 0.5, "microphonics": 0.1, "hum_db": -52.0}),
        ("a_am_radio", {"hi_hz": 4800.0, "pump": 0.4, "static_db": -54.0, "fade": 0.05}),
        ("a_fm_radio", {"enabled": False, "hiss_db": -58.0, "comp": 0.5, "multipath": 0.5}),
        ("a_bandlimit", {"low_hz": 200.0, "high_hz": 5000.0, "order": 6}),
        ("a_speaker", {"device": "tv_console_1972", "strength": 0.7}),
    ],
    variants=[
        Variant("fm-stereo-1975", "FM Simulcast", "The decade turns, the test moves to the FM side of the dial and the carrier stops pumping.",
                audio={"a_am_radio.enabled": False, "a_fm_radio.enabled": True,
                       "a_bandlimit.high_hz": 8000.0}),
        Variant("distant-station", "Distant Station", "The nearest participating transmitter is two counties away.",
                audio={"a_am_radio.static_db": -44.0, "a_am_radio.fade": 0.3,
                       "a_am_radio.pump": 0.7}),
    ],
))


# nearest: audio-hold-music-1993; differs: a leased-line music service through
# ceiling cones in a large store, not a telephone band.
register_preset(Preset(
    id="audio-in-store-music-1965",
    name="In-Store Background Music",
    family="audio",
    era="1965",
    desc="Leased-line background music in a department store: everything squeezed to one level, fed to ceiling cones over the sales floor while fluorescent ballasts hum above the racks.",
    tagline="Muzak line, ceiling cones, hard leveling",
    tags=("audio-only", "60s", "pa", "muzak"),
    keywords=("muzak", "in-store", "1960s", "background-music", "elevator",
              "ceiling-speaker", "leased-line", "leveling", "easy-listening",
              "department-store"),
    video=[],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_compressor", {"threshold_db": -30.0, "ratio": 10.0, "attack_ms": 30.0,
                          "release_ms": 900.0, "knee_db": 10.0, "makeup_db": 8.0}),
        ("a_pa_bullhorn", {"device": "intercom", "drive": 1.2, "slap_repeats": 0}),
        ("a_bandlimit", {"low_hz": 100.0, "high_hz": 7500.0, "order": 4}),
        ("a_room", {"mode": "chamber", "size": 2.5, "decay_s": 1.4, "damp": 0.6,
                    "predelay_ms": 20.0, "mix": 0.2}),
        ("a_hum", {"hz": "60", "level_db": -58.0, "buzz": 0.25}),
        ("a_bed", {"bed": "fluorescent_office", "level_db": -38.0, "duck": 0.2}),
    ],
    variants=[
        Variant("elevator-1975", "Elevator Car", "A steel cupboard with one grille in the ceiling and nowhere for the sound to go.",
                audio={"a_room.size": 0.5, "a_room.decay_s": 0.3, "a_room.mix": 0.15,
                       "a_bed.level_db": -42.0}),
        Variant("supermarket-1990", "Supermarket Aisle", "Longer room, louder lights and a service that gave up on dynamics entirely.",
                audio={"a_bed.level_db": -32.0, "a_hum.level_db": -50.0,
                       "a_room.mix": 0.28, "a_compressor.ratio": 8.0}),
    ],
))


# nearest: audio-cassette-field-1979; differs: a fixed table microphone in a
# wood-panelled room rather than a lavalier, with room tail before the tape.
register_preset(Preset(
    id="audio-courtroom-tape-1975",
    name="Courtroom Cassette",
    family="audio",
    era="1975",
    desc="The clerk's cassette of a hearing: a table-stand dynamic microphone in a wood-panelled room, Type I hiss between exchanges and a level circuit that lifts the empty room after every answer.",
    tagline="Table mic, gavel room, cassette hiss, AGC",
    tags=("audio-only", "70s", "cassette", "legal"),
    keywords=("courtroom", "cassette", "1970s", "deposition", "table-mic",
              "gavel", "hiss", "agc", "transcript", "legal"),
    video=[],
    audio=[
        ("a_historical_mic", {"profile": "broadcast_dynamic_1955", "amount": 0.5,
                              "proximity": 0.0, "overload": 0.12, "handling": 0.1,
                              "self_noise_db": -56.0}),
        ("a_room", {"mode": "room", "size": 2.0, "decay_s": 0.9, "damp": 0.5,
                    "predelay_ms": 12.0, "mix": 0.22}),
        ("a_mono", {"amount": 1.0}),
        ("a_analog_dub", {"format": "cassette", "generations": 1,
                          "alignment": 0.2, "compression": 0.35, "hiss_db": -50.0}),
        ("a_tape_sat", {"drive": 1.6, "bump_db": 2.0, "hf_loss": 0.7,
                        "eq_era": "modern"}),
        ("a_agc", {"target_db": -18.0, "max_gain_db": 14.0, "attack_ms": 10.0,
                   "release_ms": 600.0, "amount": 0.8}),
    ],
    variants=[
        Variant("front-row-mic", "Bench Microphone", "The recorder sits where the words are, so the panelling stays out of it.",
                audio={"a_room.mix": 0.1, "a_agc.max_gain_db": 8.0,
                       "a_agc.amount": 0.55}),
        Variant("archive-copy-3rd-gen", "Archive Copy", "Three dubs later the exhibit tape is mostly hiss with a hearing inside it.",
                audio={"a_analog_dub.generations": 3, "a_analog_dub.alignment": 0.5,
                       "a_analog_dub.hiss_db": -44.0}),
    ],
))


# nearest: audio-microcassette-1986; differs: a slow reel machine muffled inside
# furniture, long speed drift and mains hum rather than per-syllable flutter.
register_preset(Preset(
    id="audio-hidden-recorder-1972",
    name="Hidden Recorder Tape",
    family="audio",
    era="1972",
    desc="A reel machine running slow in a locked desk drawer: wood absorbing everything above 3.6 kHz, long speed drift, mains hum on the feed and an automatic gain circuit hunting the room between sentences.",
    tagline="Desk-drawer muffle, slow reel, hum, hiss loud",
    tags=("audio-only", "70s", "reel", "tape", "surveillance"),
    keywords=("hidden-recorder", "1972", "oval-office", "bugged", "desk",
              "muffled", "reel", "hum", "nixon", "transcript"),
    video=[],
    audio=[
        ("a_bandlimit", {"low_hz": 150.0, "high_hz": 3600.0, "order": 4}),
        ("a_mono", {"amount": 1.0}),
        ("a_analog_dub", {"format": "reel_375ips", "generations": 1,
                          "alignment": 0.35, "compression": 0.4, "hiss_db": -42.0}),
        ("a_tape_sat", {"drive": 1.5, "bump_db": 1.5, "hf_loss": 0.65,
                        "eq_era": "nab_mismatch"}),
        ("a_wow_flutter", {"wow_depth": 8.0, "flutter_depth": 5.0, "drift_long": 0.5}),
        ("a_tape_dropouts", {"enabled": False, "rate": 6.0, "depth_db": 24.0,
                             "azimuth": 0.25}),
        ("a_agc", {"target_db": -20.0, "max_gain_db": 18.0, "attack_ms": 30.0,
                   "release_ms": 900.0, "amount": 0.9}),
        ("a_hum", {"hz": "60", "level_db": -46.0, "buzz": 0.3}),
    ],
    variants=[
        Variant("better-mic-placement", "Under The Lamp", "The capsule finally clears the drawer and the voices get their consonants back.",
                audio={"a_bandlimit.low_hz": 100.0, "a_bandlimit.high_hz": 5500.0,
                       "a_analog_dub.hiss_db": -48.0, "a_agc.max_gain_db": 12.0}),
        Variant("the-18-minute-gap", "The Gap", "Somebody leaned on the erase head and the tape now loses whole clauses.",
                audio={"a_tape_dropouts.enabled": True, "a_tape_dropouts.rate": 30.0,
                       "a_tape_dropouts.depth_db": 40.0, "a_tape_dropouts.azimuth": 0.5}),
    ],
))


# nearest: audio-optical-1942; differs: the widest late-1970s optical band with
# no academy rolloff, matrix channel spread and a mid-size auditorium tail.
register_preset(Preset(
    id="audio-dolby-stereo-optical-1977",
    name="Dolby Stereo Optical",
    family="audio",
    era="1977",
    desc="A 1977 encoded optical print: the widest band a photographic track ever carried, matrix leakage spreading the channels past the screen and a mid-size auditorium answering underneath.",
    tagline="Wide optical band, matrix spread, hall bass",
    tags=("audio-only", "70s", "film", "optical", "35mm"),
    keywords=("dolby-stereo", "optical", "1970s", "cinema", "matrix", "surround",
              "theater", "wide", "35mm", "blockbuster"),
    video=[],
    audio=[
        ("a_optical_track", {"low_hz": 40.0, "high_hz": 9000.0,
                             "academy_rolloff": "none", "cell_noise": -60.0,
                             "flutter": 0.15, "drive": 1.1}),
        ("a_channel_aging", {"width": 1.3, "imbalance_db": -0.3, "crosstalk_db": -30.0,
                             "skew_us": 8.0, "phase_wander": 0.05, "mono_bass_hz": 90.0}),
        ("a_compressor", {"threshold_db": -20.0, "ratio": 2.5, "attack_ms": 12.0,
                          "release_ms": 300.0, "knee_db": 8.0}),
        ("a_room", {"mode": "chamber", "size": 2.5, "decay_s": 1.2, "damp": 0.5,
                    "predelay_ms": 22.0, "mix": 0.15}),
    ],
    variants=[
        Variant("dolby-sr-1987", "Spectral Recording", "Ten years of cell noise gone and the width pushed a little further out.",
                audio={"a_optical_track.cell_noise": -66.0, "a_optical_track.flutter": 0.08,
                       "a_channel_aging.width": 1.4, "a_channel_aging.crosstalk_db": -38.0}),
        Variant("academy-mono-print", "Academy Mono Print", "The flat print for houses that never installed the decoder: one channel, rolled off at 5 kHz.",
                audio={"a_optical_track.academy_rolloff": "feature_1940s",
                       "a_optical_track.high_hz": 5500.0, "a_optical_track.cell_noise": -50.0,
                       "a_optical_track.flutter": 0.35, "a_channel_aging.width": 0.0,
                       "a_channel_aging.crosstalk_db": -60.0}),
    ],
))


# nearest: audio-tv-speaker-1975; differs: a stereo BTSC pair with dbx companding
# breathing on quiet passages instead of a single mono cone.
register_preset(Preset(
    id="audio-tv-mts-stereo-1985",
    name="TV Stereo MTS",
    family="audio",
    era="1985",
    desc="The first season of stereo television: a narrow BTSC image with dbx companding breathing through quiet passages, intercarrier buzz behind it and two small cabinet speakers reproducing it.",
    tagline="Narrow MTS stereo, dbx pumping, TV cones",
    tags=("audio-only", "80s", "tv", "stereo", "broadcast"),
    keywords=("mts", "tv-stereo", "1980s", "btsc", "dbx", "stereo-tv", "console",
              "narrow", "broadcast", "prime-time"),
    video=[],
    audio=[
        ("a_channel_aging", {"width": 0.75, "imbalance_db": -0.6, "crosstalk_db": -32.0,
                             "skew_us": 60.0, "phase_wander": 0.2, "mono_bass_hz": 160.0}),
        ("a_noise_reduction", {"system": "dbx", "decode_error": -0.2,
                               "threshold_db": -36.0, "pumping": 0.3, "hiss_db": -58.0}),
        ("a_tv_sound", {"hz": "60", "buzz_db": -62.0, "hum_db": -64.0, "comp": 0.3}),
        ("a_speaker", {"device": "tv_mono_1985", "strength": 0.6}),
    ],
    variants=[
        Variant("mono-set-fold", "Mono Set", "The other television in the house sums it all back down to one cone.",
                audio={"a_channel_aging.width": 0.0, "a_channel_aging.crosstalk_db": -20.0,
                       "a_speaker.strength": 0.9}),
        Variant("hi-fi-stereo-set", "Stereo Monitor", "A late-decade set with a decoder that actually tracks the encoder.",
                audio={"a_channel_aging.width": 0.95, "a_channel_aging.crosstalk_db": -45.0,
                       "a_noise_reduction.pumping": 0.1, "a_speaker.strength": 0.25}),
    ],
))


# nearest: none; no muffled-neighbour space exists in the library.
register_preset(Preset(
    id="audio-through-the-wall-1995",
    name="Through the Wall",
    family="audio",
    era="1995",
    desc="Somebody else's stereo two rooms away: plaster and studs absorbing everything above 800 Hz, only thud and room bleed arriving, with your own apartment's air handler underneath.",
    tagline="Neighbor's stereo, 40-800 Hz thud, bleed",
    tags=("audio-only", "90s", "room", "muffled", "apartment"),
    keywords=("through-the-wall", "next-door", "neighbor", "muffled", "apartment",
              "thud", "bass", "bleed", "1990s", "party"),
    video=[],
    audio=[
        ("a_bandlimit", {"low_hz": 40.0, "high_hz": 800.0, "order": 6}),
        ("a_room", {"mode": "room", "size": 1.6, "decay_s": 0.8, "damp": 0.9,
                    "predelay_ms": 10.0, "mix": 0.35}),
        ("a_gain", {"db": -6.0}),
        ("a_bed", {"bed": "air_handler_hall", "level_db": -44.0, "duck": 0.1}),
    ],
    variants=[
        Variant("thin-wall", "Thin Wall", "Drywall and one stud: you can nearly make out the lyrics.",
                audio={"a_bandlimit.high_hz": 1800.0, "a_gain.db": -3.0,
                       "a_room.mix": 0.28}),
        Variant("concrete-floor", "Floor Below", "Through a concrete slab there is nothing left but the kick drum.",
                audio={"a_bandlimit.low_hz": 30.0, "a_bandlimit.high_hz": 500.0,
                       "a_gain.db": -8.0, "a_room.mix": 0.45}),
    ],
))


# nearest: audio-church-pa-1972; differs: a small hard-glazed room with a 22 ms
# flutter echo instead of a stone hall and a horn.
register_preset(Preset(
    id="audio-tiled-bathroom-1980",
    name="Tiled Bathroom",
    family="audio",
    era="1980",
    desc="A small tiled bathroom: hard glaze on every surface, a 22 ms flutter ringing between two parallel walls and a bright decay that outlasts the phrase.",
    tagline="Bright tile decay, fast flutter echo",
    tags=("audio-only", "80s", "room", "tile", "reverb"),
    keywords=("bathroom", "tile", "shower", "reverb", "flutter-echo", "bright",
              "small-room", "singing", "1980s", "echoey"),
    video=[],
    audio=[
        ("a_bandlimit", {"low_hz": 80.0, "high_hz": 12000.0, "order": 3}),
        ("a_room", {"mode": "room", "size": 0.6, "decay_s": 1.4, "damp": 0.15,
                    "predelay_ms": 4.0, "mix": 0.4}),
        ("a_slap", {"delay_ms": 22.0, "gain_db": -6.0, "repeats": 6, "damp": 0.2}),
    ],
    variants=[
        Variant("large-locker-room", "Locker Room", "The same tile, four times the floor area and a slower ring.",
                audio={"a_room.size": 1.8, "a_room.decay_s": 2.2, "a_room.mix": 0.45,
                       "a_slap.delay_ms": 45.0}),
        Variant("dry-towels", "Towels On The Rail", "Fabric on two walls takes the sting out of the flutter.",
                audio={"a_room.mix": 0.25, "a_room.decay_s": 0.9, "a_room.damp": 0.45,
                       "a_slap.gain_db": -12.0}),
    ],
))


# nearest: audio-stadium-pa-1975; differs: an enclosed hardwood box with a 240 ms
# double slap and fluorescent ballast buzz instead of open air.
register_preset(Preset(
    id="audio-gymnasium-1975",
    name="School Gymnasium",
    family="audio",
    era="1975",
    desc="A school gym at assembly: hardwood and cinder block returning a 240 ms slap twice, a horn cluster over the scoreboard smearing the words and light ballasts buzzing above the bleachers.",
    tagline="Hardwood boom, horn PA mush, ballast buzz",
    tags=("audio-only", "70s", "pa", "gym", "school"),
    keywords=("gymnasium", "gym", "school", "1970s", "hardwood", "slap", "pa",
              "assembly", "basketball", "echo"),
    video=[],
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_pa_bullhorn", {"device": "pa_hall", "drive": 1.8, "slap_ms": 240.0,
                           "slap_gain_db": -9.0, "slap_repeats": 2}),
        ("a_bandlimit", {"low_hz": 90.0, "high_hz": 7000.0, "order": 4}),
        ("a_room", {"mode": "chamber", "size": 3.0, "decay_s": 2.6, "damp": 0.45,
                    "predelay_ms": 25.0, "mix": 0.35}),
        ("a_hum", {"hz": "60", "level_db": -50.0, "buzz": 0.6}),
    ],
    variants=[
        Variant("pep-rally", "Pep Rally", "Everyone shouting into a room that keeps three seconds of everything.",
                audio={"a_room.mix": 0.45, "a_room.decay_s": 3.0,
                       "a_pa_bullhorn.drive": 2.6}),
        Variant("small-gym-quiet", "Practice Gym", "Half the floor, newer ballasts and a slap you can count.",
                audio={"a_room.size": 2.0, "a_room.decay_s": 1.6, "a_room.mix": 0.25,
                       "a_hum.level_db": -60.0}),
    ],
))


# nearest: audio-church-pa-1972; differs: no PA horn at all, a distant ribbon
# microphone and five and a half seconds of pure stone decay.
register_preset(Preset(
    id="audio-cathedral-1962",
    name="Cathedral Nave",
    family="audio",
    era="1962",
    desc="A ribbon microphone hung far back in a stone nave: 40 ms before the building answers, six seconds of decay on every syllable and choir air filling the space between.",
    tagline="Six-second stone decay, distant ribbon mic",
    tags=("audio-only", "60s", "room", "church", "reverb"),
    keywords=("cathedral", "church", "nave", "reverb", "stone", "choir",
              "pulpit", "1960s", "organ", "sacred"),
    video=[],
    audio=[
        ("a_historical_mic", {"profile": "ribbon_1938", "amount": 0.62,
                              "proximity": 0.0, "overload": 0.1, "self_noise_db": -60.0}),
        ("a_bandlimit", {"low_hz": 40.0, "high_hz": 9000.0, "order": 3}),
        ("a_channel_aging", {"width": 1.2, "imbalance_db": -0.2, "crosstalk_db": -46.0,
                             "skew_us": 30.0, "phase_wander": 0.12, "mono_bass_hz": 70.0}),
        ("a_room", {"mode": "chamber", "size": 4.0, "decay_s": 6.0, "damp": 0.45,
                    "predelay_ms": 40.0, "mix": 0.55}),
        ("a_vinyl_noise", {"enabled": False, "crackle": 6.0, "crackle_db": -40.0,
                           "pops": 2.0, "pops_db": -24.0, "frying_db": -58.0,
                           "rumble_db": -50.0, "wear": 0.2, "warp_rpm": "33"}),
        ("a_vinyl_wow", {"enabled": False, "rpm": "33", "depth_cents": 6.0}),
    ],
    variants=[
        Variant("side-chapel", "Side Chapel", "A smaller stone room off the transept with a tail you can talk over.",
                audio={"a_room.size": 2.0, "a_room.decay_s": 2.5, "a_room.mix": 0.3}),
        Variant("recorded-on-lp-1962", "Pressed To LP", "The same session as the parish sold it: cut to a 33 and played a hundred times.",
                audio={"a_vinyl_noise.enabled": True, "a_vinyl_wow.enabled": True,
                       "a_vinyl_noise.wear": 0.35}),
    ],
))


# nearest: audio-gymnasium-1975; differs: a low concrete deck with a hard 90 ms
# slap and no PA horn, ducts and ballasts instead of a hardwood boom.
register_preset(Preset(
    id="audio-parking-garage-1998",
    name="Parking Garage",
    family="audio",
    era="1998",
    desc="Two levels underground: bare concrete returning a 90 ms slap four times, a low ceiling boxing in the bottom end and fluorescent tubes buzzing the length of the deck.",
    tagline="Concrete slap, low-ceiling boom, buzz",
    tags=("audio-only", "90s", "room", "garage", "concrete"),
    keywords=("parking-garage", "concrete", "slap", "boom", "fluorescent",
              "1990s", "underground", "car-park", "echo", "urban"),
    video=[],
    audio=[
        ("a_bandlimit", {"low_hz": 60.0, "high_hz": 9000.0, "order": 4}),
        ("a_room", {"mode": "room", "size": 2.2, "decay_s": 1.8, "damp": 0.3,
                    "predelay_ms": 15.0, "mix": 0.35}),
        ("a_slap", {"delay_ms": 90.0, "gain_db": -7.0, "repeats": 4, "damp": 0.4}),
        ("a_hum", {"hz": "60", "level_db": -54.0, "buzz": 0.7}),
        ("a_bed", {"bed": "air_handler_hall", "level_db": -40.0, "duck": 0.2}),
    ],
    variants=[
        Variant("open-deck-top-level", "Roof Deck", "Open sky over the top level, so the slap goes away instead of coming back.",
                audio={"a_room.mix": 0.15, "a_room.decay_s": 0.8,
                       "a_hum.level_db": -64.0, "a_bed.level_db": -50.0}),
        Variant("deep-level", "Level P4", "Four floors down the ramps keep handing the sound back.",
                audio={"a_room.mix": 0.45, "a_room.decay_s": 2.4, "a_slap.repeats": 6}),
    ],
))


# nearest: audio-tiled-bathroom-1980; differs: a tall narrow shaft with a fast
# ringing flutter plus a slower landing return, not one small bright box.
register_preset(Preset(
    id="audio-stairwell-1990",
    name="Concrete Stairwell",
    family="audio",
    era="1990",
    desc="A concrete fire stair: a 35 ms flutter ringing up the shaft eight times, a slower return off the landings overhead and steel handrail brightness on every transient.",
    tagline="Tall narrow flutter, metal-rail ring",
    tags=("audio-only", "90s", "room", "stairwell", "concrete"),
    keywords=("stairwell", "concrete", "flutter", "narrow", "tall", "ring",
              "1990s", "echo", "fire-escape", "hallway"),
    video=[],
    audio=[
        ("a_bandlimit", {"low_hz": 100.0, "high_hz": 9000.0, "order": 3}),
        ("a_room", {"mode": "room", "size": 1.2, "decay_s": 2.6, "damp": 0.25,
                    "predelay_ms": 8.0, "mix": 0.4}),
        ("a_slap", {"delay_ms": 35.0, "gain_db": -5.0, "repeats": 8, "damp": 0.15}),
        ("a_slap", {"delay_ms": 210.0, "gain_db": -14.0, "repeats": 3, "damp": 0.5}),
    ],
    variants=[
        Variant("carpeted-stairs", "Carpeted Stairs", "An office tower stair with carpet on the treads and half the ring gone.",
                audio={"a_room.damp": 0.7, "a_room.decay_s": 1.2, "a_room.mix": 0.25,
                       "a_slap.gain_db": -12.0}),
        Variant("hospital-stairwell", "Hospital Stair", "Twelve floors of painted block and a flutter that never quite stops.",
                audio={"a_room.decay_s": 3.2, "a_slap.repeats": 10,
                       "a_slap#2.gain_db": -10.0}),
    ],
))


# nearest: audio-mp3-2002; differs: a sub-band wireless codec plus hard DSP
# loudness and a single small plastic driver, not a bare file.
register_preset(Preset(
    id="audio-bluetooth-speaker-2015",
    name="Bluetooth Speaker",
    family="audio",
    era="2015",
    desc="A portable wireless box by the pool: sub-band codec haze on the cymbals, DSP loudness holding every bar at one level and a single small driver in a plastic shell.",
    tagline="SBC codec haze, one-driver box, DSP loud",
    tags=("audio-only", "2010s", "bluetooth", "codec", "speaker"),
    keywords=("bluetooth", "speaker", "2010s", "sbc", "portable", "dsp", "loud",
              "pool", "party", "wireless"),
    video=[],
    audio=[
        ("a_codec_aac", {"kbps": 64, "mono": False}),
        ("a_compressor", {"threshold_db": -14.0, "ratio": 8.0, "attack_ms": 1.0,
                          "release_ms": 150.0, "knee_db": 3.0, "makeup_db": 5.0}),
        ("a_bandlimit", {"low_hz": 70.0, "high_hz": 13000.0, "order": 3}),
        ("a_speaker", {"device": "cellphone_2008", "strength": 0.62, "cabinet_knock": 0.45}),
        ("a_room", {"enabled": False, "mode": "room", "size": 3.0, "decay_s": 1.2,
                    "damp": 0.4, "predelay_ms": 20.0, "mix": 0.3}),
    ],
    variants=[
        Variant("premium-2020", "Premium Model", "Five years on: a better codec, a bigger driver and less panic in the limiter.",
                audio={"a_codec_aac.kbps": 128, "a_speaker.strength": 0.3,
                       "a_compressor.makeup_db": 2.0}),
        Variant("distant-across-pool", "Across The Pool", "Somebody else's playlist arriving over thirty feet of open water.",
                audio={"a_room.enabled": True, "a_room.mix": 0.35,
                       "a_bandlimit.low_hz": 100.0, "a_bandlimit.high_hz": 6000.0}),
    ],
))


# nearest: audio-bluetooth-speaker-2015; differs: an upward-firing puck on a hard
# kitchen counter, higher stream rate and a live tiled room in the chain.
register_preset(Preset(
    id="audio-smart-speaker-kitchen-2018",
    name="Kitchen Smart Speaker",
    family="audio",
    era="2018",
    desc="A voice-assistant puck on a kitchen counter: a 96 kbps stream, small-driver DSP working hard at the bottom and a tiled room answering from three feet away.",
    tagline="DSP puck, kitchen tile, stream squeeze",
    tags=("audio-only", "2010s", "smart-speaker", "streaming", "kitchen"),
    keywords=("smart-speaker", "2010s", "kitchen", "puck", "dsp", "streaming",
              "alexa", "tile", "podcast", "morning"),
    video=[],
    audio=[
        ("a_codec_aac", {"kbps": 96, "mono": False}),
        ("a_compressor", {"threshold_db": -14.0, "ratio": 5.0, "attack_ms": 4.0,
                          "release_ms": 200.0, "knee_db": 4.0, "makeup_db": 3.0}),
        ("a_bandlimit", {"low_hz": 160.0, "high_hz": 15000.0, "order": 3}),
        ("a_speaker", {"device": "laptop_2006", "strength": 0.78, "cabinet_knock": 0.2}),
        ("a_room", {"mode": "room", "size": 1.2, "decay_s": 0.6, "damp": 0.4,
                    "predelay_ms": 6.0, "mix": 0.24}),
        ("a_room", {"enabled": False, "mode": "chamber", "size": 3.5, "decay_s": 2.2,
                    "damp": 0.5, "predelay_ms": 25.0, "mix": 0.45}),
    ],
    variants=[
        Variant("bedroom-mini", "Bedroom Mini", "The small one on a nightstand, close enough that the room never gets a turn.",
                audio={"a_room.mix": 0.1, "a_speaker.strength": 0.9,
                       "a_bandlimit.low_hz": 160.0}),
        Variant("whole-home-group", "Whole-Home Group", "Four pucks in four rooms, none of them quite in time with each other.",
                audio={"a_room#2.enabled": True, "a_room#2.mix": 0.5,
                       "a_room.mix": 0.1}),
    ],
))


# nearest: audio-tv-speaker-1975; differs: a 1955 tube output stage, a narrower
# cone and heavier intercarrier buzz in a lacquered cabinet.
register_preset(Preset(
    id="audio-console-tv-1955",
    name="Console Television",
    family="audio",
    era="1955",
    desc="A 1955 console receiver: one six-inch cone in a lacquered cabinet, intercarrier buzz riding the dialogue and output tubes warming everything that passes them.",
    tagline="Six-inch cone, tube warmth, carrier buzz",
    tags=("audio-only", "50s", "tv", "broadcast", "console-tv"),
    keywords=("console-tv", "1950s", "tv-sound", "tube", "cone", "buzz",
              "living-room", "cabinet", "black-and-white-era", "fifties"),
    video=[],
    audio=[
        ("a_bandlimit", {"low_hz": 100.0, "high_hz": 6500.0, "order": 4}),
        ("a_mono", {"amount": 1.0}),
        ("a_tv_sound", {"hz": "60", "buzz_db": -50.0, "hum_db": -56.0, "comp": 0.5}),
        ("a_tube_amp", {"drive": 1.8, "sag": 0.4, "microphonics": 0.12, "hum_db": -58.0}),
        ("a_speaker", {"device": "tv_mono_1965", "strength": 1.0, "cabinet_knock": 0.4}),
    ],
    variants=[
        Variant("dealer-fresh", "Dealer Fresh", "Off the showroom floor with the buzz trimmed and the tubes still matched.",
                audio={"a_tv_sound.buzz_db": -60.0, "a_tv_sound.hum_db": -64.0,
                       "a_tube_amp.sag": 0.2, "a_tube_amp.microphonics": 0.04}),
        Variant("aging-tubes-1962", "Aging Tubes", "Seven years later the supply sags on every loud line and the sound rings back into the cabinet.",
                audio={"a_tube_amp.sag": 0.7, "a_tube_amp.drive": 2.4,
                       "a_tube_amp.microphonics": 0.35, "a_tv_sound.buzz_db": -44.0}),
    ],
))


# nearest: audio-optical-1942; differs: the same era of optical track played
# through a stage horn cluster into a balconied auditorium.
register_preset(Preset(
    id="audio-movie-palace-1935",
    name="Movie Palace",
    family="audio",
    era="1935",
    desc="A three-thousand-seat picture palace: a 1935 optical track through a horn cluster behind the screen, with the balcony handing it back two and a half seconds later.",
    tagline="Academy optical, horn cluster, balcony reverb",
    tags=("audio-only", "30s", "film", "optical", "cinema"),
    keywords=("movie-palace", "1930s", "cinema", "academy", "optical", "horn",
              "balcony", "theater", "reverb", "rko"),
    video=[],
    audio=[
        ("a_optical_track", {"low_hz": 120.0, "high_hz": 5000.0,
                             "academy_rolloff": "newsreel_1930s", "cell_noise": -46.0,
                             "flutter": 0.4, "drive": 1.5}),
        ("a_mono", {"amount": 1.0}),
        ("a_speaker", {"device": "intercom_horn_1950", "strength": 0.75}),
        ("a_room", {"mode": "chamber", "size": 4.0, "decay_s": 2.4, "damp": 0.5,
                    "predelay_ms": 30.0, "mix": 0.3}),
    ],
    variants=[
        Variant("front-row", "Front Row", "Close enough to the horns that the room barely gets a word in.",
                audio={"a_room.mix": 0.15, "a_room.predelay_ms": 10.0,
                       "a_speaker.strength": 0.6}),
        Variant("second-run-house-1950", "Second-Run House", "A tired print in a smaller neighbourhood theatre with the fader pushed up.",
                audio={"a_optical_track.cell_noise": -40.0, "a_optical_track.drive": 2.0,
                       "a_room.decay_s": 1.6, "a_room.mix": 0.25}),
    ],
))


# nearest: audio-tv-speaker-1975; differs: an aluminium window pot speaker fed by
# an optical track, heard inside a car cabin with the next row bleeding in.
register_preset(Preset(
    id="audio-drive-in-speaker-1958",
    name="Drive-In Window Speaker",
    family="audio",
    era="1958",
    desc="The pot speaker hooked over a car window: a 1940s optical track squeezed through four inches of aluminium, upholstery soaking up the rest and the next row arriving late.",
    tagline="Aluminum pot speaker, rattle, lot bleed",
    tags=("audio-only", "50s", "drive-in", "film", "optical"),
    keywords=("drive-in", "speaker", "1950s", "window", "aluminum", "rattle",
              "car", "lot", "movie", "summer"),
    video=[],
    audio=[
        ("a_optical_track", {"low_hz": 150.0, "high_hz": 5500.0,
                             "academy_rolloff": "feature_1940s", "cell_noise": -50.0,
                             "flutter": 0.4, "drive": 1.5}),
        ("a_mono", {"amount": 1.0}),
        ("a_distortion", {"enabled": False, "type": "soft", "drive": 3.0, "tone": 0.2}),
        ("a_speaker", {"device": "drive_in_speaker_1958", "strength": 1.0,
                       "cabinet_knock": 0.5}),
        ("a_room", {"mode": "room", "size": 0.7, "decay_s": 0.35, "damp": 0.6,
                    "predelay_ms": 5.0, "mix": 0.2}),
        ("a_slap", {"delay_ms": 180.0, "gain_db": -20.0, "repeats": 2, "damp": 0.7}),
    ],
    variants=[
        Variant("volume-cranked", "Volume Cranked", "The knob is at the stop and the little transformer gives up on the loud scenes.",
                audio={"a_distortion.enabled": True, "a_distortion.drive": 3.5,
                       "a_speaker.cabinet_knock": 0.75}),
        Variant("window-down-summer", "Windows Down", "Glass out of the way, so half the lot is in the mix with you.",
                audio={"a_room.mix": 0.05, "a_slap.gain_db": -14.0,
                       "a_slap.repeats": 3}),
    ],
))


# nearest: none; the library has earbuds as a playback device but no leak heard
# from outside them.
register_preset(Preset(
    id="audio-earbud-leak-2007",
    name="Earbud Leak on the Bus",
    family="audio",
    era="2007",
    desc="The white earbuds two seats over: a 128 kbps file escaping as 2 to 10 kHz tick with no bass left in it, sitting on top of the bus ventilation.",
    tagline="Tinny 2-10 kHz leak, no bass, bus hum",
    tags=("audio-only", "2000s", "earbuds", "mp3", "commute"),
    keywords=("earbud", "leak", "2000s", "bus", "tinny", "ipod",
              "someone-elses-music", "commute", "annoying", "treble"),
    video=[],
    audio=[
        ("a_codec_mp3", {"kbps": "128", "mono": False}),
        ("a_speaker", {"device": "earbud_2005", "strength": 1.0}),
        ("a_bandlimit", {"low_hz": 1800.0, "high_hz": 11000.0, "order": 6}),
        ("a_gain", {"db": -4.0}),
        ("a_bed", {"bed": "air_handler_hall", "level_db": -46.0, "duck": 0.0}),
    ],
    variants=[
        Variant("seat-next-to-you", "Next Seat", "Close enough that some of the low mid survives the trip out of the ear.",
                audio={"a_gain.db": 0.0, "a_bandlimit.low_hz": 900.0,
                       "a_bandlimit.high_hz": 12000.0}),
        Variant("across-the-aisle", "Across The Aisle", "Four feet away it is pure hi-hat and nothing else.",
                audio={"a_gain.db": -12.0, "a_bandlimit.low_hz": 2000.0,
                       "a_bandlimit.high_hz": 9000.0}),
    ],
))
