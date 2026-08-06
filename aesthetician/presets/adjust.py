"""Adjust-family presets: plain image correction, no era simulation.

Every default is neutral, so picking one changes nothing until a knob moves.
The variants are the common starting points. proc_height stays unset: these
process at the source resolution and never resample.
"""

from ..engine.presets import Preset, Variant, register_preset

register_preset(Preset(
    id="basic-adjust",
    name="Basic Adjustments",
    family="adjust",
    era="any",
    desc="The full correction toolkit on one panel: exposure, contrast, gamma, white balance, split tones, saturation, vibrance, hue and unsharp-mask sharpness.",
    tagline="Exposure, balance, saturation, sharpness",
    tags=("utility", "adjust", "correction"),
    video=[
        ("tone", {}),
        ("balance", {}),
        ("saturation", {}),
        ("sharpen", {}),
    ],
    audio=[],
    variants=[
        Variant("punchy", "Punchy", "More contrast, saturation and edge definition.",
                video={"tone.contrast": 1.14, "saturation.amount": 1.12, "sharpen.amount": 0.4}),
        Variant("flat", "Flat", "Lifted blacks and eased contrast, a log-ish starting point.",
                video={"tone.contrast": 0.88, "tone.lift": 0.05, "saturation.amount": 0.92}),
        Variant("warm-open", "Warm & Open", "A third of a stop up with warmth and gentle vibrance.",
                video={"tone.exposure": 0.3, "balance.warmth": 0.3, "saturation.vibrance": 0.25}),
    ],
))

register_preset(Preset(
    id="brightness-contrast",
    name="Brightness & Contrast",
    family="adjust",
    era="any",
    desc="Tone controls alone: exposure in stops, contrast around a pivot, midtone gamma, black lift and a soft highlight shoulder.",
    tagline="Exposure, contrast, gamma, black point",
    tags=("utility", "adjust", "tone"),
    video=[
        ("tone", {}),
    ],
    audio=[],
    variants=[
        Variant("brighter", "Brighter", "A third of a stop up with the highlights protected.",
                video={"tone.exposure": 0.35, "tone.knee": 0.85}),
        Variant("darker", "Darker", "A third of a stop down.",
                video={"tone.exposure": -0.35}),
        Variant("punchy", "Punchy", "Contrast up around a slightly low pivot.",
                video={"tone.contrast": 1.18, "tone.pivot": 0.4}),
        Variant("lifted", "Lifted", "Low contrast with raised blacks.",
                video={"tone.contrast": 0.86, "tone.lift": 0.06}),
    ],
))

register_preset(Preset(
    id="color-balance",
    name="Color Balance",
    family="adjust",
    era="any",
    desc="White balance and color controls: warmth, tint, shadow and highlight split tones, saturation, vibrance and hue rotation.",
    tagline="Warmth, tint, split tones, saturation",
    tags=("utility", "adjust", "color"),
    video=[
        ("balance", {}),
        ("saturation", {}),
    ],
    audio=[],
    variants=[
        Variant("warmer", "Warmer", "Toward orange, as shot in warmer light.",
                video={"balance.warmth": 0.35}),
        Variant("cooler", "Cooler", "Toward blue, as shot in cooler light.",
                video={"balance.warmth": -0.35}),
        Variant("vivid", "Vivid", "Saturation up with vibrance favoring the muted colors.",
                video={"saturation.amount": 1.15, "saturation.vibrance": 0.35}),
        Variant("muted", "Muted", "Saturation eased off across the board.",
                video={"saturation.amount": 0.8}),
    ],
))

register_preset(Preset(
    id="sharpness",
    name="Sharpness",
    family="adjust",
    era="any",
    desc="Unsharp-mask sharpening with an adjustable radius; negative amounts soften toward a plain blur instead.",
    tagline="Unsharp mask, radius, or soften",
    tags=("utility", "adjust", "detail"),
    video=[
        ("sharpen", {}),
    ],
    audio=[],
    variants=[
        Variant("crisp", "Crisp", "A moderate edge lift at a fine radius.",
                video={"sharpen.amount": 0.5, "sharpen.radius": 0.8}),
        Variant("very-crisp", "Very Crisp", "A strong edge lift; watch for halos on hard lines.",
                video={"sharpen.amount": 1.1, "sharpen.radius": 1.0}),
        Variant("soften", "Soften", "A gentle blend toward a wide blur.",
                video={"sharpen.amount": -0.35, "sharpen.radius": 2.5}),
    ],
))
