"""Audio-only archival presets, third wave: capture media through magnetic film.

Video passes through untouched. Every chain treats the supplied soundtrack and
adds only physical recording, playback and preservation artifacts.
"""

from ..engine.presets import Preset, Variant, register_preset


register_preset(Preset(
    id="audio-wax-cylinder-1905",
    name="Brown Wax Cylinder",
    family="audio",
    era="1905",
    desc="A brown-wax cylinder through an acoustic horn: two turns per second, papery surface wash, pinched capsule resonance and blunt groove impacts.",
    tagline="Fast wax wow, papery wash, horn mids",
    tags=("audio-only", "1900s", "cylinder", "acoustic"),
    audio=[
        ("a_historical_mic", {"profile": "carbon_1925", "amount": 0.65,
                              "overload": 0.28, "self_noise_db": -55.0}),
        ("a_disc_medium", {"medium": "wax_cylinder_1905", "wear": 0.55,
                           "surface_db": -42.0, "impacts": 14.0, "wow_cents": 18.0}),
        ("a_speaker", {"device": "gramophone_horn_1915", "strength": 0.62}),
    ],
    variants=[
        Variant("clean-transfer", "Clean Archive Transfer", "The best cylinder in the box, centered carefully and played once.",
                audio={"a_disc_medium.wear": 0.22, "a_disc_medium.surface_db": -49.0,
                       "a_disc_medium.impacts": 4.0, "a_disc_medium.wow_cents": 9.0}),
        Variant("shaved-thin", "Shaved Too Thin", "The reused cylinder wall is faint, rough and visibly eccentric in the sound.",
                audio={"a_disc_medium.wear": 0.9, "a_disc_medium.surface_db": -35.0,
                       "a_disc_medium.impacts": 30.0, "a_disc_medium.wow_cents": 30.0}),
    ],
))


register_preset(Preset(
    id="audio-wax-dictation-1922",
    name="Office Dictation Cylinder",
    family="audio",
    era="1922",
    desc="A wax office dictation recorded close to a carbon mouthpiece: narrow resonant speech, slow rotational sway and stylus wash under every pause.",
    tagline="Carbon speech, slow wax sway, stylus wash",
    tags=("audio-only", "20s", "cylinder", "dictation"),
    audio=[
        ("a_historical_mic", {"profile": "carbon_1925", "amount": 0.9,
                              "proximity": 0.18, "overload": 0.38, "self_noise_db": -51.0}),
        ("a_disc_medium", {"medium": "wax_dictation_1922", "wear": 0.42,
                           "surface_db": -44.0, "impacts": 8.0, "wow_cents": 11.0}),
        ("a_compressor", {"threshold_db": -24.0, "ratio": 3.8, "attack_ms": 5.0,
                          "release_ms": 260.0}),
    ],
    variants=[
        Variant("fresh-blank", "Fresh Blank", "A new cylinder and a recently adjusted reproducer.",
                audio={"a_disc_medium.wear": 0.15, "a_disc_medium.surface_db": -51.0,
                       "a_historical_mic.overload": 0.2}),
        Variant("filing-room", "Filing-Room Copy", "The cylinder has been handled by every clerk in the building.",
                audio={"a_disc_medium.wear": 0.82, "a_disc_medium.impacts": 24.0,
                       "a_disc_medium.surface_db": -37.0}),
    ],
))


