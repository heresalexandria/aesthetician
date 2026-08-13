'use strict';

/* Unit tests for the renderer's number handling (run: node tests/test_renderer.js).
 *
 * A parameter row has to agree with itself in three places: where the slider
 * puts the thumb, what the readout prints, and what goes into the render
 * request. It stopped agreeing once, and the failure was silent and expensive.
 * A range input snaps its value onto `min + n*step`, and the step was a 200th
 * of the range - so `vhs.dropouts`, which runs 0 to 60 events/s, had a step of
 * 0.3. A preset authored at 0.4 put the thumb on 0.3, hard against the left
 * stop and indistinguishable from a parameter switched off, while the engine
 * went on rendering 0.4. Someone saved that as a custom aesthetic, read the
 * knob as zero, and got dropouts through the whole export.
 *
 * So this walks the real library and asserts the row cannot lie: every value a
 * preset authors survives the slider grid intact, and every value the grid can
 * produce prints as itself.
 *
 * app/renderer/app.js is browser code with no module system, so it is evaluated
 * whole in a stub context and picked apart. boot() is the only thing in there
 * that runs on its own, and it stalls on its first await against a promise that
 * never settles - so nothing past `await window.aesth.checkEnv()` executes and
 * there is no UI to tear down. If boot() ever grows synchronous work before
 * that await, this is where it will show up. */

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { spawnSync } = require('child_process');

const ROOT = path.join(__dirname, '..');

// ── loading the pieces under test ──────────────────────────────────────
/* Anything the DOM is asked for answers with itself, so a chain like
   $('x').classList.toggle(…) resolves without a real document behind it. */
const stub = new Proxy(function () {}, {
  get(_t, k) {
    if (k === 'textContent' || k === 'innerHTML' || k === 'value') return '';
    if (k === Symbol.toPrimitive || k === 'toString' || k === 'valueOf') return () => '';
    if (k === Symbol.iterator) return [][Symbol.iterator].bind([]);
    return stub;
  },
  set: () => true,
  apply: () => stub,
});

const never = () => new Promise(() => {});
const sandbox = {
  console,
  document: stub,
  localStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
  window: { aesth: { version: '0.0.0', packaged: false, checkEnv: never }, addEventListener: () => {} },
};
sandbox.window.document = sandbox.document;
sandbox.window.localStorage = sandbox.localStorage;

const SRC = fs.readFileSync(path.join(ROOT, 'app', 'renderer', 'app.js'), 'utf8');
const R = vm.runInNewContext(
  `${SRC}\n;({ sliderStep, quantize, fmtVal, valueDecimals, NOISE_HINT, splitScriptToCues, parseSrt,
       G, newLayer, newCue, cueOps, migrateCues, CUE_KEYS, isCaptionStyle, captionStyleIds })`,
  sandbox,
);

function schema() {
  const candidates = [process.env.AESTHETICIAN_PYTHON, path.join(ROOT, '.venv', 'bin', 'python'),
    'python3', 'python'].filter(Boolean);
  for (const py of candidates) {
    const r = spawnSync(py, ['-m', 'aesthetician.cli', 'schema'], { cwd: ROOT, maxBuffer: 64 << 20 });
    if (r.status === 0) return JSON.parse(r.stdout.toString());
  }
  throw new Error(`could not run the engine's schema command (tried ${candidates.join(', ')})`);
}

const S = schema();

/* What the browser does to `slider.value = v` for a given min/step. */
function snap(v, prm) {
  const step = R.sliderStep(prm);
  const n = Math.round((v - prm.lo) / step);
  return Math.min(prm.hi, Math.max(prm.lo, parseFloat((prm.lo + n * step).toFixed(9))));
}

/* What the engine actually resolves a written value to - Param.coerce clips to
   the parameter's own bounds, so a preset that authors past them is rendered at
   the bound, and that is the number the row has to agree with. */
function coerce(v, prm) {
  const c = Math.min(prm.hi, Math.max(prm.lo, v));
  return prm.kind === 'int' ? Math.round(c) : c;
}

/* Every (preset, effect key, param, effective value) the param pane can show. */
function* authoredValues() {
  for (const p of Object.values(S.presets)) {
    for (const chain of [p.video, p.audio]) {
      const counts = {};
      for (const [eid, params] of chain) {
        counts[eid] = (counts[eid] || 0) + 1;
        const key = counts[eid] === 1 ? eid : `${eid}#${counts[eid]}`;
        for (const prm of S.effects[eid].params) {
          if (prm.kind !== 'float' && prm.kind !== 'int') continue;
          const written = prm.name in params ? params[prm.name] : prm.default;
          yield { where: `${p.id} ${key}.${prm.name}`, prm, authored: coerce(written, prm) };
        }
      }
    }
  }
}

