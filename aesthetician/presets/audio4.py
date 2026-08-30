"""Audio-only archival presets, fourth wave: consumer tape and video carriers."""

from ..engine.presets import Preset, Variant, register_preset


register_preset(Preset(
    id="audio-dictation-belt-1964",
    name="Dictation Belt",
    family="audio",
    era="1964",
    desc="A grooved plastic office belt: close dynamic-mic speech, long-cycle speed sway, dry plastic scrape and a hard mechanical playback edge.",
    tagline="Plastic scrape, long sway, office speech",
    tags=("audio-only", "60s", "dictation", "belt"),
    audio=[
        ("a_historical_mic", {"profile": "broadcast_dynamic_1955", "amount": 0.78,
                              "proximity": 0.24, "overload": 0.24, "self_noise_db": -54.0}),
        ("a_disc_medium", {"medium": "dictation_belt_1964", "wear": 0.5,
                           "surface_db": -42.0, "impacts": 9.0, "wow_cents": 8.0}),
        ("a_agc", {"target_db": -17.0, "max_gain_db": 11.0, "attack_ms": 12.0,
                   "release_ms": 520.0, "amount": 0.78}),
        ("a_speaker", {"device": "clock_radio_1988", "strength": 0.58}),
    ],
    variants=[
        Variant("new-belt", "New Belt", "A clean office blank with the stylus pressure set correctly.",
                audio={"a_disc_medium.wear": 0.12, "a_disc_medium.surface_db": -50.0,
                       "a_disc_medium.impacts": 2.0}),
        Variant("case-file", "Case-File Copy", "The belt has been replayed, sleeved badly and replayed again.",
                audio={"a_disc_medium.wear": 0.88, "a_disc_medium.surface_db": -35.0,
                       "a_disc_medium.impacts": 26.0, "a_agc.amount": 1.0}),
    ],
))


register_preset(Preset(
    id="audio-broadcast-cart-1976",
    name="Broadcast Cart",
    family="audio",
    era="1976",
    desc="An endless-loop NAB cartridge: compressed 7.5 ips tone, fast transport settle, loop-pack wow, splice-area dropouts and a bright station noise floor.",
    tagline="Fast cart settle, loop wow, splice wear",
    tags=("audio-only", "70s", "broadcast", "cart"),
    audio=[
        ("a_mono", {"amount": 1.0}),
        ("a_analog_dub", {"format": "broadcast_cart", "generations": 2,
                          "alignment": 0.22, "compression": 0.52, "hiss_db": -54.0}),
        ("a_wow_flutter", {"wow_depth": 7.0, "flutter_depth": 3.0,
                           "start_wobble": True, "cogging": 0.22, "cogging_hz": 30.0}),
        ("a_print_through", {"delay_s": 0.48, "pre_echo_db": -55.0,
                             "post_echo_db": -50.0, "softness": 0.58}),
        ("a_tape_dropouts", {"rate": 7.0, "depth_db": 20.0, "azimuth": 0.18}),
        ("a_compressor", {"threshold_db": -18.0, "ratio": 4.2, "attack_ms": 5.0,
                          "release_ms": 190.0}),
    ],
    variants=[
        Variant("fresh-cart", "Fresh Cart", "A newly loaded shell on a clean deck with one quiet record pass.",
                audio={"a_analog_dub.generations": 1, "a_analog_dub.alignment": 0.05,
                       "a_tape_dropouts.rate": 0.5, "a_wow_flutter.wow_depth": 3.0}),
        Variant("overnight-cart", "Overnight Cart", "The same cart has fired every hour all week and the loop pack is dragging.",
                audio={"a_analog_dub.generations": 4, "a_wow_flutter.wow_depth": 16.0,
                       "a_tape_dropouts.rate": 24.0, "a_analog_dub.hiss_db": -47.0}),
    ],
))


