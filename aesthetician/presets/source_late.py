"""Source-preserving audiovisual looks from the 1980s and 1990s.

The chains in this module model acquisition, photochemical stock, analog
carrier, and mastering artifacts. They preserve program geometry, timing,
picture content, and the complete supplied soundtrack.
"""

from __future__ import annotations

from ..engine.presets import ChainSpec, Preset, Variant, register_preset


def _film(
    *,
    profile: str = "kodak_80s",
    stock_strength: float = 0.82,
    exposure: float = 0.0,
    contrast: float = 1.12,
    lift: float = 0.025,
    knee: float = 0.8,
    warmth: float = 0.0,
    tint: float = 0.0,
    shadow_tint: str = "none",
    shadow_amt: float = 0.0,
    high_tint: str = "none",
    high_amt: float = 0.0,
    saturation: float = 1.0,
    vibrance: float = 0.0,
    soft_focus: float = 0.08,
    diffusion: float = 0.08,
    corner_softness: float = 0.08,
    aberration: float = 0.3,
    veiling_flare: float = 0.1,
    distortion: float = 0.0,
    grain: float = 0.34,
    grain_size: float = 1.8,
    grain_stock: str = "fine_35",
    chroma_grain: float = 0.14,
    halation: float = 0.28,
    halation_tint: str = "red_orange",
    optical_softness: float = 0.0,
    registration: float = 0.0,
    layer_haze: float = 0.0,
    fade: float = 0.0,
    fade_profile: str = "neutral",
    gate_weave: float = 0.55,
    flicker: float = 0.06,
    dust: float = 0.18,
    scratches: int = 0,
) -> ChainSpec:
    chain: ChainSpec = [
        ("stock", {"profile": profile, "strength": stock_strength}),
        ("tone", {"exposure": exposure, "contrast": contrast, "lift": lift, "knee": knee}),
        (
            "balance",
            {
                "warmth": warmth,
                "tint": tint,
                "shadow_tint": shadow_tint,
                "shadow_amt": shadow_amt,
                "high_tint": high_tint,
                "high_amt": high_amt,
            },
        ),
        ("saturation", {"amount": saturation, "vibrance": vibrance}),
        (
            "optics",
            {
                "soft_focus": soft_focus,
                "diffusion": diffusion,
                "corner_softness": corner_softness,
                "chromatic_aberration": aberration,
                "veiling_flare": veiling_flare,
                "distortion": distortion,
            },
        ),
    ]
    if optical_softness or registration or layer_haze:
        chain.append(
            (
                "optical_composite",
                {
                    "softness": optical_softness,
                    "registration": registration,
                    "layer_haze": layer_haze,
                    "density_breath": 0.12,
                },
            )
        )
    chain.extend(
        [
            (
                "grain",
                {
                    "amount": grain,
                    "size": grain_size,
                    "chroma_grain": chroma_grain,
                    "stock": grain_stock,
                    "layers": "print_from_neg",
                    "mottle": 0.08,
                },
            ),
            ("halation", {"strength": halation, "tint": halation_tint, "threshold": 0.72}),
            ("print_char", {"contrast_buildup": 1, "dmax_breath": 0.12, "acutance": 0.22}),
        ]
    )
    if fade:
        chain.append(("fade", {"amount": fade, "profile": fade_profile, "bloom_whites": 0.1}))
    chain.extend(
        [
            ("gate_weave", {"amount": gate_weave, "splice_bump": 0.25}),
            ("flicker", {"amount": flicker, "color_flicker": 0.04, "spatial": 0.08}),
            ("dust", {"density": dust, "hairs": 0.08}),
        ]
    )
    if scratches:
        chain.append(("scratches", {"count": scratches, "transient_rate": 0.35, "strength": 0.28}))
    return chain


def _analog_video(
    *,
    system: str = "ntsc",
    exposure: float = 0.0,
    contrast: float = 1.06,
    lift: float = 0.035,
    knee: float = 0.76,
    warmth: float = 0.0,
    tint: float = 0.0,
    shadow_tint: str = "none",
    shadow_amt: float = 0.0,
    high_tint: str = "none",
    high_amt: float = 0.0,
    saturation: float = 1.05,
    vibrance: float = 0.0,
    soft_focus: float = 0.06,
    diffusion: float = 0.08,
    distortion: float = 0.0,
    flare: float = 0.08,
    focus_drift: float = 0.0,
    hunt_rate: float = 0.0,
    auto_gain: float = 0.0,
    wb_amount: float = 0.0,
    trail: float = 0.18,
    luma_bw: float = 3.8,
    chroma_bw: float = 0.82,
    phase_noise: float = 1.6,
    dot_crawl: float = 0.24,
    rainbow: float = 0.2,
    fringing: float = 1.0,
    tape: bool = True,
    tape_mode: str = "sp",
    generation: int = 1,
    tape_luma: float = 0.18,
    tape_chroma: float = 0.2,
    time_base: float = 0.14,
    tracking: float = 0.02,
    dropouts: float = 0.3,
    sharpen: float = 0.45,
    interlace: float = 0.52,
    grain: float = 0.0,
) -> ChainSpec:
    chain: ChainSpec = [
        ("stock", {"profile": "tube_80s", "strength": 0.72}),
        ("tone", {"exposure": exposure, "contrast": contrast, "lift": lift, "knee": knee}),
        (
            "balance",
            {
                "warmth": warmth,
                "tint": tint,
                "shadow_tint": shadow_tint,
                "shadow_amt": shadow_amt,
                "high_tint": high_tint,
                "high_amt": high_amt,
            },
        ),
        ("saturation", {"amount": saturation, "vibrance": vibrance}),
        (
            "optics",
            {
                "soft_focus": soft_focus,
                "diffusion": diffusion,
                "distortion": distortion,
                "veiling_flare": flare,
                "focus_drift": focus_drift,
                "hunt_rate": hunt_rate,
            },
        ),
    ]
    if auto_gain or wb_amount:
        chain.append(
            (
                "exposure_auto",
                {
                    "lag": 0.75,
                    "overshoot": 0.28,
                    "max_boost": 4.0,
                    "agc_gain_noise": auto_gain,
                    "wb_amount": wb_amount,
                },
            )
        )
    if grain:
        chain.append(
            (
                "grain",
                {
                    "amount": grain,
                    "size": 1.7,
                    "chroma_grain": 0.12,
                    "stock": "doc_16",
                    "layers": "print_from_neg",
                },
            )
        )
    if trail:
        chain.append(("phosphor_decay", {"decay": trail, "mode": "p22"}))
    chain.append(
        (
            "ntsc",
            {
                "system": system,
                "strength": 0.68,
                "luma_bw": luma_bw,
                "chroma_bw": chroma_bw,
                "phase_noise": phase_noise,
                "dot_crawl": dot_crawl,
                "rainbow": rainbow,
                "fringing": fringing,
                "setup_level": 0.05 if system == "ntsc" else 0.0,
                "comb_mode": "comb_1line",
            },
        )
    )
    if tape:
        chain.append(
            (
                "vhs",
                {
                    "mode": tape_mode,
                    "generation": generation,
                    "luma_bw": 3.8 if tape_mode == "sp" else 2.7,
                    "chroma_bw": 0.68 if tape_mode == "sp" else 0.42,
                    "luma_noise": tape_luma,
                    "chroma_noise": tape_chroma,
                    "head_switch": 0.28,
                    "time_base_error": time_base,
                    "flagging": 0.08,
                    "tracking_error": tracking,
                    "dropouts": dropouts,
                    "sharpen": sharpen,
                    "chroma_delay": 0.8,
                },
            )
        )
    chain.append(("interlace", {"combing": interlace, "twitter": 0.28}))
    return chain


