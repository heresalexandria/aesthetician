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

# grain/noise taste: 0 = clean, 1 = as authored, 2 = heavy
aesthetician apply clip.mp4 -p news-film-1975 --texture 0.4
```

## Controlling grain and noise

Film and tape noise is **regenerated every frame** — that liveliness is the point;
a frozen noise pattern reads as a dirty lens, not as film. What you can control:

| control | what it does |
|---|---|
| `--texture 0…2` | one dial for every grain/noise/speckle *amount* in the chain (grain, tape noise, snow, dust, cel dirt, toner…). `0` renders the look completely clean. |
| `--set grain.size=N` | clump diameter. Lower = finer, tighter grain. |
| `--set grain.size_ref=output` | make `grain.size` mean pixels **in the delivered file** instead of at the era simulation resolution. |
| `--intensity 0…2` | the broader strength dial (damage, warping, glow — everything flagged as an amount). |

**Why grain can look chunkier than the number suggests:** most presets simulate at
an era resolution (`proc_height`, e.g. 520 lines for Super 8) and upscale to your
delivery size afterwards, which magnifies every texture generated inside — a 2.0 px
clump lands at ~5 px in a 1280-tall export. That magnification is physically right
(small-gauge film really is grainy relative to its frame), but it means the `size`
parameter is measured *before* the upscale. Use `grain.size_ref=output` when you
want to pin the delivered clump size instead.

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
