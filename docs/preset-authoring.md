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
  (or read the effect source). NEVER guess a param name — validation will catch you.
- Repeated effect in one chain → second instance is addressed `eid#2`.

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

## proc_height (era vertical resolution — the image is simulated at this height)

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

## Tone of names/descriptions

Concrete nouns + period texture + a wink. Study these (existing library):
- "Six hours on a T-120: half the tape speed, twice the misery."
- "42nd-Street survivor: burned, spliced, scratched to ribbons…"
- "Camera 3, aisle 5: cool drained color, time-lapse stutter…"
Never generic ("old film look"). Every preset must have a distinct identity a
stranger could pick out of a lineup.

## Verification loop (MANDATORY per batch of ~10 presets)

1. `.venv/bin/python scripts/validate_presets.py` — must be ✓
2. `.venv/bin/python scripts/audit_calibration.py` — must be ✓ (or justify in report)
3. `.venv/bin/python scripts/smoke_all_presets.py --only id1,id2,… --jobs 4` — all OK
4. `.venv/bin/python scripts/make_gallery.py --family <fam> --input videos-samples/<pick>.mp4`
   then VIEW the sheet with the Read tool. Judge each cell: would it pass as real?
   Iterate params until yes. Cartoon presets test on classic-cartoon*.mp4;
   everything else on untreated*.mp4 (untreated4 = dim interior, untreated2/3 = bright).
5. Audio-led presets: render 6 s, generate `showspectrumpic` PNG, verify band
   edges/noise floors look like the era.