def _film_to_video(*, film: ChainSpec, system: str = "ntsc", tape: bool = True) -> ChainSpec:
    chain = list(film)
    chain.append(
        (
            "ntsc",
            {
                "system": system,
                "strength": 0.5,
                "luma_bw": 4.1,
                "chroma_bw": 0.86,
                "phase_noise": 1.2,
                "dot_crawl": 0.18,
                "rainbow": 0.12,
                "comb_mode": "comb_1line",
                "setup_level": 0.045 if system == "ntsc" else 0.0,
            },
        )
    )
    if tape:
        chain.append(
            (
                "vhs",
                {
                    "mode": "sp",
                    "generation": 1,
                    "luma_bw": 4.4,
                    "chroma_bw": 0.76,
                    "luma_noise": 0.12,
                    "chroma_noise": 0.14,
                    "head_switch": 0.2,
                    "time_base_error": 0.09,
                    "flagging": 0.04,
                    "dropouts": 0.15,
                    "sharpen": 0.38,
                },
            )
        )
    chain.append(("interlace", {"combing": 0.48, "twitter": 0.24}))
    return chain


def _film_audio(
    *,
    mono: bool = False,
    generations: int = 1,
    alignment: float = 0.08,
    compression: float = 0.25,
    hiss_db: float = -64.0,
    width: float = 0.96,
    crosstalk_db: float = -46.0,
) -> ChainSpec:
    chain: ChainSpec = []
    if mono:
        chain.append(("a_mono", {"amount": 1.0}))
    chain.extend(
        [
            (
                "a_analog_dub",
                {
                    "format": "reel_15ips",
                    "generations": generations,
                    "alignment": alignment,
                    "compression": compression,
                    "hiss_db": hiss_db,
                },
            ),
            (
                "a_channel_aging",
                {
                    "width": 0.0 if mono else width,
                    "imbalance_db": -0.25,
                    "crosstalk_db": crosstalk_db,
                    "skew_us": 28.0,
                    "phase_wander": 0.08,
                    "mono_bass_hz": 100.0,
                },
            ),
            ("a_compressor", {"threshold_db": -19.0, "ratio": 2.8, "attack_ms": 8.0, "release_ms": 220.0}),
        ]
    )
    return chain


def _video_audio(
    *,
    tape_format: str = "vhs_hifi",
    mono: bool = False,
    mic: str = "electret_1985",
    mic_amount: float = 0.24,
    overload: float = 0.12,
    handling: float = 0.0,
    tracking: float = 0.14,
    dropout_rate: float = 1.0,
    noise_db: float = -58.0,
    compander_error: float = 0.0,
    width: float = 0.92,
    compression: float = 3.2,
    agc: float = 0.45,
    room_mix: float = 0.0,
) -> ChainSpec:
    chain: ChainSpec = [
        (
            "a_historical_mic",
            {
                "profile": mic,
                "amount": mic_amount,
                "overload": overload,
                "self_noise_db": -58.0,
                "handling": handling,
            },
        )
    ]
    if mono:
        chain.append(("a_mono", {"amount": 1.0}))
    chain.extend(
        [
            (
                "a_video_tape_audio",
                {
                    "format": tape_format,
                    "tracking": tracking,
                    "dropout_rate": dropout_rate,
                    "noise_db": noise_db,
                    "head_switch_db": -64.0,
                    "compander_error": compander_error,
                },
            ),
            (
                "a_channel_aging",
                {
                    "width": 0.0 if mono else width,
                    "imbalance_db": -0.2,
                    "crosstalk_db": -42.0,
                    "skew_us": 35.0,
                    "phase_wander": 0.1,
                    "mono_bass_hz": 120.0,
                },
            ),
            (
                "a_compressor",
                {"threshold_db": -20.0, "ratio": compression, "attack_ms": 6.0, "release_ms": 210.0},
            ),
            (
                "a_agc",
                {"target_db": -16.0, "max_gain_db": 10.0, "attack_ms": 22.0, "release_ms": 720.0, "amount": agc},
            ),
        ]
    )
    if room_mix:
        chain.append(
            (
                "a_room",
                {"mode": "room", "size": 1.0, "decay_s": 0.5, "damp": 0.68, "mix": room_mix},
            )
        )
    return chain


register_preset(Preset(
    id="auth-new-york-street-crime-thriller",
    name="New York Street-Crime Thriller",
    family="film",
    era="1982",
    desc="A fast 35 mm city negative holds sodium-yellow pavement, cyan-black night grain, wet-lens flare and a dense stereo magnetic master without touching the scene timing.",
    tagline="Sodium night grain and wet-lens flare",
    tags=("80s", "35mm", "crime", "night", "source-preserving"),
    video=_film(
        exposure=-0.22, contrast=1.24, lift=0.018, knee=0.72, warmth=-0.04,
        shadow_tint="teal", shadow_amt=0.18, high_tint="yellow", high_amt=0.2,
        saturation=0.86, soft_focus=0.06, diffusion=0.08, veiling_flare=0.3,
        grain=0.25, grain_size=1.12, grain_stock="push_process", chroma_grain=0.07,
        halation=0.38, gate_weave=0.62, dust=0.2,
    ),
    audio=_film_audio(generations=2, alignment=0.16, compression=0.4, width=0.9),
))


