# Discrete events: the plan, the timeline and the diff

Damage in this engine comes in two shapes. Continuous damage is a level: tape
noise, grain, a rolling tracking band. Discrete damage is a series of incidents:
a dropout is a streak on one row of one frame, a transport glitch is a shredded
stretch of two thirds of a second. This page is about the incidents - how they
are planned, how the timeline reads them, and how an edit rides a render.

## The plan

Effects that deal in incidents work out their whole schedule in `prepare`, from
the same per-frame generators the render always used, and hand it over through
`Effect.events(ctx)` as `Event(t, dur, kind, detail)`. Two facts make the plan
trustworthy:

- `t` is seconds on the **clip's** timeline (`Context.t0` positions the render
  window on the clip), so a preview and an export agree about where everything
  is.
- The plan is the render. `plan_events()` resolves and prepares the same chain
  the render would run, so the list it returns is not an estimate; the test
  suite renders with and without dropouts and asserts the differing frames are
  exactly the planned ones.

```bash
.venv/bin/python -m aesthetician.cli events clip.mp4 -p vhs-rental-1992 --seed 4242
```

```json
{"t0": 0.0, "duration": 9.68, "fps": 30.0, "n_frames": 290, "events": [
  {"effect": "vhs", "kind": "dropout", "t": 0.73, "dur": 0.033, "layer": 0,
   "detail": {"id": "vhs:dropout:22:0", "row": 139, "x": 225,
              "length_px": 15, "rows": 1, "polarity": "bright"}}
]}
```

Costs a chain `prepare`, never a render. Stacks are planned layer by layer with
the geometry each layer hands the next, and every event carries its layer index.

Effects with events so far: `vhs` (dropout), `vcr_transport` (transport_glitch,
transport_lock). Continuous effects return nothing from `events()` on purpose -
they are a curve, not a list of moments, and pretending otherwise would put pins
on the timeline that mean nothing.

## Ids, and why they are minted early

Every instance gets its id when the **base** schedule is drawn -
`vhs:dropout:<absolute frame>:<index within frame>` - and the id travels with
the instance through any edits. Minting on the base schedule is what keeps one
edit from renumbering everything after it: remove the second dropout and the
third keeps its name.

## The diff

An edit list rides each layer of the layer spec as `events`:

```json
{"preset": "vhs-rental-1992", "seed": 4242, "sets": {}, "events": [
  {"op": "remove", "id": "vhs:dropout:22:0"},
  {"op": "move",   "id": "vhs:dropout:67:1", "t": 4.10},
  {"op": "tune",   "id": "vhs:dropout:80:0", "detail": {"length_px": 200, "polarity": "dark"}},
  {"op": "add",    "kind": "dropout", "t": 6.50,
   "detail": {"row": 120, "x": 40, "length_px": 160, "rows": 2}}
]}
```

Rules, all load-bearing:

- Ops name their target by id. An op whose id the current seed no longer
  produces is **skipped, never guessed at** - editing a different dropout than
  the one you meant would be worse than editing none.
- **Adds are yours; the rest are the tape's.** An added event is anchored to
  absolute clip time and any unspecified detail is derived from the op itself,
  so it survives a reseed. Remove, move and tune are edits *of that seed's
  schedule* and die with the seed.
- The render, the still and the plan all honor the same diff, so what the
  timeline claims after an edit is what the export does.
- An empty or absent `events` list changes nothing, byte for byte.

`vcr_transport` applies the diff between drawing its glitch list and rasterising
its envelope, so a moved glitch leaves no shadow of itself in the curve the
frames actually read.

## Backward compatibility

`events` on a layer is additive with an empty default, like every parameter
change in this project: specs in the wild that predate it render exactly as
they always did.
