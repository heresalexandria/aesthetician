"""Source-preserving audiovisual looks from the 2000s and 2010s.

These presets model acquisition, carrier, transfer, and playback while
preserving source geometry, timing, picture content, and the complete supplied
soundtrack.
"""

from __future__ import annotations

from typing import Any

from ..engine.presets import ChainSpec, Preset, Variant, register_preset


def _variants(video: ChainSpec, audio: ChainSpec) -> list[Variant]:
    """Two non-editorial states assembled only from effects already present."""
    v = {eid: params for eid, params in video}
    a = {eid: params for eid, params in audio}
    clean_v: dict[str, Any] = {}
    copy_v: dict[str, Any] = {}
    clean_a: dict[str, Any] = {}
    copy_a: dict[str, Any] = {}

    if "grain" in v:
        clean_v["grain.amount"] = max(0.16, float(v["grain"].get("amount", 0.3)) * 0.65)
        copy_v["grain.amount"] = min(0.65, float(v["grain"].get("amount", 0.3)) * 1.25)
    if "exposure_auto" in v:
        clean_v["exposure_auto.agc_gain_noise"] = max(
            0.05, float(v["exposure_auto"].get("agc_gain_noise", 0.3)) * 0.55
        )
        copy_v["exposure_auto.agc_gain_noise"] = min(
            0.8, float(v["exposure_auto"].get("agc_gain_noise", 0.3)) * 1.3
        )
    if "codec_era" in v:
        codec = v["codec_era"]
        crf = int(codec.get("crf", -1))
        if codec.get("codec") == "h264" and crf >= 0:
            clean_v["codec_era.crf"] = max(0, crf - 3)
            copy_v["codec_era.crf"] = min(51, crf + 5)
        else:
            kbps = int(codec.get("kbps", 900))
            clean_v["codec_era.kbps"] = min(8000, max(kbps + 1, int(kbps * 1.65)))
            copy_v["codec_era.kbps"] = max(40, int(kbps * 0.62))
    if "vhs" in v:
        mode = str(v["vhs"].get("mode", "sp"))
        cap = {"sp": 0.6, "lp": 0.42, "ep": 0.3}.get(mode, 0.6)
        clean_v["vhs.luma_noise"] = 0.12
        clean_v["vhs.chroma_noise"] = 0.14
        copy_v["vhs.luma_noise"] = min(cap, float(v["vhs"].get("luma_noise", 0.2)) * 1.3)
        copy_v["vhs.chroma_noise"] = min(cap, float(v["vhs"].get("chroma_noise", 0.2)) * 1.3)
    if "a_tape_hiss" in a:
        clean_a["a_tape_hiss.level_db"] = -58.0
        copy_a["a_tape_hiss.level_db"] = -42.0
    if "a_codec_mp3" in a:
        clean_a["a_codec_mp3.kbps"] = 128
        copy_a["a_codec_mp3.kbps"] = 32
    if "a_codec_aac" in a:
        kbps = int(a["a_codec_aac"].get("kbps", 128))
        mono = bool(a["a_codec_aac"].get("mono", False))
        clean_a["a_codec_aac.kbps"] = max(kbps, 96 if mono else 192)
        copy_a["a_codec_aac.kbps"] = max(24, int(kbps * 0.55))
    if "a_optical_track" in a:
        clean_a["a_optical_track.cell_noise"] = -60.0
        copy_a["a_optical_track.cell_noise"] = -43.0

    return [
        Variant(
            "clean-master",
            "Clean Master",
            "The best surviving generation: the same capture signature with the carrier held in spec.",
            video=clean_v,
            audio=clean_a,
        ),
        Variant(
            "period-copy",
            "Period Copy",
            "A routine contemporary copy: a little less bandwidth and a little more medium showing through.",
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


def _dv(
    *,
    contrast: float = 1.06,
    lift: float = 0.02,
    warmth: float = 0.0,
    tint: float = 0.0,
    sat: float = 1.0,
    diffusion: float = 0.0,
    soft: float = 0.08,
    corner: float = 0.12,
    focus: float = 0.08,
    gain_noise: float = 0.28,
    wb: float = 0.22,
    sharpen: float = 0.45,
    blocks: float = 0.12,
) -> ChainSpec:
    return [
        ("tone", {"contrast": contrast, "lift": lift, "knee": 0.86}),
        ("balance", {"warmth": warmth, "tint": tint}),
        ("saturation", {"amount": sat, "vibrance": 0.04}),
        ("optics", {"diffusion": diffusion, "soft_focus": soft, "corner_softness": corner,
                     "focus_drift": focus}),
        ("exposure_auto", {"lag": 0.72, "overshoot": 0.24, "max_boost": 3.5,
                           "agc_gain_noise": gain_noise, "wb_amount": wb, "iris_step": 0.14}),
        ("chroma_dv", {"ratio": "4:1:1", "edge_sharpen": sharpen, "dct_blocks": blocks}),
        ("interlace", {"field_order": "bff", "combing": 0.42, "twitter": 0.14}),
    ]


def _web(
    *,
    codec: str = "flv1",
    kbps: int = 320,
    res: str = "240p",
    gop: int = 90,
    contrast: float = 1.06,
    warmth: float = 0.0,
    sat: float = 0.96,
    gain_noise: float = 0.42,
    wb_pump: float = 0.4,
    sharpen: float = 0.45,
) -> ChainSpec:
    return [
        ("tone", {"contrast": contrast, "lift": 0.025, "knee": 0.84}),
        ("balance", {"warmth": warmth}),
        ("saturation", {"amount": sat}),
        ("optics", {"soft_focus": 0.12, "corner_softness": 0.16, "focus_drift": 0.1}),
        ("exposure_auto", {"lag": 0.9, "overshoot": 0.3, "max_boost": 4.0,
                           "agc_gain_noise": gain_noise, "wb_amount": 0.32, "flicker_60hz": 0.1}),
        ("auto_color", {"wb_pump": wb_pump, "level_pump": 0.3, "lag_s": 0.9}),
        ("chroma_dv", {"ratio": "4:2:0", "edge_sharpen": sharpen, "dct_blocks": 0.2}),
        ("codec_era", {"codec": codec, "kbps": kbps, "res": res, "gop": gop,
                       "passes": 1, "denoise_pre": 0.15}),
    ]


def _digicam(
    *,
    warmth: float = 0.08,
    tint: float = 0.0,
    sat: float = 1.15,
    contrast: float = 1.12,
    gain_noise: float = 0.42,
    soft: float = 0.04,
) -> ChainSpec:
    return [
        ("tone", {"exposure": 0.12, "contrast": contrast, "lift": 0.01, "knee": 0.78}),
        ("balance", {"warmth": warmth, "tint": tint}),
        ("saturation", {"amount": sat, "vibrance": 0.12}),
        ("optics", {"soft_focus": soft, "corner_softness": 0.2, "chromatic_aberration": 0.7,
                     "focus_drift": 0.12, "veiling_flare": 0.1}),
        ("exposure_auto", {"lag": 0.55, "overshoot": 0.35, "max_boost": 4.5,
                           "agc_gain_noise": gain_noise, "wb_amount": 0.4, "iris_step": 0.24}),
        ("chroma_dv", {"ratio": "4:2:0", "edge_sharpen": 0.75, "dct_blocks": 0.18}),
        ("codec_era", {"codec": "mjpeg", "kbps": 2600, "res": "480p", "gop": 1}),
    ]


def _hd(
    *,
    contrast: float = 1.08,
    warmth: float = 0.0,
    tint: float = 0.0,
    sat: float = 1.04,
    diffusion: float = 0.06,
    soft: float = 0.04,
    sharpen: float = 0.42,
    kbps: int = 6000,
    interlaced: bool = True,
) -> ChainSpec:
    chain: ChainSpec = [
        ("tone", {"contrast": contrast, "lift": 0.012, "knee": 0.88}),
        ("balance", {"warmth": warmth, "tint": tint}),
        ("saturation", {"amount": sat, "vibrance": 0.08}),
        ("optics", {"diffusion": diffusion, "soft_focus": soft, "corner_softness": 0.08}),
        ("chroma_dv", {"ratio": "4:2:0", "edge_sharpen": sharpen, "dct_blocks": 0.04}),
        ("codec_era", {"codec": "mpeg2video", "kbps": kbps, "res": "native", "gop": 15,
                       "field_mode": "interlaced_tff" if interlaced else "progressive",
                       "denoise_pre": 0.12}),
    ]
    if interlaced:
        chain.append(("interlace", {"field_order": "tff", "combing": 0.32, "twitter": 0.1}))
    return chain


def _film_di(
    *,
    contrast: float = 1.08,
    warmth: float = 0.08,
    tint: float = 0.0,
    shadow_tint: str = "none",
    shadow_amt: float = 0.0,
    sat: float = 0.98,
    diffusion: float = 0.08,
    soft: float = 0.05,
    grain: float = 0.24,
) -> ChainSpec:
    return [
        ("stock", {"profile": "vision_90s", "strength": 0.45}),
        ("tone", {"contrast": contrast, "lift": 0.015, "knee": 0.87}),
        ("balance", {"warmth": warmth, "tint": tint, "shadow_tint": shadow_tint,
                     "shadow_amt": shadow_amt}),
        ("saturation", {"amount": sat, "vibrance": 0.08}),
        ("optics", {"diffusion": diffusion, "soft_focus": soft, "corner_softness": 0.08,
                     "veiling_flare": 0.08}),
        ("grain", {"amount": grain, "size": 1.55, "size_ref": "output", "roughness": 0.42,
                   "chroma_grain": 0.12, "stock": "fine_35", "layers": "color_neg"}),
        ("halation", {"strength": 0.22, "threshold": 0.78, "radius": 0.04,
                      "tint": "red_orange"}),
    ]


def _modern_capture(
    *,
    contrast: float = 1.04,
    warmth: float = 0.0,
    tint: float = 0.0,
    sat: float = 1.0,
    distortion: float = 0.0,
    corner: float = 0.04,
    gain_noise: float = 0.12,
    wb: float = 0.18,
    sharpen: float = 0.35,
    kbps: int = 5000,
    crf: int = 21,
    res: str = "native",
) -> ChainSpec:
    return [
        ("tone", {"contrast": contrast, "lift": 0.008, "knee": 0.9}),
        ("balance", {"warmth": warmth, "tint": tint}),
        ("saturation", {"amount": sat, "vibrance": 0.05}),
        ("optics", {"distortion": distortion, "corner_softness": corner,
                     "chromatic_aberration": 0.35, "veiling_flare": 0.05}),
        ("exposure_auto", {"lag": 0.48, "overshoot": 0.16, "max_boost": 3.0,
                           "agc_gain_noise": gain_noise, "wb_amount": wb, "iris_step": 0.08}),
        ("chroma_dv", {"ratio": "4:2:0", "edge_sharpen": sharpen, "dct_blocks": 0.03}),
        ("codec_era", {"codec": "h264", "kbps": kbps, "crf": crf, "res": res,
                       "gop": 60, "denoise_pre": 0.08}),
    ]


def _surveillance(
    *,
    mono: bool = False,
    infrared: bool = False,
    distortion: float = -0.16,
    kbps: int = 750,
    gain_noise: float = 0.55,
    res: str = "360p",
) -> ChainSpec:
    chain: ChainSpec = []
    if mono:
        chain.append(("mono", {"response": "modern", "tint": "phosphor_green" if infrared else "silver",
                               "tint_amt": 0.14 if infrared else 0.08}))
    chain.extend([
        ("tone", {"contrast": 1.12, "lift": 0.025, "knee": 0.78}),
        ("balance", {"warmth": -0.08 if not infrared else 0.0,
                     "shadow_tint": "green" if infrared else "blue", "shadow_amt": 0.12}),
        ("saturation", {"amount": 0.78 if not mono else 1.0}),
        ("optics", {"distortion": distortion, "corner_softness": 0.28,
                     "chromatic_aberration": 0.8, "soft_focus": 0.09}),
        ("exposure_auto", {"lag": 0.62, "overshoot": 0.34, "max_boost": 6.0,
                           "agc_gain_noise": gain_noise, "wb_amount": 0.3, "iris_step": 0.25}),
        ("chroma_dv", {"ratio": "4:2:0", "edge_sharpen": 0.65, "dct_blocks": 0.18}),
        ("codec_era", {"codec": "h264", "kbps": kbps, "res": res, "gop": 120,
                       "denoise_pre": 0.25}),
    ])
    return chain


def _dv_audio(*, high: float = 15500.0, mono: float = 0.0, agc: float = 0.42) -> ChainSpec:
    chain: ChainSpec = [
        ("a_historical_mic", {"profile": "camcorder_1994", "amount": 0.5,
                              "proximity": 0.05, "overload": 0.18,
                              "self_noise_db": -58.0, "handling": 0.06}),
        ("a_bandlimit", {"low_hz": 70.0, "high_hz": high}),
    ]
    if mono:
        chain.append(("a_mono", {"amount": mono}))
    chain.extend([
        ("a_agc", {"target_db": -17.0, "max_gain_db": 10.0, "attack_ms": 35.0,
                   "release_ms": 800.0, "amount": agc}),
        ("a_compressor", {"threshold_db": -18.0, "ratio": 2.4, "attack_ms": 6.0,
                          "release_ms": 160.0, "knee_db": 5.0}),
    ])
    return chain


def _web_audio(
    *, high: float = 7500.0, kbps: int = 48, mono: bool = True,
    room: float = 0.0, codec: str = "mp3",
) -> ChainSpec:
    chain: ChainSpec = []
    if room:
        chain.append(("a_room", {"size": 0.7, "decay_s": 0.32, "damp": 0.7, "mix": room}))
    chain.extend([
        ("a_historical_mic", {"profile": "electret_1985", "amount": 0.48,
                              "proximity": 0.04, "overload": 0.14,
                              "self_noise_db": -57.0, "handling": 0.0}),
        ("a_bandlimit", {"low_hz": 120.0, "high_hz": high}),
    ])
    if mono:
        chain.append(("a_mono", {"amount": 1.0}))
    chain.extend([
        ("a_agc", {"target_db": -15.0, "max_gain_db": 14.0, "attack_ms": 24.0,
                   "release_ms": 650.0, "amount": 0.65}),
        ("a_compressor", {"threshold_db": -20.0, "ratio": 3.2, "attack_ms": 4.0,
                          "release_ms": 130.0, "knee_db": 4.0}),
    ])
    chain.append(("a_codec_aac" if codec == "aac" else "a_codec_mp3",
                  {"kbps": kbps, "mono": mono}))
    return chain


def _broadcast_audio(
    *, mono: bool = False, high: float = 15000.0, kbps: int = 128,
    mic: str | None = None, codec: str = "mp3",
) -> ChainSpec:
    chain: ChainSpec = []
    if mic:
        chain.append(("a_historical_mic", {"profile": mic, "amount": 0.38,
                                            "proximity": 0.1, "overload": 0.12,
                                            "self_noise_db": -64.0, "handling": 0.02}))
    chain.append(("a_bandlimit", {"low_hz": 55.0, "high_hz": high}))
    if mono:
        chain.append(("a_mono", {"amount": 1.0}))
    chain.extend([
        ("a_compressor", {"threshold_db": -22.0, "ratio": 4.5, "attack_ms": 3.0,
                          "release_ms": 120.0, "knee_db": 5.0, "makeup_db": 2.0}),
    ])
    chain.append(("a_codec_aac" if codec == "aac" else "a_codec_mp3",
                  {"kbps": kbps, "mono": mono}))
    return chain


def _evidence_audio(
    *, high: float = 7000.0, kbps: int = 64,
    mic: str = "camcorder_1994",
) -> ChainSpec:
    return [
        ("a_historical_mic", {"profile": mic, "amount": 0.62,
                              "proximity": 0.0, "overload": 0.22,
                              "self_noise_db": -55.0, "handling": 0.1}),
        ("a_bandlimit", {"low_hz": 150.0, "high_hz": high}),
        ("a_mono", {"amount": 1.0}),
        ("a_agc", {"target_db": -15.0, "max_gain_db": 18.0, "attack_ms": 18.0,
                   "release_ms": 1050.0, "amount": 0.8}),
        ("a_compressor", {"threshold_db": -19.0, "ratio": 3.5, "attack_ms": 4.0,
                          "release_ms": 170.0}),
        ("a_codec_aac", {"kbps": kbps, "mono": True}),
    ]


# 172-188: missing 2000s acquisition and delivery formats.  The v0.25
# library already covers 171, 174-175, 178, 180-181, and 184.
register_preset(_preset(
    "auth-emo-performance-2005", "Emo Performance Video", "2005", "digital",
    "A cool early-digital master with clipped practicals, cyan-biased shadows, crunchy DV chroma, and dense but intact program audio pressed against a broadcast limiter.",
    "Cool DV chroma and clipped practical light", ("00s", "music-video", "dv"),
    _dv(contrast=1.18, lift=0.005, warmth=-0.18, tint=-0.08, sat=0.82, diffusion=0.04,
        soft=0.05, gain_noise=0.3, sharpen=0.7, blocks=0.18),
    _dv_audio(high=15000.0, agc=0.28), proc_height=550, upscale="sharp",
))

register_preset(_preset(
    "auth-early-youtube-webcam-2006", "Early YouTube Webcam", "2006", "digital",
    "A USB webcam compressed twice before broadband: soft fixed-focus glass, monitor-lit exposure pumping, 240-line FLV macroblocks, and narrow mono MP3 without synthetic dropouts.",
    "240-line FLV, pumping webcam exposure", ("00s", "webcam", "web-video"),
    _web(codec="flv1", kbps=220, res="240p", gop=120, contrast=1.08, sat=0.86,
         gain_noise=0.56, wb_pump=0.58, sharpen=0.3),
    _web_audio(high=6500.0, kbps=32, mono=True, room=0.18),
))

register_preset(_preset(
    "auth-paranormal-investigation-dv-2004", "Paranormal Investigation DV", "2004", "digital",
    "Consumer DV after the lights go out: green-leaning monochrome, gain-raised shadows, soft infrared-style optics, autofocus breathing, interlaced edges, and a searching camera mic.",
    "Green low-light DV and gain-raised shadows", ("00s", "night-vision", "dv"),
    [("mono", {"response": "modern", "tint": "phosphor_green", "tint_amt": 0.32})]
    + _dv(contrast=1.18, lift=0.025, warmth=-0.08, sat=1.0, soft=0.2, corner=0.3,
          focus=0.48, gain_noise=0.68, wb=0.1, sharpen=0.5, blocks=0.2),
    _dv_audio(high=10500.0, mono=1.0, agc=0.82), proc_height=540, upscale="soft",
))

register_preset(_preset(
    "auth-embedded-war-journalism-2003", "Embedded War Journalism", "2003", "digital",
    "A field MiniDV chain in dust-bright daylight: conservative color, hard electronic acutance, rapid iris correction, modest interlace combing, and aggressively managed location audio.",
    "Field MiniDV, hard acutance, riding AGC", ("00s", "news", "minidv"),
    _dv(contrast=1.12, lift=0.005, warmth=0.12, sat=0.88, soft=0.02, corner=0.08,
        focus=0.12, gain_noise=0.24, wb=0.3, sharpen=0.85, blocks=0.16),
    _dv_audio(high=12500.0, mono=0.7, agc=0.78), proc_height=550, upscale="sharp",
))

register_preset(_preset(
    "auth-food-network-studio-2005", "Food-Network Studio Show", "2005", "broadcast",
    "Warm tungsten-biased studio video with clean early-HD edges, gently polished highlights, restrained 4:2:0 chroma, interlaced delivery, and close lav audio under network compression.",
    "Warm early HD with restrained 4:2:0 color", ("00s", "food-tv", "studio"),
    _hd(contrast=1.06, warmth=0.22, tint=0.03, sat=1.12, diffusion=0.08, soft=0.03,
        sharpen=0.34, kbps=6500, interlaced=True),
    _broadcast_audio(mono=False, high=16000.0, kbps=128, mic="lavalier_1972"),
))

register_preset(_preset(
    "auth-machinima-web-series-2005", "Machinima Web Series", "2005", "digital",
    "A real-time render after desktop capture and web encoding: crisp synthetic edges softened by 4:2:0 sampling, 360-line MPEG-4 macroblocks, and narrow compressed dialogue left in sync.",
    "Synthetic edges through 360-line MPEG-4", ("00s", "machinima", "web-series"),
    [
        ("tone", {"contrast": 1.12, "lift": 0.025, "knee": 0.84}),
        ("saturation", {"amount": 1.05}),
        ("chroma_dv", {"ratio": "4:2:0", "edge_sharpen": 1.0, "dct_blocks": 0.2}),
        ("codec_era", {"codec": "mpeg4", "kbps": 420, "res": "360p", "gop": 120,
                       "passes": 1, "denoise_pre": 0.15}),
    ],
    _web_audio(high=7500.0, kbps=48, mono=True, room=0.0),
))

register_preset(_preset(
    "auth-j-horror-digital-video-2002", "J-Horror Digital Video", "2002", "digital",
    "Cool fluorescent MiniDV with lifted low-light blacks, cyan-green shadow contamination, subdued color, electronic edge enhancement, and clean tension from the camera's own narrow stereo track.",
    "Cool fluorescent DV and lifted noisy blacks", ("00s", "j-horror", "minidv"),
    _dv(contrast=1.08, lift=0.04, warmth=-0.2, tint=-0.14, sat=0.68, soft=0.1,
        corner=0.22, focus=0.2, gain_noise=0.58, wb=0.46, sharpen=0.58, blocks=0.12),
    _dv_audio(high=13500.0, mono=0.2, agc=0.52), proc_height=540, upscale="soft",
))

register_preset(_preset(
    "auth-political-campaign-spot-2008", "Political Campaign Spot", "2008", "broadcast",
    "A late-decade digital intermediate with controlled flag-blue shadows, firm broadcast contrast, polished skin highlights, conservative grain, and a television loudness chain on the untouched program.",
    "Flag-blue DI polish and broadcast density", ("00s", "campaign", "digital-intermediate"),
    _film_di(contrast=1.16, warmth=0.06, tint=0.02, shadow_tint="blue", shadow_amt=0.18,
             sat=0.94, diffusion=0.08, grain=0.18),
    _broadcast_audio(mono=False, high=16000.0, kbps=128),
))

register_preset(_preset(
    "auth-live-truck-local-news-2004", "Live-Truck Local News", "2004", "broadcast",
    "A Betacam-to-digital live path under a hard camera light: clipped highlights, cooler shadows, interlaced 4:2:0 edges, economical MPEG-2, and firmly limited field audio without simulated outages.",
    "Hard camera light, interlaced live-truck path", ("00s", "local-news", "live-truck"),
    _hd(contrast=1.16, warmth=-0.06, tint=-0.03, sat=0.94, diffusion=0.02, soft=0.02,
        sharpen=0.72, kbps=3600, interlaced=True),
    _broadcast_audio(mono=True, high=10500.0, kbps=96, mic="shotgun_1975"),
    proc_height=580, upscale="sharp",
))

register_preset(_preset(
    "auth-nu-metal-performance-2001", "Nu-Metal Performance Promo", "2001", "film",
    "A hard green-cyan 16mm-to-DI finish: push-processed shadow grain, clipped practical highlights, wide-angle chromatic stress, and dense mastered audio kept sample-for-sample intact.",
    "Green-cyan push grain and stressed optics", ("00s", "music-video", "16mm"),
    [
        ("stock", {"profile": "vision_90s", "strength": 0.62}),
        ("tone", {"contrast": 1.2, "lift": 0.0, "knee": 0.78}),
        ("balance", {"warmth": -0.2, "tint": -0.18, "shadow_tint": "green", "shadow_amt": 0.3}),
        ("saturation", {"amount": 0.78, "vibrance": 0.12}),
        ("optics", {"distortion": -0.07, "chromatic_aberration": 1.15, "soft_focus": 0.03,
                     "veiling_flare": 0.1}),
        ("grain", {"amount": 0.17, "size": 1.05, "roughness": 0.46, "chroma_grain": 0.055,
                   "stock": "push_process", "layers": "color_neg", "shadow_boost": 0.18}),
        ("halation", {"strength": 0.22, "threshold": 0.72, "radius": 0.04, "tint": "red"}),
        ("gate_weave", {"amount": 0.38, "hz": 0.65, "rotation": 0.012, "splice_bump": 0.0}),
    ],
    _broadcast_audio(mono=False, high=17000.0, kbps=128), proc_height=620, upscale="sharp",
))

register_preset(_preset(
    "auth-romcom-digital-intermediate-2006", "Glossy Romantic-Comedy Digital Intermediate", "2006", "film",
    "A clean 35mm scan finished in the DI suite: warm skin-biased mids, restrained cyan in the shadows, creamy highlight rolloff, fine color-negative grain, and transparent theatrical audio control.",
    "Warm skin, cyan shadows, creamy DI rolloff", ("00s", "romantic-comedy", "di"),
    _film_di(contrast=1.04, warmth=0.2, tint=0.03, shadow_tint="teal", shadow_amt=0.12,
             sat=1.04, diffusion=0.16, soft=0.06, grain=0.2),
    [("a_bandlimit", {"low_hz": 35.0, "high_hz": 19000.0}),
     ("a_compressor", {"threshold_db": -16.0, "ratio": 1.8, "attack_ms": 12.0,
                       "release_ms": 220.0, "knee_db": 8.0})],
))

# 190: early x264 fansub delivery, with the source's own picture left intact.
# Subtitles are presentation/content and deliberately do not belong in this
# acquisition-and-carrier collection.
register_preset(_preset(
    "auth-anime-web-fansub-encode-2006", "Anime Web-Fansub Encode", "2006", "digital",
    "An early x264 fansub carrier without added subtitles: oversharpened 4:2:0 line art, long-GOP low-bitrate H.264 mosquito texture, restrained chroma, and compact stereo AAC while every supplied frame remains in place.",
    "Early x264 line bite and compact stereo AAC", ("00s", "anime", "fansub", "web-video"),
    [
        ("tone", {"contrast": 1.06, "lift": 0.012, "knee": 0.86}),
        ("balance", {"warmth": -0.03, "tint": 0.0}),
        ("saturation", {"amount": 0.94, "vibrance": 0.04}),
        ("chroma_dv", {"ratio": "4:2:0", "edge_sharpen": 1.18, "dct_blocks": 0.16}),
        ("codec_era", {"codec": "h264", "kbps": 720, "res": "480p", "gop": 240,
                       "denoise_pre": 0.12}),
    ],
    [
        ("a_bandlimit", {"low_hz": 55.0, "high_hz": 16500.0}),
        ("a_compressor", {"threshold_db": -18.0, "ratio": 2.0, "attack_ms": 8.0,
                          "release_ms": 180.0, "knee_db": 6.0}),
        ("a_codec_aac", {"kbps": 96, "mono": False}),
    ],
))

# 191-200: missing 2010s sensors, streaming, surveillance, and social delivery.
register_preset(_preset(
    "auth-dslr-indie-naturalism-2012", "DSLR Indie Naturalism", "2012", "modern",
    "A large-sensor H.264 DSLR image with gently clipped highlights, warm available-light color, shallow-lens softness, fine chroma subsampling, restrained sensor noise, and clean dual-system audio in a transparent AAC delivery.",
    "Warm large-sensor H.264 with soft rolloff", ("10s", "dslr", "independent"),
    _modern_capture(contrast=1.02, warmth=0.14, tint=0.02, sat=0.94, corner=0.09,
                    gain_noise=0.16, wb=0.16, sharpen=0.22, kbps=6200, crf=20),
    [("a_bandlimit", {"low_hz": 40.0, "high_hz": 19000.0}),
     ("a_compressor", {"threshold_db": -18.0, "ratio": 1.8, "attack_ms": 12.0,
                       "release_ms": 240.0, "knee_db": 8.0}),
     ("a_codec_aac", {"kbps": 192, "mono": False})],
))

register_preset(_preset(
    "auth-gopro-action-footage-2014", "GoPro Action Footage", "2014", "modern",
    "A first-wave action camera: barrel-heavy ultra-wide optics, hard electronic sharpness, clipped blue skies, small-sensor autoexposure, dense 4:2:0 H.264, and wind-exposed AAC camera-mic capture.",
    "Ultra-wide barrel warp and hard H.264 edges", ("10s", "action-camera", "gopro"),
    _modern_capture(contrast=1.14, warmth=-0.05, tint=-0.02, sat=1.14, distortion=-0.24,
                    corner=0.2, gain_noise=0.18, wb=0.26, sharpen=0.92, kbps=7000,
                    crf=23),
    [
        ("a_historical_mic", {"profile": "electret_1985", "amount": 0.42,
                              "proximity": 0.0, "overload": 0.22,
                              "self_noise_db": -60.0, "handling": 0.08}),
        ("a_bandlimit", {"low_hz": 80.0, "high_hz": 14000.0}),
        ("a_agc", {"target_db": -17.0, "max_gain_db": 8.0, "attack_ms": 30.0,
                   "release_ms": 700.0, "amount": 0.35}),
        ("a_compressor", {"threshold_db": -18.0, "ratio": 2.2, "attack_ms": 6.0,
                          "release_ms": 160.0, "knee_db": 5.0}),
        ("a_codec_aac", {"kbps": 128, "mono": False}),
    ],
))

register_preset(_preset(
    "auth-body-camera-evidence-2017", "Body-Camera Evidence Footage", "2017", "digital",
    "A chest-worn evidence camera without editorial overlays: strong barrel distortion, edge softness, rolling small-sensor exposure, aggressive 360-line long-GOP H.264, and heavily managed mono AAC speech.",
    "Chest-camera barrel warp and evidence codec", ("10s", "body-camera", "evidence"),
    _surveillance(mono=False, infrared=False, distortion=-0.22, kbps=900, gain_noise=0.48,
                  res="360p"),
    _evidence_audio(high=7500.0, kbps=64),
))

register_preset(_preset(
    "auth-dashcam-archive-2015", "Dashcam Archive Clip", "2015", "digital",
    "A windshield recorder shorn of its date graphic: modest wide-angle bowing, clipped lamps, vibration-like electronic edge stress, small-sensor gain, long-GOP 360-line H.264, and thin mono AAC cabin audio.",
    "Wide windshield optics, long-GOP road video", ("10s", "dashcam", "archive"),
    _surveillance(mono=False, infrared=False, distortion=-0.12, kbps=1200, gain_noise=0.38,
                  res="360p"),
    _evidence_audio(high=6500.0, kbps=64),
))

register_preset(_preset(
    "auth-doorbell-camera-night-2018", "Doorbell-Camera Night Capture", "2018", "digital",
    "A porch camera after its infrared cut filter moves aside: cool near-monochrome response, pronounced fisheye bowing, noisy gain-raised shadows, block-heavy H.264 GOPs, and narrow mono AAC intercom sound.",
    "Infrared fisheye, block-heavy night capture", ("10s", "doorbell", "night-vision"),
    _surveillance(mono=True, infrared=True, distortion=-0.27, kbps=520, gain_noise=0.72,
                  res="360p"),
    _evidence_audio(high=4800.0, kbps=32),
))

register_preset(_preset(
    "auth-streaming-true-crime-2017", "Streaming True-Crime Documentary", "2017", "modern",
    "A cool contemporary documentary finish: restrained saturation, blue-green shadow separation, clinical microcontrast, almost invisible fine grain, and a measured H.264/AAC streaming encode on the original program.",
    "Cool clinical grade, restrained fine grain", ("10s", "documentary", "streaming"),
    _film_di(contrast=1.12, warmth=-0.1, tint=-0.04, shadow_tint="teal", shadow_amt=0.2,
             sat=0.74, diffusion=0.03, soft=0.02, grain=0.16)
    + [("codec_era", {"codec": "h264", "crf": 21, "res": "native", "gop": 120,
                       "denoise_pre": 0.04})],
    _broadcast_audio(mono=False, high=17500.0, kbps=160, codec="aac"),
))

register_preset(_preset(
    "auth-square-social-filter-2013", "Square-Format Social Filter", "2013", "modern",
    "The color science of an early square-photo app applied without changing source geometry: lifted blacks, faded contrast, warm cream highlights, cyan-leaning shadows, restrained saturation, and a lightly recompressed H.264/AAC mobile encode.",
    "Lifted blacks and warm early-social fade", ("10s", "social", "filter"),
    [
        ("tone", {"contrast": 0.82, "gamma": 0.94, "lift": 0.075, "knee": 0.8}),
        ("balance", {"warmth": 0.16, "shadow_tint": "teal", "shadow_amt": 0.18,
                     "high_tint": "cream", "high_amt": 0.24}),
        ("saturation", {"amount": 0.84, "vibrance": -0.06}),
        ("optics", {"soft_focus": 0.05, "veiling_flare": 0.08}),
        ("chroma_dv", {"ratio": "4:2:0", "edge_sharpen": 0.22, "dct_blocks": 0.04}),
        ("codec_era", {"codec": "h264", "crf": 25, "res": "native", "gop": 60,
                       "denoise_pre": 0.1}),
    ],
    _web_audio(high=15000.0, kbps=96, mono=False, codec="aac"),
))

register_preset(_preset(
    "auth-asmr-close-mic-2018", "ASMR Close-Mic Video", "2018", "modern",
    "A clean H.264 mirrorless close-up with gentle highlight rolloff and neutral color, paired with wide-band high-rate AAC so whispers, breath, and tiny transients remain physically close.",
    "Clean image, intimate wide-band stereo", ("10s", "asmr", "close-mic"),
    _modern_capture(contrast=0.98, warmth=0.04, tint=0.0, sat=0.94, distortion=0.0,
                    corner=0.06, gain_noise=0.06, wb=0.08, sharpen=0.16, kbps=7600,
                    crf=19),
    [("a_bandlimit", {"low_hz": 25.0, "high_hz": 20500.0}),
     ("a_compressor", {"threshold_db": -10.0, "ratio": 1.25, "attack_ms": 24.0,
                       "release_ms": 320.0, "knee_db": 12.0}),
     ("a_codec_aac", {"kbps": 256, "mono": False})],
))