register_preset(Preset(
    id="auth-new-wave-studio-music-video",
    name="New-Wave Studio Music Video",
    family="broadcast",
    era="1983",
    desc="A one-inch studio master pushes cobalt shadows and pink tube highlights through switcher-soft composite color, phosphor trails and a tightly aligned stereo tape path.",
    tagline="Cobalt tube color and switcher-soft trails",
    tags=("80s", "studio-video", "new-wave", "composite", "source-preserving"),
    proc_height=580,
    upscale="soft",
    video=_analog_video(
        exposure=-0.04, contrast=1.18, lift=0.025, knee=0.66, tint=0.1,
        shadow_tint="blue", shadow_amt=0.32, high_tint="pink", high_amt=0.3,
        saturation=1.32, vibrance=0.16, diffusion=0.16, flare=0.22, trail=0.42,
        phase_noise=2.5, dot_crawl=0.36, rainbow=0.32, fringing=2.2,
        tape_luma=0.14, tape_chroma=0.18, time_base=0.12,
    ),
    audio=_video_audio(tape_format="betahifi", mic_amount=0.08, tracking=0.08, noise_db=-64.0, width=1.06),
))


register_preset(Preset(
    id="auth-hair-metal-arena-promo",
    name="Hair-Metal Arena Promo",
    family="film",
    era="1988",
    desc="A pushed 16 mm concert negative records smoke-soft backlight, clipped red gels, coarse shadow grain and a hot stereo analog dub with mild channel crowding.",
    tagline="Pushed concert grain and clipped red gels",
    tags=("80s", "16mm", "concert", "arena", "source-preserving"),
    proc_height=620,
    upscale="soft",
    video=_film(
        exposure=-0.16, contrast=1.28, knee=0.66, tint=0.08, shadow_tint="blue",
        shadow_amt=0.28, high_tint="pink", high_amt=0.26, saturation=1.2,
        diffusion=0.2, veiling_flare=0.44, grain=0.58, grain_size=1.95,
        grain_stock="push_process", chroma_grain=0.2, halation=0.48,
        optical_softness=0.12, layer_haze=0.16, gate_weave=1.05, dust=0.26,
    ),
    audio=_film_audio(generations=2, alignment=0.22, compression=0.56, hiss_db=-58.0, width=1.02),
))


register_preset(Preset(
    id="auth-televangelist-broadcast",
    name="Televangelist Broadcast",
    family="broadcast",
    era="1986",
    desc="Three hot studio cameras bloom white suits into saturated tube color while a composite master and heavily leveled linear track preserve the original program intact.",
    tagline="Hot tube whites and leveled linear mono",
    tags=("80s", "broadcast", "studio-video", "religious-tv", "source-preserving"),
    proc_height=560,
    upscale="soft",
    video=_analog_video(
        exposure=0.2, contrast=1.1, lift=0.045, knee=0.62, warmth=0.14,
        high_tint="cream", high_amt=0.28, saturation=1.28, diffusion=0.18,
        flare=0.28, trail=0.28, phase_noise=2.2, dot_crawl=0.4,
        tape_luma=0.18, tape_chroma=0.22, time_base=0.14,
    ),
    audio=_video_audio(
        tape_format="vhs_linear", mono=True, mic="broadcast_dynamic_1955", mic_amount=0.34,
        overload=0.22, tracking=0.2, noise_db=-49.0, compression=5.5, agc=0.72, room_mix=0.12,
    ),
))


register_preset(Preset(
    id="auth-video-dating-profile-tape",
    name="Video-Dating Profile Tape",
    family="vhs",
    era="1987",
    desc="A single tube camera and direct VHS dub leave flat beige whites, gentle focus drift, color-under softness and a close electret mono track with audible carrier noise.",
    tagline="Flat tube color and close VHS mono",
    tags=("80s", "vhs", "camcorder", "profile", "source-preserving"),
    proc_height=540,
    upscale="soft",
    video=_analog_video(
        contrast=1.01, lift=0.06, knee=0.78, warmth=0.08, tint=-0.03,
        high_tint="cream", high_amt=0.12, saturation=0.92, soft_focus=0.14,
        focus_drift=0.16, hunt_rate=0.18, auto_gain=0.28, wb_amount=0.28,
        trail=0.16, phase_noise=2.0, tape_luma=0.24, tape_chroma=0.26,
        time_base=0.22, tracking=0.06, dropouts=0.45,
    ),
    audio=_video_audio(
        tape_format="vhs_linear", mono=True, mic_amount=0.62, overload=0.12,
        tracking=0.28, dropout_rate=2.0, noise_db=-46.0, compression=3.8, agc=0.65, room_mix=0.09,
    ),
))


register_preset(Preset(
    id="auth-public-television-science-magazine",
    name="Public-Television Science Magazine",
    family="broadcast",
    era="1985",
    desc="A restrained U-matic edit blends mild 16 mm texture with neutral tube-camera color, clean composite edges and a dry lavalier track on three-quarter-inch tape.",
    tagline="Neutral tube color on a dry U-matic edit",
    tags=("80s", "public-tv", "science", "umatic", "source-preserving"),
    proc_height=600,
    upscale="soft",
    video=_analog_video(
        contrast=1.02, lift=0.04, knee=0.8, warmth=0.02, tint=-0.03,
        shadow_tint="green", shadow_amt=0.08, saturation=0.94, vibrance=-0.08,
        soft_focus=0.08, diffusion=0.06, trail=0.12, phase_noise=1.2,
        dot_crawl=0.2, rainbow=0.12, tape_luma=0.14, tape_chroma=0.15,
        time_base=0.1, dropouts=0.2, grain=0.12,
    ),
    audio=_video_audio(
        tape_format="umatic_linear", mono=True, mic="lavalier_1972", mic_amount=0.4,
        tracking=0.14, noise_db=-52.0, compression=3.2, agc=0.42, room_mix=0.06,
    ),
))


