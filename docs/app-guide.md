# Aesthetician — Desktop App Guide

```bash
cd app && npm start
```

## Working with clips: sessions and tabs

Each video you open is a **session** with its own aesthetic, parameter overrides,
seed and scrub position. Sessions appear as tabs under the title bar, labelled
with the filename and whichever aesthetic that clip is currently wearing.

| I want to… | Do this |
|---|---|
| open another video | click **+** in the tab strip, then drop (or the current clip stays put) |
| compare two treatments of the same clip | open it twice with **+**, set a different aesthetic in each tab, click between them |
| go back to a clip | click its tab — preset, knobs, seed, intensity, texture and scrub all return exactly as you left them, and its rendered preview reappears instantly from cache |
| close a clip | the **×** on its tab (you land on the neighbouring tab, or the drop screen if it was the last one) |
| abandon a new-video screen | **← back to what I was working on** |

Switching tabs never re-renders: the preview files persist in the cache, so
flipping between tabs is instant.

## Dropping an audio file

Audio files are first-class sources. Drop a WAV, MP3, FLAC or M4A and the app
switches into an audio session:

- the **picture** half of the parameter panel disappears — only **SOUND** is
  shown, with a note saying how many picture effects the chosen preset is
  skipping;
- the audio-first presets move to the top of the browse list (all 191 still work
  — every preset has a sound chain — but the `audio` family is the one designed
  for this);
- the video/audio-only export toggles are hidden, the export button becomes
  **Export Full Audio**, and the save dialog offers audio formats;
- the tab is marked with a **♪**, and the player becomes a listening surface —
  hold **A/B** to hear the untreated original.

Export format follows the extension: WAV and AIFF stay lossless, FLAC is
lossless compressed, MP3/M4A/AAC encode at 320k.

Audio and video sessions can be open side by side; each tab keeps its own kind.

## The preview cache

Every preview render is written to disk, keyed by the **exact** parameter set that
produced it — clip, preset, variant, every override, seed, intensity, texture,
scrub position. That is what makes undoing a knob twiddle instant instead of a
re-render.

The footer shows its current size and file count:

```
Preview cache   184.0 MB · 37 previews   Clear   Reveal
```

- **Clear** deletes every cached render. Nothing is lost but time — your open
  tabs keep all their parameters and simply re-render on the next Preview.
- **Reveal** opens the folder, which lives in the app's user-data directory:
  `~/Library/Application Support/aesthetician-app/preview-cache` on macOS,
  `%APPDATA%\aesthetician-app\preview-cache` on Windows.

Exports never go through the cache — those are written wherever you point the
save dialog.

## Understanding the knobs

Hover any control — slider, toggle, dropdown, or an effect's header — and a
tooltip explains it: what the parameter physically models, its range and unit,
the value this preset uses, the effect's own default when it differs, whether it
follows the **Intensity** or **Texture** master dial, and the `--set` path to
reach the same control from the CLI.

The two master dials sit above the effect stack:

- **Intensity** — everything the preset does to picture and sound: damage,
  warping, glow, colour treatment.
- **Texture** — grain, tape noise, RF snow, dust and speckle only. Drag to **0**
  for a perfectly clean version of the look. Decay *content* (mould, water
  staining, nitrate) is deliberately left alone.

Any override you make is highlighted, and the **↺** beside it restores the
preset's value.

## Preview fidelity

Previews are rendered by the same engine that does the export, at half
resolution and three seconds long — so what you see is what you get, with two
caveats worth knowing:

- Real-codec presets (`codec_era`, `codec_glitch`) encode at the preview's
  smaller frame size, so blocking is proportionally coarser than the export.
- Grain is a fixed fraction of the frame, so it matches; but if you set
  `grain.size_ref = output` it becomes an absolute pixel size and will read
  differently between a half-res preview and the full export.
