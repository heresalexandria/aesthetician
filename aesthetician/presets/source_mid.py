"""Source-preserving audiovisual looks from the 1960s and 1970s.

The treatments in this module model acquisition, laboratory, carrier, transfer,
and playback.  They deliberately leave shot order, frame timing, framing,
graphics, and the supplied program audio alone: no cadence remaps, editorial
overlays, replacement beds, or synthetic score are used.
"""

from __future__ import annotations

from typing import Any

from ..engine.presets import ChainSpec, Preset, Variant, register_preset


def _variants(video: ChainSpec, audio: ChainSpec) -> list[Variant]:
    """Build two conservative, non-editorial medium-condition variants."""
    v = {eid: params for eid, params in video}
    a = {eid: params for eid, params in audio}
    clean_v: dict[str, Any] = {}
    copy_v: dict[str, Any] = {}
    clean_a: dict[str, Any] = {}
    copy_a: dict[str, Any] = {}

    if "grain" in v:
        amount = float(v["grain"].get("amount", 0.35))
        clean_v["grain.amount"] = max(0.12, amount * 0.7)
        copy_v["grain.amount"] = min(0.65, amount * 1.18)
    if "gate_weave" in v:
        amount = float(v["gate_weave"].get("amount", 0.8))
        clean_v["gate_weave.amount"] = amount * 0.55
        copy_v["gate_weave.amount"] = min(3.2, amount * 1.28)
    if "flicker" in v:
        amount = float(v["flicker"].get("amount", 0.1))
        clean_v["flicker.amount"] = amount * 0.45
        copy_v["flicker.amount"] = min(0.6, amount * 1.3)
    if "dust" in v:
        amount = float(v["dust"].get("density", 0.25))
        clean_v["dust.density"] = amount * 0.3
        copy_v["dust.density"] = min(1.0, amount * 1.3)
    if "scratches" in v:
        count = int(v["scratches"].get("count", 1))
        clean_v["scratches.count"] = max(0, count - 1)
        copy_v["scratches.count"] = min(8, count + 1)
    if "ntsc" in v:
        strength = float(v["ntsc"].get("strength", 0.65))
        phase = float(v["ntsc"].get("phase_noise", 1.0))
        clean_v["ntsc.strength"] = strength * 0.7
        clean_v["ntsc.phase_noise"] = phase * 0.45
        copy_v["ntsc.phase_noise"] = min(6.0, phase * 1.25)
    if "vhs" in v:
        mode = str(v["vhs"].get("mode", "sp"))
        cap = {"sp": 0.7, "lp": 0.45, "ep": 0.32}.get(mode, 0.7)
        ln = float(v["vhs"].get("luma_noise", 0.2))
        cn = float(v["vhs"].get("chroma_noise", 0.2))
        clean_v["vhs.luma_noise"] = ln * 0.55
        clean_v["vhs.chroma_noise"] = cn * 0.55
        clean_v["vhs.dropouts"] = float(v["vhs"].get("dropouts", 0.3)) * 0.25
        copy_v["vhs.luma_noise"] = min(cap, ln * 1.2)
        copy_v["vhs.chroma_noise"] = min(cap, cn * 1.2)
        copy_v["vhs.dropouts"] = min(8.0, float(v["vhs"].get("dropouts", 0.3)) * 1.4)
    if "signal_rf" in v:
        snow = float(v["signal_rf"].get("snow", 0.1))
        clean_v["signal_rf.snow"] = snow * 0.35
        copy_v["signal_rf.snow"] = min(0.65, snow * 1.35)

    if "a_optical_track" in a:
        noise = float(a["a_optical_track"].get("cell_noise", -50.0))
        flutter = float(a["a_optical_track"].get("flutter", 0.35))
        clean_a["a_optical_track.cell_noise"] = max(-75.0, noise - 7.0)
        clean_a["a_optical_track.flutter"] = flutter * 0.45
        copy_a["a_optical_track.cell_noise"] = min(-28.0, noise + 5.0)
        copy_a["a_optical_track.flutter"] = min(1.0, flutter * 1.25)
    if "a_analog_dub" in a:
        generations = int(a["a_analog_dub"].get("generations", 1))
        alignment = float(a["a_analog_dub"].get("alignment", 0.15))
        hiss = float(a["a_analog_dub"].get("hiss_db", -58.0))
        clean_a["a_analog_dub.generations"] = max(0, generations - 1)
        clean_a["a_analog_dub.alignment"] = alignment * 0.45
        clean_a["a_analog_dub.hiss_db"] = max(-80.0, hiss - 7.0)
        copy_a["a_analog_dub.generations"] = min(8, generations + 1)
        copy_a["a_analog_dub.alignment"] = min(1.0, alignment * 1.3)
        copy_a["a_analog_dub.hiss_db"] = min(-32.0, hiss + 5.0)
    if "a_video_tape_audio" in a:
        tracking = float(a["a_video_tape_audio"].get("tracking", 0.2))
        noise = float(a["a_video_tape_audio"].get("noise_db", -52.0))
        dropouts = float(a["a_video_tape_audio"].get("dropout_rate", 4.0))
        clean_a["a_video_tape_audio.tracking"] = tracking * 0.4
        clean_a["a_video_tape_audio.noise_db"] = max(-80.0, noise - 7.0)
        clean_a["a_video_tape_audio.dropout_rate"] = dropouts * 0.25
        copy_a["a_video_tape_audio.tracking"] = min(1.0, tracking * 1.3)
        copy_a["a_video_tape_audio.noise_db"] = min(-30.0, noise + 5.0)
        copy_a["a_video_tape_audio.dropout_rate"] = min(90.0, dropouts * 1.35)

    return [
        Variant(
            "reference-element",
            "Reference Element",
            "The best surviving element: the same capture signature with its carrier close to alignment.",
            video=clean_v,
            audio=clean_a,
        ),
        Variant(
            "circulation-copy",
            "Circulation Copy",
            "A routine period copy with modestly softer registration, wider wear, and a noisier carrier.",
            video=copy_v,
            audio=copy_a,
        ),
    ]


def _preset(
    pid: str,
    name: str,
    era: str,
    family: str,
    desc: str,
    tagline: str,
    tags: tuple[str, ...],
    video: ChainSpec,
    audio: ChainSpec,
    proc_height: int | None = None,
    upscale: str = "auto",
) -> Preset:
    return Preset(
        id=pid,
        name=name,
        era=era,
        family=family,
        desc=desc,
        tagline=tagline,
        tags=(*tags, "source-preserving"),
        video=video,
        audio=audio,
        proc_height=proc_height,
        upscale=upscale,
        variants=_variants(video, audio),
    )


def _film(
    *,
    profile: str = "eastman_60s",
    strength: float = 0.75,
    mono: bool = False,
    mono_response: str = "panchromatic",
    mono_tint: str = "silver",
    mono_tint_amt: float = 0.12,
    exposure: float = 0.0,
    contrast: float = 1.12,
    lift: float = 0.025,
    knee: float = 0.82,
    warmth: float = 0.04,
    tint: float = 0.0,
    shadow_tint: str = "none",
    shadow_amt: float = 0.0,
    high_tint: str = "none",
    high_amt: float = 0.0,
    sat: float = 1.0,
    vibrance: float = 0.05,
    soft: float = 0.08,
    diffusion: float = 0.05,
    corner: float = 0.1,
    focus: float = 0.04,
    distortion: float = 0.0,
    flare: float = 0.08,
    ghost: float = 0.0,
    auto_gain: float = 0.0,
    auto_lag: float = 0.8,
    composite: float = 0.0,
    registration: float = 0.0,
    grain: float = 0.35,
    grain_size: float = 1.75,
    grain_stock: str = "fine_35",
    grain_layers: str = "color_neg",
    shadow_grain: float = 0.08,
    mottle: float = 0.08,
    halation: float = 0.25,
    halation_tint: str = "red_orange",
    buildup: int = 1,
    dmax: float = 0.12,
    acutance: float = 0.2,
    fade: float = 0.0,
    fade_profile: str = "neutral",
    weave: float = 0.7,
    splice: float = 0.25,
    flicker: float = 0.09,
    color_flicker: float = 0.04,
    dust: float = 0.22,
    hairs: float = 0.08,
    scratches: int = 0,
    scratch_strength: float = 0.35,
    leak: float = 0.0,
    leak_constant: float = 0.0,
    vignette: float = 0.2,
) -> ChainSpec:
    chain: ChainSpec = []
    if mono:
        chain.append(("mono", {"response": mono_response, "tint": mono_tint,
                               "tint_amt": mono_tint_amt}))
    else:
        chain.append(("stock", {"profile": profile, "strength": strength}))
    chain.extend([
        ("tone", {"exposure": exposure, "contrast": contrast, "lift": lift,
                  "knee": knee, "pivot": 0.42}),
        ("balance", {"warmth": warmth, "tint": tint, "shadow_tint": shadow_tint,
                     "shadow_amt": shadow_amt, "high_tint": high_tint,
                     "high_amt": high_amt}),
        ("saturation", {"amount": sat, "vibrance": vibrance}),
        ("optics", {"soft_focus": soft, "diffusion": diffusion,
                    "bloom_mids": round(min(0.55, diffusion * 1.25), 3),
                    "corner_softness": corner, "focus_drift": focus,
                    "distortion": distortion, "veiling_flare": flare,
                    "aperture_ghost": ghost}),
    ])
    if auto_gain > 0.0:
        chain.append(("exposure_auto", {"lag": auto_lag, "overshoot": 0.38,
                                         "max_boost": 4.0, "agc_gain_noise": auto_gain,
                                         "wb_amount": 0.16, "iris_step": 0.22}))
    if composite > 0.0 or registration > 0.0:
        chain.append(("optical_composite", {"softness": composite,
                                             "registration": registration,
                                             "layer_haze": composite * 0.25,
                                             "density_breath": composite * 0.22}))
    chain.extend([
        ("grain", {"amount": grain, "size": grain_size, "chroma_grain": 0.0 if mono else 0.16,
                   "stock": grain_stock, "layers": "mono" if mono else grain_layers,
                   "shadow_boost": shadow_grain, "mottle": mottle}),
        ("halation", {"strength": halation, "threshold": 0.72,
                      "radius": 0.05, "tint": halation_tint}),
        ("print_char", {"contrast_buildup": buildup, "dmax_breath": dmax,
                        "acutance": acutance}),
    ])
    if fade > 0.0:
        chain.append(("fade", {"amount": fade, "profile": fade_profile,
                               "bloom_whites": fade * 0.45}))
    chain.extend([
        ("gate_weave", {"amount": weave, "hz": 0.62, "rotation": 0.025,
                        "splice_bump": splice}),
        ("flicker", {"amount": flicker, "character": "slow_drift",
                     "color_flicker": color_flicker, "spatial": 0.1}),
        ("dust", {"density": dust, "size": 0.9, "hairs": hairs}),
    ])
    if scratches > 0:
        chain.append(("scratches", {"strength": scratch_strength, "count": scratches,
                                     "wander": 0.45, "transient_rate": 0.7}))
    if leak > 0.0 or leak_constant > 0.0:
        chain.append(("light_leak", {"amount": leak, "hue": "warm", "frequency": 0.5,
                                     "constant": leak_constant, "sprocket_side": 0.22}))
    chain.append(("vignette", {"amount": vignette, "softness": 0.7, "roundness": 0.88}))
    return chain