register_preset(Preset(
    id="auth-italian-prime-time-variety-show",
    name="Italian Prime-Time Variety Show",
    family="broadcast",
    era="1987",
    desc="A PAL studio master carries crimson and electric-blue stage light through soft tube highlights, clean 50-field interlace and a wide, lightly compressed analog program track.",
    tagline="PAL tube glamour and wide analog stereo",
    tags=("80s", "italy", "pal", "variety", "source-preserving"),
    proc_height=576,
    upscale="soft",
    video=_analog_video(
        system="pal", exposure=0.14, contrast=1.13, lift=0.025, knee=0.64,
        warmth=0.1, tint=0.08, shadow_tint="blue", shadow_amt=0.18,
        high_tint="pink", high_amt=0.28, saturation=1.34, diffusion=0.16,
        flare=0.3, trail=0.36, phase_noise=1.2, dot_crawl=0.18, rainbow=0.08,
        tape=False, interlace=0.5,
    ),
    audio=_video_audio(tape_format="betahifi", mic_amount=0.1, tracking=0.06, noise_db=-65.0, width=1.12, compression=3.0, agc=0.28),
))


register_preset(Preset(
    id="auth-hong-kong-heroic-bloodshed-thriller",
    name="Hong Kong Heroic-Bloodshed Thriller",
    family="world",
    era="1988",
    desc="A fast Hong Kong 35 mm answer print holds cyan neon smoke, warm faces, hard printer contrast and clean optical wear while a compressed mono track keeps every source cue in place.",
    tagline="Cyan neon smoke on a hard answer print",
    tags=("80s", "hong-kong", "35mm", "action", "source-preserving"),
    video=_film(
        exposure=-0.08, contrast=1.28, lift=0.035, knee=0.7, warmth=0.02,
        shadow_tint="teal", shadow_amt=0.18, high_tint="pink", high_amt=0.16,
        saturation=1.16, diffusion=0.12, veiling_flare=0.34, grain=0.22,
        grain_size=1.08, grain_stock="push_process", chroma_grain=0.08,
        halation=0.4, optical_softness=0.12, registration=0.18, layer_haze=0.1,
        fade=0.12, fade_profile="cyan_loss", gate_weave=0.7, dust=0.32, scratches=1,
    ),
    audio=_film_audio(mono=True, generations=2, alignment=0.2, compression=0.48, hiss_db=-56.0, width=0.0),
))


register_preset(Preset(
    id="auth-theatrical-cel-anime-fantasy",
    name="Theatrical Cel-Anime Fantasy",
    family="cartoon",
    era="1987",
    desc="A protected 35 mm cel-animation print preserves saturated paint, deep cobalt shadows, warm highlight bloom, fine optical joins and a wide magnetic soundtrack without redrawing the input.",
    tagline="Rich cel dyes on a fine theatrical print",
    tags=("80s", "anime", "35mm", "theatrical", "source-preserving"),
    video=_film(
        contrast=1.17, lift=0.018, knee=0.78, warmth=0.06, tint=0.04,
        shadow_tint="blue", shadow_amt=0.24, high_tint="cream", high_amt=0.14,
        saturation=1.24, vibrance=0.16, soft_focus=0.04, diffusion=0.08,
        grain=0.28, grain_size=1.55, chroma_grain=0.1, halation=0.3,
        optical_softness=0.08, registration=0.12, layer_haze=0.06,
        gate_weave=0.4, flicker=0.04, dust=0.12,
    ),
    audio=_film_audio(generations=1, alignment=0.05, compression=0.2, hiss_db=-68.0, width=1.14),
))


register_preset(Preset(
    id="auth-claymation-music-video",
    name="Claymation Music Video",
    family="film",
    era="1987",
    desc="A tabletop 16 mm negative renders clay surfaces with dense tactile grain, warm tungsten rolloff, miniature-scale focus falloff and a precisely aligned stereo tape master.",
    tagline="Tactile clay under warm 16 mm grain",
    tags=("80s", "claymation", "16mm", "music-video", "source-preserving"),
    proc_height=620,
    upscale="soft",
    video=_film(
        contrast=1.16, lift=0.022, knee=0.76, warmth=0.16, high_tint="cream",
        high_amt=0.16, saturation=1.12, diffusion=0.12, corner_softness=0.18,
        grain=0.46, grain_size=1.9, grain_stock="doc_16", chroma_grain=0.18,
        halation=0.34, gate_weave=0.76, flicker=0.07, dust=0.18,
    ),
    audio=_film_audio(generations=1, alignment=0.06, compression=0.3, hiss_db=-64.0, width=1.05),
))


register_preset(Preset(
    id="auth-stop-motion-product-commercial",
    name="Stop-Motion Product Commercial",
    family="film",
    era="1985",
    desc="A polished 35 mm tabletop element gives lacquered miniatures crisp dye color, controlled specular halation, clean optical registration and a compact stereo commercial master.",
    tagline="Glossy miniatures on a clean 35 mm element",
    tags=("80s", "stop-motion", "commercial", "35mm", "source-preserving"),
    video=_film(
        exposure=0.08, contrast=1.2, lift=0.012, knee=0.7, warmth=0.08,
        high_tint="cream", high_amt=0.18, saturation=1.22, vibrance=0.12,
        soft_focus=0.03, diffusion=0.06, grain=0.25, grain_size=1.45,
        chroma_grain=0.08, halation=0.38, optical_softness=0.05,
        registration=0.08, gate_weave=0.32, flicker=0.03, dust=0.08,
    ),
    audio=_film_audio(generations=1, alignment=0.04, compression=0.36, hiss_db=-68.0, width=1.02),
))


register_preset(Preset(
    id="auth-wrestling-broadcast-tape",
    name="Wrestling Broadcast Tape",
    family="broadcast",
    era="1987",
    desc="Arena tube cameras drive saturated reds into composite smear, bright ropes leave short phosphor tails, and a field-tape stereo carrier compresses the original crowd without replacing it.",
    tagline="Arena reds, phosphor tails, crushed tape",
    tags=("80s", "wrestling", "broadcast", "arena", "source-preserving"),
    proc_height=560,
    upscale="soft",
    video=_analog_video(
        exposure=0.12, contrast=1.2, lift=0.025, knee=0.62, warmth=0.1,
        saturation=1.34, vibrance=0.16, diffusion=0.08, flare=0.22,
        auto_gain=0.44, wb_amount=0.26, trail=0.44, phase_noise=2.8,
        dot_crawl=0.44, rainbow=0.34, fringing=2.1, tape_luma=0.26,
        tape_chroma=0.3, time_base=0.22, tracking=0.08, dropouts=0.7,
    ),
    audio=_video_audio(
        tape_format="betahifi", mic="shotgun_1975", mic_amount=0.36, overload=0.5,
        tracking=0.28, dropout_rate=3.0, noise_db=-55.0, width=0.9,
        compression=7.0, agc=0.76, room_mix=0.12,
    ),
))


