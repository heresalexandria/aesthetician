# Expanded aesthetic atlas and interaction audit

The September 2026 expansion adds **211 presets**, taking the library from 789 to
**1,000 presets, 1,406 variants and 115 effects with 699 declared controls**.
There are 201 picture-and-sound recipes and 10 sound-only recipes; 40 of the new
presets belong to the arthouse family. All are explicit, independently editable
recipes in `aesthetician/presets/atlas_*.py`.

## Coverage

The collections extend carrier, optics, color, texture, print, display and sound
choices from 1894 through 2026. Each row below is a separate authored module;
the full parameter listings are in [the catalog](catalog.md).

| Area | Presets | Representative starting points |
|---|---:|---|
| Early photography and first cinema | 10 | Paper Positive Reconstruction; Museum Separation Master |
| Silent-era tinting and toning | 10 | Moonlit Cyan Reel; Silver Festival Scan |
| Sound-era silver prints | 10 | Soundstage Ribbon Silver; Fine Grain Academy Master |
| Color processes and release prints | 10 | Additive Screen Travel Color; Modern Reversal Gallery Scan |
| Small-gauge diaries and field film | 10 | Nine Five Garden Positive; Fresh Cartridge Wedding Film |
| Postwar art cinema | 10 | Postwar Apartment Silver; Desaturated Political Negative |
| 1970s modernist art cinema | 10 | Desert Modernist Bleach; Copper Surrealist Positive |
| 1980s–1990s independent film | 10 | Midnight Metro Reversal; Millennium Silver Diary |
| Contemporary art cinema | 10 | Digital Dusk Contemplation; Mineral Daylight Art Film |
| 2026 cinema and Hollywood finishing | 11 | Large Format Daylight Epic; Hollywood Blockbuster |
| Regional film archives | 10 | Mediterranean Harbor Reversal; Australasian Oral History Scan |
| Broadcast capture and delivery | 10 | Monochrome Studio Line Feed; Live Cinema Broadcast |
| Home tape and camcorders | 10 | First Home Deck Color; Last Analog Travel Camera |
| Institutional and oral-history records | 10 | Training Room Open Reel Video; Contemporary Oral History Master |
| Video art and installations | 10 | Electronic Amber Sculpture; Contemporary CRT Installation |
| Optical lab and preservation | 10 | Soft Matte Composite Print; Photochemical Gallery Filmout |
| Print, ink and animation | 10 | Graphite Animation Test; Contemporary Mixed Media Feature |
| Early digital capture and multimedia | 10 | Four Color Research Monitor; Pocket Raw Indie Grade |
| Web and streaming archives | 10 | Dialup Science Lecture; Modern Social Archive Copy |
| Modern cameras and creator finishing | 10 | Travel Drone Overcast; Digital Silver Portrait |
| Source-sound mastering and carriers | 10 | Oral History Cylinder Transfer; Contemporary Tentpole Stereo Mix |

Six Guide collections make the expansion discoverable: contemporary cinema,
art cinema across a century, photographic archives, institutional records,
expanded image art, and source-sound finishes. Search `atlas` to see all 211
new recipes or `2026` to explore the latest-era starting points.

The new **Cinema Finish** effect adds highlight desaturation, subtractive color
density, silver retention, local contrast, its spatial radius, and a mix control.
It operates on decoded SDR RGB. These are creative finishing interpretations,
not measured camera transforms or a way to recover clipped highlights. A
blockbuster treatment changes the supplied image and soundtrack; lighting,
production design, performances and editorial choices still come from the source.

No new recipe invents dialogue, music, captions, date stamps or scene cuts.
Silent-era picture treatments retain supplied program audio with a restrained
transfer treatment. Sound-only recipes can be stacked with any picture look.

## Interaction and framing changes

- Search occupies a full row, followed by era and sort controls. The library
  shows a result count and an explicit Clear filters action.
- Every numeric effect setting and both master dials have keyboard-editable
  values. Enter or blur commits, Escape cancels, empty/invalid entries retain
  the last value, and bounds apply before an override reaches the engine.
