"""Captions family: burned-in subtitle and caption styles across the eras.

Every preset here is a pure captions chain. The cues themselves (words and
timing) are placed on the timeline; stack one of these over any look, or under
it so the tape or film chews the lettering the way the era really did.

None of these set proc_height: text rasterizes at delivery resolution and only
picks up softness from whatever look is stacked above it.
"""

from ..engine.presets import Preset, Variant, register_preset

register_preset(Preset(
    id="cc-line21-1982",
    name="Line-21 Closed Captions",
    family="captions",
    era="1982",
    desc="A set-top decoder drawing Line-21 data: white monospace capitals in snug black cells, "
         "popped on whole and held. The caption look burned into every off-air recording.",
    tagline="White capitals in black decoder cells",
    tags=("captions", "cc", "broadcast", "80s"),
    video=[
        ("captions", {"font": "cc_mono", "size": 0.048, "text_case": "upper", "line_chars": 30,
                      "max_lines": 2, "align": "center", "color": "F2F2F2", "edge": "none",
                      "box": "cells", "box_color": "000000", "box_opacity": 0.92,
                      "pos_y": 0.87, "appear": "cut"}),
    ],
    variants=[
        Variant("paint-on", "Paint-On", "The decoder paints each caption in left to right.",
                video={"captions.appear": "paint_on", "captions.appear_speed": 1.2}),
        Variant("large", "Large Print", "The big-print decoder mode for the back of the room.",
                video={"captions.size": 0.062, "captions.line_chars": 24}),
        Variant("soft-cells", "Faded Cells", "An older decoder whose background bars have gone thin.",
                video={"captions.box_opacity": 0.62}),
    ],
))

register_preset(Preset(
    id="cc-rollup-1987",
    name="Live Roll-Up Captions",
    family="captions",
    era="1987",
    desc="Realtime stenography rolling up the screen: three rows of capitals scrolling in black "
         "cells, a beat behind the anchor, the way live news captioning actually landed.",
    tagline="Three rows scrolling a beat behind",
    tags=("captions", "cc", "news", "live", "80s"),
    video=[
        ("captions", {"font": "cc_mono", "size": 0.046, "text_case": "upper", "line_chars": 32,
                      "max_lines": 3, "align": "left", "color": "F2F2F2", "edge": "none",
                      "box": "cells", "box_color": "000000", "box_opacity": 0.92,
                      "pos_x": 0.5, "pos_y": 0.86, "appear": "roll_up", "appear_speed": 1.0}),
    ],
    variants=[
        Variant("two-row", "Two Rows", "The tighter two-row window some stations ran.",
                video={"captions.max_lines": 2}),
        Variant("hurried", "Hurried Steno", "A faster scroll chasing a fast talker.",
                video={"captions.appear_speed": 1.7}),
    ],
))

register_preset(Preset(
    id="teletext-1979",
    name="Teletext Page 888",
    family="captions",
    era="1979",
    desc="Broadcast teletext subtitles: chunky double-wide pixels in service yellow on black "
         "blocks, rendered by the set's own character generator off page 888.",
    tagline="Service yellow on teletext blocks",
    tags=("captions", "teletext", "uk", "70s"),
    video=[
        ("captions", {"font": "teletext", "size": 0.052, "line_chars": 34, "max_lines": 2,
                      "align": "center", "color": "F2E12C", "edge": "none",
                      "box": "cells", "box_color": "000000", "box_opacity": 1.0,
                      "pos_y": 0.88, "appear": "cut"}),
    ],
    variants=[
        Variant("cyan", "Cyan Row", "The alternate speaker color straight off the palette.",
                video={"captions.color": "3CE8E8"}),
        Variant("white", "White Row", "Plain white rows for continuity announcements.",
                video={"captions.color": "F2F2F2"}),
        Variant("double-height", "Double Height", "The double-height rows of a proud subtitler.",
                video={"captions.size": 0.068, "captions.line_chars": 26}),
    ],
))