def _film_to_tv(
    chain: ChainSpec,
    *,
    system: str = "ntsc",
    strength: float = 0.55,
    luma_bw: float = 3.7,
    chroma_bw: float = 0.78,
    phase_noise: float = 1.4,
    rainbow: float = 0.2,
    dot_crawl: float = 0.24,
    bloom: float = 0.2,
) -> ChainSpec:
    return chain + [
        ("ntsc", {"system": system, "strength": strength, "luma_bw": luma_bw,
                  "chroma_bw": chroma_bw, "phase_noise": phase_noise,
                  "rainbow": rainbow, "dot_crawl": dot_crawl,
                  "setup_level": 0.055 if system == "ntsc" else 0.0}),
        ("interlace", {"field_order": "tff", "combing": 0.48, "twitter": 0.22}),
        ("crt", {"bloom": bloom, "beam_bloom": bloom * 0.65,
                 "misconvergence": 0.16, "scan_strength": 0.06}),
    ]


def _broadcast(
    *,
    mono: bool = False,
    mono_tint: str = "silver",
    stock: str = "tube_70s",
    strength: float = 0.76,
    exposure: float = 0.03,
    contrast: float = 1.06,
    lift: float = 0.035,
    knee: float = 0.76,
    warmth: float = 0.03,
    tint: float = 0.0,
    shadow_tint: str = "none",
    shadow_amt: float = 0.0,
    high_tint: str = "none",
    high_amt: float = 0.0,
    sat: float = 1.0,
    soft: float = 0.08,
    diffusion: float = 0.04,
    flare: float = 0.06,
    auto_gain: float = 0.18,
    auto_lag: float = 0.9,
    phosphor: float = 0.16,
    system: str = "ntsc",
    ntsc_strength: float = 0.72,
    luma_bw: float = 3.6,
    chroma_bw: float = 0.75,
    phase_noise: float = 1.6,
    rainbow: float = 0.22,
    dot_crawl: float = 0.26,
    sync_jitter: float = 0.08,
    rf_snow: float = 0.0,
    rf_weak: float = 0.0,
    rf_ghost: float = 0.0,
    rf_impulse: float = 0.0,
    herringbone: float = 0.0,
    tape: bool = False,
    tape_noise: float = 0.16,
    tape_chroma_noise: float = 0.18,
    tape_dropouts: float = 0.25,
    tape_tbe: float = 0.12,
    combing: float = 0.5,
    twitter: float = 0.24,
    bloom: float = 0.26,
    beam_bloom: float = 0.18,
    misconvergence: float = 0.22,
    scan: float = 0.08,
) -> ChainSpec:
    chain: ChainSpec = []
    if mono:
        chain.append(("mono", {"response": "modern", "tint": mono_tint, "tint_amt": 0.1}))
    else:
        chain.append(("stock", {"profile": stock, "strength": strength}))
    chain.extend([
        ("tone", {"exposure": exposure, "contrast": contrast, "lift": lift, "knee": knee}),
        ("balance", {"warmth": warmth, "tint": tint, "shadow_tint": shadow_tint,
                     "shadow_amt": shadow_amt, "high_tint": high_tint, "high_amt": high_amt}),
        ("saturation", {"amount": 1.0 if mono else sat, "vibrance": 0.03}),
        ("optics", {"soft_focus": soft, "diffusion": diffusion,
                    "bloom_mids": diffusion * 1.2, "veiling_flare": flare,
                    "corner_softness": 0.08}),
        ("exposure_auto", {"lag": auto_lag, "overshoot": 0.22, "max_boost": 3.0,
                           "agc_gain_noise": auto_gain, "wb_amount": 0.24,
                           "iris_step": 0.1}),
        ("phosphor_decay", {"decay": phosphor,
                            "mode": "green_mono" if mono_tint == "phosphor_green" else "p22"}),
        ("ntsc", {"system": system, "strength": ntsc_strength, "luma_bw": luma_bw,
                  "chroma_bw": chroma_bw, "rainbow": 0.0 if mono else rainbow,
                  "dot_crawl": 0.0 if mono else dot_crawl, "phase_noise": phase_noise,
                  "setup_level": 0.055 if system == "ntsc" else 0.0,
                  "sync_jitter": sync_jitter}),
    ])
    if rf_snow > 0.0 or rf_weak > 0.0 or rf_ghost > 0.0 or rf_impulse > 0.0:
        chain.append(("signal_rf", {"snow": rf_snow, "sparkle": 2.4,
                                    "ghost_n": 1 if rf_ghost > 0.0 else 0,
                                    "ghost_px": 11.0, "ghost_alpha": rf_ghost,
                                    "impulse_noise": rf_impulse, "weak_signal": rf_weak}))
    if herringbone > 0.0:
        chain.append(("herringbone", {"amount": herringbone, "pattern": "diagonal_bars",
                                      "wavelength": 12.0, "drift": 0.45}))
    if tape:
        chain.append(("vhs", {"mode": "sp", "luma_bw": 4.5, "chroma_bw": 0.72,
                              "chroma_delay": 0.7, "sharpen": 0.42,
                              "luma_noise": tape_noise, "chroma_noise": tape_chroma_noise,
                              "head_switch": 0.18, "dropouts": tape_dropouts,
                              "time_base_error": tape_tbe, "flagging": 0.05,
                              "tracking_error": 0.01}))
    chain.extend([
        ("interlace", {"field_order": "tff", "combing": combing, "twitter": twitter}),
        ("crt", {"bloom": bloom, "beam_bloom": beam_bloom,
                 "misconvergence": 0.0 if mono else misconvergence,
                 "scan_strength": scan, "curvature": 0.0}),
    ])
    return chain


def _optical_audio(
    *,
    mic: str | None = None,
    mic_amount: float = 0.34,
    room: float = 0.0,
    low: float = 90.0,
    high: float = 7200.0,
    cell_noise: float = -52.0,
    flutter: float = 0.28,
    drive: float = 1.45,
    mono: float = 1.0,
    ratio: float = 3.2,
    distortion: float = 0.0,
) -> ChainSpec:
    chain: ChainSpec = []
    if room > 0.0:
        chain.append(("a_room", {"mode": "room", "size": 0.9, "decay_s": 0.38,
                                 "damp": 0.65, "mix": room}))
    if mic:
        chain.append(("a_historical_mic", {"profile": mic, "amount": mic_amount,
                                            "proximity": 0.08, "overload": 0.18,
                                            "self_noise_db": -60.0, "handling": 0.03}))
    if mono > 0.0:
        chain.append(("a_mono", {"amount": mono}))
    chain.extend([
        ("a_optical_track", {"low_hz": low, "high_hz": high,
                             "academy_rolloff": "none", "cell_noise": cell_noise,
                             "flutter": flutter, "drive": drive}),
        ("a_compressor", {"threshold_db": -21.0, "ratio": ratio,
                          "attack_ms": 7.0, "release_ms": 220.0, "knee_db": 5.0}),
    ])
    if distortion > 0.0:
        chain.append(("a_distortion", {"type": "soft", "drive": distortion, "tone": -0.08}))
    return chain


def _mag_audio(
    *,
    tape_format: str = "reel_75ips",
    mic: str | None = None,
    mic_amount: float = 0.4,
    room: float = 0.0,
    mono: float = 1.0,
    generations: int = 1,
    alignment: float = 0.16,
    compression: float = 0.3,
    hiss_db: float = -58.0,
    width: float = 0.88,
    ratio: float = 3.0,
    distortion: float = 0.0,
) -> ChainSpec:
    chain: ChainSpec = []
    if room > 0.0:
        chain.append(("a_room", {"mode": "room", "size": 1.0, "decay_s": 0.4,
                                 "damp": 0.62, "mix": room}))
    if mic:
        chain.append(("a_historical_mic", {"profile": mic, "amount": mic_amount,
                                            "proximity": 0.06, "overload": 0.22,
                                            "self_noise_db": -58.0, "handling": 0.08}))
    if mono > 0.0:
        chain.append(("a_mono", {"amount": mono}))
    chain.extend([
        ("a_analog_dub", {"format": tape_format, "generations": generations,
                          "alignment": alignment, "compression": compression,
                          "hiss_db": hiss_db}),
        ("a_tape_sat", {"drive": 2.0 + compression * 2.0, "bump_db": 1.4,
                        "hf_loss": alignment * 0.5}),
        ("a_channel_aging", {"width": width, "imbalance_db": -0.2,
                             "crosstalk_db": -46.0, "skew_us": 32.0,
                             "phase_wander": round(alignment * 0.35, 3),
                             "mono_bass_hz": 110.0}),
        ("a_compressor", {"threshold_db": -20.0, "ratio": ratio,
                          "attack_ms": 7.0, "release_ms": 210.0, "knee_db": 5.0}),
    ])
    if distortion > 0.0:
        chain.append(("a_distortion", {"type": "soft", "drive": distortion, "tone": -0.05}))
    return chain


