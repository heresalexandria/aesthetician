"""Curated starting points: "make it look like X" mapped onto the library.

A collection is an intent a person arrives with ("a sixties kaiju film",
"security-camera footage", "something that looks like my parents' home
movies") and the handful of presets that answer it, best first. A recipe is a
ready-made stack for an intent one preset cannot cover alone - the same
eighties adventure feature, seen on a rental tape - expressed as ordered
layers the app applies bottom to top.

The GUI shows these under the Guide chip; `scripts/validate_presets.py`
refuses a collection that names a preset that does not exist, so a rename
cannot leave a dangling recommendation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Recipe:
    id: str
    title: str
    layers: tuple[str, ...]          # preset ids, bottom layer first
    note: str = ""


@dataclass(frozen=True)
class Collection:
    id: str
    title: str
    blurb: str
    presets: tuple[str, ...]         # best answer first
    recipes: tuple[Recipe, ...] = ()
    group: str = "looks"             # looks | media | eras | sound


def _c(id, title, blurb, presets, recipes=(), group="looks"):
    return Collection(id, title, blurb, tuple(presets), tuple(recipes), group)


def _r(id, title, layers, note=""):
    return Recipe(id, title, tuple(layers), note)


COLLECTIONS: tuple[Collection, ...] = (
    # ── make it look like… ─────────────────────────────────────────────
    _c("eighties-adventure-movie", "An eighties adventure movie",
       "Matinee pulp on anamorphic Kodak: backlit smoke, warm lamps, blue shadows, Dolby optical.",
       ["genre-adventure-matinee-1984", "adventure-answer-print-1985", "genre-suburban-fantasy-1985",
        "genre-family-adventure-1993", "genre-kids-fantasy-puppets-1986"],
       [_r("on-a-rental-tape", "The same movie on a rental tape",
           ["genre-adventure-matinee-1984", "vhs-rental-1992"],
           "The release print first, then the tape that was rented forty times."),
        _r("network-premiere", "Network television premiere, 1988",
           ["genre-adventure-matinee-1984", "channel-network-primetime-1988"],
           "Pan-and-scanned, telecined and squeezed through 1988 NTSC.")]),
    _c("sixties-kaiju-film", "A sixties kaiju film",
       "Tohoscope dyes, matte seams around the monster, miniature-stage haze and a brass mono track.",
       ["genre-kaiju-feature-1964", "tokyo-spectacle-1962", "auth-japanese-tokusatsu-television-1974"],
       [_r("late-show-dub", "The dubbed late-show broadcast",
           ["genre-kaiju-feature-1964", "uhf-horror-host-1971"],
           "A faded US TV print, fed through a UHF creature-feature signal."),
        _r("tape-traded-copy", "A fourth-generation tape trade",
           ["genre-kaiju-feature-1964", "tape-swap-4th-gen-1994"])]),
    _c("security-camera-footage", "Security-camera footage",
       "Drained color, held frames, timestamps and the lonely hum of an unattended monitor.",
       ["security-vcr-1994", "liminal-cctv-2002", "closed-circuit-1970", "auth-doorbell-camera-night-2018",
        "auth-body-camera-evidence-2017", "auth-dashcam-archive-2015"]),
    _c("home-movies", "Somebody's home movies",
       "Small-gauge film and consumer tape: Kodachrome reds, Super 8 heartbeat, camcorder date stamps.",
       ["kodachrome-1964", "super8-1974", "regular8-bw-home-1960", "vhs-camcorder-1989",
        "video8-holiday-1990", "digital8-family-1999"],
       [_r("living-room-wall", "Projected on the living-room wall",
           ["kodachrome-1964", "home-8mm-wall-1966"],
           "The reel, then the wobbling projector show it was screened as.")]),
    _c("silent-film", "A silent film",
       "Hand-cranked cadence, orthochromatic skin, nitrate flicker and the accompanist's record.",
       ["silent-1918", "actuality-1900", "process-tinted-toned-nitrate-1921", "two-reeler-chase-1926",
        "nickelodeon-western-1913", "intertitle-1923"]),
    _c("old-cartoon", "An old cartoon",
       "Cels on twos, rostrum dirt, print wear, and the TV set or projector they came through.",
       ["cartoon-saturday-1969", "cartoon-technicolor-1944", "cartoon-rubberhose-1932",
        "cartoon-limited-tv-1961", "cartoon-vhs-1985", "cartoon-afternoon-block-1990"]),
    _c("anime", "Anime, by era and carrier",
       "From warm seventies cels to fansub dubs and clean web simulcasts.",
       ["anime-ova-1988", "cartoon-anime-tv-1979", "cartoon-anime-fansub-1992",
        "channel-japanese-late-night-anime-1995", "cartoon-anime-digital-paint-2004", "cartoon-anime-hd-web-2013"]),
    _c("noir-and-crime", "Film noir and crime pictures",
       "Drowning blacks, wet-street halation, sodium night grain and the sickly grades of later thrillers.",
       ["noir-1947", "genre-late-noir-location-1958", "genre-gangster-picture-1931",
        "auth-new-york-street-crime-thriller", "genre-vigilante-thriller-1974", "genre-serial-killer-procedural-1995"]),
    _c("horror", "Horror, decade by decade",
       "Gothic nitrate, fog-lit scope, video-store slashers, found footage and analog dread.",
       ["slasher-answer-print-1980", "genre-video-store-slasher-1984", "genre-poe-gothic-1963",
        "auth-gothic-studio-horror-1932", "genre-found-footage-1999", "analog-horror-1996"]),
    _c("science-fiction", "Science fiction",
       "Flying-saucer B&W, motion-control mattes, blue-steel smoke, neon rain and terminal green.",
       ["genre-space-opera-1977", "genre-neon-rain-scifi-1982", "genre-space-scifi-1986",
        "genre-flying-saucer-1953", "auth-soviet-cosmic-modernism-1968", "digital-green-1999"]),
    _c("westerns", "Westerns",
       "Technicolor sagebrush, golden scope vistas, Techniscope dust and a filmed TV series.",
       ["sunset-scope-1956", "spaghetti-scope-1966", "technicolor-sagebrush-1939",
        "matinee-b-western-1947", "revisionist-autumn-1973", "tv-western-series-1957"]),
    _c("music-video", "A music video",
       "Studio tube trails, pushed 16 mm, glossy promo masters and the channel that played them.",
       ["music-countdown-master-1987", "auth-new-wave-studio-music-video", "music-16mm-1991",
        "auth-eurodance-music-video", "neon-anamorphic-music-video-2019", "channel-music-video-launch-1983"]),
    _c("news-footage", "News footage",
       "Newsreel silver, mustard 16 mm, satellite sparklies and the cable desk.",
       ["news-film-1975", "cable-news-1991", "tv-network-news-1986", "newsreel-1942",
        "auth-live-truck-local-news-2004", "channel-cable-news-launch-1982"]),
    _c("commercials", "A commercial",
       "Shouted car-lot chroma, cereal-mascot cels, chrome appliances, and the infomercial hour.",
       ["car-dealer-ad-1986", "cartoon-cereal-mascot-1962", "auth-googie-appliance-commercial-1958",
        "local-cable-infomercial-1997", "tv-network-promo-1994", "home-shopping-cable-1987"]),
    _c("internet-video", "Internet video, by year",
       "Postage-stamp streams, 240p Flash, 360p uploads, a frozen video call and a vertical short.",
       ["webvideo-2006", "realplayer-1999", "social-youtube-360p-2010", "social-video-call-2020",
        "social-short-video-2021", "myspace-2006"]),
    _c("worn-and-damaged", "Worn, damaged, decaying",
       "Grindhouse ribbons, tracking storms, honey-fogged nitrate, vinegar warp and sticky-shed bands.",
       ["grindhouse-1973", "vhs-rental-1992", "nitrate-vault-1937", "vinegar-ektachrome-1974",
        "sticky-shed-umatic-1981", "burned-reel-1968"]),
    _c("internet-aesthetics", "Internet aesthetics",
       "Vaporwave, synthwave, liminal, dreamcore and the meme that has been re-uploaded five times.",
       ["vaporwave-vhs-1986", "synthwave-outrun-2015", "liminal-cctv-2002", "dreamcore-2021",
        "webcore-2007", "deep-fried-meme-2018"]),
    # ── a particular medium ────────────────────────────────────────────
    _c("vhs-tapes", "VHS tapes",
       "Standard play to six-hour EP, rentals, dubs, and taping off the air.",
       ["vhs-1985-sp", "vhs-ep-longplay", "vhs-rental-1992", "vhs-dub-generation",
        "vhs-taped-off-air-1987", "first-gen-vhs-1978"], group="media"),
    _c("film-stocks", "Film stocks and color processes",
       "Three-strip dye transfer, Kodachrome, the Kodak negatives of each decade, Fuji's cyan greens.",
       ["threestrip-1939", "kodachrome-1964", "process-kodak-5247-1975", "process-fuji-8510-1985",
        "process-vision-500t-1996", "process-eastmancolor-first-1955"], group="media"),
    _c("small-gauge-film", "8 mm, Super 8 and 9.5 mm",
       "Home-movie gauges: big soft grain, sprocket flashes, sound stripes that warble.",
       ["super8-1974", "kodachrome-1964", "fuji-8mm-1983", "home-95mm-1928",
        "super8-sound-mag-1979", "polavision-instant-movie-1977"], group="media"),
    _c("sixteen-millimetre", "16 mm",
       "Documentary Eastman, news film, classroom prints, Bolex diaries and Super 16 blowups.",
       ["doc-16mm-1968", "news-film-1975", "classroom-1976", "bolex-diary-1968",
        "super16-indie-1994", "film-school-16mm-bw-1995"], group="media"),
    _c("camcorders", "Camcorders",
       "Shoulder VHS to Video8, Hi8, MiniDV, Digital8 and the flip-screen vlog camera.",
       ["vhs-camcorder-1989", "video8-holiday-1990", "skate-hi8-1996", "minidv-2000",
        "digital8-family-1999", "social-vlog-camera-2017"], group="media"),
    _c("discs", "LaserDisc, DVD, VCD",
       "Crawling dots, gentle macroblocks, MPEG-1 blooming and the mall bootleg.",
       ["laserdisc-1985", "dvd-2001", "vcd-1997", "ced-videodisc-1983", "bootleg-vcd-mall-1998",
        "cdrom-mjpeg-1995"], group="media"),
    _c("print-and-paper", "Print and paper",
       "Newspaper screens, Sunday comics, zine photocopies, riso inks, instant prints and a fax.",
       ["front-page-1946", "sunday-comics-1972", "zine-photocopy-1981", "riso-flyer-1985",
        "instant-print-sx70-1975", "thermal-fax-1989"], group="media"),
    _c("displays", "The screen it was watched on",
       "A bright Trinitron, a curved console, the rec-room big screen, a Game Boy and an early LCD.",
       ["trinitron-living-room-1990", "console-tv-curved-1972", "rptv-superbowl-1993", "mall-tv-wall-1989",
        "gameboy-screen-1989", "early-lcd-tv-2005"], group="media"),
    _c("projection", "Projected in a room",
       "Changeover cue dots, the drive-in windshield, a bedsheet in the yard, a DLP's rainbow.",
       ["booth-changeover-1957", "drive-in-dusk-1961", "home-8mm-wall-1966", "bedsheet-backyard-1972",
        "matinee-scope-1955", "dlp-projector-rainbow-2003"], group="media"),
    # ── an era of television ───────────────────────────────────────────
    _c("tv-1950s", "Television in the 1950s",
       "Kinescopes, two-inch quad, image-orthicon bloom and a filmed western series.",
       ["kinescope-1953", "quadruplex-variety-1958", "network-bw-1959", "tv-western-series-1957",
        "auth-live-television-anthology-1954"], group="eras"),
    _c("tv-1960s", "Television in the 1960s",
       "Color arrives: rainbow edges, drifting flesh tones, spy gloss and fight-night orthicons.",
       ["early-color-1967", "color-premiere-1966", "tv-spy-series-1967", "channel-canadian-public-1968",
        "portable-bw-1963", "tv-boxing-broadcast-1962"], group="eras"),
    _c("tv-1970s", "Television in the 1970s",
       "Plumbicon warmth, quad tape, faded cop shows, buzzing game-show sets and the sign-off.",
       ["channel-public-tv-1971", "channel-late-night-network-1975", "tv-cop-show-1976", "game-show-1978",
        "regional-weather-1973", "sign-off-1979"], group="eras"),
    _c("tv-1980s", "Television in the 1980s",
       "Waxy talk-show skin, the music-video channel, pastel cop shows and kids cable.",
       ["talk-show-1984", "channel-music-video-launch-1983", "tv-pastel-cop-show-1985",
        "channel-kids-cable-early-1985", "tv-network-news-1986", "channel-premium-movie-1983"], group="eras"),
    _c("tv-1990s", "Television in the 1990s",
       "Multi-cam bloom, cable news, slime-green kids TV, big-money game shows and arena pyro.",
       ["sitcom-1993", "cable-news-1991", "channel-kids-cable-golden-1994", "tv-game-show-1992",
        "channel-music-video-alternative-1992", "tv-monday-night-wrestling-1998"], group="eras"),
    _c("tv-2000s", "Television in the 2000s",
       "Early 1080i edges, flag-wave cable news, desaturated procedurals and reality night-cams.",
       ["hd-1080i-2008", "channel-cable-news-flag-2003", "tv-procedural-hd-2005", "tv-reality-house-2001",
        "channel-late-night-animation-block-2003", "auth-cable-food-studio-2005"], group="eras"),
    _c("british-television", "British television",
       "405-line silver, PAL studio video with 16 mm exteriors, teatime adverts and teletext.",
       ["channel-british-public-1962", "channel-british-public-1978", "tv-british-studio-sitcom-1975",
        "channel-british-commercial-1985", "channel-british-arts-1991", "teletext-1979"], group="eras"),
    # ── a particular sound ─────────────────────────────────────────────
    _c("old-radio", "Old radio",
       "AM pumping, shortwave fades, a radio drama off the air, late-night FM and a pocket transistor.",
       ["audio-am-1948", "audio-shortwave-1962", "audio-radio-drama-aircheck-1938", "audio-fm-1978",
        "audio-transistor-pocket-radio-1965", "audio-wartime-shortwave-1942"], group="sound"),
    _c("records", "Records",
       "Warm LPs, worn 45s, boxed-in shellac, a horn gramophone, a diner jukebox and brown wax.",
       ["audio-vinyl-lp-1965", "audio-45-worn", "audio-shellac-1935", "audio-gramophone-1915",
        "audio-jukebox-diner-1958", "audio-wax-cylinder-1905"], group="sound"),
    _c("tapes", "Tapes",
       "Cassette head bump, chrome Walkman brightness, 8-track wow, boombox dubs and microcassette memos.",
       ["audio-cassette-1984", "audio-walkman-chrome-1983", "audio-8track-1974", "audio-boombox-dub-1983",
        "audio-microcassette-1986", "audio-prerecorded-cassette-1980"], group="sound"),
    _c("phones-and-radios", "Phones and two-way radios",
       "Carbon handsets, answering machines, voicemail robots, VoIP holes, CB bark and a walkie-talkie.",
       ["audio-telephone-1955", "audio-answering-machine-1988", "audio-cellphone-voicemail-2004",
        "audio-voip-call-2006", "audio-cb-1977", "audio-walkie-talkie-1990"], group="sound"),
    _c("pa-and-rooms", "PA systems and rooms",
       "Bullhorns, stadium slap, the school intercom, a gymnasium, a cathedral and the next-door stereo.",
       ["audio-pa-1970", "audio-stadium-pa-1975", "audio-school-intercom-1962", "audio-gymnasium-1975",
        "audio-cathedral-1962", "audio-through-the-wall-1995"], group="sound"),
    _c("film-sound", "Film sound",
       "Academy optical, 35 mm mag, Dolby Stereo width, 16 mm stripes, the movie palace and the drive-in pot.",
       ["audio-optical-1942", "audio-magnetic-film-1957", "audio-dolby-stereo-optical-1977",
        "audio-16mm-mag-stripe-1969", "audio-movie-palace-1935", "audio-drive-in-speaker-1958"], group="sound"),
)


def all_collections() -> tuple[Collection, ...]:
    return COLLECTIONS


def collections_schema() -> list[dict[str, Any]]:
    return [
        {
            "id": c.id,
            "title": c.title,
            "blurb": c.blurb,
            "group": c.group,
            "presets": list(c.presets),
            "recipes": [
                {"id": r.id, "title": r.title, "layers": list(r.layers), "note": r.note}
                for r in c.recipes
            ],
        }
        for c in COLLECTIONS
    ]
