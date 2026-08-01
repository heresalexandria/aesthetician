# Aesthetician - Desktop App Guide

```bash
cd app && npm start
```

## Finding a look: search, filters, favorites

The browse pane is built for 192 presets:

- **Search** matches name, id, era, family, tagline and tags. Press **/**
  (or **⌘F**) to jump to it from anywhere.
- **Family chips** under the search box narrow the list to one or more
  families; click a chip again to release it, or **All** to reset.
- The **era dropdown** narrows to a single decade, and combines with the
  family chips and search.
- **Favorites**: hover a preset row and click the star (or star the current
  preset from the panel header on the right). Favorites float to the top of
  the list in their own group, and the **★** chip shows only them. Favorites
  persist across launches.
- **↑ / ↓** walk the list one row at a time and render each one as you go, so
  you can audition a whole family without touching the mouse. See below.

## Running the list with the arrow keys

Pick anything on the left, then press **↓** and **↑** to step through the
aesthetics in the order you see them. Each stop re-renders the preview, so
holding the key runs the catalog past the player.

- The keys follow what is **on screen**: the search results you filtered down
  to, in list order, skipping any family you have collapsed.
- They work while the **search box** has focus - type `vhs`, then arrow through
  the hits without reaching for the mouse. They are left alone inside sliders
  and dropdowns, where arrows already mean something.
- A favorite is drawn twice (once at the top, once in its family) but stepped
  onto once, at the top copy, so a run down the list never renders it twice.
- Renders are debounced: holding the key scrolls freely and only the row you
  settle on is rendered.

## Keyboard shortcuts

| key | does |
|---|---|
| **⌘O** | open a video or audio file (same as the Browse button) |
| **⌘E** | export the current clip (starts another; it does not wait) |
| **↑ / ↓** | previous / next aesthetic in the list |
| **Space** | play / pause the preview |
| **B** (hold) | show the untreated original, like holding A/B |
| **/** or **⌘F** | focus the preset search |
| **Esc** | close the exports panel |

## Working with clips: sessions and tabs

Each video you open is a **session** with its own aesthetic, parameter overrides,
seed and scrub position. Sessions appear as tabs under the title bar, labelled
with the filename and whichever aesthetic that clip is currently wearing.

| I want to… | Do this |
|---|---|
| open another video | click **+** in the tab strip, then drop (or the current clip stays put) |
| compare two treatments of the same clip | open it twice with **+**, set a different aesthetic in each tab, click between them |
| go back to a clip | click its tab - preset, knobs, seed, intensity, texture and scrub all return exactly as you left them, and its rendered preview reappears instantly from cache |
| close a clip | the **×** on its tab (you land on the neighbouring tab, or the drop screen if it was the last one) |
| abandon a new-video screen | **← back to what I was working on** |

Switching tabs never re-renders: the preview files persist in the cache, so
flipping between tabs is instant.

The chip in the title bar naming the open clip is a button: click it to show
that file in the Finder. Hover it for the full path. If the file has been moved,
renamed or deleted since you opened it, the status line at the bottom says so
rather than opening nothing.

## Dropping an audio file

Audio files are first-class sources. Drop a WAV, MP3, FLAC or M4A and the app
switches into an audio session:

- the **picture** half of the parameter panel disappears - only **SOUND** is
  shown, with a note saying how many picture effects the chosen preset is
  skipping;
- the audio-first presets move to the top of the browse list (all 192 still work
  - every preset has a sound chain - but the `audio` family is the one designed
  for this);
- the video/audio-only export toggles are hidden, the export button becomes
  **Export Full Audio**, and the save dialog offers audio formats;
- the tab is marked with a **♪**, and the player becomes a listening surface -
  hold **A/B** to hear the untreated original.

Export format follows the extension: WAV and AIFF stay lossless, FLAC is
lossless compressed, MP3/M4A/AAC encode at 320k.

Audio and video sessions can be open side by side; each tab keeps its own kind.