register_preset(Preset(
    id="audio-cassette-field-1979",
    name="Cassette Field Recorder",
    family="audio",
    era="1979",
    desc="A portable cassette interview: wired lavalier chest tone, eager AGC, Type I hiss, capstan wander and Dolby B opening the top between words.",
    tagline="Lavalier chest, eager AGC, Dolby breath",
    tags=("audio-only", "70s", "cassette", "field"),
    audio=[
        ("a_historical_mic", {"profile": "lavalier_1972", "amount": 0.8,
                              "proximity": 0.3, "overload": 0.22, "handling": 0.12,
                              "self_noise_db": -58.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_analog_dub", {"format": "cassette", "generations": 1,
                          "alignment": 0.3, "compression": 0.42, "hiss_db": -52.0}),
        ("a_wow_flutter", {"wow_depth": 9.0, "flutter_depth": 6.0,
                           "drift_long": 0.22, "cogging": 0.16, "cogging_hz": 60.0}),
        ("a_noise_reduction", {"system": "dolby_b", "decode_error": -0.28,
                               "threshold_db": -35.0, "pumping": 0.42, "hiss_db": -54.0}),
        ("a_agc", {"target_db": -18.0, "max_gain_db": 10.0, "attack_ms": 16.0,
                   "release_ms": 680.0, "amount": 0.72}),
    ],
    variants=[
        Variant("tabletop", "Tabletop Interview", "The recorder stays still, the subject stays close and the batteries stay fresh.",
                audio={"a_historical_mic.handling": 0.0, "a_wow_flutter.wow_depth": 4.0,
                       "a_analog_dub.alignment": 0.12}),
        Variant("coat-pocket", "Coat Pocket", "Fabric reaches the microphone, the motor pulls and the level circuit chases every movement.",
                audio={"a_historical_mic.handling": 0.78, "a_wow_flutter.wow_depth": 20.0,
                       "a_wow_flutter.speed_pct": -1.0, "a_agc.amount": 1.0}),
    ],
))


register_preset(Preset(
    id="audio-boombox-dub-1983",
    name="Third-Generation Boombox Dub",
    family="audio",
    era="1983",
    desc="A cassette copied deck to deck to deck: shrinking high end, accumulating hiss, Dolby mistracking, wandering azimuth and the final boombox cabinet curve.",
    tagline="Three dubs, breathing hiss, boombox curve",
    tags=("audio-only", "80s", "cassette", "dub"),
    audio=[
        ("a_analog_dub", {"format": "cassette", "generations": 3,
                          "alignment": 0.5, "compression": 0.55, "hiss_db": -51.0}),
        ("a_noise_reduction", {"system": "dolby_b", "decode_error": -0.48,
                               "threshold_db": -36.0, "pumping": 0.62, "hiss_db": -50.0}),
        ("a_wow_flutter", {"wow_depth": 11.0, "flutter_depth": 7.0,
                           "drift_long": 0.45}),
        ("a_tape_dropouts", {"rate": 9.0, "depth_db": 24.0, "azimuth": 0.52}),
        ("a_channel_aging", {"width": 0.62, "imbalance_db": -1.4,
                             "crosstalk_db": -28.0, "skew_us": 140.0,
                             "phase_wander": 0.38, "mono_bass_hz": 180.0}),
        ("a_speaker", {"device": "boombox_1985", "strength": 0.58}),
    ],
    variants=[
        Variant("second-generation", "Second Generation", "One fewer copy and a deck whose heads almost agree.",
                audio={"a_analog_dub.generations": 2, "a_analog_dub.alignment": 0.24,
                       "a_tape_dropouts.azimuth": 0.25, "a_noise_reduction.decode_error": -0.22}),
        Variant("swap-meet", "Swap-Meet Copy", "Five decks, no calibration and a shell that pinches the tape at random.",
                audio={"a_analog_dub.generations": 5, "a_analog_dub.alignment": 0.82,
                       "a_tape_dropouts.rate": 28.0, "a_tape_dropouts.azimuth": 0.9,
                       "a_noise_reduction.pumping": 0.9}),
    ],
))


