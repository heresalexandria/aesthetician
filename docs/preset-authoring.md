# Preset Authoring Guide

How to write Aesthetician presets that pass review. Read fully before writing any.

## Anatomy

```python
register_preset(Preset(
    id="kebab-era-year", name="Human Name", family="...", era="1972",
    desc="One evocative, CONCRETE sentence: name the physical artifacts and the feeling.",
    tags=("...",), proc_height=560, upscale="soft",
    video=[(effect_id, {param: value}), ...],   # signal order! see below
    audio=[...],
    variants=[Variant("vid", "Name", "desc", video={"effect.param": v}, audio={...})],
))
```

- Get the full effect/param registry: `.venv/bin/aesthetician effects --json | python3 -m json.tool`
  (or read the effect source). NEVER guess a param name - validation will catch you.
- Repeated effect in one chain → second instance is addressed `eid#2`.
- `keywords=(...)`: 6-12 lower-case words or hyphenated phrases that a person types when
  they want this look and the name does not say ("kaiju", "giant-monster", "godzilla" for a
  preset named after its print). Genre and mood first, then format aliases, then at most two
  canonical touchstones. Words already in the name, tagline or tags are harmless but add
  nothing; spend the slots on what those fields leave out. They are searched, never
  displayed. See `docs/finding-presets.md`.
- Facets (medium, genre, region, condition, color) are derived, not authored: from the effects
  in the chain and from the vocabulary in `aesthetician/taxonomy.py` matched against id, name,
  tags, keywords and tagline. `validate_presets.py` refuses a picture preset that lands in no
  medium or no genre; fix that by adding the right word to `keywords`, or, if the vocabulary is
  missing a term, by adding the term to the taxonomy (once, for everyone).
- Families `genre` and `channel` exist to be found by era and kind ("Sixties Kaiju Feature",
  "Music-Video Channel, Launch Era"), so their names may lead with the era and genre; the
  tagline and desc still name the physical artifact. Everywhere else, names describe the thing.

## Chain order (the physical signal path)

**Video:** look (stock/tone/balance/saturation/mono) → lens (optics, exposure_auto)
→ medium (grain/halation/weave/flicker/damage OR cel stack OR none for video eras)
→ decay (chemical.py effects, fade) → transfer (cadence → ntsc/vhs → codec passes)
→ display (interlace → crt / lcd / rf / transmission) → scan (scan.py, for
"digitized archive" framings) → presentation (framing, plates, timestamp/osd,
exhibition.py effects, projection).

**Audio:** source tone (a_bandlimit/a_mono) → medium (tape/vinyl/optical/wire)
→ transmission (radio/phone/codec) → device (a_speaker) → room (a_room/a_slap)
→ beds last (a_projector, a_bed, a_hum).

### Real digital codec controls

`codec_era` uses the actual ffmpeg encoders. MPEG-1/2/4, H.264, FLV, H.263 and MJPEG
use `kbps`, or their period-style `qscale` when it is above zero. H.264 uses
libx264 and has two deliberately exclusive rate-control modes: `crf=-1` uses
`kbps`; `crf=0..51` uses constant quality and ignores `kbps` (0 is lossless,
18 is visually transparent, 23 is a common delivery value). Do not use
`qscale` for H.264 because its quantizer has different semantics.

For contemporary camera, mobile and streaming sound, `a_codec_aac` performs a
real native AAC-LC round trip. `kbps` is the total stream bitrate, and `mono`
controls the encoded channel count. Keep MP3 on period web/Flash chains where
MP3 is the historically correct carrier.

The `captions` effect belongs to the presentation stage: text is drawn onto
whatever the chain has already made of the picture. The captions *family*
keeps deliberately pure single-effect chains with no `proc_height`, so the
lettering rasterizes at delivery resolution and only degrades when the user
stacks a look over it - which is the intended way to age a caption. Cue text
and timing are not preset material at all; they arrive as event edits
(docs/events.md), so a captions preset is finished when its typography is.

Author them as interchangeable: the app treats the words as a track and the
preset as a coat of paint on it, so every one of these has to make sense drawn
over somebody else's script. That means no assumptions about length, and a
`pos_y` that reads as a considered spot rather than a default.