## The preview cache

Every preview render is written to disk, keyed by the **exact** parameter set that
produced it - clip, preset, variant, every override, seed, intensity, texture,
scrub position. That is what makes undoing a knob twiddle instant instead of a
re-render.

The footer shows its current size and file count:

```
Preview cache   184.0 MB · 37 previews   Clear   Reveal
```

- **Clear** deletes every cached render. Nothing is lost but time - your open
  tabs keep all their parameters and simply re-render on the next Preview.
- **Reveal** opens the folder, which lives in the app's user-data directory:
  `~/Library/Application Support/aesthetician-app/preview-cache` on macOS,
  `%APPDATA%\aesthetician-app\preview-cache` on Windows.

Exports never go through the cache - those are written wherever you point the
save dialog.

## Exporting more than one thing at once

**Export Full Video** does not put the app into an exporting mode. Press it,
pick a destination, and carry on: change the aesthetic, switch tabs, start
another export. Each job holds a frozen copy of the settings it was started
with, so nothing you do afterwards can change what is being written.

A button appears at the **top right** while anything is in flight - `2
exporting`, with a turning spinner in place of its download arrow and the
combined progress as a hairline underneath. A toast slides in under the title
bar when a job starts and again when it lands, so you can look away from the
window and still know where things are. Click the button for the queue:

- one row per export, newest first, with its own progress bar and phase;
- **×** on a running or waiting job stops it and deletes the partial file;
- **Reveal** on a finished one opens it in the Finder;
- **Clear finished** tidies the list without touching anything still running.

Two render at once and the rest wait their turn, marked *waiting for a free
slot*. A full-length pass is CPU-bound, so a third in parallel would only make
the first two slower. Exporting the same destination twice is refused rather
than letting two jobs race over one file.

### Reading the progress

A render is three passes - picture, then sound, then muxing the two together -
and the bar covers all of them as one climb, weighted by how long each usually
takes. Picture is most of it, so a job sitting at 86% has finished its frames and
is working on audio. The hairline under the titlebar button is the whole batch
you started, counting finished jobs as finished: one of a pair landing pushes it
up, never back down.

## Version and updates

The version sits at the top right, left of the exports button. Click it for the
about dialog, which has a **Check for updates** button.

Aesthetician also checks by itself, at most once a day. When a newer release
exists, a blue **Update available** button appears next to the version; clicking
it downloads the release, checks it against the checksum published with it,
replaces the installed copy and restarts. Nothing is downloaded until you ask.

If anything is still exporting, the button turns red and says **Finish exports
first**, and the export panel opens. Let the renders finish, or stop them, and
the update goes through. See [updates.md](updates.md) for the details.

## Stacking aesthetics as layers

One aesthetic is the usual case and behaves exactly as it always has. When you
want two, the row you are hovering grows a green **+**: click it to add that
aesthetic as another layer on top. **+** or **=** on the keyboard does the same
to whichever row is highlighted, so search-and-stack never needs the mouse.

Arrowing and clicking still *swap* the selected layer rather than adding to it -
that is what keeps ↑/↓ usable for auditioning a whole family against the rest of
your stack. **Enter** commits the highlighted aesthetic on its own, dropping
everything else.

With more than one layer a **Layers** panel appears above the knobs:

- rows are in **processing order**, top of the list rendered first;
- the **checkbox** takes a layer out of the render without losing its settings;
- **drag by the grip** to change the order effects are applied in;
- **×** removes a layer (removing the last one leaves an empty slot for your
  next pick);
- clicking a row selects it, and everything below - variant, Intensity, Texture,
  seed and every knob - belongs to **that layer alone**.

The same aesthetic can be stacked on itself. Two passes of the same tape is a
real thing, and so is a second helping of grain.

Layers render **in sequence**: layer 2 treats what layer 1 actually produced,
including whatever resolution and detail layer 1 threw away. That is what makes
a stack compound the way real generations do - and it means each layer is a full
render pass, so a three-layer export takes roughly three times as long. The
panel says so once you reach three.