register_preset(Preset(
    id="audio-cassette-fourtrack-1987",
    name="Cassette Four-Track",
    family="audio",
    era="1987",
    desc="Four narrow tracks sharing a cassette: hot magnetic compression, pinched stereo width, head crosstalk, azimuth phase drift and dbx gain movement.",
    tagline="Narrow tracks, hot tape, dbx movement",
    tags=("audio-only", "80s", "cassette", "multitrack"),
    audio=[
        ("a_analog_dub", {"format": "cassette", "generations": 2,
                          "alignment": 0.28, "compression": 0.72, "hiss_db": -56.0}),
        ("a_tape_sat", {"drive": 3.4, "bump_db": 2.6, "hf_loss": 0.36}),
        ("a_noise_reduction", {"system": "dbx", "decode_error": 0.18,
                               "threshold_db": -40.0, "pumping": 0.58, "hiss_db": -59.0}),
        ("a_channel_aging", {"width": 0.7, "imbalance_db": 0.8,
                             "crosstalk_db": -24.0, "skew_us": -110.0,
                             "phase_wander": 0.42, "mono_bass_hz": 220.0}),
        ("a_wow_flutter", {"wow_depth": 7.0, "flutter_depth": 5.0,
                           "cogging": 0.12, "cogging_hz": 60.0}),
    ],
    variants=[
        Variant("two-track-bounce", "Two-Track Bounce", "A single internal bounce with the meters kept below the last red segment.",
                audio={"a_analog_dub.generations": 1, "a_tape_sat.drive": 2.2,
                       "a_channel_aging.crosstalk_db": -34.0, "a_noise_reduction.pumping": 0.3}),
        Variant("bounce-again", "Bounce Again", "Every track has visited another track and the dbx no longer follows cleanly.",
                audio={"a_analog_dub.generations": 4, "a_tape_sat.drive": 5.2,
                       "a_channel_aging.crosstalk_db": -17.0,
                       "a_noise_reduction.decode_error": 0.6}),
    ],
))


register_preset(Preset(
    id="audio-umatic-linear-1977",
    name="U-matic Linear Track",
    family="audio",
    era="1977",
    desc="A three-quarter-inch U-matic longitudinal track: mono broadcast mids, tape compression, bright track hiss, frame-rate switching residue and brief oxide losses.",
    tagline="U-matic mono, bright hiss, switch residue",
    tags=("audio-only", "70s", "umatic", "video"),
    audio=[
        ("a_video_tape_audio", {"format": "umatic_linear", "tracking": 0.28,
                                "dropout_rate": 6.0, "noise_db": -49.0,
                                "head_switch_db": -58.0, "compander_error": 0.0}),
        ("a_channel_aging", {"width": 0.0, "imbalance_db": 0.0,
                             "crosstalk_db": -48.0, "skew_us": 0.0,
                             "phase_wander": 0.0, "mono_bass_hz": 120.0}),
        ("a_agc", {"target_db": -17.0, "max_gain_db": 6.0, "attack_ms": 24.0,
                   "release_ms": 540.0, "amount": 0.48}),
    ],
    variants=[
        Variant("edit-master", "Edit Master", "A calibrated deck, one generation and almost no carrier loss.",
                audio={"a_video_tape_audio.tracking": 0.08, "a_video_tape_audio.dropout_rate": 0.5,
                       "a_video_tape_audio.noise_db": -56.0}),
        Variant("station-copy", "Station Copy", "A dub with rough tracking and a longitudinal track beginning to shed.",
                audio={"a_video_tape_audio.tracking": 0.72, "a_video_tape_audio.dropout_rate": 24.0,
                       "a_video_tape_audio.noise_db": -43.0, "a_agc.amount": 0.82}),
    ],
))