def _tv_audio(
    *,
    mic: str | None = "broadcast_dynamic_1955",
    mic_amount: float = 0.42,
    room: float = 0.0,
    mono: float = 1.0,
    low: float = 100.0,
    high: float = 9000.0,
    carrier: str = "reel_15ips",
    generations: int = 1,
    tracking: float = 0.16,
    noise_db: float = -57.0,
    agc: float = 0.45,
    ratio: float = 4.0,
    hz: str = "60",
    width: float = 0.82,
) -> ChainSpec:
    chain: ChainSpec = []
    if room > 0.0:
        chain.append(("a_room", {"mode": "room", "size": 0.85, "decay_s": 0.34,
                                 "damp": 0.68, "mix": room}))
    if mic:
        chain.append(("a_historical_mic", {"profile": mic, "amount": mic_amount,
                                            "proximity": 0.08, "overload": 0.14,
                                            "self_noise_db": -62.0, "handling": 0.02}))
    chain.append(("a_bandlimit", {"low_hz": low, "high_hz": high}))
    if mono > 0.0:
        chain.append(("a_mono", {"amount": mono}))
    if carrier in {"umatic_linear", "betamax_linear", "vhs_linear", "betahifi", "vhs_hifi"}:
        chain.append(("a_video_tape_audio", {"format": carrier, "tracking": tracking,
                                              "dropout_rate": 1.5,
                                              "noise_db": noise_db,
                                              "head_switch_db": -64.0,
                                              "compander_error": 0.0}))
    else:
        chain.append(("a_analog_dub", {"format": carrier, "generations": generations,
                                        "alignment": tracking, "compression": 0.34,
                                        "hiss_db": noise_db}))
    chain.extend([
        ("a_channel_aging", {"width": width, "imbalance_db": -0.2,
                             "crosstalk_db": -44.0, "skew_us": 36.0,
                             "phase_wander": round(tracking * 0.35, 3),
                             "mono_bass_hz": 120.0}),
        ("a_agc", {"target_db": -17.0, "max_gain_db": 9.0,
                   "attack_ms": 24.0, "release_ms": 700.0, "amount": agc}),
        ("a_compressor", {"threshold_db": -21.0, "ratio": ratio,
                          "attack_ms": 5.0, "release_ms": 210.0, "knee_db": 5.0}),
        ("a_tv_sound", {"hz": hz, "buzz_db": -57.0, "hum_db": -63.0, "comp": 0.38}),
    ])
    return chain


# 64, 66-68, 70-72, 74, 76-77, 79-81, 83-84: missing 1960s looks.
register_preset(_preset(
    "auth-italian-mondo-documentary-1964", "Italian Mondo Documentary", "1964", "film",
    "A glossy Eastmancolor travel negative carried through a slightly contrasty release print: sun-warm skin, cyan distance, polished zoom-era glass, fine 35 mm grain, and intact mono program on a bright optical track.",
    "Glossy Eastmancolor and bright optical mono", ("60s", "mondo", "35mm", "documentary"),
    _film(profile="eastman_60s", strength=0.82, exposure=0.1, contrast=1.18, warmth=0.14,
          shadow_tint="teal", shadow_amt=0.12, high_tint="cream", high_amt=0.14,
          sat=1.18, vibrance=0.14, soft=0.06, diffusion=0.06, flare=0.14,
          grain=0.3, grain_size=1.55, halation=0.28, acutance=0.32, dust=0.14),
    _optical_audio(mic="broadcast_dynamic_1955", mic_amount=0.2, high=7600.0,
                   cell_noise=-55.0, flutter=0.2, drive=1.4, ratio=3.6),
    proc_height=700, upscale="sharp",
))

register_preset(_preset(
    "auth-czech-new-wave-surrealism-1966", "Czech New Wave Surrealism", "1966", "world",
    "An Agfa-like Central European color print with pale candy highlights, cool plaster shadows, tactile optical layering, modest registration drift, fine 35 mm texture, and a dry mono optical program path.",
    "Pale Agfa color and tactile optical layers", ("60s", "czech-new-wave", "agfa", "optical"),
    _film(profile="agfa_60s", strength=0.88, contrast=1.08, lift=0.045, warmth=-0.03,
          tint=0.04, shadow_tint="blue", shadow_amt=0.12, high_tint="pink", high_amt=0.1,
          sat=0.96, soft=0.08, diffusion=0.12, composite=0.24, registration=0.32,
          grain=0.36, grain_size=1.7, halation=0.22, weave=0.82, flicker=0.11,
          dust=0.2, vignette=0.16),
    _optical_audio(high=6800.0, cell_noise=-51.0, flutter=0.3, drive=1.5, ratio=3.0),
    proc_height=660, upscale="soft",
))

register_preset(_preset(
    "auth-polish-school-monochrome-1962", "Polish School Monochrome", "1962", "world",
    "A silver-rich panchromatic print built for smoke and winter windows: hard midtone separation, held highlights, dense shadow grain, restrained gate motion, and a severe narrow mono optical track.",
    "Silver contrast, smoky grain, austere mono", ("60s", "polish-school", "monochrome", "35mm"),
    _film(mono=True, mono_response="panchromatic", mono_tint="silver", mono_tint_amt=0.18,
          contrast=1.34, lift=0.018, knee=0.72, warmth=-0.06, sat=1.0,
          soft=0.05, diffusion=0.05, corner=0.15, flare=0.08, grain=0.42,
          grain_size=1.65, grain_stock="fine_35", shadow_grain=0.28,
          halation=0.2, halation_tint="neutral", buildup=2, dmax=0.22,
          weave=0.58, flicker=0.08, dust=0.2, vignette=0.3),
    _optical_audio(low=110.0, high=6200.0, cell_noise=-49.0, flutter=0.32,
                   drive=1.55, ratio=3.8), proc_height=680, upscale="sharp",
))

register_preset(_preset(
    "auth-japanese-new-wave-urbanism-1965", "Japanese New Wave Urbanism", "1965", "world",
    "A pushed monochrome street negative with hard white signage, deep asphalt blacks, wide-angle edge stress, honest handheld gate motion, coarse 35 mm grain, and portable-reel location sound kept sharply mono.",
    "Pushed street silver and portable-reel mono", ("60s", "japanese-new-wave", "street", "monochrome"),
    _film(mono=True, mono_response="panchromatic", mono_tint="neutral", mono_tint_amt=0.04,
          exposure=-0.05, contrast=1.28, lift=0.012, knee=0.76, warmth=-0.08,
          soft=0.025, diffusion=0.02, corner=0.18, distortion=-0.04, flare=0.12,
          grain=0.18, grain_size=1.2, grain_stock="push_process", shadow_grain=0.08,
          mottle=0.025, halation=0.24, halation_tint="neutral", buildup=2, weave=0.7,
          flicker=0.07, dust=0.08, scratches=1, vignette=0.22),
    _mag_audio(tape_format="reel_75ips", mic="shotgun_1975", mic_amount=0.46,
               mono=1.0, alignment=0.24, compression=0.36, hiss_db=-54.0,
               width=0.3, ratio=3.6), proc_height=720, upscale="sharp",
))

register_preset(_preset(
    "auth-soviet-cosmic-modernism-1968", "Soviet Cosmic Modernism", "1968", "world",
    "A carefully exposed ORWO/Svema-style 35 mm element: cool concrete, muted cyan color, restrained warm skin, long-scale highlights, low print wear, and a sober mono magnetic-to-optical program transfer.",
    "Cool ORWO concrete and restrained print scale", ("60s", "soviet", "orwo", "science-fiction"),
    _film(profile="orwo_east", strength=0.94, exposure=-0.05, contrast=1.04, lift=0.055,
          knee=0.86, warmth=-0.14, tint=-0.04, shadow_tint="blue", shadow_amt=0.2,
          high_tint="cyan", high_amt=0.08, sat=0.78, vibrance=-0.08, soft=0.08,
          diffusion=0.08, flare=0.12, grain=0.34, grain_size=1.62, halation=0.2,
          weave=0.48, flicker=0.05, dust=0.1, vignette=0.18),
    _mag_audio(tape_format="reel_15ips", mono=1.0, generations=1, alignment=0.12,
               compression=0.24, hiss_db=-62.0, width=0.25, ratio=2.6),
    proc_height=720, upscale="soft",
))

register_preset(_preset(
    "auth-eastern-european-stop-motion-1965", "Eastern European Stop-Motion", "1965", "world",
    "A puppet stage photographed one exposure at a time on cool Agfa stock: macro-lens softness, shallow edge falloff, visible but continuous gate chatter, layered optical density, compact 16 mm grain, and an intact mono optical stripe.",
    "Cool puppet-stage color and gate chatter", ("60s", "stop-motion", "puppet", "16mm"),
    _film(profile="agfa_60s", strength=0.9, contrast=1.14, lift=0.03, warmth=-0.04,
          tint=0.03, shadow_tint="blue", shadow_amt=0.12, high_tint="cream", high_amt=0.1,
          sat=1.04, soft=0.17, diffusion=0.08, corner=0.3, focus=0.14,
          composite=0.16, registration=0.22, grain=0.42, grain_size=1.85,
          grain_stock="doc_16", halation=0.24, weave=1.35, splice=0.55,
          flicker=0.14, color_flicker=0.08, dust=0.3, vignette=0.28),
    _optical_audio(low=110.0, high=6500.0, cell_noise=-48.0, flutter=0.4,
                   drive=1.65, ratio=3.4), proc_height=600, upscale="soft",
))