register_preset(Preset(
    id="cc-dtv-2004",
    name="Digital TV Captions",
    family="captions",
    era="2004",
    desc="A CEA-708 decoder with its factory defaults: clean mixed-case sans on a translucent "
         "smoked block, floating in the caption safe area of an early flat panel.",
    tagline="Mixed case on a smoked block",
    tags=("captions", "cc", "digital", "00s"),
    video=[
        ("captions", {"font": "sans", "size": 0.044, "line_chars": 36, "max_lines": 2,
                      "align": "center", "color": "FFFFFF", "edge": "none",
                      "box": "block", "box_color": "101014", "box_opacity": 0.68,
                      "pos_y": 0.88, "appear": "cut"}),
    ],
    variants=[
        Variant("mono", "Mono Face", "The monospace font option buried in the settings menu.",
                video={"captions.font": "mono"}),
        Variant("no-backing", "No Backing", "Backing off, edges on, the other settings-menu path.",
                video={"captions.box": "none", "captions.edge": "outline_shadow",
                       "captions.edge_strength": 0.55}),
    ],
))

register_preset(Preset(
    id="cinema-subs-1968",
    name="Theatrical Subtitles",
    family="captions",
    era="1968",
    desc="Art-house print subtitles: unbacked white serif lines resting low, a soft shadow "
         "keeping them legible over bright stock. The voice of subtitled cinema.",
    tagline="Unbacked white serif, resting low",
    tags=("captions", "cinema", "film", "60s"),
    video=[
        ("captions", {"font": "serif", "size": 0.047, "line_chars": 38, "max_lines": 2,
                      "align": "center", "color": "F7F7F2", "edge": "shadow",
                      "edge_strength": 0.35, "box": "none", "pos_y": 0.9, "appear": "cut"}),
    ],
    variants=[
        Variant("grand", "Roadshow Print", "Larger lettering for the big house.",
                video={"captions.size": 0.056, "captions.line_chars": 32}),
        Variant("sans-house", "Sans House Style", "The distributor that set its subs in a grotesque.",
                video={"captions.font": "sans", "captions.edge_strength": 0.3}),
    ],
))

register_preset(Preset(
    id="print-etch-1957",
    name="Etched Print Subtitles",
    family="captions",
    era="1957",
    desc="Subtitles burned into the release print itself: blazing white with nibbled edges "
         "where the emulsion gave way, no outline, flaring into bright scenes.",
    tagline="Blazing white, nibbled emulsion edges",
    tags=("captions", "cinema", "film", "50s"),
    video=[
        ("captions", {"font": "serif", "size": 0.05, "line_chars": 36, "max_lines": 2,
                      "align": "center", "color": "FFFFFF", "edge": "etch",
                      "edge_strength": 0.65, "box": "none", "pos_y": 0.9, "appear": "cut"}),
    ],
    variants=[
        Variant("worn", "Worn Stamp", "A tired print: heavier nibbling, thinner whites.",
                video={"captions.edge_strength": 0.95, "captions.opacity": 0.92}),
        Variant("fine", "Fresh Strike", "A new print whose burn came out clean.",
                video={"captions.edge_strength": 0.35}),
    ],
))

register_preset(Preset(
    id="dvd-subs-1999",
    name="DVD Player Subtitles",
    family="captions",
    era="1999",
    desc="A living-room player compositing its subpicture stream: bold sans with a hard dark "
         "rim from the four-color palette, hanging in the action-safe zone.",
    tagline="Bold sans with a hard palette rim",
    tags=("captions", "dvd", "digital", "90s"),
    video=[
        ("captions", {"font": "sans_bold", "size": 0.046, "line_chars": 36, "max_lines": 2,
                      "align": "center", "color": "F2F2F2", "edge": "outline",
                      "edge_strength": 0.7, "box": "none", "pos_y": 0.89, "appear": "cut"}),
    ],
    variants=[
        Variant("yellow", "Yellow Track", "The yellow subtitle track of many a region release.",
                video={"captions.color": "F2DE3C"}),
        Variant("banded", "Gray Band", "The player that boxed its subs on a gray strap.",
                video={"captions.box": "band", "captions.box_color": "3A3A3E",
                       "captions.box_opacity": 0.55}),
    ],
))

