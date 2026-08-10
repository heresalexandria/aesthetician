'use strict';

/* Aesthetician renderer - schema-driven UI, no framework. */

const $ = (id) => document.getElementById(id);

/* App-wide state. Per-video state lives in G.sessions; `state` always points at
   the active session, so every existing state.* reference keeps working. */
const G = {
  schema: null,
  thumbs: {},          // presetId -> {poster, anim|null}
  collapsed: new Set(),
  sessions: [],
  activeId: null,
  seq: 0,
  jobCounter: 0,
  layerSeq: 0,
  activeJob: null,
  exports: [],         // every export started this session, newest last
  batchId: 0,          // groups exports queued together, for the aggregate bar
  navOrder: [],        // preset ids in visible list order, for ↑/↓ navigation
  duration: 3.0,       // preview length
  scale: 0.5,          // preview scale
  autoPreview: true,
  muted: true,
  paused: false,       // the preview loop is held still
  favs: new Set(),     // favorited preset ids (persisted)
  customs: [],         // saved custom aesthetics (persisted), newest last
  customSeq: 0,
  stacks: [],          // saved layer stacks (persisted), newest last
  stackSeq: 0,
  filterFamilies: new Set(),  // family chips currently selected (empty = all)
  filterEra: '',       // decade string like "1980s" (empty = any)
  favOnly: false,      // the ★ chip: show favorites only
  customOnly: false,   // the ✎ chip: show saved customs only
  stackOnly: false,    // the ▤ chip: show saved stacks only
};

/* Update state. Declared up here with G rather than beside the update code:
   boot() runs while the script is still being parsed, and it paints the version
   chip first, so a `const` further down the file is still in its dead zone. */
const U = {
  info: null,        // { version, packaged, platform, arch, ... }
  latest: null,      // the last check result
  busy: '',          // '', 'checking', 'downloading', 'installing'
  staged: null,      // { version, tag } once a verified download is on disk
  picker: false,     // the "other versions" panel is unfolded
  releases: null,    // the whole release list, once it has been asked for
  releasesBusy: false,
  pickTag: '',       // which release the picker has selected
};

/* ── small persistence layer (localStorage) ─────────────────────────
   Favorites, collapsed families and the preview knobs survive restarts.
   Everything degrades to defaults if storage is unavailable or stale. */
const STORE_KEY = 'aesthetician.ui.v1';

function loadStore() {
  try {
    const s = JSON.parse(localStorage.getItem(STORE_KEY) || '{}');
    if (Array.isArray(s.favs)) G.favs = new Set(s.favs);
    if (Array.isArray(s.collapsed)) G.collapsed = new Set(s.collapsed);
    if (typeof s.duration === 'number' && s.duration >= 1 && s.duration <= 10) G.duration = s.duration;
    if (typeof s.scale === 'number' && s.scale >= 0.2 && s.scale <= 1) G.scale = s.scale;
    if (typeof s.autoPreview === 'boolean') G.autoPreview = s.autoPreview;
    if (typeof s.muted === 'boolean') G.muted = s.muted;
    if (typeof s.paused === 'boolean') G.paused = s.paused;
    if (Array.isArray(s.customs)) {
      // Drop anything whose base preset has since disappeared, so a stale save
      // cannot wedge the list.
      G.customs = s.customs.filter((c) => c && c.id && c.base && c.name);
      G.customSeq = G.customs.reduce((n, c) => Math.max(n, parseInt(c.id.slice(7), 10) || 0), 0);
    }
    if (Array.isArray(s.stacks)) {
      // Same rule as customs: a save with no layers left standing cannot wedge
      // the list. Individual layers are vetted at apply time, when we know which
      // base presets this build actually has.
      G.stacks = s.stacks.filter((k) => k && k.id && k.name && Array.isArray(k.layers) && k.layers.length);
      G.stackSeq = G.stacks.reduce((n, k) => Math.max(n, parseInt(k.id.slice(6), 10) || 0), 0);
    }
  } catch (_) { /* first run, or corrupted store: defaults are fine */ }
}

function saveStore() {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify({
      favs: [...G.favs],
      collapsed: [...G.collapsed],
      duration: G.duration,
      scale: G.scale,
      autoPreview: G.autoPreview,
      muted: G.muted,
      paused: G.paused,
      customs: G.customs,
      stacks: G.stacks,
    }));
  } catch (_) { /* storage full or unavailable: cosmetic only */ }
}

/* ── layers ──────────────────────────────────────────────────────────
   A session is a stack of layers rendered bottom to top, each one treating what
   the one below actually produced. One layer is the overwhelmingly common case
   and behaves exactly as it always did.

   The per-layer fields are reachable as `state.presetId`, `state.seed` and so
   on: they are accessors onto whichever layer is selected. That is deliberate -
   every existing call site (rendering knobs, saving a custom, naming an export)
   keeps working untouched, and only the code that genuinely cares about the
   stack has to know it exists. */
function newLayer(overrides = {}) {
  return {
    lid: `L${++G.layerSeq}`,
    presetId: null,
    customId: null,      // set when the pick came from a saved custom aesthetic
    variant: null,
    sets: {},
    events: [],          // the user's diff on the seeded event schedule
    seed: 1 + Math.floor(Math.random() * 99999),
    intensity: 1.0,
    texture: 1.0,
    enabled: true,
    ...overrides,
  };
}

const LAYER_FIELDS = ['presetId', 'customId', 'variant', 'sets', 'events', 'seed', 'intensity', 'texture'];

function newSession(info) {
  const sess = {
    id: `s${++G.seq}`,
    file: info,
    audioSource: info.has_video === false,  // a WAV/MP3/stem: no picture to treat
    layers: [newLayer()],
    activeLayer: 0,
    // Which saved stack this whole session is wearing, if any. It lives on the
    // session rather than a layer because a stack *is* the arrangement - the one
    // thing no single layer can describe.
    stackId: null,
    previewT: Math.max((info.duration - G.duration) / 2, 0),
    treatedSrc: null,
    originalSrc: null,
    originalT: null,
    // Filmstrip timeline state. The strip is a property of the file alone, so
    // it is fetched once per session; the event plan depends on every render
    // knob, so it is cached by the exact layer spec that asked for it.
    strip: null,         // {frames, duration} from aesth:filmstrip
    stripJob: null,      // the in-flight fetch, so racing callers share one
    eventsKey: null,     // JSON.stringify(layerSpec) the cached plan answers
    eventsPlan: null,    // the aesth:events result for eventsKey
    eventsJob: null,     // the key being planned right now, to dedupe requests
    // The most recent preview this tab asked for. Results are recorded per tab
    // rather than per screen, so this is what keeps an older render that lands
    // late from overwriting a newer one behind the user's back.
    previewJob: null,
  };
  for (const key of LAYER_FIELDS) {
    Object.defineProperty(sess, key, {
      get() { return (this.layers[this.activeLayer] || this.layers[0])[key]; },
      set(v) { (this.layers[this.activeLayer] || this.layers[0])[key] = v; },
      enumerable: true,
      configurable: true,
    });
  }
  return sess;
}

/* Layers actually worth rendering, bottom first. */
function liveLayers(sess) {
  return (sess.layers || []).filter((l) => l.enabled && l.presetId);
}

function activeLayer(sess = state) {
  return sess.layers[sess.activeLayer] || sess.layers[0];
}

/* The active session, or a blank stand-in before the first video is loaded so
   early reads never explode. */
let state = newSession({ path: '', duration: 0, width: 0, height: 0 });
G.sessions = [];

const videoA = $('video-a'); // treated
const videoB = $('video-b'); // original

// ── boot ────────────────────────────────────────────────────────────
(async function boot() {
  loadStore();
  // Synchronously, before the first await and before the first paint: the
  // preload picks the version off our own argv, so there is no round trip to
  // wait on and no placeholder to flash. Painting it last used to leave the chip
  // empty for the ~2 s that checkEnv and schema spend spawning Python.
  setVersionChip();
  const env = await window.aesth.checkEnv();
  if (!env.ok) {
    const w = $('env-warning');
    w.classList.remove('hidden');
    w.textContent = env.problems.join('\n\n');
  }
  try {
    G.thumbs = (await window.aesth.thumbs()).thumbs || {};
  } catch (_) {
    G.thumbs = {}; // thumbs are optional: rows fall back to a placeholder
  }
  try {
    G.schema = await window.aesth.schema();
    buildFilterBar();
    buildPresetList();
  } catch (err) {
    const w = $('env-warning');
    w.classList.remove('hidden');
    w.textContent = 'Could not load the engine schema:\n' + err.message;
  }
  window.aesth.onProgress(onProgress);
  wireDrop();
  wireControls();
  wireShortcuts();
  wireUpdates();
  renderTabs();
  refreshCacheInfo();
  if (G.schema) console.log('aesth:renderer-ready');
  // Off the critical path: the window is usable before GitHub answers.
  initUpdates();
})();

// ── drag & drop ─────────────────────────────────────────────────────
function wireDrop() {
  const zone = document.body;
  const inner = $('drop-zone');
  ['dragover', 'dragenter'].forEach((ev) =>
    zone.addEventListener(ev, (e) => { e.preventDefault(); inner.classList.add('armed'); }));
  ['dragleave', 'drop'].forEach((ev) =>
    zone.addEventListener(ev, (e) => { e.preventDefault(); if (ev === 'dragleave' && e.target !== zone) return; inner.classList.remove('armed'); }));
  zone.addEventListener('drop', async (e) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (!f) return;
    const p = window.aesth.pathForFile(f);
    await loadFile(p);
  });
  $('btn-browse').addEventListener('click', browseForFile);
}

async function browseForFile() {
  const p = await window.aesth.pickInput();
  if (p) await loadFile(p);
}

async function loadFile(p) {
  try {
    const info = await window.aesth.probe(p);
    const sess = newSession(info);
    G.sessions.push(sess);
    activateSession(sess.id);
  } catch (err) {
    alert('Could not read that file:\n' + err.message);
  }
}

// ── sessions (one open video each) ───────────────────────────────────
function activeSession() {
  return G.sessions.find((s) => s.id === G.activeId) || null;
}

function activateSession(id) {
  const sess = G.sessions.find((s) => s.id === id);
  if (!sess) return;
  G.activeId = id;
  state = sess;
  G.activeJob = null;              // any in-flight preview belongs to the old tab

  $('drop-screen').classList.add('hidden');
  $('workspace').classList.remove('hidden');
  $('file-chip-text').textContent = sess.audioSource
    ? `${basename(sess.file.path)} · audio · ${(sess.file.sr / 1000).toFixed(1)} kHz ${sess.file.channels === 1 ? 'mono' : 'stereo'} · ${sess.file.duration.toFixed(1)}s`
    : `${basename(sess.file.path)} · ${sess.file.width}×${sess.file.height} · ${sess.file.duration.toFixed(1)}s`;
  $('file-chip').title = `${sess.file.path}\nClick to show it in the Finder`;
  $('file-chip').classList.remove('hidden');

  const scrub = $('scrub');
  scrub.max = Math.max(sess.file.duration - G.duration, 0).toFixed(1);
  scrub.value = sess.previewT.toFixed(1);
  paintRange(scrub);
  $('scrub-label').textContent = `preview at ${sess.previewT.toFixed(1)}s`;
  $('seed').value = sess.seed;
  $('intensity').value = sess.intensity;
  $('intensity-val').textContent = sess.intensity.toFixed(2);
  paintRange($('intensity'));
  $('texture').value = sess.texture;
  $('texture-val').textContent = sess.texture.toFixed(2);
  paintRange($('texture'));

  // Splitting picture from sound is meaningless when there is no picture.
  $('exp-video-only').closest('label').classList.toggle('hidden', sess.audioSource);
  $('exp-audio-only').closest('label').classList.toggle('hidden', sess.audioSource);
  if (sess.audioSource) { $('exp-video-only').checked = false; $('exp-audio-only').checked = false; }
  document.body.classList.toggle('audio-session', sess.audioSource);
  $('btn-export').textContent = sess.audioSource ? 'Export Full Audio' : 'Export Full Video';

  renderTabs();
  buildFilterBar();   // chip order follows famRank, which flips for audio sources
  buildPresetList();
  buildLayersPanel();
  buildParamPane();

  // Restore this tab's already-rendered preview if it has one; the files live in
  // the preview cache, so switching back is instant and costs no re-render.
  hideStill();   // any stand-in on screen belongs to the tab being left
  if (sess.treatedSrc && sess.originalSrc) {
    $('player-empty').classList.add('hidden');
    setVideo(videoA, sess.treatedSrc);
    setVideo(videoB, sess.originalSrc);
  } else {
    videoA.removeAttribute('src'); videoB.removeAttribute('src');
    videoA.load(); videoB.load();
    $('player-empty').classList.remove('hidden');
    $('player-empty').textContent = sess.presetId
      ? 'Rendering this clip…'
      : (sess.audioSource ? 'Pick an aesthetic to hear it applied' : 'Pick an aesthetic to render a preview');
    if (sess.presetId) schedulePreview(true);
  }
  // The timeline belongs to the tab: repaint its cached strip and plan, and
  // fetch whichever of the two this session never loaded. Not awaited, because
  // switching tabs has to stay instant.
  refreshTimeline();
  setExportStatus('Ready.');
}

function closeSession(id) {
  const i = G.sessions.findIndex((s) => s.id === id);
  if (i < 0) return;
  G.sessions.splice(i, 1);
  if (G.activeId !== id) { renderTabs(); return; }
  const next = G.sessions[i] || G.sessions[i - 1];
  if (next) {
    activateSession(next.id);
  } else {
    // last tab closed → back to the drop screen
    G.activeId = null;
    state = newSession({ path: '', duration: 0, width: 0, height: 0 });
    G.sessions = [];
    videoA.removeAttribute('src'); videoB.removeAttribute('src');
    videoA.load(); videoB.load();
    $('workspace').classList.add('hidden');
    $('drop-screen').classList.remove('hidden');
    $('file-chip').classList.add('hidden');
    renderTabs();
  }
}

/* Show the drop screen without discarding open tabs. */
function showNewSessionScreen() {
  G.activeId = null;
  $('workspace').classList.add('hidden');
  $('drop-screen').classList.remove('hidden');
  $('file-chip').classList.add('hidden');
  renderTabs();
}

/* The titlebar chip is a button: it shows the clip you are working on where it
   actually lives. A session can outlive its file - renamed, moved, on a volume
   that has since been ejected - so say so rather than opening nothing. */
async function revealFile(path) {
  const res = await window.aesth.reveal(path);
  if (res && res.ok) return true;
  setExportStatus(`${basename(path)} is no longer at ${path} - `
    + 'it looks like it was moved, renamed or deleted.', true);
  return false;
}

function revealSourceFile() {
  const sess = activeSession();
  if (!sess || !sess.file || !sess.file.path) return;
  revealFile(sess.file.path);
}

function basename(p) {
  return (p || '').split(/[\\/]/).pop();
}

function renderTabs() {
  const bar = $('tab-bar');
  bar.innerHTML = '';
  bar.classList.toggle('hidden', G.sessions.length === 0);
  document.body.classList.toggle('has-tabs', G.sessions.length > 0);
  const cancel = $('btn-drop-cancel');
  cancel.classList.toggle('hidden', !(G.sessions.length && G.activeId === null));
  for (const sess of G.sessions) {
    const tab = document.createElement('div');
    tab.className = 'tab' + (sess.id === G.activeId ? ' active' : '');
    const wearing = wearingName(sess);
    tab.title = `${sess.file.path}\n${wearing || 'no aesthetic yet'}`;

    const name = document.createElement('span');
    name.className = 't-name';
    name.textContent = (sess.audioSource ? '♪ ' : '') + basename(sess.file.path);
    tab.appendChild(name);

    if (wearing) {
      const kind = sess.stackId ? 'stack' : (sess.customId ? 'custom' : '');
      const badge = document.createElement('span');
      badge.className = 't-preset' + (kind ? ` ${kind}` : '');
      badge.textContent = (sess.stackId ? '▤ ' : (sess.customId ? '✎ ' : '')) + wearing;
      tab.appendChild(badge);
    }

    const x = document.createElement('button');
    x.className = 't-close';
    x.textContent = '×';
    x.title = 'Close this video';
    x.onclick = (e) => { e.stopPropagation(); closeSession(sess.id); };
    tab.appendChild(x);

    tab.onclick = () => { if (sess.id !== G.activeId) activateSession(sess.id); };
    bar.appendChild(tab);
  }
  const add = document.createElement('button');
  add.className = 'tab-add' + (G.activeId === null && G.sessions.length ? ' armed' : '');
  add.textContent = '+';
  add.title = 'Open another video';
  add.onclick = showNewSessionScreen;
  bar.appendChild(add);
}

function presetName(pid) {
  return (G.schema && G.schema.presets[pid] && G.schema.presets[pid].name) || pid;
}

// ── preview cache ───────────────────────────────────────────────────
function fmtBytes(n) {
  if (!n) return '0 B';
  const u = ['B', 'KB', 'MB', 'GB'];
  const i = Math.min(Math.floor(Math.log(n) / Math.log(1024)), u.length - 1);
  return `${(n / 1024 ** i).toFixed(i ? 1 : 0)} ${u[i]}`;
}

async function refreshCacheInfo() {
  try {
    const info = await window.aesth.cacheInfo();
    G.cacheDir = info.dir;
    $('cache-size').textContent = `${fmtBytes(info.bytes)} · ${info.count} preview${info.count === 1 ? '' : 's'}`;
    $('cache-row').title = `Preview cache: ${info.dir}`;
  } catch (_) {
    $('cache-size').textContent = 'unavailable';
  }
}

// ── hover tooltips ──────────────────────────────────────────────────
/* Every parameter already carries a written description in the schema; this
   surfaces it on hover (with range, default and the --set path) instead of
   relying on the OS tooltip, which is slow and unstyled. */
let tipEl = null;
let tipTimer = null;

function tipNode() {
  if (!tipEl) {
    tipEl = document.createElement('div');
    tipEl.id = 'tip';
    document.body.appendChild(tipEl);
  }
  return tipEl;
}

function hideTip() {
  clearTimeout(tipTimer);
  if (tipEl) tipEl.classList.remove('show');
}

function showTipAt(anchor, { title, desc, facts = [], path = '', stack = false }) {
  const el = tipNode();
  el.innerHTML = '';
  // `stack` lays the facts one per line - for payloads that are a dict readout
  // rather than a few prose fragments. The class comes off again here because
  // the one tip element is shared by every anchor in the app.
  el.classList.toggle('stack', stack);
  const h = document.createElement('div');
  h.className = 'tip-title';
  h.textContent = title;
  el.appendChild(h);
  if (desc) {
    const d = document.createElement('div');
    d.className = 'tip-desc';
    d.textContent = desc;
    el.appendChild(d);
  }
  if (facts.length) {
    const f = document.createElement('div');
    f.className = 'tip-facts';
    for (const t of facts) {
      const sp = document.createElement('span');
      sp.textContent = t;
      f.appendChild(sp);
    }
    el.appendChild(f);
  }
  if (path) {
    const pth = document.createElement('div');
    pth.className = 'tip-path';
    pth.textContent = `--set ${path}=…`;
    el.appendChild(pth);
  }
  el.classList.add('show');
  // place to the left of the (right-hand) panel, clamped to the viewport
  const r = anchor.getBoundingClientRect();
  const tr = el.getBoundingClientRect();
  let left = r.left - tr.width - 12;
  if (left < 8) left = Math.min(r.right + 12, window.innerWidth - tr.width - 8);
  let top = r.top + r.height / 2 - tr.height / 2;
  top = Math.max(8, Math.min(top, window.innerHeight - tr.height - 8));
  el.style.left = `${Math.round(left)}px`;
  el.style.top = `${Math.round(top)}px`;
}

/* attach(el, () => payload) - payload is built lazily on hover */
function attachTip(el, build) {
  el.addEventListener('mouseenter', () => {
    clearTimeout(tipTimer);
    tipTimer = setTimeout(() => showTipAt(el, build()), 260);
  });
  el.addEventListener('mouseleave', hideTip);
  el.addEventListener('mousedown', hideTip);
}