- Numeric fields and sliders share precision and state; labels, units, reset
  buttons and focus rings make the controls usable without a pointer. Filter
  chips, variants, disclosures and the auto-preview switch are focusable.
- Mode-dependent settings explain why they are inactive: codec rate control,
  interlacing, tint strength, stock strength, local-contrast radius and matte
  settings. Expanding a card survives a parameter reset.
- Playback, preview settings, cache information and export controls reflow
  within the center pane at the minimum supported window size. The existing
  library/player/inspector arrangement remains intact.
- Every built-in framing preset and variant now inherits the source aspect.
  Explicit user overrides still work. Fit and crop preserve proportions in an
  aperture inside the existing output canvas; overscan operates in both modes.
- Probe and render paths honor phone rotation and non-square archival pixels.
  Direct encoding and intermediate paths normalize the resulting pixel aspect.
  Preview cache identity changes so old framing results are not reused.

## Verification performed

| Check | Result |
|---|---|
| Full catalog render smoke | **1,000 / 1,000 healthy**, 1.2-second clips, four workers |
| Preset and variant validation | **1,000 presets / 1,406 variants valid** |
| Calibration guardrails | **All 1,000 within vetted ranges** |
| New-recipe similarity | **211 checked; no near-clones** under the repository's same-effects / mean-distance threshold of 0.05 |
| Engine regression suite | **53 passed** |
| Renderer regression suite | **24 passed** |
| Control and source-geometry suite | **8 passed**, covering 115 effects / 699 declarations |
| Live Electron control harness | Numeric, enum, toggle, date and text edits; clamping, cancellation, reset, dependency changes, control bounds and decoded engine preview |
| Window review | **1120×700 and 1480×940**, preserving the three-pane layout |
| Visual review | All **201 picture recipes** on bright and dim source contact sheets; cartoon recipes also use animation sources |
| Sound-only review | All **10** rendered for six seconds; nonzero finite audio and spectrum inspection |
| Browse thumbnails | **211 generated, zero failed**; local manifest contains 1,000 entries |

The registry-wide control audit checks declared parameter consumption, coercion,
override routing and repeated-effect keys. Behavioral regression tests exercise
the changed controls and geometry branches. It is not an exhaustive perceptual
proof for every knob combination or every input: conditional controls need an
appropriate signal, some artifacts are temporal, and short smoke renders do not
substitute for reviewing a full-length export.

Thumbnails and review media are generated local assets excluded from Git. A
release build should generate/include the thumbnail pack through the existing
asset workflow. This change does not publish a release or replace the installed
application.

### Reproduce the automated checks

```bash
.venv/bin/python tests/test_engine.py
.venv/bin/python tests/test_controls.py
node tests/test_renderer.js
.venv/bin/python scripts/validate_presets.py
.venv/bin/python scripts/audit_calibration.py
.venv/bin/python scripts/audit_similarity.py --only-new
.venv/bin/python scripts/smoke_all_presets.py --jobs 4
app/node_modules/.bin/electron app --smoke
app/node_modules/.bin/electron app --shot /tmp/aesthetician-controls.png \
  --shot-file videos-samples/untreated.mp4 \
  --shot-js tests/renderer_controls_shot.js --shot-size 1120x700
```

### Design references

Historical color choices draw on the distinctions between applied tint/toning,
additive color and subtractive dye processes described by the
[BFI's film colour systems overview](https://www.bfi.org.uk/lists/10-best-film-colour-systems).
The recipes interpret those visual properties without claiming reconstruction
of a specific archival print.

Fine shadow texture and restrained highlight handling are informed by
[Kodak's VISION3 500T design description](https://www.kodak.com/en/motion/product/camera-films/500t-5219-7219).
Contemporary color, highlight and texture choices use
[ARRI's image-science overview](https://www.arri.com/en/learn-help/learn-help-camera-system/image-science)
as a design reference. The engine's SDR transforms do not reproduce the capture
latitude or proprietary processing of either system.
