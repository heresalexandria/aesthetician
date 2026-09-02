"""Search keywords for presets authored before the keywords field existed.

New presets declare `keywords=(...)` inline. The library's first 426 were
written when the only vocabulary was `tags`, and their names deliberately
describe the physical artifact rather than the thing a person is looking for
("Tokyo Spectacle Print" is the sixties kaiju feature). This sidecar gives
each of them the words people actually type, without rewriting 31 modules.

Applied once by `aesthetician.presets` after every module has registered;
`scripts/validate_presets.py` refuses an id that no longer exists and warns
about a preset with no keywords at all.

Conventions: lower-case; plain words or hyphenated phrases; genre and mood
words first, then format aliases, then a few canonical touchstones. Never
duplicate a word already in the name, tags or tagline - that costs nothing
but adds nothing either.
"""

from __future__ import annotations

KEYWORDS: dict[str, tuple[str, ...]] = {
    "auth-observational-handheld-dv-2005": (
        "verite", "documentary", "handheld", "mumblecore", "observational", "fly-on-the-wall",
        "camcorder", "home-video", "autofocus", "fluorescent", "indie", "dv-doc",
    ),
    "auth-stunt-reality-minidv-2001": (
        "stunt", "prank", "reality", "skate", "fisheye", "jackass", "camcorder", "home-video",
        "backyard", "skateboard", "sports", "minidv-fisheye",
    ),
    "auth-syndicated-limited-animation-1973": (
        "cartoon", "kids", "saturday-morning", "syndication", "limited-animation", "cel",
        "seventies-cartoon", "rerun", "tv-cartoon", "flat-paint", "after-school",
    ),
    "actuality-1900": (
        "early-cinema", "lumiere", "hand-crank", "nitrate", "primitive", "nonfiction", "fragile",
        "flickering"
    ),
    "adventure-answer-print-1985": (
        "eighties-adventure", "indiana", "matinee", "pulp", "treasure", "blockbuster", "amblin",
        "action-adventure"
    ),
    "analog-horror-1996": (
        "creepypasta", "found-footage", "liminal", "uncanny", "cursed", "static", "off-air",
        "local58"
    ),
    "anime-ova-1988": (
        "japan", "japanese", "direct-to-video", "laserdisc", "manga", "otaku", "japanimation"
    ),
    "anscochrome-pageant-1954": (
        "community", "small-town", "local", "amateur", "civic", "hometown", "americana",
        "homemade"
    ),
    "audio-16mm-mag-stripe-1969": (
        "educational", "classroom", "documentary", "narration", "institutional", "archival",
        "screening"
    ),
    "audio-45-worn": (
        "music", "jukebox", "single", "seven-inch", "diner", "teenage", "scratchy", "well-loved"
    ),
    "audio-8track-1974": (
        "music", "road-trip", "dashboard", "cruising", "classic-rock", "stereo", "muscle-car",
        "album"
    ),
    "audio-acetate-home-1947": (
        "voice-letter", "greeting", "family-voice", "living-room", "crystal-mic", "lacquer-disc",
        "keepsake", "personal-recording"
    ),
    "audio-aluminum-disc-1934": (
        "voice-letter", "parlor", "carbon-mic", "diy-recording", "home-cut", "keepsake",
        "family-voice", "stylus-noise"
    ),
    "audio-am-1948": (
        "radio-drama", "broadcast", "tube-radio", "living-room", "evening", "nightcap",
        "distant-station", "programming"
    ),
    "audio-answering-machine-1988": (
        "voicemail", "missed-call", "microcassette", "beep", "message", "landline",
        "kitchen-counter", "outgoing-message"
    ),
    "audio-atc-1969": (
        "pilot", "cockpit", "control-tower", "airport", "headset", "clearance", "flight",
        "airband"
    ),
    "audio-betamax-hifi-1985": (
        "videotape-audio", "stereo-soundtrack", "movie-night", "living-room", "movie-rental",
        "rental-tape", "home-theater", "consumer-video"
    ),
    "audio-betamax-linear-1981": (
        "videotape-audio", "mono-track", "consumer-tape", "living-room", "vcr-deck", "dialogue",
        "rental", "worn-tape"
    ),
    "audio-boombox-dub-1983": (
        "mixtape", "hip-hop", "block-party", "street", "generation-loss", "dubbed-copy",
        "cassette-culture", "trading-tapes"
    ),
    "audio-broadcast-cart-1976": (
        "jingle", "station-id", "commercial", "radio-station", "control-room", "dj-booth",
        "top-forty", "on-air"
    ),
    "audio-broadcast-reel-1961": (
        "interview", "program-audio", "syndicated-program", "radio-station", "archive-copy",
        "station-library", "generation-loss", "vault"
    ),
    "audio-camcorder-onboard-1994": (
        "home-video", "family-event", "birthday", "backyard", "handheld", "wedding",
        "vacation-tape", "candid"
    ),
    "audio-carbon-newsreel-1941": (
        "reportage", "war-correspondent", "narration", "movie-theater", "cinema-newsreel",
        "field-recording", "announcer", "wartime"
    ),
    "audio-cassette-1984": (
        "mixtape", "walkman", "bedroom", "love-song", "personal-mix", "type-one", "dubbed",
        "handwritten-label"
    ),
    "audio-cassette-field-1979": (
        "interview", "oral-history", "wired-mic", "reportage", "documentary-sound", "portable",
        "fieldwork", "vox-pop"
    ),
    "audio-cassette-fourtrack-1987": (
        "home-recording", "demo-tape", "songwriting", "bedroom-studio", "garage-band",
        "lo-fi-production", "indie-rock", "self-recorded"
    ),
    "audio-cb-1977": (
        "trucker", "highway", "convoy", "smokey-and-the-bandit", "truck-cab", "citizens-band",
        "ten-four", "roadside"
    ),
    "audio-cd-skip-1999": (
        "commute", "bus-ride", "portable-cd", "skipping", "glitchy", "subway", "walkman-era",
        "anti-shock"
    ),
    "audio-church-pa-1972": (
        "sermon", "cathedral", "congregation", "hymn", "stone-hall", "amplified-voice",
        "sunday-service", "echo-chamber"
    ),
    "audio-dat-1994": (
        "studio-master", "demo-recording", "helical-scan", "dropout-glitch", "archival-master",
        "session-tape", "engineer", "freeze-frame-audio"
    ),
    "audio-dictation-belt-1964": (
        "office-memo", "transcription", "secretary", "dictaphone", "typing-pool",
        "business-letter", "workplace", "steno"
    ),
    "audio-dolby-mistrack-1979": (
        "mixtape", "dubbed-copy", "cassette-deck", "mismatched-deck", "borrowed-tape",
        "noise-reduction-error", "breathing-hiss", "home-dub"
    ),
    "audio-drive-thru-1988": (
        "fast-food", "order-window", "squawk-box", "parking-lot", "menu-board",
        "late-night-snack", "clipped-audio", "car-window"
    ),
    "audio-fm-1978": (
        "album-rock", "dj-voice", "fm-tuner", "night-drive", "stereo-broadcast", "classic-rock",
        "mellow", "insomnia"
    ),
    "audio-full-track-master-1953": (
        "studio-recording", "session-master", "ribbon-mic", "recording-studio", "session-copy",
        "high-fidelity", "vault-copy", "engineer"
    ),
    "audio-gramophone-1915": (
        "parlor-music", "dance-hall", "victrola", "hand-crank", "acoustic-recording", "ragtime",
        "antique"
    ),
    "audio-hi8-stereo-1996": (
        "home-video", "family-footage", "vacation-tape", "hi-band", "prosumer", "handheld",
        "video8", "keepsake"
    ),
    "audio-hold-music-1993": (
        "customer-service", "waiting", "call-center", "repetitive", "elevator-music", "muzak",
        "queue", "help-desk"
    ),
    "audio-karaoke-1989": (
        "singalong", "party", "bar", "living-room", "spring-reverb", "amateur-singer",
        "backing-track", "microphone"
    ),
    "audio-magnetic-film-1957": (
        "post-production", "dubbing-stage", "sound-mixing", "editing-room", "sound-stage",
        "sync-sound", "studio-dub", "picture-sync"
    ),
    "audio-microcassette-1986": (
        "voice-memo", "note-to-self", "pocket-recorder", "reporter-notes", "personal-log",
        "interview-backup", "handheld", "journalist"
    ),
    "audio-mp3-2002": (
        "file-sharing", "downloaded-song", "dorm-room", "limewire", "dial-up", "peer-to-peer",
        "burned-cd", "computer-speakers"
    ),
    "audio-nagra-location-1970": (
        "documentary-sound", "film-set", "boom-mic", "field-mixer", "production-sound",
        "sync-sound", "location-recording", "verite"
    ),
    "audio-optical-1942": (
        "newsreel-voice", "narration", "movie-theater", "academy-mono", "cinema-sound",
        "projection-room", "announcer", "vintage-broadcast"
    ),
    "audio-pa-1970": (
        "shopping", "department-store", "supermarket", "mall", "horn-speaker",
        "blue-light-special", "checkout", "public-announcement"
    ),
    "audio-portable-reel-1965": (
        "field-interview", "fieldwork", "battery-recorder", "oral-history", "reporter",
        "on-the-street", "documentary-sound", "traveling-recordist"
    ),
    "audio-ribbon-studio-1938": (
        "radio-drama", "crooner", "broadcast-studio", "tube-console", "golden-age-radio",
        "vocal-booth", "warm-vocal", "sound-stage"
    ),
    "audio-shellac-1935": (
        "music", "dance-band", "big-band", "parlor", "turntable-rumble", "record-store",
        "antique-record", "swing-era"
    ),
    "audio-shortwave-1962": (
        "numbers-station", "dx-listening", "world-band", "cold-war", "basement-radio",
        "morse-code", "distant-signal", "ionosphere"
    ),
    "audio-subway-pa-1975": (
        "commute", "transit-announcement", "subway-platform", "underground", "tiled-tunnel",
        "train-station", "muffled", "public-transit"
    ),
    "audio-telephone-1955": (
        "phone-call", "conversation", "rotary-dial", "party-line", "long-distance", "operator",
        "kitchen-wall", "bakelite"
    ),
    "audio-transcription-1938": (
        "radio-program", "syndication", "syndicated-radio", "radio-archive", "station-copy",
        "electrical-transcription", "broadcast-library", "16-inch"
    ),
    "audio-tube-console-1948": (
        "evening-listening", "music", "radiogram", "living-room", "parlor", "valve-amp",
        "warm-tone", "after-dinner"
    ),
    "audio-tv-speaker-1975": (
        "sitcom-audio", "tv-program", "living-room", "den", "console-tv", "tinny", "mono-speaker",
        "family-room"
    ),
    "audio-umatic-linear-1977": (
        "news-editing", "broadcast-audio", "edit-bay", "newsroom", "three-quarter-inch",
        "field-tape", "station-copy", "videocassette"
    ),
    "audio-vhs-hifi-1988": (
        "movie-night", "rental-tape", "vcr-deck", "living-room", "video-store", "stereo-vhs",
        "home-theater", "tape-swap"
    ),
    "audio-vhs-linear-1985": (
        "home-recording", "tv-taping", "vcr-deck", "living-room", "rental", "camcorder-audio",
        "taped-off-tv", "family-video"
    ),
    "audio-video8-afm-1991": (
        "home-video", "travel-tape", "vacation", "handheld", "8mm-tape", "family-archive",
        "eight-millimeter", "consumer-video"
    ),
    "audio-vinyl-lp-1965": (
        "album", "music-listening", "turntable", "living-room", "record-collection",
        "record-sleeve", "warm-analog", "surface-noise"
    ),
    "audio-wax-cylinder-1905": (
        "music-hall", "recitation", "edison", "parlor", "antique", "phonograph", "spoken-word",
        "fragile-recording"
    ),
    "audio-wax-dictation-1922": (
        "office-memo", "business-letter", "dictaphone", "secretary", "typing-pool", "steno",
        "workplace", "executive-desk"
    ),
    "audio-wire-1945": (
        "field-recording", "wartime-memo", "spool-recorder", "battlefield", "voice-letter",
        "military-surplus", "underwater-tone", "signal-corps"
    ),
    "auth-16mm-skate-film-1978": (
        "skateboarding", "sidewalk-surfing", "backyard-pool", "empty-pool", "verite",
        "youth-culture", "handheld", "gritty"
    ),
    "auth-analog-science-education-television-1974": (
        "classroom", "science-class", "instructional", "filmstrip-era", "lecture",
        "public-television", "studio-set", "chalkboard"
    ),
    "auth-anime-web-fansub-encode-2006": (
        "fansub-culture", "subbing-group", "internet-anime", "otaku", "download", "irc-channel",
        "torrent", "release-group"
    ),
    "auth-art-deco-luxury-commercial-1937": (
        "luxury-goods", "department-store", "elegant", "high-society", "jazz-age", "advertising",
        "glamour", "moderne"
    ),
    "auth-asmr-close-mic-2018": (
        "whisper", "tingles", "relaxation", "intimate-audio", "youtube", "binaural",
        "soft-spoken", "sleep-aid"
    ),
    "auth-atomic-age-industrial-futurism-1957": (
        "corporate-film", "space-age", "silver-future", "midcentury", "sponsored-film",
        "world-of-tomorrow", "atomic-optimism", "push-button"
    ),
    "auth-australian-ozploitation-1978": (
        "outback", "action", "car-chase", "road-movie", "mad-max", "drive-in", "sunburnt",
        "exploitation"
    ),
    "auth-baroque-euro-horror-1964": (
        "castle", "giallo-adjacent", "mario-bava", "gothic-romance", "european-horror",
        "atmospheric", "ominous", "cobwebs"
    ),
    "auth-big-band-soundie-1944": (
        "jukebox-film", "swing-music", "bandleader", "nightclub", "musical-short", "panoram",
        "jitterbug", "wartime-swing"
    ),
    "auth-biker-exploitation-1967": (
        "outlaw-gang", "motorcycle-club", "rebel", "roger-corman", "grindhouse", "leather-jacket",
        "open-road", "counterculture"
    ),
    "auth-body-camera-evidence-2017": (
        "bodycam", "police", "law-enforcement", "traffic-stop", "arrest", "chest-mounted",
        "docket", "courtroom"
    ),
    "auth-british-folk-horror-1972": (
        "pagan", "countryside", "witchcraft", "wicker-man", "rural-england", "occult-ritual",
        "ancient-rite", "eerie-village"
    ),
    "auth-british-postwar-studio-comedy-1949": (
        "ealing-comedy", "music-hall", "class-satire", "stiff-upper-lip", "postwar-britain",
        "farce", "wit", "repertory"
    ),
    "auth-british-quota-quickie-1936": (
        "b-picture", "programmer", "drama", "second-feature", "cheaply-made",
        "quickie-production", "shoestring-budget", "studio-system"
    ),
    "auth-cabaret-soundie-1939": (
        "nightclub", "chanteuse", "smoky-lounge", "vaudeville", "jazz-singer", "panoram",
        "torch-song", "supper-club"
    ),
    "auth-canadian-tax-shelter-horror-1978": (
        "tax-shelter-film", "slasher", "low-budget-horror", "canuxploitation", "winter-shoot",
        "cheap-thrills", "b-movie", "cult-horror"
    ),
    "auth-cinerama-travel-spectacle-1958": (
        "widescreen-spectacle", "roadshow", "three-panel", "travel-epic", "grand-tour",
        "immersive", "seven-channel-sound", "panoramic"
    ),
    "auth-civil-defense-instruction-film-1953": (
        "cold-war", "duck-and-cover", "bomb-shelter", "government-film", "classroom-film",
        "propaganda-adjacent", "solemn-narrator", "atomic-drill"
    ),
    "auth-classroom-hygiene-film-1948": (
        "health-class", "scare-film", "social-guidance", "mental-hygiene", "wash-your-hands",
        "cautionary-tale", "school-assembly", "earnest-narrator"
    ),
    "auth-claymation-music-video": (
        "stop-motion", "plasticine", "tabletop", "aardman-style", "tactile-texture", "quirky",
        "handcrafted", "frame-by-frame"
    ),
    "auth-color-fashion-commercial-1966": (
        "mod-fashion", "runway", "glossy-advertising", "editorial", "swinging", "haute-couture",
        "chic", "boutique"
    ),
    "auth-color-industrial-optimism-1948": (
        "corporate-film", "factory-tour", "postwar-optimism", "manufacturing", "sponsored-film",
        "assembly-line", "progress", "modern-living"
    ),
    "auth-color-travelogue-short-1938": (
        "technicolor-two-strip", "travel-short", "postcard", "exotic-locale",
        "early-color-process", "vacation-film", "scenic", "vintage-travel"
    ),
    "auth-country-music-television-video": (
        "nashville", "line-dancing", "honky-tonk", "cmt", "cowboy-hat", "twangy", "rural-america",
        "heartland"
    ),
    "auth-czech-new-wave-surrealism-1966": (
        "surrealist", "absurdist", "prague", "milos-forman", "dark-comedy", "satire",
        "eastern-bloc-cinema", "allegory"
    ),
    "auth-dashcam-archive-2015": (
        "road-trip", "windshield-view", "commute", "highway", "car-camera", "accident-footage",
        "daily-drive", "windshield-mount"
    ),
    "auth-department-store-holiday-reel-1949": (
        "shopping", "santa", "window-display", "retail", "christmas-shopping", "holiday-special",
        "toyland", "festive"
    ),
    "auth-depression-road-drama-1935": (
        "dust-bowl", "hobo", "migrant", "hard-times", "social-realism", "hitchhiking",
        "breadline", "grapes-of-wrath"
    ),
    "auth-doorbell-camera-night-2018": (
        "porch-pirate", "front-door", "motion-triggered", "motion-alert", "package-theft",
        "night-watch", "ring-camera", "neighborhood-watch"
    ),
    "auth-drive-in-rebel-drama-1956": (
        "teen-drama", "juvenile-delinquent", "greaser", "rebel-without-a-cause", "hot-rod",
        "leather-jacket", "generation-gap", "youth-rebellion"
    ),
    "auth-dslr-indie-naturalism-2012": (
        "mumblecore", "naturalistic", "available-light", "sundance", "handheld-intimacy",
        "low-budget-indie", "slice-of-life", "understated"
    ),
    "auth-early-cgi-demo-reel-1988": (
        "computer-graphics", "raster-art", "workstation", "vector-render", "tech-demo",
        "siggraph", "wireframe", "polygon-render"
    ),
    "auth-early-talkie-revue-1929": (
        "musical", "vaudeville", "broadway", "chorus-line", "vitaphone", "backstage",
        "song-and-dance", "pre-code"
    ),
    "auth-early-video-sharing-webcam-2006": (
        "webcore", "vlog", "internet-fame", "geocities", "bedroom-broadcast", "early-internet",
        "low-res", "confessional"
    ),
    "auth-eastern-european-stop-motion-1965": (
        "puppetry", "eastern-bloc-animation", "fairy-tale", "handcrafted", "trnka-style",
        "folkloric", "whimsical", "communist-era"
    ),
    "auth-eastmancolor-tourist-film-1957": (
        "postcard", "scenic-vista", "vacation-film", "sightseeing", "resort", "pastel-landscape",
        "leisure-travel", "grand-tour"
    ),
    "auth-educational-interstitial-animation-1975": (
        "schoolhouse-rock", "psa-animation", "rostrum-camera", "bumper", "learning-segment",
        "cel-graphics", "sesame-street-era", "mnemonic-jingle"
    ),
    "auth-embedded-war-journalism-2003": (
        "war-correspondent", "combat-footage", "frontline", "iraq-war", "handheld-urgency",
        "field-report", "conflict-zone", "embedded-reporter"
    ),
    "auth-emo-performance-2005": (
        "emo-scene", "warped-tour", "eyeliner", "basement-show", "screamo", "myspace-era",
        "mall-goth", "angsty"
    ),
    "auth-eurodance-music-video": (
        "rave", "techno-pop", "club-mix", "vinyl-single", "dance-floor", "neon-lights",
        "continental-pop", "hi-nrg"
    ),
    "auth-expedition-archive-reel-1934": (
        "exploration", "wilderness", "field-team", "uncharted", "safari-jacket",
        "natural-history-museum", "specimen-collecting", "jungle-trek"
    ),
    "auth-eyewitness-local-news-1975": (
        "action-news", "anchor-desk", "field-reporter", "microwave-truck", "nightly-news",
        "community-news", "urgent-bulletin", "six-oclock-news"
    ),
    "auth-fashion-editorial-film-1977": (
        "haute-couture", "vogue", "runway", "glamour-shoot", "commercial", "studio-lighting",
        "high-fashion", "editorial-spread"
    ),
    "auth-cable-food-studio-2005": (
        "cooking-show", "celebrity-chef", "kitchen-set", "recipe", "studio-audience",
        "cable-cooking", "culinary", "how-to-cook"
    ),
    "auth-french-couture-newsreel-1957": (
        "paris-fashion-week", "runway-report", "haute-couture", "flashbulbs",
        "fashion-journalism", "elegant-reportage", "chic", "dior-era"
    ),
    "auth-geometric-chorus-spectacle-1934": (
        "busby-berkeley", "chorus-line", "kaleidoscope-formation", "art-deco-stage", "showgirls",
        "backstage-musical", "precision-dance", "ornate"
    ),
    "auth-german-expressionist-nightmare-1920": (
        "horror", "caligari", "nosferatu", "angular-shadows", "weimar-cinema", "silent-horror",
        "chiaroscuro", "nightmarish"
    ),
    "auth-googie-appliance-commercial-1958": (
        "midcentury-modern", "space-age-design", "kitchen-appliance", "populuxe", "atomic-ranch",
        "housewife", "boomerang-shapes", "suburban-dream"
    ),
    "auth-first-wave-action-camera-2014": (
        "extreme-sports", "pov", "helmet-cam", "adrenaline", "mountain-biking", "surfing",
        "skiing", "first-person"
    ),
    "auth-gothic-studio-horror-1932": (
        "classic-monster", "frankenstein", "dracula", "moody-atmosphere", "fog-machine",
        "gaslight-era", "candelabra", "shadowy"
    ),
    "auth-hair-metal-arena-promo": (
        "glam-rock", "spandex", "power-ballad", "big-hair", "stadium-rock", "guitar-solo",
        "mtv-era", "backcombed"
    ),
    "auth-hand-colored-trick-film-1904": (
        "melies", "magic-show", "stage-illusion", "early-special-effects", "fantastical",
        "stop-trick", "fairy-tale-cinema", "hand-painted"
    ),
    "auth-hand-tinted-fairy-photoplay-1921": (
        "fairy-tale", "storybook", "enchanted-forest", "pixie", "dreamlike", "whimsical",
        "spun-sugar", "gossamer"
    ),
    "auth-hi8-family-camcorder": (
        "home-video", "family-vacation", "birthday-party", "camcorder-diary", "backyard-bbq",
        "handheld-family", "everyday-life", "vhs-era-video"
    ),
    "auth-holiday-stop-motion-tv-special-1966": (
        "holiday-special", "christmas", "rankin-bass", "claymation-classic", "santa", "reindeer",
        "yuletide", "tv-tradition"
    ),
    "auth-hong-kong-heroic-bloodshed-thriller": (
        "bullet-ballet", "john-woo", "gunfight", "slow-motion-doves", "triad", "gangster",
        "shootout", "cantonese"
    ),
    "auth-hong-kong-urban-crime-film-1977": (
        "shaw-brothers", "kowloon", "neon-streets", "triad", "cantonese", "gritty-urban",
        "underworld", "back-alley"
    ),
    "auth-indian-studio-musical-melodrama-1955": (
        "bollywood-golden-age", "playback-singing", "studio-system", "jewel-tones",
        "song-picturization", "epic-romance", "classical-dance", "raj-kapoor-era"
    ),
    "auth-italian-mondo-documentary-1964": (
        "shockumentary", "exotic-locale", "taboo", "sensationalist", "globe-trotting",
        "voyeuristic", "provocative", "banned-footage"
    ),
    "auth-italian-peplum-spectacle-1959": (
        "sword-and-sandal", "hercules", "gladiator", "sun-baked-italy", "muscleman",
        "ancient-rome", "cinecitta", "toga"
    ),
    "auth-italian-prime-time-variety-show": (
        "rai", "showgirls", "spectacle", "game-segments", "studio-audience", "sequined",
        "sequins", "rai-uno"
    ),
    "auth-j-horror-digital-video-2002": (
        "ring", "cursed-tape", "onryo", "vengeful-ghost", "long-black-hair", "japanese-horror",
        "creepy-child", "urban-legend"
    ),
    "auth-japanese-new-wave-urbanism-1965": (
        "nagisa-oshima", "student-protest", "alienation", "urban-anomie", "handheld-verite",
        "postwar-tokyo", "restless-youth", "black-and-white-tokyo"
    ),
    "auth-japanese-occupation-era-drama-1947": (
        "ozu-style", "tatami-shot", "family-drama", "quiet-restraint", "postwar-japan",
        "domestic-life", "generational", "understated-emotion"
    ),
    "auth-japanese-samuraiscope-1958": (
        "action", "chanbara", "swordsman", "kurosawa", "feudal-japan", "sword-fight", "ronin",
        "toho-scope"
    ),
    "auth-japanese-tokusatsu-television-1974": (
        "kaiju", "ultraman", "rubber-suit", "sentai", "special-effects", "miniature-city", "toho",
        "hero-show"
    ),
    "auth-jazz-age-city-symphony-1927": (
        "metropolis", "urban-montage", "skyscrapers", "avant-garde", "jazz-era", "modernist",
        "vertov-style", "rhythmic-editing"
    ),
    "auth-jet-age-airline-commercial-1965": (
        "stewardess", "jet-set", "airport-terminal", "midcentury-travel", "pan-am",
        "glamorous-flight", "runway-glamour", "air-travel"
    ),
    "auth-kinescope-comedy-revue-1952": (
        "sketch-comedy", "variety-hour", "live-television", "milton-berle", "vaudeville-tv",
        "studio-audience", "golden-age-tv", "borscht-belt"
    ),
    "auth-kodachrome-family-vacation-1958": (
        "family-road-trip", "national-park", "summer-holiday", "station-wagon",
        "postcard-perfect", "home-movie", "sunny-memories", "kodak-moment"
    ),
    "auth-kodachrome-home-front-reel-1944": (
        "wartime-family", "victory-garden", "rationing", "wwii-era", "family-reunion", "backyard",
        "domestic-life", "keepsake-reel"
    ),
    "auth-live-television-anthology-1954": (
        "teleplay", "playhouse-90", "live-drama", "single-camera-drama", "golden-age-television",
        "studio-drama", "philco-playhouse", "broadway-actors"
    ),
    "auth-live-truck-local-news-2004": (
        "breaking-news", "satellite-truck", "field-reporter", "live-shot", "on-scene",
        "action-news-team", "traffic-report", "weather-update"
    ),
    "auth-lumiere-era-actuality-1896": (
        "lumiere-brothers", "cinematographe", "first-films", "birth-of-cinema", "pioneering",
        "single-shot", "static-camera", "unedited"
    ),
    "auth-machinima-web-series-2005": (
        "comedy", "webcore", "red-vs-blue", "halo-era", "game-engine", "voice-acting",
        "fan-production", "screen-capture"
    ),
    "auth-magical-girl-cel-broadcast": (
        "sailor-moon", "transformation-sequence", "sparkle-effects", "shojo",
        "saturday-morning-anime", "toonami", "pastel-magic", "heroine"
    ),
    "auth-mall-portrait-studio-commercial": (
        "olan-mills", "glamour-shots", "family-photo", "backdrop", "mall-culture",
        "soft-focus-portrait", "studio-package", "senior-photos"
    ),
    "auth-mexican-lucha-cinema-1973": (
        "luchador", "masked-wrestler", "santo", "wrestling-movie", "monster-mashup",
        "arena-crowd", "campy", "mexploitation"
    ),
    "auth-mission-control-television-feed-1969": (
        "nasa", "apollo-program", "houston", "space-race", "astronauts", "splashdown",
        "telemetry", "orthicon-bloom"
    ),
    "auth-movie-of-the-week-melodrama-1975": (
        "tv-movie", "network-premiere", "disease-of-the-week", "issue-drama", "weepie",
        "star-studded", "sunday-night", "tearjerker"
    ),
    "auth-space-agency-mission-tape-1972": (
        "apollo-era", "space-program", "flight-controllers", "telemetry-feed",
        "astronaut-footage", "houston", "orbital", "splashdown"
    ),
    "auth-new-wave-studio-music-video": (
        "synth-pop", "mtv-generation", "neon-studio", "keytar", "post-punk", "cobalt-lighting",
        "music-television", "new-romantic"
    ),
    "auth-new-york-street-crime-thriller": (
        "gritty-nyc", "times-square", "vigilante", "urban-decay", "sodium-streetlight",
        "subway-crime", "scorsese-era", "42nd-street"
    ),
    "auth-nickelodeon-melodrama-1912": (
        "nickelodeon-theater", "penny-arcade", "working-class-audience", "damsel-in-distress",
        "early-narrative-film", "griffith-era", "storefront-cinema", "one-reeler"
    ),
    "auth-nu-metal-performance-2001": (
        "angst", "mosh-pit", "rap-rock", "korn-era", "aggressive", "baggy-jeans", "turntablist",
        "downtuned"
    ),
    "auth-ocean-liner-newsreel-1938": (
        "transatlantic-crossing", "queen-mary", "maiden-voyage", "high-society", "steamship",
        "dockside", "luxury-travel", "port-of-call"
    ),
    "auth-paranormal-investigation-dv-2004": (
        "ghost-hunting", "haunted-house", "evp", "found-footage-horror", "creepy-basement", "orb",
        "supernatural", "ghost-hunters"
    ),
    "auth-pastel-single-camera-sitcom-1959": (
        "domestic-comedy", "suburban-family", "picket-fence", "wholesome", "laugh-track",
        "family-values", "father-knows-best", "pastel-kitchen"
    ),
    "auth-polish-school-monochrome-1962": (
        "drama", "arthouse", "wajda-era", "war-trauma", "existential", "black-and-white-poland",
        "art-cinema", "somber"
    ),
    "auth-political-campaign-spot-2008": (
        "election", "attack-ad", "stump-speech", "swing-state", "flag-waving", "voter",
        "political-advertising", "debate-season"
    ),
    "auth-poliziotteschi-crime-thriller-1975": (
        "eurocrime", "vigilante-cop", "car-chase", "rome-streets", "hardboiled",
        "dubbed-dialogue", "maverick-cop", "loose-cannon"
    ),
    "auth-pop-art-limited-animation-1967": (
        "experimental", "warhol-adjacent", "graphic-design", "bold-primaries", "op-art",
        "psychedelic", "advertising-aesthetic", "mod-graphics"
    ),
    "auth-prestige-historical-miniseries": (
        "period-piece", "costume-drama", "sweeping-saga", "masterpiece-theatre",
        "historical-epic", "multi-part", "literary-adaptation", "sunday-night-tv"
    ),
    "auth-prog-rock-concert-film-1974": (
        "progressive-rock", "concept-album", "light-show", "arena-rock", "synthesizer",
        "epic-solo", "pink-floyd-era", "laser-light"
    ),
    "auth-public-access-goth-program": (
        "goth-subculture", "local-cable", "batcave-scene", "candlelit-set", "diy-television",
        "underground-scene", "community-tv", "cult-following"
    ),
    "auth-public-information-nightmare-1975": (
        "psa", "scare-tactics", "safety-film", "cautionary", "government-warning",
        "classroom-terror", "stark-warning", "hazard"
    ),
    "auth-public-television-science-lecture-1968": (
        "pbs", "professor", "chalkboard-diagram", "physics", "nova-era", "educational-tv",
        "academic", "lecture-hall"
    ),
    "auth-public-television-science-magazine": (
        "pbs", "nova", "science-magazine-show", "documentary-segment", "expert-interview",
        "field-report", "educational-broadcast", "nature-segment"
    ),
    "auth-punk-club-super-8-1978": (
        "cbgb", "mosh-pit", "diy-show", "basement-show", "safety-pins", "anarchist",
        "loud-and-fast", "underground-venue"
    ),
    "auth-puppet-advertising-short-1947": (
        "marionette", "tabletop-commercial", "product-mascot", "stop-motion-ad",
        "vintage-advertising", "sales-pitch", "jingle", "toy-commercial"
    ),
    "auth-r-b-slow-jam-video": (
        "late-night-radio", "quiet-storm", "candlelit-romance", "silky-vocals", "love-ballad",
        "soul-music", "boudoir-lighting", "smooth-groove"
    ),
    "auth-radio-mystery-adaptation-1937": (
        "whodunit", "detective-story", "suspenseful", "shadowy-study", "noir-precursor",
        "radio-drama-adaptation", "old-time-radio", "gaslight-mystery"
    ),
    "auth-rock-and-roll-jukebox-picture-1956": (
        "elvis-era", "teen-idol", "sock-hop", "juke-joint", "rockabilly", "record-hop",
        "greaser-culture", "hand-jive"
    ),
    "auth-roller-disco-promotional-reel-1979": (
        "roller-rink", "disco-ball", "skate-party", "platform-shoes", "studio-54", "funk",
        "boogie", "nightlife"
    ),
    "auth-romcom-digital-intermediate-2006": (
        "meet-cute", "chick-flick", "wedding-scene", "happy-ending", "banter", "love-story",
        "sundrenched", "girls-night"
    ),
    "auth-rooftop-hip-hop-promo": (
        "rap-video", "boom-bap", "golden-era-hiphop", "urban-rooftop", "graffiti", "b-boy", "mc",
        "block-party"
    ),
    "auth-rubber-hose-rural-cartoon-1932": (
        "fleischer-style", "silly-symphony", "vaudeville-humor", "bouncy-animation",
        "early-animation", "barnyard", "black-and-white-cartoon", "inkwell-studio"
    ),
    "auth-saturday-morning-live-action-serial-1976": (
        "krofft-era", "kids-adventure", "cliffhanger", "costumed-hero", "live-action-kids",
        "matinee-serial", "cereal-commercial", "campy-heroics"
    ),
    "auth-sepia-family-home-movie-1938": (
        "family-archive", "attic-reel", "grandparents", "keepsake", "prewar-family", "heirloom",
        "generational-memory", "faded-memory"
    ),
    "auth-skateboard-vhs": (
        "skate-video", "vert-ramp", "grip-tape", "half-pipe", "thrasher-mag", "fisheye-lens",
        "gnarly", "backyard-ramp"
    ),
    "auth-slapstick-two-reeler-1924": (
        "keaton-style", "chaplin-era", "pratfall", "sight-gag", "custard-pie", "guffaw",
        "physical-comedy", "one-reeler"
    ),
    "auth-soft-rock-variety-special-1976": (
        "yacht-rock", "soft-focus", "guest-stars", "orchestra-backing", "sequined-gowns",
        "sunset-strip", "mellow-gold", "network-special"
    ),
    "auth-soul-dance-broadcast-1973": (
        "soul-train", "funk", "afro", "dance-floor", "live-band", "studio-audience-dancing",
        "motown-adjacent", "groove"
    ),
    "auth-southern-gothic-tv-movie-1976": (
        "deep-south", "spanish-moss", "plantation", "swamp", "faulkner-esque", "humidity",
        "family-secrets", "front-porch"
    ),
    "auth-soviet-color-ballet-film-1957": (
        "bolshoi", "kirov", "prima-ballerina", "cold-war-culture", "state-arts",
        "classical-dance", "cultural-diplomacy", "grand-theater"
    ),
    "auth-soviet-cosmic-modernism-1968": (
        "cosmonaut", "space-race", "brutalist", "solaris-era", "eastern-bloc-scifi", "cosmism",
        "space-age", "concrete-utopia"
    ),
    "auth-soviet-montage-agitfilm-1925": (
        "mass-choreography", "propaganda", "eisenstein-style", "revolutionary-cinema",
        "dialectical-editing", "constructivist", "kino-eye", "vertov"
    ),
    "auth-square-social-filter-2013": (
        "hipstamatic", "vsco", "square-crop", "faded-polaroid-look", "brunch-photo", "iphone-app",
        "early-instagram", "square-photo"
    ),
    "auth-stop-motion-product-commercial": (
        "claymation-ad", "miniature-set", "tabletop-product-shot", "toy-commercial",
        "california-raisins-era", "lacquered-toys", "practical-effects", "sunday-morning-ads"
    ),
    "auth-streaming-true-crime-2017": (
        "netflix-doc", "cold-case", "interview-subject", "reenactment", "binge-watch",
        "unsolved-mystery", "investigative", "talking-head"
    ),
    "auth-streamline-moderne-industrial-film-1937": (
        "art-deco-factory", "machine-age", "modernist-design", "corporate-film", "sponsored-film",
        "aerodynamic-design", "industrial-progress", "assembly-line"
    ),
    "auth-super-8-family-vacation-1974": (
        "road-trip", "national-park", "campground", "station-wagon", "camping-trip",
        "amusement-park", "sunny-memories", "grandmas-house"
    ),
    "auth-supernatural-romantic-melodrama-1947": (
        "ghost-romance", "afterlife-love-story", "weepie", "star-crossed", "ethereal",
        "misty-dreamscape", "haunting-romance", "golden-age-hollywood"
    ),
    "auth-surf-video-magazine": (
        "surf-culture", "beach-break", "longboard", "wipeout", "endless-summer", "wetsuit",
        "point-break", "swell"
    ),
    "auth-technology-launch-keynote": (
        "product-launch", "tech-demo", "auditorium-stage", "corporate-event", "big-reveal",
        "silicon-valley", "press-conference", "unveiling"
    ),
    "auth-televangelist-broadcast": (
        "televangelism", "prosperity-gospel", "faith-healing", "pledge-drive", "choir", "sermon",
        "800-number", "tent-revival"
    ),
    "auth-theatrical-cel-anime-fantasy": (
        "studio-ghibli-adjacent", "feature-anime", "theatrical-release", "epic-score",
        "hand-painted-cels", "mythic-quest", "japanese-animation", "matte-painting"
    ),
    "auth-tinted-adventure-serial-1914": (
        "cliffhanger", "damsel-in-distress", "perils-of-pauline", "melodrama-serial",
        "amber-tint", "movie-palace", "weekly-chapter", "villain"
    ),
    "auth-trip-hop-noir-promo": (
        "massive-attack-era", "downtempo", "moody-electronica", "blue-hour",
        "rain-slicked-streets", "smoky-atmosphere", "bristol-sound", "cinematic-triphop"
    ),
    "auth-turkish-exploitation-dub-1976": (
        "action", "yesilcam", "turkish-star-wars", "cheap-remake", "unlicensed-dub",
        "practical-chaos", "bootleg-spectacle", "so-bad-its-good"
    ),
    "auth-underground-16mm-happening-1967": (
        "warhol-factory", "avant-garde", "psychedelic", "beat-scene", "no-budget",
        "experimental-film", "counterculture-cinema", "loft-party"
    ),
    "auth-video-dating-profile-tape": (
        "dating", "singles-tape", "personal-ad", "matchmaking", "awkward-intro", "blind-date",
        "nervous-smile", "lonely-hearts"
    ),
    "auth-warehouse-rave-vhs": (
        "acid-house", "glow-sticks", "techno", "laser-lights", "strobe-lights", "illegal-party",
        "all-night", "flyer-culture"
    ),
    "auth-wartime-signal-corps-film-1943": (
        "combat-training", "military-film", "propaganda", "boot-camp", "army-training",
        "ww2-footage", "field-manual", "drill-instructor"
    ),
    "auth-watergate-political-paranoia-1974": (
        "conspiracy", "surveillance-state", "whistleblower", "cold-war-paranoia", "wiretap",
        "investigative-journalism", "deep-throat", "fluorescent-office"
    ),
    "auth-womens-picture-gloss-1942": (
        "joan-crawford-era", "melodrama", "close-up-lighting", "tearjerker", "self-sacrifice",
        "silver-screen-siren", "satin-gowns", "hollywood-golden-age"
    ),
    "auth-wpa-social-documentary-1936": (
        "new-deal", "great-depression-relief", "social-realism", "public-works", "labor",
        "government-film", "farm-security-administration", "civic-duty"
    ),
    "auth-wrestling-broadcast-tape": (
        "wwf-era", "kayfabe", "tag-team", "squared-circle", "arena-crowd", "body-slam",
        "championship-belt", "heel-and-face"
    ),
    "basic-adjust": ("hd", "color-grading", "levels", "curves", "white-balance", "retouch", "cleanup",),
    "bedsheet-backyard-1972": (
        "home-movie", "summer-night", "childhood", "nostalgic", "amateur", "outdoor-screening",
        "family", "diy-cinema"
    ),
    "betacam-eng-1989": (
        "electronic-news-gathering", "field-camera", "reporter", "eyewitness", "local-news",
        "professional", "high-band", "component-video"
    ),
    "betamax-1978": (
        "home-video", "consumer-format", "format-war", "sony", "warm-glow", "analog-video",
        "chroma-noise", "nostalgic"
    ),
    "bleach-bypass-1998": (
        "war", "gritty", "desaturated", "high-contrast", "metallic-sheen", "crime",
        "silver-retention", "millennium"
    ),
    "bolex-diary-1968": (
        "handmade", "intimate", "poetic", "personal-cinema", "brakhage", "reversal",
        "student-film", "confessional"
    ),
    "bollywood-1969": (
        "masala", "melodrama", "romance", "dance", "playback-singing", "vibrant", "golden-age",
        "tropical"
    ),
    "booth-changeover-1957": (
        "nostalgia", "matinee", "double-feature", "revival-house", "grindhouse", "popcorn",
        "vintage", "theater-experience"
    ),
    "bootleg-vcd-mall-1998": (
        "camrip", "telesync", "action", "blockbuster", "hong-kong", "multiplex", "screener",
        "pirated"
    ),
    "border-yellow-2000": (
        "border-crossing", "desert-heat", "sun-bleached", "cartel", "crime", "traffic", "gritty",
        "monochromatic-tint"
    ),
    "brightness-contrast": (
        "hd", "levels", "curves", "highlight-rolloff", "midtones", "shadows", "tone-mapping",
        "grade"
    ),
    "burned-reel-1968": (
        "archival", "nitrate-fire", "disaster", "lost-film", "carbon-arc", "projection-booth",
        "found-in-vault"
    ),
    "bw-home-16mm-1938": (
        "family-archive", "nostalgic", "sunday-afternoon", "amateur-film", "reversal-stock",
        "attic-find", "grandparents", "keepsake"
    ),
    "cable-news-1991": (
        "breaking-news", "24-hour", "satellite-feed", "cnn", "anchor-desk", "live-truck",
        "urgent", "network"
    ),
    "camcorder-slp-1999": (
        "home-video", "camcorder-tape", "tracking-error", "worn-out", "family-tape",
        "dying-format", "handycam", "found-footage"
    ),
    "cameraphone-2007": ("concert", "music", "low-res", "mms", "razr", "pixelated", "home-video", "y2k",),
    "car-dealer-ad-1986": (
        "tape", "dealership", "hard-sell", "cheap", "bargain", "blown-out", "late-night",
        "limited-time"
    ),
    "cartoon-anime-fansub-1992": (
        "otaku", "toonami", "ova", "bootleg", "generation-loss", "tape-trading", "import",
        "dubbed"
    ),
    "cartoon-anime-tv-1979": (
        "japan", "dubbed", "nostalgic", "rerun", "import", "weeknight", "mono-broadcast",
        "syndication"
    ),
    "cartoon-cereal-mascot-1962": (
        "kids", "breakfast", "catchy-tune", "saturday-morning", "eye-popping", "cheerful",
        "sponsor", "toys"
    ),
    "cartoon-euro-short-1965": (
        "muted-stock", "cine-club", "short-film", "painterly", "gentle", "understated",
        "prize-winner", "fine-art"
    ),
    "cartoon-syndicated-1975": (
        "kids", "saturday-morning", "limited-animation", "after-school", "rerun", "cheap",
        "recycled", "budget"
    ),
    "cartoon-fleischer-1936": (
        "kids", "betty-boop", "popeye", "jazz-age", "surreal", "rubbery", "inkwell", "creepy"
    ),
    "cartoon-mtv-1994": (
        "beavis", "liquid-television", "alternative", "irreverent", "teen", "gritty",
        "worn-film-look", "late-night"
    ),
    "cartoon-nick-90s": (
        "kids", "orange-and-green", "after-school", "gross-out", "saturday-morning",
        "tape-recorded", "teen", "rerun"
    ),
    "cartoon-pencil-test-1968": (
        "kids", "16mm", "rough-draft", "unfinished", "bare-bones", "behind-the-scenes", "sketchy",
        "animators"
    ),
    "cartoon-rubberhose-1932": (
        "kids", "surreal", "bouncy", "haunted", "inkwell", "jazz-age", "early-animation", "creepy"
    ),
    "cartoon-saturday-1969": (
        "kids", "cereal", "rerun", "limited-animation", "after-school", "cartoons", "nostalgic",
        "budget-animation"
    ),
    "cartoon-sunday-comic-1972": (
        "kids", "funny-pages", "cheap-paper-stock", "cartoons", "syndicated", "weekend",
        "rosette", "offset"
    ),
    "cartoon-technicolor-1944": (
        "kids", "rich-hues", "classic-animation", "theatrical", "lush", "vibrant", "matinee",
        "short-subject"
    ),
    "cartoon-toy-ad-1985": (
        "kids", "toys", "jingle", "sponsor", "action-figures", "bright-colors", "fast-cuts",
        "upsell"
    ),
    "cartoon-upa-1957": (
        "kids", "experimental", "limited-animation", "mid-century", "flat-design", "minimalist",
        "jazz-score", "gallery-quality"
    ),
    "cartoon-vhs-1985": (
        "kids", "saturday-morning", "taped-off-air", "chroma-bleed", "rerun", "home-recorded",
        "syndication", "fuzzy"
    ),
    "cband-superstation-1982": (
        "retro", "nostalgic", "analog-relay", "ghosting", "backyard-dish", "rural", "usa",
        "big-dish"
    ),
    "cc-dtv-2004": (
        "subtitles", "accessibility", "flat-panel", "hd", "atsc", "closed-caption",
        "deaf-friendly", "over-the-air"
    ),
    "cc-line21-1982": (
        "subtitles", "accessibility", "deaf-friendly", "decoder-box", "closed-caption",
        "monospace", "set-top-box", "eia-608"
    ),
    "cc-rollup-1987": (
        "broadcast", "tv", "stenography", "steno-machine", "real-time", "deaf-friendly",
        "subtitles", "closed-caption"
    ),
    "cdrom-mjpeg-1995": (
        "beige-computer", "retro", "nostalgic", "educational", "multimedia-pc", "clip-art",
        "computer-lab", "interactive", "any-program"
    ),
    "ced-videodisc-1983": (
        "retro", "nostalgic", "groove-tracking", "grooved-disc", "home-theater", "rca",
        "movie-night", "prerecorded", "any-program"
    ),
    "chamber-face-1961": (
        "film", "bergman", "austere", "minimalist", "spare", "introspective", "psychological",
        "tense"
    ),
    "cinecolor-travel-print-1948": (
        "35mm", "travelogue", "bipack-process", "postcard", "tourist", "brick-red",
        "exotic-locale", "archival"
    ),
    "cinema-du-look-1986": (
        "stylish", "neo-noir", "parisian", "high-sheen", "music-video-gloss", "postmodern",
        "diffusion-glow", "subway"
    ),
    "cinema-subs-1968": (
        "caption-text", "art-house-print", "serif-type", "festival-print", "imported-film",
        "foreign-film", "unbacked-text", "legible"
    ),
    "classroom-1976": (
        "kids", "school", "filmstrip-day", "av-cart", "bell-and-howell", "substitute-teacher",
        "reel-to-reel-projector", "lunchroom"
    ),
    "closed-circuit-1970": (
        "surveillance", "institutional-tv", "hospital", "school-system", "building-monitor",
        "the-lobby-channel", "vidicon-gray", "raster-glow"
    ),
    "color-balance": (
        "hd", "grading", "correction-tool", "temperature", "hue-shift", "vibrance",
        "white-balance", "post-production"
    ),
    "color-premiere-1966": (
        "variety", "peacock", "showcase", "gala", "must-see", "prestige", "special-event", "vivid"
    ),
    "corporate-umatic-1988": (
        "boardroom", "training-video", "fluorescent-lighting", "taupe-tones", "dry-narration",
        "office-park", "shareholder-meeting", "overhead-projector"
    ),
    "cross-process-1996": (
        "acid-colors", "slide-film", "alt-rock", "band-promo", "saturated", "gritty-glam",
        "teen-spirit", "indie-label"
    ),
    "datamosh": (
        "web", "glitch-art", "corrupted-file", "prediction-blocks", "chaotic", "broken-codec",
        "video-art", "macroblocks"
    ),
    "digicam-mjpeg-2002": (
        "home-video", "point-and-shoot", "vacation", "candid", "tiny-sensor", "compact",
        "snapshot", "electret-mic"
    ),
    "digital-green-1999": (
        "matrix", "hacker", "code-rain", "office-drone", "dystopian-office", "cyber",
        "surveillance-state", "server-room"
    ),
    "disco-variety-master-1979": (
        "mirror-ball", "dance-floor", "glitter", "soul-train", "funk", "sequins", "live-band",
        "studio-audience"
    ),
    "doc-16mm-1968": (
        "verite", "handheld", "observational", "eastman-color", "field-crew", "unscripted",
        "real-life", "muted-tones"
    ),
    "drama-kitchen-sink-1961": (
        "angry-young-man", "working-class", "gritty-realism", "rain", "terraced-houses",
        "social-realism", "industrial-north", "new-wave"
    ),
    "drive-in-1959": (
        "creature-feature", "scifi", "atomic-age", "teen-crowd", "double-bill", "popcorn", "dusk",
        "cheap-thrills"
    ),
    "drive-in-dusk-1961": (
        "creature-feature", "scifi", "teen-crowd", "double-bill", "dashboard-speaker", "twilight",
        "popcorn", "cheap-thrills"
    ),
    "dvd-2001": (
        "retro", "nostalgic", "chapter-menu", "special-features", "rental-era", "home-theater",
        "digital-transfer", "movie-night", "any-program"
    ),
    "dvd-subs-1999": (
        "caption-overlay", "subpicture", "dvd-menu", "four-color-palette", "hard-rim",
        "action-safe", "home-theater", "rental-disc"
    ),
    "dvdr-home-transfer-2005": (
        "dad-archive", "camcorder-transfer", "clip-art-menu", "waxy-skin", "denoised",
        "vhs-to-dvd", "beach-clipart", "family-tapes"
    , "home-video", "any-program"),
    "dx-skip-1959": (
        "retro", "nostalgic", "ionosphere", "far-off-station", "fringe-reception", "ghostly",
        "late-night", "antenna-hunting", "any-program"
    ),
    "dx-tv-1963": (
        "retro", "nostalgic", "ionospheric-bounce", "logbook", "distant-station",
        "catch-of-the-night", "dx-hobby", "fringe-reception", "any-program"
    ),
    "early-color-1967": (
        "retro", "nostalgic", "color-tv-debut", "vivid", "showcase", "rainbow-fringe",
        "primetime", "novelty", "any-program"
    ),
    "eastman-faded-1979": (
        "nostalgic", "vintage", "sun-bleached", "cinema-relic", "rewatched", "attic-find",
        "projector-worn", "time-capsule"
    ),
    "ektachrome-news-1972": (
        "field-crew", "reversal-stock", "cyan-cast", "overexposed", "eyewitness",
        "local-affiliate", "assignment-desk", "on-the-scene"
    ),
    "expressionist-shadows-1922": (
        "nightmare", "caligari", "angular", "distorted-sets", "weimar", "silent-horror",
        "tinted-print", "chiaroscuro"
    ),
    "fansub-vhs-1994": (
        "subtitles", "anime", "otaku", "amiga-genlock", "tape-trading", "import",
        "hot-yellow-text", "timebase-drift"
    ),
    "fantasy-sitcom-1964": (
        "magic-trick", "suburban-magic", "laugh-track", "soundstage", "optical-effects",
        "wholesome", "primetime", "luminous-faces"
    ),
    "first-vertical-2013": (
        "home-video", "selfie-era", "shaky", "candid", "vertical-video", "pocket-camera",
        "spontaneous", "social-clip"
    ),
    "fitness-vhs-1984": (
        "aerobics", "leotard", "leg-warmers", "workout-tape", "jazzercise", "studio-audience",
        "upbeat", "sweatband"
    ),
    "front-page-1946": (
        "news", "headline", "press-photo", "breaking", "wire-photo", "tabloid", "above-the-fold",
        "ink-gain"
    ),
    "fuji-8mm-1983": (
        "summer", "algae-green", "backyard", "cartridge-film", "cooler-tones", "family-reel",
        "vacation", "birthday-party"
    ),
    "game-show-1978": (
        "game-show", "quiz", "prize-wall", "big-wheel", "showcase-lights", "contestant-podium",
        "buzzer", "applause"
    ),
    "giallo-1972": (
        "horror", "crime", "argento", "black-gloves", "razor", "psychosexual", "stylish-murder",
        "eurocult"
    ),
    "golden-reverie-1978": (
        "terrence-malick", "wheat-field", "rim-lit", "voice-over", "poetic", "sun-drenched",
        "wistful", "impressionistic"
    ),
    "golf-sunday-1977": (
        "clubhouse", "fairway", "whispered-commentary", "tee-off", "country-club", "leaderboard",
        "green-grass", "hushed-crowd"
    ),
    "grindhouse-1973": (
        "horror", "kung-fu", "exploitation-era", "42nd-street", "double-feature", "sleazy",
        "lurid", "midnight-movie"
    ),
    "hammer-eastmancolor-1960": (
        "horror", "gothic", "dracula", "gaslit", "period-horror", "candlelit", "fog",
        "velvet-cape"
    ),
    "hd-1080i-2008": (
        "retro", "nostalgic", "flatscreen-era", "showroom-demo", "crisp-debut", "widescreen",
        "appointment-viewing", "state-of-the-art", "any-program"
    ),
    "hk-action-1988": (
        "heroic-bloodshed", "john-woo", "gunplay", "doves", "slow-motion", "triads",
        "midnight-screening", "dubbed-english"
    ),
    "home-8mm-wall-1966": (
        "home-movie", "amateur", "projector-cart", "bedsheet-screen", "angled-projection",
        "bookshelf-perch", "couch-jolt", "front-room"
    ),
    "home-95mm-1928": (
        "amateur", "parlor-projector", "single-perforation", "splice-flash", "family-reel",
        "hand-cranked", "attic-reel", "nostalgic"
    ),
    "home-shopping-cable-1987": (
        "qvc", "infomercial", "operators-standing-by", "gemstone", "order-now", "toll-free",
        "glossy-products", "white-card-bloom"
    ),
    "intertitle-1923": (
        "subtitles", "title-card", "serif-lettering", "black-card", "storytelling-text",
        "vintage-typography", "exhibition-print", "ornate-border"
    ),
    "ipod-video-2005": (
        "retro", "nostalgic", "pocket-screen", "commute-viewing", "synced", "click-wheel",
        "tiny-screen", "bus-ride", "any-program"
    ),
    "jammed-broadcast-1984": (
        "conspiracy", "paranoia", "censored", "blackout", "cold-war", "forbidden-broadcast",
        "cut-off", "signal-war"
    ),
    "karaoke-1988": (
        "laserdisc", "sing-along", "text-crawl", "bouncing-ball", "bar-night", "party", "cheesy",
        "lounge"
    ),
    "kinemacolor-1912": (
        "documentary", "actuality", "newsreel", "edwardian", "early-cinema", "fairground",
        "music-hall", "exhibition-hall"
    ),
    "kinescope-1953": (
        "archival", "live-television", "preserved-broadcast", "silvery", "earliest-tv",
        "telerecording", "scanline-ghost", "monitor-filmed"
    ),
    "kodachrome-1964": (
        "red-reds", "cyan-skies", "brownie-camera", "attic-reel", "family-vacation", "summer",
        "projector-whir", "sun-faded"
    ),
    "laserdisc-1985": (
        "retro", "nostalgic", "videophile", "criterion-era", "chapter-stop", "home-theater",
        "rental-shelf", "audiophile", "any-program"
    ),
    "late-night-timer-rec-1987": (
        "retro", "nostalgic", "unattended", "overnight", "half-asleep", "missed-part",
        "timer-set", "insomnia", "any-program"
    ),
    "liminal-cctv-2002": (
        "backrooms", "empty-mall", "food-court", "3am", "dvr-footage", "fluorescent-green",
        "dreamcore", "nobody-there"
    ),
    "local-cable-infomercial-1997": (
        "late-night", "order-now", "toll-free", "fluorescent-drift", "hard-sell", "testimonial",
        "s-vhs-edit", "budget-production"
    ),
    "local-morning-1985": (
        "breakfast-tv", "weatherman", "coffee", "rise-and-shine", "community-bulletin", "folksy",
        "channel-8", "cream-diffusion"
    ),
    "lower-third-1985": (
        "chyron", "name-strap", "character-generator", "control-room", "identification-graphic",
        "condensed-type", "news-graphic", "strap-graphic"
    ),
    "magazine-gloss-1967": (
        "advertising", "fashion-spread", "coated-stock", "lacquer-shine", "full-page-ad",
        "glamour-shot", "loupe", "cocktail-ad"
    ),
    "mall-tv-wall-1989": (
        "retail-therapy", "showroom", "electronics-department", "commercial-district",
        "big-box-store", "chroma-cranked", "americana", "consumerism"
    ),
    "matinee-b-western-1947": (
        "poverty-row", "singing-cowboy", "shootout", "double-bill", "dusty-town", "cliffhanger",
        "saturday-serial", "six-shooter"
    ),
    "matinee-scope-1955": (
        "popcorn", "newsreel-intro", "cartoon-short", "double-feature", "reel-change",
        "hall-echo", "faded-dyes", "county-theater"
    ),
    "mexico-golden-1948": (
        "drama", "romance", "melodrama", "cantinflas", "charro", "mariachi", "lustrous",
        "silver-screen"
    ),
    "microfilm-morgue-1958": (
        "archive", "newspaper-morgue", "reader-glare", "roller-scratches", "reference-room",
        "research", "microfiche-reader", "reel-crank"
    ),
    "microwave-remote-1978": (
        "live-truck", "field-report", "antenna-mast", "parking-lot", "comms-relay", "signal-hop",
        "reporter-standup", "on-location"
    ),
    "minidv-2000": (
        "home-video", "family-camcorder", "millennium", "over-sharpened", "chroma-steps",
        "handheld", "wedding-video", "school-play"
    ),
    "moldy-basement-16mm-1958": (
        "home-movie", "amateur", "forgotten-reel", "attic-find", "black-mold", "musty",
        "basement-find", "estate-sale"
    ),
    "moody-crush-2016": (
        "music-video", "midnight-blue", "desaturated", "single-color-pop", "attitude",
        "cinematic", "brooding", "high-contrast"
    ),
    "moonlight-blue-2015": (
        "day-for-night", "blue-hour", "moonlit", "two-stops-under", "nighttime-illusion",
        "impossible-moon", "faces-in-shadow", "cool-tones"
    ),
    "morning-block-1990": (
        "cereal-commercial", "cartoon-block", "mascot", "comet-trails", "loud-jingles",
        "weekday-morning", "pumped-color", "rerun"
    ),
    "music-16mm-1991": (
        "alt-rock", "flannel", "buzz-bin", "label-budget", "film-school", "splice-bumps",
        "seattle-sound", "handheld-camera"
    ),
    "music-countdown-master-1987": (
        "top-40", "chart-show", "vjs", "chroma-delay", "switcher-cuts", "request-line",
        "teen-audience", "hit-parade"
    ),
    "music-promo-1967": (
        "lip-sync", "sunlit-field", "optical-zoom", "flower-power", "promotional-clip",
        "band-on-film", "mod-fashion", "sun-flare"
    ),
    "musical-1952": (
        "mgm", "soundstage-glow", "dance-number", "chorus-line", "glamour", "diffused-close-up",
        "tap-dance", "showstopper"
    ),
    "myspace-2006": (
        "vlog", "profile", "glitter-graphics", "top-8", "emo", "scene-kid", "y2k", "personal-page"
    ),
    "neo-western-2017": (
        "contemporary-western", "modern-frontier", "power-lines", "cinematic-grade", "sicario",
        "grief", "sun-bleached-earth", "clean-digital"
    ),
    "neon-noir-2018": (
        "cyberpunk", "rain-slick", "arcade-glow", "synth-score", "drive", "wet-streets",
        "night-city", "magenta-glow"
    ),
    "neorealismo-1948": (
        "de-sica", "war-torn-streets", "nonprofessional-actors", "postwar-poverty",
        "documentary-style", "available-light", "bicycle", "working-class"
    ),
    "network-bw-1959": (
        "anthology", "live-television", "kinescope", "klieg-lights", "orthicon-glow",
        "soundstage", "prestige-drama", "studio-system"
    ),
    "network-feed-raw-1988": (
        "news", "behind-the-scenes", "raw-feed", "control-room", "unedited", "satellite-relay",
        "before-air", "internal-feed"
    ),
    "news-film-1975": (
        "assignment-desk", "telecine-judder", "six-oclock-news", "reversal-film",
        "field-reporter", "local-affiliate", "breaking-story", "film-at-eleven"
    ),
    "newsreel-1942": (
        "movietone", "home-front", "combat-footage", "patriotic", "propaganda-reel",
        "cinema-newsreel", "theater-intro", "stirring-music"
    ),
    "newsreel-sound-1930": (
        "movietone", "early-talkie", "optical-soundtrack", "square-frame", "historic-voice",
        "cinema-newsreel", "archival-audio", "crackling-voice"
    ),
    "nickelodeon-western-1913": (
        "one-reeler", "hand-cranked", "tent-show", "oater", "gallop", "sped-up-motion",
        "ortho-skies", "frontier-town"
    ),
    "nightshot-2001": (
        "infrared-green", "night-vision", "glowing-eyes", "paranormal-investigation",
        "found-footage", "ir-glow", "ghost-hunting", "creepy"
    ),
    "nitrate-terminal-1929": (
        "archival", "preservation", "lost-film", "fire-risk", "decomposition", "ghostly",
        "unwatchable", "final-screening"
    ),
    "nitrate-vault-1937": (
        "archival", "preservation", "studio-vault", "time-capsule", "fragile", "honey-glow",
        "rescued-print", "fading-fast"
    ),
    "noir-1947": (
        "detective", "hardboiled", "cigarette-smoke", "wet-asphalt", "venetian-blinds",
        "femme-fatale", "shadowy", "double-cross"
    ),
    "nordic-noir-2011": (
        "detective", "wallander", "december-light", "knitwear", "procedural", "slate-blue",
        "muted-winter", "brooding"
    ),
    "nouvelle-vague-1962": (
        "new-wave", "godard", "jump-cut", "handheld", "paris-streets", "youthful", "spontaneous",
        "cigarette-smoke"
    ),
    "pal-vhs-1988": (
        "retro", "nostalgic", "hanover-bars", "fifty-hertz", "european-tape", "import-copy",
        "stable-hue", "mains-hum", "any-program"
    ),
    "panavision-disaster-print-1974": (
        "blockbuster", "disaster-movie", "ensemble-cast", "practical-effects", "smoke-and-fire",
        "big-budget", "roadshow-epic", "poseidon"
    ),
    "pastel-musical-1964": (
        "cherbourg", "candy-colors", "sung-dialogue", "parisian-romance", "storybook-town",
        "operetta", "wallpaper-perfect", "sugared-light"
    ),
    "pastel-pop-2019": (
        "mint-and-pink", "instagram-aesthetic", "brand-safe", "influencer", "soft-light",
        "oat-milk", "lifestyle-content", "airy"
    ),
    "pathe-stencil-1923": (
        "fairy-tale", "trick-film", "storybook", "hand-tinted", "parisian", "fantastical",
        "dreamlike", "early-special-effects"
    ),
    "pbs-pledge-1983": (
        "telethon", "tote-bag", "phone-volunteers", "folding-tables", "member-supported",
        "fundraising", "viewers-like-you", "call-in-now"
    ),
    "pirate-uhf-1987": (
        "clandestine", "rooftop-transmitter", "outlaw-broadcast", "bent-sync", "unlicensed",
        "radio-free", "tower-block", "forty-watts"
    ),
    "pixel-1990": (
        "ega-vga", "shareware", "dos-game", "ordered-dither", "chunky-pixels", "nostalgic",
        "boot-disk", "dos-prompt"
    ),
    "pixelvision-1989": (
        "fisher-price", "toy-camera", "art-school", "smeared-motion", "cassette-video",
        "charcoal-texture", "underground-video-art", "handheld-toy"
    ),
    "poetic-realism-1937": (
        "foggy-docks", "doomed-romance", "fatalism", "working-class-paris", "gentle-contrast",
        "silvery-mist", "haloed-lamps", "predawn-melancholy"
    ),
    "portable-bw-1963": (
        "retro", "nostalgic", "rabbit-ears", "kitchen-tv", "tiny-speaker", "swimming-snow",
        "roofline-ghost", "countertop-tv", "any-program"
    ),
    "precode-studio-print-1932": (
        "drama", "gangster", "risque", "hays-code-era", "scandalous", "hollywood-glamour",
        "fast-talking", "pre-war"
    ),
    "press-reel-pool-1963": (
        "assignment-desk", "wire-service", "pool-camera", "sprocket-bruised", "hard-contrast",
        "missed-focus", "before-dawn-print", "breaking-history"
    ),
    "print-etch-1957": (
        "caption-burn", "burned-in-text", "emulsion-etched", "white-serif", "no-outline",
        "flare-prone", "foreign-film", "hand-etched"
    ),
    "propaganda-1943": (
        "victory-bonds", "home-front", "patriotic", "church-basement", "civic-duty", "rally-cry",
        "stirring-narration", "dupe-stock"
    ),
    "psp-ripped-2006": (
        "retro", "nostalgic", "bus-ride", "memory-stick", "handheld-gaming", "commute",
        "ripped-video", "umd", "any-program"
    ),
    "psychedelic-optical-1968": (
        "acid-trip", "light-show", "liquid-projection", "fillmore", "trippy", "kaleidoscopic",
        "strobing-color", "freak-out"
    ),
    "public-access-1989": (
        "community-tv", "local-weirdo", "one-camera-show", "fluorescent-hum", "outsider-art",
        "call-in-show", "channel-19", "after-midnight"
    ),
    "quadruplex-variety-1958": (
        "two-inch-tape", "image-orthicon-bloom", "live-broadcast", "control-room",
        "vaudeville-tv", "soundstage", "tape-splice-edit", "broadcast-history"
    ),
    "realplayer-1999": (
        "retro", "nostalgic", "buffering", "dial-up-era", "early-internet", "choppy",
        "modem-noise", "aquarium-echo", "any-program"
    ),
    "regional-weather-1973": (
        "forecast", "meteorologist", "weather-map", "plumbicon", "five-day-outlook",
        "physical-map-board", "early-color-tube", "booth-narration"
    ),
    "rescued-scan-2019": (
        "4k-restoration", "preservationist", "film-archive", "pin-registered", "digital-rescue",
        "museum-quality", "frame-by-frame", "careful-scan"
    ),
    "retro-grain-1968": (
        "outside-broadcast", "warm-highlights", "soft-lens", "dark-corners", "uncorrected-tape",
        "even-grain", "baseline-warmth", "tape-era"
    ),
    "revisionist-autumn-1973": (
        "new-hollywood", "zoom-lens", "rust-and-mud", "anti-heroic", "peckinpah", "flat-daylight",
        "fading-myth", "no-white-hats"
    ),
    "riso-flyer-1985": (
        "music", "concert", "punk", "basement-show", "zine-culture", "two-color-print",
        "gig-poster", "diy-print"
    ),
    "rptv-superbowl-1993": (
        "sports", "football", "big-game", "party", "nachos", "commercials", "halftime-show",
        "living-room"
    ),
    "safety-print-1952": (
        "archival", "acetate-safety-stock", "velvet-midtones", "first-generation", "lab-fresh",
        "quiet-grain", "best-behavior", "pristine-quality"
    ),
    "satellite-feed-1991": (
        "raw-feed", "between-commercials", "low-noise-relay", "static-specks", "pre-air",
        "uplink", "downlink", "backhaul-signal"
    ),
    "scope-1958": (
        "roadshow", "black-bars", "biblical-spectacle", "grand-vista", "reserved-seating",
        "cast-of-thousands", "sword-and-sandal", "widescreen-grandeur"
    ),
    "screen-recording-2009": (
        "experimental", "recursive-copy", "screen-capture", "moire-pattern", "backlight-glow",
        "secondhand-copy", "analog-to-digital", "camera-on-screen"
    ),
    "sdh-2007": (
        "dvd", "dialogue-text", "accessibility", "deaf-and-hard-of-hearing", "sound-cues",
        "bracketed", "speaker-names", "home-theater"
    ),
    "security-vcr-1994": (
        "aisle-five", "time-lapse-stutter", "phosphor-smear", "retail-security",
        "overnight-watch", "evidence-tape", "parking-lot-cam", "grainy-monitor"
    ),
    "serial-western-1938": (
        "cliffhanger", "matinee-crowd", "chapter-play", "kid-audience", "worn-gray", "fistfight",
        "weekly-installment", "poverty-row"
    ),
    "sharpness": (
        "hd", "edge-enhance", "crispness", "clarity", "unsharp-mask", "blur", "restoration",
        "touch-up"
    ),
    "sign-off-1979": (
        "national-anthem", "test-pattern", "transmitter-hum", "end-of-broadcast", "insomniac",
        "empty-airwaves", "static-after", "overnight"
    ),
    "silent-1918": (
        "melodrama", "tinted-print", "hand-cranked", "piano-score", "flickering",
        "ghostly-motion", "early-cinema", "exhibition-print"
    ),
    "silent-comedy-1925": (
        "slapstick", "pratfall", "custard-pie", "chase-sequence", "live-wire-print",
        "vaudeville-comedy", "sight-gag", "two-reel-comedy"
    ),
    "sitcom-1993": (
        "laugh-track", "three-camera", "friday-night-lineup", "soft-bloom", "studio-audience",
        "tgif", "warm-glow", "forgiving-video"
    ),
    "skate-hi8-1996": (
        "fisheye-lens", "curb-grinding", "vx1000", "street-skating", "backyard-ramp",
        "barrel-distortion", "dubbed-soundtrack", "skate-video"
    ),
    "slasher-answer-print-1980": (
        "final-girl", "friday-the-13th", "stalker-pov", "body-count", "tungsten-glow",
        "practical-gore", "dense-blacks", "oily-flare"
    ),
    "slow-cinema-2009": (
        "long-take", "tarkovsky", "minimalist-sound", "patient-camera", "static-shot",
        "meditative", "glacial-pace", "empty-frame"
    ),
    "soap-opera-1982": (
        "organ-sting", "cliffhanger-episode", "afternoon-tv", "tape-to-tape-editing",
        "studio-set", "weepy", "gauzy-focus", "supercouple"
    ),
    "soviet-color-1975": (
        "drama", "mosfilm", "austere", "state-cinema", "cold-war-era", "muted-palette",
        "socialist-realism", "behind-the-curtain"
    ),
    "spaghetti-scope-1966": (
        "leone", "dubbed-dialogue", "sun-bleached-badlands", "extreme-close-up", "standoff",
        "desert-heat", "terracotta-faces", "two-perf-grain"
    ),
    "stag-loop-1959": (
        "underground", "peep-show", "coin-operated", "novelty", "backroom", "risque",
        "flickering-loop", "worn-print"
    ),
    "step-print-1994": (
        "wong-kar-wai", "neon-alley", "unrequited-longing", "jukebox-glow", "dragged-motion",
        "hong-kong-nights", "time-lapse-emotion", "neon-ribbons"
    ),
    "sticky-shed-umatic-1981": (
        "archival", "preservation", "binder-failure", "oven-bake", "audio-dropout",
        "format-obsolescence", "vault-tape", "deteriorating"
    ),
    "storm-antenna-1966": (
        "retro", "nostalgic", "lightning-strike", "static-crash", "rabbit-ears", "stormy-night",
        "signal-fade", "thunderhead", "any-program"
    ),
    "storybook-symmetry-2012": (
        "wes-anderson", "dollhouse-framing", "centered-composition", "pastel-palette",
        "deadpan-humor", "flat-frontal-light", "wildflower-press", "twee"
    ),
    "streaming-filmic-2021": (
        "a24", "faux-grain", "warm-neutral-skin", "8k", "binge-watch", "streaming-service",
        "subtle-grade", "gentle-s-curve"
    ),
    "student-film-1971": (
        "drama", "experimental", "film-school", "earnest", "first-film", "ambitious",
        "borrowed-gear", "underexposed"
    ),
    "sunday-comics-1972": (
        "cartoons", "funny-pages", "syndicated-strip", "sunday-supplement", "cmyk-rosette",
        "newsprint-color", "weekend-read", "offset-print"
    ),
    "sunset-scope-1956": (
        "monument-valley", "golden-hour", "cattle-drive", "big-sky-country", "dust-in-the-beam",
        "a-picture", "cinemascope-vista", "frontier-panorama"
    ),
    "super16-indie-1994": (
        "credit-card-budget", "festival-favorite", "mumblecore", "low-budget", "first-feature",
        "16mm-blowup", "scrappy", "breakout-film"
    ),
    "super8-1974": (
        "backyard-bbq", "faded-warmth", "big-soft-grain", "cartridge-load", "home-projector-whir",
        "family-archive", "summer-memories", "birthday-candles"
    ),
    "supermarionation-print-1966": (
        "puppets", "scifi", "thunderbirds", "marionette", "model-effects", "miniature-sets",
        "kids-adventure", "tv-puppetry"
    ),
    "svhs-1992": (
        "retro", "nostalgic", "prosumer-grade", "camcorder-flex", "four-hundred-lines",
        "hifi-audio", "enthusiast", "upgrade-format", "any-program"
    ),
    "tabloid-reenactment-1992": (
        "dramatization", "true-crime", "hidden-identity", "actors-portray", "lurid-headline",
        "low-light-video", "sensationalized", "voice-disguised"
    ),
    "talk-show-1984": (
        "studio-audience", "hot-lights", "confessional-guest", "couch-and-desk", "applause-sign",
        "station-archive", "sequin-trails", "waxy-skin"
    ),
    "tape-swap-4th-gen-1994": (
        "anime-club", "mail-order-tape", "otaku", "vcr-daisy-chain", "flagging-picture",
        "four-vcrs-deep", "dedicated-fandom", "import-anime"
    ),
    "teal-orange-2012": (
        "4k", "color-grade", "tentpole", "summer-movie", "popcorn", "trailer-ready",
        "digital-cinema", "punchy"
    ),
    "technicolor-sagebrush-1939": (
        "singing-cowboy", "open-range", "three-strip-glory", "blue-never-was", "rim-halation",
        "red-kerchief", "prairie-skies", "matinee-western"
    ),
    "techniscope-blowup-1966": (
        "vintage", "budget-widescreen", "location-shooting", "co-production", "enlarged-grain",
        "theatrical", "cost-saving", "genre-picture"
    ),
    "teletext-1979": (
        "subtitles", "ceefax", "double-height-text", "chunky-blocks", "service-yellow",
        "broadcast-data", "character-generator", "analog-data-page"
    ),
    "telethon-1976": (
        "tote-board", "marathon-broadcast", "charity-drive", "phone-bank", "fundraiser",
        "jerry-lewis", "tired-hosts", "video-noise-smear"
    ),
    "three-strip-worn-1946": (
        "epic", "roadshow", "dye-transfer", "touring-print", "small-town-cinema", "worn-reel",
        "grand-spectacle", "fortieth-town"
    ),
    "threestrip-1939": (
        "fantasy", "wizard-of-oz", "fairy-tale", "jewel-tones", "storybook", "dazzling",
        "rainbow-halos", "musical-epic"
    ),
    "todd-ao-roadshow-1958": (
        "epic", "premiere-engagement", "reserved-seating", "intermission", "overture",
        "spectacle", "grand-scale", "cinerama-rival"
    ),
    "tokyo-spectacle-1962": (
        "kaiju", "giant-monster", "monster-movie", "godzilla", "toho", "japanese-scifi",
        "suitmation", "rubber-suit"
    ),
    "training-film-1966": (
        "safety-film", "filmstrip-narrator", "workplace-safety", "av-department",
        "ektachrome-flat", "orientation-video", "hard-hat", "dry-narration"
    ),
    "travelogue-1958": (
        "postcard-saturation", "lecture-hall", "world-tour", "exotic-destination",
        "slide-show-companion", "vacation-footage", "narrated-journey", "armchair-travel"
    ),
    "tv-movie-1977": (
        "tv-movie", "movie-of-the-week", "sunday-night-movie", "telefilm", "amber-warmth",
        "network-premiere", "broadcast-premiere", "grain-under-tape"
    ),
    "two-reeler-chase-1926": (
        "slapstick", "keystone-cops", "pursuit-picture", "pie-fight", "frantic-pace",
        "splice-per-gag", "live-wire-comedy", "two-reeler"
    ),
    "twostrip-1929": (
        "dreamlike", "peach-and-seafoam", "off-register", "early-hollywood", "art-deco",
        "surreal-palette", "nostalgic", "antique-color"
    ),
    "typewriter-doc-1976": (
        "16mm", "location-card", "field-report", "investigative", "courier-font",
        "blinking-cursor", "true-crime", "expose"
    ),
    "uhf-horror-host-1971": (
        "elvira", "horror-host", "channel-62", "cackling-laugh", "herringbone-weave",
        "midnight-monster-movie", "tube-glare", "late-show"
    ),
    "umatic-news-1982": (
        "eng-camera", "news-van", "three-quarter-inch", "field-reporter",
        "professional-bandwidth", "beta-precursor", "local-news-archive", "tape-based-eng"
    ),
    "vaporwave-vhs-1986": (
        "synthwave", "outrun", "pink-and-teal", "phosphor-trails", "fm-radio-dub",
        "mall-aesthetic", "analog-dream", "cassette-futurism"
    ),
    "vcd-1997": (
        "retro", "nostalgic", "bootleg-market", "hong-kong", "night-market", "blocky-cuts",
        "pan-and-scan", "dollar-bin", "any-program"
    ),
    "vcr-osd-1990": (
        "subtitles", "on-screen-display", "dot-matrix-text", "deck-firmware", "channel-clock",
        "timer-display", "firmware-font", "shivering-text"
    ),
    "vhs-1985-sp": (
        "retro", "nostalgic", "standard-play", "reliable", "good-deck", "everyday-tape",
        "default-look", "familiar", "any-program"
    ),
    "vhs-camcorder-1989": (
        "orange-date-stamp", "pumping-iris", "big-camcorder", "birthday-party", "shoulder-mount",
        "autofocus-hunt", "family-event", "home-recording"
    ),
    "vhs-camcorder-1996": (
        "white-date-stamp", "vhs-c", "compact-camcorder", "tighter-image", "family-gathering",
        "cleaner-color", "handheld-video", "pocket-camcorder"
    ),
    "vhs-dub-generation": (
        "retro", "nostalgic", "copy-of-a-copy", "tape-trading", "fifth-generation",
        "smeared-chroma", "underground-network", "dubbed-tape", "any-program"
    ),
    "vhs-ep-longplay": (
        "retro", "nostalgic", "six-hour-tape", "budget-recording", "t-120", "slow-speed",
        "muddy-image", "economy-mode", "any-program"
    ),
    "vhs-rental-1992": (
        "blockbuster", "be-kind-rewind", "video-store", "late-fee", "well-loved", "dusty-shelf",
        "clamshell-case", "tracking-storm"
    ),
    "vhs-tape-start": (
        "rainbow-junk", "vertical-roll", "play-button", "tracking-lock", "countdown-leader",
        "reveal-effect", "staggered-picture", "tape-header"
    ),
    "vhs-taped-off-air-1987": (
        "saturday-morning", "antenna-ghosting", "channel-readout", "home-recording",
        "off-air-capture", "preserved-broadcast", "commercial-breaks", "snow-and-tape"
    ),
    "vhs-tracking-nightmare": (
        "rolling-noise-bands", "shredded-lines", "tracking-knob", "transport-failure",
        "static-roll", "worn-out-heads", "video-noise-storm", "unstable-playback"
    ),
    "video8-holiday-1990": (
        "shore-vacation", "handycam", "azimuth-shimmer", "afm-sound", "beach-day", "seagulls",
        "gray-date-stamp", "palm-sized-camera"
    ),
    "vinegar-ektachrome-1974": (
        "archival", "preservation", "acetate-decay", "warping", "pungent", "fading-memory",
        "reel-rescue", "time-capsule"
    ),
    "vistavision-release-1956": (
        "epic", "widescreen-glamour", "reserved-seating", "hollywood-prestige", "roadshow",
        "premiere", "cinemascope-rival", "grand-picture"
    ),
    "vitaphone-palace-1929": (
        "music", "revue", "vaudeville", "jazz-age", "movie-palace", "orchestra-pit",
        "gala-premiere", "talkie-debut"
    ),
    "water-damaged-attic-1965": (
        "home-movie", "attic-find", "flood-damage", "water-stains", "forgotten-box", "mildew",
        "family-archive", "estate-sale"
    ),
    "webcam-2004": (
        "chat", "video-call", "msn-messenger", "dorm-room", "buddy-list", "late-night",
        "dial-tone", "pixelated-face"
    ),
    "webcam-stream-2012": (
        "chat", "video-call", "laptop-lid", "white-balance-hunt", "stuck-pixel", "webcam-light",
        "late-night", "dorm-desk"
    ),
    "webcore-2007": (
        "early-youtube", "flv-blocks", "subpixel-stripes", "hand-me-down-monitor", "embed-code",
        "amber-tint", "webcam-quality", "grainy-reupload"
    ),
    "webvideo-2006": (
        "retro", "nostalgic", "broadcast-yourself", "grainy-upload", "early-creator", "low-res",
        "dial-up", "home-clip", "any-program"
    ),
    "wedding-16mm-1954": (
        "blushing-kodachrome", "nervous-framing", "rented-camera", "family-heirloom",
        "anniversary-reel", "church-steps", "bouquet-toss", "reception-hall"
    ),
    "wedding-master-1991": (
        "pro-mist-filter", "videographer", "white-clip", "wireless-lav", "vows", "garter-toss",
        "first-dance", "reception-video"
    ),
    "zine-photocopy-1981": (
        "diy-culture", "cut-and-paste", "toner-streaks", "basement-press", "underground-press",
        "staple-bound", "fourth-generation-copy", "skewed-page"
    ),
}
