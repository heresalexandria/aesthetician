"""Finding presets: the controlled vocabulary behind search, facets and synonyms.

A preset's name says what the physical artifact is ("Tokyo Spectacle Print");
the person looking for it types what they mean ("60s kaiju film"). This module
is the bridge. It does three things:

* **Facets.** Every preset is placed in a handful of orthogonal, controlled
  facets - medium, genre, region, condition, color - derived from its chain
  (a `vhs` effect means videotape, a `mono` effect at full amount means black
  and white) and from its vocabulary (id, name, tags, keywords, tagline). The
  GUI filters on these; nothing is authored per preset beyond keywords.
* **Synonyms.** Query expansion for the search box: "eighties" finds "80s",
  "monster movie" finds kaiju and creature features, "b&w" finds "bw".
* **Search text.** One canonical token soup per preset, so the CLI and the GUI
  agree on what a query matches.

Vocabulary terms match whole tokens (or hyphenated phrases) in the preset's own
words, never substrings, so "print" in "answer print" cannot make a film preset
a halftone print. Add terms here rather than special-casing presets.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from .engine.presets import Preset

# ── tokenizing ───────────────────────────────────────────────────────────

_STOP = {"a", "an", "the", "of", "and", "or", "on", "in", "at", "to", "for", "with",
         "from", "by", "as", "its", "it", "is", "that", "this", "over", "under",
         "into", "through", "off", "then", "than", "one", "two", "very", "s"}

_DECADE_WORDS = {
    1890: "eighteen-nineties", 1900: "nineteen-hundreds", 1910: "tens", 1920: "twenties",
    1930: "thirties", 1940: "forties", 1950: "fifties", 1960: "sixties",
    1970: "seventies", 1980: "eighties", 1990: "nineties", 2000: "aughts",
    2010: "twenty-tens", 2020: "twenty-twenties",
}

# Phrases people type that the vocabulary spells one specific way. Applied to
# queries before tokenizing, and to preset text so both sides agree.
PHRASES: dict[str, str] = {
    "black and white": "bw",
    "black & white": "bw",
    "black-and-white": "bw",
    "b&w": "bw",
    "b/w": "bw",
    "sci fi": "scifi",
    "sci-fi": "scifi",
    "science fiction": "scifi",
    "hi fi": "hifi",
    "hi-fi": "hifi",
    "lo fi": "lofi",
    "lo-fi": "lofi",
    "super 8": "super8",
    "super-8": "super8",
    "super 16": "super16",
    "super-16": "super16",
    "8 mm": "8mm",
    "16 mm": "16mm",
    "35 mm": "35mm",
    "65 mm": "65mm",
    "70 mm": "70mm",
    "9.5 mm": "9.5mm",
    "9.5mm": "9.5mm",
    "hong kong": "hong-kong",
    "u matic": "umatic",
    "u-matic": "umatic",
    "s-vhs": "svhs",
    "s vhs": "svhs",
    "vhs-c": "vhs-c",
    "hi 8": "hi8",
    "hi-8": "hi8",
    "video 8": "video8",
    "video-8": "video8",
    "mini dv": "minidv",
    "mini-dv": "minidv",
    "laser disc": "laserdisc",
    "cd rom": "cdrom",
    "cd-rom": "cdrom",
    "home movie": "home-movie",
    "home video": "home-video",
    "music video": "music-video",
    "found footage": "found-footage",
    "stop motion": "stop-motion",
    "game show": "game-show",
    "talk show": "talk-show",
    "soap opera": "soap-opera",
    "public access": "public-access",
    "drive in": "drive-in",
    "drive-in": "drive-in",
    "new wave": "new-wave",
    "film noir": "noir",
    "giant monster": "kaiju",
    "monster movie": "kaiju",
    "creature feature": "creature",
    "security camera": "cctv",
    "security cam": "cctv",
    "surveillance camera": "cctv",
    "body cam": "bodycam",
    "body camera": "bodycam",
    "dash cam": "dashcam",
    "night vision": "night-vision",
    "closed captions": "captions",
    "closed captioning": "captions",
    "sub titles": "subtitles",
    "kung fu": "kung-fu",
    "wire fu": "wire-fu",
    "sword and sorcery": "sword-and-sorcery",
    "post apocalyptic": "post-apocalyptic",
    "post-apocalyptic": "post-apocalyptic",
    "saturday morning": "saturday-morning",
    "late night": "late-night",
    "prime time": "primetime",
    "prime-time": "primetime",
    "off air": "off-air",
    "off-air": "off-air",
    "taped off": "off-air",
    "multi cam": "multicam",
    "multi-cam": "multicam",
    "single cam": "single-camera",
    "answer print": "answer-print",
    "release print": "release-print",
    "public information": "public-information",
    "screen recording": "screen-recording",
    "web cam": "webcam",
    "cell phone": "cellphone",
    "cell-phone": "cellphone",
    "flip phone": "cellphone",
    "smart phone": "smartphone",
    "smart-phone": "smartphone",
    "video call": "video-call",
    "video chat": "video-call",
    "shot on video": "shot-on-video",
    "made for tv": "tv-movie",
    "made-for-tv": "tv-movie",
    "tv movie": "tv-movie",
}

_PHRASE_RE = re.compile("|".join(re.escape(k) for k in sorted(PHRASES, key=len, reverse=True)))


def normalize_text(text: str) -> str:
    """Lower-case, fold known phrases to their canonical token, tidy decades."""
    t = text.lower().replace("’", "'")
    t = re.sub(r"\b(\d{2,4})'s\b", r"\1s", t)          # 80's -> 80s, 1980's -> 1980s
    t = _PHRASE_RE.sub(lambda m: PHRASES[m.group(0)], t)
    return t


def tokens(text: str) -> list[str]:
    """Split into search tokens; hyphenated phrases stay whole AND split.

    "hong-kong crime" -> ["hong-kong", "hong", "kong", "crime"]. Digits and
    letters stick together ("16mm", "1985"). Stop words are dropped.
    """
    out: list[str] = []
    for raw in re.split(r"[^a-z0-9\-\.]+", normalize_text(text)):
        raw = raw.strip("-.")
        if not raw:
            continue
        if "-" in raw:
            out.append(raw)
            out.extend(p for p in raw.split("-") if p)
        else:
            out.append(raw)
    return [t for t in out if t and t not in _STOP]


def era_tokens(era: str) -> list[str]:
    """'1985' -> ['1985', '1980s', '80s', 'eighties']."""
    m = re.match(r"(\d{4})", str(era))
    if not m:
        return [str(era)] if era else []
    year = int(m.group(1))
    dec = year // 10 * 10
    out = [str(year), f"{dec}s", f"{dec % 100:02d}s"]
    word = _DECADE_WORDS.get(dec)
    if word:
        out.append(word)
    return out


# ── facets ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FacetValue:
    id: str
    label: str
    terms: tuple[str, ...] = ()             # whole-token matches in the preset's words
    effects: tuple[str, ...] = ()           # any of these effects in a chain implies it
    params: tuple[tuple[str, str, Any], ...] = ()   # (effect, param, value) implies it
    audio_only: bool | None = None          # restrict the rule to sound-only presets (True) or picture presets (False)


@dataclass(frozen=True)
class Facet:
    id: str
    label: str
    values: tuple[FacetValue, ...]
    hint: str = ""


FACETS: tuple[Facet, ...] = (
    Facet("medium", "Medium", hint="What it was shot on and carried by", values=(
        FacetValue("film", "Film (any gauge)",
                   terms=("film", "print", "nitrate", "emulsion", "reel", "photochemical", "celluloid",
                          "kodak", "eastman", "eastmancolor", "technicolor", "kodachrome", "ektachrome",
                          "agfa", "orwo", "fuji", "answer-print", "release-print", "dupe", "telecine",
                          "theatrical", "35mm", "16mm", "8mm", "super8", "super16", "9.5mm", "70mm", "65mm"),
                   effects=("grain", "halation", "gate_weave", "print_char", "nitrate", "vinegar",
                            "scratches", "changeover", "telecine_scan", "light_leak"),
                   audio_only=False),
        FacetValue("film-35mm", "35 mm film",
                   terms=("35mm", "panavision", "anamorphic", "cinemascope", "scope", "vistavision",
                          "techniscope", "technirama", "technicolor", "roadshow", "theatrical",
                          "answer-print", "release-print", "feature"),
                   params=(("grain", "stock", "fine_35"), ("grain", "stock", "newsreel_35")),
                   audio_only=False),
        FacetValue("film-16mm", "16 mm film",
                   terms=("16mm", "super16", "bolex", "news-film", "newsfilm", "reversal"),
                   params=(("grain", "stock", "doc_16"),),
                   audio_only=False),
        FacetValue("film-8mm", "8 mm / Super 8",
                   terms=("8mm", "super8", "9.5mm", "single-8", "double-8", "regular-8", "small-gauge",
                          "pathe-baby", "polavision"),
                   params=(("grain", "stock", "super8"),),
                   audio_only=False),
        FacetValue("film-large", "65/70 mm and IMAX",
                   terms=("70mm", "65mm", "imax", "todd-ao", "cinerama", "large-format", "15-perf"),
                   audio_only=False),
        FacetValue("video-tube", "Tube-camera video",
                   terms=("tube", "tube-camera", "plumbicon", "orthicon", "image-orthicon", "vidicon",
                          "saticon", "kinescope", "quadruplex", "quad", "2-inch", "portapak"),
                   params=(("stock", "profile", "tube_70s"), ("stock", "profile", "tube_80s")),
                   audio_only=False),
        FacetValue("videotape", "Videotape (VHS, Beta, U-matic, 8 mm)",
                   terms=("vhs", "vhs-c", "svhs", "betamax", "beta", "umatic", "betacam", "video8",
                          "hi8", "digital8", "videotape", "camcorder", "vcr", "tape-deck", "rental",
                          "ep", "slp", "1-inch", "type-c", "d-2", "m-ii", "video-tape"),
                   effects=("vhs", "vcr_transport", "tape_junk", "sticky_shed", "osd"),
                   audio_only=False),
        FacetValue("video-digital", "Digital video (DV, HD, DSLR, phone)",
                   terms=("dv", "minidv", "dvcam", "dvcpro", "hdv", "hd", "1080i", "1080p", "720p",
                          "4k", "dslr", "mirrorless", "digital-cinema", "red-one", "alexa", "phone",
                          "smartphone", "iphone", "cellphone", "gopro", "action-camera", "webcam",
                          "dashcam", "bodycam", "doorbell", "drone", "digicam", "flip", "handycam",
                          "screen-recording"),
                   effects=("chroma_dv",),
                   audio_only=False),
        FacetValue("broadcast", "Broadcast signal (TV, cable, satellite)",
                   terms=("broadcast", "tv", "television", "network", "cable", "satellite", "uhf", "vhf",
                          "antenna", "off-air", "ntsc", "pal", "secam", "channel", "station", "live-tv",
                          "syndication", "superstation", "rf", "airwaves", "feed", "backhaul",
                          "microwave", "dx"),
                   effects=("ntsc", "signal_rf", "rf_dx", "herringbone", "jam_bars", "microwave_hit"),
                   audio_only=False),
        FacetValue("disc", "Optical / video disc",
                   terms=("laserdisc", "dvd", "vcd", "video-cd", "ced", "videodisc", "blu-ray", "bluray",
                          "cdrom", "mpeg1", "mpeg2", "dvd-r", "dvdr"),
                   audio_only=False),
        FacetValue("web", "Web video and streaming",
                   terms=("web", "web-video", "stream", "streaming", "livestream", "youtube", "upload",
                          "re-upload", "flv", "realplayer", "realvideo", "wmv", "divx", "xvid", "twitch",
                          "video-call", "skype", "vine", "tiktok", "instagram", "snapchat", "social", "myspace",
                          "facetime", "video-call", "vlog", "meme", "gif", "webcore", "internet"),
                   effects=("upload_gen",),
                   audio_only=False),
        FacetValue("animation", "Animation (cel, stop-motion, CGI)",
                   terms=("cel", "cels", "cartoon", "anime", "animation", "animated", "stop-motion",
                          "claymation", "puppet", "rotoscope", "cgi", "pencil-test", "ova", "toon",
                          "limited-animation", "cutout", "flash-animation", "machinima"),
                   effects=("animate_on", "cel_dirt", "cel_flatten", "cel_wobble", "color_era",
                            "ink_line", "paper_texture"),
                   audio_only=False),
        FacetValue("pixel", "Computer / console graphics",
                   terms=("pixel", "pixels", "8-bit", "16-bit", "vga", "cga", "ega", "c64", "commodore",
                          "gameboy", "game-boy", "console", "arcade", "sprite", "retro-game", "games",
                          "amiga", "teletext", "videotex", "prestel", "terminal", "fmv", "dither"),
                   effects=("pixel_era",),
                   audio_only=False),
        FacetValue("print", "Print, paper and photocopy",
                   terms=("halftone", "newspaper", "newsprint", "magazine", "comic", "comics",
                          "photocopy", "xerox", "zine", "riso", "risograph", "microfilm", "microfiche",
                          "fax", "mimeograph", "ditto", "poster", "polaroid", "photograph", "photo",
                          "slide", "rotogravure", "screen-print", "screenprint", "manga", "screentone",
                          "blueprint", "cyanotype", "letterpress", "dot-matrix", "thermal", "printout",
                          "transparency", "overhead", "view-master", "disposable-camera"),
                   effects=("halftone", "photocopy", "riso_print", "microfilm"),
                   audio_only=False),
        FacetValue("projection", "Projected in a room",
                   terms=("projector", "projected", "projection", "drive-in", "cinema", "theater",
                          "theatre", "matinee", "booth", "changeover", "roadshow", "home-projection",
                          "bedsheet", "living-room-wall", "screening", "palace", "grindhouse", "multiplex"),
                   effects=("projection", "screen", "changeover", "drive_in"),
                   audio_only=False),
        FacetValue("crt", "CRT display",
                   terms=("crt", "tube-tv", "trinitron", "monitor", "phosphor", "rptv", "big-screen",
                          "jumbotron", "watchman", "console-tv", "picture-tube", "scanlines", "shadow-mask",
                          "aperture-grille"),
                   effects=("crt", "rear_projection_tv", "phosphor_decay"),
                   audio_only=False),
        FacetValue("lcd", "LCD / flat panel",
                   terms=("lcd", "plasma", "flat-panel", "panel", "laptop", "screen-recording",
                          "off-the-monitor", "handheld-tv", "seatback", "vr", "headset", "led-wall"),
                   effects=("lcd_screen",),
                   audio_only=False),
        # Sound-only carriers (family audio, or an empty picture chain).
        FacetValue("audio-disc", "Disc and cylinder",
                   terms=("vinyl", "lp", "45", "78", "78rpm", "shellac", "cylinder", "wax", "acetate",
                          "lacquer", "transcription", "disc", "record", "gramophone", "phonograph",
                          "jukebox", "cd", "compact-disc", "minidisc", "discman", "turntable", "needle",
                          "belt", "dictation-belt"),
                   effects=("a_vinyl_noise", "a_vinyl_wow", "a_needle", "a_disc_medium",
                            "a_transcription_disc", "a_cd_skip"),
                   audio_only=True),
        FacetValue("audio-tape", "Magnetic tape",
                   terms=("tape", "cassette", "reel", "reel-to-reel", "8-track", "8track", "microcassette",
                          "wire", "cart", "dictation", "dictaphone", "walkman", "boombox", "four-track",
                          "fourtrack", "multitrack", "dat", "mag", "magnetic", "stripe", "mixtape",
                          "dolby", "dbx", "answering-machine", "hifi", "afm", "linear-track", "nagra"),
                   effects=("a_tape_hiss", "a_tape_sat", "a_wow_flutter", "a_analog_dub", "a_8track",
                            "a_microcassette", "a_wire_recorder", "a_print_through", "a_tape_dropouts",
                            "a_video_tape_audio", "a_noise_reduction", "a_dat_error"),
                   audio_only=True),
        FacetValue("radio", "Radio",
                   terms=("am", "fm", "shortwave", "radio", "cb", "ham", "walkie-talkie", "walkie",
                          "scanner", "transistor", "aviation", "atc", "pirate", "airwaves", "receiver",
                          "wireless", "marine", "two-way", "dispatch", "aircheck", "air-check", "dial"),
                   effects=("a_am_radio", "a_fm_radio", "a_shortwave", "a_cb_radio"),
                   audio_only=True),
        FacetValue("telephone", "Telephone and voice codecs",
                   terms=("phone", "telephone", "voip", "skype", "voicemail", "answering-machine",
                          "hold", "dial-up", "cell", "cellphone", "mobile", "handset", "speakerphone",
                          "cordless", "candlestick", "rotary", "touchtone", "baby-monitor", "intercom"),
                   effects=("a_telephone", "a_codec_speech"),
                   audio_only=True),
        FacetValue("pa", "PA, horns and intercoms",
                   terms=("pa", "bullhorn", "megaphone", "intercom", "announcement", "tannoy", "horn",
                          "stadium", "church", "subway", "drive-thru", "loudspeaker", "public-address",
                          "airport", "station", "gym", "gymnasium", "arena", "hall"),
                   effects=("a_pa_bullhorn",),
                   audio_only=True),
        FacetValue("film-sound", "Film soundtrack",
                   terms=("optical", "optical-track", "mag", "magnetic-film", "soundtrack", "dolby-stereo",
                          "academy", "projector", "sprocket", "newsreel", "mag-stripe"),
                   effects=("a_optical_track", "a_projector"),
                   audio_only=True),
        FacetValue("digital-audio", "Digital audio and codecs",
                   terms=("mp3", "aac", "codec", "bitcrush", "8-bit", "12-bit", "sampler", "cd", "dat",
                          "minidisc", "digital", "napster", "bluetooth", "smart-speaker", "game-audio",
                          "chiptune", "pcm", "lossy"),
                   effects=("a_codec_mp3", "a_codec_aac", "a_bitcrush", "a_digital_glitch"),
                   audio_only=True),
        FacetValue("playback-space", "Playback device and room",
                   terms=("speaker", "room", "hall", "cathedral", "stairwell", "garage", "through-the-wall",
                          "next-door", "bathroom", "tile", "car", "dashboard", "earbud", "earbuds",
                          "headphones", "laptop", "console", "clock-radio", "tv-speaker", "cabinet",
                          "living-room", "kitchen", "elevator", "supermarket", "muzak"),
                   effects=("a_speaker", "a_room", "a_slap", "a_bed"),
                   audio_only=True),
    )),
    Facet("genre", "Genre", hint="The kind of program or picture", values=(
        FacetValue("adventure", "Adventure",
                   terms=("adventure", "swashbuckler", "jungle", "pulp", "treasure", "expedition",
                          "safari", "quest", "serial", "cliffhanger", "matinee", "explorer", "pirate-movie",
                          "seafaring", "mountain")),
        FacetValue("action", "Action",
                   terms=("action", "buddy-cop", "cop", "heist", "car-chase", "chase", "martial-arts",
                          "kung-fu", "ninja", "wuxia", "wire-fu", "blockbuster", "vigilante",
                          "heroic-bloodshed", "lucha", "biker", "stunt", "shootout", "commando",
                          "mercenary", "spy", "bond", "espionage", "agent", "caper")),
        FacetValue("horror", "Horror",
                   terms=("horror", "slasher", "gothic", "creature", "zombie", "vampire", "haunted",
                          "ghost-story", "ghosts", "paranormal", "giallo", "folk-horror", "body-horror", "j-horror",
                          "analog-horror", "found-footage", "nightmare", "occult", "witch", "possession",
                          "unsettling", "creepy", "eerie", "macabre", "splatter", "torture")),
        FacetValue("scifi", "Science fiction",
                   terms=("scifi", "space", "alien", "aliens", "cyberpunk", "dystopia", "dystopian",
                          "robot", "atomic", "flying-saucer", "future", "futurism", "futuristic",
                          "space-opera", "spaceship", "cosmic", "android", "mutant", "invasion",
                          "post-apocalyptic", "wasteland", "time-travel", "matrix", "cyber",
                          "science-fiction", "planet")),
        FacetValue("kaiju", "Kaiju and tokusatsu",
                   terms=("kaiju", "tokusatsu", "giant-monster", "monster", "monsters", "godzilla",
                          "gamera", "toho", "rubber-suit", "suitmation", "sentai", "ultraman",
                          "hero-show", "tohoscope", "daikaiju")),
        FacetValue("western", "Western",
                   terms=("western", "cowboy", "sagebrush", "spaghetti", "frontier", "ranch", "outlaw",
                          "gunfighter", "saloon", "cattle", "prairie", "revisionist", "neo-western",
                          "indianerfilm", "singing-cowboy", "b-western", "western-color", "oater")),
        FacetValue("crime", "Crime, noir and thriller",
                   terms=("crime", "noir", "gangster", "detective", "mystery", "thriller", "heist",
                          "mob", "police", "procedural", "poliziotteschi", "conspiracy", "paranoia",
                          "serial-killer", "killer", "suspense", "hardboiled", "pulp-crime", "hood",
                          "street-crime", "spy", "espionage", "erotic-thriller", "courtroom", "legal")),
        FacetValue("comedy", "Comedy",
                   terms=("comedy", "sitcom", "slapstick", "screwball", "farce", "teen-comedy", "gag",
                          "two-reeler", "comedian", "stand-up", "sketch", "parody", "spoof", "stoner",
                          "romcom", "romantic-comedy", "buddy-comedy", "multicam", "laugh-track")),
        FacetValue("drama", "Drama and art film",
                   terms=("drama", "melodrama", "romance", "weepie", "prestige", "arthouse", "art-film",
                          "chamber", "kitchen-sink", "neorealism", "neorealismo", "new-wave", "slow-cinema",
                          "period", "coming-of-age", "indie", "independent", "literary", "poetic",
                          "contemplative", "realism", "naturalism", "mumblecore", "dogme", "miniseries",
                          "anthology", "tv-movie", "movie-of-the-week", "soap", "soap-opera", "telenovela",
                          "daytime", "primetime-soap", "teen-drama", "womens-picture", "tearjerker",
                          "biopic", "epic", "historical", "costume", "swinging")),
        FacetValue("music", "Music: videos, concerts, musicals",
                   terms=("musical", "music", "music-video", "dance", "disco", "concert", "jukebox",
                          "cabaret", "soundie", "revue", "song", "ballet", "opera", "promo", "big-band",
                          "rock", "punk", "grunge", "hip-hop", "rap", "rave", "techno", "eurodance",
                          "new-wave", "pop", "idol", "country", "soul", "jazz", "metal", "hair-metal",
                          "nu-metal", "emo", "trip-hop", "r-and-b", "prog-rock", "karaoke", "countdown",
                          "mtv", "music-tv", "chorus", "playback", "synth", "synthwave", "vaporwave",
                          "lofi", "chillwave", "hyperpop")),
        FacetValue("war", "War and wartime",
                   terms=("war", "wartime", "combat", "propaganda", "military", "signal-corps", "army",
                          "navy", "vietnam", "battle", "home-front", "occupation", "cold-war", "civil-defense",
                          "soldier", "platoon", "blitz", "trenches", "invasion-war", "veteran")),
        FacetValue("fantasy", "Fantasy",
                   terms=("fantasy", "fairy", "fairy-tale", "magical", "magic", "sword-and-sorcery",
                          "sorcery", "storybook", "whimsy", "whimsical", "dreamlike", "trick-film",
                          "wizard", "dragon", "labyrinth", "enchanted", "mythic", "sword", "barbarian",
                          "peplum", "biblical", "supernatural")),
        FacetValue("documentary", "Documentary and actuality",
                   terms=("documentary", "doc", "verite", "actuality", "newsreel", "travelogue", "mondo",
                          "nature", "wildlife", "expedition", "ethnographic", "true-crime", "reportage",
                          "mission", "nasa", "archive", "archival", "diary", "essay", "observational",
                          "interview", "oral-history", "social", "wpa", "city-symphony", "tourist",
                          "travel", "skate", "surf", "concert-film")),
        FacetValue("news", "News and weather",
                   terms=("news", "newsreel", "eyewitness", "reporter", "anchor", "live-truck", "bulletin",
                          "weather", "forecast", "election", "campaign", "press", "correspondent",
                          "embedded", "war-journalism", "headline", "newsdesk", "ticker", "24-hour",
                          "cable-news", "local-news", "network-news", "breaking")),
        FacetValue("sports", "Sports and fitness",
                   terms=("sports", "sport", "golf", "football", "boxing", "wrestling", "olympics",
                          "olympic", "skate", "skateboard", "skateboarding", "surf", "surfing", "race",
                          "racing", "fitness", "aerobics", "workout", "baseball", "basketball", "hockey",
                          "arena", "stadium", "highlight", "highlights", "match", "tournament", "ballpark",
                          "motorsport", "rodeo", "bowling", "soccer", "nfl", "nba")),
        FacetValue("commercial", "Commercials and promotion",
                   terms=("commercial", "commercials", "ad", "ads", "advert", "advertising", "spot",
                          "jingle", "infomercial", "shopping", "dealer", "product", "sponsored", "brand",
                          "promotional", "promotion", "pitch", "sales", "demo-reel", "showreel",
                          "trailer", "trailers", "psa", "public-service", "ident", "bumper", "station-id",
                          "keynote", "launch", "corporate", "industrial")),
        FacetValue("kids", "Kids and family",
                   terms=("kids", "children", "childrens", "saturday-morning", "toy", "toys", "cereal",
                          "preschool", "family", "holiday-special", "puppet", "puppets", "after-school",
                          "teen", "teenage", "juvenile", "school", "classroom", "sesame", "kids-cable",
                          "slime", "gross-out", "cartoon", "cartoons")),
        FacetValue("anime", "Anime",
                   terms=("anime", "ova", "fansub", "magical-girl", "mecha", "shonen", "shojo", "manga",
                          "toonami", "japanimation", "otaku")),
        FacetValue("educational", "Educational, industrial and institutional",
                   terms=("educational", "education", "classroom", "instructional", "training", "industrial",
                          "hygiene", "civil-defense", "public-information", "safety", "science", "lecture",
                          "corporate", "sponsored", "filmstrip", "school", "institutional", "government",
                          "orientation", "how-to", "explainer", "tutorial", "lesson", "campus", "college",
                          "university", "museum", "library", "scare-film")),
        FacetValue("home-movie", "Home movies and personal video",
                   terms=("home-movie", "home-video", "family", "vacation", "wedding", "birthday", "diary",
                          "holiday", "amateur", "backyard", "living-room", "personal", "vlog", "party",
                          "memories", "reunion", "graduation", "christmas", "camcorder", "handycam",
                          "palmcorder", "polavision", "snapshot", "scrapbook", "dating", "profile")),
        FacetValue("surveillance", "Surveillance and evidence",
                   terms=("surveillance", "security", "cctv", "closed-circuit", "dashcam", "bodycam",
                          "doorbell", "nanny-cam", "evidence", "timestamp", "night-vision", "liminal",
                          "monitoring", "lobby", "parking", "baby-monitor", "elevator-cam", "traffic-cam",
                          "police", "courtroom", "interrogation", "hidden-camera", "spy-cam")),
        FacetValue("talk-variety", "Talk, variety and lifestyle TV",
                   terms=("talk-show", "talk", "variety", "late-night", "morning", "morning-show",
                          "telethon", "pledge", "televangelist", "religious", "sermon", "host", "horror-host",
                          "cooking", "food", "lifestyle", "makeover", "chat", "panel", "awards", "pageant",
                          "parade", "special", "sign-off", "public-access", "call-in", "shopping",
                          "home-shopping", "pledge-drive", "keynote", "dance-show")),
        FacetValue("game-show", "Game shows and quizzes",
                   terms=("game-show", "quiz", "contest", "contestant", "prize", "buzzer", "trivia",
                          "dating-game", "countdown-show", "panel-game", "spelling-bee")),
        FacetValue("reality", "Reality and tabloid TV",
                   terms=("reality", "makeover", "court", "court-tv", "tabloid", "reenactment", "dating",
                          "big-brother", "paranormal-investigation", "ride-along", "confessional",
                          "docusoap", "competition-show", "survival", "ghost-hunters", "unsolved",
                          "cops", "true-crime")),
        FacetValue("experimental", "Experimental and avant-garde",
                   terms=("experimental", "avant-garde", "underground", "psychedelic", "abstract",
                          "glitch", "datamosh", "happening", "structural", "city-symphony", "montage",
                          "expressionist", "expressionism", "surrealism", "surreal", "collage", "found",
                          "video-art", "art", "scratch-film", "direct-on-film", "flicker-film")),
        FacetValue("aesthetic", "Internet aesthetics and grades",
                   terms=("vaporwave", "synthwave", "outrun", "aesthetic", "aesthetics", "webcore",
                          "dreamcore", "weirdcore", "liminal", "lofi", "y2k", "nostalgia", "nostalgic",
                          "mood", "moody", "grade", "graded", "look", "frutiger-aero", "cottagecore",
                          "dark-academia", "hauntology", "cursed", "deep-fried", "tumblr", "vsco",
                          "hipstamatic", "chillwave", "backrooms", "retro", "vintage", "filmic",
                          "teal-orange", "bleach-bypass", "cross-process", "day-for-night", "pastel")),
        FacetValue("games", "Video games and computers",
                   terms=("games", "game", "gaming", "videogame", "video-game", "arcade", "console",
                          "retro-game", "computer", "home-computer", "pc", "dos", "demo", "demoscene",
                          "fmv", "cutscene", "sprite", "8-bit", "16-bit", "micro", "bedroom-coder",
                          "playstation", "nintendo", "sega", "gameboy", "game-boy", "emulator", "rom")),
        FacetValue("any-program", "Any program (a channel, format or signal)",
                   terms=("any-program", "format", "carrier", "blank-tape", "generic", "whatever-was-on",
                          "off-the-shelf", "playback-format", "recording-format", "test-signal",
                          "channel", "network", "broadcaster", "public-broadcaster", "public-television",
                          "state-television", "terrestrial", "cable-network", "station", "superstation",
                          "public-service", "house-style", "signal", "feed")),
        FacetValue("utility", "Utility and captions",
                   terms=("utility", "adjust", "correction", "captions", "subtitles", "intertitle",
                          "lower-third", "osd", "teletext", "sdh", "cc", "karaoke-fill", "typewriter")),
    )),
    Facet("region", "Region", hint="Where it was made or aired", values=(
        FacetValue("usa", "United States",
                   terms=("usa", "us", "american", "america", "hollywood", "network", "nyc", "new-york",
                          "los-angeles", "la", "chicago", "southern", "midwest", "texas", "california",
                          "miami", "philadelphia", "nasa", "wpa", "brooklyn", "detroit", "vegas",
                          "appalachian", "route-66", "ntsc", "uhf", "cable", "superstation", "pbs")),
        FacetValue("uk", "United Kingdom",
                   terms=("british", "britain", "uk", "england", "english", "london", "scottish",
                          "scotland", "welsh", "wales", "irish", "ireland", "ealing", "hammer",
                          "quota-quickie", "teletext", "kitchen-sink", "britpop", "swinging-london",
                          "pinewood", "shepperton", "channel-4", "itv", "bbc", "public-service",
                          "405-line", "625-line")),
        FacetValue("japan", "Japan",
                   terms=("japan", "japanese", "tokyo", "osaka", "anime", "tokusatsu", "kaiju", "samurai",
                          "toho", "nikkatsu", "shochiku", "daiei", "j-horror", "v-cinema", "idol", "ova",
                          "godzilla", "manga", "ntsc-j", "chanbara", "yakuza", "sentai", "ghibli-era")),
        FacetValue("italy", "Italy",
                   terms=("italy", "italian", "giallo", "peplum", "spaghetti", "poliziotteschi",
                          "cinecitta", "neorealism", "neorealismo", "mondo", "rai", "rome", "roman",
                          "eurocrime", "euro-horror", "cannibal", "italo")),
        FacetValue("france", "France",
                   terms=("france", "french", "paris", "parisian", "nouvelle-vague", "cinema-du-look",
                          "gaumont", "pathe", "lumiere", "secam", "poetic-realism", "ye-ye",
                          "couture", "riviera")),
        FacetValue("germany", "Germany and Austria",
                   terms=("german", "germany", "berlin", "munich", "expressionist", "expressionism",
                          "ufa", "defa", "east-german", "west-german", "weimar", "krautrock",
                          "austrian", "vienna", "agfacolor")),
        FacetValue("hong-kong", "Hong Kong",
                   terms=("hong-kong", "hongkong", "hk", "shaw", "shawscope", "golden-harvest",
                          "heroic-bloodshed", "wuxia", "cantonese", "kung-fu", "kowloon", "category-iii",
                          "tvb")),
        FacetValue("india", "India",
                   terms=("india", "indian", "bollywood", "bombay", "mumbai", "hindi", "tamil", "telugu",
                          "tollywood", "kollywood", "doordarshan", "masala", "bengali", "malayalam",
                          "kannada", "parallel-cinema")),
        FacetValue("latin-america", "Latin America",
                   terms=("mexico", "mexican", "lucha", "latin", "latino", "telenovela", "brazil",
                          "brazilian", "argentina", "argentine", "cuba", "cuban", "chile", "chilean",
                          "colombia", "colombian", "peru", "venezuela", "spanish-language", "univision",
                          "televisa", "cinema-novo", "epoca-de-oro", "cantinflas")),
        FacetValue("soviet", "Soviet Union and Russia",
                   terms=("soviet", "ussr", "russia", "russian", "mosfilm", "lenfilm", "sovcolor",
                          "agitprop", "agitfilm", "cosmic", "moscow", "leningrad", "kino", "thaw",
                          "perestroika", "post-soviet", "ukrainian", "georgian")),
        FacetValue("eastern-europe", "Eastern Europe",
                   terms=("polish", "poland", "czech", "czechoslovak", "czechoslovakia", "hungarian",
                          "hungary", "yugoslav", "yugoslavia", "romanian", "romania", "bulgarian",
                          "bulgaria", "east-german", "defa", "orwo", "eastern-european", "prague",
                          "warsaw", "budapest", "balkan", "black-wave", "moral-anxiety")),
        FacetValue("scandinavia", "Scandinavia and the Nordics",
                   terms=("swedish", "sweden", "danish", "denmark", "dogme", "norwegian", "norway",
                          "finnish", "finland", "icelandic", "iceland", "nordic", "scandinavia",
                          "scandinavian", "stockholm", "copenhagen")),
        FacetValue("spain", "Spain and Portugal",
                   terms=("spain", "spanish", "iberian", "catalan", "madrid", "barcelona", "portuguese",
                          "portugal", "lisbon", "almodovar-era")),
        FacetValue("benelux", "Benelux",
                   terms=("dutch", "netherlands", "holland", "belgian", "belgium", "flemish", "amsterdam",
                          "brussels", "luxembourg")),
        FacetValue("australia", "Australia and New Zealand",
                   terms=("australia", "australian", "ozploitation", "aussie", "new-zealand", "nz",
                          "kiwi", "sydney", "melbourne", "outback")),
        FacetValue("canada", "Canada",
                   terms=("canada", "canadian", "quebec", "quebecois", "tax-shelter", "nfb", "toronto",
                          "montreal", "cbc")),
        FacetValue("china", "China and Taiwan",
                   terms=("china", "chinese", "mainland", "beijing", "shanghai", "fifth-generation",
                          "sixth-generation", "taiwan", "taiwanese", "mandarin", "revolutionary",
                          "cultural-revolution", "cctv-china")),
        FacetValue("korea", "Korea",
                   terms=("korea", "korean", "seoul", "hallyu", "k-drama", "kbs", "mbc", "chungmuro")),
        FacetValue("southeast-asia", "Southeast Asia",
                   terms=("thai", "thailand", "bangkok", "filipino", "philippines", "manila", "indonesian",
                          "indonesia", "jakarta", "vietnamese", "malaysia", "malaysian", "singapore",
                          "singaporean", "cambodian", "burmese")),
        FacetValue("middle-east", "Middle East and Turkey",
                   terms=("iranian", "iran", "tehran", "turkish", "turkey", "istanbul", "yesilcam",
                          "egyptian", "egypt", "cairo", "israeli", "israel", "lebanese", "lebanon",
                          "arab", "arabic", "persian", "bourekas")),
        FacetValue("africa", "Africa",
                   terms=("african", "africa", "nigerian", "nigeria", "nollywood", "lagos", "senegal",
                          "senegalese", "ghana", "ghanaian", "south-africa", "south-african", "kenya",
                          "kenyan", "ethiopian", "malian", "burkina", "algerian", "moroccan", "tunisian")),
    )),
    Facet("condition", "Condition", hint="How well it survived", values=(
        FacetValue("clean", "Clean / first generation",
                   terms=("clean", "pristine", "fresh", "vault", "master", "mint", "restored",
                          "restoration", "archival-scan", "first-generation", "transparent",
                          "source-clean", "original", "new", "polished", "immaculate", "studio-line",
                          "direct", "rehearsal-feed", "source-preserving", "neutral", "lossless",
                          "glossy", "tidy", "quiet")),
        FacetValue("worn", "Worn and faded",
                   terms=("worn", "wear", "dupe", "faded", "fade", "scratched", "dirty", "dust", "splices",
                          "spliced", "tired", "well-traveled", "grindhouse", "rental", "library-print",
                          "pink", "magenta", "vinegar", "tea-stain", "yellowed", "aged", "aging",
                          "well-worn", "survivor", "battered", "mileage", "beat-up", "seasoned")),
        FacetValue("damaged", "Damaged and decayed",
                   terms=("damaged", "damage", "torn", "burn", "burned", "burnt", "tracking",
                          "dropouts", "skew", "storm", "shredded", "jam", "jammed", "jamming", "corrupt",
                          "corruption", "glitch", "broken", "mistrack", "sticky-shed", "mold", "moldy",
                          "mildew", "water-damaged", "water-damage", "flood", "decay", "decayed",
                          "decomposition", "melting", "terminal", "nightmare", "rescued", "crease",
                          "creased", "chewed", "eaten", "ruined", "wrecked", "mangled")),
        FacetValue("multi-gen", "Copy of a copy",
                   terms=("dub", "generation", "generations", "bootleg", "copy", "copy-of-a-copy",
                          "fansub", "third-gen", "fourth-gen", "fifth-gen", "re-upload", "reupload",
                          "screener", "cam", "telesync", "pirated", "pirate", "tape-traded", "dubbed-copy",
                          "reissue", "syndication-copy", "off-air", "re-encode", "rip", "ripped",
                          "generation-loss", "multi-gen", "nth-gen")),
        FacetValue("weak-signal", "Weak signal and interference",
                   terms=("snow", "snowy", "ghost", "ghosting", "rf", "dx", "skip", "interference",
                          "weak-signal", "multipath", "herringbone", "static", "antenna", "rabbit-ears",
                          "fringe", "reception", "skywave", "sparklies", "rain-fade", "co-channel",
                          "hum-bar", "jamming", "sporadic-e", "distant")),
        FacetValue("low-bitrate", "Crushed by compression",
                   terms=("low-bitrate", "blocky", "macroblock", "macroblocks", "blocks", "compression",
                          "compressed", "artifacted", "mush", "240p", "144p", "360p", "postage-stamp",
                          "codec", "mosquito", "banding", "swirl", "pixelated", "pixelation", "tiling",
                          "buffering", "freeze", "3gp", "flv", "realplayer", "mpeg-1", "mpeg1", "vcd",
                          "deep-fried", "re-encoded", "over-compressed")),
    )),
    Facet("color", "Color", hint="Black and white, color or tinted", values=(
        FacetValue("bw", "Black and white",
                   terms=("bw", "monochrome", "mono-picture", "silver", "grayscale", "greyscale",
                          "orthochromatic", "ortho", "panchromatic"),
                   audio_only=False),
        FacetValue("tinted", "Tinted and toned",
                   terms=("tinted", "tint", "toned", "sepia", "cyanotype", "hand-colored", "hand-tinted",
                          "stencil", "amber-tint", "blue-tint"),
                   audio_only=False),
        FacetValue("color", "Color", terms=(), audio_only=False),
    )),
)

FACET_BY_ID: dict[str, Facet] = {f.id: f for f in FACETS}


# ── synonyms (query expansion) ───────────────────────────────────────────

# token -> tokens that should also count as a hit. Kept deliberately narrow:
# a synonym that fires on too many presets makes every search return the
# library. Decade words are generated, not listed.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "bw": ("monochrome", "silver", "black-and-white"),
    "monochrome": ("bw",),
    "colour": ("color",),
    "movie": ("film", "feature", "picture"),
    "movies": ("film", "feature", "picture"),
    "film": ("movie", "feature"),
    "flick": ("film", "feature", "movie"),
    "picture": ("film", "feature"),
    "feature": ("film", "movie"),
    "cinema": ("theatrical", "film", "projection"),
    "theatrical": ("cinema", "release-print", "answer-print"),
    "tv": ("television", "broadcast"),
    "television": ("tv", "broadcast"),
    "telly": ("tv", "television", "broadcast"),
    "show": ("tv", "program", "series"),
    "series": ("tv", "show"),
    "channel": ("network", "station", "broadcast"),
    "network": ("channel", "broadcast", "tv"),
    "station": ("channel", "broadcast", "radio"),
    "tape": ("vhs", "videotape", "cassette"),
    "videotape": ("vhs", "tape"),
    "video": ("videotape", "tape", "camcorder", "vhs", "video-digital"),
    "vcr": ("vhs", "videotape"),
    "beta": ("betamax",),
    "camcorder": ("home-video", "handycam", "palmcorder"),
    "handycam": ("camcorder",),
    "phone": ("cellphone", "smartphone", "telephone", "mobile"),
    "mobile": ("phone", "cellphone", "smartphone"),
    "iphone": ("smartphone", "phone"),
    "android": ("smartphone", "phone"),
    "smartphone": ("phone", "cellphone", "vertical"),
    "cellphone": ("phone", "mobile", "3gp"),
    "computer": ("pixel", "vga", "terminal", "monitor"),
    "pc": ("pixel", "vga", "computer"),
    "game": ("pixel", "console", "arcade", "games"),
    "gaming": ("pixel", "console", "arcade", "games", "twitch"),
    "videogame": ("pixel", "console", "arcade"),
    "console": ("pixel", "games"),
    "nintendo": ("gameboy", "console", "pixel"),
    "playstation": ("fmv", "console", "pixel"),
    "internet": ("web", "streaming", "upload"),
    "online": ("web", "streaming", "upload"),
    "youtube": ("web", "web-video", "upload", "streaming"),
    "stream": ("streaming", "web"),
    "streamer": ("twitch", "streaming", "webcam"),
    "livestream": ("streaming", "web", "twitch"),
    "meme": ("deep-fried", "cursed", "upload", "web"),
    "toon": ("cartoon", "animation"),
    "cartoon": ("animation", "cel", "toon"),
    "animated": ("animation", "cartoon", "cel"),
    "animation": ("cartoon", "cel"),
    "anime": ("animation", "cel", "japan", "ova"),
    "manga": ("anime", "comic", "screentone"),
    "claymation": ("stop-motion", "clay"),
    "puppet": ("stop-motion", "puppets", "supermarionation"),
    "cgi": ("computer", "digital", "3d"),
    "3d": ("cgi", "anaglyph"),
    "monster": ("kaiju", "creature", "horror"),
    "monsters": ("kaiju", "creature", "horror"),
    "godzilla": ("kaiju", "tokusatsu", "japan"),
    "kaiju": ("tokusatsu", "monster", "giant-monster"),
    "tokusatsu": ("kaiju", "sentai", "japan"),
    "scary": ("horror", "creepy", "unsettling"),
    "spooky": ("horror", "creepy", "eerie", "haunted"),
    "creepy": ("horror", "unsettling", "eerie"),
    "haunted": ("horror", "ghost", "paranormal"),
    "zombie": ("horror", "undead"),
    "vampire": ("horror", "gothic"),
    "slasher": ("horror",),
    "gore": ("horror", "splatter", "grindhouse"),
    "scifi": ("space", "science-fiction", "future"),
    "space": ("scifi", "nasa", "cosmic"),
    "alien": ("scifi", "space"),
    "robot": ("scifi", "android"),
    "cyberpunk": ("scifi", "neon", "dystopia"),
    "apocalypse": ("post-apocalyptic", "wasteland", "dystopia"),
    "apocalyptic": ("post-apocalyptic", "wasteland", "dystopia"),
    "spy": ("espionage", "agent", "thriller", "caper"),
    "espionage": ("spy", "agent", "thriller"),
    "detective": ("noir", "crime", "mystery"),
    "gangster": ("crime", "noir", "mob"),
    "mob": ("gangster", "crime"),
    "cop": ("police", "crime", "buddy-cop", "procedural"),
    "cops": ("police", "crime", "ride-along", "reality"),
    "police": ("cop", "crime", "procedural", "evidence"),
    "heist": ("crime", "caper"),
    "thriller": ("crime", "suspense", "conspiracy"),
    "suspense": ("thriller", "crime"),
    "noir": ("crime", "detective", "shadows"),
    "romance": ("drama", "romantic", "melodrama"),
    "romantic": ("romance", "romcom", "melodrama"),
    "love": ("romance", "romantic", "romcom"),
    "funny": ("comedy", "sitcom", "slapstick"),
    "comedy": ("sitcom", "slapstick", "screwball"),
    "sitcom": ("comedy", "multicam"),
    "cowboy": ("western", "sagebrush"),
    "cowboys": ("western", "sagebrush"),
    "western": ("cowboy", "sagebrush", "frontier"),
    "sword": ("sword-and-sorcery", "fantasy", "samurai", "peplum", "swashbuckler"),
    "swords": ("sword-and-sorcery", "fantasy", "samurai", "swashbuckler"),
    "dragon": ("fantasy", "sword-and-sorcery"),
    "wizard": ("fantasy", "sword-and-sorcery", "magical"),
    "medieval": ("fantasy", "period", "sword-and-sorcery", "historical"),
    "pirate": ("swashbuckler", "adventure", "bootleg"),
    "pirates": ("swashbuckler", "adventure"),
    "jungle": ("adventure", "safari", "expedition"),
    "explorer": ("adventure", "expedition"),
    "indiana": ("adventure", "matinee", "serial"),
    "adventure": ("matinee", "serial", "swashbuckler"),
    "action": ("blockbuster", "stunt", "chase"),
    "explosions": ("action", "blockbuster"),
    "blockbuster": ("action", "spectacle", "epic"),
    "epic": ("roadshow", "scope", "spectacle", "widescreen"),
    "spectacle": ("epic", "roadshow"),
    "war": ("combat", "wartime", "military"),
    "army": ("military", "war", "combat", "signal-corps"),
    "soldier": ("war", "combat", "military"),
    "soldiers": ("war", "combat", "military"),
    "battle": ("war", "combat"),
    "vietnam": ("war", "combat", "seventies", "sixties"),
    "wwii": ("war", "wartime", "forties", "1940s"),
    "ww2": ("war", "wartime", "forties", "1940s"),
    "propaganda": ("war", "agitprop", "wartime"),
    "musical": ("music", "song", "dance"),
    "concert": ("music", "live", "performance", "gig"),
    "gig": ("concert", "music", "punk", "club"),
    "band": ("music", "concert", "promo"),
    "song": ("music", "musical"),
    "singer": ("music", "musical", "performance", "idol"),
    "mtv": ("music-video", "music-tv", "countdown"),
    "dance": ("music", "disco", "dance-show"),
    "dj": ("music", "rave", "mixtape", "radio"),
    "rave": ("music", "techno", "warehouse"),
    "hiphop": ("hip-hop", "rap", "music"),
    "rap": ("hip-hop", "music"),
    "rocker": ("rock", "music"),
    "documentary": ("doc", "verite", "actuality", "newsreel"),
    "doc": ("documentary", "verite"),
    "docu": ("documentary", "doc"),
    "reportage": ("news", "documentary", "newsreel"),
    "journalism": ("news", "reportage"),
    "journalist": ("news", "reportage", "reporter"),
    "reporter": ("news", "eyewitness", "local-news"),
    "anchor": ("news", "newsdesk"),
    "newscast": ("news", "local-news", "network-news"),
    "headlines": ("news",),
    "weatherman": ("weather", "forecast", "news"),
    "forecast": ("weather",),
    "sport": ("sports",),
    "sports": ("sport", "game", "match", "arena"),
    "football": ("sports", "nfl", "soccer", "stadium"),
    "soccer": ("sports", "football", "match", "stadium"),
    "basketball": ("sports", "nba", "arena"),
    "baseball": ("sports", "ballpark"),
    "hockey": ("sports", "arena"),
    "boxing": ("sports", "arena", "fight"),
    "fight": ("boxing", "wrestling", "martial-arts", "kung-fu"),
    "fighting": ("boxing", "wrestling", "martial-arts", "kung-fu"),
    "wrestling": ("sports", "arena", "lucha"),
    "gym": ("fitness", "aerobics", "workout", "gymnasium"),
    "exercise": ("fitness", "aerobics", "workout"),
    "skating": ("skate", "skateboard"),
    "skateboard": ("skate", "skateboarding"),
    "surfing": ("surf",),
    "ad": ("commercial", "advert", "spot"),
    "ads": ("commercial", "advert", "spot", "commercials"),
    "advert": ("commercial", "ad", "spot"),
    "advertisement": ("commercial", "ad", "spot"),
    "advertising": ("commercial", "ad", "spot"),
    "commercial": ("ad", "advert", "spot", "jingle"),
    "infomercial": ("commercial", "shopping", "cable"),
    "trailer": ("promo", "commercial", "trailers"),
    "promo": ("music-video", "commercial", "trailer", "promotional"),
    "kids": ("children", "saturday-morning", "cartoon", "family"),
    "kid": ("kids", "children", "family"),
    "children": ("kids", "family", "saturday-morning"),
    "childrens": ("kids", "children", "family"),
    "childhood": ("kids", "nostalgia", "saturday-morning", "home-movie"),
    "toy": ("kids", "commercial", "toys"),
    "school": ("classroom", "educational", "instructional"),
    "educational": ("classroom", "instructional", "training"),
    "training": ("industrial", "educational", "instructional", "corporate"),
    "instructional": ("educational", "training", "classroom"),
    "corporate": ("industrial", "training", "keynote", "presentation"),
    "office": ("corporate", "fluorescent", "dictation", "industrial"),
    "government": ("public-information", "civil-defense", "institutional"),
    "church": ("religious", "televangelist", "sermon", "cathedral"),
    "religious": ("church", "televangelist", "sermon"),
    "preacher": ("televangelist", "religious", "sermon"),
    "wedding": ("home-video", "home-movie", "ceremony"),
    "vacation": ("home-movie", "travelogue", "holiday"),
    "holiday": ("vacation", "home-movie", "christmas", "travelogue"),
    "christmas": ("holiday", "holiday-special", "home-movie"),
    "family": ("home-movie", "home-video", "kids"),
    "amateur": ("home-movie", "home-video", "student"),
    "homemade": ("home-movie", "home-video", "amateur"),
    "birthday": ("home-video", "home-movie", "party"),
    "party": ("home-video", "rave", "club"),
    "vlog": ("youtube", "webcam", "social", "web"),
    "selfie": ("smartphone", "vertical", "social", "webcam"),
    "vertical": ("smartphone", "9:16", "social", "tiktok"),
    "security": ("cctv", "surveillance", "timestamp"),
    "cctv": ("surveillance", "security", "closed-circuit"),
    "surveillance": ("cctv", "security", "evidence"),
    "camera": ("camcorder", "cctv", "film", "photo"),
    "footage": ("archive", "documentary", "found-footage"),
    "evidence": ("bodycam", "dashcam", "surveillance", "security"),
    "night": ("night-vision", "low-light", "dark", "noir", "neon"),
    "dark": ("night", "low-light", "moody", "crushed"),
    "infrared": ("night-vision", "nightshot", "ir"),
    "nightvision": ("night-vision", "nightshot", "infrared"),
    "liminal": ("cctv", "empty", "eerie", "backrooms"),
    "backrooms": ("liminal", "cctv", "eerie"),
    "talkshow": ("talk-show", "talk", "late-night"),
    "gameshow": ("game-show", "quiz"),
    "quiz": ("game-show", "contest"),
    "soap": ("soap-opera", "daytime", "telenovela", "melodrama"),
    "telenovela": ("soap-opera", "latin", "melodrama"),
    "sitcoms": ("sitcom", "comedy", "multicam"),
    "drama": ("melodrama", "prestige", "arthouse"),
    "arthouse": ("art-film", "drama", "festival"),
    "artsy": ("arthouse", "art-film", "experimental"),
    "indie": ("independent", "sundance", "super16", "drama"),
    "independent": ("indie", "sundance"),
    "student": ("student-film", "16mm", "amateur"),
    "experimental": ("avant-garde", "underground", "abstract"),
    "psychedelic": ("optical", "sixties", "trippy", "experimental"),
    "trippy": ("psychedelic", "optical", "experimental"),
    "glitch": ("datamosh", "corruption", "damaged", "digital"),
    "glitchy": ("glitch", "datamosh", "corruption", "damaged"),
    "broken": ("damaged", "glitch", "tracking", "corrupt"),
    "ruined": ("damaged", "decayed", "decay"),
    "rotten": ("decayed", "decay", "mold", "vinegar"),
    "rotting": ("decayed", "decay", "mold", "vinegar"),
    "melted": ("nitrate", "melting", "decay"),
    "burnt": ("burn", "burned", "fire"),
    "fire": ("burn", "burned", "burnt"),
    "wet": ("water-damage", "flood", "damp"),
    "flooded": ("water-damage", "flood"),
    "old": ("worn", "faded", "aged", "vintage", "archive"),
    "aged": ("worn", "faded", "old"),
    "vintage": ("retro", "old", "worn", "nostalgia"),
    "retro": ("vintage", "nostalgia", "old"),
    "faded": ("fade", "worn", "pink", "eastman"),
    "washed": ("faded", "fade", "worn", "lifted"),
    "grainy": ("grain", "16mm", "pushed", "push-process"),
    "grain": ("grainy", "film"),
    "dirty": ("dust", "dirt", "grime", "worn"),
    "scratchy": ("scratches", "scratched", "worn"),
    "scratched": ("scratches", "worn"),
    "clean": ("pristine", "master", "restored", "source-clean"),
    "pristine": ("clean", "master", "restored", "vault"),
    "restored": ("restoration", "clean", "rescued", "archival-scan"),
    "hq": ("clean", "master", "pristine"),
    "crisp": ("clean", "sharp"),
    "sharp": ("crisp", "clean", "sharpen"),
    "blurry": ("soft", "soft-focus", "diffusion", "smeared"),
    "blur": ("soft", "soft-focus", "diffusion"),
    "soft": ("soft-focus", "diffusion", "dreamy"),
    "dreamy": ("soft-focus", "diffusion", "pastel", "halation", "dreamlike"),
    "hazy": ("haze", "diffusion", "veiling-flare", "smoke"),
    "smoky": ("smoke", "haze", "diffusion"),
    "foggy": ("fog", "haze", "diffusion", "mist"),
    "glow": ("halation", "bloom", "glass-glow"),
    "glowing": ("halation", "bloom", "neon"),
    "neon": ("night", "cyberpunk", "eighties", "synthwave"),
    "pastel": ("soft", "pink", "mint", "sixties", "pop"),
    "saturated": ("vivid", "technicolor", "candy", "punchy"),
    "vivid": ("saturated", "technicolor", "vibrant"),
    "colorful": ("saturated", "technicolor", "vivid"),
    "muted": ("desaturated", "drab", "restrained", "gray"),
    "desaturated": ("muted", "drab", "bleach-bypass", "gray"),
    "drab": ("muted", "desaturated", "gray", "orwo"),
    "gritty": ("grain", "pushed", "grindhouse", "raw", "street"),
    "raw": ("gritty", "verite", "unpolished"),
    "lofi": ("low-fi", "degraded", "cheap", "hiss"),
    "cheap": ("lofi", "degraded", "budget", "public-access"),
    "budget": ("cheap", "b-movie", "poverty-row", "exploitation"),
    "bmovie": ("b-movie", "drive-in", "exploitation", "creature"),
    "exploitation": ("grindhouse", "drive-in", "b-movie"),
    "grindhouse": ("exploitation", "worn", "42nd-street", "damaged"),
    "bootleg": ("dub", "generation", "pirated", "copy", "cam"),
    "pirated": ("bootleg", "cam", "rip", "copy"),
    "rip": ("bootleg", "encode", "divx", "web"),
    "dub": ("generation", "copy", "bootleg", "dubbed"),
    "dubbed": ("dub", "generation", "optical", "italian", "hong-kong"),
    "copy": ("dub", "generation", "bootleg", "photocopy"),
    "generation": ("dub", "copy", "bootleg", "multi-gen"),
    "compression": ("codec", "blocky", "low-bitrate", "compressed"),
    "compressed": ("codec", "blocky", "low-bitrate"),
    "blocky": ("macroblock", "codec", "low-bitrate", "pixelated"),
    "pixelated": ("pixel", "blocky", "low-bitrate"),
    "pixel": ("pixelated", "8-bit", "retro-game"),
    "digital": ("codec", "dv", "hd", "web", "video-digital"),
    "analog": ("tape", "film", "vhs", "broadcast", "ntsc"),
    "analogue": ("analog", "tape", "film", "vhs"),
    "static": ("snow", "rf", "interference", "noise"),
    "snowy": ("snow", "rf", "weak-signal"),
    "noisy": ("noise", "snow", "hiss", "grain"),
    "noise": ("hiss", "snow", "grain", "static"),
    "hiss": ("tape", "noise", "cassette"),
    "hum": ("mains", "buzz", "60hz", "hum-bar"),
    "buzz": ("hum", "mains", "intercarrier"),
    "signal": ("rf", "broadcast", "reception", "antenna"),
    "reception": ("rf", "antenna", "signal", "weak-signal"),
    "interference": ("rf", "herringbone", "jamming", "static"),
    "ghost": ("ghosting", "multipath", "rf"),
    "distant": ("dx", "shortwave", "weak-signal", "skywave"),
    "widescreen": ("scope", "2.35", "1.85", "16:9", "letterbox", "anamorphic"),
    "letterbox": ("widescreen", "scope", "2.35"),
    "cinemascope": ("scope", "widescreen", "anamorphic"),
    "anamorphic": ("scope", "widescreen", "panavision", "flare"),
    "fullscreen": ("4:3", "pan-and-scan", "tv"),
    "square": ("1:1", "instagram", "social"),
    "portrait": ("9:16", "vertical", "smartphone"),
    "silent": ("intertitle", "nitrate", "hand-cranked", "1910s", "1920s"),
    "talkie": ("early-sound", "optical", "1929", "1930s"),
    "thirties": ("30s", "1930s"),
    "sepia": ("tinted", "toned", "brown", "old"),
    "tint": ("tinted", "toned"),
    "hand": ("hand-colored", "hand-tinted", "hand-cranked"),
    "newsreel": ("news", "documentary", "wartime", "actuality"),
    "archive": ("archival", "footage", "documentary", "vault"),
    "archival": ("archive", "footage", "restoration"),
    "historical": ("period", "archive", "costume", "epic"),
    "period": ("historical", "costume", "prestige"),
    "prestige": ("period", "miniseries", "quality", "drama"),
    "hbo": ("premium", "cable", "prestige"),
    "premium": ("cable", "pay-tv", "movie-channel"),
    "cable": ("broadcast", "tv", "channel", "public-access"),
    "satellite": ("feed", "c-band", "ku-band", "broadcast"),
    "local": ("regional", "local-news", "local-tv", "uhf"),
    "regional": ("local", "local-tv", "regional-tv"),
    "public": ("pbs", "public-television", "public-access", "public-service"),
    "pbs": ("public-television", "pledge", "educational"),
    "bbc": ("british", "public-service", "uk", "television"),
    "japanese": ("japan",),
    "italian": ("italy",),
    "french": ("france",),
    "german": ("germany",),
    "british": ("uk", "england"),
    "english": ("uk", "british", "england"),
    "american": ("usa", "hollywood"),
    "russian": ("soviet", "russia"),
    "chinese": ("china", "hong-kong", "taiwan"),
    "korean": ("korea",),
    "indian": ("india", "bollywood"),
    "mexican": ("mexico", "latin-america"),
    "spanish": ("spain", "latin-america", "spanish-language"),
    "european": ("euro", "france", "italy", "germany", "eastern-europe"),
    "euro": ("european", "france", "italy", "germany"),
    "asian": ("japan", "hong-kong", "china", "korea", "india", "southeast-asia"),
    "africa": ("african", "nollywood"),
    "nollywood": ("nigeria", "nigerian", "shot-on-video"),
    "bollywood": ("india", "indian", "masala", "musical"),
    "hollywood": ("usa", "american", "studio"),
    "toho": ("kaiju", "japan", "tokusatsu"),
    "shaw": ("hong-kong", "shawscope", "kung-fu"),
    "hammer": ("british", "gothic", "horror", "eastmancolor"),
    "disney": ("animation", "cel", "multiplane", "kids"),
    "pixar": ("cgi", "animation", "digital"),
    "ghibli": ("anime", "theatrical", "cel", "watercolor"),
    "akira": ("anime", "theatrical", "cel"),
    "corman": ("drive-in", "b-movie", "gothic", "exploitation"),
    "spielberg": ("adventure", "eighties", "suburban", "backlit"),
    "amblin": ("adventure", "eighties", "suburban", "backlit"),
    "lucas": ("space-opera", "scifi", "seventies"),
    "kubrick": ("clean", "symmetrical", "65mm", "candlelight"),
    "lynch": ("dreamy", "soap-opera", "small-town", "surreal"),
    "hitchcock": ("thriller", "suspense", "vistavision", "technicolor"),
    "tarantino": ("grindhouse", "exploitation", "seventies", "35mm"),
    "wes": ("storybook", "symmetrical", "pastel", "whimsy"),
    "anderson": ("storybook", "symmetrical", "pastel", "whimsy"),
    "malick": ("magic-hour", "golden", "backlit", "natural-light"),
    "fincher": ("green", "yellow", "digital", "desaturated", "silver-retention"),
    "mann": ("digital", "night", "sodium", "los-angeles"),
    "scott": ("smoke", "backlit", "neon", "anamorphic"),
    "bergman": ("chamber", "sweden", "swedish", "faces"),
    "godard": ("nouvelle-vague", "france", "french", "jump-cut"),
    "fellini": ("italy", "italian", "arthouse", "circus"),
    "kurosawa": ("samurai", "japan", "japanese", "widescreen"),
    "ozu": ("japan", "japanese", "agfa", "quiet"),
    "tarkovsky": ("soviet", "slow-cinema", "poetic", "sovcolor"),
    "sirk": ("melodrama", "technicolor", "fifties", "lush"),
    "argento": ("giallo", "italy", "italian", "primaries"),
    "bava": ("giallo", "euro-horror", "gothic", "italy"),
    "romero": ("zombie", "horror", "16mm", "seventies"),
    "carpenter": ("slasher", "horror", "panavision", "synth"),
    "cronenberg": ("body-horror", "canadian", "clinical"),
    "woo": ("heroic-bloodshed", "hong-kong", "action"),
    "wong": ("step-print", "hong-kong", "neon", "nineties"),
    "miyazaki": ("anime", "ghibli", "theatrical", "cel"),
    "stranger": ("eighties", "pastiche", "nostalgia", "synth"),
    "twin": ("dreamy", "soap-opera", "small-town", "surreal"),
    "peaks": ("dreamy", "soap-opera", "small-town", "surreal"),
    "miami": ("pastel", "eighties", "cop", "neon"),
    "vice": ("pastel", "eighties", "cop", "neon"),
    "sopranos": ("prestige", "cable", "35mm", "warm"),
    "wire": ("prestige", "cable", "super16", "baltimore"),
    "simpsons": ("cartoon", "primetime", "cel", "nineties"),
    "seinfeld": ("sitcom", "multicam", "nineties"),
    "friends": ("sitcom", "multicam", "nineties", "warm"),
    "office": ("mockumentary", "single-camera", "hd", "corporate"),
    "matrix": ("green", "digital-green", "scifi", "cyber"),
    "bladerunner": ("cyberpunk", "neon", "smoke", "eighties"),
    "runner": ("cyberpunk", "neon", "smoke", "eighties"),
    "terminator": ("scifi", "eighties", "blue", "action"),
    "rambo": ("action", "eighties", "commando", "jungle"),
    "rocky": ("sports", "boxing", "seventies", "philadelphia"),
    "jaws": ("adventure", "seventies", "summer", "panavision"),
    "goonies": ("adventure", "eighties", "kids", "amblin"),
    "gremlins": ("eighties", "amblin", "kids", "horror-comedy"),
    "ghostbusters": ("eighties", "comedy", "scifi", "panavision"),
    "alien": ("scifi", "space", "horror", "smoke"),
    "predator": ("action", "jungle", "eighties", "scifi"),
    "conan": ("sword-and-sorcery", "barbarian", "eighties"),
    "krull": ("sword-and-sorcery", "fantasy", "eighties"),
    "willow": ("fantasy", "eighties", "sword-and-sorcery"),
    "labyrinth": ("fantasy", "puppet", "eighties"),
    "neverending": ("fantasy", "eighties", "kids"),
    "tron": ("cgi", "eighties", "neon", "computer"),
    "wargames": ("computer", "eighties", "terminal", "cold-war"),
    "hackers": ("cyber", "nineties", "neon", "computer"),
    "scream": ("slasher", "nineties", "teen", "horror"),
    "halloween": ("slasher", "horror", "seventies", "panavision"),
    "friday": ("slasher", "horror", "eighties", "camp"),
    "nightmare": ("slasher", "horror", "eighties", "dream"),
    "evil": ("horror", "16mm", "cabin", "eighties"),
    "dead": ("zombie", "horror", "evil"),
    "poltergeist": ("horror", "suburban", "eighties", "amblin"),
    "blair": ("found-footage", "hi8", "16mm", "horror"),
    "witch": ("found-footage", "horror", "folk-horror"),
    "paranormal": ("found-footage", "horror", "night-vision", "reality"),
    "cloverfield": ("found-footage", "kaiju", "hd", "camcorder"),
    "saw": ("torture", "horror", "green", "aughts"),
    "hostel": ("torture", "horror", "aughts"),
    "ring": ("j-horror", "vhs", "horror", "cursed"),
    "grudge": ("j-horror", "horror", "dv"),
    "bourne": ("shaky", "spy", "aughts", "desaturated"),
    "bond": ("spy", "espionage", "action", "caper"),
    "mission": ("spy", "action", "nasa"),
    "impossible": ("spy", "action"),
    "diehard": ("action", "eighties", "blockbuster"),
    "lethal": ("buddy-cop", "action", "eighties"),
    "weapon": ("buddy-cop", "action", "eighties"),
    "topgun": ("action", "eighties", "sunset", "anamorphic"),
    "gun": ("action", "shootout", "western", "crime"),
    "jurassic": ("family-adventure", "nineties", "adventure", "dinosaur"),
    "titanic": ("epic", "nineties", "romance", "period"),
    "independence": ("disaster", "nineties", "scifi", "blockbuster"),
    "twister": ("disaster", "nineties", "blockbuster"),
    "armageddon": ("disaster", "nineties", "bruckheimer", "action"),
    "bruckheimer": ("action", "nineties", "bleach", "orange"),
    "bay": ("action", "nineties", "orange", "teal"),
    "lotr": ("fantasy", "epic", "aughts", "digital-intermediate"),
    "rings": ("fantasy", "epic", "aughts"),
    "potter": ("fantasy", "aughts", "kids", "british"),
    "avatar": ("3d", "digital-cinema", "aughts", "saturated"),
    "marvel": ("superhero", "digital", "teal-orange", "blockbuster"),
    "superhero": ("action", "blockbuster", "comic", "digital"),
    "batman": ("superhero", "deco", "dark", "animated"),
    "spiderman": ("superhero", "aughts", "digital-intermediate"),
    "star": ("space-opera", "scifi", "star-wars", "star-trek"),
    "wars": ("space-opera", "scifi", "seventies", "optical"),
    "trek": ("scifi", "space", "television", "sixties"),
    "doctor": ("british", "videotape", "scifi", "public-service"),
    "who": ("british", "videotape", "scifi", "public-service"),
    "muppets": ("puppet", "variety", "seventies", "kids"),
    "sesame": ("kids", "educational", "public-television", "seventies"),
    "nickelodeon": ("kids-cable", "slime", "nineties", "cartoon"),
    "nick": ("kids-cable", "slime", "nineties", "cartoon"),
    "cartoon-network": ("kids-cable", "cartoon", "nineties"),
    "toonami": ("anime", "cable", "nineties", "dub"),
    "adult": ("late-night", "animation", "cable", "aughts"),
    "swim": ("late-night", "animation", "cable", "aughts"),
    "cnn": ("cable-news", "news", "satellite", "24-hour"),
    "espn": ("sports", "cable", "arena"),
    "qvc": ("shopping", "cable", "home-shopping"),
    "hsn": ("shopping", "cable", "home-shopping"),
    "cspan": ("legislative", "hearing", "c-band", "static-camera"),
    "weather-channel": ("weather", "cable", "forecast"),
    "discovery": ("documentary", "cable", "nature", "nineties"),
    "history": ("documentary", "cable", "archive"),
    "nhk": ("japan", "public-broadcaster", "television"),
    "rai": ("italy", "television", "variety"),
    "zdf": ("germany", "public-television"),
    "ard": ("germany", "public-television"),
    "doordarshan": ("india", "state-television", "pal"),
    "televisa": ("mexico", "telenovela", "latin-america"),
    "univision": ("spanish-language", "telenovela", "latin-america"),
    "polaroid": ("instant", "photo", "print", "seventies"),
    "instant": ("polaroid", "photo"),
    "photo": ("photograph", "print", "polaroid", "snapshot"),
    "photograph": ("photo", "print", "snapshot"),
    "instagram": ("social", "square", "filter", "web"),
    "insta": ("instagram", "social", "square", "filter"),
    "tiktok": ("vertical", "social", "web", "smartphone"),
    "snapchat": ("vertical", "social", "web", "smartphone"),
    "vine": ("social", "square", "loop", "web"),
    "twitch": ("streaming", "gaming", "webcam", "web"),
    "zoom": ("video-call", "webcam", "streaming", "web"),
    "skype": ("video-call", "webcam", "voip", "web"),
    "facetime": ("video-call", "smartphone", "web"),
    "webcam": ("web", "laptop", "video-call"),
    "msn": ("webcam", "web", "aughts"),
    "myspace": ("web", "aughts", "upload"),
    "napster": ("mp3", "aughts", "web"),
    "limewire": ("mp3", "aughts", "web", "divx"),
    "torrent": ("rip", "divx", "xvid", "bootleg"),
    "divx": ("rip", "mpeg4", "aughts", "web"),
    "xvid": ("rip", "mpeg4", "aughts", "web"),
    "realplayer": ("web", "streaming", "nineties", "postage-stamp"),
    "quicktime": ("web", "nineties", "cdrom"),
    "flash": ("web", "flv", "aughts", "animation"),
    "newgrounds": ("flash", "web", "animation", "aughts"),
    "geocities": ("web", "nineties", "gif"),
    "dialup": ("dial-up", "web", "nineties", "modem"),
    "modem": ("dial-up", "web", "nineties"),
    "ipod": ("handheld", "aughts", "earbud", "aac"),
    "psp": ("handheld", "aughts", "codec"),
    "gameboy": ("pixel", "handheld", "lcd", "nintendo"),
    "atari": ("pixel", "console", "arcade", "seventies"),
    "nes": ("pixel", "console", "8-bit", "nintendo"),
    "snes": ("pixel", "console", "16-bit", "nintendo"),
    "sega": ("pixel", "console", "16-bit", "fmv"),
    "genesis": ("pixel", "console", "16-bit", "sega"),
    "amiga": ("pixel", "computer", "demo", "video-toaster"),
    "commodore": ("c64", "pixel", "computer", "eighties"),
    "apple": ("apple2", "pixel", "computer", "macintosh"),
    "macintosh": ("computer", "pixel", "monochrome", "eighties"),
    "dos": ("vga", "pixel", "computer", "nineties"),
    "windows": ("computer", "wmv", "screen-recording", "webcam"),
    "vga": ("pixel", "computer", "256-color"),
    "cga": ("pixel", "computer", "cyan", "magenta"),
    "teletext": ("ceefax", "captions", "videotex", "pixel"),
    "ceefax": ("teletext", "captions", "british"),
    "vhs": ("videotape", "tape", "rental", "camcorder"),
    "betamax": ("beta", "videotape", "tape"),
    "laserdisc": ("disc", "ld", "eighties", "composite"),
    "dvd": ("disc", "mpeg2", "aughts"),
    "vcd": ("disc", "mpeg1", "nineties", "bootleg"),
    "bluray": ("disc", "hd", "clean"),
    "cassette": ("tape", "walkman", "boombox", "mixtape"),
    "walkman": ("cassette", "tape", "eighties"),
    "boombox": ("cassette", "tape", "eighties", "dub"),
    "mixtape": ("cassette", "tape", "radio", "dub"),
    "vinyl": ("record", "lp", "turntable", "crackle"),
    "record": ("vinyl", "lp", "45", "78", "turntable"),
    "records": ("vinyl", "lp", "45", "78"),
    "turntable": ("vinyl", "record", "lp"),
    "lp": ("vinyl", "record"),
    "78": ("shellac", "gramophone", "record"),
    "shellac": ("78", "gramophone", "record"),
    "gramophone": ("78", "shellac", "horn", "acoustic"),
    "phonograph": ("gramophone", "cylinder", "78"),
    "cylinder": ("wax", "phonograph", "acoustic"),
    "jukebox": ("45", "vinyl", "diner", "fifties"),
    "radio": ("am", "fm", "shortwave", "broadcast", "receiver"),
    "am": ("radio",),
    "fm": ("radio",),
    "shortwave": ("radio", "dx", "distant"),
    "walkie": ("walkie-talkie", "two-way", "radio", "cb"),
    "cb": ("radio", "trucker", "two-way"),
    "scanner": ("police", "radio", "dispatch"),
    "dispatch": ("police", "radio", "two-way", "scanner"),
    "telephone": ("phone", "handset", "landline"),
    "landline": ("telephone", "phone", "rotary"),
    "voicemail": ("answering-machine", "phone", "telephone"),
    "voip": ("skype", "internet", "phone", "codec"),
    "hold": ("hold-music", "phone", "telephone"),
    "pa": ("public-address", "loudspeaker", "announcement", "bullhorn"),
    "megaphone": ("bullhorn", "pa"),
    "bullhorn": ("megaphone", "pa"),
    "intercom": ("pa", "school", "buzz", "speaker"),
    "announcement": ("pa", "intercom", "airport", "subway"),
    "airport": ("pa", "announcement", "terminal"),
    "subway": ("pa", "transit", "announcement"),
    "stadium": ("pa", "arena", "sports", "crowd"),
    "arena": ("stadium", "concert", "wrestling", "sports"),
    "speaker": ("playback", "tv-speaker", "boombox", "laptop"),
    "speakers": ("speaker", "playback", "laptop"),
    "headphones": ("earbuds", "walkman", "playback"),
    "earbuds": ("earbud", "ipod", "playback"),
    "bluetooth": ("speaker", "wireless", "aac", "phone"),
    "alexa": ("smart-speaker", "kitchen", "aac"),
    "echo": ("smart-speaker", "slap", "reverb"),
    "reverb": ("room", "hall", "echo", "chamber"),
    "reverby": ("reverb", "room", "hall", "echo"),
    "echoey": ("reverb", "room", "hall", "echo", "slap"),
    "room": ("reverb", "hall", "space", "playback-space"),
    "hall": ("reverb", "room", "gymnasium", "auditorium"),
    "cathedral": ("church", "reverb", "chamber"),
    "muffled": ("through-the-wall", "next-door", "bandlimit", "lowpass"),
    "wall": ("through-the-wall", "next-door", "muffled"),
    "underwater": ("muffled", "lowpass", "wobble"),
    "tinny": ("speaker", "transistor", "pocket", "telephone"),
    "thin": ("tinny", "bandlimit", "telephone", "am"),
    "warbly": ("wow", "flutter", "wobble", "tape"),
    "wobbly": ("wow", "flutter", "warbly", "tape"),
    "wobble": ("wow", "flutter", "warbly", "tape"),
    "wow": ("flutter", "warbly", "tape", "vinyl"),
    "crackle": ("vinyl", "crackly", "78", "surface"),
    "crackly": ("crackle", "vinyl", "78", "optical"),
    "pops": ("vinyl", "crackle", "record"),
    "skip": ("skipping", "cd", "record", "dx"),
    "skipping": ("skip", "cd", "record"),
    "stutter": ("skip", "digital-glitch", "buffer", "freeze"),
    "robotic": ("codec", "bitcrush", "speech-codec", "vocoder"),
    "crunchy": ("bitcrush", "sampler", "8-bit", "distortion"),
    "distorted": ("distortion", "clipping", "overdrive", "fuzz"),
    "clipped": ("distortion", "clipping", "overload"),
    "loud": ("clipping", "compressed", "limiter", "overload"),
    "quiet": ("clean", "low-noise", "restrained"),
    "mono": ("a_mono", "single-channel", "optical"),
    "stereo": ("wide", "hifi", "channel"),
    "hifi": ("stereo", "vhs-hifi", "beta-hifi", "afm"),
    "sample": ("sampler", "bitcrush", "12-bit", "hip-hop"),
    "sampler": ("bitcrush", "12-bit", "8-bit", "hip-hop"),
    "chiptune": ("8-bit", "console", "pixel", "game-audio"),
    "8bit": ("8-bit", "chiptune", "pixel", "bitcrush"),
    "audio": ("audio-only", "sound"),
    "sound": ("audio", "audio-only"),
    "voice": ("speech", "dialogue", "microphone", "telephone"),
    "speech": ("voice", "dialogue", "narration", "telephone"),
    "narration": ("speech", "voice", "documentary", "booth"),
    "microphone": ("mic", "capsule", "historical-mic"),
    "mic": ("microphone", "capsule"),
}


# ── deriving facets for a preset ─────────────────────────────────────────

def is_audio_only(p: Preset) -> bool:
    return p.family == "audio" or not p.video


def _chain_effects(p: Preset) -> set[str]:
    return {eid for eid, _ in p.video} | {eid for eid, _ in p.audio}


def _chain_params(p: Preset) -> set[tuple[str, str, Any]]:
    out: set[tuple[str, str, Any]] = set()
    for eid, params in list(p.video) + list(p.audio):
        for k, v in params.items():
            out.add((eid, k, v))
    return out


def vocabulary_tokens(p: Preset) -> set[str]:
    """The tokens facet rules match against: the preset's own words, not its prose.

    Hyphenated words stay whole here ("c-band" is not "band", "answer-print"
    is not a print), unlike the search tokenizer, which also splits them so a
    typed "kong" still finds Hong Kong. Tags and keywords with spaces are
    folded to hyphens so "music video" meets the term "music-video".
    """
    words: list[str] = [p.id.replace("-", " "), p.name, p.tagline, p.family]
    words.extend(p.tags)
    words.extend(p.keywords)
    toks: set[str] = set()
    for w in words:
        for t in re.split(r"[^a-z0-9\-\.]+", normalize_text(w)):
            t = t.strip("-.")
            if t and t not in _STOP:
                toks.add(t)
        folded = normalize_text(w).strip().replace(" ", "-")
        if folded:
            toks.add(folded)
    return toks


def _mono_amount(p: Preset) -> float:
    amt = 0.0
    for eid, params in p.video:
        if eid == "mono" and params.get("enabled", True):
            amt = max(amt, float(params.get("amount", 1.0)))
    return amt


def _mono_tint(p: Preset) -> tuple[str, float]:
    for eid, params in p.video:
        if eid == "mono":
            return str(params.get("tint", "neutral")), float(params.get("tint_amt", 0.25))
    return "neutral", 0.0


def facets_for(p: Preset) -> dict[str, list[str]]:
    """Place a preset in every facet; values come back in vocabulary order."""
    toks = vocabulary_tokens(p)
    effects = _chain_effects(p)
    params = _chain_params(p)
    audio_only = is_audio_only(p)
    out: dict[str, list[str]] = {}
    for facet in FACETS:
        hits: list[str] = []
        for v in facet.values:
            if v.audio_only is not None and v.audio_only != audio_only:
                continue
            if any(t in toks for t in v.terms) or any(e in effects for e in v.effects) \
                    or any(pr in params for pr in v.params):
                hits.append(v.id)
        out[facet.id] = hits

    # Color is decided by the chain, not by adjectives.
    if not audio_only:
        color: list[str] = []
        mono = _mono_amount(p)
        tint, tint_amt = _mono_tint(p)
        if mono >= 0.85:
            color.append("bw")
            if tint not in ("neutral", "silver") and tint_amt >= 0.3:
                color.append("tinted")
        elif "tinted" in out["color"] and mono < 0.85:
            color.append("tinted")
            color.append("color")
        else:
            color.append("color")
        if "bw" in out["color"] and "bw" not in color:
            # Vocabulary says black and white but the chain does not desaturate:
            # trust the chain (a "bw" tag on a color-capable chain is a lie).
            pass
        out["color"] = color
    else:
        out["color"] = []

    # Family fallbacks so nothing is unfindable through the dropdowns.
    if not out["genre"]:
        fallback = {
            "adjust": "utility", "captions": "utility", "cartoon": "kids",
            "western": "western", "arthouse": "drama", "modern": "aesthetic",
            "stylized": "aesthetic", "decay": None, "print": None,
        }.get(p.family)
        if fallback:
            out["genre"] = [fallback]
    if not audio_only and not out["medium"]:
        out["medium"] = ["film"] if "grain" in effects else []
    return out


def search_text(p: Preset, facets: dict[str, list[str]] | None = None) -> dict[str, str]:
    """Per-field text the search box scores; every field is normalized once here."""
    facets = facets if facets is not None else facets_for(p)
    facet_words: list[str] = []
    for fid, vals in facets.items():
        for vid in vals:
            facet_words.append(vid)
            fv = next((v for v in FACET_BY_ID[fid].values if v.id == vid), None)
            if fv:
                facet_words.append(fv.label)
    return {
        "name": normalize_text(p.name),
        "id": normalize_text(p.id.replace("-", " ")),
        "era": " ".join(era_tokens(p.era)),
        "family": p.family,
        "tagline": normalize_text(p.tagline),
        "tags": " ".join(normalize_text(t) for t in p.tags),
        "keywords": " ".join(normalize_text(k) for k in p.keywords),
        "facets": " ".join(normalize_text(w) for w in facet_words),
        "desc": normalize_text(p.desc),
        "variants": " ".join(normalize_text(f"{v.name} {v.id.replace('-', ' ')}") for v in p.variants),
    }


# Relative weight of a hit in each field. Name and tagline are what a person
# reads; keywords are what they type; prose is the tie-breaker.
FIELD_WEIGHTS: dict[str, float] = {
    "name": 10.0, "tagline": 6.0, "keywords": 5.0, "tags": 4.0, "facets": 3.0,
    "id": 3.0, "era": 3.0, "family": 2.0, "variants": 1.5, "desc": 1.0,
}


# A synonym hit is worth less than the word itself, so "noir" ranks the
# preset called Film Noir above every crime picture the synonym also reaches.
SYNONYM_FACTOR = 0.7
PREFIX_FACTOR = 0.6
NAME_COVERAGE_BONUS = 2.0

Alternatives = list[tuple[str, float]]
QueryGroup = tuple[Alternatives, bool]     # (alternatives, era_only)

_DECADE_WORD_TO_DECADE = {v: k for k, v in _DECADE_WORDS.items()}


def expand_query(query: str) -> list[QueryGroup]:
    """Query -> per token, the alternatives that count and how much:
    "80s adventure" -> [([("80s",1), ("1980s",1), ("eighties",1)], True),
                        ([("adventure",1), ("matinee",.7), ...], False)].

    A decade ("80s", "1980s", "eighties") is a fact about the preset, not a
    word to be found in its prose, so it is scored against the era field only:
    a keyword "eighties" must not outrank a tag "80s" for the same decade.
    """
    groups: list[QueryGroup] = []
    for tok in tokens(query):
        alts: Alternatives = [(tok, 1.0)]
        seen = {tok}
        m = re.fullmatch(r"(\d{2}|\d{4})s", tok)
        dec = None
        if m:
            n = int(m.group(1))
            dec = (1900 + n if n < 100 else n) // 10 * 10
        elif tok in _DECADE_WORD_TO_DECADE:
            dec = _DECADE_WORD_TO_DECADE[tok]
        if dec is not None:
            for t in era_tokens(str(dec)):
                if t != str(dec) and t not in seen:   # "80s" should not match the single year
                    seen.add(t)
                    alts.append((t, 1.0))
            groups.append((alts, True))
            continue
        for syn in SYNONYMS.get(tok, ()):
            if syn not in seen:
                seen.add(syn)
                alts.append((syn, SYNONYM_FACTOR))
        groups.append((alts, False))
    return groups


def score(fields: dict[str, str], groups: list[QueryGroup]) -> float:
    """0 when any token group misses; otherwise the summed weighted hits.

    A group hits when any alternative equals a field token, or is a prefix of
    one (typing "adventur" already finds adventure). Exact beats prefix, the
    typed word beats its synonyms, and the name beats the prose.
    """
    field_tokens = {f: tokens(v) for f, v in fields.items()}
    total = 0.0
    name_hits = 0
    for alts, era_only in groups:
        best = 0.0
        for fname, ftoks in field_tokens.items():
            if era_only and fname != "era":
                continue
            w = FIELD_WEIGHTS.get(fname, 1.0)
            if w <= best:
                continue
            hit = 0.0
            for ft in ftoks:
                for a, factor in alts:
                    if ft == a:
                        hit = max(hit, w * factor)
                    elif len(a) >= 3 and ft.startswith(a):
                        hit = max(hit, w * factor * PREFIX_FACTOR)
            if hit > 0 and fname == "name":
                name_hits += 1
            best = max(best, hit)
        if best <= 0:
            return 0.0
        total += best
    # A query that covers most of a short name beats one word buried in a long
    # one: "noir" is Film Noir before it is Trip-Hop Noir Promo.
    n_name = len(set(field_tokens.get("name", ()))) or 1
    total += NAME_COVERAGE_BONUS * name_hits / n_name
    return total


def search(presets: Iterable[Preset], query: str) -> list[tuple[float, Preset]]:
    groups = expand_query(query)
    if not groups:
        return [(0.0, p) for p in presets]
    hits = []
    for p in presets:
        s = score(search_text(p), groups)
        if s > 0:
            hits.append((s, p))
    hits.sort(key=lambda t: (-t[0], t[1].id))
    return hits


def taxonomy_schema() -> dict[str, Any]:
    """What the GUI needs to build its facet dropdowns and expand queries."""
    return {
        "facets": [
            {"id": f.id, "label": f.label, "hint": f.hint,
             "values": [{"id": v.id, "label": v.label} for v in f.values]}
            for f in FACETS
        ],
        "synonyms": {k: list(v) for k, v in SYNONYMS.items()},
        "phrases": dict(PHRASES),
        "stop": sorted(_STOP),
        "decades": {str(k): v for k, v in _DECADE_WORDS.items()},
        "weights": dict(FIELD_WEIGHTS),
        "synonym_factor": SYNONYM_FACTOR,
        "prefix_factor": PREFIX_FACTOR,
        "name_coverage_bonus": NAME_COVERAGE_BONUS,
    }