function paramTip(path, prm, baseVal) {
  const facts = [];
  if (prm.kind === 'float' || prm.kind === 'int') {
    facts.push(`range ${prm.lo} – ${prm.hi}${prm.unit ? ' ' + prm.unit : ''}`);
  } else if (prm.kind === 'enum') {
    facts.push(`${prm.choices.length} options`);
  }
  facts.push(`preset value ${baseVal}`);
  if (String(prm.default) !== String(baseVal)) facts.push(`effect default ${prm.default}`);
  if (prm.iscale) facts.push('follows Intensity');
  // Repeats of one effect carry a #n suffix; Texture scales the effect, not the
  // copy, so the suffix comes off before the lookup.
  if (NOISE_HINT.has(path.replace(/#\d+\./, '.'))) facts.push('follows Texture');
  return { title: prm.label, desc: prm.desc || '', facts, path };
}

/* Params the master Texture dial scales, keyed exactly as engine/texture.py
   keys them. Used only to annotate tooltips - but on the effect *and* the param,
   because matching the bare name told anyone hovering Saturation → Amount that
   the Texture dial would move it, and it will not. */
const NOISE_HINT = new Set(['grain.amount', 'grain.intermittent', 'grain.mottle',
  'dust.density', 'vhs.luma_noise', 'vhs.chroma_noise', 'vhs.fm_sparkle',
  'vhs.azimuth_error', 'ntsc.phase_noise', 'signal_rf.snow',
  'signal_rf.impulse_noise', 'rf_dx.noise_floor', 'herringbone.amount',
  'crt.retrace_lines', 'lcd_screen.moire_cam', 'exposure_auto.agc_gain_noise',
  'cel_dirt.density', 'paper_texture.amount', 'photocopy.toner',
  'riso_print.grain_ink']);

// ── range fill ──────────────────────────────────────────────────────
/* Sliders paint their track with the accent gradient up to the thumb; the CSS
   reads the percentage from a custom property this keeps in sync. */
function paintRange(el) {
  const lo = parseFloat(el.min) || 0;
  const hi = parseFloat(el.max) || 1;
  const v = parseFloat(el.value) || 0;
  const p = hi > lo ? ((v - lo) / (hi - lo)) * 100 : 0;
  el.style.setProperty('--p', `${Math.max(0, Math.min(100, p))}%`);
}

// ── favorites ───────────────────────────────────────────────────────
const STAR_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"><path d="m12 3 2.7 5.8 6.3.7-4.7 4.3 1.3 6.2-5.6-3.2L6.4 20l1.3-6.2L3 9.5l6.3-.7z"/></svg>';

function toggleFav(pid) {
  if (G.favs.has(pid)) G.favs.delete(pid);
  else G.favs.add(pid);
  if (!G.favs.size && G.favOnly) G.favOnly = false;
  saveStore();
  buildFilterBar();
  buildPresetList();
  if (state.presetId) syncFavButton();
}

function syncFavButton() {
  const btn = $('btn-fav');
  btn.classList.toggle('hidden', !state.presetId);
  btn.classList.toggle('faved', G.favs.has(state.presetId));
  btn.title = G.favs.has(state.presetId) ? 'Remove from favorites' : 'Favorite this aesthetic';
  $('btn-save-custom').classList.toggle('hidden', !state.presetId);
}

// ── custom aesthetics ───────────────────────────────────────────────
/* A custom is a preset plus the knobs you moved: same engine chain, different
   numbers. It stores the base preset id rather than a copy of the chain, so a
   preset that gains an effect in a later version carries its customs forward.
   Everything the render request needs is captured, seed included, because
   "the version I made" means the noise landed where it landed. */

function customById(cid) {
  return G.customs.find((c) => c.id === cid) || null;
}

/* What the list highlights and ↑/↓ walk: a custom masquerades as a preset id.
   A saved stack deliberately stays out of it - `sel` means "the aesthetic in the
   layer you have selected", and a stack is every layer at once. It gets its own
   `worn` marker instead, so editing layer 2 still lights layer 2's row. */
function selectionId() {
  return state.customId || state.presetId;
}

function isCustomId(id) {
  return typeof id === 'string' && id.startsWith('custom:');
}

function customName(cid) {
  const c = customById(cid);
  return c ? c.name : cid;
}

/* "VHS Standard Play - custom 2026-07-31 14:22" */
function defaultCustomName(baseId) {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  const stamp = `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
  return `${presetName(baseId)} - custom ${stamp}`;
}

async function saveCustom() {
  if (!state.presetId) return;
  const name = await askName({
    title: 'Save a custom aesthetic',
    sub: `Keeps every knob exactly as it is now, on top of ${presetName(state.presetId)}.`,
    value: defaultCustomName(state.presetId),
  });
  if (!name) return;
  const custom = {
    id: `custom:${++G.customSeq}`,
    name,
    base: state.presetId,
    variant: state.variant,
    sets: { ...state.sets },
    events: (state.events || []).map((e) => ({ ...e })),
    intensity: state.intensity,
    texture: state.texture,
    seed: state.seed,
    created: Date.now(),
  };
  G.customs.push(custom);
  saveStore();
  state.customId = custom.id;
  buildFilterBar();
  buildPresetList();
  buildParamPane();
  buildLayersPanel();
  renderTabs();
  setExportStatus(`Saved “${name}”.`);
}

/* A custom as a fresh layer, carrying everything it was saved with. This exists
   because there are two ways to reach for one - applying it to the selected
   layer, and stacking it on top - and they were restoring different things:
   stacking used to rebuild only the preset, variant and tweaks, so a custom
   whose whole point was a dialled-back Intensity came back at 1.0 and rendered
   as the plain preset. Both paths go through the same fields now. */
function layerFromCustom(c) {
  return newLayer({
    presetId: c.base,
    customId: c.id,
    variant: c.variant || null,
    sets: { ...(c.sets || {}) },
    events: (c.events || []).map((e) => ({ ...e })),
    seed: typeof c.seed === 'number' ? c.seed : 1 + Math.floor(Math.random() * 99999),
    intensity: typeof c.intensity === 'number' ? c.intensity : 1,
    texture: typeof c.texture === 'number' ? c.texture : 1,
  });
}

function applyCustom(cid, opts = {}) {
  const c = customById(cid);
  if (!c || !G.schema.presets[c.base]) return;
  state.stackId = null;    // a layer just changed what it is: no longer that stack
  state.presetId = c.base;
  state.customId = c.id;
  state.variant = c.variant || null;
  state.sets = { ...(c.sets || {}) };
  state.events = (c.events || []).map((e) => ({ ...e }));
  state.intensity = typeof c.intensity === 'number' ? c.intensity : 1;
  state.texture = typeof c.texture === 'number' ? c.texture : 1;
  if (typeof c.seed === 'number') state.seed = c.seed;
  syncMasterDials();
  syncSelection();
  renderTabs();
  buildParamPane();
  buildLayersPanel();
  schedulePreview(true, opts.previewDelay);
}

/* The master dials live outside buildParamPane, so applying a custom has to
   push its values back into them by hand. */
function syncMasterDials() {
  $('intensity').value = state.intensity;
  $('intensity-val').textContent = state.intensity.toFixed(2);
  paintRange($('intensity'));
  $('texture').value = state.texture;
  $('texture-val').textContent = state.texture.toFixed(2);
  paintRange($('texture'));
  $('seed').value = state.seed;
}

async function renameCustom(cid) {
  const c = customById(cid);
  if (!c) return;
  const name = await askName({
    title: 'Rename this custom aesthetic',
    sub: `Based on ${presetName(c.base)}.`,
    value: c.name,
    okLabel: 'Rename',
  });
  if (!name) return;
  c.name = name;
  saveStore();
  buildPresetList();
  if (state.customId === cid) { buildParamPane(); renderTabs(); }
}

function deleteCustom(cid) {
  const c = customById(cid);
  if (!c) return;
  if (!confirm(`Delete “${c.name}”?\n\nThe preset it was built on is untouched.`)) return;
  G.customs = G.customs.filter((x) => x.id !== cid);
  if (!G.customs.length) G.customOnly = false;
  saveStore();
  // Any tab wearing it keeps the settings, it just stops claiming the name.
  for (const s of G.sessions) if (s.customId === cid) s.customId = null;
  buildFilterBar();
  buildPresetList();
  if (state.presetId) buildParamPane();
  renderTabs();
}

/* Has the session drifted from the custom it was loaded from? Saying so beats
   letting the list claim you are still looking at the saved version. */
function customDrifted() {
  const c = state.customId ? customById(state.customId) : null;
  if (!c) return false;
  return (c.variant || null) !== state.variant
    || c.intensity !== state.intensity
    || c.texture !== state.texture
    || c.seed !== state.seed
    || JSON.stringify(c.sets || {}) !== JSON.stringify(state.sets)
    || JSON.stringify(c.events || []) !== JSON.stringify(state.events || []);
}

/* Names go into filenames, so keep them to something a filesystem enjoys. */
function slugify(s) {
  return (s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60)
    || 'custom';
}

/* ── saved stacks ────────────────────────────────────────────────────
   A custom is one aesthetic with your knobs on it. A stack is the whole
   arrangement: which aesthetics, in what order, each with its own knobs, and
   which of them are switched off. Same storage rule as customs - every layer
   holds a base preset *id*, never a copy of the chain, so a preset that gains
   an effect in a later version carries every stack that uses it forward. */

function stackById(sid) {
  return G.stacks.find((k) => k.id === sid) || null;
}

function isStackId(id) {
  return typeof id === 'string' && id.startsWith('stack:');
}

function stackName(sid) {
  const k = stackById(sid);
  return k ? k.name : sid;
}

/* The session's layers in saved form. Empty slots are dropped - an unfilled
   layer is not part of the arrangement - but disabled ones are kept, because
   "off for now" is a decision worth restoring. */
function captureStackLayers(sess = state) {
  return (sess.layers || []).filter((l) => l.presetId).map((l) => ({
    base: l.presetId,
    customId: l.customId || null,
    variant: l.variant || null,
    sets: { ...(l.sets || {}) },
    events: (l.events || []).map((e) => ({ ...e })),
    seed: l.seed,
    intensity: l.intensity,
    texture: l.texture,
    enabled: l.enabled !== false,
  }));
}

function savedLayerLabel(sl) {
  if (sl.customId && customById(sl.customId)) return customName(sl.customId);
  const p = G.schema && G.schema.presets[sl.base];
  return p ? p.name : sl.base;
}

/* "VHS Standard Play → Co-Channel Ghost" - the order they actually render in. */
function stackChain(k) {
  return (k.layers || []).map(savedLayerLabel).join(' → ');
}

function defaultStackName() {
  const names = captureStackLayers().map(savedLayerLabel);
  if (!names.length) return 'Stack';
  if (names.length === 1) return names[0];
  if (names.length === 2) return `${names[0]} + ${names[1]}`;
  return `${names[0]} +${names.length - 1} more`;
}

async function saveStack() {
  const layers = captureStackLayers();
  if (!layers.length) return;
  const name = await askName({
    title: 'Save this stack',
    sub: `Keeps all ${layers.length} layers, their order and every knob on each one.`,
    value: defaultStackName(),
  });
  if (!name) return;
  const stack = { id: `stack:${++G.stackSeq}`, name, layers, created: Date.now() };
  G.stacks.push(stack);
  saveStore();
  state.stackId = stack.id;
  buildFilterBar();
  buildPresetList();
  buildLayersPanel();
  renderTabs();
  setExportStatus(`Saved “${name}”.`);
}

/* One saved layer back into a live one. Seed included: "the version I made"
   means the noise landed where it landed. */
function layerFromSaved(sl) {
  return newLayer({
    presetId: sl.base,
    // A custom the user has since deleted leaves the numbers intact and just
    // stops claiming its name.
    customId: sl.customId && customById(sl.customId) ? sl.customId : null,
    variant: sl.variant || null,
    sets: { ...(sl.sets || {}) },
    events: (sl.events || []).map((e) => ({ ...e })),
    seed: typeof sl.seed === 'number' ? sl.seed : 1 + Math.floor(Math.random() * 99999),
    intensity: typeof sl.intensity === 'number' ? sl.intensity : 1,
    texture: typeof sl.texture === 'number' ? sl.texture : 1,
    enabled: sl.enabled !== false,
  });
}

/* Layers whose base preset still exists in this build. */
function usableStackLayers(k) {
  return (k.layers || []).filter((sl) => G.schema.presets[sl.base]);
}

function applyStack(sid, opts = {}) {
  const k = stackById(sid);
  if (!k) return;
  const usable = usableStackLayers(k);
  if (!usable.length) {
    setExportStatus(`“${k.name}” uses aesthetics this build does not have.`, true);
    return;
  }
  state.layers = usable.map(layerFromSaved);
  state.activeLayer = state.layers.length - 1;
  state.stackId = k.id;
  syncMasterDials();
  syncSelection();
  renderTabs();
  buildParamPane();
  buildLayersPanel();
  schedulePreview(true, opts.previewDelay);
  const lost = (k.layers || []).length - usable.length;
  if (lost) setExportStatus(`Applied “${k.name}” without ${lost} missing layer${lost === 1 ? '' : 's'}.`, true);
}

/* The green + on a stack row: pile the whole arrangement on top of what is
   already there, rather than replacing it. */
function appendStack(sid, opts = {}) {
  const k = stackById(sid);
  if (!k) return;
  const usable = usableStackLayers(k);
  if (!usable.length) return;
  // An untouched empty slot would otherwise sit under the stack doing nothing.
  if (state.layers.length === 1 && !state.layers[0].presetId) state.layers = [];
  for (const sl of usable) state.layers.push(layerFromSaved(sl));
  state.activeLayer = state.layers.length - 1;
  state.stackId = null;   // it is no longer that stack, it contains it
  syncMasterDials();
  syncSelection();
  renderTabs();
  buildParamPane();
  buildLayersPanel();
  schedulePreview(true, opts.previewDelay);
}

async function renameStack(sid) {
  const k = stackById(sid);
  if (!k) return;
  const name = await askName({
    title: 'Rename this stack',
    sub: stackChain(k),
    value: k.name,
    okLabel: 'Rename',
  });
  if (!name) return;
  k.name = name;
  saveStore();
  buildPresetList();
  buildLayersPanel();
  renderTabs();
}

function deleteStack(sid) {
  const k = stackById(sid);
  if (!k) return;
  if (!confirm(`Delete “${k.name}”?\n\nThe aesthetics it was built from are untouched.`)) return;
  G.stacks = G.stacks.filter((x) => x.id !== sid);
  if (!G.stacks.length) G.stackOnly = false;
  saveStore();
  // Any tab wearing it keeps its layers, it just stops claiming the name.
  for (const s of G.sessions) if (s.stackId === sid) s.stackId = null;
  buildFilterBar();
  buildPresetList();
  buildLayersPanel();
  renderTabs();
}

/* Has the arrangement drifted from the stack it was loaded from? Picking a
   different aesthetic into a layer drops the name outright (see selectPreset);
   this catches the quieter kind - a knob moved, a layer switched off. */
function stackDrifted() {
  const k = state.stackId ? stackById(state.stackId) : null;
  if (!k) return false;
  return JSON.stringify(captureStackLayers()) !== JSON.stringify(usableStackLayers(k));
}

/* What the session is wearing, for tabs and export filenames. */
function wearingName(sess = state) {
  if (sess.stackId) return stackName(sess.stackId);
  if (sess.customId) return customName(sess.customId);
  return sess.presetId ? presetName(sess.presetId) : null;
}

/* The header's second line reports drift, and drift changes on every knob. */
function syncPresetSub() {
  if (!state.presetId) return;
  const p = G.schema.presets[state.presetId];
  const c = state.customId ? customById(state.customId) : null;
  $('preset-sub').textContent = c
    ? `custom · from ${p.name}${customDrifted() ? ' · edited' : ''}`
    : `${p.era} · ${p.family}`;
}

/* Electron has no window.prompt, and a name is worth asking for properly. */
let modalResolve = null;

function askName({ title, sub = '', value = '', okLabel = 'Save' }) {
  if (modalResolve) return Promise.resolve(null);   // one question at a time
  const inp = $('modal-input');
  $('modal-title').textContent = title;
  $('modal-sub').textContent = sub;
  $('modal-ok').textContent = okLabel;
  inp.value = value;
  $('modal').classList.remove('hidden');
  inp.focus();
  inp.select();
  return new Promise((resolve) => { modalResolve = resolve; });
}

function closeModal(result) {
  $('modal').classList.add('hidden');
  const r = modalResolve;
  modalResolve = null;
  if (r) r(result);
}

/* The other kind of question: no text to type, just a choice between named
   ways out. Resolves with the chosen key, or null for cancel. */
let choiceResolve = null;

function askChoice({ title, sub = '', choices }) {
  // Holding ↓ on a layer worth protecting would otherwise queue one of these
  // per keypress. The first question wins and the rest are dropped.
  if (choiceResolve) return Promise.resolve(null);
  $('choice-title').textContent = title;
  $('choice-sub').textContent = sub;
  const row = $('choice-row');
  row.innerHTML = '';
  for (const c of choices) {
    const b = document.createElement('button');
    b.textContent = c.label;
    if (c.className) b.className = c.className;
    if (c.title) b.title = c.title;
    b.onclick = () => closeChoice(c.key);
    row.appendChild(b);
  }
  $('choice-modal').classList.remove('hidden');
  const preferred = row.querySelector('button.accent');
  if (preferred) preferred.focus();
  return new Promise((resolve) => { choiceResolve = resolve; });
}

function closeChoice(key) {
  $('choice-modal').classList.add('hidden');
  const r = choiceResolve;
  choiceResolve = null;
  if (r) r(key || null);
}

function choiceOpen() {
  return Boolean(choiceResolve);
}

/* ── updates ─────────────────────────────────────────────────────────
   The main process owns the network and the install; this half owns when to
   ask and what to say about it. See app/updater.js for why the app updates
   itself rather than going through electron-updater.                       */

function setVersionChip() {
  // window.aesth.version is available before the page runs; U.info arrives
  // later and carries the rest (last check time, platform, arch).
  const version = (U.info && U.info.version) || window.aesth.version || '';
  const packaged = U.info ? U.info.packaged : window.aesth.packaged;
  $('btn-version').textContent = version ? `v${version}` : '';
  $('btn-version').title = version && !packaged
    ? `Aesthetician ${version} - running from a dev checkout`
    : 'About Aesthetician';
}

function syncUpdateButton() {
  const btn = $('btn-update');
  const newer = Boolean(U.latest && U.latest.available);
  // A staged download names its own version: it can be the newest release or an
  // older one picked out of the list, and the button has to say which.
  btn.classList.toggle('hidden', !(U.staged || newer));
  btn.classList.remove('blocked');
  if (U.staged) {
    btn.textContent = `Install ${U.staged.version}`;
    btn.title = `Version ${U.staged.version} is downloaded and ready to install`;
    return;
  }
  if (!newer) return;
  btn.textContent = 'Update available';
  btn.title = `Aesthetician ${U.latest.latest} is out (you have ${U.latest.current})`;
}

/* Boot: show the version straight away, then check in the background if the
   last check has aged past a day. A failed check stays quiet - the button just
   does not appear. */
/* Just the version, as early as possible. */
async function loadVersion() {
  try {
    U.info = await window.aesth.updateInfo();
  } catch (_) { /* leave the chip reading v- */ }
  setVersionChip();
}

async function initUpdates() {
  if (!U.info) await loadVersion();
  window.aesth.onUpdateProgress(onUpdateProgress);
  if (!U.info || !U.info.stale) {
    if (U.info && U.info.last) { U.latest = U.info.last; syncUpdateButton(); }
    return;
  }
  try {
    U.latest = await window.aesth.updateCheck({});
    syncUpdateButton();
  } catch (_) { /* offline: try again tomorrow */ }
}

function onUpdateProgress(msg) {
  if (msg.stage !== 'download') return;
  $('about-bar').classList.remove('hidden');
  $('about-bar-fill').style.width = `${Math.round((msg.frac || 0) * 100)}%`;
  const got = formatBytes(msg.received);
  const total = msg.total ? ` of ${formatBytes(msg.total)}` : '';
  setAboutStatus(`Downloading ${got}${total}…`, 'busy');
}

function formatBytes(n) {
  if (!n) return '0 MB';
  const mb = n / (1024 * 1024);
  return mb >= 1024 ? `${(mb / 1024).toFixed(2)} GB` : `${mb.toFixed(0)} MB`;
}

/* Electron wraps every rejected IPC call in "Error invoking remote method
   'aesth:x': Error: ..." - the part worth showing is the last one. */
function errText(err) {
  const raw = String((err && err.message) || err || '');
  const m = /Error: ([\s\S]*)$/.exec(raw);
  return (m ? m[1] : raw).trim();
}

function setAboutStatus(text, tone = '') {
  const el = $('about-status');
  el.textContent = text;
  el.className = `about-status ${tone || 'dim'}`;
}

/* ── release notes ───────────────────────────────────────────────────
   Notes are text off the network, so nothing here ever goes near innerHTML.
   Lines are turned into elements one at a time and every image URL is checked
   against GitHub's own hosts before it becomes a src - which is why the raw
   <img> tags used to sit there as literal markup, and why the fix is a parser
   rather than "just render the HTML". */
const NOTE_IMAGE_HOSTS = ['github.com', 'objects.githubusercontent.com'];

function noteImageUrl(raw) {
  let u;
  try { u = new URL(String(raw).trim()); } catch (_) { return null; }
  if (u.protocol !== 'https:') return null;
  const ok = NOTE_IMAGE_HOSTS.includes(u.hostname) || u.hostname.endsWith('.githubusercontent.com');
  if (!ok) return null;
  // github.com hosts plenty that is not an image; only the attachment path is.
  if (u.hostname === 'github.com' && !u.pathname.startsWith('/user-attachments/')) return null;
  return u.toString();
}

const NOTE_MD_IMAGE = /!\[[^\]]*\]\(\s*<?(https:\/\/[^\s)>]+)>?[^)]*\)/g;
const NOTE_HTML_IMAGE = /<img\b[^>]*\bsrc\s*=\s*["'](https:\/\/[^"']+)["'][^>]*>/gi;

function renderNotes(text, host) {
  host.innerHTML = '';
  const lines = String(text || '').split('\n');
  let buffer = [];

  const flush = () => {
    if (!buffer.length) return;
    const para = document.createElement('div');
    para.className = 'note-text';
    para.textContent = buffer.join('\n').replace(/\n{3,}/g, '\n\n').trim();
    if (para.textContent) host.appendChild(para);
    buffer = [];
  };

  const addImage = (url) => {
    const src = noteImageUrl(url);
    if (!src) return;
    flush();
    const img = document.createElement('img');
    img.className = 'note-img';
    img.alt = 'Screenshot from the release notes';
    img.title = 'Open full size';
    img.onclick = () => window.aesth.openExternal(src);
    host.appendChild(img);
    // The bytes come back from the main process as a data: URL. The renderer
    // never reaches out itself, so its CSP still forbids remote images - which
    // matters here because user-attachments redirects onto an S3 host.
    window.aesth.noteImage(src).then((data) => {
      if (data) img.src = data;
      else img.remove();          // no broken-image gap for one that will not load
    }).catch(() => img.remove());
  };

  for (const line of lines) {
    const urls = [];
    let rest = line.replace(NOTE_HTML_IMAGE, (_m, u) => { urls.push(u); return ''; });
    rest = rest.replace(NOTE_MD_IMAGE, (_m, u) => { urls.push(u); return ''; });
    // A bare attachment URL on its own line is how GitHub itself renders one.
    const bare = rest.trim();
    if (!urls.length && noteImageUrl(bare)) { urls.push(bare); rest = ''; }

    if (urls.length) {
      if (rest.trim()) buffer.push(rest.trim());
      urls.forEach(addImage);
      continue;
    }
    const heading = /^#{1,6}\s+(.*)$/.exec(line);
    if (heading) {
      flush();
      const h = document.createElement('div');
      h.className = 'note-head';
      h.textContent = heading[1].trim();
      host.appendChild(h);
      continue;
    }
    buffer.push(line);
  }
  flush();
}

function openAbout() {
  $('about-modal').classList.remove('hidden');
  $('about-version').textContent = U.info
    ? `version ${U.info.version}${U.info.packaged ? '' : ' · dev checkout'}`
    : 'version unknown';
  $('about-bar').classList.add('hidden');
  paintAbout();
}

function closeAbout() {
  $('about-modal').classList.add('hidden');
}

/* Whichever release the dialog is currently talking about: the one picked out
   of the list if there is one, otherwise whatever the check turned up. Painted
   once per source, because rendering notes fetches their screenshots. */
function paintNotes() {
  const host = $('about-notes');
  const pick = pickedRelease();
  const r = U.latest;
  const text = pick ? pick.notes
    : (r && r.ok && r.available ? r.notes : '');
  const source = pick ? pick.tag : 'latest';
  if (!text) {
    host.classList.add('hidden');
    host.dataset.source = '';
    return;
  }
  if (host.dataset.source !== source) {
    renderNotes(text, host);
    // The pane normally holds the newest release's notes, so a picked one has
    // to say whose it is showing instead.
    if (pick) {
      const head = document.createElement('div');
      head.className = 'note-head';
      const when = releaseDate(pick.publishedAt);
      head.textContent = `What ${pick.version} shipped with${when ? ` · ${when}` : ''}`;
      host.prepend(head);
    }
    host.dataset.source = source;
  }
  host.classList.remove('hidden');
}

/* One dialog covers up to date, out of date, downloaded, and every way those
   can fail, so the button label and the status line are derived rather than
   set at each call site. */
function paintAbout() {
  const action = $('about-action');
  const r = U.latest;

  action.disabled = false;
  action.textContent = 'Check for updates';
  paintNotes();
  paintPicker();

  if (U.busy === 'checking') { setAboutStatus('Checking for updates…', 'busy'); action.disabled = true; return; }
  if (U.busy === 'downloading') { action.textContent = 'Cancel'; return; }
  if (U.busy === 'installing') { setAboutStatus('Installing…', 'busy'); action.disabled = true; return; }

  // A download waiting on disk outranks everything else the dialog could say,
  // and it names its own version - it is not always the newest release.
  if (U.staged) {
    setAboutStatus(`Version ${U.staged.version} is downloaded and ready to install. `
      + 'Aesthetician will restart.', 'ok');
    action.textContent = 'Install and restart';
    return;
  }
  if (!r) {
    setAboutStatus(U.info && U.info.lastCheckAt
      ? `Last checked ${relativeTime(U.info.lastCheckAt)}.`
      : 'Not checked yet.');
    return;
  }
  if (!r.ok) {
    setAboutStatus(`Could not reach GitHub: ${r.error}`, 'warn');
    return;
  }
  if (!r.available) {
    setAboutStatus(`Aesthetician ${r.current} is the latest version. `
      + `Checked ${relativeTime(r.checkedAt)}.`, 'ok');
    return;
  }
  if (!r.installable) {
    setAboutStatus(`Version ${r.latest} is available. ${r.note}`, 'warn');
    action.textContent = 'View releases';
    return;
  }
  const size = r.asset && r.asset.size ? ` (${formatBytes(r.asset.size)})` : '';
  setAboutStatus(`Version ${r.latest} is available - you have ${r.current}.`);
  action.textContent = `Download${size}`;
}

/* ── the version picker ──────────────────────────────────────────────
   Everything published, newest first, so a specific version can be put back
   on - to find out which release a bug arrived in, or to get off one that
   broke something. Installing an older build is the same download, checksum
   and swap as an update; only the direction differs.                        */
function pickedRelease() {
  if (!U.picker || !U.pickTag || !U.releases || !U.releases.ok) return null;
  return U.releases.releases.find((rel) => rel.tag === U.pickTag) || null;
}

function platformLabel() {
  const src = (U.releases && U.releases.ok ? U.releases : U.info) || {};
  const name = src.platform === 'darwin' ? 'macOS'
    : src.platform === 'win32' ? 'Windows'
      : src.platform || 'this platform';
  return [name, src.arch].filter(Boolean).join(' ');
}

function releaseDate(iso) {
  const d = iso ? new Date(iso) : null;
  if (!d || Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

/* What one row of the dropdown says. The reasons a version cannot be installed
   belong here rather than in a message that only appears after picking it. */
function releaseLabel(rel) {
  const bits = [`v${rel.version}`];
  if (rel.direction === 'current') bits.push('running now');
  if (rel.prerelease) bits.push('pre-release');
  const when = releaseDate(rel.publishedAt);
  if (when) bits.push(when);
  if (!rel.asset) bits.push(`no ${platformLabel()} build`);
  return bits.join(' · ');
}

function fillVersionSelect() {
  const sel = $('about-version-select');
  const list = (U.releases && U.releases.ok) ? U.releases.releases : [];
  sel.innerHTML = '';
  const first = document.createElement('option');
  first.value = '';
  first.textContent = list.length ? 'Choose a version…' : 'No releases found';
  sel.appendChild(first);
  for (const rel of list) {
    const opt = document.createElement('option');
    opt.value = rel.tag;
    opt.textContent = releaseLabel(rel);
    sel.appendChild(opt);
  }
  // A refreshed list keeps the selection if it still has it.
  sel.value = list.some((rel) => rel.tag === U.pickTag) ? U.pickTag : '';
  U.pickTag = sel.value;
  sel.disabled = !list.length;
}

function paintPicker() {
  const wrap = $('about-picker');
  const btn = $('about-version-action');
  const note = $('about-picker-note');
  const setNote = (text, tone = '') => {
    note.textContent = text;
    note.className = `about-picker-note ${tone || 'dim'}`;
  };

  $('about-other').textContent = U.picker ? 'Hide versions' : 'Other versions';
  // With a version selected, the link goes to that release rather than the
  // newest one, because that is the one being read about.
  $('about-repo').textContent = pickedRelease() ? 'View this release' : 'View releases';
  wrap.classList.toggle('hidden', !U.picker);
  if (!U.picker) return;

  btn.textContent = 'Download';
  btn.disabled = true;

  if (U.releasesBusy) { setNote('Reading the release list…', 'busy'); return; }
  if (U.releases && !U.releases.ok) {
    setNote(`Could not reach GitHub: ${U.releases.error}`, 'warn');
    return;
  }

  const rel = pickedRelease();
  if (!rel) {
    setNote('Any published release can be installed from here, including older ones.');
    return;
  }
  if (U.busy === 'downloading') { setNote(`Downloading ${rel.version}…`, 'busy'); return; }
  if (U.busy) return;
  if (U.staged && U.staged.tag === rel.tag) {
    setNote(`Version ${rel.version} is downloaded and ready. Aesthetician will restart into it.`, 'ok');
    btn.textContent = 'Install and restart';
    btn.disabled = false;
    return;
  }

  if (U.releases.note) { setNote(U.releases.note, 'warn'); return; }
  if (!rel.asset) {
    setNote(`${rel.tag} has no build for ${platformLabel()}. `
      + 'Its release page lists whatever it does carry.', 'warn');
    return;
  }
  const size = rel.asset.size ? ` (${formatBytes(rel.asset.size)})` : '';
  btn.textContent = `Download${size}`;
  btn.disabled = false;
  setNote(pickNote(rel));
}

function pickNote(rel) {
  const current = (U.releases && U.releases.current) || (U.info && U.info.version) || '';
  if (rel.direction === 'older') {
    return `Goes back to ${rel.version} from ${current}. The installed copy is replaced and `
      + 'the app restarts; nothing you have saved is removed, and the newer version can be '
      + 'reinstalled the same way.';
  }
  if (rel.direction === 'current') {
    return `Reinstalls ${rel.version}, the version already running.`;
  }
  return `Moves up to ${rel.version} from ${current}. The installed copy is replaced and the `
    + 'app restarts.';
}

async function loadReleases({ force = false } = {}) {
  U.releasesBusy = true;
  paintPicker();
  try {
    U.releases = await window.aesth.updateReleases({ force });
  } catch (err) {
    U.releases = { ok: false, error: errText(err), releases: [] };
  }
  U.releasesBusy = false;
  fillVersionSelect();
  paintPicker();
  paintNotes();
}

function toggleVersionPicker() {
  U.picker = !U.picker;
  paintPicker();
  paintNotes();
  if (U.picker && !U.releases && !U.releasesBusy) loadReleases();
}

function relativeTime(ts) {
  const mins = Math.max(Math.round((Date.now() - ts) / 60000), 0);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours} h ago`;
  return `${Math.round(hours / 24)} d ago`;
}

async function checkForUpdates({ force = true } = {}) {
  U.busy = 'checking';
  paintAbout();
  try {
    U.latest = await window.aesth.updateCheck({ force });
  } catch (err) {
    U.latest = { ok: false, error: errText(err) };
  }
  U.busy = '';
  U.staged = null;
  syncUpdateButton();
  paintAbout();
}

/* Without a tag this takes the newest release; with one it takes whatever the
   picker selected, which may well be older than what is running. */
async function downloadUpdate({ tag = '' } = {}) {
  U.busy = 'downloading';
  // The main process clears its download directory before it starts, so
  // anything staged from before is gone the moment this begins.
  U.staged = null;
  $('about-bar').classList.remove('hidden');
  $('about-bar-fill').style.width = '0%';
  paintAbout();
  try {
    const staged = await window.aesth.updateDownload({ tag });
    U.staged = {
      version: (staged && staged.version) || (U.latest && U.latest.latest) || '',
      tag: (staged && staged.tag) || tag,
    };
    U.busy = '';
    $('about-bar').classList.add('hidden');
  } catch (err) {
    U.busy = '';
    U.staged = null;
    $('about-bar').classList.add('hidden');
    const msg = errText(err);
    paintAbout();
    setAboutStatus(msg.includes('canceled') ? 'Download canceled.' : `Download failed: ${msg}`,
      msg.includes('canceled') ? '' : 'warn');
    syncUpdateButton();
    return;
  }
  syncUpdateButton();
  paintAbout();
}

async function installUpdate() {
  // The installer replaces files this process has open, so anything still
  // writing a video has to land first. Killing an export to install an update
  // is not a trade the app gets to make on the user's behalf.
  const busy = activeExports();
  if (busy.length) {
    const btn = $('btn-update');
    btn.classList.add('blocked');
    btn.textContent = 'Finish exports first';
    setTimeout(syncUpdateButton, 4000);
    const detail = `${busy.length} export${busy.length > 1 ? 's are' : ' is'} still running. `
      + 'Let them finish or cancel them, then update.';
    if ($('about-modal').classList.contains('hidden')) setExportStatus(detail, true);
    else setAboutStatus(detail, 'warn');
    toggleExportsPanel(true);
    return;
  }
  U.busy = 'installing';
  paintAbout();
  try {
    await window.aesth.updateInstall();
    // On macOS the app exits here and a helper puts the new copy in place.
    setAboutStatus('Restarting…', 'busy');
  } catch (err) {
    U.busy = '';
    paintAbout();
    setAboutStatus(`Install failed: ${errText(err)}`, 'warn');
    await window.aesth.updateReveal();
  }
}

/* The titlebar button is a shortcut through whatever step comes next. */
async function updateButtonClicked() {
  if (U.staged) { await installUpdate(); return; }
  openAbout();
  if (U.latest && U.latest.available && U.latest.installable) await downloadUpdate();
}

function wireUpdates() {
  $('btn-version').addEventListener('click', openAbout);
  $('btn-update').addEventListener('click', updateButtonClicked);
  $('about-close').addEventListener('click', closeAbout);
  $('about-repo').addEventListener('click', () => {
    const pick = pickedRelease();
    window.aesth.openExternal((pick && pick.htmlUrl)
      || (U.latest && U.latest.htmlUrl)
      || (U.info && U.info.releasesUrl)
      || 'https://github.com/heresalexandria/aesthetician/releases');
  });
  $('about-other').addEventListener('click', toggleVersionPicker);
  $('about-version-select').addEventListener('change', (e) => {
    U.pickTag = e.target.value;
    paintPicker();
    paintNotes();
  });
  $('about-version-action').addEventListener('click', async () => {
    const rel = pickedRelease();
    if (!rel || U.busy) return;
    if (U.staged && U.staged.tag === rel.tag) { await installUpdate(); return; }
    await downloadUpdate({ tag: rel.tag });
  });
  $('about-action').addEventListener('click', async () => {
    const r = U.latest;
    if (U.busy === 'downloading') {
      await window.aesth.updateCancel();
      return;                                  // downloadUpdate's catch tidies up
    }
    if (U.busy) return;
    if (U.staged) { await installUpdate(); return; }
    if (r && r.ok && r.available && !r.installable) {
      window.aesth.openExternal(r.htmlUrl || r.releasesUrl);
      return;
    }
    if (r && r.ok && r.available && r.installable) { await downloadUpdate(); return; }
    await checkForUpdates();
  });
  $('about-modal').addEventListener('mousedown', (e) => {
    if (e.target === $('about-modal') && !U.busy) closeAbout();
  });
}

// ── filter bar (family chips + era decades) ─────────────────────────
function decadeOf(p) {
  const y = parseInt(p.era, 10);
  return Number.isFinite(y) ? `${Math.floor(y / 10) * 10}s` : null;
}

function buildFilterBar() {
  const presets = Object.values(G.schema.presets);

  const chips = $('family-chips');
  chips.innerHTML = '';
  if (G.favs.size) {
    const star = document.createElement('span');
    star.className = 'chip star-chip' + (G.favOnly ? ' sel' : '');
    star.textContent = `★ ${G.favs.size}`;
    star.title = 'Show favorites only';
    star.onclick = () => {
      G.favOnly = !G.favOnly;
      if (G.favOnly) G.customOnly = false;
      buildFilterBar(); buildPresetList();
    };
    chips.appendChild(star);
  }
  if (G.customs.length) {
    const cc = document.createElement('span');
    cc.className = 'chip custom-chip' + (G.customOnly ? ' sel' : '');
    cc.textContent = `✎ ${G.customs.length}`;
    cc.title = 'Show my custom aesthetics only';
    cc.onclick = () => {
      G.customOnly = !G.customOnly;
      if (G.customOnly) { G.favOnly = false; G.stackOnly = false; }
      buildFilterBar(); buildPresetList();
    };
    chips.appendChild(cc);
  }
  if (G.stacks.length) {
    const sc = document.createElement('span');
    sc.className = 'chip stack-chip' + (G.stackOnly ? ' sel' : '');
    sc.textContent = `▤ ${G.stacks.length}`;
    sc.title = 'Show my saved stacks only';
    sc.onclick = () => {
      G.stackOnly = !G.stackOnly;
      if (G.stackOnly) { G.favOnly = false; G.customOnly = false; }
      buildFilterBar(); buildPresetList();
    };
    chips.appendChild(sc);
  }
  const all = document.createElement('span');
  all.className = 'chip' + (G.filterFamilies.size || G.favOnly || G.customOnly || G.stackOnly ? '' : ' sel');
  all.textContent = 'All';
  all.onclick = () => {
    G.filterFamilies.clear();
    G.favOnly = false;
    G.customOnly = false;
    G.stackOnly = false;
    buildFilterBar(); buildPresetList();
  };
  chips.appendChild(all);
  const fams = [...new Set(presets.map((p) => p.family))]
    .sort((a, b) => famRank(a) - famRank(b));
  for (const f of fams) {
    const n = presets.filter((p) => p.family === f).length;
    const c = document.createElement('span');
    c.className = 'chip' + (G.filterFamilies.has(f) ? ' sel' : '');
    c.textContent = f;
    c.title = `${n} preset${n === 1 ? '' : 's'}`;
    c.onclick = () => {
      if (G.filterFamilies.has(f)) G.filterFamilies.delete(f);
      else G.filterFamilies.add(f);
      buildFilterBar();
      buildPresetList();
    };
    chips.appendChild(c);
  }

  const era = $('era-filter');
  const current = G.filterEra;
  era.innerHTML = '<option value="">Any era</option>';
  const decades = [...new Set(presets.map(decadeOf).filter(Boolean))]
    .sort((a, b) => parseInt(a, 10) - parseInt(b, 10));
  for (const d of decades) {
    const o = document.createElement('option');
    o.value = d;
    o.textContent = d;
    if (d === current) o.selected = true;
    era.appendChild(o);
  }
  era.classList.toggle('active', !!current);

  $('preset-search').placeholder = `Search ${presets.length} aesthetics…`;
}

function passesFilters(p) {
  if (G.favOnly && !G.favs.has(p.id)) return false;
  if (G.filterFamilies.size && !G.filterFamilies.has(p.family)) return false;
  if (G.filterEra && decadeOf(p) !== G.filterEra) return false;
  return true;
}

function anyFilterActive() {
  return G.favOnly || G.customOnly || G.stackOnly || G.filterFamilies.size > 0
    || !!G.filterEra || !!$('preset-search').value;
}

function clearFilters() {
  G.favOnly = false;
  G.customOnly = false;
  G.stackOnly = false;
  G.filterFamilies.clear();
  G.filterEra = '';
  $('preset-search').value = '';
  buildFilterBar();
  buildPresetList();
}

// ── preset list ─────────────────────────────────────────────────────
const BLANK_PX = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';

/* Adjust leads: plain corrections are reached for in a hurry when they are
   wanted at all. Then the looks people reach for most; audio-only sits last
   because those rows leave the picture untouched (their thumbnails are all the
   same untreated frame, so alphabetical order opened the app on 29 of them). */
const FAMILY_ORDER = ['adjust', 'vhs', 'film', 'broadcast', 'cartoon', 'digital', 'world',
  'decay', 'exhibition', 'print', 'transmission', 'stylized', 'audio'];

function famRank(f) {
  // With an audio source, the audio-first presets are the relevant ones, so they
  // lead instead of trailing. (Every preset has an audio chain, so none are hidden.)
  if (state.audioSource) {
    if (f === 'audio') return -1;
    const j = FAMILY_ORDER.indexOf(f);
    return j < 0 ? FAMILY_ORDER.length : j;
  }
  const i = FAMILY_ORDER.indexOf(f);
  return i < 0 ? FAMILY_ORDER.length : i;   // unknown families sort before audio
}

function fileUrl(p) {
  return 'file://' + encodeURI(p).replace(/#/g, '%23').replace(/\?/g, '%3F');
}

function isAudioOnly(p) {
  return p.family === 'audio' || !(p.video && p.video.length);
}

/* Tagline: preset.tagline when the schema has one, else a tidy ~45-char
   truncation of the long description (cut on a word boundary). */
function taglineFor(p) {
  const t = (p.tagline || '').trim();
  if (t) return t;
  let d = (p.desc || '').replace(/\s+/g, ' ').trim();
  if (!d || d.length <= 45) return d;
  d = d.slice(0, 44);
  const sp = d.lastIndexOf(' ');
  if (sp > 28) d = d.slice(0, sp);
  return d.replace(/[\s,;:.\-–—]+$/, '') + '…';
}

/* Exactly one animated image exists in the document at any time: it is moved
   into whichever row the pointer is over. 192 rows never animate at once. */
const hoverAnim = document.createElement('img');
hoverAnim.className = 't-anim';
hoverAnim.alt = '';
hoverAnim.decoding = 'async';
hoverAnim.draggable = false;
let hoverTimer = null;
let hoverHost = null;

function stopHoverAnim() {
  clearTimeout(hoverTimer);
  if (hoverHost) {
    hoverAnim.remove();
    hoverAnim.src = BLANK_PX; // detach + blank: the webp stops decoding
    hoverHost = null;
  }
}

function armHoverAnim(card, holder, animPath) {
  const url = fileUrl(animPath);
  card.addEventListener('mouseenter', () => {
    clearTimeout(hoverTimer);
    // small delay so sweeping the pointer down the list costs nothing
    hoverTimer = setTimeout(() => {
      if (hoverHost && hoverHost !== holder) hoverAnim.remove();
      hoverAnim.src = url; // re-setting restarts the loop at frame 0
      holder.appendChild(hoverAnim);
      hoverHost = holder;
    }, 90);
  });
  card.addEventListener('mouseleave', () => {
    clearTimeout(hoverTimer);
    if (hoverHost === holder) stopHoverAnim();
  });
}

function thumbFor(p) {
  const holder = document.createElement('div');
  holder.className = 'p-thumb';
  const t = G.thumbs[p.id];
  if (t && t.poster) {
    const img = document.createElement('img');
    img.className = 't-poster';
    img.src = fileUrl(t.poster);
    img.width = 50;
    img.height = 50;
    img.loading = 'lazy';
    img.decoding = 'async';
    img.draggable = false;
    img.alt = '';
    img.onerror = () => { img.remove(); holder.classList.add('empty'); };
    holder.appendChild(img);
  } else {
    holder.classList.add('empty');
  }
  if (isAudioOnly(p)) {
    holder.classList.add('audio');
    const badge = document.createElement('span');
    badge.className = 't-badge';
    badge.textContent = '♪';
    badge.title = 'Audio-only preset - the picture is untouched';
    holder.appendChild(badge);
  } else if (t && t.anim) {
    holder.classList.add('animable');
  }
  return holder;
}

/* Stacking is deliberate: the row itself still swaps the selected layer, and
   only this button (or +/=) adds another. Otherwise arrowing down the list
   would build a twenty-layer stack in a second of key repeat. */
function addLayerButton(id) {
  const add = document.createElement('button');
  add.className = 'card-add';
  add.textContent = '+';
  add.title = 'Add as another layer on top';
  add.onclick = (e) => { e.stopPropagation(); addLayer(id); };
  return add;
}

function presetCard(p) {
  const card = document.createElement('div');
  card.className = 'preset-card' + (p.id === selectionId() ? ' sel' : '');
  card.dataset.pid = p.id;
  card.title = p.desc || p.name;

  const holder = thumbFor(p);
  card.appendChild(holder);

  const text = document.createElement('div');
  text.className = 'p-text';
  const name = document.createElement('span');
  name.className = 'p-name';
  name.textContent = p.name;
  const meta = document.createElement('span');
  meta.className = 'p-meta';
  const nv = p.variants.length;
  meta.textContent = `${p.era}${nv ? ` · ${nv} variant${nv === 1 ? '' : 's'}` : ''}`;
  text.appendChild(name);
  text.appendChild(meta);
  const tag = taglineFor(p);
  if (tag) {
    const tl = document.createElement('span');
    tl.className = 'p-tag';
    tl.textContent = tag;
    text.appendChild(tl);
  }
  card.appendChild(text);

  const star = document.createElement('button');
  star.className = 'card-star' + (G.favs.has(p.id) ? ' faved' : '');
  star.innerHTML = STAR_SVG;
  star.title = G.favs.has(p.id) ? 'Remove from favorites' : 'Favorite this aesthetic';
  star.onclick = (e) => { e.stopPropagation(); toggleFav(p.id); };
  card.appendChild(star);

  card.appendChild(addLayerButton(p.id));

  const t = G.thumbs[p.id];
  if (t && t.anim && !isAudioOnly(p)) armHoverAnim(card, holder, t.anim);
  card.onclick = () => pickFromList(p.id);
  return card;
}

/* A saved custom borrows its base preset's thumbnail - it is the same chain
   underneath - and wears a badge so it never reads as a stock aesthetic. */
function customCard(c) {
  const base = G.schema.presets[c.base];
  const card = document.createElement('div');
  card.className = 'preset-card custom' + (c.id === selectionId() ? ' sel' : '');
  card.dataset.pid = c.id;
  // The name leads, because two lines still clamp a long one and the tooltip is
  // then the only place the whole thing exists.
  card.title = `${c.name}\n\nCustom aesthetic based on ${base.name}`;

  const holder = thumbFor(base);
  const badge = document.createElement('span');
  badge.className = 'c-badge';
  badge.textContent = '✎';
  badge.title = 'Your custom edit';
  holder.appendChild(badge);
  card.appendChild(holder);

  const text = document.createElement('div');
  text.className = 'p-text';
  const name = document.createElement('span');
  name.className = 'p-name';
  name.textContent = c.name;
  const meta = document.createElement('span');
  meta.className = 'p-meta';
  const n = Object.keys(c.sets || {}).length;
  meta.textContent = `custom · ${n} tweak${n === 1 ? '' : 's'}`;
  const tl = document.createElement('span');
  tl.className = 'p-tag';
  tl.textContent = `from ${base.name}`;
  text.appendChild(name);
  text.appendChild(meta);
  text.appendChild(tl);
  card.appendChild(text);

  const tools = document.createElement('div');
  tools.className = 'card-tools';
  const ren = document.createElement('button');
  ren.textContent = '✎';
  ren.title = 'Rename';
  ren.onclick = (e) => { e.stopPropagation(); renameCustom(c.id); };
  const del = document.createElement('button');
  del.textContent = '×';
  del.title = 'Delete this custom aesthetic';
  del.onclick = (e) => { e.stopPropagation(); deleteCustom(c.id); };
  tools.appendChild(ren);
  tools.appendChild(del);
  card.appendChild(tools);

  card.appendChild(addLayerButton(c.id));
  card.onclick = () => pickFromList(c.id);
  return card;
}

/* A saved stack borrows the thumbnail of its *last* layer - the one applied
   last, so the one that dominates what you actually end up looking at - and
   carries a ▤ badge with the layer count so it never reads as a single
   aesthetic. */
function stackCard(k) {
  const usable = usableStackLayers(k);
  const top = usable[usable.length - 1];
  const base = top && G.schema.presets[top.base];
  const card = document.createElement('div');
  card.className = 'preset-card stack'
    + (k.id === state.stackId ? ' worn' : '')
    + (usable.length ? '' : ' broken');
  card.dataset.pid = k.id;
  card.title = usable.length
    ? `${k.name}\n\nSaved stack · ${stackChain(k)}`
    : `${k.name}\n\nThis stack uses aesthetics that are not in this build.`;

  let holder;
  if (base) {
    holder = thumbFor(base);
  } else {
    // Nothing left to borrow a picture from: an empty slot beats mislabelling
    // the row as audio-only, which is what thumbFor infers from a bare object.
    holder = document.createElement('div');
    holder.className = 'p-thumb empty';
  }
  const badge = document.createElement('span');
  badge.className = 's-badge';
  badge.textContent = '▤';
  badge.title = 'Your saved stack';
  holder.appendChild(badge);
  card.appendChild(holder);

  const text = document.createElement('div');
  text.className = 'p-text';
  const name = document.createElement('span');
  name.className = 'p-name';
  name.textContent = k.name;
  const meta = document.createElement('span');
  meta.className = 'p-meta';
  const n = usable.length;
  const off = usable.filter((sl) => sl.enabled === false).length;
  meta.textContent = `stack · ${n} layer${n === 1 ? '' : 's'}${off ? ` · ${off} off` : ''}`;
  const tl = document.createElement('span');
  tl.className = 'p-tag';
  tl.textContent = stackChain(k);
  text.appendChild(name);
  text.appendChild(meta);
  text.appendChild(tl);
  card.appendChild(text);

  const tools = document.createElement('div');
  tools.className = 'card-tools';
  const ren = document.createElement('button');
  ren.textContent = '✎';
  ren.title = 'Rename';
  ren.onclick = (e) => { e.stopPropagation(); renameStack(k.id); };
  const del = document.createElement('button');
  del.textContent = '×';
  del.title = 'Delete this stack';
  del.onclick = (e) => { e.stopPropagation(); deleteStack(k.id); };
  tools.appendChild(ren);
  tools.appendChild(del);
  card.appendChild(tools);

  if (usable.length) card.appendChild(addLayerButton(k.id));
  card.onclick = () => pickFromList(k.id);
  return card;
}

function buildPresetList() {
  const list = $('preset-list');
  stopHoverAnim(); // the row that owned it is about to be discarded
  list.innerHTML = '';
  const presets = Object.values(G.schema.presets)
    .sort((a, b) => (famRank(a.family) - famRank(b.family)) || a.id.localeCompare(b.id));
  const q = ($('preset-search').value || '').toLowerCase();
  const matches = (p) => {
    if (!passesFilters(p)) return false;
    if (!q) return true;
    const hay = `${p.id} ${p.name} ${p.era} ${p.family} ${p.tagline || ''} ${(p.tags || []).join(' ')}`.toLowerCase();
    return hay.includes(q);
  };

  /* ↑/↓ walk this: the ids the eye can actually see, top to bottom. A favorite
     is rendered twice (its row at the top, and again inside its family) but is
     navigated once, at the first of the two, so a run down the list never
     re-renders the same preset. */
  const nav = [];
  const navSeen = new Set();
  const addNav = (pid) => { if (!navSeen.has(pid)) { navSeen.add(pid); nav.push(pid); } };

  /* Saved stacks lead, then saved customs: the things this user made, biggest
     arrangement first. Stacks stay out of `nav` on purpose - ↑/↓ auditions one
     aesthetic against the rest of your stack, and applying a saved stack
     replaces every layer, which is not something a held-down arrow key should
     be able to do. */
  const stackRows = G.stacks.filter((k) => {
    if (G.favOnly || G.customOnly) return false;
    if (!q) return true;
    return `${k.name} ${stackChain(k)}`.toLowerCase().includes(q);
  });
  if (stackRows.length) {
    const sl = document.createElement('div');
    sl.className = 'family-label stacks';
    sl.innerHTML = `▤ MY STACKS <span class="count">${stackRows.length}</span>`;
    list.appendChild(sl);
    for (const k of stackRows) list.appendChild(stackCard(k));
  }

  if (G.stackOnly) {
    G.navOrder = [];
    if (!stackRows.length) {
      const empty = document.createElement('div');
      empty.className = 'list-empty';
      empty.textContent = 'No stacks match.';
      const btn = document.createElement('button');
      btn.textContent = 'Clear filters';
      btn.onclick = clearFilters;
      empty.appendChild(document.createElement('br'));
      empty.appendChild(btn);
      list.appendChild(empty);
    }
    return;
  }

  /* Saved customs sit above the stock library: they are this user's too. */
  const customRows = G.customs.filter((c) => {
    if (G.favOnly) return false;
    if (!G.schema.presets[c.base]) return false;   // base preset went away
    if (G.filterFamilies.size && !G.filterFamilies.has(G.schema.presets[c.base].family)) return false;
    if (G.filterEra && decadeOf(G.schema.presets[c.base]) !== G.filterEra) return false;
    if (!q) return true;
    return `${c.name} ${presetName(c.base)}`.toLowerCase().includes(q);
  });
  if (customRows.length) {
    const cl = document.createElement('div');
    cl.className = 'family-label customs';
    cl.innerHTML = `✎ MY AESTHETICS <span class="count">${customRows.length}</span>`;
    list.appendChild(cl);
    for (const c of customRows) { list.appendChild(customCard(c)); addNav(c.id); }
  }

  if (G.customOnly) {
    G.navOrder = nav;
    if (!customRows.length) {
      const empty = document.createElement('div');
      empty.className = 'list-empty';
      empty.textContent = 'No custom aesthetics match.';
      const btn = document.createElement('button');
      btn.textContent = 'Clear filters';
      btn.onclick = clearFilters;
      empty.appendChild(document.createElement('br'));
      empty.appendChild(btn);
      list.appendChild(empty);
    }
    return;
  }

  // Favorites lead the list (unless the ★ chip already narrows to them, which
  // would render every row twice).
  const favRows = G.favOnly ? [] : presets.filter((p) => G.favs.has(p.id) && matches(p));
  if (favRows.length) {
    const fl = document.createElement('div');
    fl.className = 'family-label favorites';
    fl.innerHTML = `★ FAVORITES <span class="count">${favRows.length}</span>`;
    list.appendChild(fl);
    for (const p of favRows) { list.appendChild(presetCard(p)); addNav(p.id); }
  }

  let family = null;
  let familyBody = null;
  let familyHidden = false;
  let shown = favRows.length + customRows.length + stackRows.length;
  for (const p of presets) {
    if (!matches(p)) continue;
    shown++;
    if (p.family !== family) {
      family = p.family;
      const count = presets.filter((x) => x.family === family && matches(x)).length;
      const fl = document.createElement('div');
      fl.className = 'family-label clickable';
      const isCollapsed = !q && G.collapsed.has(family);
      fl.innerHTML = `<span class="chev">${isCollapsed ? '▸' : '▾'}</span> ${family.toUpperCase()} <span class="count">${count}</span>`;
      const fam = family;
      fl.onclick = () => {
        if (G.collapsed.has(fam)) G.collapsed.delete(fam);
        else G.collapsed.add(fam);
        saveStore();
        buildPresetList();
      };
      list.appendChild(fl);
      familyBody = document.createElement('div');
      familyBody.className = 'family-body';
      if (isCollapsed) familyBody.style.display = 'none';
      familyHidden = isCollapsed;
      list.appendChild(familyBody);
    }
    (familyBody || list).appendChild(presetCard(p));
    if (!familyHidden) addNav(p.id);   // a collapsed family is not on screen
  }
  G.navOrder = nav;

  if (!shown) {
    const empty = document.createElement('div');
    empty.className = 'list-empty';
    empty.textContent = 'No aesthetics match.';
    if (anyFilterActive()) {
      const btn = document.createElement('button');
      btn.textContent = 'Clear filters';
      btn.onclick = clearFilters;
      empty.appendChild(document.createElement('br'));
      empty.appendChild(btn);
    }
    list.appendChild(empty);
  }
}

/* ── layers panel ────────────────────────────────────────────────────
   One row per layer in processing order, top of the list rendered first. The
   selected row is the one whose knobs fill the rest of the pane, which is what
   makes this an accordion without needing N copies of the parameter UI. */
function layerLabel(l) {
  if (!l.presetId) return 'Empty layer';
  if (l.customId) return customName(l.customId);
  const p = G.schema && G.schema.presets[l.presetId];
  return p ? p.name : l.presetId;
}

function layerSub(l) {
  const bits = [];
  if (l.variant) bits.push(l.variant);
  const n = Object.keys(l.sets || {}).length;
  if (n) bits.push(`${n} tweak${n === 1 ? '' : 's'}`);
  if (l.intensity !== 1) bits.push(`int ${l.intensity.toFixed(2)}`);
  if (l.texture !== 1) bits.push(`tex ${l.texture.toFixed(2)}`);
  return bits.join(' · ');
}

function buildLayersPanel() {
  const panel = $('layers-panel');
  const list = $('layers-list');
  const layers = state.layers || [];
  const many = layers.length > 1;
  // With one layer this is just noise - the pane below already names it.
  panel.classList.toggle('hidden', !many);
  document.body.classList.toggle('has-layers', liveLayers(state).length > 0);
  if (!many) return;

  const live = liveLayers(state).length;
  $('lp-hint').textContent = `${live} of ${layers.length} rendering, in order`;
  // Nothing to save until at least one layer has an aesthetic in it.
  $('btn-save-stack').classList.toggle('hidden', !captureStackLayers().length);

  /* Which saved stack this arrangement came from, and whether it still matches.
     Same honesty as a custom's "· edited": the panel never claims you are
     looking at the saved version when you are not. */
  const worn = $('lp-stack');
  worn.classList.toggle('hidden', !state.stackId);
  if (state.stackId) {
    worn.textContent = `▤ ${stackName(state.stackId)}${stackDrifted() ? ' · edited' : ''}`;
    worn.classList.toggle('drifted', stackDrifted());
  }
  list.innerHTML = '';

  layers.forEach((l, i) => {
    const row = document.createElement('div');
    row.className = 'layer-row'
      + (i === state.activeLayer ? ' sel' : '')
      + (l.enabled ? '' : ' off');
    row.draggable = true;
    row.dataset.lid = l.lid;

    const grip = document.createElement('span');
    grip.className = 'l-grip';
    grip.textContent = '⣿';
    grip.title = 'Drag to change the order effects are applied in';
    row.appendChild(grip);

    const check = document.createElement('input');
    check.type = 'checkbox';
    check.className = 'l-check';
    check.checked = l.enabled;
    check.title = l.enabled ? 'Skip this layer' : 'Include this layer';
    check.onclick = (e) => {
      e.stopPropagation();
      l.enabled = check.checked;
      buildLayersPanel();
      schedulePreview();
    };
    row.appendChild(check);

    const num = document.createElement('span');
    num.className = 'l-num';
    num.textContent = String(i + 1);
    row.appendChild(num);

    const text = document.createElement('div');
    text.className = 'l-text';
    const name = document.createElement('span');
    name.className = 'l-name';
    name.textContent = layerLabel(l);
    text.appendChild(name);
    const sub = layerSub(l);
    if (sub) {
      const s = document.createElement('span');
      s.className = 'l-sub';
      s.textContent = sub;
      text.appendChild(s);
    }
    row.appendChild(text);

    const drop = document.createElement('button');
    drop.className = 'l-drop';
    drop.textContent = '×';
    drop.title = 'Remove this layer';
    drop.onclick = (e) => { e.stopPropagation(); removeLayer(i); };
    row.appendChild(drop);

    row.onclick = () => selectLayer(i);
    wireLayerDrag(row, i);
    list.appendChild(row);
  });

  // Each layer is a full encode, so a deep stack is worth warning about before
  // someone starts a feature-length export and wonders why it never ends.
  const warn = $('lp-warn');
  const slow = live >= 3;
  warn.classList.toggle('hidden', !slow);
  if (slow) {
    warn.textContent = `${live} layers means ${live} full render passes - `
      + 'exports take roughly that many times as long.';
  }
}

let dragFrom = -1;

function wireLayerDrag(row, index) {
  row.addEventListener('dragstart', (e) => {
    dragFrom = index;
    row.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    // Firefox and Chromium both want *something* set or the drag never starts.
    try { e.dataTransfer.setData('text/plain', String(index)); } catch (_) {}
  });
  row.addEventListener('dragend', () => {
    row.classList.remove('dragging');
    for (const r of $('layers-list').children) r.classList.remove('drag-over');
  });
  row.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    row.classList.add('drag-over');
  });
  row.addEventListener('dragleave', () => row.classList.remove('drag-over'));
  row.addEventListener('drop', (e) => {
    e.preventDefault();
    row.classList.remove('drag-over');
    if (dragFrom < 0 || dragFrom === index) return;
    moveLayer(dragFrom, index);
    dragFrom = -1;
  });
}

function moveLayer(from, to) {
  const layers = state.layers;
  if (from < 0 || to < 0 || from >= layers.length || to >= layers.length) return;
  const [moved] = layers.splice(from, 1);
  layers.splice(to, 0, moved);
  // Keep the selection on the layer the user was holding, wherever it landed.
  state.activeLayer = to;
  syncSelection();
  buildLayersPanel();
  buildParamPane();
  schedulePreview();
}

function selectLayer(i) {
  if (i === state.activeLayer) return;
  state.activeLayer = i;
  buildLayersPanel();
  buildParamPane();
  syncSelection();
  renderTabs();
}

function removeLayer(i) {
  const layers = state.layers;
  if (layers.length <= 1) {
    // The last one becomes empty rather than vanishing: a session always has a
    // layer to put the next pick into.
    layers[0] = newLayer();
    state.activeLayer = 0;
  } else {
    layers.splice(i, 1);
    state.activeLayer = Math.min(state.activeLayer, layers.length - 1);
  }
  buildLayersPanel();
  buildParamPane();
  syncSelection();
  renderTabs();
  schedulePreview();
}

/* Append `pid` as a new layer on top and select it. The same aesthetic can be
   stacked on itself - two passes of the same tape is a real thing. */
function addLayer(pid, opts = {}) {
  if (!pid) return;
  if (isStackId(pid)) { appendStack(pid, opts); return; }
  const custom = isCustomId(pid) ? customById(pid) : null;
  if (isCustomId(pid) && !custom) return;   // a row for a custom that just went away
  state.layers.push(custom ? layerFromCustom(custom) : newLayer({ presetId: pid }));
  state.activeLayer = state.layers.length - 1;
  state.stackId = null;   // the arrangement has grown past the saved one
  buildLayersPanel();
  buildParamPane();       // repaints the master dials onto the new layer
  syncSelection();
  renderTabs();
  schedulePreview(true, opts.previewDelay);
}

/* Collapse the stack to this one aesthetic - what Enter does while arrowing. */
function applyOnly(id) {
  state.layers = [newLayer()];
  state.activeLayer = 0;
  selectById(id);
  buildLayersPanel();
}

function selectPreset(pid, opts = {}) {
  state.presetId = pid;
  state.customId = null;   // picking a stock preset leaves any custom behind
  state.stackId = null;    // and the arrangement is no longer the saved one
  state.variant = null;
  state.sets = {};
  state.events = [];
  syncSelection();       // the rows themselves have not changed, only which one is lit
  renderTabs();          // the tab shows which aesthetic the clip is wearing
  buildParamPane();
  buildLayersPanel();
  schedulePreview(true, opts.previewDelay);
}

/* One entry point for both kinds of row, so ↑/↓ does not care which it lands on. */
function selectById(id, opts = {}) {
  if (isStackId(id)) applyStack(id, opts);
  else if (isCustomId(id)) applyCustom(id, opts);
  else selectPreset(id, opts);
}

/* ── guarding a pick ─────────────────────────────────────────────────
   Picking from the list writes over the selected layer. Usually that costs
   nothing and has to stay instant - swapping one untouched preset for another
   is exactly what arrowing the list is for. But a layer you have actually
   worked on is worth a question first, because there is no undo.

   The predicate is the whole design: ask only when something would be lost.
   Once a swap has happened the fresh layer carries no work, so the next arrow
   press is silent again. */
function layerHasWork(l) {
  if (!l || !l.presetId) return false;
  return Boolean(l.customId)
    || Boolean(l.variant)
    || Object.keys(l.sets || {}).length > 0
    || (l.events || []).length > 0
    || l.intensity !== 1
    || l.texture !== 1;
}

/* Applying a saved stack, or committing one aesthetic with Enter, replaces
   every layer - so the stakes are the whole arrangement, not one layer. */
function sessionHasWork(sess = state) {
  const filled = (sess.layers || []).filter((l) => l.presetId);
  return filled.length > 1 || filled.some(layerHasWork);
}

function pickLabel(id) {
  if (isStackId(id)) return stackName(id);
  if (isCustomId(id)) return customName(id);
  return presetName(id);
}

/* What the selected layer is about to lose, in words. */
function describeLayerWork(l) {
  const bits = [];
  const n = Object.keys(l.sets || {}).length;
  if (n) bits.push(`${n} tweak${n === 1 ? '' : 's'}`);
  const ne = (l.events || []).length;
  if (ne) bits.push(`${ne} timeline edit${ne === 1 ? '' : 's'}`);
  if (l.variant) bits.push(`the ${l.variant} variant`);
  if (l.intensity !== 1) bits.push(`intensity ${l.intensity.toFixed(2)}`);
  if (l.texture !== 1) bits.push(`texture ${l.texture.toFixed(2)}`);
  if (!bits.length) return '';
  if (bits.length === 1) return bits[0];
  return `${bits.slice(0, -1).join(', ')} and ${bits[bits.length - 1]}`;
}

/* Open the same clip again in its own tab, wearing the thing that was just
   picked - the way out of the dialog that loses nothing at all. */
function openInNewTab(id) {
  const src = activeSession();
  if (!src) return;
  const sess = newSession(src.file);
  sess.previewT = src.previewT;
  G.sessions.push(sess);
  activateSession(sess.id);   // `state` now points at the new tab
  selectById(id);             // a fresh session: one empty layer, nothing to guard
}

/* Every pick that comes from the browse list goes through here - clicks and
   ↑/↓ alike, so both obey the same rule. */
async function pickFromList(id, opts = {}) {
  if (!id) return;
  const stack = isStackId(id);
  const atRisk = stack ? sessionHasWork() : layerHasWork(activeLayer(state));
  if (!atRisk) { selectById(id, opts); return; }

  const layer = activeLayer(state);
  const lost = describeLayerWork(layer);
  const many = (state.layers || []).filter((l) => l.presetId).length;
  // A layer can be worth protecting purely because it is a saved custom, with
  // nothing moved on top of it - so there is no list of tweaks to recite.
  const carries = lost
    ? `${layerLabel(layer)} carries ${lost}.`
    : `${layerLabel(layer)} is one of your saved aesthetics.`;
  const choice = await askChoice({
    title: stack ? `Apply “${pickLabel(id)}” over this stack?` : `Replace ${layerLabel(layer)}?`,
    sub: stack
      ? `This tab has ${many} layer${many === 1 ? '' : 's'} set up. Applying a saved stack `
        + 'replaces all of them.'
      : `${carries} Picking ${pickLabel(id)} writes over it, `
        + 'and the other layers stay as they are.',
    choices: [
      { key: 'tab', label: 'Open in a new tab', title: 'Leave this tab exactly as it is' },
      { key: 'go', label: stack ? 'Replace stack' : 'Replace layer', className: 'accent' },
      { key: null, label: 'Cancel' },
    ],
  });
  if (choice === 'tab') openInNewTab(id);
  else if (choice === 'go') selectById(id, opts);
}

/* Enter collapses everything to one aesthetic, so it asks about the whole
   arrangement rather than the selected layer. */
async function pickOnly(id) {
  if (!id) return;
  if (!sessionHasWork()) { applyOnly(id); return; }
  const many = (state.layers || []).filter((l) => l.presetId).length;
  const layer = activeLayer(state);
  const lost = describeLayerWork(layer);
  const choice = await askChoice({
    title: `Commit ${pickLabel(id)} on its own?`,
    // With a single layer there is nothing to drop - what is at stake is the
    // work sitting on that one layer.
    sub: many > 1
      ? `This drops the other ${many - 1} layer${many === 2 ? '' : 's'} and every tweak on them.`
      : `${lost ? `${layerLabel(layer)} carries ${lost}` : `${layerLabel(layer)} is one of your saved aesthetics`}, `
        + 'and this writes over it.',
    choices: [
      { key: 'tab', label: 'Open in a new tab', title: 'Leave this tab exactly as it is' },
      { key: 'go', label: 'Drop the rest', className: 'accent' },
      { key: null, label: 'Cancel' },
    ],
  });
  if (choice === 'tab') openInNewTab(id);
  else if (choice === 'go') applyOnly(id);
}

/* Moving the highlight is a class flip, not a rebuild of 192 rows - which is
   what makes holding ↓ feel like scrubbing rather than stuttering. A favorited
   preset owns two rows and both light up. */
function syncSelection() {
  const id = selectionId();
  for (const card of $('preset-list').querySelectorAll('.preset-card')) {
    const pid = card.dataset.pid;
    card.classList.toggle('sel', pid === id && !isStackId(pid));
    card.classList.toggle('worn', isStackId(pid) && pid === state.stackId);
  }
}

/* ↑/↓ step through the visible list. Hold the key and the whole list runs past
   the player; the preview is debounced by this much, so only the row you
   actually settle on is rendered. */
const NAV_PREVIEW_MS = 260;

async function navPreset(delta) {
  const order = G.navOrder;
  if (!order.length) return;
  const at = order.indexOf(selectionId());
  // Nothing picked yet (or the current pick is filtered out of view): enter the
  // list from whichever end the key points at.
  const next = at < 0
    ? (delta > 0 ? 0 : order.length - 1)
    : Math.max(0, Math.min(order.length - 1, at + delta));
  if (order[next] === selectionId()) return;   // already against the end
  // Same guard as a click: a layer carrying work asks first. Cancelling leaves
  // the highlight where it was, and scrolling to it is a no-op.
  await pickFromList(order[next], { previewDelay: NAV_PREVIEW_MS });
  const card = $('preset-list').querySelector('.preset-card.sel');
  if (card) card.scrollIntoView({ block: 'nearest' });
}

// ── parameter pane ──────────────────────────────────────────────────
function chainWithKeys(chain) {
  const counts = {};
  return chain.map(([eid, params]) => {
    counts[eid] = (counts[eid] || 0) + 1;
    return { eid, key: counts[eid] === 1 ? eid : `${eid}#${counts[eid]}`, params };
  });
}

function variantOverrides() {
  if (!state.variant) return {};
  const p = G.schema.presets[state.presetId];
  const v = p.variants.find((x) => x.id === state.variant);
  return v ? { ...v.video, ...v.audio } : {};
}

function clearParamPane() {
  $('preset-title').textContent = '-';
  $('preset-sub').textContent = '';
  $('btn-fav').classList.add('hidden');
  $('btn-save-custom').classList.add('hidden');
  $('override-row').classList.add('hidden');
  $('variant-row').innerHTML = '';
  $('param-list').innerHTML = '<div class="hint">Pick an aesthetic on the left.</div>';
}

function buildParamPane() {
  // A layer can be emptied - remove the last one and it stays as an empty slot
  // waiting for the next pick - so this is reachable with nothing selected.
  if (!state.presetId || !G.schema.presets[state.presetId]) { clearParamPane(); return; }
  // The dials belong to the selected layer, so they move with it.
  syncMasterDials();
  const p = G.schema.presets[state.presetId];
  const c = state.customId ? customById(state.customId) : null;
  $('preset-title').textContent = c ? c.name : p.name;
  $('preset-title').title = c ? `Custom aesthetic based on ${p.name}\n\n${p.desc}` : p.desc;
  $('preset-sub').textContent = c
    ? `custom · from ${p.name}${customDrifted() ? ' · edited' : ''}`
    : `${p.era} · ${p.family}`;
  syncFavButton();
  syncOverrideRow();

  const vrow = $('variant-row');
  vrow.innerHTML = '';
  if (p.variants.length) {
    const base = document.createElement('span');
    base.className = 'variant-pill' + (state.variant === null ? ' sel' : '');
    base.textContent = 'standard';
    base.onclick = () => { state.variant = null; buildParamPane(); schedulePreview(); };
    vrow.appendChild(base);
    for (const v of p.variants) {
      const pill = document.createElement('span');
      pill.className = 'variant-pill' + (state.variant === v.id ? ' sel' : '');
      pill.textContent = v.name;
      pill.title = v.desc;
      pill.onclick = () => { state.variant = v.id; buildParamPane(); schedulePreview(); };
      vrow.appendChild(pill);
    }
  }

  const holder = $('param-list');
  holder.innerHTML = '';
  const vo = variantOverrides();
  const sections = state.audioSource
    ? [['SOUND', p.audio]]                 // the video chain cannot apply here
    : [['PICTURE', p.video], ['SOUND', p.audio]];
  if (state.audioSource && p.video.length) {
    const note = document.createElement('div');
    note.className = 'audio-note';
    note.textContent = `Audio source - this preset's ${p.video.length} picture effects are not applied.`;
    holder.appendChild(note);
  }
  for (const [label, chain] of sections) {
    if (!chain.length) continue;
    const cl = document.createElement('div');
    cl.className = 'chain-label';
    cl.textContent = label;
    holder.appendChild(cl);
    for (const entry of chainWithKeys(chain)) {
      holder.appendChild(effectCard(entry, vo));
    }
  }
}

/* The "N tweaks · Reset all" strip under the master dials: visible only while
   manual --set overrides exist on this session. */
function syncOverrideRow() {
  const n = Object.keys(state.sets).length;
  $('override-row').classList.toggle('hidden', n === 0);
  if (n) $('override-count').textContent = `${n} manual tweak${n === 1 ? '' : 's'}`;
  syncPresetSub();
}

function effectCard({ eid, key, params }, variantOv) {
  const eff = G.schema.effects[eid];
  const card = document.createElement('div');
  card.className = 'effect-card';
  /* Effects that burn words into the picture - dates, channel labels, tape
     counters - open on sight. Their text is the first thing anyone wants to
     change, and it was previously two clicks deep in a collapsed card. */
  const hasText = eff.params.some((p) => p.kind === 'str');
  if (hasText) card.classList.add('open');
  const head = document.createElement('div');
  head.className = 'effect-head';
  const tweaked = Object.keys(state.sets).some((s) => s.startsWith(`${key}.`));
  head.innerHTML = `<span class="chev">▶</span><span>${eff.label}</span>`
    + (hasText ? '<span class="e-text" title="Burns text into the picture - editable below">Aa</span>' : '')
    + (tweaked ? '<span class="e-tweaks" title="Has manual tweaks"></span>' : '');

  /* Every effect carries an `enabled` flag, and it belongs in the header rather
     than buried in the parameter list: it is the one control that decides
     whether any of the others matter. Some effects have no dial that reaches
     nothing - a Risograph is its ink pair, a projection surface is its material
     - so this is the only way to hear or see the chain without them. */
  const onPath = `${key}.enabled`;
  const onBase = onPath in variantOv ? variantOv[onPath]
    : ('enabled' in params ? params.enabled : true);
  const isOn = onPath in state.sets ? state.sets[onPath] : onBase;
  card.classList.toggle('off', !isOn);
  const power = document.createElement('input');
  power.type = 'checkbox';
  power.className = 'e-power';
  power.checked = !!isOn;
  power.title = isOn ? `Switch ${eff.label} off for this layer` : `Switch ${eff.label} back on`;
  power.onclick = (e) => e.stopPropagation();      // the header row toggles open
  power.onchange = () => {
    if (power.checked === onBase) delete state.sets[onPath];
    else state.sets[onPath] = power.checked;
    card.classList.toggle('off', !power.checked);
    power.title = power.checked ? `Switch ${eff.label} off for this layer` : `Switch ${eff.label} back on`;
    syncOverrideRow();
    schedulePreview();
  };
  head.appendChild(power);
  attachTip(head, () => ({
    title: eff.label,
    desc: eff.desc || '',
    facts: [`${eff.params.length} parameter${eff.params.length === 1 ? '' : 's'}`,
            eff.kind === 'filepass' ? 'real codec pass' : eff.kind],
    path: `${key}.<param>`,
  }));
  head.onclick = () => card.classList.toggle('open');
  card.appendChild(head);
  const body = document.createElement('div');
  body.className = 'effect-body';

  let lastGroup = null;
  for (const prm of eff.params) {
    if (prm.name === 'enabled') continue;   // it lives in the header
    const path = `${key}.${prm.name}`;
    const baseVal = path in variantOv ? variantOv[path] : (prm.name in params ? params[prm.name] : prm.default);
    const curVal = path in state.sets ? state.sets[path] : baseVal;
    if (prm.group && prm.group !== lastGroup) {
      lastGroup = prm.group;
      const g = document.createElement('div');
      g.className = 'pgroup';
      g.textContent = prm.group.toUpperCase();
      body.appendChild(g);
    }
    body.appendChild(paramRow(path, prm, baseVal, curVal));
  }
  card.appendChild(body);
  return card;
}

function paramRow(path, prm, baseVal, curVal) {
  const row = document.createElement('div');
  // Free text and date pickers need more width than a 92px label leaves them,
  // so those rows put the label on its own line and give the field the pane.
  row.className = 'prow' + (prm.kind === 'str' ? ' stacked' : '')
    + (path in state.sets ? ' overridden' : '');
  const label = document.createElement('label');
  label.textContent = prm.label;
  row.appendChild(label);
  attachTip(row, () => paramTip(path, prm, baseVal));

  /* Numbers are pinned to the precision the row prints before they are stored,
     so what a row says is what the engine is handed. Everything else goes
     through untouched. */
  const norm = (v) => (prm.kind === 'float' || prm.kind === 'int') ? quantize(v, prm) : v;

  const commit = (rawVal) => {
    const val = norm(rawVal);
    // Landing back on the preset's own number clears the override rather than
    // pinning a rounded copy of it next to it.
    if (val === norm(baseVal) || String(val) === String(baseVal)) delete state.sets[path];
    else state.sets[path] = val;
    row.classList.toggle('overridden', path in state.sets);
    syncOverrideRow();
    schedulePreview();
  };

  if (prm.kind === 'float' || prm.kind === 'int') {
    const slider = document.createElement('input');
    slider.type = 'range';
    slider.className = 'range-fill';
    slider.min = prm.lo; slider.max = prm.hi;
    slider.step = sliderStep(prm);
    slider.value = curVal;
    paintRange(slider);
    const val = document.createElement('span');
    val.className = 'pval';
    const paint = (v) => {
      val.textContent = fmtVal(v, prm);
      // The one thing the thumb cannot show: on a wide range a live value can
      // park against the same end stop as a dead one.
      row.classList.toggle('at-min', quantize(v, prm) <= prm.lo);
      paintRange(slider);
    };
    paint(curVal);
    slider.oninput = () => paint(parseFloat(slider.value));
    slider.onchange = () => commit(parseFloat(slider.value));
    /* The grid is finer than a keypress wants to move - it has to be, to hold
       the numbers presets actually author - so the arrows keep their own nudge
       of a 200th of the range, which is the travel they always had. */
    slider.addEventListener('keydown', (e) => {
      const dir = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1 }[e.key];
      if (!dir) return;
      e.preventDefault();
      const nudge = prm.kind === 'int' ? 1 : (prm.hi - prm.lo) / 200;
      const next = quantize(Math.min(prm.hi, Math.max(prm.lo, parseFloat(slider.value) + dir * nudge)), prm);
      if (next === parseFloat(slider.value)) return;
      slider.value = next;
      paint(next);
      commit(next);
    });
    row.appendChild(slider);
    row.appendChild(val);
  } else if (prm.kind === 'bool') {
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = !!curVal;
    cb.onchange = () => commit(cb.checked);
    row.appendChild(cb);
    row.appendChild(document.createElement('span')).className = 'grow';
  } else if (prm.kind === 'enum') {
    const sel = document.createElement('select');
    for (const c of prm.choices) {
      const o = document.createElement('option');
      o.value = c; o.textContent = c.replaceAll('_', ' ');
      if (c === curVal) o.selected = true;
      sel.appendChild(o);
    }
    sel.onchange = () => commit(sel.value);
    row.appendChild(sel);
  } else if (prm.kind === 'str' && prm.fmt === 'datetime') {
    /* The engine wants 'YYYY-MM-DD HH:MM:SS' and raises on anything else, which
       is a rough way to find out you mistyped a date three minutes into an
       export. A real picker cannot produce an unparseable value. */
    const inp = document.createElement('input');
    inp.type = 'datetime-local';
    inp.step = 1;
    inp.value = String(curVal).trim().replace(' ', 'T');
    inp.onchange = () => { if (inp.value) commit(inp.value.replace('T', ' ')); };
    row.appendChild(inp);
  } else if (prm.kind === 'str') {
    const inp = document.createElement('input');
    inp.type = 'text';
    inp.value = String(curVal);
    inp.spellcheck = false;
    if (prm.fmt === 'clock') inp.placeholder = 'H:MM:SS';
    inp.onchange = () => commit(inp.value);
    row.appendChild(inp);
  }

  const reset = document.createElement('button');
  reset.className = 'reset-mini';
  reset.textContent = '↺';
  reset.title = 'Reset to preset value';
  reset.onclick = () => { delete state.sets[path]; buildParamPane(); schedulePreview(); };
  row.appendChild(reset);
  return row;
}

/* ── slider precision ───────────────────────────────────────────────
   A range input snaps its value onto `min + n*step`, so a step coarser than the
   numbers presets actually author makes the thumb sit somewhere the engine is
   not. Dropouts run 0 to 60 events/s, which used to give a step of 0.3: a
   preset authored at 0.4 landed the thumb on 0.3, hard against the left stop
   and indistinguishable from a parameter switched off - while the engine went
   on rendering 0.4. Somebody saved that as a custom aesthetic, read the knob as
   zero and got dropouts through a whole export.

   The grid, the readout and the number written into `sets` all come from here,
   so they cannot drift apart again. tests/test_renderer.js walks the library
   and holds them to it. */
function valueDecimals(prm, v) {
  if (prm.kind === 'int') return 0;
  // Ranges this narrow (setup level, black crush, keystone) are all detail; two
  // decimals would flatten most of the travel to the same printed number.
  if (Math.abs(prm.hi - prm.lo) < 0.5) return 3;
  return Math.abs(v) >= 100 ? 0 : 2;
}

/* One grid for every float, fine enough for the most precise number anyone
   authors (three decimals, in tone.lift at 0.015) whatever the range around it.
   Deriving it from the range is what went wrong before: any rule that scales
   with `hi - lo` is coarse exactly where the range is widest, which is exactly
   where a value near the bottom has no other way to show itself. */
function sliderStep(prm) {
  if (prm.kind === 'int') return 1;
  return prm.step || 0.001;
}

/* A value pinned to what the row can print, so a slider never holds 0.4025
   under a readout that says 0.40. */
function quantize(v, prm) {
  const n = typeof v === 'number' ? v : parseFloat(v);
  if (!Number.isFinite(n)) return v;
  if (prm.kind === 'int') return Math.round(n);
  return parseFloat(n.toFixed(valueDecimals(prm, n)));
}

function fmtVal(v, prm) {
  if (typeof v !== 'number') return String(v);
  const s = prm.kind === 'int' ? String(v) : v.toFixed(valueDecimals(prm, v));
  return prm.unit ? `${s}${prm.unit === '°' ? '' : ' '}${prm.unit}` : s;
}

// ── preview rendering ───────────────────────────────────────────────
let previewTimer = null;
/* `immediate` means "render even with auto off" - a deliberate pick, not a knob
   twiddle. `delayMs` overrides the wait: keyboard navigation passes a longer one
   so running down the list does not start a render per row. */
function schedulePreview(immediate = false, delayMs = null) {
  if (!state.file || !liveLayers(state).length) return;
  if (!G.autoPreview && !immediate) return;
  clearTimeout(previewTimer);
  previewTimer = setTimeout(runPreview, delayMs != null ? delayMs : (immediate ? 40 : 550));
}

/* The stack as the engine wants it: bottom layer first, disabled ones dropped.
   Only render-affecting fields, because this is also what the preview cache is
   keyed on - anything cosmetic in here would cost a re-render for nothing. */
function layerSpec(sess = state) {
  return liveLayers(sess).map((l) => ({
    preset: l.presetId,
    variant: l.variant || null,
    sets: l.sets || {},
    events: l.events || [],
    seed: l.seed,
    intensity: l.intensity,
    texture: l.texture,
  }));
}

/* ── the paused player's first look ──────────────────────────────────
   Frame 0 of the very same render, which the engine can produce for about a
   tenth of the clip's cost because it does one frame of pixel work instead of
   ninety. Only while paused: a still over a running loop would just be a
   flicker, and pausing is already what you do when you are working on a look
   rather than watching one. */
function showStill(src, exact) {
  const img = $('still-frame');
  img.src = `file://${src}?t=${Date.now()}`;
  img.classList.remove('hidden');
  $('player-wrap').classList.add('has-still');
  $('player-empty').classList.add('hidden');
  const chip = $('still-chip');
  chip.classList.remove('hidden');
  chip.classList.toggle('provisional', !exact);
  chip.textContent = exact ? 'still · frame 1' : 'still · frame 1 · settles when the clip lands';
  chip.title = exact
    ? 'Frame 1 of the clip being rendered, exactly as it will look.'
    : 'This chain has a real codec pass, which needs a clip rather than one '
      + 'frame. The picture will shift slightly once the clip finishes.';
}

function hideStill() {
  $('still-frame').classList.add('hidden');
  $('still-frame').removeAttribute('src');
  $('still-chip').classList.add('hidden');
  $('player-wrap').classList.remove('has-still');
}

async function runPreview() {
  if (!state.file || !liveLayers(state).length) return;
  const sess = state;                    // this render belongs to THIS tab
  const jobId = `job${++G.jobCounter}`;
  G.activeJob = jobId;
  sess.previewJob = jobId;
  hideStill();                           // whatever is up belongs to the last render
  showRenderOverlay(true, 'rendering preview…', 0);
  // The tick plan depends on the same state this render does, so it refreshes
  // alongside - fire and forget, the strip must never delay the preview.
  refreshTimeline();
  const req = {
    jobId,
    input: state.file.path,
    layers: layerSpec(),
    presetId: state.presetId,
    variant: state.variant,
    sets: state.sets,
    seed: state.seed,
    intensity: state.intensity,
    texture: state.texture,
    start: state.previewT,
    duration: G.duration,
    scale: G.scale,
    crf: 19,
    audioSource: state.audioSource,
    videoOnly: $('exp-video-only').checked,
    audioOnly: $('exp-audio-only').checked,
  };
  /* Alongside the clip rather than before it: the still is short enough that
     racing it costs the clip almost nothing, and serialising them would push
     the clip back by the whole still. Whichever lands first paints - and on a
     cache hit that is the clip, so the still has to know it has been beaten by
     *this* render rather than by the one still on screen from last time. */
  let clipPainted = false;
  if (G.paused && !state.audioSource) {
    window.aesth.still(req).then((s) => {
      if (clipPainted || sess.previewJob !== jobId || sess.id !== G.activeId) return;
      showStill(s.output, s.exact);
    }).catch(() => { /* the clip is the real answer; a lost still is not worth a message */ });
  }

  try {
    const [treated, original] = await Promise.all([
      window.aesth.preview(req),
      state.originalSrc && state.originalT === state.previewT
        ? Promise.resolve({ output: state.originalSrc })
        : window.aesth.snippet({ input: state.file.path, start: state.previewT, duration: G.duration, scale: G.scale, audioSource: state.audioSource }),
    ]);
    // Record the result on its own session even if the user has moved on, so
    // coming back to that tab costs nothing - but only while this is still the
    // render that tab last asked for. A knob moved mid-render starts a newer
    // one, and if that newer one is a cache hit it answers immediately while
    // this one is still going; landing afterwards and writing over it would
    // leave the tab holding a render of settings the user has already left,
    // which is what you would then get back on returning to it.
    if (sess.previewJob !== jobId) return;
    sess.treatedSrc = treated.output;
    sess.originalSrc = original.output;
    sess.originalT = req.start;
    if (sess.id !== G.activeId) return;  // a different tab is on screen now
    if (G.activeJob !== jobId) return;   // superseded by a newer render
    $('player-empty').classList.add('hidden');
    clipPainted = true;
    setVideo(videoA, treated.output);
    setVideo(videoB, original.output);
  } catch (err) {
    if (String(err.message || '').includes('superseded')) return;
    reportFailure('Preview', err);
  } finally {
    if (G.activeJob === jobId) showRenderOverlay(false);
    refreshCacheInfo();
  }
}

function setVideo(el, src) {
  const t = el === videoA ? (videoB.currentTime || 0) : (videoA.currentTime || 0);
  el.src = `file://${src}?t=${Date.now()}`;
  el.load();
  el.onloadeddata = () => {
    // The clip is here, so the stand-in has done its job. Swapped on load
    // rather than on request, so there is never a blank frame between them.
    if (el === videoA) hideStill();
    try { el.currentTime = Math.min(t, el.duration - 0.05) || 0; } catch (_) {}
    el.muted = el === videoB ? true : G.muted;
    // A held pause survives re-renders: the new take arrives on a still frame
    // rather than restarting the loop under the user.
    if (!G.paused) el.play().catch(() => {});
  };
}

/* ── filmstrip timeline ──────────────────────────────────────────────
   A strip of source-frame thumbnails under the player spanning the whole clip,
   with a colored tick wherever the engine plans discrete damage. Read-only for
   now: ticks explain themselves on hover and clicking the strip moves the
   preview window. The editor comes next, so the seams stay clean - fetching is
   separated from painting, and the cached plan is the aesth:events result
   exactly as the engine sent it. */

/* One color per event kind. A kind this build has never heard of falls back to
   the dim ink rather than crashing the paint: the engine grows new kinds, and
   the strip has to survive every one of them. */
const TICK_COLORS = {
  dropout: '#f4b64e',
  transport_glitch: '#8fb4ff',
  transport_lock: '#f06a72',
  tracking_storm: '#6fd7b8',
  skew_tear: '#a88df8',
};

/* CSS position only: scrubbing moves the head many times a second, and paying
   a repaint of thumbnails and ticks for a pointer move would make the slider
   feel like wading. */
function syncTimelinePlayhead() {
  const total = state.file && state.file.duration;
  if (!total) return;
  const left = (state.previewT / total) * 100;
  $('strip-playhead').style.left = `${left}%`;
  $('strip-window').style.left = `${left}%`;
  $('strip-window').style.width = `${(Math.min(G.duration, total) / total) * 100}%`;
}

/* The frames are a property of the file, not of any knob, so the only reason
   to repaint is that the strip on screen belongs to another tab - or that a
   fetch that had failed has since delivered. */
function paintTimelineFrames(sess) {
  const host = $('strip-frames');
  const frames = (sess.strip && sess.strip.frames) || [];
  const key = `${sess.id}|${frames.length}`;
  if (host.dataset.key === key) return;
  host.dataset.key = key;
  host.innerHTML = '';
  for (const f of frames) {
    const img = document.createElement('img');
    img.src = fileUrl(f);
    img.draggable = false;
    host.appendChild(img);
  }
}

function paintTimelineMarkers(sess) {
  const host = $('strip-markers');
  const key = `${sess.id}|${sess.eventsKey}`;
  if (host.dataset.key === key) return;
  host.dataset.key = key;
  host.innerHTML = '';
  const total = sess.file.duration;
  const events = (sess.eventsPlan && sess.eventsPlan.events) || [];
  const chip = $('strip-count');
  chip.classList.toggle('hidden', !events.length);
  chip.textContent = events.length ? `${events.length} event${events.length === 1 ? '' : 's'}` : '';
  chip.title = 'Open the timeline events editor';
  chip.onclick = (e) => { e.stopPropagation(); openEventEditor(); };
  const edited = editedIds(sess);
  for (const ev of events) {
    const tick = document.createElement('div');
    const id = ev.detail && ev.detail.id;
    // An instance that lasts paints as a span the width of its stay; a
    // one-frame incident paints as a tick. Same positioning, same handlers.
    const spanPct = (ev.dur / total) * 100;
    const wide = spanPct * host.clientWidth / 100 > 5;
    tick.className = wide ? 'strip-tick span' : 'strip-tick';
    if (id && String(id).startsWith('edit:')) tick.classList.add('added');
    else if (id && edited.has(id)) tick.classList.add('edited');
    if (wide) {
      tick.style.left = `calc(${(ev.t / total) * 100}% )`;
      tick.style.width = `${spanPct}%`;
    } else {
      // Centered on its moment: the tick is 3px wide, so back up one.
      tick.style.left = `calc(${(ev.t / total) * 100}% - 1px)`;
    }
    tick.style.background = TICK_COLORS[ev.kind] || 'var(--dim)';
    attachTip(tick, () => ({
      title: ev.kind.replace(/_/g, ' '),
      facts: [
        `effect ${ev.effect}`,
        `at ${ev.t.toFixed(2)}s for ${ev.dur.toFixed(2)}s`,
        ...Object.entries(ev.detail || {}).map(([k, v]) => `${k} ${v}`),
        'click to edit · drag to move',
      ],
      stack: true,
    }));
    /* Click opens the editor; a horizontal drag past a few pixels moves the
       instance and commits on release. The threshold is what keeps a shaky
       click from becoming an accidental move. */
    tick.addEventListener('pointerdown', (e) => {
      e.stopPropagation();
      e.preventDefault();
      const strip = host.getBoundingClientRect();
      const grabbed = e.clientX;
      let moved = false;
      const onMove = (m) => {
        if (!moved && Math.abs(m.clientX - grabbed) < 4) return;
        moved = true;
        const frac = Math.min(Math.max((m.clientX - strip.left) / strip.width, 0), 1);
        if (wide) tick.style.left = `${frac * 100}%`;
        else tick.style.left = `calc(${frac * 100}% - 1px)`;
      };
      const onUp = (u) => {
        window.removeEventListener('pointermove', onMove);
        window.removeEventListener('pointerup', onUp);
        if (!moved) { openEventEditor(id); return; }
        const frac = Math.min(Math.max((u.clientX - strip.left) / strip.width, 0), 1);
        moveEvent(ev, Math.round(frac * total * 20) / 20);
      };
      window.addEventListener('pointermove', onMove);
      window.addEventListener('pointerup', onUp);
    });
    host.appendChild(tick);
  }
  if (eventEditorOpen() && sess.id === G.activeId) rebuildEventRows();
}

/* Fetches whatever the strip is missing, then paints. Called fire-and-forget
   from runPreview - the strip must never delay a render - and from
   activateSession, so a revisited tab shows its cached strip instantly. The
   plan is keyed by the exact layer spec, which is why knob-fiddling that lands
   back on a spec already planned costs nothing. */
async function refreshTimeline() {
  const sess = state;
  const bar = $('timeline');
  if (!sess.file || !sess.file.path) { bar.classList.add('hidden'); return; }
  // body.audio-session already keeps the row off screen; skipping here also
  // keeps us from asking a WAV for frames it does not have.
  if (sess.audioSource) return;
  bar.classList.remove('hidden');
  syncTimelinePlayhead();

  if (!sess.strip && !sess.stripJob) {
    sess.stripJob = window.aesth.filmstrip({ input: sess.file.path })
      .then((r) => { sess.strip = r; })
      .catch(() => { /* the strip is decoration - seek and ticks work without it */ })
      .finally(() => { sess.stripJob = null; });
  }

  const key = JSON.stringify(layerSpec(sess));
  if (sess.eventsKey !== key && sess.eventsJob !== key) {
    if (!liveLayers(sess).length) {
      // Nothing selected plans nothing; asking the engine would only earn a
      // usage error back.
      sess.eventsKey = key;
      sess.eventsPlan = null;
    } else {
      sess.eventsJob = key;
      try {
        const plan = await window.aesth.events({
          input: sess.file.path,
          layers: layerSpec(sess),
          presetId: sess.presetId,
          variant: sess.variant,
          sets: sess.sets,
          seed: sess.seed,
          intensity: sess.intensity,
          texture: sess.texture,
        });
        // Only keep the answer while it is still the question: a knob moved
        // during planning makes this plan stale on arrival, and the refresh
        // that knob triggered is already fetching the real one.
        if (JSON.stringify(layerSpec(sess)) === key) {
          sess.eventsKey = key;
          sess.eventsPlan = plan;
        }
      } catch (_) {
        // A failed plan just leaves the strip tickless. The render pipeline
        // reports its own failures; a second report for decoration would only
        // shout over it.
      } finally {
        if (sess.eventsJob === key) sess.eventsJob = null;
      }
    }
  }

  if (sess.stripJob) await sess.stripJob;
  if (sess.id !== G.activeId) return;   // a different tab is on screen now
  paintTimelineFrames(sess);
  paintTimelineMarkers(sess);
}

/* ── the timeline events editor ──────────────────────────────────────
   The rows are the engine's own plan for the current spec - edits included -
   so the window never shows a schedule the render would disagree with. Ops are
   written onto the layer the event belongs to, the preview re-renders, and the
   plan refresh brings the rows back in the edited shape.

   Two kinds of target, one rule each. An instance the seed drew is edited by
   ops naming its minted id; an instance the user added IS its op, so editing
   one mutates the op in place and deleting one deletes the op. The engine
   enforces the same split (see docs/events.md) - this mirror just keeps the op
   list minimal instead of stacking contradictions. */

function evLayerOf(ev) {
  return state.layers[ev.layer] || activeLayer(state);
}

function findAddOp(l, id) {
  return (l.events || []).find((e) => e.op === 'add' && e.id === id);
}

/* One op per (op, id): re-moving a moved dropout replaces its move op rather
   than queueing a second opinion behind it. */
function upsertOp(l, op) {
  l.events = l.events || [];
  if (op.op === 'tune') {
    const prev = l.events.find((e) => e.op === 'tune' && e.id === op.id);
    if (prev) { prev.detail = { ...prev.detail, ...op.detail }; return; }
  } else if (op.op === 'move') {
    const prev = l.events.find((e) => e.op === 'move' && e.id === op.id);
    if (prev) { prev.t = op.t; return; }
  }
  l.events.push(op);
}

function afterEventEdit() {
  state.stackId = null;          // the arrangement is no longer the saved one
  schedulePreview();
  refreshTimeline().then(() => { if (eventEditorOpen()) rebuildEventRows(); });
  renderTabs();
}

function eventEditorOpen() {
  return !$('events-modal').classList.contains('hidden');
}

function openEventEditor(focusId = null) {
  if (!state.file || state.audioSource) return;
  $('events-modal').classList.remove('hidden');
  $('ev-add-t').value = state.previewT.toFixed(2);
  rebuildEventRows(focusId);
}

function closeEventEditor() {
  $('events-modal').classList.add('hidden');
}

function removeEvent(ev) {
  const l = evLayerOf(ev);
  const id = ev.detail && ev.detail.id;
  const addOp = id && findAddOp(l, id);
  if (addOp) {
    l.events = l.events.filter((e) => e !== addOp);
  } else if (id) {
    // Any pending move or tune of it is moot once it is gone.
    l.events = (l.events || []).filter((e) => !(e.id === id && e.op !== 'add'));
    upsertOp(l, { op: 'remove', id, effect: ev.effect, kind: ev.kind });
  }
  afterEventEdit();
}

function moveEvent(ev, t) {
  const l = evLayerOf(ev);
  const id = ev.detail && ev.detail.id;
  const addOp = id && findAddOp(l, id);
  if (addOp) addOp.t = t;
  else if (id) upsertOp(l, { op: 'move', id, t, effect: ev.effect, kind: ev.kind });
  afterEventEdit();
}

function tuneEvent(ev, detail) {
  const l = evLayerOf(ev);
  const id = ev.detail && ev.detail.id;
  const addOp = id && findAddOp(l, id);
  if (addOp) addOp.detail = { ...addOp.detail, ...detail };
  else if (id) upsertOp(l, { op: 'tune', id, detail, effect: ev.effect, kind: ev.kind });
  afterEventEdit();
}

let evAddSeq = 0;
function addEventAt(effect, kind, t, detail = {}) {
  const l = activeLayer(state);
  l.events = l.events || [];
  // The id is minted here so the plan can report it back and the row can find
  // its op again; the prefix is what marks it as the user's own.
  l.events.push({ op: 'add', id: `edit:add:${Date.now()}:${++evAddSeq}`,
                  effect, kind, t, detail });
  afterEventEdit();
}

function editedIds(sess = state) {
  const ids = new Set();
  for (const l of sess.layers || []) {
    for (const e of l.events || []) {
      if (e.op === 'move' || e.op === 'tune') ids.add(e.id);
    }
  }
  return ids;
}

/* A dial and a number that agree: drag the range or type the value, same
   commit. This is the row-level answer to "knobs and value entry". */
function evKnob(value, { min = 0, max = 1, step = 0.01, width = 64 }, commit) {
  const wrap = document.createElement('span');
  wrap.className = 'ev-knob';
  const r = document.createElement('input');
  r.type = 'range'; r.className = 'range-fill';
  r.min = min; r.max = max; r.step = step; r.value = value;
  r.style.width = `${width}px`;
  paintRange(r);
  const n = document.createElement('input');
  n.type = 'number'; n.className = 'ev-n';
  n.min = min; n.max = max; n.step = step; n.value = value;
  r.oninput = () => { n.value = r.value; paintRange(r); };
  r.onchange = () => commit(parseFloat(r.value));
  n.onchange = () => {
    const v = parseFloat(n.value);
    if (!Number.isFinite(v)) return;
    r.value = v; paintRange(r);
    commit(Math.min(Math.max(v, min), max));
  };
  wrap.appendChild(r);
  wrap.appendChild(n);
  return wrap;
}

/* A number input that commits on change, shared by every field in a row. */
function evNum(value, { min = 0, max = null, step = 1, cls = 'ev-n' }, commit) {
  const inp = document.createElement('input');
  inp.type = 'number';
  inp.className = cls;
  inp.min = min; if (max != null) inp.max = max;
  inp.step = step;
  inp.value = value;
  inp.onchange = () => {
    const v = parseFloat(inp.value);
    if (Number.isFinite(v)) commit(v);
  };
  return inp;
}

function rebuildEventRows(focusId = null) {
  const host = $('ev-list');
  host.innerHTML = '';
  const plan = state.eventsPlan;
  const all = (plan && plan.events) || [];
  /* The kind chips: damage one effect at a time. The set is whatever the plan
     actually contains, so the bar never advertises a kind this chain cannot
     produce. */
  const kinds = [...new Set(all.map((e) => e.kind))];
  const bar = $('ev-filter');
  bar.innerHTML = '';
  if (kinds.length > 1) {
    const mk = (label, value) => {
      const c = document.createElement('span');
      c.className = 'chip' + ((G.evFilter || '') === value ? ' sel' : '');
      c.textContent = label;
      if (value) c.style.color = TICK_COLORS[value] || '';
      c.onclick = () => { G.evFilter = value; rebuildEventRows(); };
      bar.appendChild(c);
    };
    mk('all', '');
    for (const k of kinds) mk(k.replace(/_/g, ' '), k);
  } else {
    G.evFilter = '';
  }
  const events = (G.evFilter ? all.filter((e) => e.kind === G.evFilter) : all);
  $('ev-count').textContent = all.length
    ? `${events.length}${G.evFilter ? ` of ${all.length}` : ''} planned, seed ${state.seed}`
    : 'none planned';
  const dur = state.file.duration;
  const edited = editedIds();
  if (!events.length) {
    const hint = document.createElement('div');
    hint.className = 'hint';
    hint.style.padding = '14px';
    hint.textContent = state.eventsJob
      ? 'Planning…'
      : 'Nothing planned. This aesthetic has no discrete damage - or every instance has been removed.';
    host.appendChild(hint);
    return;
  }
  for (const ev of events) {
    const id = ev.detail && ev.detail.id;
    const row = document.createElement('div');
    row.className = 'ev-row';
    row.dataset.id = id || '';
    row.dataset.kind = ev.kind;

    const dot = document.createElement('span');
    dot.className = 'ev-kind';
    dot.style.background = TICK_COLORS[ev.kind] || 'var(--dim)';
    row.appendChild(dot);

    row.appendChild(evNum(ev.t.toFixed(2), { min: 0, max: dur, step: 0.05, cls: 'ev-t' },
      (v) => moveEvent(ev, Math.min(Math.max(v, 0), dur))));
    const sLab = document.createElement('label');
    sLab.textContent = 's';
    row.appendChild(sLab);

    const what = document.createElement('span');
    what.className = 'ev-what';
    what.textContent = `${ev.kind.replace(/_/g, ' ')} · ${ev.effect}`;
    row.appendChild(what);

    if (ev.kind === 'dropout') {
      const d = ev.detail;
      const lab = (t) => { const el = document.createElement('label'); el.textContent = t; return el; };
      row.appendChild(lab('row'));
      row.appendChild(evNum(d.row, { min: 0, step: 1 }, (v) => tuneEvent(ev, { row: Math.round(v) })));
      row.appendChild(lab('x'));
      row.appendChild(evNum(d.x, { min: 0, step: 1 }, (v) => tuneEvent(ev, { x: Math.round(v) })));
      row.appendChild(lab('len'));
      row.appendChild(evNum(d.length_px, { min: 6, step: 1 }, (v) => tuneEvent(ev, { length_px: Math.round(v) })));
      const pol = document.createElement('select');
      for (const c of ['bright', 'dark']) {
        const o = document.createElement('option');
        o.value = c; o.textContent = c;
        if (c === d.polarity) o.selected = true;
        pol.appendChild(o);
      }
      pol.onchange = () => tuneEvent(ev, { polarity: pol.value });
      row.appendChild(pol);
    } else if (ev.kind === 'transport_glitch' || ev.kind === 'tracking_storm') {
      const lab = document.createElement('label');
      lab.textContent = 'lasts';
      row.appendChild(lab);
      row.appendChild(evNum(ev.dur.toFixed(2), { min: 0.05, step: 0.05 },
        (v) => tuneEvent(ev, { dur_s: v })));
      const sl = document.createElement('label');
      sl.textContent = 's';
      row.appendChild(sl);
      const il = document.createElement('label');
      il.textContent = 'intensity';
      row.appendChild(il);
      row.appendChild(evKnob(ev.detail.intensity ?? 1, { min: 0.05, max: 1, step: 0.01 },
        (v) => tuneEvent(ev, { intensity: v })));
    } else if (ev.kind === 'skew_tear') {
      const il = document.createElement('label');
      il.textContent = 'intensity';
      row.appendChild(il);
      row.appendChild(evKnob(ev.detail.intensity ?? 1, { min: 0.05, max: 2, step: 0.01 },
        (v) => tuneEvent(ev, { intensity: v })));
    } else if (ev.kind === 'transport_lock') {
      const note = document.createElement('span');
      note.className = 'dim';
      note.textContent = 'the deck locking on - move it with Start Glitch in VCR Transport';
      row.appendChild(note);
    }

    const grow = document.createElement('span');
    grow.className = 'grow';
    row.appendChild(grow);

    if (id && (String(id).startsWith('edit:') || edited.has(id))) {
      const tag = document.createElement('span');
      tag.className = 'ev-edited';
      tag.textContent = String(id).startsWith('edit:') ? 'yours' : 'edited';
      row.appendChild(tag);
    }

    if (ev.kind !== 'transport_lock') {
      const del = document.createElement('button');
      del.className = 'ev-del';
      del.textContent = '×';
      del.title = 'Remove this instance from the render';
      del.onclick = () => removeEvent(ev);
      row.appendChild(del);
    }
    host.appendChild(row);
  }
  if (focusId) {
    const hit = host.querySelector(`.ev-row[data-id="${CSS.escape(focusId)}"]`);
    if (hit) { hit.scrollIntoView({ block: 'center' }); hit.classList.add('flash'); }
  }
}

/* With auto on, every change re-renders by itself and Preview has nothing left
   to do, so it stops taking up space pretending otherwise. Turn auto off and it
   comes back as the way to ask for a render. */
function syncRenderButton() {
  $('btn-render').classList.toggle('hidden', G.autoPreview);
}

/* One switch for the pair. videoB sits underneath videoA for the A/B hold, so
   they have to start and stop together or the comparison drifts apart. */
function setPlaying(play) {
  G.paused = !play;
  saveStore();
  const btn = $('btn-play');
  btn.classList.toggle('paused', G.paused);
  btn.title = G.paused
    ? 'Play the preview (or press Space)'
    : 'Pause the looping preview (or press Space)';
  if (!videoA.getAttribute('src')) return;   // nothing to play; a still may still be up
  if (play) hideStill();                     // asking for the clip means asking past the still
  for (const v of [videoA, videoB]) {
    if (play) v.play().catch(() => {});
    else v.pause();
  }
}

function showRenderOverlay(show, phase = '', frac = 0) {
  $('render-overlay').classList.toggle('hidden', !show);
  if (show) { $('render-phase').textContent = phase; $('render-bar').style.width = `${frac * 100}%`; }
}

function onProgress(msg) {
  if (msg.jobId === G.activeJob) {
    showRenderOverlay(true, `${msg.phase} ${(msg.progress * 100).toFixed(0)}%`, msg.progress);
    return;
  }
  const job = G.exports.find((j) => j.id === msg.jobId);
  if (!job || job.status !== 'running') return;
  job.phase = msg.phase;
  // The engine reports monotonically; hold the line here too so a line that
  // arrives out of order cannot rewind a bar the user is watching.
  job.progress = Math.max(job.progress, msg.progress);
  updateExportRow(job);
  syncExportsButton();
}

// ── keyboard shortcuts ──────────────────────────────────────────────
function typingTarget(e) {
  const t = e.target;
  return t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT');
}

function wireShortcuts() {
  window.addEventListener('keydown', (e) => {
    const meta = e.metaKey || e.ctrlKey;
    // A pending "this would overwrite your work" question owns the keyboard
    // outright: the answer is a click, and Escape means leave it alone.
    if (choiceOpen()) {
      if (e.code === 'Escape') closeChoice(null);
      e.preventDefault();
      return;
    }
    /* The failure detail is a reading pane: Escape closes it, and everything
       else - ⌘C above all - belongs to the selection in it. */
    if (!$('error-modal').classList.contains('hidden')) {
      if (e.code === 'Escape') { e.preventDefault(); closeErrorDetail(); }
      return;
    }
    /* The events editor is typing-heavy; the keyboard is its own until Escape. */
    if (eventEditorOpen()) {
      if (e.code === 'Escape') { e.preventDefault(); closeEventEditor(); }
      return;
    }
    if (meta && e.code === 'KeyO') { e.preventDefault(); browseForFile(); return; }
    // The about dialog owns the keyboard while it is up, the same way the name
    // prompt does - Cmd+O behind a modal is nobody's intent.
    if (!$('about-modal').classList.contains('hidden')) {
      if (e.code === 'Escape' && !U.busy) { e.preventDefault(); closeAbout(); return; }
      // ...except in the version dropdown, where arrows and letters are how you
      // move through the list.
      if (e.target === $('about-version-select')) return;
      e.preventDefault();
      return;
    }
    if (e.code === 'Escape' && !$('exports-panel').classList.contains('hidden')) {
      e.preventDefault();
      toggleExportsPanel(false);
      return;
    }
    /* ↑/↓ run the preset list. They work from the search box too - type a few
       letters, then walk the hits without reaching for the mouse - but not from
       a slider or dropdown, where the arrows already mean something. */
    if (G.activeId && (e.code === 'ArrowDown' || e.code === 'ArrowUp')
        && (!typingTarget(e) || e.target === $('preset-search'))) {
      e.preventDefault();
      navPreset(e.code === 'ArrowDown' ? 1 : -1);
      return;
    }
    /* Enter commits the highlighted aesthetic on its own, dropping any stack;
       + / = appends it as another layer. Both work from the search box, so a
       search-and-stack never needs the mouse. */
    if (G.activeId && selectionId()
        && (!typingTarget(e) || e.target === $('preset-search'))) {
      if (e.code === 'Enter' && !meta) {
        e.preventDefault();
        pickOnly(selectionId());
        return;
      }
      if ((e.key === '+' || e.key === '=') && !meta && liveLayers(state).length) {
        e.preventDefault();
        addLayer(selectionId());
        return;
      }
    }
    if (typingTarget(e)) return;
    if (meta && e.code === 'KeyE') {
      e.preventDefault();
      if (G.activeId && state.presetId) doExport();
      return;
    }
    if (!G.activeId) return;
    if (e.code === 'Slash' || (meta && e.code === 'KeyF')) {
      e.preventDefault();
      $('preset-search').focus();
      $('preset-search').select();
      return;
    }
    if (e.code === 'Space') {
      e.preventDefault();
      setPlaying(G.paused);
      return;
    }
    if (e.code === 'KeyB' && !e.repeat && videoA.src) G.showOriginal(true);
  });
  window.addEventListener('keyup', (e) => {
    if (e.code === 'KeyB' && G.activeId) G.showOriginal(false);
  });
}

// ── controls ────────────────────────────────────────────────────────
function wireControls() {
  document.querySelectorAll('input.range-fill').forEach(paintRange);
  $('preset-search').addEventListener('input', buildPresetList);
  $('era-filter').addEventListener('change', (e) => {
    G.filterEra = e.target.value;
    e.target.classList.toggle('active', !!G.filterEra);
    buildPresetList();
  });

  const scrub = $('scrub');
  scrub.addEventListener('input', () => {
    state.previewT = parseFloat(scrub.value);
    paintRange(scrub);
    $('scrub-label').textContent = `preview at ${state.previewT.toFixed(1)}s`;
    syncTimelinePlayhead();
  });
  scrub.addEventListener('change', () => schedulePreview());

  /* The strip is the same seek surface as the slider, just map-shaped: x is
     time across the whole clip. It borrows the slider's own max and 0.1 s
     grid, so the two controls can never disagree about where the preview
     window is allowed to sit. */
  const stripSeek = (clientX, commit) => {
    if (!state.file || !state.file.duration) return;
    const r = $('timeline').getBoundingClientRect();
    if (!r.width) return;
    const frac = Math.min(Math.max((clientX - r.left) / r.width, 0), 1);
    const t = Math.min(frac * state.file.duration, parseFloat(scrub.max) || 0);
    state.previewT = parseFloat(t.toFixed(1));
    scrub.value = state.previewT.toFixed(1);
    paintRange(scrub);
    $('scrub-label').textContent = `preview at ${state.previewT.toFixed(1)}s`;
    syncTimelinePlayhead();
    if (commit) schedulePreview();
  };
  /* Press and slide scrubs the strip like a timeline, not like a button: the
     playhead follows the pointer live, and the render fires once on release.
     A plain click is the degenerate drag and behaves exactly as before. */
  $('timeline').addEventListener('pointerdown', (e) => {
    if (e.target.closest('.strip-tick')) return;   // ticks own their own drags
    stripSeek(e.clientX, false);
    const onMove = (m) => stripSeek(m.clientX, false);
    const onUp = (u) => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      stripSeek(u.clientX, true);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  });

  $('auto-preview').checked = G.autoPreview;
  $('auto-preview').addEventListener('change', (e) => {
    G.autoPreview = e.target.checked;
    saveStore();
    syncRenderButton();
  });
  $('btn-render').addEventListener('click', () => { clearTimeout(previewTimer); runPreview(); });
  syncRenderButton();

  /* Preview window length and render scale. Changing either re-keys the cache,
     so the next Preview is a fresh render at the new setting. */
  const lenSel = $('preview-len');
  lenSel.value = String(G.duration);
  lenSel.addEventListener('change', () => {
    G.duration = parseFloat(lenSel.value);
    saveStore();
    if (state.file && state.file.duration) {
      scrub.max = Math.max(state.file.duration - G.duration, 0).toFixed(1);
      if (state.previewT > parseFloat(scrub.max)) {
        state.previewT = parseFloat(scrub.max);
        scrub.value = state.previewT.toFixed(1);
        $('scrub-label').textContent = `preview at ${state.previewT.toFixed(1)}s`;
      }
      paintRange(scrub);
    }
    // The translucent span *is* the window: a new length changes its width.
    syncTimelinePlayhead();
    schedulePreview();
  });
  const scaleSel = $('preview-scale');
  scaleSel.value = String(G.scale);
  scaleSel.addEventListener('change', () => {
    G.scale = parseFloat(scaleSel.value);
    saveStore();
    schedulePreview();
  });

  const ab = $('btn-ab');
  const showOriginal = (on) => {
    videoA.style.opacity = on ? '0' : '1';
    // The still sits above videoA, so it has to step aside for the same reason.
    $('still-frame').style.opacity = on ? '0' : '1';
    ab.classList.toggle('held', on);
    $('ab-badge').classList.toggle('hidden', !on);
    if (on) { videoB.currentTime = videoA.currentTime; videoB.muted = G.muted; videoA.muted = true; }
    else { videoA.muted = G.muted; videoB.muted = true; }
  };
  ab.addEventListener('mousedown', () => showOriginal(true));
  ab.addEventListener('mouseup', () => showOriginal(false));
  ab.addEventListener('mouseleave', () => showOriginal(false));
  G.showOriginal = showOriginal;   // the B-key shortcut shares this

  /* Clicking the picture stops and starts it, the same as the button and the
     space bar. Stopping a loop on the frame you want to look at is the most
     common thing anyone does here, and it should not need a trip to a 24px
     button below the picture. */
  $('player-wrap').addEventListener('click', () => {
    if (!videoA.getAttribute('src')) return;   // nothing rendered yet
    setPlaying(G.paused);
  });

  const muteBtn = $('btn-mute');
  muteBtn.classList.toggle('on', !G.muted);
  videoA.muted = G.muted;
  muteBtn.addEventListener('click', () => {
    G.muted = !G.muted;
    videoA.muted = G.muted;
    muteBtn.classList.toggle('on', !G.muted);
    saveStore();
  });

  $('btn-play').addEventListener('click', () => setPlaying(G.paused));
  setPlaying(!G.paused);   // paint the icon to match the restored state

  $('intensity').addEventListener('input', (e) => {
    state.intensity = parseFloat(e.target.value);
    $('intensity-val').textContent = state.intensity.toFixed(2);
    paintRange(e.target);
  });
  $('intensity').addEventListener('change', () => { syncPresetSub(); schedulePreview(); });

  $('texture').addEventListener('input', (e) => {
    state.texture = parseFloat(e.target.value);
    $('texture-val').textContent = state.texture.toFixed(2);
    paintRange(e.target);
  });
  $('texture').addEventListener('change', () => { syncPresetSub(); schedulePreview(); });

  $('seed').value = state.seed;
  $('seed').addEventListener('change', (e) => {
    state.seed = parseInt(e.target.value || '1', 10);
    syncPresetSub();
    schedulePreview();
  });
  $('btn-dice').addEventListener('click', () => {
    state.seed = 1 + Math.floor(Math.random() * 999998);
    $('seed').value = state.seed;
    syncPresetSub();
    schedulePreview();
  });

  $('btn-fav').addEventListener('click', () => { if (state.presetId) toggleFav(state.presetId); });
  $('btn-save-custom').addEventListener('click', saveCustom);
  $('btn-save-stack').addEventListener('click', saveStack);

  $('ev-close').addEventListener('click', closeEventEditor);
  $('events-modal').addEventListener('mousedown', (e) => {
    if (e.target === $('events-modal')) closeEventEditor();
  });
  $('ev-add').addEventListener('click', () => {
    const t = parseFloat($('ev-add-t').value);
    if (!Number.isFinite(t)) return;
    const kind = $('ev-add-kind').value;
    // The op targets the effect that owns the kind; if the active layer's
    // chain has no such effect the engine simply plans nothing for it, which
    // the rows will show - honest, if unhelpful, so keep the two aligned.
    const owner = { dropout: 'vhs', tracking_storm: 'vhs', skew_tear: 'vhs',
                    transport_glitch: 'vcr_transport' }[kind] || 'vhs';
    addEventAt(owner, kind, Math.min(Math.max(t, 0), state.file.duration), {});
  });
  $('ev-reset').addEventListener('click', () => {
    const l = activeLayer(state);
    if (!(l.events || []).length) return;
    l.events = [];
    afterEventEdit();
  });

  $('btn-error-detail').addEventListener('click', () => showErrorDetail(G.lastFailure));
  $('error-close').addEventListener('click', closeErrorDetail);
  $('error-modal').addEventListener('mousedown', (e) => {
    if (e.target === $('error-modal')) closeErrorDetail();
  });
  $('error-copy').addEventListener('click', async () => {
    const btn = $('error-copy');
    try {
      await navigator.clipboard.writeText($('error-text').textContent);
      btn.textContent = 'Copied';
    } catch (_) {
      // Clipboard refused: select it so ⌘C still works rather than saying nothing.
      const r = document.createRange();
      r.selectNodeContents($('error-text'));
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(r);
      btn.textContent = 'Press ⌘C';
    }
    setTimeout(() => { btn.textContent = 'Copy'; }, 1800);
  });

  $('modal-cancel').addEventListener('click', () => closeModal(null));
  $('modal-ok').addEventListener('click', () => closeModal($('modal-input').value.trim() || null));
  $('modal-input').addEventListener('keydown', (e) => {
    if (e.code === 'Enter') { e.preventDefault(); closeModal($('modal-input').value.trim() || null); }
    if (e.code === 'Escape') { e.preventDefault(); closeModal(null); }
    e.stopPropagation();   // the modal owns the keyboard while it is up
  });
  $('modal').addEventListener('mousedown', (e) => { if (e.target === $('modal')) closeModal(null); });
  // Clicking the backdrop of a "this would overwrite your work" question is a
  // cancel, same as Escape: the safe answer is always the default.
  $('choice-modal').addEventListener('mousedown', (e) => {
    if (e.target === $('choice-modal')) closeChoice(null);
  });
  $('btn-reset-overrides').addEventListener('click', () => {
    state.sets = {};
    buildParamPane();
    schedulePreview();
  });
  $('exp-video-only').addEventListener('change', (e) => {
    if (e.target.checked) $('exp-audio-only').checked = false;
    schedulePreview();
  });
  $('exp-audio-only').addEventListener('change', (e) => {
    if (e.target.checked) $('exp-video-only').checked = false;
    schedulePreview();
  });

  $('btn-export').addEventListener('click', doExport);
  $('file-chip').addEventListener('click', revealSourceFile);

  $('btn-exports').addEventListener('click', () => toggleExportsPanel());
  $('btn-exports-clear').addEventListener('click', clearFinishedExports);
  // Click anywhere else to dismiss the panel, the way a menu behaves.
  document.addEventListener('mousedown', (e) => {
    if ($('exports-panel').classList.contains('hidden')) return;
    if ($('exports-panel').contains(e.target) || $('btn-exports').contains(e.target)) return;
    toggleExportsPanel(false);
  });

  $('btn-drop-cancel').addEventListener('click', () => {
    const last = G.sessions[G.sessions.length - 1];
    if (last) activateSession(last.id);
  });

  $('btn-cache-clear').addEventListener('click', async () => {
    const btn = $('btn-cache-clear');
    btn.disabled = true;
    try {
      const r = await window.aesth.cacheClear();
      // the open tabs' cached previews are gone; keep params, drop the players
      for (const sess of G.sessions) { sess.treatedSrc = null; sess.originalSrc = null; sess.originalT = null; }
      videoA.removeAttribute('src'); videoB.removeAttribute('src');
      videoA.load(); videoB.load();
      $('player-empty').classList.remove('hidden');
      $('player-empty').textContent = 'Cache cleared';
      setExportStatus(`Cleared ${r.removed} cached preview${r.removed === 1 ? '' : 's'} (${fmtBytes(r.bytes)}).`);
      await refreshCacheInfo();
      // Rebuild what was on screen. Without this the player is left empty with
      // no obvious way back, since Preview is hidden while auto is on.
      schedulePreview(true);
    } catch (err) {
      setExportStatus(`Could not clear cache: ${err.message.slice(0, 200)}`, true);
    } finally {
      btn.disabled = false;
    }
  });

  $('btn-cache-reveal').addEventListener('click', () => window.aesth.cacheReveal());

  attachTip($('intensity').previousElementSibling, () => ({
    title: 'Intensity',
    desc: 'Master strength for everything the preset does to the picture and sound - damage, warping, glow, colour treatment. 0 leaves the clip almost untouched, 2 doubles the authored amounts.',
    facts: ['range 0 – 2', 'applies to the whole chain'],
  }));
  attachTip($('texture').previousElementSibling, () => ({
    title: 'Texture',
    desc: 'Master amount for grain, tape noise, RF snow, dust and speckle only. Drag to 0 for a perfectly clean version of the look; decay content like mould or water staining is left alone.',
    facts: ['range 0 – 2', 'grain and noise only'],
  }));
  attachTip($('btn-save-stack'), () => {
    const n = captureStackLayers().length;
    return {
      title: 'Save this stack',
      desc: 'Keeps the whole arrangement: which aesthetics, the order they render in, '
        + 'every knob on each one, and which layers you have switched off. Saved stacks '
        + 'appear under MY STACKS at the top of the list. Clicking one rebuilds all of it; '
        + 'its green + piles it on top of what you already have instead.',
      facts: [
        n ? `${n} layer${n === 1 ? '' : 's'} right now` : 'nothing to save yet',
        'a custom saves one aesthetic, a stack saves the lot',
      ],
    };
  });
  attachTip($('cache-row'), () => ({
    title: 'Preview cache',
    desc: 'Every preview render is kept on disk, keyed by its exact parameters, so returning to earlier settings is instant. It is safe to clear at any time - you only pay the re-render.',
    facts: [G.cacheDir || 'location unavailable'],
  }));
}

/* ── exports ─────────────────────────────────────────────────────────
   Exports are jobs, not a mode the app sits in: start as many as you like and
   carry on working. Each one carries a frozen copy of the settings it was
   started with, so editing the session afterwards - or switching tabs, or
   picking a different aesthetic - cannot change what is being written.

   Two render at once. A full-length pass is CPU-bound, so a third would only
   make the first two slower; the rest wait their turn and say so. */
const MAX_ACTIVE_EXPORTS = 2;

function activeExports() {
  return G.exports.filter((j) => j.status === 'running' || j.status === 'queued');
}

/* Jobs started while the queue was already busy belong to the same batch, and
   the titlebar bar averages over the whole batch rather than over whatever is
   running right now. Averaging only the running jobs made the bar lurch
   backwards every time one of a parallel pair landed: 95% and 10% averages to
   52%, then the 95% one finishes and the average drops to 10%. */
function currentBatch() {
  return G.exports.filter((j) => j.batchId === G.batchId && j.status !== 'canceled');
}

function batchProgress() {
  const batch = currentBatch();
  if (!batch.length) return 0;
  const total = batch.reduce((n, j) => {
    if (j.status === 'done' || j.status === 'failed') return n + 1;
    return n + (j.status === 'running' ? j.progress : 0);
  }, 0);
  return total / batch.length;
}

async function doExport() {
  const sess = activeSession();
  if (!sess || !sess.file || !liveLayers(sess).length) return;

  // Freeze everything now: the save dialog is modal, but the export outlives it.
  const req = {
    input: sess.file.path,
    layers: layerSpec(sess),
    presetId: sess.presetId,
    variant: sess.variant,
    sets: { ...sess.sets },
    seed: sess.seed,
    intensity: sess.intensity,
    texture: sess.texture,
    crf: 17,
    videoOnly: $('exp-video-only').checked,
    audioOnly: $('exp-audio-only').checked,
  };
  const base = sess.file.path.replace(/\.[^.]+$/, '');
  const variantTag = sess.variant ? `-${sess.variant}` : '';
  const srcExt = (sess.file.path.match(/\.[^.\/]+$/) || ['.mp4'])[0];
  const outExt = sess.audioSource ? srcExt : '.mp4';
  // A custom or a stack names the file after itself; the base presets are still
  // what the engine renders, but "my-look" beats "vhs-1985-sp" on disk.
  const tag = sess.stackId
    ? slugify(stackName(sess.stackId))
    : (sess.customId
      ? slugify(customName(sess.customId))
      : sess.presetId.replace('/', '-') + variantTag);
  const suggestion = `${base}.${tag}${outExt}`;
  const out = await window.aesth.pickExportPath(suggestion, sess.audioSource);
  if (!out) return;

  // Two jobs writing the same path would race to produce a corrupt file, and the
  // save dialog only knows about files that already exist.
  if (activeExports().some((j) => j.req.output === out)) {
    setExportStatus(`Already exporting to ${basename(out)}.`, true);
    return;
  }

  // A job queued while nothing is in flight opens a fresh batch for the
  // titlebar's aggregate bar.
  if (!activeExports().length) G.batchId++;

  const job = {
    id: `job${++G.jobCounter}`,
    batchId: G.batchId,
    label: wearingName(sess) + (sess.stackId ? '' : (sess.variant ? ` · ${sess.variant}` : '')),
    source: basename(sess.file.path),
    status: 'queued',
    phase: '',
    progress: 0,
    error: '',
    req: { ...req, output: out },
  };
  job.req.jobId = job.id;
  G.exports.push(job);
  renderExports();
  pumpExports();
}

/* Fill the free slots, oldest queued job first. */
function pumpExports() {
  let slots = MAX_ACTIVE_EXPORTS - G.exports.filter((j) => j.status === 'running').length;
  for (const job of G.exports) {
    if (slots <= 0) break;
    if (job.status !== 'queued') continue;
    slots--;
    startExport(job);
  }
  syncExportsButton();
}

/* An export runs for minutes, so the point of it is that you go and do
   something else - which is exactly when an in-app toast is no use. One banner
   per *batch*, not per job: queueing ten exports and getting ten notifications
   would be its own kind of rude, so only the job that empties the queue speaks,
   and it speaks for all of them. */
/* What the banner for a batch should say, or null if it should stay quiet.
   Kept separate from sending it so the wording is a plain function of the
   batch, with nothing to stub out to check it. */
function exportNotice(batch) {
  if (batch.some((j) => j.status === 'running' || j.status === 'queued')) return null;
  const done = batch.filter((j) => j.status === 'done');
  const failed = batch.filter((j) => j.status === 'failed');
  if (!done.length && !failed.length) return null;   // a batch cancelled outright

  let title;
  let body;
  if (!failed.length) {
    title = done.length === 1 ? 'Export finished' : `${done.length} exports finished`;
    body = done.length === 1
      ? `${done[0].label} · ${basename(done[0].req.output)}`
      : done.map((j) => basename(j.req.output)).join(', ');
  } else if (!done.length) {
    title = failed.length === 1 ? 'Export failed' : `${failed.length} exports failed`;
    body = failed.length === 1
      ? `${basename(failed[0].req.output)} · ${failed[0].error}`
      : failed.map((j) => basename(j.req.output)).join(', ');
  } else {
    title = `${done.length} exported, ${failed.length} failed`;
    body = `Failed: ${failed.map((j) => basename(j.req.output)).join(', ')}`;
  }
  // Clicking reveals the file, so the banner lands you where the work is. Only
  // when there is exactly one, since a folder full is nobody's idea of a target.
  return { title, body: body.slice(0, 300), reveal: done.length === 1 ? done[0].req.output : '' };
}

function notifyBatchDone(job) {
  // Keyed off this job's own batch, not G.batchId: by the time a long export
  // lands, the counter may already have moved on to a batch queued after it.
  const notice = exportNotice(G.exports.filter((j) => j.batchId === job.batchId));
  if (!notice) return;
  try { window.aesth.notify(notice); } catch (_) {
    /* notifications are a courtesy: never let one break the export flow */
  }
}

async function startExport(job) {
  job.status = 'running';
  job.phase = 'starting';
  renderExports();
  flash('Export started', { sub: `${job.label} · ${basename(job.req.output)}` });
  try {
    const res = await window.aesth.exportRender(job.req);
    job.status = 'done';
    job.progress = 1;
    setExportStatusLink('Exported ', res.output);
    flash('Export finished', { sub: basename(res.output), kind: 'done', ms: 6000 });
  } catch (err) {
    const msg = String(err.message || '');
    if (msg.includes('superseded')) {
      // The only thing that kills an export mid-flight is our own cancel.
      job.status = 'canceled';
      setExportStatus(`Export canceled - the partial ${basename(job.req.output)} was removed.`);
      flash('Export canceled', { sub: basename(job.req.output) });
    } else {
      job.status = 'failed';
      // The row shows the cause; the whole message stays on the job so the
      // Details button can hand it over intact.
      const parts = errorParts(err);
      job.error = parts.headline;
      job.errorFull = parts.full;
      reportFailure('Export', err);
      flash('Export failed', { sub: basename(job.req.output), kind: 'error', ms: 8000 });
    }
  } finally {
    // Before pumpExports, so "is the queue empty" is asked of the queue as it
    // stands now rather than after the next job has already claimed a slot.
    if (job.status !== 'canceled') notifyBatchDone(job);
    renderExports();
    pumpExports();     // whatever happened, a slot just came free
  }
}

async function cancelExport(job) {
  if (job.status === 'queued') {     // never started: nothing to kill
    job.status = 'canceled';
    renderExports();
    pumpExports();
    return;
  }
  if (job.status !== 'running') return;
  await window.aesth.cancelExport(job.id);   // rejects startExport's promise
}

function clearFinishedExports() {
  G.exports = activeExports();
  renderExports();
  if (!G.exports.length) toggleExportsPanel(false);
}

/* The titlebar button: how many are in flight, and how far along as a whole. */
function syncExportsButton() {
  const btn = $('btn-exports');
  btn.classList.toggle('hidden', G.exports.length === 0);
  if (!G.exports.length) return;
  const live = activeExports();
  const failed = G.exports.filter((j) => j.status === 'failed').length;
  const done = G.exports.filter((j) => j.status === 'done').length;
  btn.classList.toggle('busy', live.length > 0);
  btn.classList.toggle('has-error', live.length === 0 && failed > 0);
  if (live.length) {
    const running = live.filter((j) => j.status === 'running');
    $('exports-label').textContent = `${live.length} exporting`;
    $('exports-mini-bar').style.width = `${Math.round(batchProgress() * 100)}%`;
    btn.title = `${running.length} rendering, ${live.length - running.length} queued`;
  } else {
    $('exports-label').textContent = failed
      ? `${failed} failed`
      : `${done} exported`;
    $('exports-mini-bar').style.width = '0%';
    btn.title = 'Show the export queue';
  }
}

const EXPORT_STATE_TEXT = {
  queued: 'waiting for a free slot',
  running: 'rendering',
  done: 'finished',
  failed: 'failed',
  canceled: 'canceled',
};

function renderExports() {
  syncExportsButton();
  const list = $('exports-list');
  list.innerHTML = '';
  if (!G.exports.length) {
    const empty = document.createElement('div');
    empty.className = 'ep-empty';
    empty.textContent = 'Nothing exported yet.';
    list.appendChild(empty);
    $('btn-exports-clear').disabled = true;
    return;
  }
  $('btn-exports-clear').disabled = activeExports().length === G.exports.length;

  // Newest first: the thing you just started is the thing you want to see.
  for (const job of [...G.exports].reverse()) {
    const row = document.createElement('div');
    row.className = `ex-row ${job.status}`;

    const head = document.createElement('div');
    head.className = 'ex-head';
    const name = document.createElement('span');
    name.className = 'ex-name';
    name.textContent = basename(job.req.output);
    name.title = job.req.output;
    head.appendChild(name);

    if (job.status === 'queued' || job.status === 'running') {
      const stop = document.createElement('button');
      stop.className = 'ex-stop';
      stop.textContent = '×';
      stop.title = 'Stop this export and delete the partial file';
      stop.onclick = () => cancelExport(job);
      head.appendChild(stop);
    } else if (job.status === 'done') {
      const rev = document.createElement('button');
      rev.className = 'link-btn';
      rev.textContent = 'Reveal';
      rev.onclick = () => revealFile(job.req.output);
      head.appendChild(rev);
    }
    row.appendChild(head);

    const sub = document.createElement('div');
    sub.className = 'ex-sub';
    sub.textContent = `${job.label} · ${job.source}`;
    sub.title = sub.textContent;
    row.appendChild(sub);

    const bar = document.createElement('div');
    bar.className = 'ex-bar';
    const fill = document.createElement('div');
    fill.className = 'ex-fill';
    fill.style.width = `${Math.round(job.progress * 100)}%`;
    bar.appendChild(fill);
    row.appendChild(bar);

    const foot = document.createElement('div');
    foot.className = 'ex-foot';
    const st = document.createElement('span');
    st.textContent = job.status === 'running' && job.phase
      ? job.phase
      : EXPORT_STATE_TEXT[job.status];
    foot.appendChild(st);
    const pct = document.createElement('span');
    pct.className = 'ex-pct';
    pct.textContent = job.status === 'running' ? `${Math.round(job.progress * 100)}%` : '';
    foot.appendChild(pct);
    row.appendChild(foot);

    if (job.status === 'failed' && job.error) {
      const err = document.createElement('div');
      err.className = 'ex-err';
      err.textContent = job.error;
      err.title = 'Click for the whole message';
      err.onclick = () => showErrorDetail({
        title: `Export failed · ${basename(job.req.output)}`,
        sub: job.error,
        text: job.errorFull || job.error,
      });
      row.appendChild(err);
    }

    // Progress arrives several times a second; the row is rebuilt only on state
    // changes, and these nodes are written in place in between.
    job.nodes = { fill, phase: st, pct };
    list.appendChild(row);
  }
}

/* Cheap per-tick update: no DOM rebuild, so the bar animates smoothly. */
function updateExportRow(job) {
  if (!job.nodes || !job.nodes.fill.isConnected) return;
  job.nodes.fill.style.width = `${Math.round(job.progress * 100)}%`;
  job.nodes.phase.textContent = job.phase || EXPORT_STATE_TEXT[job.status];
  job.nodes.pct.textContent = `${Math.round(job.progress * 100)}%`;
}

function toggleExportsPanel(show) {
  const panel = $('exports-panel');
  const open = show === undefined ? panel.classList.contains('hidden') : show;
  panel.classList.toggle('hidden', !open);
  $('btn-exports').classList.toggle('open', open);
  if (open) renderExports();
}

/* ── toasts ─────────────────────────────────────────────────────────
   The export bar at the bottom already says what happened, but it is nowhere
   near where the eye is and it says it silently. A toast covers the two moments
   worth interrupting for: a job started, and a job landed. */
function flash(text, { sub = '', kind = '', ms = 4200 } = {}) {
  const host = $('toasts');
  if (!host) return;
  const el = document.createElement('div');
  el.className = `toast ${kind}`.trim();
  const body = document.createElement('div');
  body.textContent = text;
  if (sub) {
    const s = document.createElement('div');
    s.className = 't-sub';
    s.textContent = sub;
    body.appendChild(s);
  }
  el.appendChild(body);
  host.appendChild(el);

  // Never let them stack past a handful - a batch of eight exports finishing
  // should not wallpaper the window.
  while (host.children.length > 4) host.removeChild(host.firstChild);

  setTimeout(() => {
    el.classList.add('leaving');
    setTimeout(() => el.remove(), 240);
  }, ms);
}

function setExportStatus(text, isError = false) {
  const el = $('export-status');
  el.textContent = text;
  el.style.color = isError ? 'var(--danger)' : '';
  // Any new status supersedes the last failure's detail button.
  if (!isError) $('btn-error-detail').classList.add('hidden');
}

/* ── failures ────────────────────────────────────────────────────────
   What a render says when it dies is often the only thing that explains it, and
   it arrives wrapped: Electron prefixes the IPC channel, and Python puts the
   sentence that names the cause on the *last* line of a traceback. The status
   bar is one ellipsised line, so it was showing the prefix and hiding the
   sentence - "Error invoking remote method 'aesth:preview'" and nothing else.
   So: lead with the cause, keep the whole thing, and put it a click away. */
function errorParts(err) {
  const full = String((err && err.stack) || (err && err.message) || err || 'unknown error');
  const stripped = full.replace(/^Error: Error invoking remote method '[^']*':\s*/, '')
    .replace(/^Error invoking remote method '[^']*':\s*/, '');
  // A Python traceback ends on the line that matters; ffmpeg and Node errors are
  // already one line, so the last non-empty line is the right pick either way.
  const lines = stripped.split('\n').map((l) => l.trim()).filter(Boolean);
  const named = [...lines].reverse().find((l) => /^[A-Za-z_.]+(Error|Exception)\b/.test(l));
  return { headline: named || lines[lines.length - 1] || 'unknown error', full: stripped };
}

function reportFailure(what, err) {
  const { headline, full } = errorParts(err);
  G.lastFailure = { title: `${what} failed`, sub: headline, text: full };
  setExportStatus(`${what} failed: ${headline}`, true);
  $('btn-error-detail').classList.remove('hidden');
}

function showErrorDetail(failure) {
  if (!failure) return;
  $('error-title').textContent = failure.title;
  $('error-sub').textContent = failure.sub || '';
  $('error-text').textContent = failure.text;
  $('error-modal').classList.remove('hidden');
  $('error-text').focus();
}

function closeErrorDetail() {
  $('error-modal').classList.add('hidden');
}

function setExportStatusLink(prefix, file) {
  const el = $('export-status');
  el.style.color = '';
  el.innerHTML = '';
  el.append(prefix);
  const a = document.createElement('a');
  a.textContent = file.split('/').pop();
  a.onclick = () => revealFile(file);
  el.appendChild(a);
  el.append(' - click to reveal');
}