## Saving your own aesthetics

Once you have a preset dialled in - knobs moved, intensity and texture set,
a seed you like - the **bookmark** button beside the star saves the whole thing
as a custom aesthetic. It offers a name (`Shoulder Camcorder - custom 2026-07-31
14:22`); replace it with something you will recognise.

Saved customs appear in a **MY AESTHETICS** group at the very top of the browse
list, each with a **✎** badge on its thumbnail and a note of the preset it grew
from. The **✎** chip beside the search box shows only them.

- Clicking one restores everything: variant, every override, intensity, texture
  and seed.
- Move a knob afterwards and the header adds **· edited**, so the list never
  claims you are looking at the saved version when you are not. Save again to
  keep the new one as well.
- Hover a custom row for **✎** to rename and **×** to delete. Deleting only
  discards the recipe; the preset it was built on is untouched, and any tab
  wearing it keeps its settings.
- Exports name the file after the custom (`clip.night-shift.mp4`).

A custom stores the base preset's **id**, not a copy of its effect chain, so a
preset that gains an effect in a later version carries your customs forward.
They are kept with your favorites and survive restarts.

## Understanding the knobs

Hover any control - slider, toggle, dropdown, or an effect's header - and a
tooltip explains it: what the parameter physically models, its range and unit,
the value this preset uses, the effect's own default when it differs, whether it
follows the **Intensity** or **Texture** master dial, and the `--set` path to
reach the same control from the CLI.

The two master dials sit above the effect stack:

- **Intensity** - everything the preset does to picture and sound: damage,
  warping, glow, colour treatment.
- **Texture** - grain, tape noise, RF snow, dust and speckle only. Drag to **0**
  for a perfectly clean version of the look. Decay *content* (mould, water
  staining, nitrate) is deliberately left alone.

Any override you make is highlighted, and the **↺** beside it restores the
preset's value. While any overrides exist, a strip above the effect stack
counts them and offers **Reset all**; effects carrying a tweak show a dot on
their header.

### On-screen text and dates

Presets that burn text into the picture - camcorder date stamps, security
clocks, `PLAY`/`REC` chrome, tape counters, channel labels - mark that effect
with an **Aa** badge and open it on arrival, because the text is the first
thing anyone wants to change.

- **Show** at the top of the effect turns the whole overlay off in one click,
  leaving the rest of the preset alone.
- **Start Time** is a real date-and-time picker; the clock advances from there
  with playback. It cannot produce a value the engine refuses, which a typed
  date could.
- Tape counters, channel labels and the rest are plain text fields, one per
  line so there is room to read them.

The same controls exist on the CLI as `--set timestamp.show=false`,
`--set timestamp.start='1994-11-05 20:15:30'`, `--set osd.channel='CH 12'`.

## Preview fidelity

Previews are rendered by the same engine that does the export - so what you
see is what you get. Two dropdowns beside the scrub bar control the trade
between speed and fidelity, and both settings persist across launches:

- **length** (2s / 3s / 5s / 8s) - how much of the clip each preview renders;
- **scale** (25% / 50% / 75% / 100%) - the preview's render resolution.
  Exports always render at full resolution regardless.

The preview loops forever, which is not always what you want with the app open
on a second screen. **⏸** beside the A/B button holds it on a frame (so does
**Space**), and it stays held through the next render rather than restarting
the loop under you.

**auto** re-renders after every change. With it on there is nothing for a
Preview button to do, so there isn't one; turn auto off and **Preview** appears
beside the switch as the way to ask for a render.

Two caveats worth knowing at reduced scale:

- Real-codec presets (`codec_era`, `codec_glitch`) encode at the preview's
  smaller frame size, so blocking is proportionally coarser than the export.
- Grain is a fixed fraction of the frame, so it matches; but if you set
  `grain.size_ref = output` it becomes an absolute pixel size and will read
  differently between a half-res preview and the full export.