register_preset(_preset(
    "auth-biker-exploitation-1967", "Biker Exploitation", "1967", "film",
    "A sun-baked low-budget Eastmancolor print with ochre dust, hard road highlights, wandering zoom focus, thick 16 mm-sized grain, modest drive-in wear, and the supplied soundtrack squeezed through gritty mono optical playback.",
    "Sun-baked Eastman and optical grit", ("60s", "biker", "exploitation", "drive-in"),
    _film(profile="eastman_60s", strength=0.88, exposure=0.12, contrast=1.24, lift=0.025,
          knee=0.72, warmth=0.22, tint=-0.04, shadow_tint="brown", shadow_amt=0.24,
          high_tint="yellow", high_amt=0.14, sat=1.04, soft=0.08, diffusion=0.04,
          focus=0.2, flare=0.2, grain=0.48, grain_size=1.95, grain_stock="doc_16",
          halation=0.34, buildup=2, dmax=0.2, fade=0.08, fade_profile="eastman_pink",
          weave=1.1, flicker=0.12, dust=0.46, scratches=2, vignette=0.28),
    _optical_audio(mic="shotgun_1975", mic_amount=0.28, low=100.0, high=6800.0,
                   cell_noise=-45.0, flutter=0.44, drive=1.9, ratio=4.0,
                   distortion=1.5), proc_height=620, upscale="soft",
))

register_preset(_preset(
    "auth-mission-control-television-feed-1969", "Mission-Control Television Feed", "1969", "broadcast",
    "A monochrome mission-room camera and microwave monitor path: image-orthicon bloom, clipped console whites, narrow horizontal detail, restrained RF snow, interlace twitter, and headset speech on a hard-limited reel master.",
    "Orthicon bloom, RF snow, clipped headset mono", ("60s", "mission-control", "television", "monochrome"),
    _broadcast(mono=True, mono_tint="silver", exposure=0.05, contrast=1.16, lift=0.045,
               knee=0.66, soft=0.12, diffusion=0.06, flare=0.12, auto_gain=0.2,
               phosphor=0.24, ntsc_strength=0.58, luma_bw=2.9, chroma_bw=0.4,
               phase_noise=0.8, sync_jitter=0.16, rf_snow=0.1, rf_weak=0.12,
               rf_ghost=0.06, rf_impulse=0.7, combing=0.56, twitter=0.34,
               bloom=0.44, beam_bloom=0.36, scan=0.18),
    _tv_audio(mic="broadcast_dynamic_1955", mic_amount=0.72, room=0.05, low=220.0,
              high=4800.0, carrier="reel_75ips", generations=2, tracking=0.24,
              noise_db=-53.0, agc=0.72, ratio=6.0, width=0.2), proc_height=520,
    upscale="soft",
))

register_preset(_preset(
    "auth-public-television-science-lecture-1968", "Public-Television Science Lecture", "1968", "broadcast",
    "A restrained monochrome educational studio chain: clean orthicon gray, softly blooming chalk, stable scan structure, mild reel-master texture, and measured lectern speech captured by a period broadcast microphone.",
    "Clean orthicon gray and measured mono", ("60s", "public-television", "science", "lecture"),
    _broadcast(mono=True, exposure=0.02, contrast=1.08, lift=0.04, knee=0.72,
               soft=0.1, diffusion=0.04, flare=0.08, auto_gain=0.12, phosphor=0.16,
               ntsc_strength=0.46, luma_bw=3.4, chroma_bw=0.4, phase_noise=0.35,
               sync_jitter=0.05, combing=0.48, twitter=0.26, bloom=0.3,
               beam_bloom=0.22, scan=0.12),
    _tv_audio(mic="broadcast_dynamic_1955", mic_amount=0.62, room=0.12, low=120.0,
              high=6500.0, carrier="reel_15ips", tracking=0.1, noise_db=-62.0,
              agc=0.35, ratio=3.2, width=0.25), proc_height=560, upscale="soft",
))

register_preset(_preset(
    "auth-color-fashion-commercial-1966", "Color Fashion Commercial", "1966", "film",
    "A first-generation glossy 35 mm commercial element: saturated fabrics held inside a smooth Eastmancolor curve, silk-net diffusion, precise zoom-era glass, clean printer density, fine grain, and polished mono magnetic mastering.",
    "Silk diffusion, saturated fabric, fine 35 mm", ("60s", "fashion", "commercial", "35mm"),
    _film(profile="eastman_60s", strength=0.86, exposure=0.12, contrast=1.12, lift=0.025,
          knee=0.76, warmth=0.13, tint=0.04, high_tint="cream", high_amt=0.18,
          sat=1.3, vibrance=0.18, soft=0.12, diffusion=0.22, corner=0.08,
          focus=0.06, flare=0.18, ghost=0.1, grain=0.24, grain_size=1.45,
          halation=0.34, buildup=1, dmax=0.08, acutance=0.3, weave=0.4,
          flicker=0.04, dust=0.08, vignette=0.12),
    _mag_audio(tape_format="reel_15ips", mic="ribbon_1938", mic_amount=0.18,
               mono=0.72, generations=1, alignment=0.08, compression=0.28,
               hiss_db=-66.0, width=0.68, ratio=3.4), proc_height=720, upscale="sharp",
))

register_preset(_preset(
    "auth-underground-16mm-happening-1967", "Underground 16mm Happening", "1967", "film",
    "A reversal-loaded underground camera running close to the limit: overexposed whites, red sprocket fog, coarse 16 mm grain, breathing density, gate chatter and scratches, while raw room sound stays intact on a rough portable reel.",
    "Hot reversal, sprocket fog, raw portable reel", ("60s", "underground", "16mm", "reversal"),
    _film(profile="ektachrome", strength=0.78, exposure=0.36, contrast=1.18, lift=0.035,
          knee=0.64, warmth=0.14, tint=0.08, high_tint="pink", high_amt=0.18,
          sat=1.12, soft=0.1, diffusion=0.05, corner=0.18, focus=0.18,
          auto_gain=0.32, composite=0.1, grain=0.58, grain_size=2.05,
          grain_stock="doc_16", grain_layers="reversal", shadow_grain=0.26,
          halation=0.42, weave=1.65, splice=0.8, flicker=0.34,
          color_flicker=0.18, dust=0.5, scratches=3, leak=0.48,
          leak_constant=0.08, vignette=0.34),
    _mag_audio(tape_format="reel_375ips", mic="crystal_1940", mic_amount=0.6,
               room=0.18, mono=1.0, generations=2, alignment=0.38,
               compression=0.48, hiss_db=-49.0, width=0.2, ratio=4.8,
               distortion=1.7), proc_height=560, upscale="soft",
))

register_preset(_preset(
    "auth-pop-art-limited-animation-1967", "Pop-Art Limited Animation", "1967", "cartoon",
    "A bold graphic source photographed to high-saturation color film and carried through clean optical layers: primary dyes, slight record misregistration, compact 16 mm grain, restrained rostrum weave, and punchy optical mono.",
    "Primary dye, optical drift, 16 mm grain", ("60s", "pop-art", "limited-animation", "16mm"),
    _film(profile="technicolor3", strength=0.9, contrast=1.2, lift=0.02, knee=0.78,
          warmth=0.06, tint=0.05, high_tint="yellow", high_amt=0.1,
          sat=1.42, vibrance=0.26, soft=0.025, diffusion=0.02, corner=0.04,
          composite=0.16, registration=0.55, grain=0.3, grain_size=1.7,
          grain_stock="doc_16", halation=0.2, buildup=1, acutance=0.42,
          weave=0.72, flicker=0.07, dust=0.14, vignette=0.08),
    _optical_audio(low=90.0, high=7600.0, cell_noise=-53.0, flutter=0.22,
                   drive=1.65, ratio=5.0), proc_height=620, upscale="sharp",
))

register_preset(_preset(
    "auth-holiday-stop-motion-tv-special-1966", "Holiday Stop-Motion Television Special", "1966", "broadcast",
    "Warm miniature photography on fine 16 mm, transferred to an early color network master without altering the source motion: fuzzy lens edges, gentle gate chatter, festive dye density, composite softness, and warm mono reel sound.",
    "Warm miniature film through early color TV", ("60s", "stop-motion", "holiday", "television"),
    _film_to_tv(_film(profile="eastman_60s", strength=0.86, contrast=1.1, lift=0.035,
                      warmth=0.22, tint=0.04, shadow_tint="blue", shadow_amt=0.08,
                      high_tint="cream", high_amt=0.18, sat=1.14, soft=0.16,
                      diffusion=0.14, corner=0.28, focus=0.12, composite=0.14,
                      registration=0.2, grain=0.34, grain_size=1.72,
                      grain_stock="doc_16", halation=0.32, weave=1.12,
                      flicker=0.1, dust=0.18, vignette=0.24), strength=0.58,
                luma_bw=3.3, chroma_bw=0.68, phase_noise=1.1, bloom=0.26),
    _tv_audio(mic=None, mono=1.0, high=8000.0, carrier="reel_15ips", tracking=0.12,
              noise_db=-61.0, agc=0.3, ratio=3.8, width=0.35),
    proc_height=580, upscale="soft",
))

register_preset(_preset(
    "auth-baroque-euro-horror-1964", "Baroque Euro-Horror", "1964", "world",
    "A candlelit Eastmancolor release print with wine-red mids, cool stone shadows, velvet toe, gauze-soft zoom glass, dense halation, measured 35 mm grain, and ominous source audio narrowed by a European optical track.",
    "Wine-red candlelight and velvet print shadows", ("60s", "euro-horror", "gothic", "35mm"),
    _film(profile="eastman_60s", strength=0.9, exposure=-0.18, contrast=1.25, lift=0.012,
          knee=0.76, warmth=0.18, tint=0.08, shadow_tint="blue", shadow_amt=0.28,
          high_tint="cream", high_amt=0.16, sat=1.03, soft=0.15, diffusion=0.2,
          corner=0.22, focus=0.08, flare=0.26, grain=0.37, grain_size=1.68,
          halation=0.44, buildup=2, dmax=0.24, weave=0.62, flicker=0.09,
          dust=0.22, vignette=0.46),
    _optical_audio(low=100.0, high=6700.0, cell_noise=-49.0, flutter=0.3,
                   drive=1.75, ratio=3.5), proc_height=680, upscale="soft",
))

