# Aesthetician — Usage

## Setup (macOS)

```bash
brew install ffmpeg            # if not already present
cd aesthetician
python3 -m venv .venv
.venv/bin/pip install -e .
cd app && npm install          # for the GUI
```

Optional, once (AI overlay plates — needs OPENAI_API_KEY in `.env`):

```bash
.venv/bin/aesthetician assets generate
```

## CLI

```bash
# discover
aesthetician list                       # all presets by family
aesthetician list --family vhs
aesthetician info vhs-camcorder-1989    # every knob, range, and variant

# apply
aesthetician apply clip.mp4 -p vhs-camcorder-1989
aesthetician apply clip.mp4 -p film-musical-1952 --variant worn-print -o out.mp4
aesthetician apply clip.mp4 -p vhs-rental-1992 \
    --set vhs.tracking_error=0.8 --set vhs.dropouts=3.5 --set a_wow_flutter.wow_depth=18

# quick look (3 s, half res, from the middle)
aesthetician preview clip.mp4 -p broadcast-news-film-1975

# audio or video alone
aesthetician apply clip.mp4 -p audio-am-1948            # audio-only family
aesthetician apply clip.mp4 -p vhs-ep-longplay --video-only

# reproducibility & strength
aesthetician apply clip.mp4 -p super8-1974 --seed 42 --intensity 1.4
```

Every parameter printed by `info` can be overridden with `--set
effect.param=value`; audio effects start with `a_`. Repeated effects get `#2`
suffixes (`grain#2.amount`).

## GUI

```bash
cd app && npm start
```

Drop a clip → pick an aesthetic → tweak knobs (preview re-renders
automatically, faithful to the final output) → hold **A/B** to flash the
original → **Export Full Video**.

## Notes

- Renders are deterministic per seed; the dice button rerolls character.
- `--intensity` scales the "amount-like" parameters chain-wide (0–2).
- Preview cache lives in the app's user-data dir and is keyed by every
  parameter, so flipping back to previous settings is instant.
