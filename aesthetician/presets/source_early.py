"""Source-preserving acquisition and carrier looks from the 1890s-1950s.

These presets reproduce lens, emulsion, print, television, microphone, and
sound-carrier signatures.  They do not retime or replace frames, crop the
picture, add editorial graphics, mute the program, or synthesize a score.
"""

from __future__ import annotations

from typing import Any

from ..engine.presets import ChainSpec, Preset, Variant, register_preset


def _variants(video: ChainSpec, audio: ChainSpec) -> list[Variant]:
    """Conservative preservation and circulation states of the same source."""
    v = {eid: params for eid, params in video}
    a = {eid: params for eid, params in audio}
    preserve_v: dict[str, Any] = {}
    circulate_v: dict[str, Any] = {}
    preserve_a: dict[str, Any] = {}
    circulate_a: dict[str, Any] = {}

    if "grain" in v:
        amount = float(v["grain"].get("amount", 0.35))
        preserve_v["grain.amount"] = max(0.14, amount * 0.72)
        circulate_v["grain.amount"] = min(0.65, amount * 1.16)
    if "flicker" in v:
        amount = float(v["flicker"].get("amount", 0.12))
        preserve_v["flicker.amount"] = max(0.025, amount * 0.55)
        circulate_v["flicker.amount"] = min(0.6, amount * 1.28)
    if "gate_weave" in v:
        amount = float(v["gate_weave"].get("amount", 0.7))
        preserve_v["gate_weave.amount"] = max(0.18, amount * 0.55)
        circulate_v["gate_weave.amount"] = min(8.0, amount * 1.35)
    if "dust" in v:
        density = float(v["dust"].get("density", 0.2))
        preserve_v["dust.density"] = max(0.025, density * 0.4)
        circulate_v["dust.density"] = min(1.0, density * 1.55)
    if "scratches" in v:
        count = int(v["scratches"].get("count", 1))
        preserve_v["scratches.count"] = max(0, count - 1)
        circulate_v["scratches.count"] = min(8, count + 1)
    if "print_char" in v:
        generations = int(v["print_char"].get("contrast_buildup", 1))
        preserve_v["print_char.contrast_buildup"] = max(0, generations - 1)
        circulate_v["print_char.contrast_buildup"] = min(4, generations + 1)
    if "optical_composite" in v:
        reg = float(v["optical_composite"].get("registration", 0.0))
        preserve_v["optical_composite.registration"] = reg * 0.45
        circulate_v["optical_composite.registration"] = min(3.0, reg * 1.45 + 0.04)
    if "fade" in v:
        fade = float(v["fade"].get("amount", 0.0))
        preserve_v["fade.amount"] = fade * 0.35
        circulate_v["fade.amount"] = min(1.0, fade * 1.6 + 0.03)

    if "a_optical_track" in a:
        floor = float(a["a_optical_track"].get("cell_noise", -50.0))
        flutter = float(a["a_optical_track"].get("flutter", 0.3))
        preserve_a["a_optical_track.cell_noise"] = max(-75.0, floor - 7.0)
        preserve_a["a_optical_track.flutter"] = max(0.03, flutter * 0.5)
        circulate_a["a_optical_track.cell_noise"] = min(-28.0, floor + 5.0)
        circulate_a["a_optical_track.flutter"] = min(1.0, flutter * 1.35)
    if "a_disc_medium" in a:
        wear = float(a["a_disc_medium"].get("wear", 0.3))
        preserve_a["a_disc_medium.wear"] = max(0.02, wear * 0.45)
        circulate_a["a_disc_medium.wear"] = min(1.0, wear * 1.45)
    if "a_analog_dub" in a:
        generations = int(a["a_analog_dub"].get("generations", 1))
        preserve_a["a_analog_dub.generations"] = max(0, generations - 1)
        circulate_a["a_analog_dub.generations"] = min(8, generations + 1)
        preserve_a["a_analog_dub.alignment"] = 0.03
        circulate_a["a_analog_dub.alignment"] = min(
            1.0, float(a["a_analog_dub"].get("alignment", 0.1)) + 0.16
        )
    if "a_tv_sound" in a:
        buzz = float(a["a_tv_sound"].get("buzz_db", -58.0))
        preserve_a["a_tv_sound.buzz_db"] = max(-80.0, buzz - 7.0)
        circulate_a["a_tv_sound.buzz_db"] = min(-30.0, buzz + 5.0)

    return [
        Variant(
            "preservation-element",
            "Preservation Element",
            "A carefully held source element with steadier registration, cleaner surfaces, and the same period response.",
            video=preserve_v,
            audio=preserve_a,
        ),
        Variant(
            "circulation-copy",
            "Circulation Copy",
            "A routine contemporary copy with another print or carrier generation, never a different edit.",
            video=circulate_v,
            audio=circulate_a,
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
        family=family,
        era=era,
        desc=desc,
        tagline=tagline,
        tags=(*tags, "source-preserving"),
        proc_height=proc_height,
        upscale=upscale,
        video=video,
        audio=audio,
        variants=_variants(video, audio),
    )


def _mono_print(
    *,
    response: str = "panchromatic",
    tint: str = "silver",
    tint_amt: float = 0.18,
    mono_amount: float = 1.0,
    exposure: float = 0.0,
    contrast: float = 1.2,
    gamma: float = 1.0,
    lift: float = 0.035,
    knee: float = 0.78,
    soft: float = 0.12,
    diffusion: float = 0.06,
    corner: float = 0.16,
    flare: float = 0.05,
    grain: float = 0.4,
    grain_size: float = 1.75,
    grain_stock: str = "fine_35",
    mottle: float = 0.08,
    shadow_boost: float = 0.08,
    halation: float = 0.2,
    print_generations: int = 1,
    acutance: float = 0.16,
    dmax: float = 0.12,
    flicker: float = 0.1,
    flicker_character: str = "projector",
    weave: float = 0.7,
    dust: float = 0.18,
    scratch_count: int = 1,
    scratch_rate: float = 0.35,
) -> ChainSpec:
    return [
        ("mono", {"amount": mono_amount, "response": response, "tint": tint,
                  "tint_amt": tint_amt}),
        ("tone", {"exposure": exposure, "contrast": contrast, "gamma": gamma,
                  "lift": lift, "knee": knee}),
        ("optics", {"soft_focus": soft, "diffusion": diffusion,
                    "corner_softness": corner, "veiling_flare": flare}),
        ("grain", {"amount": grain, "size": grain_size, "size_ref": "output",
                   "roughness": 0.52, "chroma_grain": 0.0, "stock": grain_stock,
                   "layers": "mono", "shadow_boost": shadow_boost, "mottle": mottle}),
        ("halation", {"strength": halation, "threshold": 0.72, "radius": 0.042,
                      "tint": "neutral"}),
        ("print_char", {"acutance": acutance, "dmax_breath": dmax,
                        "contrast_buildup": print_generations}),
        ("flicker", {"amount": flicker, "character": flicker_character,
                     "color_flicker": 0.0, "spatial": 0.14}),
        ("gate_weave", {"amount": weave, "hz": 0.62, "rotation": 0.025,
                        "splice_bump": 0.0}),
        ("dust", {"density": dust, "size": 0.85, "polarity": "print", "hairs": 0.1}),
        ("scratches", {"strength": 0.28, "count": scratch_count, "wander": 0.3,
                       "transient_rate": scratch_rate, "emulsion_side": 0.0,
                       "gouge_rate": 0.0}),
    ]


def _color_print(
    *,
    profile: str = "eastman_60s",
    stock_strength: float = 0.72,
    exposure: float = 0.0,
    contrast: float = 1.1,
    lift: float = 0.025,
    knee: float = 0.82,
    warmth: float = 0.08,
    tint: float = 0.0,
    shadow_tint: str = "none",
    shadow_amt: float = 0.0,
    high_tint: str = "cream",
    high_amt: float = 0.08,
    saturation: float = 1.05,
    vibrance: float = 0.08,
    soft: float = 0.08,
    diffusion: float = 0.06,
    corner: float = 0.1,
    flare: float = 0.07,
    optical_softness: float = 0.04,
    registration: float = 0.06,
    layer_haze: float = 0.03,
    density_breath: float = 0.06,
    grain: float = 0.32,
    grain_size: float = 1.65,
    chroma_grain: float = 0.12,
    grain_stock: str = "fine_35",
    layers: str = "print_from_neg",
    mottle: float = 0.06,
    halation: float = 0.24,
    print_generations: int = 1,
    fade: float = 0.04,
    fade_profile: str = "neutral",
    flicker: float = 0.07,
    weave: float = 0.55,
    dust: float = 0.13,
    scratch_count: int = 0,
) -> ChainSpec:
    return [
        ("stock", {"profile": profile, "strength": stock_strength}),
        ("tone", {"exposure": exposure, "contrast": contrast, "lift": lift,
                  "knee": knee}),
        ("balance", {"warmth": warmth, "tint": tint, "shadow_tint": shadow_tint,
                     "shadow_amt": shadow_amt, "high_tint": high_tint,
                     "high_amt": high_amt}),
        ("saturation", {"amount": saturation, "vibrance": vibrance}),
        ("optics", {"soft_focus": soft, "diffusion": diffusion,
                    "corner_softness": corner, "veiling_flare": flare}),
        ("optical_composite", {"softness": optical_softness, "matte_line": 0.0,
                               "registration": registration, "layer_haze": layer_haze,
                               "density_breath": density_breath}),
        ("grain", {"amount": grain, "size": grain_size, "size_ref": "output",
                   "roughness": 0.46, "chroma_grain": chroma_grain,
                   "stock": grain_stock, "layers": layers, "mottle": mottle}),
        ("halation", {"strength": halation, "threshold": 0.73, "radius": 0.045,
                      "tint": "red_orange"}),
        ("print_char", {"acutance": 0.2, "dmax_breath": 0.08,
                        "contrast_buildup": print_generations}),
        ("fade", {"amount": fade, "profile": fade_profile, "bloom_whites": 0.06}),
        ("flicker", {"amount": flicker, "character": "projector",
                     "color_flicker": 0.05, "spatial": 0.08}),
        ("gate_weave", {"amount": weave, "hz": 0.58, "rotation": 0.018,
                        "splice_bump": 0.0}),
        ("dust", {"density": dust, "size": 0.8, "polarity": "print", "hairs": 0.07}),
        ("scratches", {"strength": 0.2, "count": scratch_count, "wander": 0.22,
                       "transient_rate": 0.18, "emulsion_side": 0.0,
                       "gouge_rate": 0.0}),
    ]


def _kinescope(*, contrast: float = 1.16, lift: float = 0.04,
               bloom: float = 0.24, grain: float = 0.38,
               flicker: float = 0.1, weave: float = 0.65) -> ChainSpec:
    return [
        ("mono", {"response": "panchromatic", "tint": "silver", "tint_amt": 0.12}),
        ("tone", {"contrast": contrast, "lift": lift, "knee": 0.76}),
        ("ntsc", {"system": "ntsc", "luma_bw": 3.3, "chroma_bw": 0.5,
                  "comb": 0.2, "rainbow": 0.0, "dot_crawl": 0.05,
                  "phase_noise": 0.5, "strength": 0.55}),
        ("interlace", {"field_order": "tff", "combing": 0.28, "twitter": 0.12}),
        ("crt", {"scan_strength": 0.13, "phosphor_mask": "none", "bloom": bloom,
                 "bloom_radius": 12.0, "glass_glow": 0.06, "curvature": 0.0,
                 "misconvergence": 0.0, "vignette_crt": 0.0}),
        ("optics", {"soft_focus": 0.2, "diffusion": 0.08, "corner_softness": 0.12}),
        ("grain", {"amount": grain, "size": 1.7, "size_ref": "output",
                   "roughness": 0.5, "chroma_grain": 0.0,
                   "stock": "fine_35", "layers": "mono"}),
        ("halation", {"strength": 0.18, "threshold": 0.68, "radius": 0.038,
                      "tint": "neutral"}),
        ("print_char", {"acutance": 0.12, "dmax_breath": 0.14,
                        "contrast_buildup": 1}),
        ("flicker", {"amount": flicker, "character": "projector", "spatial": 0.1}),
        ("gate_weave", {"amount": weave, "hz": 0.6, "rotation": 0.018,
                        "splice_bump": 0.0}),
        ("dust", {"density": 0.14, "size": 0.8, "polarity": "print", "hairs": 0.05}),
    ]


def _silent_program_audio(*, high_hz: float = 10500.0,
                          mono: float = 0.86, room_mix: float = 0.08) -> ChainSpec:
    return [
        ("a_bandlimit", {"low_hz": 55.0, "high_hz": high_hz, "order": 3}),
        ("a_mono", {"amount": mono}),
        ("a_room", {"mode": "chamber", "size": 1.25, "decay_s": 0.72,
                    "damp": 0.72, "predelay_ms": 12.0, "mix": room_mix}),
    ]


def _optical_audio(
    *,
    mic: str = "ribbon_1938",
    mic_amount: float = 0.58,
    proximity: float = 0.08,
    overload: float = 0.16,
    self_noise: float = -62.0,
    low_hz: float = 100.0,
    high_hz: float = 6200.0,
    rolloff: str = "feature_1940s",
    cell_noise: float = -50.0,
    flutter: float = 0.35,
    drive: float = 1.45,
    ratio: float = 3.2,
    room_mix: float = 0.0,
) -> ChainSpec:
    chain: ChainSpec = [
        ("a_historical_mic", {"profile": mic, "amount": mic_amount,
                              "proximity": proximity, "overload": overload,
                              "self_noise_db": self_noise, "handling": 0.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_optical_track", {"low_hz": low_hz, "high_hz": high_hz,
                             "academy_rolloff": rolloff, "cell_noise": cell_noise,
                             "flutter": flutter, "drive": drive}),
        ("a_compressor", {"threshold_db": -21.0, "ratio": ratio,
                          "attack_ms": 7.0, "release_ms": 220.0, "knee_db": 5.0}),
    ]
    if room_mix > 0.0:
        chain.append(("a_room", {"mode": "chamber", "size": 0.9, "decay_s": 0.65,
                                 "damp": 0.74, "predelay_ms": 5.0, "mix": room_mix}))
    return chain


def _disc_audio(*, mic: str = "ribbon_1938", wear: float = 0.28,
                surface_db: float = -50.0, impacts: float = 5.0,
                wow_cents: float = 5.0) -> ChainSpec:
    return [
        ("a_historical_mic", {"profile": mic, "amount": 0.68, "proximity": 0.12,
                              "overload": 0.18, "self_noise_db": -60.0,
                              "handling": 0.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_disc_medium", {"medium": "aluminum_disc_1934", "wear": wear,
                           "surface_db": surface_db, "impacts": impacts,
                           "wow_cents": wow_cents}),
        ("a_compressor", {"threshold_db": -22.0, "ratio": 3.8,
                          "attack_ms": 6.0, "release_ms": 210.0, "knee_db": 4.0}),
    ]


def _magnetic_audio(*, mic: str = "broadcast_dynamic_1955", mono: float = 1.0,
                    generations: int = 1, alignment: float = 0.07,
                    compression: float = 0.24, hiss_db: float = -64.0,
                    width: float | None = None) -> ChainSpec:
    chain: ChainSpec = [
        ("a_historical_mic", {"profile": mic, "amount": 0.5, "proximity": 0.08,
                              "overload": 0.1, "self_noise_db": -68.0,
                              "handling": 0.0}),
    ]
    if mono > 0.0:
        chain.append(("a_mono", {"amount": mono}))
    chain.extend([
        ("a_analog_dub", {"format": "reel_15ips", "generations": generations,
                          "alignment": alignment, "compression": compression,
                          "hiss_db": hiss_db}),
        ("a_wow_flutter", {"wow_depth": 2.2, "flutter_depth": 2.6,
                           "scrape": 0.0, "speed_pct": 0.0, "drift_long": 0.04}),
        ("a_compressor", {"threshold_db": -18.0, "ratio": 2.4,
                          "attack_ms": 12.0, "release_ms": 260.0, "knee_db": 7.0}),
    ])
    if width is not None:
        chain.append(("a_channel_aging", {"width": width, "imbalance_db": -0.2,
                                          "crosstalk_db": -48.0, "skew_us": 22.0,
                                          "phase_wander": 0.05,
                                          "mono_bass_hz": 120.0}))
    return chain


def _kinescope_audio(*, high_hz: float = 6500.0, buzz_db: float = -60.0) -> ChainSpec:
    return [
        ("a_historical_mic", {"profile": "broadcast_dynamic_1955", "amount": 0.6,
                              "proximity": 0.08, "overload": 0.12,
                              "self_noise_db": -64.0, "handling": 0.0}),
        ("a_mono", {"amount": 1.0}),
        ("a_tv_sound", {"hz": "60", "buzz_db": buzz_db, "hum_db": -65.0,
                        "comp": 0.45}),
        ("a_optical_track", {"low_hz": 100.0, "high_hz": high_hz,
                             "academy_rolloff": "feature_1940s", "cell_noise": -54.0,
                             "flutter": 0.22, "drive": 1.3}),
        ("a_compressor", {"threshold_db": -20.0, "ratio": 3.2,
                          "attack_ms": 8.0, "release_ms": 220.0, "knee_db": 5.0}),
    ]


# 1-10: silent cinema through the first optical-talkie revue.
register_preset(_preset(
    "auth-lumiere-era-actuality-1896", "Lumière-Era Actuality", "1896", "film",
    "A clean first-generation actuality print: blue-sensitive faces and skies, hand-cranked exposure breathing, modest nitrate grain, and a gently wandering gate; the supplied soundtrack is only given an acoustic-room response.",
    "Blue-sensitive nitrate and hand-crank breath", ("1890s", "actuality", "silent", "nitrate"),
    _mono_print(response="blue_sensitive", tint="nitrate_warm", tint_amt=0.16,
                contrast=1.25, gamma=0.94, lift=0.055, knee=0.72, soft=0.18,
                corner=0.36, grain=0.5, grain_size=2.0, grain_stock="print_dupe",
                mottle=0.18, halation=0.18, print_generations=1, flicker=0.34,
                flicker_character="hand_cranked", weave=1.45, dust=0.25),
    _silent_program_audio(high_hz=8500.0, mono=0.92, room_mix=0.1), 520, "soft",
))

register_preset(_preset(
    "auth-hand-colored-trick-film-1904", "Hand-Colored Trick Film", "1904", "film",
    "A blue-sensitive trick-film print with restrained surviving dye color, soft painted-looking chroma registration, smoky printer haze, nitrate shimmer, and fine surface wear, without adding substitutions or altering a frame.",
    "Nitrate silver under softly registered dyes", ("1900s", "silent", "hand-color", "trick-film"),
    [("mono", {"amount": 0.72, "response": "blue_sensitive", "tint": "nitrate_warm", "tint_amt": 0.12}),
     ("tone", {"contrast": 1.18, "gamma": 0.92, "lift": 0.055, "knee": 0.76}),
     ("saturation", {"amount": 1.18, "vibrance": 0.16}),
     ("optics", {"soft_focus": 0.2, "diffusion": 0.12, "corner_softness": 0.38,
                  "veiling_flare": 0.12}),
     ("optical_composite", {"softness": 0.18, "matte_line": 0.0, "registration": 0.72,
                            "layer_haze": 0.12, "density_breath": 0.16}),
     ("grain", {"amount": 0.48, "size": 2.0, "size_ref": "output", "roughness": 0.55,
                "chroma_grain": 0.08, "stock": "print_dupe", "layers": "print_from_neg",
                "mottle": 0.18}),
     ("halation", {"strength": 0.2, "threshold": 0.7, "radius": 0.045, "tint": "orange"}),
     ("print_char", {"acutance": 0.08, "dmax_breath": 0.16, "contrast_buildup": 1}),
     ("flicker", {"amount": 0.28, "character": "hand_cranked", "color_flicker": 0.18,
                  "spatial": 0.2}),
     ("gate_weave", {"amount": 1.35, "hz": 0.58, "rotation": 0.035, "splice_bump": 0.0}),
     ("dust", {"density": 0.24, "size": 0.9, "polarity": "print", "hairs": 0.12}),
     ("scratches", {"strength": 0.28, "count": 1, "wander": 0.35,
                    "transient_rate": 0.4, "gouge_rate": 0.0})],
    _silent_program_audio(high_hz=8200.0, mono=0.9, room_mix=0.11), 540, "soft",
))

register_preset(_preset(
    "auth-tinted-adventure-serial-1914", "Tinted Adventure Serial", "1914", "film",
    "An amber-tinted serial release print with orthochromatic faces, firm cliff-edge blacks, energetic hand-crank density movement, dupe grain, and theater wear; its color is global and never used to invent transitions.",
    "Amber ortho print with serial-house wear", ("1910s", "silent", "tinted", "serial"),
    _mono_print(response="orthochromatic", tint="sepia", tint_amt=0.58,
                contrast=1.28, lift=0.045, knee=0.73, soft=0.13, grain=0.49,
                grain_size=1.95, grain_stock="print_dupe", mottle=0.14,
                print_generations=2, flicker=0.26, flicker_character="hand_cranked",
                weave=1.25, dust=0.28, scratch_count=2, scratch_rate=0.65),
    _silent_program_audio(high_hz=9000.0, mono=0.9, room_mix=0.09), 560, "soft",
))

register_preset(_preset(
    "auth-nickelodeon-melodrama-1912", "Nickelodeon Melodrama", "1912", "film",
    "A neighborhood-house melodrama print: orthochromatic skin, soft black falloff, modest lens bloom, lively density flutter, and well-traveled nitrate texture while all blocking, titles, and timing remain the source's own.",
    "Soft ortho faces and nickelodeon flutter", ("1910s", "silent", "melodrama", "nitrate"),
    _mono_print(response="orthochromatic", tint="nitrate_warm", tint_amt=0.2,
                contrast=1.16, gamma=0.94, lift=0.06, knee=0.76, soft=0.2,
                diffusion=0.1, corner=0.32, grain=0.46, grain_size=1.9,
                mottle=0.16, halation=0.23, flicker=0.3,
                flicker_character="hand_cranked", weave=1.2, dust=0.27),
    _silent_program_audio(high_hz=8500.0, mono=0.94, room_mix=0.12), 550, "soft",
))

register_preset(_preset(
    "auth-german-expressionist-nightmare-1920", "German Expressionist Nightmare", "1920", "film",
    "A severe orthochromatic nitrate print with crushed architectural blacks, chalk-white highlights, silver-rich grain, hard printer acutance, and restrained projection instability; no canted frame or shadow is fabricated.",
    "Chalk whites, angular blacks, nitrate silver", ("1920s", "silent", "expressionism", "nitrate"),
    _mono_print(response="orthochromatic", tint="silver", tint_amt=0.1,
                exposure=-0.08, contrast=1.55, gamma=0.9, lift=0.005, knee=0.64,
                soft=0.07, diffusion=0.02, corner=0.22, grain=0.5,
                grain_size=1.85, grain_stock="print_dupe", shadow_boost=0.22,
                halation=0.16, print_generations=2, acutance=0.32, dmax=0.18,
                flicker=0.22, weave=1.0, dust=0.24, scratch_count=1),
    _silent_program_audio(high_hz=9200.0, mono=0.95, room_mix=0.07), 580, "soft",
))

register_preset(_preset(
    "auth-soviet-montage-agitfilm-1925", "Soviet Montage Agitfilm", "1925", "film",
    "A forceful high-contrast agitfilm print: coarse newsreel silver, dense blacks, blunt ortho response, hard duplication acutance, and utilitarian circulation wear, with every source shot and its duration untouched.",
    "Hard dupe contrast and newsreel silver", ("1920s", "silent", "soviet", "agitfilm"),
    _mono_print(response="orthochromatic", tint="silver", tint_amt=0.08,
                contrast=1.48, lift=0.015, knee=0.65, soft=0.06, diffusion=0.0,
                grain=0.54, grain_size=2.0, grain_stock="newsreel_35", mottle=0.2,
                shadow_boost=0.25, halation=0.13, print_generations=3,
                acutance=0.4, flicker=0.18, weave=0.95, dust=0.32,
                scratch_count=2, scratch_rate=0.75),
    _silent_program_audio(high_hz=8800.0, mono=0.96, room_mix=0.06), 600, "sharp",
))

register_preset(_preset(
    "auth-jazz-age-city-symphony-1927", "Jazz-Age City Symphony", "1927", "film",
    "A polished late-silent city print with crisp panchromatic geometry, silvery midtones, optical-printer softness, subtle density pulse, and fine metropolitan release grain; no montage or exposure is inserted.",
    "Silvery geometry and optical-printer breath", ("1920s", "silent", "city-symphony", "nitrate"),
    _mono_print(response="panchromatic", tint="silver", tint_amt=0.14,
                contrast=1.3, lift=0.035, knee=0.72, soft=0.1, diffusion=0.05,
                grain=0.42, grain_size=1.7, grain_stock="fine_35", mottle=0.1,
                halation=0.2, print_generations=1, acutance=0.27, dmax=0.16,
                flicker=0.2, weave=0.75, dust=0.16, scratch_count=0),
    _silent_program_audio(high_hz=11000.0, mono=0.76, room_mix=0.08), 620, "soft",
))

register_preset(_preset(
    "auth-slapstick-two-reeler-1924", "Slapstick Two-Reeler", "1924", "film",
    "A bright comedy exchange print with open orthochromatic faces, crisp action detail, brisk hand-crank exposure flutter, firm dupe contrast, and practical theater wear; motion speed and gag timing stay native.",
    "Bright ortho comedy print, native timing", ("1920s", "silent", "slapstick", "two-reeler"),
    _mono_print(response="orthochromatic", tint="nitrate_warm", tint_amt=0.14,
                exposure=0.05, contrast=1.26, lift=0.05, knee=0.72, soft=0.09,
                grain=0.48, grain_size=1.85, grain_stock="print_dupe",
                print_generations=2, flicker=0.25, flicker_character="hand_cranked",
                weave=1.1, dust=0.29, scratch_count=2, scratch_rate=0.7),
    _silent_program_audio(high_hz=9800.0, mono=0.88, room_mix=0.1), 580, "sharp",
))

register_preset(_preset(
    "auth-hand-tinted-fairy-photoplay-1921", "Hand-Tinted Fairy Photoplay", "1921", "film",
    "A gauzy fairy photoplay with gently retained dye color over warm silver, soft lens bloom, visible color-record drift, fine nitrate grain, and a velvety low-contrast print; no sparkle or vignette is drawn in.",
    "Gauzy silver with drifting pastel dyes", ("1920s", "silent", "hand-tinted", "fantasy"),
    [("mono", {"amount": 0.66, "response": "orthochromatic", "tint": "nitrate_warm", "tint_amt": 0.2}),
     ("tone", {"contrast": 0.96, "gamma": 0.92, "lift": 0.07, "knee": 0.8}),
     ("saturation", {"amount": 0.96, "vibrance": 0.2}),
     ("balance", {"warmth": 0.18, "tint": 0.04, "high_tint": "cream", "high_amt": 0.16}),
     ("optics", {"soft_focus": 0.3, "bloom_mids": 0.5, "diffusion": 0.24,
                  "corner_softness": 0.38, "veiling_flare": 0.16}),
     ("optical_composite", {"softness": 0.2, "matte_line": 0.0, "registration": 0.55,
                            "layer_haze": 0.12, "density_breath": 0.12}),
     ("grain", {"amount": 0.4, "size": 1.8, "size_ref": "output", "roughness": 0.44,
                "chroma_grain": 0.06, "stock": "fine_35", "layers": "print_from_neg",
                "mottle": 0.1}),
     ("halation", {"strength": 0.32, "threshold": 0.68, "radius": 0.055, "tint": "warm_white"}),
     ("print_char", {"acutance": 0.05, "dmax_breath": 0.12, "contrast_buildup": 1}),
     ("flicker", {"amount": 0.17, "character": "projector", "color_flicker": 0.1,
                  "spatial": 0.12}),
     ("gate_weave", {"amount": 0.8, "hz": 0.55, "rotation": 0.018, "splice_bump": 0.0}),
     ("dust", {"density": 0.15, "size": 0.75, "polarity": "print", "hairs": 0.06})],
    _silent_program_audio(high_hz=10500.0, mono=0.8, room_mix=0.12), 580, "soft",
))

register_preset(_preset(
    "auth-early-talkie-revue-1929", "Early Talkie Revue", "1929", "film",
    "A first-wave sound revue on panchromatic nitrate: soft fixed-focus stage detail, hot lamp highlights, steady fine grain, modest projection breath, and a boxy carbon-microphone optical mono stripe.",
    "Soft nitrate stage and carbon optical mono", ("1929", "early-sound", "revue", "optical"),
    _mono_print(response="panchromatic", tint="silver", tint_amt=0.16,
                contrast=1.22, lift=0.045, knee=0.72, soft=0.2, diffusion=0.08,
                corner=0.22, grain=0.44, grain_size=1.75, grain_stock="fine_35",
                halation=0.24, print_generations=1, flicker=0.13, weave=0.72,
                dust=0.16, scratch_count=0),
    _optical_audio(mic="carbon_1925", mic_amount=0.78, proximity=0.12,
                   overload=0.32, self_noise=-56.0, low_hz=180.0, high_hz=4400.0,
                   rolloff="newsreel_1930s", cell_noise=-44.0, flutter=0.62,
                   drive=2.05, ratio=4.8, room_mix=0.08), 640, "soft",
))


# 12-26: studio sound, documentary, advertising, and small-gauge records.
register_preset(_preset(
    "auth-gothic-studio-horror-1932", "Gothic Studio Horror", "1932", "film",
    "A nitrate studio-horror release print with moon-white panchromatic highlights, velvety D-max, fog-softened glass, restrained silver halation, and a low-bandwidth optical stripe carrying the original program intact.",
    "Moon-white nitrate and ominous optical mono", ("1930s", "horror", "nitrate", "studio"),
    _mono_print(response="panchromatic", tint="silver", tint_amt=0.12,
                exposure=-0.08, contrast=1.48, lift=0.005, knee=0.65, soft=0.14,
                diffusion=0.18, flare=0.12, grain=0.43, grain_size=1.7,
                shadow_boost=0.22, halation=0.25, print_generations=2,
                dmax=0.2, flicker=0.1, weave=0.62, dust=0.13,
                scratch_count=0),
    _optical_audio(mic="carbon_1925", mic_amount=0.62, overload=0.22,
                   high_hz=5000.0, rolloff="newsreel_1930s", cell_noise=-48.0,
                   flutter=0.4, drive=1.7, ratio=4.0, room_mix=0.12), 680, "soft",
))

register_preset(_preset(
    "auth-geometric-chorus-spectacle-1934", "Geometric Chorus Spectacle", "1934", "film",
    "A premium musical print with glossy panchromatic skin, lacquer-black density, soft high-key diffusion, fine studio grain, and a bright variable-area mono track; choreography and camera movement are never manufactured.",
    "Glossy stage silver and bright optical mono", ("1930s", "musical", "chorus", "studio"),
    _mono_print(response="panchromatic", tint="silver", tint_amt=0.16,
                exposure=0.04, contrast=1.3, lift=0.025, knee=0.7, soft=0.14,
                diffusion=0.16, flare=0.1, grain=0.36, grain_size=1.55,
                halation=0.28, print_generations=1, acutance=0.22, flicker=0.07,
                weave=0.48, dust=0.09, scratch_count=0),
    _optical_audio(mic="ribbon_1938", mic_amount=0.58, proximity=0.12,
                   overload=0.12, high_hz=5700.0, rolloff="newsreel_1930s",
                   cell_noise=-51.0, flutter=0.28, drive=1.45, ratio=3.4,
                   room_mix=0.08), 700, "soft",
))

register_preset(_preset(
    "auth-wpa-social-documentary-1936", "WPA Social Documentary", "1936", "archive",
    "A sober 16 mm civic-documentary element: practical-light panchromatic response, coarse but controlled location grain, modest lens falloff, work-print density, and plain carbon-microphone optical narration.",
    "Practical-light 16 mm and plain civic mono", ("1930s", "documentary", "wpa", "16mm"),
    _mono_print(response="panchromatic", tint="silver", tint_amt=0.11,
                contrast=1.2, lift=0.045, knee=0.76, soft=0.12, diffusion=0.03,
                corner=0.24, grain=0.52, grain_size=2.05, grain_stock="doc_16",
                mottle=0.18, shadow_boost=0.16, halation=0.16,
                print_generations=1, acutance=0.24, flicker=0.12, weave=0.9,
                dust=0.2, scratch_count=1),
    _optical_audio(mic="carbon_1925", mic_amount=0.7, overload=0.25,
                   self_noise=-56.0, low_hz=150.0, high_hz=4800.0,
                   rolloff="classroom_16mm", cell_noise=-46.0, flutter=0.52,
                   drive=1.65, ratio=4.2), 620, "soft",
))

register_preset(_preset(
    "auth-art-deco-luxury-commercial-1937", "Art Deco Luxury Commercial", "1937", "film",
    "A meticulously exposed luxury short with chrome-bright speculars, lacquered panchromatic blacks, silky diffusion, low-mileage nitrate grain, and a refined ribbon-to-optical mono chain.",
    "Chrome highlights, lacquer blacks, ribbon", ("1930s", "commercial", "art-deco", "nitrate"),
    _mono_print(response="panchromatic", tint="silver", tint_amt=0.14,
                exposure=0.03, contrast=1.38, lift=0.012, knee=0.67, soft=0.1,
                diffusion=0.12, flare=0.06, grain=0.32, grain_size=1.45,
                halation=0.3, print_generations=1, acutance=0.3, dmax=0.1,
                flicker=0.045, weave=0.36, dust=0.055, scratch_count=0),
    _optical_audio(mic="ribbon_1938", mic_amount=0.72, proximity=0.16,
                   overload=0.08, self_noise=-66.0, low_hz=90.0, high_hz=6200.0,
                   rolloff="feature_1940s", cell_noise=-54.0, flutter=0.2,
                   drive=1.25, ratio=2.8, room_mix=0.06), 720, "sharp",
))

register_preset(_preset(
    "auth-rubber-hose-rural-cartoon-1932", "Rubber-Hose Rural Cartoon", "1932", "cartoon",
    "A grayscale cartoon release print with warm paper whites, dense ink-like blacks, duotone rubber-hose color response, optical-camera softness, cel-era silver grain, and hot narrow mono, without changing a drawing or its exposure count.",
    "Warm paper whites and hot cartoon mono", ("1930s", "cartoon", "rubber-hose", "cel"),
    [("color_era", {"profile": "rubber_hose_1930s", "strength": 0.92}),
     ("tone", {"contrast": 1.32, "lift": 0.035, "knee": 0.7}),
     ("optics", {"soft_focus": 0.1, "diffusion": 0.03, "corner_softness": 0.12}),
     ("grain", {"amount": 0.4, "size": 1.65, "size_ref": "output", "roughness": 0.46,
                "chroma_grain": 0.0, "stock": "fine_35", "layers": "mono"}),
     ("halation", {"strength": 0.2, "threshold": 0.68, "radius": 0.04, "tint": "neutral"}),
     ("print_char", {"acutance": 0.28, "dmax_breath": 0.1, "contrast_buildup": 2}),
     ("flicker", {"amount": 0.09, "character": "projector", "spatial": 0.06}),
     ("gate_weave", {"amount": 0.7, "hz": 0.62, "rotation": 0.018, "splice_bump": 0.0}),
     ("dust", {"density": 0.13, "size": 0.75, "polarity": "print", "hairs": 0.04}),
     ("scratches", {"strength": 0.2, "count": 0, "wander": 0.2,
                    "transient_rate": 0.16, "gouge_rate": 0.0})],
    _optical_audio(mic="carbon_1925", mic_amount=0.7, overload=0.34,
                   high_hz=5200.0, rolloff="newsreel_1930s", cell_noise=-47.0,
                   flutter=0.42, drive=1.9, ratio=4.5), 640, "sharp",
))

register_preset(_preset(
    "auth-ocean-liner-newsreel-1938", "Ocean-Liner Newsreel", "1938", "archive",
    "A wind-bright newsreel print with hard panchromatic contrast, coarse reporter stock, crisp printer edge, moderate exchange wear, and a carbon microphone squeezed into a crackling variable-area stripe.",
    "Wind-bright silver, clipped optical speech", ("1930s", "newsreel", "ocean-liner", "reportage"),
    _mono_print(response="panchromatic", tint="silver", tint_amt=0.1,
                contrast=1.42, lift=0.02, knee=0.66, soft=0.06, diffusion=0.0,
                grain=0.56, grain_size=2.0, grain_stock="newsreel_35", mottle=0.2,
                shadow_boost=0.22, halation=0.17, print_generations=3,
                acutance=0.38, flicker=0.15, weave=0.98, dust=0.3,
                scratch_count=2, scratch_rate=0.7),
    _optical_audio(mic="carbon_1925", mic_amount=0.84, overload=0.48,
                   self_noise=-53.0, low_hz=180.0, high_hz=4500.0,
                   rolloff="newsreel_1930s", cell_noise=-42.0, flutter=0.64,
                   drive=2.15, ratio=5.2), 640, "sharp",
))

register_preset(_preset(
    "auth-radio-mystery-adaptation-1937", "Radio Mystery Adaptation", "1937", "film",
    "A shadow-rich studio print paired with close carbon-and-ribbon speech: soft low-key panchromatic detail, deep nitrate blacks, quiet gate movement, narrow optical bandwidth, and a short dark chamber around the original track.",
    "Shadow-rich nitrate and chamber mono", ("1930s", "mystery", "radio", "studio"),
    _mono_print(response="panchromatic", tint="silver", tint_amt=0.12,
                exposure=-0.05, contrast=1.4, lift=0.01, knee=0.66, soft=0.13,
                diffusion=0.1, flare=0.08, grain=0.4, grain_size=1.6,
                shadow_boost=0.2, halation=0.2, print_generations=1,
                dmax=0.18, flicker=0.065, weave=0.44, dust=0.09,
                scratch_count=0),
    _optical_audio(mic="ribbon_1938", mic_amount=0.76, proximity=0.34,
                   overload=0.13, self_noise=-63.0, low_hz=100.0, high_hz=5600.0,
                   rolloff="feature_1940s", cell_noise=-51.0, flutter=0.28,
                   drive=1.5, ratio=3.8, room_mix=0.18), 700, "soft",
))

register_preset(_preset(
    "auth-depression-road-drama-1935", "Depression Road Drama", "1935", "film",
    "A weathered location negative printed plainly: dry ortho-panchromatic faces, dusty lifted mids, natural-lens softness, visible 35 mm grain, restrained print wear, and thin location speech on optical mono.",
    "Dry roadside silver and thin location optical", ("1930s", "drama", "location", "depression-era"),
    _mono_print(response="panchromatic", tint="nitrate_warm", tint_amt=0.13,
                contrast=1.18, gamma=0.96, lift=0.055, knee=0.76, soft=0.1,
                diffusion=0.02, corner=0.2, flare=0.08, grain=0.47,
                grain_size=1.85, grain_stock="fine_35", mottle=0.14,
                halation=0.16, print_generations=2, flicker=0.1, weave=0.72,
                dust=0.2, scratch_count=1),
    _optical_audio(mic="carbon_1925", mic_amount=0.55, proximity=0.03,
                   self_noise=-57.0, low_hz=150.0, high_hz=4800.0,
                   rolloff="newsreel_1930s", cell_noise=-49.0, flutter=0.42,
                   drive=1.55, ratio=3.6), 650, "soft",
))

register_preset(_preset(
    "auth-british-quota-quickie-1936", "British Quota Quickie", "1936", "film",
    "An economical British studio release: tidy panchromatic grayscale, modest Cooke softness, efficient one-light printing, restrained grain, and a thin but intelligible optical mono path with no added theatrical business.",
    "Tidy one-light print, economical mono", ("1930s", "british", "quota-quickie", "studio"),
    _mono_print(response="panchromatic", tint="silver", tint_amt=0.13,
                contrast=1.2, lift=0.035, knee=0.75, soft=0.15, diffusion=0.05,
                corner=0.18, grain=0.38, grain_size=1.6, halation=0.18,
                print_generations=1, acutance=0.18, flicker=0.07, weave=0.5,
                dust=0.12, scratch_count=0),
    _optical_audio(mic="ribbon_1938", mic_amount=0.48, overload=0.11,
                   low_hz=130.0, high_hz=5300.0, rolloff="feature_1940s",
                   cell_noise=-51.0, flutter=0.31, drive=1.4, ratio=3.1), 680, "soft",
))

register_preset(_preset(
    "auth-color-travelogue-short-1938", "Color Travelogue Short", "1938", "world",
    "A two-color travel print with brick-red skin, cyan-green distance, restrained yellow, postcard-bright exposure, soft dye-record registration, fine duplitized grain, and formal optical mono narration.",
    "Brick red, cyan-green, soft two-color records", ("1930s", "travelogue", "two-color", "early-color"),
    _color_print(profile="technicolor2", stock_strength=0.9, contrast=1.14,
                 lift=0.035, knee=0.77, warmth=0.18, tint=-0.04,
                 shadow_tint="teal", shadow_amt=0.16, high_tint="pink",
                 high_amt=0.1, saturation=1.1, vibrance=0.08, soft=0.12,
                 optical_softness=0.14, registration=0.3, layer_haze=0.07,
                 density_breath=0.12, grain=0.4, grain_size=1.8,
                 chroma_grain=0.1, mottle=0.1, halation=0.26,
                 print_generations=1, fade=0.05, flicker=0.09, weave=0.7,
                 dust=0.14),
    _optical_audio(mic="ribbon_1938", mic_amount=0.52, low_hz=120.0,
                   high_hz=5600.0, rolloff="feature_1940s", cell_noise=-52.0,
                   flutter=0.3, drive=1.4, ratio=3.0), 680, "soft",
))

register_preset(_preset(
    "auth-streamline-moderne-industrial-film-1937", "Streamline Moderne Industrial Film", "1937", "archive",
    "A precision industrial print with polished panchromatic steel, hard development-edge acutance, clean geometric tonal separation, low-mileage grain, and authoritative ribbon speech on a disciplined optical track.",
    "Polished steel, hard acutance, clean mono", ("1930s", "industrial", "streamline-moderne", "instructional"),
    _mono_print(response="panchromatic", tint="silver", tint_amt=0.12,
                exposure=0.02, contrast=1.38, lift=0.018, knee=0.68, soft=0.05,
                diffusion=0.01, corner=0.08, grain=0.36, grain_size=1.55,
                halation=0.2, print_generations=1, acutance=0.42, dmax=0.08,
                flicker=0.055, weave=0.42, dust=0.08, scratch_count=0),
    _optical_audio(mic="ribbon_1938", mic_amount=0.68, proximity=0.18,
                   overload=0.1, high_hz=5700.0, rolloff="feature_1940s",
                   cell_noise=-53.0, flutter=0.24, drive=1.32, ratio=3.4), 700, "sharp",
))

register_preset(_preset(
    "auth-cabaret-soundie-1939", "Cabaret Soundie", "1939", "film",
    "A compact nightclub performance on glossy monochrome stock: luminous faces through smoke-soft glass, dense stage blacks, fine release grain, and a close ribbon capture pressed onto a worn period disc response.",
    "Smoke-soft stage silver and period disc swish", ("1930s", "cabaret", "soundie", "disc"),
    _mono_print(response="panchromatic", tint="silver", tint_amt=0.15,
                exposure=-0.02, contrast=1.32, lift=0.018, knee=0.68, soft=0.16,
                diffusion=0.2, flare=0.14, grain=0.38, grain_size=1.55,
                halation=0.28, print_generations=1, flicker=0.07, weave=0.46,
                dust=0.1, scratch_count=0),
    _disc_audio(mic="ribbon_1938", wear=0.3, surface_db=-49.0,
                impacts=5.0, wow_cents=5.0), 680, "soft",
))

register_preset(_preset(
    "auth-expedition-archive-reel-1934", "Expedition Archive Reel", "1934", "archive",
    "A 16 mm expedition reversal held as an archive reel: coarse silver, uncertain daylight exposure, soft corners, mild density drift, careful surface wear, and narrow field narration on an early optical stripe.",
    "Coarse 16 mm silver, uncertain exposure", ("1930s", "expedition", "archive", "16mm"),
    _mono_print(response="orthochromatic", tint="nitrate_warm", tint_amt=0.17,
                exposure=0.04, contrast=1.24, gamma=0.94, lift=0.05, knee=0.72,
                soft=0.18, corner=0.42, flare=0.12, grain=0.58,
                grain_size=2.15, grain_stock="doc_16", mottle=0.26,
                shadow_boost=0.18, halation=0.17, print_generations=2,
                dmax=0.22, flicker=0.22, weave=1.35, dust=0.34,
                scratch_count=2, scratch_rate=0.9),
    _optical_audio(mic="carbon_1925", mic_amount=0.58, proximity=0.02,
                   overload=0.3, self_noise=-53.0, low_hz=180.0, high_hz=4200.0,
                   rolloff="classroom_16mm", cell_noise=-43.0, flutter=0.7,
                   drive=1.85, ratio=4.5), 600, "soft",
))

register_preset(_preset(
    "auth-sepia-family-home-movie-1938", "Sepia Family Home Movie", "1938", "film",
    "A small-gauge family reel with warm sepia silver, simple-lens softness, rounded tonal shoulders, lively but continuous gate drift, reversal-sized grain, and no manufactured silence or missing frames.",
    "Warm small-gauge silver and simple-lens drift", ("1930s", "home-movie", "sepia", "small-gauge"),
    _mono_print(response="orthochromatic", tint="sepia", tint_amt=0.62,
                exposure=0.06, contrast=1.04, gamma=0.93, lift=0.065, knee=0.8,
                soft=0.25, diffusion=0.08, corner=0.48, flare=0.14, grain=0.58,
                grain_size=2.15, grain_stock="super8", mottle=0.24,
                halation=0.2, print_generations=0, acutance=0.06, dmax=0.22,
                flicker=0.25, weave=1.75, dust=0.26, scratch_count=1),
    _silent_program_audio(high_hz=9000.0, mono=0.82, room_mix=0.08), 520, "soft",
))

register_preset(_preset(
    "auth-wartime-signal-corps-film-1943", "Wartime Signal Corps Film", "1943", "archive",
    "A utilitarian wartime 16 mm print: hard panchromatic daylight, dense military midtones, coarse documentary grain, disciplined one-light duplication, field wear, and clipped carbon narration on classroom-width optical mono.",
    "Hard 16 mm and clipped field narration", ("1940s", "wartime", "signal-corps", "16mm"),
    _mono_print(response="panchromatic", tint="silver", tint_amt=0.1,
                contrast=1.36, lift=0.025, knee=0.68, soft=0.08, diffusion=0.01,
                corner=0.16, grain=0.56, grain_size=2.05, grain_stock="doc_16",
                mottle=0.18, shadow_boost=0.2, halation=0.17,
                print_generations=2, acutance=0.34, flicker=0.14, weave=0.95,
                dust=0.29, scratch_count=2, scratch_rate=0.75),
    _optical_audio(mic="carbon_1925", mic_amount=0.8, proximity=0.12,
                   overload=0.42, self_noise=-54.0, low_hz=140.0, high_hz=5000.0,
                   rolloff="classroom_16mm", cell_noise=-44.0, flutter=0.58,
                   drive=1.9, ratio=5.0), 620, "sharp",
))


# 29-40: postwar studio polish, home color, classrooms, and industry.
register_preset(_preset(
    "auth-supernatural-romantic-melodrama-1947", "Supernatural Romantic Melodrama", "1947", "film",
    "A moonlit romantic release print with luminous panchromatic skin, fog-soft highlights, gentle silver halation, fine 35 mm grain, quiet density breathing, and warm feature-width optical mono.",
    "Moonlit diffusion, warm optical mono", ("1940s", "romance", "supernatural", "melodrama"),
    _mono_print(response="panchromatic", tint="silver", tint_amt=0.17,
                exposure=-0.02, contrast=1.2, lift=0.03, knee=0.74, soft=0.22,
                diffusion=0.24, flare=0.16, grain=0.34, grain_size=1.5,
                halation=0.34, print_generations=1, acutance=0.12, dmax=0.14,
                flicker=0.055, weave=0.38, dust=0.07, scratch_count=0),
    _optical_audio(mic="ribbon_1938", mic_amount=0.68, proximity=0.18,
                   overload=0.1, self_noise=-66.0, low_hz=80.0, high_hz=6800.0,
                   rolloff="feature_1940s", cell_noise=-56.0, flutter=0.2,
                   drive=1.3, ratio=2.8, room_mix=0.08), 720, "soft",
))

register_preset(_preset(
    "auth-womens-picture-gloss-1942", "Women’s Picture Gloss", "1942", "film",
    "A studio glamour print with sculpted panchromatic faces, satin diffusion, pearl-like highlight bloom, velvety blacks, exceptionally fine grain, and a smooth ribbon-to-optical mono chain retaining every original cue.",
    "Satin faces, pearl highlights, velvet mono", ("1940s", "womens-picture", "glamour", "studio"),
    _mono_print(response="panchromatic", tint="silver", tint_amt=0.16,
                exposure=0.03, contrast=1.27, lift=0.018, knee=0.68, soft=0.18,
                diffusion=0.28, corner=0.1, flare=0.12, grain=0.3,
                grain_size=1.4, halation=0.32, print_generations=1,
                acutance=0.18, dmax=0.1, flicker=0.04, weave=0.32,
                dust=0.045, scratch_count=0),
    _optical_audio(mic="ribbon_1938", mic_amount=0.74, proximity=0.2,
                   overload=0.08, self_noise=-67.0, low_hz=75.0, high_hz=6900.0,
                   rolloff="feature_1940s", cell_noise=-57.0, flutter=0.17,
                   drive=1.25, ratio=2.7, room_mix=0.07), 720, "soft",
))

register_preset(_preset(
    "auth-big-band-soundie-1944", "Big-Band Soundie", "1944", "film",
    "A compact performance print with bright panchromatic brass, glossy stage blacks, firm printer acutance, fine-grain monochrome, and hot ribbon-captured optical mono compressed for small playback systems.",
    "Glossy bandstand silver, punchy mono", ("1940s", "soundie", "big-band", "performance"),
    _mono_print(response="panchromatic", tint="silver", tint_amt=0.13,
                exposure=0.03, contrast=1.34, lift=0.02, knee=0.67, soft=0.09,
                diffusion=0.1, flare=0.08, grain=0.38, grain_size=1.55,
                halation=0.24, print_generations=2, acutance=0.3,
                flicker=0.06, weave=0.48, dust=0.11, scratch_count=0),
    _optical_audio(mic="ribbon_1938", mic_amount=0.82, proximity=0.15,
                   overload=0.2, self_noise=-62.0, low_hz=90.0, high_hz=6400.0,
                   rolloff="feature_1940s", cell_noise=-50.0, flutter=0.3,
                   drive=1.75, ratio=4.6, room_mix=0.06), 680, "sharp",
))

register_preset(_preset(
    "auth-british-postwar-studio-comedy-1949", "British Postwar Studio Comedy", "1949", "film",
    "A tidy postwar British release: clean panchromatic ensembles, restrained Cooke softness, open midtones, modest fine grain, steady printing, and articulate feature optical mono with dry studio presence.",
    "Tidy British grayscale, dry mono", ("1940s", "british", "comedy", "studio"),
    _mono_print(response="panchromatic", tint="silver", tint_amt=0.11,
                contrast=1.16, lift=0.035, knee=0.78, soft=0.11,
                diffusion=0.05, corner=0.12, grain=0.33, grain_size=1.45,
                halation=0.18, print_generations=1, acutance=0.22,
                flicker=0.04, weave=0.34, dust=0.055, scratch_count=0),
    _optical_audio(mic="ribbon_1938", mic_amount=0.56, proximity=0.08,
                   overload=0.08, self_noise=-67.0, low_hz=85.0, high_hz=6900.0,
                   rolloff="feature_1940s", cell_noise=-57.0, flutter=0.18,
                   drive=1.25, ratio=2.6, room_mix=0.04), 720, "sharp",
))

register_preset(_preset(
    "auth-japanese-occupation-era-drama-1947", "Japanese Occupation-Era Drama", "1947", "world",
    "A restrained postwar Japanese print with soft panchromatic gray, quiet interior shadow separation, low-contrast glass, delicate silver grain, minimal gate motion, and a narrow, carefully controlled optical mono track.",
    "Quiet gray interiors, restrained mono", ("1940s", "japanese", "postwar", "drama"),
    _mono_print(response="panchromatic", tint="silver", tint_amt=0.09,
                exposure=-0.02, contrast=1.08, gamma=0.97, lift=0.045, knee=0.8,
                soft=0.15, diffusion=0.06, corner=0.16, flare=0.08, grain=0.4,
                grain_size=1.65, mottle=0.1, halation=0.16,
                print_generations=1, acutance=0.14, dmax=0.08, flicker=0.045,
                weave=0.38, dust=0.08, scratch_count=0),
    _optical_audio(mic="ribbon_1938", mic_amount=0.48, proximity=0.04,
                   overload=0.07, self_noise=-66.0, low_hz=110.0, high_hz=6000.0,
                   rolloff="feature_1940s", cell_noise=-55.0, flutter=0.22,
                   drive=1.28, ratio=2.5, room_mix=0.04), 700, "soft",
))

register_preset(_preset(
    "auth-kodachrome-home-front-reel-1944", "Kodachrome Home Front Reel", "1944", "film",
    "A wartime Kodachrome reversal reel with deep warm reds, clear daylight blues, slightly dense shadows, simple-lens corners, small-gauge dye grain, and a continuously moving but never retimed gate.",
    "Deep Kodachrome reds and small-gauge daylight", ("1940s", "kodachrome", "home-front", "home-movie"),
    _color_print(profile="kodachrome", stock_strength=0.94, exposure=0.03,
                 contrast=1.2, lift=0.02, knee=0.76, warmth=0.14,
                 shadow_tint="blue", shadow_amt=0.08, high_tint="cream",
                 high_amt=0.1, saturation=1.2, vibrance=0.1, soft=0.14,
                 corner=0.32, flare=0.12, optical_softness=0.04,
                 registration=0.04, grain=0.22, grain_size=1.0,
                 chroma_grain=0.075, grain_stock="super8", layers="reversal",
                 mottle=0.07, halation=0.28, print_generations=0, fade=0.035,
                 flicker=0.07, weave=0.58, dust=0.055, scratch_count=0),
    _silent_program_audio(high_hz=11000.0, mono=0.72, room_mix=0.06), 540, "soft",
))

register_preset(_preset(
    "auth-classroom-hygiene-film-1948", "Classroom Hygiene Film", "1948", "archive",
    "An earnest 16 mm classroom print with flat panchromatic exposure, chalky instructional mids, institutional grain, modest library wear, and a crystal microphone pressed through a noisy classroom optical stripe.",
    "Flat classroom 16 mm, earnest speech", ("1940s", "classroom", "hygiene", "16mm"),
    _mono_print(response="panchromatic", tint="silver", tint_amt=0.1,
                contrast=1.12, lift=0.055, knee=0.78, soft=0.13,
                diffusion=0.03, corner=0.18, grain=0.52, grain_size=1.95,
                grain_stock="doc_16", mottle=0.16, halation=0.15,
                print_generations=2, acutance=0.22, flicker=0.12, weave=0.8,
                dust=0.26, scratch_count=1, scratch_rate=0.55),
    _optical_audio(mic="crystal_1940", mic_amount=0.74, proximity=0.16,
                   overload=0.26, self_noise=-55.0, low_hz=160.0, high_hz=4800.0,
                   rolloff="classroom_16mm", cell_noise=-43.0, flutter=0.58,
                   drive=1.8, ratio=4.5), 620, "soft",
))

register_preset(_preset(
    "auth-department-store-holiday-reel-1949", "Department-Store Holiday Reel", "1949", "film",
    "A warm holiday display reel with dense early color, glowing practical highlights, gentle diffusion, fine 35 mm dye grain, a softly registered print, and polished mono narration kept free of added cheer.",
    "Warm display color, glowing practicals", ("1940s", "holiday", "department-store", "color"),
    _color_print(profile="technicolor3", stock_strength=0.8, contrast=1.08,
                 lift=0.035, knee=0.78, warmth=0.22, high_tint="cream",
                 high_amt=0.16, saturation=1.12, vibrance=0.12, soft=0.14,
                 diffusion=0.18, flare=0.14, optical_softness=0.1,
                 registration=0.14, layer_haze=0.06, grain=0.36,
                 grain_size=1.65, chroma_grain=0.12, halation=0.34,
                 print_generations=1, fade=0.045, flicker=0.08, weave=0.62,
                 dust=0.12, scratch_count=0),
    _optical_audio(mic="ribbon_1938", mic_amount=0.56, overload=0.1,
                   high_hz=6500.0, rolloff="feature_1940s", cell_noise=-54.0,
                   flutter=0.25, drive=1.35, ratio=3.0), 680, "soft",
))

register_preset(_preset(
    "auth-puppet-advertising-short-1947", "Puppet Advertising Short", "1947", "film",
    "A tabletop puppet commercial on saturated three-color stock: miniature-scale lens softness, warm painted primaries, clean optical-composite registration, fine print grain, and lively mono bandwidth without changing motion cadence.",
    "Warm puppet primaries, tabletop softness", ("1940s", "puppet", "advertising", "color"),
    _color_print(profile="technicolor3", stock_strength=0.88, contrast=1.16,
                 lift=0.025, knee=0.74, warmth=0.14, saturation=1.22,
                 vibrance=0.14, soft=0.12, diffusion=0.08, corner=0.18,
                 flare=0.08, optical_softness=0.12, registration=0.18,
                 layer_haze=0.05, grain=0.38, grain_size=1.7,
                 chroma_grain=0.13, halation=0.28, print_generations=1,
                 fade=0.025, flicker=0.07, weave=0.58, dust=0.1),
    _optical_audio(mic="ribbon_1938", mic_amount=0.62, overload=0.18,
                   high_hz=6200.0, rolloff="feature_1940s", cell_noise=-52.0,
                   flutter=0.3, drive=1.55, ratio=3.8), 680, "sharp",
))

register_preset(_preset(
    "auth-color-industrial-optimism-1948", "Color Industrial Optimism", "1948", "archive",
    "A premium color industrial print with saturated machinery, polished metal highlights, precise three-color separation, controlled fine grain, restrained release wear, and a confident optical narration chain.",
    "Saturated machinery, precise dye color", ("1940s", "industrial", "optimism", "color"),
    _color_print(profile="technicolor3", stock_strength=0.86, exposure=0.03,
                 contrast=1.2, lift=0.018, knee=0.72, warmth=0.1,
                 shadow_tint="blue", shadow_amt=0.06, saturation=1.2,
                 vibrance=0.1, soft=0.055, diffusion=0.025, corner=0.06,
                 optical_softness=0.06, registration=0.1, layer_haze=0.025,
                 grain=0.32, grain_size=1.5, chroma_grain=0.1,
                 halation=0.25, print_generations=1, fade=0.02,
                 flicker=0.05, weave=0.4, dust=0.07),
    _optical_audio(mic="ribbon_1938", mic_amount=0.66, proximity=0.14,
                   overload=0.09, self_noise=-66.0, high_hz=6600.0,
                   rolloff="feature_1940s", cell_noise=-55.0, flutter=0.22,
                   drive=1.3, ratio=3.0), 700, "sharp",
))


# 42-60: drive-in prints, television capture, Eastman color, and wide-format sound.
register_preset(_preset(
    "auth-drive-in-rebel-drama-1956", "Drive-In Rebel Drama", "1956", "film",
    "A hard-edged monochrome drive-in print with chrome-bright highlights, leather-black shadows, slightly pushed 35 mm grain, firm dupe contrast, and hot optical mono that leaves every performance and cue in place.",
    "Chrome highlights, hot drive-in mono", ("1950s", "drive-in", "rebel", "bw"),
    _mono_print(response="panchromatic", tint="silver", tint_amt=0.09,
                contrast=1.45, lift=0.01, knee=0.64, soft=0.055, diffusion=0.015,
                corner=0.1, grain=0.5, grain_size=1.8, grain_stock="push_process",
                mottle=0.12, shadow_boost=0.25, halation=0.2,
                print_generations=2, acutance=0.4, flicker=0.06, weave=0.52,
                dust=0.12, scratch_count=1),
    _optical_audio(mic="broadcast_dynamic_1955", mic_amount=0.7,
                   proximity=0.16, overload=0.2, self_noise=-62.0,
                   low_hz=80.0, high_hz=7000.0, rolloff="feature_1940s",
                   cell_noise=-52.0, flutter=0.28, drive=1.75, ratio=4.3), 700, "sharp",
))

register_preset(_preset(
    "auth-eastmancolor-tourist-film-1957", "Eastmancolor Tourist Film", "1957", "world",
    "A sunlit tourist short on early Eastman color: pastel landscapes, warm cream highlights, gentle cyan separation in distant shadows, soft fine-grain printing, and clean formal narration on mono optical sound.",
    "Pastel Eastman landscapes, clean mono", ("1950s", "eastmancolor", "tourist", "travelogue"),
    _color_print(profile="eastman_60s", stock_strength=0.64, exposure=0.07,
                 contrast=1.02, lift=0.04, knee=0.84, warmth=0.12,
                 shadow_tint="blue", shadow_amt=0.1, high_tint="cream",
                 high_amt=0.15, saturation=0.96, vibrance=0.1, soft=0.11,
                 diffusion=0.1, corner=0.12, flare=0.12,
                 optical_softness=0.06, registration=0.07, layer_haze=0.04,
                 grain=0.28, grain_size=1.45, chroma_grain=0.09,
                 halation=0.24, print_generations=1, fade=0.035,
                 flicker=0.04, weave=0.36, dust=0.06),
    _optical_audio(mic="broadcast_dynamic_1955", mic_amount=0.48,
                   overload=0.07, self_noise=-68.0, low_hz=80.0, high_hz=7200.0,
                   rolloff="feature_1940s", cell_noise=-58.0, flutter=0.15,
                   drive=1.2, ratio=2.5), 700, "soft",
))

register_preset(_preset(
    "auth-live-television-anthology-1954", "Live Television Anthology", "1954", "broadcast",
    "A live monochrome television feed preserved by kinescope: limited composite bandwidth, interlaced CRT line structure, blooming whites, film-recording softness, fine silver grain, and urgent mono broadcast sound.",
    "Interlaced CRT bloom on fine kinescope grain", ("1950s", "live-tv", "anthology", "kinescope"),
    _kinescope(contrast=1.13, lift=0.045, bloom=0.25, grain=0.36,
               flicker=0.085, weave=0.58),
    _kinescope_audio(high_hz=6300.0, buzz_db=-61.0), 620, "soft",
))

register_preset(_preset(
    "auth-kinescope-comedy-revue-1952", "Kinescope Comedy Revue", "1952", "broadcast",
    "A comedy revue caught from a bright studio monitor: blooming white shirts, visible CRT line texture, panchromatic film softness, modest kinescope grain, and brassy-band program squeezed through television and optical mono.",
    "Blooming whites and bright kinescope mono", ("1950s", "kinescope", "comedy", "revue"),
    _kinescope(contrast=1.22, lift=0.055, bloom=0.34, grain=0.4,
               flicker=0.11, weave=0.68),
    _kinescope_audio(high_hz=6000.0, buzz_db=-58.0), 610, "soft",
))

register_preset(_preset(
    "auth-googie-appliance-commercial-1958", "Googie Appliance Commercial", "1958", "film",
    "A pristine appliance spot on pastel Eastman color: turquoise-clean shadows, warm smiling skin, chrome product highlights, soft studio diffusion, exact fine-grain printing, and buoyant program sound retained as polished mono.",
    "Pastel Eastman color and chrome product shine", ("1950s", "commercial", "googie", "eastmancolor"),
    _color_print(profile="eastman_60s", stock_strength=0.7, exposure=0.05,
                 contrast=1.08, lift=0.035, knee=0.8, warmth=0.1, tint=-0.015,
                 shadow_tint="teal", shadow_amt=0.08, high_tint="cream",
                 high_amt=0.13, saturation=1.1, vibrance=0.12, soft=0.09,
                 diffusion=0.12, corner=0.06, flare=0.08,
                 optical_softness=0.04, registration=0.04, grain=0.25,
                 grain_size=1.4, chroma_grain=0.08, halation=0.24,
                 print_generations=1, fade=0.015, flicker=0.035, weave=0.3,
                 dust=0.035),
    _magnetic_audio(mic="broadcast_dynamic_1955", mono=1.0, generations=1,
                    alignment=0.04, compression=0.22, hiss_db=-68.0), 720, "sharp",
))

register_preset(_preset(
    "auth-civil-defense-instruction-film-1953", "Civil-Defense Instruction Film", "1953", "archive",
    "A stark institutional 16 mm release with panchromatic diagrams, hard midtone separation, coarse classroom grain, sober one-light printing, library wear, and solemn dynamic-microphone narration on a narrow optical stripe.",
    "Stark 16 mm diagrams, solemn speech", ("1950s", "civil-defense", "instructional", "16mm"),
    _mono_print(response="panchromatic", tint="silver", tint_amt=0.09,
                contrast=1.4, lift=0.015, knee=0.66, soft=0.07,
                diffusion=0.0, corner=0.12, grain=0.55, grain_size=2.0,
                grain_stock="doc_16", mottle=0.17, shadow_boost=0.2,
                halation=0.14, print_generations=2, acutance=0.38,
                flicker=0.12, weave=0.82, dust=0.24, scratch_count=1,
                scratch_rate=0.6),
    _optical_audio(mic="broadcast_dynamic_1955", mic_amount=0.74,
                   proximity=0.18, overload=0.18, self_noise=-60.0,
                   low_hz=140.0, high_hz=5100.0, rolloff="classroom_16mm",
                   cell_noise=-45.0, flutter=0.5, drive=1.7, ratio=4.6), 620, "sharp",
))

register_preset(_preset(
    "auth-rock-and-roll-jukebox-picture-1956", "Rock-and-Roll Jukebox Picture", "1956", "film",
    "A stage-hot jukebox release print with bright panchromatic performers, inky crowd shadows, pushed fine grain, crisp printer edge, and an overloaded dynamic microphone driving punchy optical mono.",
    "Stage-hot silver and overloaded jukebox mono", ("1950s", "rock-and-roll", "jukebox", "performance"),
    _mono_print(response="panchromatic", tint="silver", tint_amt=0.1,
                exposure=0.03, contrast=1.42, lift=0.01, knee=0.64, soft=0.06,
                diffusion=0.05, flare=0.08, grain=0.46, grain_size=1.7,
                grain_stock="push_process", shadow_boost=0.2, halation=0.24,
                print_generations=2, acutance=0.36, flicker=0.05, weave=0.45,
                dust=0.1, scratch_count=0),
    _optical_audio(mic="broadcast_dynamic_1955", mic_amount=0.88,
                   proximity=0.2, overload=0.42, self_noise=-58.0,
                   low_hz=70.0, high_hz=7200.0, rolloff="feature_1940s",
                   cell_noise=-49.0, flutter=0.3, drive=2.05, ratio=5.4,
                   room_mix=0.05), 700, "sharp",
))

register_preset(_preset(
    "auth-italian-peplum-spectacle-1959", "Italian Peplum Spectacle", "1959", "world",
    "A sun-baked Italian release print on economical Eastman color: ochre highlights, cyan-shadow separation, firm muscular contrast, visible 35 mm dye grain, soft duplication, and dubbed program dialogue on optical mono.",
    "Sun-baked Eastman, dubbed optical mono", ("1950s", "italian", "peplum", "eastmancolor"),
    _color_print(profile="eastman_60s", stock_strength=0.78, exposure=0.05,
                 contrast=1.24, lift=0.015, knee=0.7, warmth=0.2,
                 shadow_tint="teal", shadow_amt=0.17, high_tint="yellow",
                 high_amt=0.1, saturation=1.06, vibrance=0.08, soft=0.08,
                 diffusion=0.04, flare=0.12, optical_softness=0.12,
                 registration=0.12, layer_haze=0.07, grain=0.4,
                 grain_size=1.7, chroma_grain=0.14, mottle=0.1,
                 halation=0.28, print_generations=2, fade=0.06,
                 fade_profile="cyan_loss", flicker=0.06, weave=0.58,
                 dust=0.12, scratch_count=0),
    _optical_audio(mic="broadcast_dynamic_1955", mic_amount=0.54,
                   proximity=0.12, overload=0.15, low_hz=100.0, high_hz=6500.0,
                   rolloff="feature_1940s", cell_noise=-51.0, flutter=0.3,
                   drive=1.55, ratio=3.8, room_mix=0.1), 700, "soft",
))

register_preset(_preset(
    "auth-japanese-samuraiscope-1958", "Japanese SamuraiScope", "1958", "world",
    "A wide-format Japanese monochrome element rendered without a crop: taut panchromatic geometry, wind-textured midtones, crisp motion detail, fine-grain 35 mm silver, steady printing, and broad optical mono ambience.",
    "Taut wide-format silver and broad optical air", ("1950s", "japanese", "samurai", "widescreen"),
    _mono_print(response="panchromatic", tint="silver", tint_amt=0.08,
                contrast=1.34, lift=0.015, knee=0.68, soft=0.055,
                diffusion=0.015, corner=0.05, flare=0.06, grain=0.4,
                grain_size=1.6, shadow_boost=0.16, halation=0.16,
                print_generations=1, acutance=0.4, dmax=0.1, flicker=0.035,
                weave=0.3, dust=0.045, scratch_count=0),
    _optical_audio(mic="broadcast_dynamic_1955", mic_amount=0.4,
                   proximity=0.0, overload=0.06, self_noise=-68.0,
                   low_hz=70.0, high_hz=7400.0, rolloff="feature_1940s",
                   cell_noise=-58.0, flutter=0.16, drive=1.22, ratio=2.3,
                   room_mix=0.08), 720, "sharp",
))

register_preset(_preset(
    "auth-indian-studio-musical-melodrama-1955", "Indian Studio Musical Melodrama", "1955", "world",
    "A richly lit Indian studio print with jewel-toned costumes, warm skin, theatrical three-color separation, fine release grain, gentle optical diffusion, and playback vocals preserved through a full-bodied mono optical chain.",
    "Jewel studio color, full playback mono", ("1950s", "indian", "musical", "melodrama"),
    _color_print(profile="technicolor3", stock_strength=0.8, exposure=0.02,
                 contrast=1.18, lift=0.02, knee=0.72, warmth=0.18, tint=0.03,
                 shadow_tint="blue", shadow_amt=0.08, high_tint="cream",
                 high_amt=0.12, saturation=1.22, vibrance=0.14, soft=0.11,
                 diffusion=0.14, flare=0.12, optical_softness=0.1,
                 registration=0.12, layer_haze=0.05, grain=0.34,
                 grain_size=1.55, chroma_grain=0.12, halation=0.3,
                 print_generations=1, fade=0.025, flicker=0.05, weave=0.42,
                 dust=0.07),
    _optical_audio(mic="ribbon_1938", mic_amount=0.66, proximity=0.14,
                   overload=0.13, self_noise=-65.0, low_hz=70.0, high_hz=7200.0,
                   rolloff="feature_1940s", cell_noise=-55.0, flutter=0.22,
                   drive=1.45, ratio=3.2, room_mix=0.08), 720, "soft",
))

register_preset(_preset(
    "auth-soviet-color-ballet-film-1957", "Soviet Color Ballet Film", "1957", "world",
    "A formal Soviet ballet record on cool eastern color stock: luminous stage reds, disciplined blue shadows, soft optical-composite layers, fine 35 mm grain, long-density stability, and a carefully dubbed full-track mono master.",
    "Cool eastern color, full-track mono", ("1950s", "soviet", "ballet", "color"),
    _color_print(profile="orwo_east", stock_strength=0.82, exposure=0.02,
                 contrast=1.12, lift=0.025, knee=0.78, warmth=-0.03,
                 shadow_tint="blue", shadow_amt=0.14, high_tint="cream",
                 high_amt=0.08, saturation=1.08, vibrance=0.08, soft=0.1,
                 diffusion=0.1, corner=0.08, flare=0.08,
                 optical_softness=0.1, registration=0.1, layer_haze=0.05,
                 density_breath=0.04, grain=0.32, grain_size=1.5,
                 chroma_grain=0.11, halation=0.25, print_generations=1,
                 fade=0.02, flicker=0.04, weave=0.38, dust=0.055),
    _magnetic_audio(mic="ribbon_1938", mono=1.0, generations=1,
                    alignment=0.05, compression=0.26, hiss_db=-67.0), 720, "soft",
))

register_preset(_preset(
    "auth-cinerama-travel-spectacle-1958", "Cinerama Travel Spectacle", "1958", "world",
    "A premium multi-panel travel presentation translated without cropping or drawing seams: brilliant Eastman vistas, faint layer-registration divergence, exceptionally fine grain, steady density, and broad seven-channel-era magnetic character.",
    "Brilliant multi-panel color, magnetic air", ("1950s", "cinerama", "travelogue", "magnetic"),
    _color_print(profile="eastman_60s", stock_strength=0.76, exposure=0.04,
                 contrast=1.14, lift=0.018, knee=0.76, warmth=0.1,
                 shadow_tint="blue", shadow_amt=0.08, high_tint="cream",
                 high_amt=0.1, saturation=1.14, vibrance=0.12, soft=0.035,
                 diffusion=0.04, corner=0.02, flare=0.08,
                 optical_softness=0.06, registration=0.16, layer_haze=0.035,
                 density_breath=0.03, grain=0.24, grain_size=1.35,
                 chroma_grain=0.08, halation=0.22, print_generations=1,
                 fade=0.01, flicker=0.025, weave=0.24, dust=0.025),
    _magnetic_audio(mic="broadcast_dynamic_1955", mono=0.0, generations=1,
                    alignment=0.035, compression=0.2, hiss_db=-70.0,
                    width=1.24), 720, "sharp",
))

register_preset(_preset(
    "auth-kodachrome-family-vacation-1958", "Kodachrome Family Vacation", "1958", "film",
    "A sun-bright 8 mm vacation reel with saturated Kodachrome reds, dense blue skies, rounded simple-lens corners, fine reversal dye grain, mild exposure breathing, and continuous native source timing.",
    "Sun-bright Kodachrome and rounded 8 mm optics", ("1950s", "kodachrome", "vacation", "8mm"),
    _color_print(profile="kodachrome", stock_strength=0.96, exposure=0.06,
                 contrast=1.2, lift=0.025, knee=0.75, warmth=0.16,
                 shadow_tint="blue", shadow_amt=0.08, high_tint="cream",
                 high_amt=0.1, saturation=1.24, vibrance=0.12, soft=0.16,
                 diffusion=0.06, corner=0.42, flare=0.14,
                 optical_softness=0.03, registration=0.035, grain=0.24,
                 grain_size=1.0, chroma_grain=0.08, grain_stock="super8",
                 layers="reversal", mottle=0.08, halation=0.3,
                 print_generations=0, fade=0.03, flicker=0.075, weave=0.65,
                 dust=0.06, scratch_count=0),
    _silent_program_audio(high_hz=11500.0, mono=0.68, room_mix=0.055), 520, "soft",
))

register_preset(_preset(
    "auth-atomic-age-industrial-futurism-1957", "Atomic-Age Industrial Futurism", "1957", "archive",
    "A spotless corporate-future print with chrome machinery, turquoise-clean shadows, warm demonstration skin, precise Eastman separation, fine grain, and authoritative dynamic-microphone narration on polished magnetic mono.",
    "Chrome machinery, turquoise shadows", ("1950s", "atomic-age", "industrial", "futurism"),
    _color_print(profile="eastman_60s", stock_strength=0.72, exposure=0.04,
                 contrast=1.16, lift=0.02, knee=0.75, warmth=0.08,
                 shadow_tint="teal", shadow_amt=0.14, high_tint="cream",
                 high_amt=0.1, saturation=1.12, vibrance=0.1, soft=0.055,
                 diffusion=0.04, corner=0.04, flare=0.08,
                 optical_softness=0.04, registration=0.04, layer_haze=0.02,
                 grain=0.27, grain_size=1.4, chroma_grain=0.08,
                 halation=0.24, print_generations=1, fade=0.01,
                 flicker=0.03, weave=0.28, dust=0.035),
    _magnetic_audio(mic="broadcast_dynamic_1955", mono=1.0, generations=1,
                    alignment=0.04, compression=0.24, hiss_db=-68.0), 720, "sharp",
))

register_preset(_preset(
    "auth-pastel-single-camera-sitcom-1959", "Pastel Single-Camera Sitcom", "1959", "broadcast",
    "A clean single-camera comedy print with pastel Eastman interiors, warm flattering fill, creamy highlight rolloff, restrained 35 mm grain, stable release printing, and gently compressed full-track mono.",
    "Pastel Eastman, gentle full-track mono", ("1950s", "sitcom", "single-camera", "eastmancolor"),
    _color_print(profile="eastman_60s", stock_strength=0.62, exposure=0.05,
                 contrast=1.02, lift=0.045, knee=0.84, warmth=0.15,
                 high_tint="cream", high_amt=0.16, saturation=0.96,
                 vibrance=0.08, soft=0.1, diffusion=0.15, corner=0.06,
                 flare=0.1, optical_softness=0.04, registration=0.035,
                 layer_haze=0.025, grain=0.25, grain_size=1.4,
                 chroma_grain=0.08, halation=0.25, print_generations=1,
                 fade=0.015, flicker=0.025, weave=0.26, dust=0.03),
    _magnetic_audio(mic="broadcast_dynamic_1955", mono=1.0, generations=1,
                    alignment=0.035, compression=0.22, hiss_db=-69.0), 720, "soft",
))

register_preset(_preset(
    "auth-french-couture-newsreel-1957", "French Couture Newsreel", "1957", "world",
    "An elegant fashion newsreel print with pearly panchromatic skin, flashbulb halation, crisp runway midtones, fine reporter grain, light circulation wear, and clipped sophisticated narration on optical mono.",
    "Pearly runway silver and flashbulb halation", ("1950s", "french", "couture", "newsreel"),
    _mono_print(response="panchromatic", tint="silver", tint_amt=0.13,
                exposure=0.04, contrast=1.3, lift=0.025, knee=0.68, soft=0.1,
                diffusion=0.12, corner=0.09, flare=0.14, grain=0.4,
                grain_size=1.65, grain_stock="newsreel_35", mottle=0.1,
                halation=0.36, print_generations=2, acutance=0.3,
                flicker=0.065, weave=0.48, dust=0.14, scratch_count=0),
    _optical_audio(mic="broadcast_dynamic_1955", mic_amount=0.66,
                   proximity=0.12, overload=0.14, self_noise=-61.0,
                   low_hz=100.0, high_hz=6200.0, rolloff="feature_1940s",
                   cell_noise=-50.0, flutter=0.32, drive=1.55, ratio=3.8), 680, "soft",
))