register_preset(Preset(
    id="auth-skateboard-vhs",
    name="Skateboard VHS",
    family="vhs",
    era="1988",
    desc="A shoulder-mounted VHS camera bends close curbs through a modest fisheye, pumps gain between pavement and sky, and records color-under noise with a hard-limited onboard mono track.",
    tagline="Fisheye VHS with gain-pumped pavement",
    tags=("80s", "skateboard", "vhs", "camcorder", "source-preserving"),
    proc_height=540,
    upscale="soft",
    video=_analog_video(
        contrast=1.1, knee=0.74, saturation=1.02, distortion=0.18,
        soft_focus=0.08, focus_drift=0.14, hunt_rate=0.36, auto_gain=0.56,
        wb_amount=0.32, trail=0.18, phase_noise=2.2, tape_luma=0.32,
        tape_chroma=0.34, time_base=0.3, tracking=0.16, dropouts=1.0, sharpen=0.6,
    ),
    audio=_video_audio(
        tape_format="vhs_linear", mono=True, mic_amount=0.68, overload=0.42,
        handling=0.36, tracking=0.36, dropout_rate=4.0, noise_db=-44.0,
        compression=6.5, agc=0.82,
    ),
))


register_preset(Preset(
    id="auth-surf-video-magazine",
    name="Surf Video Magazine",
    family="vhs",
    era="1987",
    desc="A sun-worked prosumer tape carries pale cyan water, clipped white spray, long-lens haze and gentle chroma delay through a bright Hi-Fi stereo carrier.",
    tagline="Sun-worked tape and cyan water haze",
    tags=("80s", "surf", "video-magazine", "vhs", "source-preserving"),
    proc_height=560,
    upscale="soft",
    video=_analog_video(
        exposure=0.16, contrast=1.06, lift=0.04, knee=0.64, warmth=0.02,
        tint=-0.05, shadow_tint="teal", shadow_amt=0.16, saturation=0.92,
        soft_focus=0.12, diffusion=0.1, flare=0.22, auto_gain=0.22,
        wb_amount=0.2, trail=0.18, phase_noise=1.8, tape_luma=0.22,
        tape_chroma=0.26, time_base=0.16, dropouts=0.45,
    ),
    audio=_video_audio(tape_format="vhs_hifi", mic_amount=0.18, tracking=0.16, noise_db=-60.0, width=1.02, compression=3.0, agc=0.36),
))


register_preset(Preset(
    id="auth-prestige-historical-miniseries",
    name="Prestige Historical Miniseries",
    family="broadcast",
    era="1984",
    desc="A restrained 35 mm camera negative reaches television through a clean analog master, leaving muted period dye, soft highlight diffusion, fine grain and gently narrowed stereo.",
    tagline="Muted 35 mm through a clean TV master",
    tags=("80s", "miniseries", "35mm", "telecine", "source-preserving"),
    proc_height=640,
    upscale="soft",
    video=_film_to_video(
        film=_film(
            contrast=1.08, lift=0.035, knee=0.84, warmth=0.04, shadow_tint="brown",
            shadow_amt=0.12, high_tint="cream", high_amt=0.12, saturation=0.86,
            vibrance=-0.08, soft_focus=0.1, diffusion=0.18, grain=0.3,
            grain_size=1.7, chroma_grain=0.12, halation=0.24,
            gate_weave=0.4, flicker=0.03, dust=0.1,
        )
    ),
    audio=_video_audio(tape_format="betahifi", mic_amount=0.06, tracking=0.06, noise_db=-66.0, width=0.94, compression=2.4, agc=0.2),
))