register_preset(Preset(
    id="audio-aluminum-disc-1934",
    name="Aluminum Home Disc",
    family="audio",
    era="1934",
    desc="A home-cut bare aluminum disc: carbon-mic bite, metallic cutter resonance, steady stylus scrape and small hard pits in the recording surface.",
    tagline="Metallic cutter ring and hard surface scrape",
    tags=("audio-only", "30s", "disc", "home-recording"),
    audio=[
        ("a_historical_mic", {"profile": "carbon_1925", "amount": 0.72,
                              "overload": 0.32, "self_noise_db": -56.0}),
        ("a_disc_medium", {"medium": "aluminum_disc_1934", "wear": 0.46,
                           "surface_db": -43.0, "impacts": 12.0, "wow_cents": 8.0}),
        ("a_tube_amp", {"drive": 1.8, "sag": 0.28, "hum_db": -52.0}),
    ],
    variants=[
        Variant("fresh-cut", "Fresh Cut", "Still warm from the cutter with only a low steady scrape.",
                audio={"a_disc_medium.wear": 0.1, "a_disc_medium.surface_db": -49.0,
                       "a_disc_medium.impacts": 3.0}),
        Variant("warped-blank", "Warped Blank", "The platter rises once per turn and the stylus argues with every pit.",
                audio={"a_disc_medium.wear": 0.72, "a_disc_medium.wow_cents": 20.0,
                       "a_disc_medium.impacts": 28.0}),
    ],
))


register_preset(Preset(
    id="audio-acetate-home-1947",
    name="Home Acetate Recorder",
    family="audio",
    era="1947",
    desc="A lacquer-coated home recording disc: crystal-mic presence, small tube-stage sag, soft groove wash and the top edge worn gray by repeat plays.",
    tagline="Crystal presence, lacquer wash, tube sag",
    tags=("audio-only", "40s", "acetate", "home-recording"),
    audio=[
        ("a_historical_mic", {"profile": "crystal_1940", "amount": 0.82,
                              "overload": 0.2, "self_noise_db": -58.0}),
        ("a_disc_medium", {"medium": "acetate_home_1947", "wear": 0.38,
                           "surface_db": -48.0, "impacts": 7.0, "wow_cents": 6.0}),
        ("a_tube_amp", {"drive": 2.0, "sag": 0.42, "microphonics": 0.12,
                        "hum_db": -53.0}),
        ("a_room", {"mode": "room", "size": 0.75, "decay_s": 0.32,
                    "mix": 0.1, "damp": 0.72}),
    ],
    variants=[
        Variant("family-copy", "Family Copy", "A careful living-room side with the recording level kept out of the red.",
                audio={"a_historical_mic.overload": 0.08, "a_disc_medium.wear": 0.2,
                       "a_tube_amp.drive": 1.5}),
        Variant("closet-find", "Closet Find", "The lacquer is crazed and the crystal microphone overloaded at every laugh.",
                audio={"a_disc_medium.wear": 0.82, "a_disc_medium.surface_db": -39.0,
                       "a_disc_medium.impacts": 22.0, "a_historical_mic.overload": 0.6}),
    ],
))


register_preset(Preset(
    id="audio-ribbon-studio-1938",
    name="Ribbon Studio Chain",
    family="audio",
    era="1938",
    desc="A velocity ribbon into a tube console: broad soft midrange, proximity weight, transformer sag and a short dark studio chamber around the mono feed.",
    tagline="Soft ribbon mids, transformer give, chamber",
    tags=("audio-only", "30s", "microphone", "studio"),
    audio=[
        ("a_historical_mic", {"profile": "ribbon_1938", "amount": 0.92,
                              "proximity": 0.32, "overload": 0.12, "self_noise_db": -64.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_tube_amp", {"drive": 2.2, "sag": 0.55, "microphonics": 0.08,
                        "hum_db": -58.0}),
        ("a_compressor", {"threshold_db": -19.0, "ratio": 2.4, "attack_ms": 14.0,
                          "release_ms": 300.0}),
        ("a_room", {"mode": "chamber", "size": 0.7, "decay_s": 0.55,
                    "mix": 0.14, "damp": 0.78, "predelay_ms": 4.0}),
    ],
    variants=[
        Variant("close-ribbon", "Close Ribbon", "The performer leans into the ribbon and the low end gathers at the grille.",
                audio={"a_historical_mic.proximity": 0.72, "a_historical_mic.overload": 0.26,
                       "a_tube_amp.sag": 0.7}),
        Variant("room-mic", "Across The Studio", "Less proximity, more chamber and a quieter capsule overload.",
                audio={"a_historical_mic.proximity": 0.0, "a_room.mix": 0.28,
                       "a_room.decay_s": 0.9}),
    ],
))