register_preset(_preset(
    "auth-jet-age-airline-commercial-1965", "Jet-Age Airline Commercial", "1965", "film",
    "A pristine 35 mm advertising answer print: bright terminal whites, clear cyan skies, polished Eastmancolor skin, smooth low-distortion glass, fine grain, restrained printer movement, and immaculate announcer audio on a wide mono reel master.",
    "Bright terminals and polished 35 mm color", ("60s", "airline", "commercial", "jet-age"),
    _film(profile="eastman_60s", strength=0.8, exposure=0.16, contrast=1.08, lift=0.025,
          knee=0.8, warmth=0.1, tint=-0.02, shadow_tint="blue", shadow_amt=0.08,
          high_tint="cream", high_amt=0.16, sat=1.18, vibrance=0.16,
          soft=0.045, diffusion=0.08, corner=0.05, flare=0.12, grain=0.22,
          grain_size=1.4, halation=0.24, acutance=0.42, weave=0.32,
          flicker=0.03, dust=0.06, vignette=0.08),
    _mag_audio(tape_format="reel_15ips", mic="ribbon_1938", mic_amount=0.28,
               mono=0.85, generations=0, alignment=0.05, compression=0.22,
               hiss_db=-69.0, width=0.62, ratio=3.0), proc_height=760, upscale="sharp",
))


# 86-115: missing 1970s film, broadcast, home-movie, and transfer looks.
register_preset(_preset(
    "auth-watergate-political-paranoia-1974", "Watergate-Era Political Paranoia", "1974", "film",
    "A cool, restrained 35 mm negative timed for fluorescent offices and distant street observation: cyan-gray shadows, compressed practicals, long-lens softness, fine grain, low laboratory wear, and sparse source sound on a disciplined magnetic master.",
    "Cool fluorescent 35 mm and quiet mag master", ("70s", "paranoia", "political-thriller", "35mm"),
    _film(profile="eastman_70s", strength=0.82, exposure=-0.12, contrast=1.12, lift=0.02,
          knee=0.82, warmth=-0.12, tint=-0.05, shadow_tint="teal", shadow_amt=0.24,
          high_tint="cyan", high_amt=0.08, sat=0.74, vibrance=-0.06, soft=0.07,
          diffusion=0.05, corner=0.1, focus=0.04, flare=0.12, grain=0.3,
          grain_size=1.58, halation=0.2, buildup=1, dmax=0.12, weave=0.42,
          flicker=0.04, dust=0.1, vignette=0.28),
    _mag_audio(tape_format="reel_15ips", mic="shotgun_1975", mic_amount=0.24,
               mono=0.35, generations=1, alignment=0.09, compression=0.22,
               hiss_db=-65.0, width=0.82, ratio=2.2), proc_height=720, upscale="sharp",
))

register_preset(_preset(
    "auth-poliziotteschi-crime-thriller-1975", "Poliziotteschi Crime Thriller", "1975", "world",
    "A hard Italian Eastmancolor street print with tobacco-green shadows, sun-struck stone, zoom-lens breathing, pushed 35 mm grain, modest release wear, and post-synchronized dialogue held tightly inside a driven mono optical track.",
    "Tobacco street color and driven dubbed mono", ("70s", "poliziotteschi", "italian", "crime"),
    _film(profile="eastman_70s", strength=0.92, exposure=0.03, contrast=1.27, lift=0.015,
          knee=0.72, warmth=0.12, tint=-0.08, shadow_tint="green", shadow_amt=0.22,
          high_tint="yellow", high_amt=0.14, sat=0.96, vibrance=0.08,
          soft=0.07, diffusion=0.03, corner=0.12, focus=0.22, flare=0.2,
          grain=0.47, grain_size=1.78, grain_stock="push_process", shadow_grain=0.3,
          halation=0.34, buildup=2, dmax=0.2, weave=0.8, flicker=0.08,
          dust=0.28, scratches=1, vignette=0.27),
    _optical_audio(mic="lavalier_1972", mic_amount=0.2, low=100.0, high=6900.0,
                   cell_noise=-47.0, flutter=0.36, drive=2.0, ratio=4.0,
                   distortion=1.35), proc_height=680, upscale="sharp",
))

register_preset(_preset(
    "auth-british-folk-horror-1972", "British Folk Horror", "1972", "film",
    "An earthy British color print exposed under cloud and candle: moss-green mids, russet skin, restrained dye saturation, slow zoom softness, textured 35 mm grain, gentle halation, and acoustic detail aged only by a narrow mono optical release path.",
    "Moss-green earth and restrained optical dread", ("70s", "folk-horror", "british", "35mm"),
    _film(profile="eastman_70s", strength=0.84, exposure=-0.12, contrast=1.13, lift=0.028,
          knee=0.8, warmth=0.08, tint=-0.06, shadow_tint="brown", shadow_amt=0.2,
          high_tint="cream", high_amt=0.1, sat=0.82, vibrance=-0.03,
          soft=0.1, diffusion=0.1, corner=0.15, focus=0.1, flare=0.12,
          grain=0.38, grain_size=1.67, halation=0.28, buildup=1, dmax=0.16,
          weave=0.56, flicker=0.07, dust=0.2, vignette=0.38),
    _optical_audio(mic="shotgun_1975", mic_amount=0.18, low=90.0, high=7200.0,
                   cell_noise=-51.0, flutter=0.26, drive=1.55, ratio=3.0),
    proc_height=700, upscale="soft",
))

register_preset(_preset(
    "auth-public-information-nightmare-1975", "Public Information Nightmare", "1975", "film",
    "A severe 16 mm institutional print built from blunt contrast and chalky warning color: hard practical highlights, coarse grain, accumulated dust and scratches, unsteady density, and narration forced through a heavily used classroom optical stripe.",
    "Severe 16 mm warnings and worn optical stripe", ("70s", "public-information", "16mm", "institutional"),
    _film(profile="eastman_70s", strength=0.78, exposure=-0.02, contrast=1.32, lift=0.025,
          knee=0.68, warmth=-0.02, tint=-0.06, shadow_tint="green", shadow_amt=0.18,
          high_tint="yellow", high_amt=0.12, sat=0.78, soft=0.08, diffusion=0.02,
          corner=0.2, flare=0.12, composite=0.1, grain=0.56, grain_size=2.02,
          grain_stock="doc_16", shadow_grain=0.35, halation=0.3, buildup=2,
          dmax=0.3, fade=0.18, fade_profile="neutral", weave=1.5, splice=0.9,
          flicker=0.22, dust=0.74, hairs=0.34, scratches=4, vignette=0.34),
    _optical_audio(mic="lavalier_1972", mic_amount=0.5, low=130.0, high=5400.0,
                   cell_noise=-40.0, flutter=0.65, drive=2.35, ratio=5.4,
                   distortion=1.5), proc_height=560, upscale="soft",
))

register_preset(_preset(
    "auth-soul-dance-broadcast-1973", "Soul Dance Broadcast", "1973", "broadcast",
    "A warm live color-studio master with amber skin, saturated wardrobe, expressive tube-camera highlight trails, gentle composite fringing, interlace texture, and a broad reel program channel held by period broadcast limiting.",
    "Warm tube skin, trails, broad reel sound", ("70s", "soul", "dance-show", "studio-video"),
    _broadcast(stock="tube_70s", strength=0.9, exposure=0.1, contrast=1.1, lift=0.035,
               knee=0.66, warmth=0.16, tint=0.05, shadow_tint="blue", shadow_amt=0.1,
               high_tint="cream", high_amt=0.18, sat=1.3, soft=0.08, diffusion=0.11,
               flare=0.2, auto_gain=0.18, phosphor=0.44, ntsc_strength=0.72,
               luma_bw=3.5, chroma_bw=0.78, phase_noise=2.0, rainbow=0.28,
               dot_crawl=0.3, sync_jitter=0.08, combing=0.5, twitter=0.24,
               bloom=0.38, beam_bloom=0.34, misconvergence=0.42, scan=0.06),
    _tv_audio(mic=None, mono=0.18, low=55.0, high=14500.0, carrier="reel_15ips",
              generations=1, tracking=0.1, noise_db=-64.0, agc=0.28,
              ratio=3.8, width=0.88), proc_height=580, upscale="soft",
))

register_preset(_preset(
    "auth-soft-rock-variety-special-1976", "Soft-Rock Variety Special", "1976", "broadcast",
    "A hazed network variety master with sunset warmth, cream highlights, low-contrast tube-camera diffusion, mild phosphor trails, soft composite edges, and a polished stereo reel program path with subtle channel age.",
    "Sunset tube haze and polished stereo reel", ("70s", "variety", "soft-rock", "broadcast"),
    _broadcast(stock="tube_70s", strength=0.84, exposure=0.1, contrast=1.02, lift=0.05,
               knee=0.68, warmth=0.2, tint=0.06, shadow_tint="brown", shadow_amt=0.08,
               high_tint="pink", high_amt=0.17, sat=1.06, soft=0.14, diffusion=0.22,
               flare=0.28, auto_gain=0.12, phosphor=0.34, ntsc_strength=0.62,
               luma_bw=3.7, chroma_bw=0.86, phase_noise=1.4, rainbow=0.2,
               dot_crawl=0.25, sync_jitter=0.05, combing=0.46, twitter=0.2,
               bloom=0.42, beam_bloom=0.32, misconvergence=0.28, scan=0.04),
    _tv_audio(mic=None, mono=0.05, low=45.0, high=15500.0, carrier="reel_15ips",
              generations=1, tracking=0.08, noise_db=-66.0, agc=0.2,
              ratio=3.2, width=0.94), proc_height=600, upscale="soft",
))