register_preset(Preset(
    id="audio-betamax-linear-1981",
    name="Betamax Linear Audio",
    family="audio",
    era="1981",
    desc="A Betamax longitudinal track: narrow mono head response, dense consumer tape hiss, mild level squeeze and small tracking holes near worn sections.",
    tagline="Narrow Beta track, dense hiss, small holes",
    tags=("audio-only", "80s", "betamax", "video"),
    audio=[
        ("a_video_tape_audio", {"format": "betamax_linear", "tracking": 0.34,
                                "dropout_rate": 7.0, "noise_db": -47.0,
                                "head_switch_db": -60.0, "compander_error": 0.05}),
        ("a_tape_dropouts", {"rate": 4.0, "depth_db": 18.0, "azimuth": 0.2}),
        ("a_mono", {"amount": 1.0}),
    ],
    variants=[
        Variant("new-tape", "New Tape", "A first-recording cassette on a deck whose audio head was just aligned.",
                audio={"a_video_tape_audio.tracking": 0.08, "a_video_tape_audio.noise_db": -53.0,
                       "a_tape_dropouts.rate": 0.0, "a_tape_dropouts.azimuth": 0.05}),
        Variant("rental-copy", "Rental Copy", "Repeated passes have dulled the head contact and raised the noise between every word.",
                audio={"a_video_tape_audio.tracking": 0.8, "a_video_tape_audio.dropout_rate": 28.0,
                       "a_video_tape_audio.noise_db": -40.0, "a_tape_dropouts.azimuth": 0.62}),
    ],
))


register_preset(Preset(
    id="audio-vhs-linear-1985",
    name="VHS Linear Audio",
    family="audio",
    era="1985",
    desc="The ordinary VHS audio track: slow longitudinal tape, mono midrange, loud hiss, automatic level squeeze and frame-rate head-switch grit underneath.",
    tagline="Slow VHS mono, loud hiss, switch grit",
    tags=("audio-only", "80s", "vhs", "video"),
    audio=[
        ("a_video_tape_audio", {"format": "vhs_linear", "tracking": 0.42,
                                "dropout_rate": 9.0, "noise_db": -44.0,
                                "head_switch_db": -54.0, "compander_error": 0.08}),
        ("a_agc", {"target_db": -18.0, "max_gain_db": 8.0, "attack_ms": 18.0,
                   "release_ms": 520.0, "amount": 0.68}),
        ("a_mono", {"amount": 1.0}),
        ("a_hum", {"hz": "60", "level_db": -62.0, "buzz": 0.28}),
    ],
    variants=[
        Variant("sp-master", "SP Master", "A clean SP recording with low tracking roughness and restrained AGC.",
                audio={"a_video_tape_audio.tracking": 0.12, "a_video_tape_audio.dropout_rate": 1.0,
                       "a_video_tape_audio.noise_db": -50.0, "a_agc.amount": 0.35}),
        Variant("six-hour", "Six-Hour Tape", "Half-speed linear audio with the track floor close behind every syllable.",
                audio={"a_video_tape_audio.tracking": 0.86, "a_video_tape_audio.dropout_rate": 34.0,
                       "a_video_tape_audio.noise_db": -37.0, "a_video_tape_audio.head_switch_db": -46.0}),
    ],
))


register_preset(Preset(
    id="audio-betamax-hifi-1985",
    name="Beta Hi-Fi Carrier",
    family="audio",
    era="1985",
    desc="Frequency-modulated Beta Hi-Fi: broad stereo response, soft carrier compression, low demodulation hiss and brief bright tracking roughness on weak tape.",
    tagline="Broad Beta carrier, soft companding, shimmer",
    tags=("audio-only", "80s", "betamax", "hifi"),
    audio=[
        ("a_video_tape_audio", {"format": "betahifi", "tracking": 0.2,
                                "dropout_rate": 3.0, "noise_db": -59.0,
                                "head_switch_db": -66.0, "compander_error": -0.12}),
        ("a_channel_aging", {"width": 0.94, "imbalance_db": -0.35,
                             "crosstalk_db": -48.0, "skew_us": 35.0,
                             "phase_wander": 0.12, "mono_bass_hz": 80.0}),
        ("a_compressor", {"threshold_db": -17.0, "ratio": 2.2, "attack_ms": 8.0,
                          "release_ms": 220.0}),
    ],
    variants=[
        Variant("reference-deck", "Reference Deck", "The carrier locks immediately and the stereo channels remain aligned.",
                audio={"a_video_tape_audio.tracking": 0.03, "a_video_tape_audio.dropout_rate": 0.0,
                       "a_video_tape_audio.compander_error": 0.0,
                       "a_channel_aging.phase_wander": 0.02}),
        Variant("tracking-edge", "Tracking Edge", "The carrier rides the edge of lock and the quiet top end breathes too brightly.",
                audio={"a_video_tape_audio.tracking": 0.72, "a_video_tape_audio.dropout_rate": 18.0,
                       "a_video_tape_audio.compander_error": -0.62,
                       "a_channel_aging.phase_wander": 0.58}),
    ],
))