register_preset(Preset(
    id="audio-carbon-newsreel-1941",
    name="Carbon Newsreel Chain",
    family="audio",
    era="1941",
    desc="A carbon field microphone printed to variable-area optical sound: hard speech resonance, photographic squeeze, cell grain and distant 35 mm booth machinery.",
    tagline="Carbon bite, optical grain, distant booth",
    tags=("audio-only", "40s", "newsreel", "optical"),
    audio=[
        ("a_historical_mic", {"profile": "carbon_1925", "amount": 0.78,
                              "overload": 0.52, "handling": 0.14, "self_noise_db": -55.0}),
        ("a_optical_track", {"low_hz": 120.0, "high_hz": 5200.0,
                             "academy_rolloff": "newsreel_1930s", "cell_noise": -45.0,
                             "flutter": 0.7, "drive": 1.9}),
        ("a_mono", {"amount": 1.0}),
        ("a_compressor", {"threshold_db": -23.0, "ratio": 5.0, "attack_ms": 4.0,
                          "release_ms": 170.0}),
        ("a_projector", {"machine": "proj_35mm_booth", "level_db": -48.0,
                         "distance": 0.72}),
    ],
    variants=[
        Variant("field-report", "Field Report", "The microphone cable is long, the capsule is hot and the stand takes one knock.",
                audio={"a_historical_mic.handling": 0.55, "a_historical_mic.overload": 0.72,
                       "a_optical_track.cell_noise": -42.0}),
        Variant("vault-track", "Vault Track", "A protected optical element with steadier sprockets and a lower cell floor.",
                audio={"a_optical_track.cell_noise": -54.0, "a_optical_track.flutter": 0.25,
                       "a_projector.level_db": -56.0}),
    ],
))


register_preset(Preset(
    id="audio-full-track-master-1953",
    name="Full-Track Tape Master",
    family="audio",
    era="1953",
    desc="A full-track mono master at 15 ips: ribbon capture, wide head response, modest magnetic compression, low tape hiss and a faint adjacent-wind pre-echo.",
    tagline="Wide mono tape, soft iron, faint pre-echo",
    tags=("audio-only", "50s", "reel", "master"),
    audio=[
        ("a_historical_mic", {"profile": "ribbon_1938", "amount": 0.62,
                              "proximity": 0.18, "overload": 0.08, "self_noise_db": -69.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_analog_dub", {"format": "reel_15ips", "generations": 1,
                          "alignment": 0.06, "compression": 0.26, "hiss_db": -66.0}),
        ("a_print_through", {"delay_s": 1.15, "pre_echo_db": -56.0,
                             "post_echo_db": -62.0, "layers": 1, "softness": 0.42}),
        ("a_tube_amp", {"drive": 1.65, "sag": 0.3, "hum_db": -66.0}),
    ],
    variants=[
        Variant("first-generation", "First Generation", "The master before safety copies, with almost no alignment loss.",
                audio={"a_analog_dub.alignment": 0.01, "a_analog_dub.hiss_db": -72.0,
                       "a_print_through.pre_echo_db": -64.0}),
        Variant("stored-head-out", "Stored Head-Out", "Decades on a tight pack make the next loud phrase arrive early.",
                audio={"a_print_through.pre_echo_db": -38.0, "a_print_through.post_echo_db": -48.0,
                       "a_print_through.layers": 2}),
    ],
))