## proc_height (era vertical resolution - the image is simulated at this height)

35mm/scope: none (native) · 16mm: 600–640 · 8mm/Super8: 500–560 · VHS SP: 540–560
· VHS EP / U-matic worn: 480–520 · broadcast video: 520–600 · early web/handheld
digital: none (codec_era's res ladder handles it) · pixel eras: none (pixel_era handles).

## Calibration guardrails (scripts/audit_calibration.py enforces; violations need justification)

| param | vetted range | why |
|---|---|---|
| grain.amount | ≤ 0.65 | upscales louder than you think |
| grain.chroma_grain | ≤ 0.28 | above = rainbow confetti |
| vhs.luma_noise / chroma_noise | ≤ 0.7 / 0.6 (SP); ≤ 0.32 for EP, 0.45 LP | modes multiply internally ~2.6×/1.7× |
| ntsc.phase_noise | 1–4 typical (degrees) | >6 = broken set |
| cel_dirt.visibility | ≤ 0.14 | must read subliminally |
| paper_texture.amount | ≤ 0.07 | above reads as canvas |
| crt.scan_strength | ≤ 0.45; 0.1–0.2 typical | hard lines read as shader |
| flicker.amount | ≤ 0.6; 0.1–0.3 typical | above = strobe |
| halation.strength | ≤ 0.6 | |

Audio: `*_db` params are dBFS (hiss −55…−36 typical; beds −34…−24). a_tape_sat.drive
1..8 (1 = clean). a_wow_flutter depths are cents (3–10 subtle, 10–25 seasick).

### Grain size is measured BEFORE the final upscale

`grain.size` is in *processing* pixels. A preset with `proc_height=520` delivering
1280 lines magnifies its grain 2.46×, so `size=2.9` lands as ~7 px clumps - blobby,
not filmic. Keep the **effective** size (`size × out_h / proc_height`) at or under:

- **≤ 5.0 px** for small gauge (8 mm / Super 8 / 9.5 mm, `proc_height ≤ 560`)
- **≤ 4.2 px** for 16 mm and broadcast-res film (`proc_height` 600–640)
- no limit at native resolution (35 mm) - there is no upscale to magnify it

So at `proc_height=520` targeting 1280, `size` should be ≈2.0, not 2.9. Alternatively
set `grain.size_ref="output"` and specify the delivered clump size directly - but note
that processing-referred sizing keeps grain a constant *fraction of the frame*, which
is what makes half-resolution GUI previews match the full export.

Every noise *amount* in your chain is also scaled by the user's master `--texture`
knob (see `engine/texture.py` for the registry) - author at texture 1.0.

## Tone of names/descriptions

Concrete nouns + period texture + a wink. Study these (existing library):
- "Six hours on a T-120: half the tape speed, twice the misery."
- "42nd-Street survivor: burned, spliced, scratched to ribbons…"
- "Camera 3, aisle 5: cool drained color, time-lapse stutter…"
Never generic ("old film look"). Every preset must have a distinct identity a
stranger could pick out of a lineup.

## Verification loop (MANDATORY per batch of ~10 presets)

1. `.venv/bin/python scripts/validate_presets.py` - must be ✓
2. `.venv/bin/python scripts/audit_calibration.py` - must be ✓ (or justify in report)
3. `.venv/bin/python scripts/smoke_all_presets.py --only id1,id2,… --jobs 4` - all OK
4. `.venv/bin/python scripts/make_gallery.py --family <fam> --input videos-samples/<pick>.mp4`
   then VIEW the sheet with the Read tool. Judge each cell: would it pass as real?
   Iterate params until yes. Cartoon presets test on classic-cartoon*.mp4;
   everything else on untreated*.mp4 (untreated4 = dim interior, untreated2/3 = bright).
5. Audio-led presets: render 6 s, generate `showspectrumpic` PNG, verify band
   edges/noise floors look like the era.
6. `.venv/bin/python scripts/audit_similarity.py --only-new` - every new preset's nearest
   neighbour, and a non-zero exit for near-clones (same effect list, authored parameters
   within 5% of each other). A clone is not a new look; commit harder to one identity or
   drop it.