register_preset(Preset(
    id="audio-vhs-hifi-1988",
    name="VHS Hi-Fi Mistrack",
    family="audio",
    era="1988",
    desc="VHS Hi-Fi after a deck swap: wide FM audio with level-dependent top-end breathing, head-switch ticks, phase wander and occasional carrier dropouts.",
    tagline="Wide VHS FM, top breath, carrier drops",
    tags=("audio-only", "80s", "vhs", "hifi"),
    audio=[
        ("a_video_tape_audio", {"format": "vhs_hifi", "tracking": 0.38,
                                "dropout_rate": 7.0, "noise_db": -56.0,
                                "head_switch_db": -58.0, "compander_error": -0.35}),
        ("a_channel_aging", {"width": 0.88, "imbalance_db": 0.7,
                             "crosstalk_db": -39.0, "skew_us": 75.0,
                             "phase_wander": 0.32, "mono_bass_hz": 110.0}),
        ("a_noise_reduction", {"system": "dbx", "decode_error": -0.18,
                               "threshold_db": -38.0, "pumping": 0.38, "hiss_db": -64.0}),
    ],
    variants=[
        Variant("same-deck", "Same Deck", "Recorded and replayed on one aligned machine with the carrier centered.",
                audio={"a_video_tape_audio.tracking": 0.06, "a_video_tape_audio.compander_error": 0.0,
                       "a_channel_aging.skew_us": 12.0, "a_channel_aging.phase_wander": 0.04,
                       "a_noise_reduction.decode_error": 0.0}),
        Variant("rental-vcr", "Rental VCR", "A stranger's alignment turns the carrier edge into shimmer, pumping and short losses.",
                audio={"a_video_tape_audio.tracking": 0.9, "a_video_tape_audio.dropout_rate": 28.0,
                       "a_video_tape_audio.compander_error": -0.78,
                       "a_noise_reduction.pumping": 0.82}),
    ],
))


register_preset(Preset(
    id="audio-video8-afm-1991",
    name="Video8 AFM Track",
    family="audio",
    era="1991",
    desc="An 8 mm camcorder AFM track: compact carrier bandwidth, mostly mono pickup, soft companding, bright demodulation noise and short tracking nicks.",
    tagline="Compact AFM, soft companding, bright nicks",
    tags=("audio-only", "90s", "video8", "camcorder"),
    audio=[
        ("a_video_tape_audio", {"format": "video8_afm", "tracking": 0.32,
                                "dropout_rate": 6.0, "noise_db": -53.0,
                                "head_switch_db": -61.0, "compander_error": -0.2}),
        ("a_channel_aging", {"width": 0.35, "imbalance_db": -0.4,
                             "crosstalk_db": -34.0, "skew_us": 50.0,
                             "phase_wander": 0.2, "mono_bass_hz": 140.0}),
        ("a_agc", {"target_db": -19.0, "max_gain_db": 9.0, "attack_ms": 12.0,
                   "release_ms": 460.0, "amount": 0.62}),
    ],
    variants=[
        Variant("new-cassette", "New Cassette", "A short recording on clean tape with a firmly locked carrier.",
                audio={"a_video_tape_audio.tracking": 0.06, "a_video_tape_audio.dropout_rate": 0.0,
                       "a_video_tape_audio.noise_db": -59.0}),
        Variant("long-playback", "Long Playback", "A reused cassette brings carrier shimmer, noise and repeated short nicks.",
                audio={"a_video_tape_audio.tracking": 0.82, "a_video_tape_audio.dropout_rate": 26.0,
                       "a_video_tape_audio.noise_db": -45.0, "a_agc.amount": 0.88}),
    ],
))


