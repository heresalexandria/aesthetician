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
       G, U, newLayer, newCue, cueOps, migrateCues, CUE_KEYS, isCaptionStyle, captionStyleIds,
       automaticUpdateCheck, liveLayers, layerSpec, isAudioOnly, passesFilters,
       searchTokens, eraTokens, expandQuery, searchScore, searchTier, sortPresets, SORT_OPTIONS,
       passesFacets, presetSubline, facetLabel })`,
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

function test_audio_filter_selects_sound_only_presets() {
  const audio = { id: 'audio-test', family: 'audio', era: '1985', video: [], audio: [['a_mono', {}]] };
  const soundOnly = { id: 'sound-only-test', family: 'custom', era: '1975', video: [], audio: [['a_mono', {}]] };
  const audiovisual = { id: 'av-test', family: 'film', era: '1985', video: [['grain', {}]], audio: [['a_mono', {}]] };
  assert.strictEqual(R.isAudioOnly(audio), true);
  assert.strictEqual(R.isAudioOnly(soundOnly), true, 'empty video chains count even outside the audio family');
  assert.strictEqual(R.isAudioOnly(audiovisual), false);

  R.G.audioOnly = true;
  R.G.favOnly = false;
  R.G.filterEra = '';
  R.G.filterFamilies.clear();
  assert.strictEqual(R.passesFilters(audio), true);
  assert.strictEqual(R.passesFilters(soundOnly), true);
  assert.strictEqual(R.passesFilters(audiovisual), false);
  R.G.audioOnly = false;
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

async function test_automatic_update_checks_only_when_due() {
  let networkChecks = 0;
  const saved = {
    ok: true,
    current: '1.3.0',
    latest: '1.4.0',
    available: true,
    installable: true,
  };
  sandbox.window.aesth.updateInfo = async () => ({
    version: '1.3.0',
    packaged: true,
    stale: false,
    last: saved,
    staged: { version: '1.4.0', tag: 'v1.4.0', verified: true },
  });
  sandbox.window.aesth.updateCheck = async () => {
    networkChecks++;
    return { ...saved, latest: '1.5.0' };
  };
  await R.automaticUpdateCheck();
  assert.strictEqual(networkChecks, 0, 'an hourly poll must reuse a fresh disk answer');
  assert.strictEqual(R.U.latest.latest, '1.4.0');
  assert.strictEqual(R.U.staged.version, '1.4.0');

  sandbox.window.aesth.updateInfo = async () => ({
    version: '1.3.0',
    packaged: true,
    stale: true,
    last: saved,
    staged: null,
  });
  await R.automaticUpdateCheck();
  assert.strictEqual(networkChecks, 1, 'a due poll must refresh GitHub');
  assert.strictEqual(R.U.latest.latest, '1.5.0');
  assert.strictEqual(R.U.staged, null, 'a missing staged file must stop looking installable');
}

/* ── finding presets ─────────────────────────────────────────────────
   The search mirrors aesthetician/taxonomy.py: every typed token must land
   somewhere (whole word or prefix), synonyms and decade words expand, and the
   engine's schema supplies the vocabulary. These run against the real library,
   so they double as a check that the vocabulary actually covers what people
   type. */
function hits(query, filter = () => true) {
  R.G.schema = S;   // the vocabulary rides on the schema
  const groups = R.expandQuery(query);
  return Object.values(S.presets)
    .filter(filter)
    .map((p) => [R.searchScore(p, groups), p])
    .filter(([s]) => s > 0)
    .sort((a, b) => (b[0] - a[0]) || a[1].id.localeCompare(b[1].id))
    .map(([, p]) => p.id);
}

function test_search_tokens_fold_phrases_and_decades() {
  R.G.schema = S;
  // Arrays cross the vm realm boundary with a foreign prototype: copy first.
  assert.deepStrictEqual(Array.from(R.searchTokens("Black & White 80's sci-fi")), ['bw', '80s', 'scifi']);
  assert.deepStrictEqual(Array.from(R.searchTokens('hong kong crime')), ['hong-kong', 'hong', 'kong', 'crime']);
  assert.deepStrictEqual(Array.from(R.eraTokens('1985')), ['1985', '1980s', '80s', 'eighties']);
  const raw = R.expandQuery('80s adventure');
  const groups = raw.map((g) => g.alts.map(([a]) => a));
  assert.ok(groups[0].includes('1980s') && groups[0].includes('eighties'), `decade did not expand: ${groups[0]}`);
  assert.ok(!groups[0].includes('1980'), 'a decade must not match the single year');
  assert.ok(raw[0].era && !raw[1].era, 'a decade is scored against the era only');
  assert.ok(groups[1].includes('adventure'));
  const noir = R.expandQuery('noir')[0].alts;
  assert.ok(noir[0][1] === 1 && noir.slice(1).every(([, f]) => f < 1), 'a synonym must be worth less than the typed word');
}

function test_every_typed_word_has_to_land() {
  const eightiesTv = hits('80s tv');
  assert.ok(eightiesTv.length > 0, 'a plain decade + medium query must find something');
  for (const id of eightiesTv) {
    const p = S.presets[id];
    assert.ok(String(p.era).startsWith('198') || /eighties|1980s|80s/.test(`${p.tags} ${p.keywords} ${p.desc}`.toLowerCase()),
      `${id} matched "80s tv" without being from the eighties`);
  }
  assert.ok(!hits('80s tv kaiju zebra').length, 'a token nothing has must return nothing');
  assert.ok(hits('adventur').includes('adventure-answer-print-1985'), 'a prefix still finds the word');
}

function test_synonyms_and_facets_find_the_artifact_names() {
  // The name says "Tokyo Spectacle Print"; a person types this.
  assert.ok(hits('kaiju').includes('tokyo-spectacle-1962'), 'kaiju must find the kaiju preset');
  assert.ok(hits('monster movie 60s').includes('tokyo-spectacle-1962'), 'synonym + phrase + decade');
  assert.ok(hits('80s adventure movie').includes('adventure-answer-print-1985'));
  const bw40s = hits('black and white 1940s');
  assert.ok(bw40s.length >= 5, `expected a shelf of 1940s B&W, got ${bw40s.length}`);
  for (const id of bw40s) {
    const p = S.presets[id];
    assert.ok(p.facets.color.includes('bw') || p.family === 'audio', `${id} is not black and white`);
  }
  assert.ok(hits('security camera').includes('security-vcr-1994'));
  assert.ok(hits('cassette', R.isAudioOnly).length >= 3, 'audio carriers are findable by format');
}

function test_search_answers_in_two_tiers() {
  R.G.schema = S;
  const tiers = (q) => {
    const g = R.expandQuery(q);
    const out = { direct: [], related: [] };
    for (const p of Object.values(S.presets)) { const t = R.searchTier(p, g); if (t) out[t].push(p.id); }
    return out;
  };
  const witch = tiers('witch');
  assert.ok(witch.direct.length >= 1 && witch.direct.length <= 5, `witch direct: ${witch.direct}`);
  assert.ok(witch.direct.includes('genre-found-footage-1999'));
  assert.ok(witch.related.length > witch.direct.length, 'the synonym reach lives in the related tier');
  const scifi = tiers('scifi');
  const audio = [...scifi.direct, ...scifi.related].filter((id) => R.isAudioOnly(S.presets[id]));
  assert.ok(audio.length <= 3, `scifi must not reach the sound-only shelf: ${audio}`);
  const spooky = tiers('spooky');
  assert.strictEqual(spooky.direct.length, 0);
  assert.ok(spooky.related.length > 0, 'a vague word still relates to something');
  // Mirror check: the engine and the app agree on the direct tier.
  const py = spawnSync(path.join(ROOT, '.venv', 'bin', 'python'), ['-c',
    'import json,aesthetician.presets\nfrom aesthetician.engine.presets import all_presets\nfrom aesthetician.taxonomy import search\nps=all_presets()\nprint(json.dumps({q:[p.id for _,p in search(ps.values(),q,"direct")] for q in ["witch","scifi","80s adventure","cassette"]}))'],
    { cwd: ROOT });
  if (py.status === 0) {
    const engine = JSON.parse(py.stdout.toString());
    for (const [q, ids] of Object.entries(engine)) {
      assert.deepStrictEqual(Array.from(tiers(q).direct).sort(), ids.sort(), `direct tier for ${q} differs from the engine`);
    }
  }
}

function test_sorting_the_library() {
  R.G.schema = S;
  const all = Object.values(S.presets);
  assert.deepStrictEqual(Array.from(R.SORT_OPTIONS.map((o) => o.id)), ['family', 'name', 'year', 'newest', 'oldest']);
  const byName = R.sortPresets(all, 'name');
  for (let i = 1; i < byName.length; i++) assert.ok(byName[i - 1].name.localeCompare(byName[i].name) <= 0, 'A to Z');
  const byYear = R.sortPresets(all, 'year');
  for (let i = 1; i < byYear.length; i++) assert.ok((parseInt(byYear[i - 1].era, 10) || 9999) <= (parseInt(byYear[i].era, 10) || 9999), 'year');
  const newest = R.sortPresets(all, 'newest');
  assert.ok(newest[0].introduced.date >= newest[newest.length - 1].introduced.date, 'newest first');
  assert.ok(newest.every((p) => p.introduced && p.introduced.date), 'every preset carries an introduction date');
  const oldest = R.sortPresets(all, 'oldest');
  assert.strictEqual(oldest[0].introduced.version, '0.3.0', `the oldest presets shipped in 0.3.0, got ${oldest[0].introduced.version}`);
  const byFamily = R.sortPresets(all, 'family');
  assert.strictEqual(byFamily.length, all.length);
  assert.strictEqual(byFamily[0].family, 'adjust', 'family order starts with the utility shelf');
  assert.strictEqual(byFamily[byFamily.length - 1].family, 'audio', 'and ends with the sound-only shelf');
}

function test_ranking_prefers_the_name_over_the_prose() {
  const ranked = hits('film noir');
  assert.strictEqual(ranked[0], 'noir-1947', `expected the noir preset first, got ${ranked.slice(0, 3)}`);
  // A decade word in a keyword list must not beat the era itself.
  const a = hits('80s adventure');
  const b = hits('eighties adventure');
  assert.deepStrictEqual(Array.from(a), Array.from(b), 'decade spellings must rank identically');
}

function test_facet_filters_are_real_and_exhaustive() {
  R.G.schema = S;
  const facetIds = S.taxonomy.facets.map((f) => f.id);
  assert.deepStrictEqual(facetIds, ['medium', 'genre', 'region', 'condition', 'color']);
  for (const p of Object.values(S.presets)) {
    for (const [fid, vals] of Object.entries(p.facets)) {
      const f = S.taxonomy.facets.find((x) => x.id === fid);
      assert.ok(f, `${p.id} carries an unknown facet ${fid}`);
      for (const v of vals) assert.ok(f.values.some((x) => x.id === v), `${p.id}: unknown ${fid} value ${v}`);
    }
    if (!R.isAudioOnly(p) && !['adjust', 'captions'].includes(p.family)) {
      assert.ok(p.facets.medium.length, `${p.id} has no medium facet`);
      assert.ok(p.facets.genre.length, `${p.id} has no genre facet`);
      assert.ok(p.facets.color.length, `${p.id} has no color facet`);
    }
  }
  R.G.filterFacets = { medium: 'videotape' };
  assert.strictEqual(R.passesFacets(S.presets['vhs-1985-sp']), true);
  assert.strictEqual(R.passesFacets(S.presets['noir-1947']), false);
  R.G.filterFacets = { color: 'bw', genre: 'crime' };
  assert.strictEqual(R.passesFacets(S.presets['noir-1947']), true);
  assert.strictEqual(R.passesFacets(S.presets['vhs-1985-sp']), false);
  R.G.filterFacets = {};
  assert.ok(R.presetSubline(S.presets['noir-1947']).startsWith('1947 · film · crime'), R.presetSubline(S.presets['noir-1947']));
  assert.strictEqual(R.facetLabel('genre', 'kaiju'), 'Kaiju and tokusatsu');
}

function test_collections_name_real_presets() {
  for (const c of S.collections) {
    assert.ok(c.id && c.title && c.blurb, `collection ${c.id} is incomplete`);
    for (const id of c.presets) assert.ok(S.presets[id], `collection ${c.id} names a missing preset ${id}`);
    for (const r of c.recipes) {
      assert.ok(r.layers.length >= 2, `recipe ${c.id}/${r.id} is not a stack`);
      for (const id of r.layers) assert.ok(S.presets[id], `recipe ${c.id}/${r.id} names a missing preset ${id}`);
    }
  }
}

const tests = [
  test_search_tokens_fold_phrases_and_decades,
  test_search_answers_in_two_tiers,
  test_sorting_the_library,
  test_every_typed_word_has_to_land,
  test_synonyms_and_facets_find_the_artifact_names,
  test_ranking_prefers_the_name_over_the_prose,
  test_facet_filters_are_real_and_exhaustive,
  test_collections_name_real_presets,
  test_the_grid_holds_every_authored_value,
  test_a_live_value_never_prints_as_the_minimum,
  test_committed_values_print_as_themselves,
  test_quantize_is_idempotent,
  test_audio_filter_selects_sound_only_presets,
  test_texture_hint_mirrors_the_engine,
  test_texture_hint_names_real_params,
  test_srt_timing_survives_the_paste,
  test_a_pasted_script_spreads_without_losing_words,
  test_every_cue_field_is_one_the_engine_reads,
  test_cues_become_the_engines_own_add_ops,
  test_a_legacy_caption_diff_replays_into_cues,
  test_automatic_update_checks_only_when_due,
  test_section_switches_ride_the_layer_spec,
];

/* The PICTURE / SOUND master switches live on the layer and go to the engine
   through layerSpec. Three promises hold them together: absence means on (so
   old sessions, saved stacks and every existing preview-cache key are
   untouched), off goes over the wire as an explicit false, and a layer with
   both sections muted is not rendered at all - the same contract the layer
   `enabled` checkbox has always had. */
function test_section_switches_ride_the_layer_spec() {
  const sess = { layers: [R.newLayer({ presetId: 'grindhouse-1973' })], activeLayer: 0 };
  const fresh = R.layerSpec(sess)[0];
  assert.ok(!('picture' in fresh) && !('sound' in fresh),
    'both sections on must serialize exactly as before the switches existed');

  sess.layers[0].picture = false;
  assert.deepStrictEqual(
    R.layerSpec(sess).map((l) => [l.picture, l.sound]), [[false, undefined]]);
  sess.layers[0].picture = true;
  sess.layers[0].sound = false;
  assert.strictEqual(R.layerSpec(sess)[0].sound, false);
  assert.ok(!('picture' in R.layerSpec(sess)[0]));

  // Layers from before the switches existed lack the keys entirely: on.
  const legacy = R.newLayer({ presetId: 'vhs-1985-sp' });
  delete legacy.picture;
  delete legacy.sound;
  sess.layers = [legacy];
  assert.strictEqual(R.liveLayers(sess).length, 1);
  assert.ok(!('picture' in R.layerSpec(sess)[0]) && !('sound' in R.layerSpec(sess)[0]));

  // Both muted = nothing to render, exactly like enabled: false.
  const muted = R.newLayer({ presetId: 'grindhouse-1973', picture: false, sound: false });
  sess.layers = [muted, R.newLayer({ presetId: 'vhs-1985-sp' })];
  assert.strictEqual(R.liveLayers(sess).length, 1);
  assert.strictEqual(R.layerSpec(sess).length, 1);
  assert.strictEqual(R.layerSpec(sess)[0].preset, 'vhs-1985-sp');
}

(async () => {
  let failed = 0;
  for (const t of tests) {
    try {
      await t();
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
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