register_preset(Preset(
    id="audio-magnetic-film-1957",
    name="35 mm Magnetic Film",
    family="audio",
    era="1957",
    desc="A mono magnetic film dubber: broad response, controlled head saturation, slight sprocket-linked flutter and a projection-booth floor well below the program.",
    tagline="Broad mag track, sprocket flutter, booth floor",
    tags=("audio-only", "50s", "film", "magnetic"),
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_analog_dub", {"format": "reel_15ips", "generations": 2,
                          "alignment": 0.09, "compression": 0.34, "hiss_db": -64.0}),
        ("a_wow_flutter", {"wow_depth": 2.0, "flutter_depth": 2.8,
                           "cogging": 0.12, "cogging_hz": 24.0}),
        ("a_print_through", {"delay_s": 0.72, "pre_echo_db": -58.0,
                             "post_echo_db": -60.0, "softness": 0.35}),
        ("a_compressor", {"threshold_db": -19.0, "ratio": 2.6, "attack_ms": 10.0,
                          "release_ms": 240.0}),
        ("a_projector", {"machine": "proj_35mm_booth", "level_db": -55.0,
                         "distance": 0.82}),
    ],
    variants=[
        Variant("dub-stage", "Dub Stage", "The mag roll on a calibrated machine, with the booth machinery absent.",
                audio={"a_analog_dub.alignment": 0.03, "a_wow_flutter.flutter_depth": 1.0,
                       "a_projector.level_db": -60.0}),
        Variant("roadshow-copy", "Roadshow Copy", "Another magnetic generation with audible alignment drift and print-through.",
                audio={"a_analog_dub.generations": 4, "a_analog_dub.alignment": 0.32,
                       "a_print_through.pre_echo_db": -44.0}),
    ],
))


register_preset(Preset(
    id="audio-broadcast-reel-1961",
    name="Broadcast Reel Copy",
    family="audio",
    era="1961",
    desc="A 7.5 ips station reel: broadcast-dynamic presence, two tape generations, automatic level riding and a low pre-echo from years stored tails-out.",
    tagline="Station presence, level riding, tape ghost",
    tags=("audio-only", "60s", "broadcast", "reel"),
    audio=[
        ("a_historical_mic", {"profile": "broadcast_dynamic_1955", "amount": 0.45,
                              "proximity": 0.16, "overload": 0.12, "self_noise_db": -68.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_analog_dub", {"format": "reel_75ips", "generations": 2,
                          "alignment": 0.16, "compression": 0.35, "hiss_db": -61.0}),
        ("a_print_through", {"delay_s": 1.0, "pre_echo_db": -50.0,
                             "post_echo_db": -57.0, "softness": 0.52}),
        ("a_agc", {"target_db": -17.0, "max_gain_db": 7.0, "attack_ms": 35.0,
                   "release_ms": 760.0, "amount": 0.48}),
        ("a_hum", {"hz": "60", "level_db": -60.0, "buzz": 0.12}),
    ],
    variants=[
        Variant("network-master", "Network Master", "One generation, aligned heads and the level rider barely moving.",
                audio={"a_analog_dub.generations": 1, "a_analog_dub.alignment": 0.04,
                       "a_agc.amount": 0.2, "a_print_through.pre_echo_db": -60.0}),
        Variant("affiliate-copy", "Affiliate Copy", "The station copy has crossed three machines and one questionable patch bay.",
                audio={"a_analog_dub.generations": 4, "a_analog_dub.alignment": 0.48,
                       "a_analog_dub.hiss_db": -55.0, "a_agc.amount": 0.75}),
    ],
))


register_preset(Preset(
    id="audio-portable-reel-1965",
    name="Portable Reel Recorder",
    family="audio",
    era="1965",
    desc="A battery portable at 3.75 ips: crystal-mic edge, capstan drift, head-bump warmth, bright tape hiss and AGC opening up between phrases.",
    tagline="Crystal edge, capstan drift, breathing hiss",
    tags=("audio-only", "60s", "reel", "portable"),
    audio=[
        ("a_historical_mic", {"profile": "crystal_1940", "amount": 0.72,
                              "overload": 0.32, "handling": 0.18, "self_noise_db": -55.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_analog_dub", {"format": "reel_375ips", "generations": 1,
                          "alignment": 0.25, "compression": 0.42, "hiss_db": -51.0}),
        ("a_wow_flutter", {"wow_depth": 9.0, "flutter_depth": 5.0,
                           "drift_long": 0.35, "cogging": 0.18, "cogging_hz": 50.0}),
        ("a_agc", {"target_db": -18.0, "max_gain_db": 10.0, "attack_ms": 18.0,
                   "release_ms": 620.0, "amount": 0.7}),
    ],
    variants=[
        Variant("fresh-batteries", "Fresh Batteries", "The motor is steady and the microphone stand stays untouched.",
                audio={"a_wow_flutter.wow_depth": 4.0, "a_wow_flutter.drift_long": 0.08,
                       "a_historical_mic.handling": 0.0}),
        Variant("field-batteries", "Field Batteries", "The motor wanders, the reel pulls and every hand reaches the microphone body.",
                audio={"a_wow_flutter.wow_depth": 22.0, "a_wow_flutter.speed_pct": -1.2,
                       "a_historical_mic.handling": 0.72, "a_analog_dub.hiss_db": -45.0}),
    ],
))