register_preset(Preset(
    id="fansub-vhs-1994",
    name="Tape-Traded Fansub",
    family="captions",
    era="1994",
    desc="A genlocked Amiga burning fan translations onto third-generation tape: hot yellow "
         "bold with a thick rim, drifting a little where the timebase wandered.",
    tagline="Hot yellow bold, drifting on tape",
    tags=("captions", "fansub", "vhs", "90s"),
    video=[
        ("captions", {"font": "sans_bold", "size": 0.05, "line_chars": 34, "max_lines": 2,
                      "align": "center", "color": "F2DE3C", "edge": "outline",
                      "edge_strength": 0.85, "box": "none", "pos_y": 0.88,
                      "appear": "cut", "jitter": 0.3}),
    ],
    variants=[
        Variant("cyan", "Cyan Circle", "The circle that subbed in cyan to stand apart.",
                video={"captions.color": "56E8E8"}),
        Variant("chunky", "Chunky Master", "First-generation master: bigger type, heavier rim.",
                video={"captions.size": 0.058, "captions.edge_strength": 1.0,
                       "captions.jitter": 0.15}),
    ],
))

register_preset(Preset(
    id="sdh-2007",
    name="SDH Subtitles",
    family="captions",
    era="2007",
    desc="Subtitles for the deaf and hard of hearing off a late DVD: clean mixed-case sans "
         "with rim and shadow, room for bracketed sound cues and speaker names.",
    tagline="Clean sans with room for sound cues",
    tags=("captions", "sdh", "digital", "00s"),
    video=[
        ("captions", {"font": "sans", "size": 0.042, "line_chars": 42, "max_lines": 3,
                      "align": "center", "color": "FFFFFF", "edge": "outline_shadow",
                      "edge_strength": 0.5, "box": "none", "pos_y": 0.89, "appear": "cut"}),
    ],
    variants=[
        Variant("boxed", "Boxed", "The player profile that kept a smoked block behind SDH.",
                video={"captions.box": "block", "captions.box_color": "101014",
                       "captions.box_opacity": 0.6, "captions.edge": "none"}),
        Variant("large", "Large Print", "Bigger type for the ten-foot living room.",
                video={"captions.size": 0.052, "captions.line_chars": 34}),
    ],
))

register_preset(Preset(
    id="lower-third-1985",
    name="News Lower Third",
    family="captions",
    era="1985",
    desc="A control-room character generator keying names over the strap: heavy condensed "
         "capitals on a full-width band, cut in and out between takes.",
    tagline="Heavy capitals on a full-width strap",
    tags=("captions", "broadcast", "news", "80s"),
    video=[
        ("captions", {"font": "heavy", "size": 0.052, "text_case": "upper", "line_chars": 30,
                      "max_lines": 2, "align": "left", "color": "FFFFFF", "edge": "shadow",
                      "edge_strength": 0.4, "box": "band", "box_color": "10102E",
                      "box_opacity": 0.72, "pos_x": 0.26, "pos_y": 0.87, "appear": "cut"}),
    ],
    variants=[
        Variant("election", "Election Night", "The solid strap of a long results night.",
                video={"captions.box_opacity": 0.95, "captions.box_color": "1A1A40"}),
        Variant("cable", "Cable Access", "A humbler generator: plain white on smoke.",
                video={"captions.font": "sans_bold", "captions.box_color": "141414",
                       "captions.box_opacity": 0.6}),
    ],
))