register_preset(Preset(
    id="auth-early-cgi-demo-reel-1988",
    name="Early CGI Demo Reel",
    family="digital",
    era="1988",
    desc="A late-1980s workstation framebuffer reaches an analog showreel master with deep render blacks, hard quantized color, visible raster precision, composite edge shimmer and a clean stereo tape path, leaving every supplied image and sound in place.",
    tagline="VGA raster precision on an analog showreel",
    tags=("80s", "cgi", "demo-reel", "analog-master", "source-preserving"),
    proc_height=600,
    upscale="soft",
    video=[
        ("tone", {"exposure": -0.04, "contrast": 1.22, "lift": 0.008, "knee": 0.64, "pivot": 0.4}),
        ("saturation", {"amount": 1.16, "vibrance": 0.1}),
        (
            "pixel_era",
            {
                "res_h": 480,
                "palette": "none",
                "dither": "none",
                "contrast_snap": 0.06,
                "pixel_aspect": 1.0,
            },
        ),
        (
            "optics",
            {
                "soft_focus": 0.025,
                "diffusion": 0.025,
                "chromatic_aberration": 0.22,
                "veiling_flare": 0.035,
            },
        ),
        (
            "ntsc",
            {
                "strength": 0.58,
                "luma_bw": 4.2,
                "chroma_bw": 0.9,
                "phase_noise": 1.0,
                "dot_crawl": 0.22,
                "rainbow": 0.12,
                "fringing": 0.8,
                "setup_level": 0.05,
                "comb_mode": "comb_1line",
            },
        ),
        (
            "vhs",
            {
                "mode": "sp",
                "generation": 1,
                "luma_bw": 4.7,
                "chroma_bw": 0.82,
                "chroma_delay": 0.45,
                "sharpen": 0.48,
                "luma_noise": 0.08,
                "chroma_noise": 0.1,
                "head_switch": 0.08,
                "dropouts": 0.08,
                "time_base_error": 0.055,
                "flagging": 0.02,
                "jitter_v": 0.025,
                "tracking_error": 0.0,
                "fm_sparkle": 0.06,
                "white_clip": 0.97,
                "black_crush": 0.025,
            },
        ),
        ("interlace", {"field_order": "tff", "combing": 0.46, "twitter": 0.34}),
    ],
    audio=[
        (
            "a_analog_dub",
            {
                "format": "reel_15ips",
                "generations": 1,
                "alignment": 0.045,
                "compression": 0.24,
                "hiss_db": -67.0,
            },
        ),
        ("a_tape_sat", {"drive": 1.55, "bump_db": 0.8, "hf_loss": 0.08}),
        (
            "a_channel_aging",
            {
                "width": 0.98,
                "imbalance_db": -0.12,
                "crosstalk_db": -49.0,
                "skew_us": 22.0,
                "phase_wander": 0.05,
                "mono_bass_hz": 90.0,
            },
        ),
        ("a_compressor", {"threshold_db": -18.0, "ratio": 2.5, "attack_ms": 8.0, "release_ms": 210.0}),
    ],
    variants=[
        Variant(
            id="framebuffer-feed",
            name="Direct Framebuffer Feed",
            desc="A cleaner 480-line workstation output before showreel copying.",
            video={
                "pixel_era.res_h": 480,
                "pixel_era.contrast_snap": 0.025,
                "ntsc.strength": 0.38,
                "ntsc.phase_noise": 0.45,
                "ntsc.dot_crawl": 0.08,
                "vhs.luma_noise": 0.025,
                "vhs.chroma_noise": 0.035,
                "vhs.head_switch": 0.02,
                "vhs.dropouts": 0.0,
                "vhs.time_base_error": 0.015,
                "vhs.fm_sparkle": 0.015,
                "interlace.twitter": 0.2,
            },
            audio={
                "a_analog_dub.alignment": 0.015,
                "a_analog_dub.compression": 0.14,
                "a_analog_dub.hiss_db": -72.0,
                "a_tape_sat.drive": 1.25,
                "a_channel_aging.phase_wander": 0.015,
            },
        ),
        Variant(
            id="trade-show-dub",
            name="Trade-Show Dub",
            desc="A second-generation presentation copy with softer raster edges and busier composite tape.",
            video={
                "ntsc.strength": 0.78,
                "ntsc.luma_bw": 3.45,
                "ntsc.chroma_bw": 0.62,
                "ntsc.phase_noise": 2.2,
                "ntsc.dot_crawl": 0.42,
                "ntsc.rainbow": 0.24,
                "vhs.generation": 2,
                "vhs.luma_bw": 3.05,
                "vhs.chroma_bw": 0.4,
                "vhs.luma_noise": 0.26,
                "vhs.chroma_noise": 0.28,
                "vhs.head_switch": 0.38,
                "vhs.dropouts": 0.55,
                "vhs.time_base_error": 0.22,
                "vhs.flagging": 0.1,
                "vhs.tracking_error": 0.05,
                "vhs.fm_sparkle": 0.18,
                "interlace.twitter": 0.42,
            },
            audio={
                "a_analog_dub.generations": 2,
                "a_analog_dub.alignment": 0.24,
                "a_analog_dub.compression": 0.42,
                "a_analog_dub.hiss_db": -56.0,
                "a_tape_sat.drive": 2.1,
                "a_tape_sat.hf_loss": 0.22,
                "a_channel_aging.width": 0.9,
                "a_channel_aging.phase_wander": 0.18,
            },
        ),
    ],
))


register_preset(Preset(
    id="auth-trip-hop-noir-promo",
    name="Trip-Hop Noir Promo",
    family="film",
    era="1995",
    desc="A pushed 35 mm night negative sinks the city into blue-green blacks, dense silver grain, damp veiling flare and softly blooming practicals while a clean analog stereo dub retains the source mix.",
    tagline="Blue-green night grain and damp flare",
    tags=("90s", "trip-hop", "noir", "35mm", "source-preserving"),
    video=_film(
        profile="vision_90s", exposure=-0.3, contrast=1.2, lift=0.016, knee=0.74,
        warmth=-0.12, tint=-0.06, shadow_tint="teal", shadow_amt=0.2,
        high_tint="cyan", high_amt=0.12, saturation=0.76, vibrance=-0.1,
        soft_focus=0.1, diffusion=0.2, corner_softness=0.14,
        veiling_flare=0.34, grain=0.24, grain_size=1.1,
        grain_stock="push_process", chroma_grain=0.06, halation=0.32,
        gate_weave=0.42, flicker=0.035, dust=0.12,
    ),
    audio=_film_audio(
        generations=1, alignment=0.08, compression=0.34,
        hiss_db=-67.0, width=1.04, crosstalk_db=-50.0,
    ),
))


register_preset(Preset(
    id="auth-warehouse-rave-vhs",
    name="Warehouse Rave VHS",
    family="vhs",
    era="1993",
    desc="A low-light VHS camcorder turns lasers into clipped cyan-magenta blooms, drags bright phosphor tails across noisy blacks and presses the original club mix into a strained Hi-Fi tape carrier.",
    tagline="Laser bloom in low-light Hi-Fi VHS",
    tags=("90s", "rave", "warehouse", "vhs", "source-preserving"),
    proc_height=540,
    upscale="soft",
    video=_analog_video(
        exposure=-0.18, contrast=1.22, lift=0.045, knee=0.58, warmth=-0.1,
        tint=0.08, shadow_tint="blue", shadow_amt=0.34,
        high_tint="pink", high_amt=0.3, saturation=1.26, vibrance=0.14,
        soft_focus=0.1, diffusion=0.2, flare=0.42, focus_drift=0.08,
        auto_gain=0.58, wb_amount=0.32, trail=0.58, phase_noise=2.8,
        dot_crawl=0.36, rainbow=0.34, fringing=1.8, tape_luma=0.34,
        tape_chroma=0.38, time_base=0.24, tracking=0.12, dropouts=0.75,
        sharpen=0.42,
    ),
    audio=_video_audio(
        tape_format="vhs_hifi", mic="camcorder_1994", mic_amount=0.32,
        overload=0.58, handling=0.18, tracking=0.28, dropout_rate=2.2,
        noise_db=-53.0, compander_error=0.22, width=0.92,
        compression=7.0, agc=0.64, room_mix=0.08,
    ),
))


