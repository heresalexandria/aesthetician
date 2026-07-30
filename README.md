# Aesthetician

**A premium archival-media aesthetic engine.** Aesthetician applies era-authentic looks — and sounds — to modern video: VHS in a dozen states of decay, three-strip Technicolor, 16mm news film, Saturday-morning cartoons, dying broadcast signals, early web video, and much more.

It is not a filter pack. Every aesthetic is a physically-motivated simulation of the original signal path:

- **Composite NTSC/PAL** is actually encoded onto a subcarrier and decoded like a receiver — dot crawl genuinely crawls, cross-color rainbows shimmer on fine detail, hue jitters per scanline.
- **VHS** models color-under chroma, VCR edge-enhancement ringing, head-switch bending, comet-tail dropouts, tracking storms, time-base error and generation loss.
- **Film** gets living multi-scale grain with luminance response, red halation, gate weave, hand-crank flicker, tramline scratches, splice jumps, dye-fade profiles (Eastman pink and friends), and projector presentation.
- **Digital-era looks run the real codecs** — MPEG-1/2, MSMPEG4, FLV, H.263, MJPEG at era bitrates, with true bitstream-corruption datamosh decoded through error concealment.
- **Audio** is treated with the same seriousness: wow/flutter from an integrated speed curve, tape saturation with head bump, vinyl crackle/pops/wear, optical-track noise, synthesized projector clatter, AM/FM/TV sound, era telephones with real μ-law, real low-bitrate MP3/AMR/G.726 round-trips, and eleven period speaker recipes.
- **Archive-grade extremes**: five-stage nitrate decomposition, vinegar-syndrome warp, water tide marks, sticky-shed tape, reel-change cue dots, rear-projection TV, CMYK halftone with true rosettes, photocopy generations, DX television that breathes with the ionosphere, PXL2000, LaserDisc, analog horror.
- **AI-generated overlay plates** (86 across 14 packs: dust, leaks, burns, grime, paper, tape creases, water stains, mold, emulsion decay, copier streaks, CRT glare, lens dirt, screen weaves, static discharge) blend with era-correct motion; 10 synthesized loopable ambience beds (projectors, TV-shop wall, CRT whine…) sit under the audio. Everything degrades gracefully to procedural fallbacks.

**191 presets across twelve families** (vhs / broadcast / film / cartoon / digital / audio-only / world / decay / exhibition / print / transmission / stylized), **238 variants**, 103 effects, and well over a thousand exposed parameters. Deterministic per seed.

## Setup (macOS)

```bash
brew install ffmpeg                    # if not already present
python3 -m venv .venv
.venv/bin/pip install -e .
cd app && npm install && cd ..        # for the GUI
```

Optional one-time asset generation (needs `OPENAI_API_KEY` in `.env`, see `.env.example`):

```bash
.venv/bin/aesthetician assets generate
```

## CLI

```bash
aesthetician list                          # every preset, by family
aesthetician info vhs-camcorder-1989       # every knob, range, and variant
aesthetician apply clip.mp4 -p vhs-rental-1992
aesthetician apply clip.mp4 -p musical-1952 --variant worn-print --seed 42
aesthetician apply clip.mp4 -p vhs-ep-longplay --set vhs.tracking_error=0.6 \
    --set a_wow_flutter.wow_depth=14 --intensity 1.3
aesthetician preview clip.mp4 -p news-film-1975    # fast 3 s look
aesthetician apply clip.mp4 -p audio-am-1948       # audio-only family
aesthetician apply song.wav -p audio-cassette-1984 # an audio FILE as the source
aesthetician apply clip.mp4 -p grindhouse-1973 --video-only
```

Any parameter shown by `info` can be overridden with `--set effect.param=value`
(audio effects start with `a_`). `--seed` pins the stochastic character;
`--intensity` scales damage/noise amounts chain-wide.

## GUI

```bash
cd app && npm start
```

Drop a clip (video **or** audio) → pick an aesthetic → tweak knobs (the preview re-renders through the
real engine, so what you see is what exports) → hold **A/B** for the original →
**Export Full Video**.

Each row in the browse list carries a thumbnail of that treatment (hover to see it
move) and a one-line summary of its artifacts. Hover any knob for a tooltip
explaining what it physically models, its range, and the `--set` path to reach it
from the CLI. Two master dials sit above the parameter stack: **Intensity**
(damage, warping, glow) and **Texture** (grain, tape noise, dust, speckle — drag
to 0 for a perfectly clean version of the look).

Open as many clips as you like: each is a tab with its own aesthetic and knob
positions, so you can try one clip several ways side by side, and switching back
is instant. The footer shows what the preview cache is costing you on disk, with
**Clear** and **Reveal** beside it.

Full walkthrough: [docs/app-guide.md](docs/app-guide.md).

Thumbnails are generated once:

```bash
.venv/bin/python scripts/make_thumbs.py
```

## Desktop app (packaged)

To build an installable app that needs no Python, ffmpeg or checkout:

```bash
python3 scripts/package/build.py --target mac
```

Artifacts land in `app/dist/` — a DMG on macOS (~495 MB, ~960 MB installed;
almost all of it NumPy/SciPy/OpenCV), an NSIS installer on Windows. The bundle
carries a relocatable CPython, static ffmpeg, and the asset packs.

### First run on macOS

The build is **ad-hoc signed** — there is no Apple Developer ID in this project —
which is enough to run locally but not enough to satisfy Gatekeeper on a
downloaded or copied DMG. The first launch will be blocked, showing a refusal or
*"Aesthetician is damaged and can't be opened"*. Either right-click the app and
choose **Open**, or clear the quarantine flag:

```bash
xattr -dr com.apple.quarantine /Applications/Aesthetician.app
```

After that it opens normally. Real distribution needs a Developer ID plus
notarization — see [docs/packaging.md](docs/packaging.md), which also covers the
GPL obligations that come with the bundled ffmpeg.

The Windows target is fully scripted but has not been built or tested on Windows.

## Documentation

- [docs/usage.md](docs/usage.md) — setup and workflows
- [docs/catalog.md](docs/catalog.md) — the full preset/parameter catalog
- [docs/app-guide.md](docs/app-guide.md) — using the desktop app
- [docs/packaging.md](docs/packaging.md) — building installable macOS/Windows apps
- [docs/architecture.md](docs/architecture.md) — how the engine works
- [docs/preset-plan.md](docs/preset-plan.md) — the design map of the library

## Development

```bash
.venv/bin/python tests/test_engine.py         # engine unit tests
.venv/bin/python tests/test_smoke.py          # end-to-end render
.venv/bin/python scripts/validate_presets.py  # preset/registry consistency
.venv/bin/python scripts/make_gallery.py --family vhs --input videos-samples/untreated.mp4
```

No media files or secrets are ever committed; sample footage lives untracked in
`videos-samples/`, generated assets in `assets/packs/`.