register_preset(Preset(
    id="vcr-osd-1990",
    name="VCR On-Screen Text",
    family="captions",
    era="1990",
    desc="The deck's own character generator writing over playback: glowing dot-matrix "
         "capitals that sit wherever the firmware put them and shiver with the tape.",
    tagline="Glowing dot-matrix deck lettering",
    tags=("captions", "vcr", "osd", "90s"),
    video=[
        ("captions", {"font": "dotmatrix", "size": 0.055, "text_case": "upper", "line_chars": 24,
                      "max_lines": 2, "align": "left", "color": "F2F2F2", "edge": "glow",
                      "edge_strength": 0.5, "box": "none", "pos_x": 0.24, "pos_y": 0.14,
                      "appear": "cut", "jitter": 0.18}),
    ],
    variants=[
        Variant("green", "Counter Green", "The green phosphor personality of another deck.",
                video={"captions.color": "4CF26B"}),
        Variant("orange", "Camcorder Amber", "Amber lettering straight off a camcorder EVF.",
                video={"captions.color": "F2953C", "captions.edge_strength": 0.7}),
        Variant("tracking", "Bad Tracking", "A deck fighting the tape: heavy shiver.",
                video={"captions.jitter": 0.55}),
    ],
))

register_preset(Preset(
    id="typewriter-doc-1976",
    name="Documentary Typewriter",
    family="captions",
    era="1976",
    desc="Location cards typed onto the frame: courier capitals spelled out letter by letter "
         "with a blinking cursor, sitting low in the corner like an investigator's note.",
    tagline="Typed location cards, blinking cursor",
    tags=("captions", "documentary", "typewriter", "70s"),
    video=[
        ("captions", {"font": "typewriter", "size": 0.042, "text_case": "upper", "line_chars": 34,
                      "max_lines": 2, "align": "left", "color": "F2F2EC", "edge": "shadow",
                      "edge_strength": 0.45, "box": "none", "pos_x": 0.2, "pos_y": 0.84,
                      "appear": "typewriter", "appear_speed": 1.0}),
    ],
    variants=[
        Variant("bold-strike", "Bold Strike", "A fresh ribbon striking heavier.",
                video={"captions.font": "typewriter_bold"}),
        Variant("instant", "Pre-Typed", "The card already typed when the shot cuts in.",
                video={"captions.appear": "cut"}),
    ],
))

register_preset(Preset(
    id="karaoke-1988",
    name="Karaoke Fill",
    family="captions",
    era="1988",
    desc="A laserdisc karaoke machine sweeping its lyric line: rimmed white capitals filling "
         "gold left to right across the hold, parked above the action.",
    tagline="Lyrics filling gold across the hold",
    tags=("captions", "karaoke", "80s"),
    video=[
        ("captions", {"font": "sans_bold", "size": 0.055, "line_chars": 30, "max_lines": 2,
                      "align": "center", "color": "FFFFFF", "edge": "outline",
                      "edge_strength": 0.8, "box": "none", "pos_y": 0.84,
                      "appear": "karaoke", "karaoke_color": "F2C23C"}),
    ],
    variants=[
        Variant("pink", "Snack Bar Pink", "The pink fill of a well-loved machine.",
                video={"captions.karaoke_color": "F26BB4"}),
        Variant("cyan", "Arcade Cyan", "The cyan fill wired into an arcade cabinet.",
                video={"captions.karaoke_color": "56D8F2"}),
    ],
))

register_preset(Preset(
    id="intertitle-1923",
    name="Silent Film Intertitle",
    family="captions",
    era="1923",
    desc="A full title card cut into the picture: warm lettering on a near-black card that "
         "replaces the frame for as long as the cue holds, then hands the scene back.",
    tagline="Full title cards cut into the reel",
    tags=("captions", "silent", "film", "20s"),
    video=[
        ("captions", {"font": "bookface", "size": 0.06, "line_chars": 30, "max_lines": 3,
                      "align": "center", "color": "E8DCC0", "edge": "none",
                      "box": "card", "box_color": "0C0A08", "box_opacity": 1.0,
                      "pos_x": 0.5, "pos_y": 0.5, "appear": "fade", "appear_speed": 0.8}),
    ],
    variants=[
        Variant("hand-set", "Hand-Set Italic", "The card shop that set its titles in italic.",
                video={"captions.size": 0.066}),
        Variant("overlay", "Superimposed", "Lettering over the scene instead of a cut card.",
                video={"captions.box_opacity": 0.0, "captions.edge": "shadow",
                       "captions.edge_strength": 0.5}),
    ],
))