register_preset(_preset(
    "auth-analog-science-education-television-1974", "Analog Science-Education Television", "1974", "broadcast",
    "A softly aligned educational studio chain: neutral plumbicon color, clean practical highlights, mild color spill already present in the source carried through composite bandwidth, early U-matic texture, and calm lavalier speech on linear mono tape.",
    "Soft plumbicon color and clean U-matic mono", ("70s", "science", "education", "umatic"),
    _broadcast(stock="tube_70s", strength=0.8, exposure=0.04, contrast=1.04, lift=0.045,
               knee=0.74, warmth=0.02, tint=-0.03, shadow_tint="teal", shadow_amt=0.1,
               sat=0.94, soft=0.1, diffusion=0.06, flare=0.08, auto_gain=0.14,
               phosphor=0.16, ntsc_strength=0.68, luma_bw=3.6, chroma_bw=0.7,
               phase_noise=1.3, rainbow=0.18, dot_crawl=0.28, sync_jitter=0.08,
               tape=True, tape_noise=0.12, tape_chroma_noise=0.14,
               tape_dropouts=0.18, tape_tbe=0.1, combing=0.5, twitter=0.25,
               bloom=0.24, beam_bloom=0.14, misconvergence=0.18, scan=0.06),
    _tv_audio(mic="lavalier_1972", mic_amount=0.52, room=0.08, mono=1.0,
              low=100.0, high=8200.0, carrier="umatic_linear", tracking=0.14,
              noise_db=-55.0, agc=0.42, ratio=3.8, width=0.25),
    proc_height=560, upscale="soft",
))

register_preset(_preset(
    "auth-space-agency-mission-tape-1972", "Space-Agency Mission Tape", "1972", "broadcast",
    "A washed institutional color feed preserved on early videotape: raised setup, tired cyan, clipped console whites, narrow composite bandwidth, mild RF instability and oxide noise, while any source telemetry remains untouched and headset speech stays synchronized.",
    "Washed mission color, RF drift, headset tape", ("70s", "space-program", "mission", "videotape"),
    _broadcast(stock="tube_70s", strength=0.68, exposure=0.12, contrast=0.98, lift=0.075,
               knee=0.65, warmth=-0.08, tint=-0.04, shadow_tint="teal", shadow_amt=0.16,
               high_tint="cyan", high_amt=0.08, sat=0.72, soft=0.12, diffusion=0.04,
               flare=0.12, auto_gain=0.28, auto_lag=1.2, phosphor=0.22,
               ntsc_strength=0.78, luma_bw=3.0, chroma_bw=0.58, phase_noise=2.8,
               rainbow=0.22, dot_crawl=0.28, sync_jitter=0.2, rf_snow=0.12,
               rf_weak=0.14, rf_ghost=0.07, rf_impulse=1.1, herringbone=0.06,
               tape=True, tape_noise=0.2, tape_chroma_noise=0.22,
               tape_dropouts=0.7, tape_tbe=0.22, combing=0.56, twitter=0.28,
               bloom=0.3, beam_bloom=0.2, misconvergence=0.26, scan=0.1),
    _tv_audio(mic="broadcast_dynamic_1955", mic_amount=0.68, mono=1.0,
              low=240.0, high=4700.0, carrier="umatic_linear", tracking=0.28,
              noise_db=-49.0, agc=0.7, ratio=6.2, width=0.18),
    proc_height=520, upscale="soft",
))

register_preset(_preset(
    "auth-japanese-tokusatsu-television-1974", "Japanese Tokusatsu Television", "1974", "broadcast",
    "Bright 16 mm effects photography transferred to Japanese composite television: popping Eastman color, miniature-scale lens haze, clean optical layer registration with a visible density join, compact grain, interlace texture, and forceful mono broadcast sound.",
    "Bright 16 mm effects through composite TV", ("70s", "tokusatsu", "japanese", "television"),
    _film_to_tv(_film(profile="eastman_70s", strength=0.88, exposure=0.14, contrast=1.18,
                      lift=0.025, knee=0.68, warmth=0.1, tint=0.04,
                      shadow_tint="blue", shadow_amt=0.1, high_tint="yellow", high_amt=0.14,
                      sat=1.32, vibrance=0.2, soft=0.08, diffusion=0.09, corner=0.14,
                      flare=0.22, composite=0.22, registration=0.4, grain=0.38,
                      grain_size=1.78, grain_stock="doc_16", halation=0.32,
                      buildup=1, weave=0.82, flicker=0.08, dust=0.16, vignette=0.16),
                strength=0.7, luma_bw=3.3, chroma_bw=0.68, phase_noise=1.7,
                rainbow=0.28, dot_crawl=0.3, bloom=0.28),
    _tv_audio(mic=None, mono=1.0, low=90.0, high=8200.0, carrier="reel_75ips",
              generations=2, tracking=0.22, noise_db=-54.0, agc=0.5,
              ratio=5.0, width=0.22), proc_height=580, upscale="soft",
))

register_preset(_preset(
    "auth-hong-kong-urban-crime-film-1977", "Hong Kong Urban Crime Film", "1977", "world",
    "A pushed Eastmancolor negative timed for sodium streets and cyan shop light: hard zoom glass, wet-pavement halation, dense shadow grain, energetic but continuous gate motion, and dubbed dialogue on a bright compressed mono optical track.",
    "Sodium neon, pushed grain, bright dubbed mono", ("70s", "hong-kong", "crime", "urban"),
    _film(profile="eastman_70s", strength=0.9, exposure=-0.08, contrast=1.28, lift=0.01,
          knee=0.74, warmth=0.08, tint=-0.04, shadow_tint="teal", shadow_amt=0.28,
          high_tint="yellow", high_amt=0.2, sat=1.08, vibrance=0.14,
          soft=0.055, diffusion=0.03, corner=0.12, focus=0.18, flare=0.32,
          ghost=0.12, grain=0.5, grain_size=1.85, grain_stock="push_process",
          shadow_grain=0.44, halation=0.46, buildup=2, dmax=0.22,
          weave=0.92, flicker=0.08, dust=0.24, scratches=1, vignette=0.3),
    _optical_audio(mic="lavalier_1972", mic_amount=0.16, low=100.0, high=7000.0,
                   cell_noise=-47.0, flutter=0.38, drive=2.1, ratio=4.6,
                   distortion=1.4), proc_height=660, upscale="sharp",
))

register_preset(_preset(
    "auth-turkish-exploitation-dub-1976", "Turkish Exploitation Dub", "1976", "world",
    "A repeatedly printed Eastmancolor element with cyan loss, pink highlights, coarse duplicate grain, soft optical composites, restless density, dust and scratches; the supplied audio remains in sync while taking on the narrow grit of a multi-generation mono dub.",
    "Faded dupe grain and narrow multi-gen mono", ("70s", "turkish", "exploitation", "dub"),
    _film(profile="eastman_70s", strength=0.74, exposure=0.08, contrast=1.26, lift=0.055,
          knee=0.68, warmth=0.18, tint=0.12, shadow_tint="green", shadow_amt=0.2,
          high_tint="pink", high_amt=0.24, sat=0.78, soft=0.15, diffusion=0.08,
          corner=0.24, focus=0.15, flare=0.2, composite=0.34, registration=0.78,
          grain=0.6, grain_size=2.1, grain_stock="print_dupe", grain_layers="print_from_neg",
          shadow_grain=0.38, mottle=0.26, halation=0.36, buildup=3, dmax=0.4,
          fade=0.4, fade_profile="eastman_pink", weave=1.7, splice=1.1,
          flicker=0.28, color_flicker=0.2, dust=0.82, hairs=0.42,
          scratches=5, vignette=0.38),
    _mag_audio(tape_format="reel_375ips", mic=None, mono=1.0, generations=4,
               alignment=0.52, compression=0.58, hiss_db=-45.0, width=0.16,
               ratio=5.2, distortion=1.8), proc_height=540, upscale="soft",
))

register_preset(_preset(
    "auth-mexican-lucha-cinema-1973", "Mexican Lucha Cinema", "1973", "world",
    "A vivid Mexican Eastmancolor release print with warm arena skin, cyan-painted shadows, bright costume dyes, theatrical lens softness, sturdy 35 mm grain, modest projection wear, and broad dubbed dialogue on optical mono.",
    "Vivid arena dye and broad dubbed optical mono", ("70s", "mexican", "lucha", "35mm"),
    _film(profile="eastman_70s", strength=0.9, exposure=0.08, contrast=1.18, lift=0.025,
          knee=0.74, warmth=0.2, tint=0.04, shadow_tint="teal", shadow_amt=0.16,
          high_tint="yellow", high_amt=0.16, sat=1.3, vibrance=0.2,
          soft=0.1, diffusion=0.08, corner=0.12, focus=0.08, flare=0.22,
          grain=0.4, grain_size=1.7, halation=0.36, buildup=2, dmax=0.18,
          weave=0.72, flicker=0.08, dust=0.3, scratches=1, vignette=0.24),
    _optical_audio(mic="lavalier_1972", mic_amount=0.16, low=90.0, high=7000.0,
                   cell_noise=-47.0, flutter=0.34, drive=1.85, ratio=4.2),
    proc_height=680, upscale="soft",
))

register_preset(_preset(
    "auth-australian-ozploitation-1978", "Australian Ozploitation", "1978", "world",
    "An unforgiving Australian color negative exposed in hard midday sun: ochre roads, pale cyan sky, clipped highlights, rough wide-angle glass, pushed grain and raw location audio carried through a muscular magnetic-to-optical release chain.",
    "Ochre road glare and muscular location sound", ("70s", "australian", "ozploitation", "location"),
    _film(profile="eastman_70s", strength=0.9, exposure=0.18, contrast=1.22, lift=0.012,
          knee=0.68, warmth=0.16, tint=-0.06, shadow_tint="brown", shadow_amt=0.2,
          high_tint="cyan", high_amt=0.12, sat=0.9, vibrance=0.08,
          soft=0.035, diffusion=0.02, corner=0.15, distortion=-0.03,
          focus=0.1, flare=0.24, grain=0.16, grain_size=1.22,
          grain_stock="push_process", shadow_grain=0.06, mottle=0.025, halation=0.32,
          buildup=1, dmax=0.12, weave=0.65, flicker=0.05, dust=0.08,
          scratches=1, vignette=0.22),
    _mag_audio(tape_format="reel_75ips", mic="shotgun_1975", mic_amount=0.62,
               room=0.04, mono=0.72, generations=2, alignment=0.24,
               compression=0.4, hiss_db=-53.0, width=0.58, ratio=4.4,
               distortion=1.35), proc_height=720, upscale="sharp",
))