register_preset(Preset(
    id="audio-camcorder-onboard-1994",
    name="On-Camera Microphone",
    family="audio",
    era="1994",
    desc="A plastic-body camcorder microphone into AFM tape: forward electret presence, body-handling thumps, fast AGC and camera-width stereo narrowing.",
    tagline="Electret presence, body thumps, fast AGC",
    tags=("audio-only", "90s", "camcorder", "microphone"),
    audio=[
        ("a_historical_mic", {"profile": "camcorder_1994", "amount": 0.94,
                              "proximity": 0.0, "overload": 0.34, "handling": 0.46,
                              "self_noise_db": -52.0}),
        ("a_video_tape_audio", {"format": "video8_afm", "tracking": 0.22,
                                "dropout_rate": 3.0, "noise_db": -55.0,
                                "head_switch_db": -63.0, "compander_error": -0.12}),
        ("a_agc", {"target_db": -18.0, "max_gain_db": 13.0, "attack_ms": 6.0,
                   "release_ms": 720.0, "amount": 0.9}),
        ("a_channel_aging", {"width": 0.55, "imbalance_db": -0.6,
                             "crosstalk_db": -30.0, "skew_us": 60.0,
                             "phase_wander": 0.18, "mono_bass_hz": 180.0}),
    ],
    variants=[
        Variant("tripod", "On A Tripod", "Hands off the body, a steady carrier and the AGC with less empty-room gain.",
                audio={"a_historical_mic.handling": 0.0, "a_video_tape_audio.tracking": 0.06,
                       "a_agc.amount": 0.55}),
        Variant("family-handheld", "Family Handheld", "Every grip reaches the capsule while the level circuit lifts the room between words.",
                audio={"a_historical_mic.handling": 0.9, "a_historical_mic.overload": 0.58,
                       "a_video_tape_audio.tracking": 0.58, "a_agc.amount": 1.0}),
    ],
))


register_preset(Preset(
    id="audio-hi8-stereo-1996",
    name="Hi8 Stereo AFM",
    family="audio",
    era="1996",
    desc="A good Hi8 AFM recording after years in the case: broad stereo, mild compander drift, small channel skew and occasional carrier scuffs without cassette hiss.",
    tagline="Broad Hi8 stereo, skew, carrier scuffs",
    tags=("audio-only", "90s", "hi8", "camcorder"),
    audio=[
        ("a_video_tape_audio", {"format": "hi8_afm", "tracking": 0.18,
                                "dropout_rate": 3.0, "noise_db": -60.0,
                                "head_switch_db": -68.0, "compander_error": 0.12}),
        ("a_channel_aging", {"width": 0.92, "imbalance_db": 0.35,
                             "crosstalk_db": -46.0, "skew_us": -45.0,
                             "phase_wander": 0.16, "mono_bass_hz": 85.0}),
        ("a_compressor", {"threshold_db": -18.0, "ratio": 2.0, "attack_ms": 9.0,
                          "release_ms": 250.0}),
    ],
    variants=[
        Variant("camera-master", "Camera Master", "A first-generation tape with clean carrier lock and centered channels.",
                audio={"a_video_tape_audio.tracking": 0.02, "a_video_tape_audio.dropout_rate": 0.0,
                       "a_video_tape_audio.compander_error": 0.0,
                       "a_channel_aging.skew_us": 0.0, "a_channel_aging.phase_wander": 0.0}),
        Variant("archive-playback", "Archive Playback", "The tape path is slightly wrong and the carrier shows it in the top end first.",
                audio={"a_video_tape_audio.tracking": 0.62, "a_video_tape_audio.dropout_rate": 16.0,
                       "a_video_tape_audio.compander_error": 0.48,
                       "a_channel_aging.phase_wander": 0.52}),
    ],
))