// ── tests ──────────────────────────────────────────────────────────────

/* The bug itself: the thumb must land on the number the engine was handed. */
function test_the_grid_holds_every_authored_value() {
  const bad = [];
  for (const { where, prm, authored } of authoredValues()) {
    const held = snap(authored, prm);
    if (R.fmtVal(held, prm) !== R.fmtVal(authored, prm)) {
      bad.push(`${where}: preset ${authored}, slider holds ${held}`);
    }
  }
  assert.deepStrictEqual(bad.slice(0, 12), [],
    `${bad.length} parameters whose slider misreports the preset value`);
}

/* A dial parked at the bottom of a 0-60 range is the one case the thumb cannot
   show, so the readout is what has to carry it - and it can only do that if it
   never rounds a live value to the same text as a dead one. */
function test_a_live_value_never_prints_as_the_minimum() {
  const bad = [];
  for (const { where, prm, authored } of authoredValues()) {
    if (authored <= prm.lo) continue;
    if (R.fmtVal(snap(authored, prm), prm) === R.fmtVal(prm.lo, prm)) {
      bad.push(`${where}: ${authored} prints as ${R.fmtVal(prm.lo, prm)}, same as off`);
    }
  }
  assert.deepStrictEqual(bad.slice(0, 12), [],
    `${bad.length} live parameters that print identically to their minimum`);
}

/* What a row stores is what a row printed: no 0.4025 hiding under "0.40". */
function test_committed_values_print_as_themselves() {
  const bad = [];
  for (const { where, prm } of authoredValues()) {
    const step = R.sliderStep(prm);
    // Walk the grid the way a drag does, plus both stops.
    for (const t of [0, 0.013, 0.5, 0.777, 1]) {
      const raw = Math.min(prm.hi, prm.lo + Math.round((prm.hi - prm.lo) * t / step) * step);
      const stored = R.quantize(raw, prm);
      if (snap(stored, prm) !== stored) bad.push(`${where}: stored ${stored} snaps to ${snap(stored, prm)}`);
      else if (R.fmtVal(stored, prm) !== R.fmtVal(raw, prm)) {
        bad.push(`${where}: printed ${R.fmtVal(raw, prm)}, stored ${stored}`);
      }
    }
  }
  assert.deepStrictEqual(bad.slice(0, 12), [], `${bad.length} values that do not print as themselves`);
}

function test_quantize_is_idempotent() {
  for (const { prm } of authoredValues()) {
    for (const v of [prm.lo, prm.hi, (prm.lo + prm.hi) / 3, 99.994, 100.6]) {
      const once = R.quantize(v, prm);
      assert.strictEqual(R.quantize(once, prm), once, `quantize drifts on ${prm.name} at ${v}`);
    }
  }
}

/* The tooltip claims which dials move a parameter. Keyed on the bare param name
   it told anyone hovering Saturation → Amount that Texture would move it, which
   it will not: engine/texture.py keys on the effect too. */
function test_texture_hint_mirrors_the_engine() {
  const src = fs.readFileSync(path.join(ROOT, 'aesthetician', 'engine', 'texture.py'), 'utf8');
  const body = src.slice(src.indexOf('NOISE_PARAMS'), src.indexOf('# Deliberately NOT here'));
  const engine = new Set([...body.matchAll(/\(\s*"([a-z0-9_]+)"\s*,\s*"([a-z0-9_]+)"\s*\)/g)]
    .map((m) => `${m[1]}.${m[2]}`));
  assert.ok(engine.size > 15, `only found ${engine.size} entries in texture.py - parser drifted`);
  assert.deepStrictEqual([...R.NOISE_HINT].sort(), [...engine].sort());
}

/* Every one of those parameters is real, so a rename in an effect cannot leave
   the hint quietly pointing at nothing. */
function test_texture_hint_names_real_params() {
  for (const hint of R.NOISE_HINT) {
    const [eid, pname] = hint.split('.');
    assert.ok(S.effects[eid], `texture hint names a missing effect: ${eid}`);
    assert.ok(S.effects[eid].params.some((p) => p.name === pname), `no such param: ${hint}`);
  }
}