register_preset(_preset(
    "auth-canadian-tax-shelter-horror-1978", "Canadian Tax-Shelter Horror", "1978", "film",
    "A cold late-1970s answer print built from underexposed interiors and winter daylight: blue-green shadow contamination, low-saturation skin, soft laboratory contrast, coarse pushed grain, dim halation, and a quiet magnetic program master.",
    "Cold underexposure, coarse blue-green grain", ("70s", "canadian", "horror", "answer-print"),
    _film(profile="eastman_70s", strength=0.86, exposure=-0.34, contrast=1.1, lift=0.025,
          knee=0.84, warmth=-0.18, tint=-0.08, shadow_tint="blue", shadow_amt=0.34,
          high_tint="cyan", high_amt=0.08, sat=0.7, vibrance=-0.08,
          soft=0.12, diffusion=0.1, corner=0.22, focus=0.09, flare=0.12,
          grain=0.52, grain_size=1.9, grain_stock="push_process", shadow_grain=0.5,
          halation=0.2, buildup=1, dmax=0.2, weave=0.55, flicker=0.06,
          dust=0.14, vignette=0.46),
    _mag_audio(tape_format="reel_15ips", mic=None, mono=0.45, generations=1,
               alignment=0.13, compression=0.26, hiss_db=-62.0, width=0.76,
               ratio=2.4), proc_height=680, upscale="soft",
))

register_preset(_preset(
    "auth-southern-gothic-tv-movie-1976", "Southern Gothic Television Movie", "1976", "broadcast",
    "A tobacco-brown 16 mm television feature transferred without cadence alteration: humid diffusion, cream highlight bloom, softened network color, fine field grain, composite edges, and a compressed mono reel master with gentle room decay.",
    "Tobacco 16 mm, humid bloom, network mono", ("70s", "southern-gothic", "tv-movie", "16mm"),
    _film_to_tv(_film(profile="eastman_70s", strength=0.84, exposure=-0.06,
                      contrast=1.04, lift=0.055, knee=0.76, warmth=0.22, tint=0.04,
                      shadow_tint="brown", shadow_amt=0.26, high_tint="cream", high_amt=0.18,
                      sat=0.82, soft=0.16, diffusion=0.22, corner=0.16, focus=0.08,
                      flare=0.2, grain=0.36, grain_size=1.7, grain_stock="doc_16",
                      halation=0.32, weave=0.6, flicker=0.06, dust=0.12,
                      vignette=0.32), strength=0.62, luma_bw=3.5, chroma_bw=0.72,
                phase_noise=1.2, rainbow=0.16, dot_crawl=0.22, bloom=0.28),
    _tv_audio(mic=None, room=0.1, mono=1.0, low=90.0, high=7600.0,
              carrier="reel_75ips", generations=2, tracking=0.18,
              noise_db=-56.0, agc=0.42, ratio=4.2, width=0.26),
    proc_height=600, upscale="soft",
))

register_preset(_preset(
    "auth-movie-of-the-week-melodrama-1975", "Movie-of-the-Week Melodrama", "1975", "broadcast",
    "A practical network movie master with flat but stable Eastmancolor, economical 16 mm texture, ordinary zoom-era softness, restrained composite color, interlace detail, and earnest source audio kept inside a dense mono broadcast reel chain.",
    "Flat network color and dense mono reel master", ("70s", "movie-of-the-week", "melodrama", "network"),
    _film_to_tv(_film(profile="eastman_70s", strength=0.74, contrast=1.02, lift=0.045,
                      knee=0.8, warmth=0.06, tint=-0.02, shadow_tint="green", shadow_amt=0.08,
                      high_tint="cream", high_amt=0.08, sat=0.9, soft=0.1,
                      diffusion=0.07, corner=0.12, focus=0.08, flare=0.09,
                      grain=0.32, grain_size=1.66, grain_stock="doc_16",
                      halation=0.22, weave=0.48, flicker=0.05, dust=0.1,
                      vignette=0.18), strength=0.66, luma_bw=3.6, chroma_bw=0.72,
                phase_noise=1.35, rainbow=0.2, dot_crawl=0.26, bloom=0.23),
    _tv_audio(mic=None, mono=1.0, low=90.0, high=7800.0,
              carrier="reel_75ips", generations=2, tracking=0.16,
              noise_db=-56.0, agc=0.46, ratio=4.5, width=0.24),
    proc_height=600, upscale="soft",
))

register_preset(_preset(
    "auth-eyewitness-local-news-1975", "Eyewitness Local News", "1975", "broadcast",
    "A hard-lit local-news chain joining coarse 16 mm field photography to a tube-camera studio and analog tape master: hot faces, urgent contrast, soft chroma, composite crawl, mild oxide noise, and compressed reporter mono.",
    "Hard-lit 16 mm news through analog tape", ("70s", "local-news", "eyewitness", "16mm"),
    _film_to_tv(_film(profile="eastman_70s", strength=0.82, exposure=0.12,
                      contrast=1.24, lift=0.02, knee=0.64, warmth=0.1, tint=-0.04,
                      shadow_tint="brown", shadow_amt=0.12, high_tint="yellow", high_amt=0.1,
                      sat=0.92, soft=0.05, diffusion=0.02, corner=0.14, focus=0.1,
                      auto_gain=0.22, grain=0.47, grain_size=1.9,
                      grain_stock="doc_16", shadow_grain=0.28, halation=0.32,
                      weave=1.0, flicker=0.1, dust=0.28, scratches=1,
                      vignette=0.2), strength=0.74, luma_bw=3.2, chroma_bw=0.64,
                phase_noise=2.0, rainbow=0.26, dot_crawl=0.34, bloom=0.25),
    _tv_audio(mic="lavalier_1972", mic_amount=0.58, mono=1.0, low=110.0,
              high=6800.0, carrier="umatic_linear", tracking=0.24,
              noise_db=-51.0, agc=0.66, ratio=5.4, width=0.2),
    proc_height=540, upscale="soft",
))

register_preset(_preset(
    "auth-super-8-family-vacation-1974", "Super 8 Family Vacation", "1974", "film",
    "A warm reversal home-movie element with breathing autoexposure, corner-soft consumer glass, drifting focus, thick Super 8 grain, gentle gate wander, dye flicker and small scratches; any supplied sound remains present on a narrow magnetic-style carrier.",
    "Warm reversal, breathing iris, Super 8 grain", ("70s", "super8", "home-movie", "reversal"),
    _film(profile="ektachrome", strength=0.84, exposure=0.12, contrast=1.1, lift=0.04,
          knee=0.72, warmth=0.28, tint=0.03, shadow_tint="brown", shadow_amt=0.16,
          high_tint="cream", high_amt=0.16, sat=1.08, soft=0.12, diffusion=0.06,
          corner=0.3, focus=0.2, flare=0.18, auto_gain=0.3, auto_lag=1.1,
          grain=0.23, grain_size=1.4, grain_stock="super8", grain_layers="reversal",
          shadow_grain=0.08, mottle=0.04, halation=0.3, weave=0.85,
          splice=0.2, flicker=0.1, color_flicker=0.05, dust=0.08,
          scratches=0, leak=0.03, leak_constant=0.0, vignette=0.3),
    _mag_audio(tape_format="reel_375ips", mic="crystal_1940", mic_amount=0.34,
               mono=1.0, generations=2, alignment=0.32, compression=0.38,
               hiss_db=-51.0, width=0.18, ratio=3.6), proc_height=680, upscale="soft",
))

register_preset(_preset(
    "auth-16mm-skate-film-1978", "16mm Skate Film", "1978", "film",
    "A close-running reversal camera with genuine fisheye barrel bow, hard daylight exposure, coarse 16 mm grain, restless gate position and scratched work-print texture; the supplied soundtrack is preserved through a raw mono portable-reel chain.",
    "Fisheye reversal, coarse grain, raw reel mono", ("70s", "skate", "16mm", "fisheye"),
    _film(profile="ektachrome", strength=0.82, exposure=0.16, contrast=1.26, lift=0.015,
          knee=0.66, warmth=0.1, tint=-0.02, shadow_tint="blue", shadow_amt=0.12,
          high_tint="yellow", high_amt=0.12, sat=1.04, soft=0.045,
          diffusion=0.02, corner=0.28, focus=0.14, distortion=-0.2,
          flare=0.22, auto_gain=0.28, grain=0.58, grain_size=2.0,
          grain_stock="doc_16", grain_layers="reversal", shadow_grain=0.34,
          halation=0.34, buildup=1, weave=1.45, splice=0.6, flicker=0.14,
          dust=0.5, scratches=3, vignette=0.35),
    _mag_audio(tape_format="reel_375ips", mic="shotgun_1975", mic_amount=0.5,
               mono=1.0, generations=2, alignment=0.38, compression=0.46,
               hiss_db=-49.0, width=0.2, ratio=5.0, distortion=1.45),
    proc_height=560, upscale="soft",
))

register_preset(_preset(
    "auth-fashion-editorial-film-1977", "Fashion Editorial Film", "1977", "film",
    "A refined 35 mm fashion negative timed for warm skin and cool mirrored shadows: silk diffusion, gentle zoom-focus breathing, creamy halation, fine grain, pristine printer movement, and a lush but entirely source-derived stereo reel master.",
    "Silk-soft 35 mm and creamy highlights", ("70s", "fashion", "editorial", "35mm"),
    _film(profile="eastman_70s", strength=0.82, exposure=0.12, contrast=1.06, lift=0.04,
          knee=0.78, warmth=0.2, tint=0.04, shadow_tint="blue", shadow_amt=0.12,
          high_tint="cream", high_amt=0.22, sat=1.04, vibrance=0.1,
          soft=0.16, diffusion=0.26, corner=0.1, focus=0.12, flare=0.24,
          ghost=0.16, grain=0.26, grain_size=1.45, halation=0.4,
          buildup=1, dmax=0.08, acutance=0.26, weave=0.36, flicker=0.035,
          dust=0.06, vignette=0.16),
    _mag_audio(tape_format="reel_15ips", mic=None, mono=0.0, generations=1,
               alignment=0.07, compression=0.28, hiss_db=-67.0, width=0.96,
               ratio=2.8), proc_height=740, upscale="sharp",
))