register_preset(Preset(
    id="auth-hi8-family-camcorder",
    name="Hi8 Family Camcorder",
    family="vhs",
    era="1996",
    desc="A consumer Hi8 camera leaves soft electret-era color, hesitant autofocus, slow white-balance correction, edge enhancement and fine AFM carrier noise without placing a date stamp over the picture.",
    tagline="Soft Hi8 color and hesitant autofocus",
    tags=("90s", "hi8", "family-video", "camcorder", "source-preserving"),
    proc_height=600,
    upscale="soft",
    video=_analog_video(
        exposure=0.05, contrast=1.02, lift=0.045, knee=0.78, warmth=0.08,
        saturation=0.94, soft_focus=0.11, diffusion=0.08, distortion=0.03,
        flare=0.12, focus_drift=0.24, hunt_rate=0.46, auto_gain=0.42,
        wb_amount=0.55, trail=0.12, luma_bw=4.2, chroma_bw=0.94,
        phase_noise=1.25, dot_crawl=0.14, rainbow=0.1, fringing=0.72,
        tape_luma=0.14, tape_chroma=0.17, time_base=0.1, tracking=0.03,
        dropouts=0.18, sharpen=0.72, interlace=0.48,
    ),
    audio=_video_audio(
        tape_format="hi8_afm", mic="camcorder_1994", mic_amount=0.72,
        overload=0.2, handling=0.2, tracking=0.1, dropout_rate=0.7,
        noise_db=-62.0, compander_error=0.06, width=0.78,
        compression=3.8, agc=0.62, room_mix=0.05,
    ),
))


register_preset(Preset(
    id="auth-technology-launch-keynote",
    name="Technology Launch Keynote",
    family="broadcast",
    era="1998",
    desc="A late-1990s auditorium camera holds cool neutral tube color, luminous projection-screen bloom, mild composite edges and a clean Beta-derived master around the untouched presentation feed.",
    tagline="Projection bloom on a clean auditorium master",
    tags=("90s", "keynote", "auditorium", "broadcast-video", "source-preserving"),
    proc_height=640,
    upscale="soft",
    video=_analog_video(
        exposure=0.08, contrast=1.08, lift=0.03, knee=0.62, warmth=-0.04,
        high_tint="cyan", high_amt=0.08, saturation=0.88, soft_focus=0.045,
        diffusion=0.14, flare=0.3, auto_gain=0.18, wb_amount=0.2, trail=0.1,
        luma_bw=4.5, chroma_bw=1.0, phase_noise=0.75, dot_crawl=0.1,
        rainbow=0.06, fringing=0.48, tape_luma=0.07, tape_chroma=0.08,
        time_base=0.05, tracking=0.01, dropouts=0.06, sharpen=0.62,
        interlace=0.42,
    ),
    audio=_video_audio(
        tape_format="betahifi", mic="lavalier_1972", mic_amount=0.48,
        overload=0.08, tracking=0.04, dropout_rate=0.15, noise_db=-68.0,
        width=0.72, compression=3.4, agc=0.38, room_mix=0.045,
    ),
))


register_preset(Preset(
    id="auth-public-access-goth-program",
    name="Public-Access Goth Program",
    family="broadcast",
    era="1994",
    desc="An underlit public-access camera renders candle smoke as blue-black tube haze with purple chroma smear, modest composite instability and a narrow linear VHS carrier around the original studio sound.",
    tagline="Candle haze on blue-black public-access tape",
    tags=("90s", "public-access", "goth", "vhs", "source-preserving"),
    proc_height=540,
    upscale="soft",
    video=_analog_video(
        exposure=-0.24, contrast=1.18, lift=0.018, knee=0.68, warmth=-0.12,
        tint=0.1, shadow_tint="blue", shadow_amt=0.36,
        high_tint="pink", high_amt=0.18, saturation=0.9,
        soft_focus=0.12, diffusion=0.16, flare=0.3, focus_drift=0.05,
        auto_gain=0.5, wb_amount=0.28, trail=0.34, phase_noise=2.6,
        dot_crawl=0.4, rainbow=0.24, fringing=1.7, generation=2,
        tape_luma=0.3, tape_chroma=0.34, time_base=0.28, tracking=0.14,
        dropouts=0.8, sharpen=0.38,
    ),
    audio=_video_audio(
        tape_format="vhs_linear", mono=True, mic="electret_1985",
        mic_amount=0.5, overload=0.2, tracking=0.32, dropout_rate=2.8,
        noise_db=-47.0, compression=5.5, agc=0.7, room_mix=0.08,
    ),
))


register_preset(Preset(
    id="auth-magical-girl-cel-broadcast",
    name="Magical-Girl Cel Broadcast",
    family="cartoon",
    era="1995",
    desc="A pastel cel photography element carries minute layer registration, optical softness and restrained 35 mm grain into a gentle NTSC broadcast dub, preserving every original transformation and sparkle.",
    tagline="Pastel cel layers through a gentle NTSC dub",
    tags=("90s", "cel-animation", "anime", "broadcast", "source-preserving"),
    proc_height=620,
    upscale="soft",
    video=_film_to_video(
        film=_film(
            profile="vision_90s", stock_strength=0.74, exposure=0.05,
            contrast=1.04, lift=0.04, knee=0.78, warmth=0.08,
            high_tint="cream", high_amt=0.12, saturation=1.14,
            vibrance=0.08, soft_focus=0.05, diffusion=0.08,
            corner_softness=0.04, aberration=0.12, veiling_flare=0.08,
            grain=0.2, grain_size=1.35, chroma_grain=0.06, halation=0.14,
            optical_softness=0.1, registration=0.2, layer_haze=0.08,
            gate_weave=0.26, flicker=0.02, dust=0.04,
        )
    ),
    audio=_video_audio(
        tape_format="betahifi", mic_amount=0.04, tracking=0.08,
        dropout_rate=0.25, noise_db=-65.0, width=0.98,
        compression=3.0, agc=0.24,
    ),
))