/* Pasted .srt text keeps its own timing: indices and styling tags dropped,
   hours/minutes/seconds/millis added up, bodies kept whole. Anything that does
   not look like SRT is prose and belongs to the splitter instead. */
function test_srt_timing_survives_the_paste() {
  const srt = [
    '1', '00:00:01,500 --> 00:00:03,000', 'First line', 'and its second row', '',
    '2', '00:01:02,250 --> 00:01:04,000', '<i>Styled</i> words', '',
  ].join('\n');
  const cues = R.parseSrt(srt);
  assert.ok(cues && cues.length === 2, `expected 2 cues, got ${cues && cues.length}`);
  assert.strictEqual(cues[0].t, 1.5);
  assert.strictEqual(cues[0].text, 'First line\nand its second row');
  assert.ok(Math.abs(cues[0].dur_s - 1.5) < 0.06, `dur ${cues[0].dur_s}`);
  assert.strictEqual(cues[1].t, 62.25);
  assert.strictEqual(cues[1].text, 'Styled words');
  assert.strictEqual(R.parseSrt('just some prose, no timing anywhere'), null);
}

/* The splitter's contract: nothing dropped, nothing reordered, everything on
   the clip, cues never overlapping - so a pasted script is refined, not
   repaired. */
function test_a_pasted_script_spreads_without_losing_words() {
  const script = 'One short thought. A second, considerably longer sentence that will need '
    + 'to wrap or split somewhere sensible.\n\nA new paragraph starts its own caption. Tail.';
  const dur = 30;
  const cues = R.splitScriptToCues(script, dur, { lineChars: 24, maxLines: 2 });
  assert.ok(cues.length >= 3, `expected several cues, got ${cues.length}`);
  const rejoined = cues.map((c) => c.text).join(' ').replace(/\s+/g, ' ');
  const original = script.replace(/\s+/g, ' ');
  assert.strictEqual(rejoined, original, 'splitting dropped or reordered words');
  let last = 0;
  for (const c of cues) {
    assert.ok(c.t >= last - 1e-9, `cue at ${c.t} starts before the previous one ended (${last})`);
    assert.ok(c.dur_s >= 0.3, `cue shorter than the floor: ${c.dur_s}`);
    assert.ok(c.t + c.dur_s <= dur + 0.5, `cue overruns the clip: ${c.t} + ${c.dur_s}`);
    last = c.t + c.dur_s;
  }
  // strictEqual on length: the array was born in the vm realm, so deepStrictEqual
  // would fail it on prototype identity alone.
  assert.strictEqual(R.splitScriptToCues('   \n\n  ', dur).length, 0, 'whitespace makes no cues');
}

/* ── the caption track ───────────────────────────────────────────────
   Cues are content and the caption preset is a style, and the renderer keeps
   them apart precisely so a change of style cannot cost a script. These are
   the seams where that separation could quietly break: the moment cues are
   handed back to the engine, and the moment an old save is read in. */

/* Everything the app writes into a cue has to be something the engine's
   captions effect will act on - and the effect's `tune` branch is the honest
   list, because it names every editable field literally. A key added on one
   side and not the other is silent: the render simply ignores it. */
function test_every_cue_field_is_one_the_engine_reads() {
  const src = fs.readFileSync(
    path.join(ROOT, 'aesthetician', 'effects', 'video', 'captions.py'), 'utf8');
  const engine = new Set();
  for (const m of src.matchAll(/"([a-z_]+)" in d\b/g)) engine.add(m[1]);
  for (const m of src.matchAll(/for k in \(((?:\s*"[a-z_]+",?)+)\s*\):/g)) {
    for (const k of m[1].matchAll(/"([a-z_]+)"/g)) engine.add(k[1]);
  }
  assert.ok(engine.size > 5, `only found ${engine.size} tunable cue fields - parser drifted`);
  assert.deepStrictEqual([...R.CUE_KEYS].sort(), [...engine].sort());
}

/* A cue becomes exactly one `add` op, carrying every optional field explicitly:
   null is how a cue says "the style decides", and a missing key would read the
   same on the way out but not on the way back. Cues on a layer that is not
   wearing a caption style emit nothing - the words are kept, but there is
   nothing there to draw them. */
