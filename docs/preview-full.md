# preview-full: the whole-clip seek surface

Main-process contract for `aesth:preview-full`, exposed to the renderer as
`window.aesth.previewFull(req)`. A window preview answers "how does it look";
seeking outside that window costs a re-render. After a window preview lands,
the renderer quietly asks for the entire clip at preview quality. Once that
file exists, any seek is just a seek inside it.

## Request

Same shape as `aesth:preview` minus `start` and `duration`:
`{ input, layers, presetId, variant, sets, seed, intensity, texture, scale,
audioSource, videoOnly, audioOnly, jobId? }`. The handler renders from 0 to
the end of the clip and pins `crf` at 21 (a seek surface, not a master).
`start`, `duration` and `crf` in the request are ignored before the cache key
is computed, so a careless caller can neither cache a partial file as "the
whole clip" nor fork the cache by quality.

## Response

- `{ output, cached: true }`: already on disk, usable immediately.
- `{ output, cached: false }`: freshly rendered, `.part` renamed into place.
- `{ superseded: true }`: killed by a newer `previewFull` or by an interactive
  preview. Not an error and not a rejection; do nothing, a newer answer is
  coming or the user has moved on.
- Real engine failures reject with the stderr tail, like `preview` does.

## Concurrency rules (load-bearing)

1. At most one full render in flight. A new `previewFull` request kills the
   old one; the old call resolves `{ superseded: true }`.
2. A full render never kills or delays interactive work: `previewProc` and
   `stillProc` are untouched by this endpoint.
3. An interactive `aesth:preview` render kills any in-flight full render (it
   was for a spec the user just left, and it was stealing cores). While the
   user is actively working, expect `{ superseded: true }` often.
4. Full renders emit no `aesth:progress` events. The progress bar belongs to
   renders the user is watching; this one is invisible by design.

## What the renderer must do

- Request: after the window preview resolves and paints, call `previewFull`
  with the same spec minus `start`, `duration` and `crf`. Do not fire it
  earlier or it will race rule 3 and lose. No debounce needed: rules 1 and 3
  make stale requests self-cleaning.
- Invalidate: any render-affecting change (file, layers, preset, variant,
  seed, intensity, texture, sets, scale, audio flags) makes a held full file
  stale. Drop the reference and re-request after the next window preview
  lands. Cache keys also include the app version and the input's mtime, so a
  re-request after an edit or update re-renders instead of lying.
- Use: on a seek to time T outside the current preview window, if the full
  file for the current spec is held, point the player at it and seek to T.
  The file starts at clip time 0, so no offset math; the window preview's
  `start` offset does not apply to it.
- On `{ superseded: true }`, do not retry in a loop: the next landed window
  preview is the natural trigger for the next request.