register_preset(_preset(
    "auth-roller-disco-promotional-reel-1979", "Roller-Disco Promotional Reel", "1979", "film",
    "A glossy late-1970s 16 mm promotional element with dense magenta-blue dye, glitter-soft diffusion, highlight star ghosts, smooth fine grain, mild optical layering and a wide, saturated reel program path that never replaces the supplied music.",
    "Magenta glitter haze and wide reel saturation", ("70s", "roller-disco", "promotional", "16mm"),
    _film(profile="eastman_70s", strength=0.9, exposure=0.08, contrast=1.16, lift=0.025,
          knee=0.66, warmth=0.08, tint=0.12, shadow_tint="blue", shadow_amt=0.24,
          high_tint="pink", high_amt=0.28, sat=1.42, vibrance=0.24,
          soft=0.08, diffusion=0.22, corner=0.12, flare=0.34, ghost=0.34,
          composite=0.12, registration=0.16, grain=0.34, grain_size=1.72,
          grain_stock="doc_16", halation=0.45, weave=0.56, flicker=0.08,
          color_flicker=0.08, dust=0.14, vignette=0.2),
    _mag_audio(tape_format="reel_15ips", mic=None, mono=0.0, generations=1,
               alignment=0.1, compression=0.42, hiss_db=-63.0, width=1.02,
               ratio=4.0), proc_height=620, upscale="soft",
))

register_preset(_preset(
    "auth-saturday-morning-live-action-serial-1976", "Saturday-Morning Live-Action Serial", "1976", "broadcast",
    "A bright economical 16 mm adventure print transferred to network composite: primary wardrobe color, broad highlight rolloff, visible effects-layer registration, compact grain, light circulation wear, interlace softness, and cheerful source sound on punchy mono tape.",
    "Bright 16 mm adventure through network tape", ("70s", "saturday-morning", "serial", "16mm"),
    _film_to_tv(_film(profile="eastman_70s", strength=0.84, exposure=0.14,
                      contrast=1.14, lift=0.035, knee=0.68, warmth=0.14, tint=0.04,
                      shadow_tint="blue", shadow_amt=0.08, high_tint="yellow", high_amt=0.14,
                      sat=1.22, vibrance=0.16, soft=0.08, diffusion=0.05,
                      corner=0.14, flare=0.17, composite=0.24, registration=0.46,
                      grain=0.38, grain_size=1.78, grain_stock="doc_16",
                      halation=0.3, buildup=1, weave=0.72, flicker=0.08,
                      dust=0.26, scratches=1, vignette=0.16), strength=0.68,
                luma_bw=3.4, chroma_bw=0.7, phase_noise=1.6,
                rainbow=0.26, dot_crawl=0.3, bloom=0.24),
    _tv_audio(mic=None, mono=1.0, low=90.0, high=8000.0,
              carrier="reel_75ips", generations=2, tracking=0.2,
              noise_db=-55.0, agc=0.5, ratio=5.0, width=0.22),
    proc_height=580, upscale="soft",
))

register_preset(_preset(
    "auth-syndicated-limited-animation-1973", "Syndicated Limited-Animation Print", "1973", "cartoon",
    "A source-preserving cel-and-carrier treatment with flat cheerful paint, clean black outlines, rostrum registration jitter, soft 16 mm grain, light print wear, composite chroma bleed and a boxy mono television master; it does not invent drawing holds, repeated cycles, captions or music.",
    "Flat cel paint through a worn mono TV master", ("70s", "limited-animation", "cel", "syndication"),
    [
        ("cel_flatten", {"levels": 14, "flatness": 0.48, "sat_snap": 0.24}),
        ("color_era", {"profile": "limited_1970s", "strength": 0.88}),
        ("cel_wobble", {"amount": 0.9, "rot": 0.05, "layers": 2}),
        ("cel_dirt", {"density": 0.42, "visibility": 0.075, "glass_shadows": 0.12}),
        ("ink_line", {"weight": 0.38, "xerox_grit": 0.22}),
        ("grain", {"amount": 0.34, "size": 2.05, "chroma_grain": 0.11,
                    "stock": "doc_16", "layers": "print_from_neg", "mottle": 0.08}),
        ("gate_weave", {"amount": 0.9, "rotation": 0.025}),
        ("flicker", {"amount": 0.09, "color_flicker": 0.04, "spatial": 0.08}),
        ("dust", {"density": 0.34, "size": 0.9, "hairs": 0.12}),
        ("ntsc", {"strength": 0.72, "luma_bw": 3.2, "chroma_bw": 0.62,
                  "phase_noise": 1.9, "rainbow": 0.3, "dot_crawl": 0.34}),
        ("interlace", {"combing": 0.42, "twitter": 0.2}),
        ("crt", {"bloom": 0.27, "scan_strength": 0.08}),
    ],
    _tv_audio(mic=None, mono=1.0, low=110.0, high=6800.0,
              carrier="umatic_linear", tracking=0.24, noise_db=-51.0,
              agc=0.56, ratio=5.2, width=0.18),
    proc_height=560, upscale="soft",
))

register_preset(_preset(
    "auth-educational-interstitial-animation-1975", "Educational Interstitial Animation", "1975", "cartoon",
    "A flat graphic source photographed onto clean 16 mm and copied to an educational broadcast master: bright primaries, slight rostrum registration, restrained cel-film grain, composite tape softness, and mnemonic source audio pressed through clear mono television limiting.",
    "Bright rostrum color through soft tape", ("70s", "educational", "animation", "interstitial"),
    _film_to_tv(_film(profile="eastman_70s", strength=0.8, contrast=1.12, lift=0.025,
                      knee=0.76, warmth=0.08, tint=0.04, high_tint="yellow", high_amt=0.1,
                      sat=1.34, vibrance=0.22, soft=0.035, diffusion=0.025,
                      corner=0.04, composite=0.18, registration=0.48, grain=0.3,
                      grain_size=1.68, grain_stock="doc_16", halation=0.2,
                      acutance=0.38, weave=0.64, flicker=0.06, dust=0.12,
                      vignette=0.08), strength=0.72, luma_bw=3.25,
                chroma_bw=0.66, phase_noise=1.7, rainbow=0.28,
                dot_crawl=0.34, bloom=0.25),
    _tv_audio(mic=None, mono=1.0, low=100.0, high=7600.0,
              carrier="umatic_linear", tracking=0.2, noise_db=-53.0,
              agc=0.6, ratio=6.0, width=0.2), proc_height=560, upscale="sharp",
))

register_preset(_preset(
    "auth-prog-rock-concert-film-1974", "Prog-Rock Concert Film", "1974", "film",
    "A stage-lit 16 mm concert negative held deep in the blacks: cyan and magenta gels, hot practical halation, long-lens softness, pushed shadow grain, stable continuous gate motion, and a wide analog reel program chain allowed to saturate without adding music.",
    "Deep stage black, colored halation, wide reel", ("70s", "concert", "prog-rock", "16mm"),
    _film(profile="ektachrome", strength=0.82, exposure=-0.14, contrast=1.17, lift=0.014,
          knee=0.74, warmth=-0.04, tint=0.1, shadow_tint="blue", shadow_amt=0.32,
          high_tint="pink", high_amt=0.28, sat=1.22, vibrance=0.18,
          soft=0.09, diffusion=0.1, corner=0.2, focus=0.16, flare=0.34,
          ghost=0.16, grain=0.22, grain_size=1.35, grain_stock="push_process",
          grain_layers="reversal", shadow_grain=0.12, mottle=0.035, halation=0.4,
          buildup=1, dmax=0.12, weave=0.65, flicker=0.07, dust=0.08,
          vignette=0.32),
    _mag_audio(tape_format="reel_15ips", mic=None, mono=0.0, generations=2,
               alignment=0.16, compression=0.54, hiss_db=-59.0, width=1.0,
               ratio=4.5, distortion=1.45), proc_height=680, upscale="soft",
))

register_preset(_preset(
    "auth-punk-club-super-8-1978", "Punk-Club Super 8", "1978", "film",
    "A Super 8 camera pushed against bare club lamps: clipped whites, murky red-cyan dye, coarse dancing grain, corner-soft focus, strong gate chatter and emulsion scratches, with the original live sound crushed through an overloaded mono cassette-like field chain.",
    "Clipped club lamps, coarse Super 8, hot mono", ("70s", "punk", "super8", "club"),
    _film(profile="ektachrome", strength=0.76, exposure=0.18, contrast=1.24, lift=0.005,
          knee=0.64, warmth=0.1, tint=0.1, shadow_tint="blue", shadow_amt=0.26,
          high_tint="pink", high_amt=0.26, sat=0.98, soft=0.17, diffusion=0.04,
          corner=0.34, focus=0.24, flare=0.32, auto_gain=0.42, auto_lag=0.5,
          grain=0.3, grain_size=1.5, grain_stock="super8", grain_layers="reversal",
          shadow_grain=0.16, mottle=0.06, halation=0.42, buildup=1,
          weave=1.25, splice=0.4, flicker=0.14, dust=0.2, scratches=2,
          scratch_strength=0.42, leak=0.06, leak_constant=0.01, vignette=0.36),
    _mag_audio(tape_format="cassette", mic="electret_1985", mic_amount=0.72,
               room=0.12, mono=1.0, generations=3, alignment=0.48,
               compression=0.66, hiss_db=-43.0, width=0.14, ratio=7.0,
               distortion=2.2), proc_height=620, upscale="soft",
))