register_preset(Preset(
    id="auth-eurodance-music-video",
    name="Eurodance Music Video",
    family="broadcast",
    era="1996",
    desc="A glossy studio-video master drives cobalt light and magenta highlights into vivid tube color, smooth phosphor persistence and clean composite edges while retaining the supplied stereo dance mix.",
    tagline="Cobalt studio color on a glossy video master",
    tags=("90s", "eurodance", "music-video", "studio-video", "source-preserving"),
    proc_height=600,
    upscale="soft",
    video=_analog_video(
        exposure=0.06, contrast=1.16, lift=0.026, knee=0.64, warmth=-0.1,
        tint=0.06, shadow_tint="blue", shadow_amt=0.4,
        high_tint="pink", high_amt=0.28, saturation=1.3, vibrance=0.16,
        soft_focus=0.05, diffusion=0.14, flare=0.22, trail=0.28,
        luma_bw=4.3, chroma_bw=0.96, phase_noise=1.15, dot_crawl=0.2,
        rainbow=0.18, fringing=0.9, tape_luma=0.1, tape_chroma=0.13,
        time_base=0.07, tracking=0.02, dropouts=0.12, sharpen=0.58,
        interlace=0.45,
    ),
    audio=_video_audio(
        tape_format="betahifi", mic_amount=0.04, tracking=0.05,
        dropout_rate=0.15, noise_db=-67.0, compander_error=0.04,
        width=1.04, compression=4.2, agc=0.3,
    ),
))


register_preset(Preset(
    id="auth-r-b-slow-jam-video",
    name="R&B Slow-Jam Video",
    family="film",
    era="1996",
    desc="A fine-grain 35 mm negative wraps polished interiors in warm pearlescent diffusion, creamy highlight halation and restrained shadow dye, with a wide low-generation analog stereo master.",
    tagline="Pearlescent warmth on fine-grain 35 mm",
    tags=("90s", "r-and-b", "music-video", "35mm", "source-preserving"),
    video=_film(
        profile="vision_90s", stock_strength=0.82, exposure=0.12,
        contrast=1.08, lift=0.04, knee=0.68, warmth=0.2,
        shadow_tint="brown", shadow_amt=0.1, high_tint="cream",
        high_amt=0.28, saturation=1.08, vibrance=0.08, soft_focus=0.14,
        diffusion=0.34, corner_softness=0.12, veiling_flare=0.24,
        grain=0.22, grain_size=1.35, chroma_grain=0.08, halation=0.36,
        gate_weave=0.26, flicker=0.02, dust=0.05,
    ),
    audio=_film_audio(
        generations=1, alignment=0.04, compression=0.28,
        hiss_db=-70.0, width=1.08, crosstalk_db=-54.0,
    ),
))


register_preset(Preset(
    id="auth-rooftop-hip-hop-promo",
    name="Rooftop Hip-Hop Promo",
    family="film",
    era="1994",
    desc="A pushed 16 mm rooftop negative combines hard sky contrast, broad-lens edge bend, coarse silver texture and slight cyan shadow dye with a punchy but source-faithful analog stereo dub.",
    tagline="Hard-sky contrast on pushed rooftop 16 mm",
    tags=("90s", "hip-hop", "rooftop", "16mm", "source-preserving"),
    video=_film(
        profile="vision_90s", stock_strength=0.78, exposure=-0.08,
        contrast=1.28, lift=0.018, knee=0.66, warmth=-0.04,
        shadow_tint="teal", shadow_amt=0.22, high_tint="cream",
        high_amt=0.08, saturation=0.88, vibrance=-0.04, soft_focus=0.04,
        diffusion=0.04, corner_softness=0.16, aberration=0.5,
        veiling_flare=0.16, distortion=0.12, grain=0.54,
        grain_size=2.25, grain_stock="push_process", chroma_grain=0.16,
        halation=0.25, gate_weave=0.62, flicker=0.04, dust=0.14,
    ),
    audio=_film_audio(
        generations=2, alignment=0.1, compression=0.44,
        hiss_db=-63.0, width=0.96, crosstalk_db=-45.0,
    ),
))


register_preset(Preset(
    id="auth-country-music-television-video",
    name="Country-Music Television Video",
    family="film",
    era="1995",
    desc="A warm 35 mm negative carries honeyed daylight, softly veiled landscapes and fine print grain through a clean television transfer, leaving the original Nashville production fully intact.",
    tagline="Honeyed 35 mm through a clean TV transfer",
    tags=("90s", "country", "music-video", "telecine", "source-preserving"),
    proc_height=640,
    upscale="soft",
    video=_film_to_video(
        film=_film(
            profile="vision_90s", stock_strength=0.8, exposure=0.1,
            contrast=1.08, lift=0.036, knee=0.74, warmth=0.2,
            shadow_tint="brown", shadow_amt=0.08, high_tint="yellow",
            high_amt=0.18, saturation=1.06, vibrance=0.08,
            soft_focus=0.1, diffusion=0.18, corner_softness=0.1,
            veiling_flare=0.2, grain=0.25, grain_size=1.45,
            chroma_grain=0.08, halation=0.28, gate_weave=0.3,
            flicker=0.02, dust=0.05,
        )
    ),
    audio=_video_audio(
        tape_format="betahifi", mic_amount=0.03, tracking=0.04,
        dropout_rate=0.12, noise_db=-69.0, width=1.02,
        compression=3.2, agc=0.2,
    ),
))


register_preset(Preset(
    id="auth-mall-portrait-studio-commercial",
    name="Mall Portrait-Studio Commercial",
    family="broadcast",
    era="1997",
    desc="A soft studio-video master gives pastel backdrops creamy tube highlights, restrained pink warmth, gauze diffusion and low-noise composite edges while preserving the supplied voice and music track.",
    tagline="Pastel tube color behind creamy studio gauze",
    tags=("90s", "commercial", "portrait-studio", "analog-video", "source-preserving"),
    proc_height=600,
    upscale="soft",
    video=_analog_video(
        exposure=0.12, contrast=1.0, lift=0.06, knee=0.66, warmth=0.14,
        tint=0.06, high_tint="cream", high_amt=0.24, saturation=0.96,
        vibrance=-0.02, soft_focus=0.16, diffusion=0.34, flare=0.18,
        trail=0.1, luma_bw=4.2, chroma_bw=0.94, phase_noise=0.9,
        dot_crawl=0.14, rainbow=0.1, fringing=0.62, tape_luma=0.08,
        tape_chroma=0.1, time_base=0.05, tracking=0.01, dropouts=0.08,
        sharpen=0.38, interlace=0.42,
    ),
    audio=_video_audio(
        tape_format="betahifi", mic="lavalier_1972", mic_amount=0.18,
        overload=0.06, tracking=0.04, dropout_rate=0.1, noise_db=-68.0,
        width=0.96, compression=3.5, agc=0.32,
    ),
))
