"""The master Texture control.

Real film and tape regenerate their noise every frame — a static noise pattern
reads as a dirty lens, not as film. That liveliness is intentional, but "how
much grain/noise/speckle" is a taste decision that spans many effects at once,
so scattering it across a dozen effect cards makes it un-tunable in practice.

`Context.texture` scales every parameter listed here (1.0 = as authored, 0 =
none, >1 = heavier), giving one dial for the whole chain. Only *amount-like*
noise parameters belong here — never sizes, rates of physical damage events, or
anything whose zero value is not "clean".
"""

from __future__ import annotations

# (effect_id, param_name) — per-frame noise/speckle amounts.
NOISE_PARAMS: frozenset[tuple[str, str]] = frozenset(
    {
        # photochemical texture
        ("grain", "amount"),
        ("grain", "intermittent"),
        ("grain", "mottle"),
        ("dust", "density"),
        # tape
        ("vhs", "luma_noise"),
        ("vhs", "chroma_noise"),
        ("vhs", "fm_sparkle"),
        ("vhs", "azimuth_error"),
        # broadcast / reception
        ("ntsc", "phase_noise"),
        ("signal_rf", "snow"),
        ("signal_rf", "impulse_noise"),
        ("rf_dx", "noise_floor"),
        ("herringbone", "amount"),
        # display
        ("crt", "retrace_lines"),
        ("lcd_screen", "moire_cam"),
        # camera electronics
        ("exposure_auto", "agc_gain_noise"),
        # cel / print
        ("cel_dirt", "density"),
        ("paper_texture", "amount"),
        ("photocopy", "toner"),
        ("riso_print", "grain_ink"),
    }
)

# Deliberately NOT here, though they are also "texture" in a loose sense:
#   plate.opacity        — the packs in use carry decay CONTENT (mold, water
#                          stains, nitrate blistering, burns). Erasing a preset's
#                          water damage because the user asked for less grain
#                          would be a nasty surprise.
#   scratches.*, dust size, frame_damage.*, sticky_shed.severity — physical
#                          damage events, not noise; they belong to --intensity.


def is_noise_param(eid: str, param: str) -> bool:
    return (eid, param) in NOISE_PARAMS


def scaled(eid: str, param: str, value: float, texture: float) -> float:
    """Apply the texture multiplier to `value` if this param is a noise amount."""
    if texture == 1.0 or not is_noise_param(eid, param):
        return value
    return value * texture
