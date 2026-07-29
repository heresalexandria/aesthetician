# Aesthetician — Architecture

## Overview

Aesthetician is a Python media engine wrapped by two frontends (a CLI and an
Electron app). Every aesthetic is a **preset**: an ordered chain of video
effects and audio effects with parameter values, optional era processing
resolution, and named variants.

```
input ──► video chain (streamed frames + real-codec file passes) ──► x264
      └─► audio chain (full-buffer DSP + real-codec round trips) ──► aac ──► mux
```

## Engine (`aesthetician/engine/`)

- **graph.py** — `Effect` base class with typed `Param` specs. Four kinds:
  `frame` (per-frame numpy transform), `filepass` (real codec round-trip on an
  intermediate file), `audio` (full-buffer DSP), `audio_filepass` (real audio
  codec round-trip). `Context` carries geometry, fps, seed, master intensity,
  and the noise system.
- **rng.py** — all randomness is deterministic per (seed, key): decorrelated
  PCG64 streams plus per-frame `TemporalNoise` tracks (band-limited smooth
  noise, 1/f drift, Poisson event masks). A render with the same seed is
  bit-identical in its stochastic decisions.
- **media.py** — ffmpeg-piped frame streaming (float32 RGB), audio buffers,
  muxing, and codec round-trip helpers.
- **render.py** — splits a chain into segments around file passes, composes
  **time remaps** (frame holds, pulldown, splice skips) into a monotonic
  source-index map, streams frames through each segment, then runs the audio
  chain and muxes. Presets can process at an era-authentic vertical resolution
  (`proc_height`, e.g. 480 for VHS) and upscale at the end (sharp/soft).
- **presets.py** — preset/variant model and registry. Overrides address
  parameters as `effect_key.param` (duplicated effects get `#2`, `#3`…).

## Effects (`aesthetician/effects/`)

Auto-registered on import; each declares UI-ready parameter metadata
(label/description/unit/group/choices/ranges) so both the CLI (`info`) and the
GUI parameter panel are generated from the same schema (`schema.py`).

Two temporal keys matter: `ctx.fi_out` (output timeline — film/tape-level
artifacts like grain refresh every frame) and `ctx.fi_src` (source timeline —
cel/content-level artifacts stick during frame holds).

## Assets (`aesthetician/assets/`)

Organic overlay plates (dust, light leaks, burns, grime, paper, tape creases)
are AI-generated once via `aesthetician assets generate` (OpenAI gpt-image-1,
key from `.env`) into `assets/packs/` (gitignored). The `plate` effect blends
them with era-correct motion. Every look degrades gracefully to procedural
fallbacks when packs are absent.

## Frontends

- **CLI** (`cli.py`) — `list`, `info`, `effects`, `schema`, `apply`, `preview`,
  `probe`, `snippet`, `assets`. `--set effect.param=value` overrides anything;
  `--seed` pins the stochastic character; `--intensity` scales flagged
  "amount" parameters chain-wide.
- **Electron app** (`app/`) — drag-and-drop; schema-driven parameter panel;
  debounced preview renders (3 s, half res) through the real engine (previews
  are faithful by construction); hold-to-compare A/B against the untouched
  original; full-quality export. The app shells out to the CLI with
  `--json-progress`.