register_preset(Preset(
    id="audio-16mm-mag-stripe-1969",
    name="16 mm Magnetic Stripe",
    family="audio",
    era="1969",
    desc="A narrow magnetic stripe on 16 mm release film: modest top end, mono head smear, stripe hiss, short oxide losses and the projector just behind the wall.",
    tagline="Narrow mag stripe, oxide dips, projector wall",
    tags=("audio-only", "60s", "16mm", "magnetic"),
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_analog_dub", {"format": "reel_375ips", "generations": 2,
                          "alignment": 0.34, "compression": 0.3, "hiss_db": -53.0}),
        ("a_wow_flutter", {"wow_depth": 3.0, "flutter_depth": 5.0,
                           "cogging": 0.22, "cogging_hz": 24.0}),
        ("a_tape_dropouts", {"rate": 8.0, "depth_db": 22.0, "azimuth": 0.28}),
        ("a_projector", {"machine": "proj_16mm", "level_db": -48.0,
                         "distance": 0.7}),
    ],
    variants=[
        Variant("fresh-stripe", "Fresh Stripe", "A new print on a clean playback head.",
                audio={"a_analog_dub.alignment": 0.1, "a_tape_dropouts.rate": 1.0,
                       "a_tape_dropouts.azimuth": 0.05, "a_projector.level_db": -55.0}),
        Variant("school-circuit", "School Circuit", "The stripe has shed at every splice and the projector shares the room.",
                audio={"a_tape_dropouts.rate": 32.0, "a_tape_dropouts.depth_db": 34.0,
                       "a_analog_dub.hiss_db": -46.0, "a_projector.level_db": -39.0,
                       "a_projector.distance": 0.28}),
    ],
))


register_preset(Preset(
    id="audio-nagra-location-1970",
    name="Nagra Location Track",
    family="audio",
    era="1970",
    desc="A mono pilot-tone field reel: directional microphone presence, firm limiter action, fine 7.5 ips hiss and restrained transport flutter under the location air.",
    tagline="Shotgun presence, firm limiter, fine reel hiss",
    tags=("audio-only", "70s", "location", "reel"),
    audio=[
        ("a_historical_mic", {"profile": "shotgun_1975", "amount": 0.75,
                              "proximity": 0.08, "overload": 0.12, "handling": 0.1,
                              "self_noise_db": -66.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_analog_dub", {"format": "reel_75ips", "generations": 1,
                          "alignment": 0.06, "compression": 0.22, "hiss_db": -65.0}),
        ("a_wow_flutter", {"wow_depth": 2.2, "flutter_depth": 1.8,
                           "drift_long": 0.05}),
        ("a_compressor", {"threshold_db": -16.0, "ratio": 5.5, "attack_ms": 2.5,
                          "release_ms": 180.0, "knee_db": 3.0}),
    ],
    variants=[
        Variant("close-boom", "Close Boom", "The microphone sits just out of frame with little room and a touch of proximity.",
                audio={"a_historical_mic.proximity": 0.35, "a_historical_mic.handling": 0.02,
                       "a_compressor.threshold_db": -13.0}),
        Variant("run-and-gun", "Run And Gun", "The boom moves, the limiter works and the transport has taken one hard day.",
                audio={"a_historical_mic.handling": 0.68, "a_historical_mic.overload": 0.38,
                       "a_wow_flutter.flutter_depth": 5.5, "a_compressor.threshold_db": -22.0}),
    ],
))