function test_cues_become_the_engines_own_add_ops() {
  R.G.schema = S;
  const l = R.newLayer({ presetId: 'cc-line21-1982' });
  l.cues = [R.newCue(1.5, { text: 'HELLO', dur_s: 2 }),
    R.newCue(4, { text: 'AGAIN', pos_y: 0.2, color: 'F2DE3C' })];
  const ops = R.cueOps(l);
  assert.strictEqual(ops.length, 2);
  for (const op of ops) {
    assert.strictEqual(op.op, 'add');
    assert.strictEqual(op.kind, 'caption');
    assert.strictEqual(op.effect, 'captions');
    assert.ok(op.id, 'every cue must name itself, so edits can find it again');
    assert.deepStrictEqual(Object.keys(op.detail).sort(), [...R.CUE_KEYS].sort());
  }
  assert.strictEqual(ops[0].detail.pos_y, null, 'unset must go over the wire as null');
  assert.strictEqual(ops[1].detail.pos_y, 0.2);
  assert.strictEqual(ops[1].detail.color, 'F2DE3C');

  const tape = R.newLayer({ presetId: 'vhs-1985-sp' });
  tape.cues = [R.newCue(1, { text: 'orphaned' })];
  assert.strictEqual(R.cueOps(tape).length, 0, 'only a caption style draws cues');

  assert.ok(R.isCaptionStyle('cc-line21-1982') && !R.isCaptionStyle('vhs-1985-sp'));
  assert.ok(R.captionStyleIds().length >= 10, 'the caption styles should all be pickable');
}

/* Saves made before cues had a list of their own carry them as a diff inside
   `events`. Reading only the adds back would silently undo every edit that had
   been made to them, so the whole little diff gets replayed - and the damage
   ops sharing that list are left strictly alone. */
function test_a_legacy_caption_diff_replays_into_cues() {
  R.G.schema = S;
  const l = R.migrateCues(R.newLayer({
    presetId: 'cc-line21-1982',
    events: [
      { op: 'add', id: 'a', kind: 'caption', t: 1, detail: { text: 'ONE', dur_s: 2 } },
      { op: 'add', id: 'b', kind: 'caption', t: 5, detail: { text: 'TWO', dur_s: 2 } },
      { op: 'add', id: 'c', kind: 'caption', t: 8, detail: { text: 'THREE', dur_s: 2 } },
      { op: 'tune', id: 'a', kind: 'caption', detail: { text: 'ONE EDITED', pos_y: 0.3 } },
      { op: 'move', id: 'b', kind: 'caption', t: 9 },
      { op: 'remove', id: 'c', kind: 'caption' },
      { op: 'tune', id: 'ghost', kind: 'caption', detail: { text: 'never existed' } },
      { op: 'add', id: 'vhs:dropout:3:0', kind: 'dropout', t: 2, detail: { row: 40 } },
    ],
  }));
  assert.strictEqual(l.cues.length, 2, 'the removed cue should be gone, the ghost ignored');
  assert.strictEqual(l.cues[0].text, 'ONE EDITED');
  assert.strictEqual(l.cues[0].pos_y, 0.3);
  assert.strictEqual(l.cues[0].id, 'a', 'ids travel with the cue, so pins keep their target');
  assert.strictEqual(l.cues[1].t, 9);
  assert.strictEqual(l.events.length, 1, 'damage edits are not captions and must survive');
  assert.strictEqual(l.events[0].kind, 'dropout');
  // A layer that never had captions is handed back untouched.
  const clean = R.newLayer({ presetId: 'vhs-1985-sp', events: [{ op: 'remove', id: 'x', kind: 'dropout' }] });
  assert.strictEqual(R.migrateCues(clean).cues.length, 0);
}

const tests = [
  test_the_grid_holds_every_authored_value,
  test_a_live_value_never_prints_as_the_minimum,
  test_committed_values_print_as_themselves,
  test_quantize_is_idempotent,
  test_texture_hint_mirrors_the_engine,
  test_texture_hint_names_real_params,
  test_srt_timing_survives_the_paste,
  test_a_pasted_script_spreads_without_losing_words,
  test_every_cue_field_is_one_the_engine_reads,
  test_cues_become_the_engines_own_add_ops,
  test_a_legacy_caption_diff_replays_into_cues,
];

let failed = 0;
for (const t of tests) {
  try {
    t();
    console.log(`  ok ${t.name}`);
  } catch (err) {
    failed++;
    console.error(`  FAIL ${t.name}: ${err.message}`);
  }
}
if (failed) {
  console.error(`${failed} renderer test${failed === 1 ? '' : 's'} failed`);
  process.exit(1);
}
console.log(`${tests.length} renderer tests passed`);
