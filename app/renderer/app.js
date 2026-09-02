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
  history: [],         // every finished export ever (persisted), oldest first
  historySeq: 0,
  filterFamilies: new Set(),  // family chips currently selected (empty = all)
  filterEra: '',       // decade string like "1980s" (empty = any)
  audioOnly: false,    // the always-visible Audio chip: presets that leave picture untouched
  favOnly: false,      // the ★ chip: show favorites only
  customOnly: false,   // the ✎ chip: show saved customs only
  stackOnly: false,    // the ▤ chip: show saved stacks only
  filterFacets: {},    // facet id -> selected value id (empty = any facet value)
  refineOpen: true,    // the facet dropdown row is unfolded (persisted)
  guideOpen: false,    // the ✦ chip: browse the curated collections instead of the library
  recents: [],         // preset ids picked by hand, newest first (persisted)
  searchIndex: new Map(),   // preset id -> tokenized search fields (see searchFields)
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
const UPDATE_POLL_MS = 60 * 60 * 1000;
let automaticUpdateBusy = false;
let updatePollTimer = null;

/* ── small persistence layer (localStorage) ─────────────────────────
   Favorites, collapsed families and the preview knobs survive restarts.
   Everything degrades to defaults if storage is unavailable or stale. */
const STORE_KEY = 'aesthetician.ui.v1';
const RECENTS_MAX = 8;

function loadStore() {
  try {
    const s = JSON.parse(localStorage.getItem(STORE_KEY) || '{}');
    if (Array.isArray(s.favs)) G.favs = new Set(s.favs);
    if (Array.isArray(s.collapsed)) G.collapsed = new Set(s.collapsed);
    if (Array.isArray(s.recents)) G.recents = s.recents.filter((id) => typeof id === 'string').slice(0, RECENTS_MAX);
    if (typeof s.refineOpen === 'boolean') G.refineOpen = s.refineOpen;
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
      recents: G.recents,
      refineOpen: G.refineOpen,
    }));
  } catch (_) { /* storage full or unavailable: cosmetic only */ }
}

/* ── export history (localStorage, its own key) ─────────────────────
   Every export that finishes writing a file is remembered: which clip, where
   it lived, where the result went, and the exact layers and knobs that were
   rendered. Its own key rather than a field on the main store because it can
   grow large, and a corrupt or oversized history must never take the
   favorites and customs down with it. */
const HISTORY_KEY = 'aesthetician.history.v1';
const HISTORY_MAX = 500;   // the oldest entries fall off past this

function loadHistory() {
  try {
    const s = JSON.parse(localStorage.getItem(HISTORY_KEY) || '{}');
    if (Array.isArray(s.runs)) {
      G.history = s.runs.filter((r) => r && r.id && r.input && r.output && Array.isArray(r.layers));
      G.historySeq = G.history.reduce((n, r) => Math.max(n, parseInt(r.id.slice(1), 10) || 0), 0);
    }
  } catch (_) { /* first run, or corrupted store: an empty history is fine */ }
}

function saveHistory() {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify({ runs: G.history }));
  } catch (_) { /* storage full or unavailable: remembering is a courtesy */ }
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
/* Where the Texture dial rests when a layer starts or a preset is picked.
   Most looks read best with the noise well below the authored ceiling; the
   dial still runs its full 0-2 range for anyone who wants more. */
const DEFAULT_TEXTURE = 0.25;

function newLayer(overrides = {}) {
  return {
    lid: `L${++G.layerSeq}`,
    presetId: null,
    customId: null,      // set when the pick came from a saved custom aesthetic
    variant: null,
    sets: {},
    events: [],          // the user's diff on the seeded event schedule
    /* Caption cues: the words, when they show and where they sit. They are
       content, not a diff against anything the seed drew, so they get their own
       list rather than riding `events` as add-ops the way they used to. That
       separation is the whole point - a caption style is an aesthetic you try
       on, the script underneath it is work you did once and should never lose
       to a change of style. layerSpec() turns them back into the add-ops the
       engine has always read. */
    cues: [],
    seed: 1 + Math.floor(Math.random() * 99999),
    intensity: 1.0,
    texture: DEFAULT_TEXTURE,
    enabled: true,
    /* Section master switches: false mutes this layer's whole picture / sound
       chain in one click, leaving every per-effect power switch where it was -
       so flipping a section back on restores the arrangement, not a blank
       slate. Layers saved before these existed simply lack the keys, and
       everything below reads absence as on. */
    picture: true,
    sound: true,
    ...overrides,
  };
}

const LAYER_FIELDS = ['presetId', 'customId', 'variant', 'sets', 'events', 'cues', 'seed',
  'intensity', 'texture', 'picture', 'sound'];

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

/* Layers actually worth rendering, bottom first. A layer with both sections
   muted would only cost an encode to change nothing, so it does not count. */
function liveLayers(sess) {
  return (sess.layers || []).filter((l) => l.enabled && l.presetId
    && (l.picture !== false || l.sound !== false));
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
  loadHistory();
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
  syncHistoryChip();
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
  // The editor was showing the last tab's timeline. Closed before anything is
  // rebuilt, so a pane that wants to open it for *this* tab still can.
  if (damageEditorOpen()) closeDamageEditor();

  $('drop-screen').classList.add('hidden');
  $('workspace').classList.remove('hidden');
  $('file-chip-text').textContent = sess.audioSource
    ? `${basename(sess.file.path)} · audio · ${(sess.file.sr / 1000).toFixed(1)} kHz ${sess.file.channels === 1 ? 'mono' : 'stereo'} · ${sess.file.duration.toFixed(1)}s`
    : `${basename(sess.file.path)} · ${sess.file.width}×${sess.file.height} · ${sess.file.duration.toFixed(1)}s`;
  $('file-chip').title = `${sess.file.path}\nClick to show it in the Finder`;
  $('file-chip').classList.remove('hidden');

  $('timecode').value = fmtTimecode(sess.previewT);
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
  refreshCaptionLaunch();   // the button's count belongs to this tab

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
    // A caption style saved as a custom keeps its script too: "the version I
    // made" is the words as much as the knobs.
    cues: (state.cues || []).map((c) => ({ ...c })),
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
  return migrateCues(newLayer({
    presetId: c.base,
    customId: c.id,
    variant: c.variant || null,
    sets: { ...(c.sets || {}) },
    events: (c.events || []).map((e) => ({ ...e })),
    cues: (c.cues || []).map((x) => ({ ...x })),
    seed: typeof c.seed === 'number' ? c.seed : 1 + Math.floor(Math.random() * 99999),
    intensity: typeof c.intensity === 'number' ? c.intensity : 1,
    texture: typeof c.texture === 'number' ? c.texture : 1,
  }));
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
  state.cues = (c.cues || []).map((x) => ({ ...x }));
  migrateCues(activeLayer(state));
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
    || JSON.stringify(c.events || []) !== JSON.stringify(state.events || [])
    || JSON.stringify(c.cues || []) !== JSON.stringify(state.cues || []);
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
    cues: (l.cues || []).map((c) => ({ ...c })),
    seed: l.seed,
    intensity: l.intensity,
    texture: l.texture,
    enabled: l.enabled !== false,
    // Only when off, so stacks saved before these switches existed compare
    // equal to a recapture and do not wrongly show "· edited".
    ...(l.picture === false ? { picture: false } : {}),
    ...(l.sound === false ? { sound: false } : {}),
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
  return migrateCues(newLayer({
    presetId: sl.base,
    // A custom the user has since deleted leaves the numbers intact and just
    // stops claiming its name.
    customId: sl.customId && customById(sl.customId) ? sl.customId : null,
    variant: sl.variant || null,
    sets: { ...(sl.sets || {}) },
    events: (sl.events || []).map((e) => ({ ...e })),
    cues: (sl.cues || []).map((c) => ({ ...c })),
    seed: typeof sl.seed === 'number' ? sl.seed : 1 + Math.floor(Math.random() * 99999),
    intensity: typeof sl.intensity === 'number' ? sl.intensity : 1,
    texture: typeof sl.texture === 'number' ? sl.texture : 1,
    enabled: sl.enabled !== false,
    picture: sl.picture !== false,
    sound: sl.sound !== false,
  }));
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
    : presetSubline(p);
}

/* "1964 · genre · kaiju and tokusatsu · 35 mm film": the year, the shelf and
   the two facets that say what the thing IS, for a name that only says what
   it is made of. */
function presetSubline(p) {
  const bits = [p.era, p.family];
  const f = p.facets || {};
  if (f.genre && f.genre.length) bits.push(facetLabel('genre', f.genre[0]).toLowerCase());
  const medium = (f.medium || []).filter((m) => m !== 'film' && m !== 'broadcast');
  const m = medium[0] || (f.medium || [])[0];
  if (m) bits.push(facetLabel('medium', m).toLowerCase().replace(/ \(.*\)$/, ''));
  return bits.join(' · ');
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
    if (U.info.last) U.latest = U.info.last;
    U.staged = U.info.staged || null;
  } catch (_) { /* leave the chip reading v- */ }
  setVersionChip();
  syncUpdateButton();
}

/* Re-read the persisted answer each time so a staged download survives an app
   restart. The hourly and focus checks are cheap unless the 24-hour network
   interval has elapsed, in which case the main process refreshes GitHub. */
async function automaticUpdateCheck() {
  if (automaticUpdateBusy || U.busy) return;
  automaticUpdateBusy = true;
  try {
    U.info = await window.aesth.updateInfo();
    if (U.info.last) U.latest = U.info.last;
    U.staged = U.info.staged || null;
    setVersionChip();
    if (U.info.stale) U.latest = await window.aesth.updateCheck({});
    syncUpdateButton();
  } catch (_) {
    // Background checks stay quiet. Opening About still shows a manual error.
  } finally {
    automaticUpdateBusy = false;
  }
}

async function initUpdates() {
  if (!U.info) await loadVersion();
  window.aesth.onUpdateProgress(onUpdateProgress);
  await automaticUpdateCheck();
  if (updatePollTimer) return;
  updatePollTimer = setInterval(automaticUpdateCheck, UPDATE_POLL_MS);
  window.addEventListener('focus', automaticUpdateCheck);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') automaticUpdateCheck();
  });
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

function openAbout(refresh = true) {
  $('about-modal').classList.remove('hidden');
  $('about-version').textContent = U.info
    ? `version ${U.info.version}${U.info.packaged ? '' : ' · dev checkout'}`
    : 'version unknown';
  $('about-bar').classList.add('hidden');
  paintAbout();
  // Like Clawnsole and Pawvis, opening About is an explicit request for a fresh
  // answer. Do not replace a verified download that is already waiting.
  if (refresh && !U.staged && !U.busy) checkForUpdates({ force: true });
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
  // The download path refreshes GitHub before choosing its asset, so starting
  // another About check here would race it and paint two competing answers.
  openAbout(false);
  if (U.latest && U.latest.available && U.latest.installable) await downloadUpdate();
}

function wireUpdates() {
  $('btn-version').addEventListener('click', () => openAbout());
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

// ── finding presets: search, facets, guide, recents ─────────────────
/* The engine owns the vocabulary (aesthetician/taxonomy.py) and ships it in
   the schema: phrase folds ("black and white" -> "bw"), synonyms ("monster"
   also finds kaiju), stop words, decade words, facet labels and the weight of
   a hit in each field. The renderer mirrors the engine's tokenizing and
   scoring exactly, so `aesthetician list` and the app agree on what a query
   finds. Every token a person types has to land somewhere (AND, not OR);
   a token matches a whole word or the start of one, so "adventur" already
   finds adventure. */
function taxonomy() {
  return (G.schema && G.schema.taxonomy)
    || { phrases: {}, synonyms: {}, stop: [], decades: {}, weights: {}, facets: [] };
}

let phraseFold = { src: null, re: null, stop: new Set() };
function normalizeSearchText(text) {
  const tx = taxonomy();
  if (phraseFold.src !== tx.phrases) {
    const keys = Object.keys(tx.phrases)
      .sort((a, b) => b.length - a.length)
      .map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    phraseFold = { src: tx.phrases, re: keys.length ? new RegExp(keys.join('|'), 'g') : null,
      stop: new Set(tx.stop || []) };
  }
  let t = String(text || '').toLowerCase().replace(/’/g, "'");
  t = t.replace(/\b(\d{2,4})'s\b/g, '$1s');          // 80's -> 80s
  if (phraseFold.re) t = t.replace(phraseFold.re, (m) => tx.phrases[m]);
  return t;
}

/* "hong-kong crime" -> ["hong-kong", "hong", "kong", "crime"]: a hyphenated
   phrase stays whole AND splits, digits stick to letters ("16mm", "1985"). */
function searchTokens(text) {
  normalizeSearchText('');   // make sure the stop set is built
  const out = [];
  for (let raw of normalizeSearchText(text).split(/[^a-z0-9\-.]+/)) {
    raw = raw.replace(/^[-.]+|[-.]+$/g, '');
    if (!raw) continue;
    if (raw.includes('-')) {
      out.push(raw);
      for (const p of raw.split('-')) if (p) out.push(p);
    } else {
      out.push(raw);
    }
  }
  return out.filter((t) => t && !phraseFold.stop.has(t));
}

/* "1985" -> ["1985", "1980s", "85s"? no: "80s", "eighties"], matching the engine. */
function eraTokens(era) {
  const m = /^(\d{4})/.exec(String(era || ''));
  if (!m) return era ? [String(era)] : [];
  const year = parseInt(m[1], 10);
  const dec = Math.floor(year / 10) * 10;
  const out = [String(year), `${dec}s`, `${String(dec % 100).padStart(2, '0')}s`];
  const word = (taxonomy().decades || {})[String(dec)];
  if (word) out.push(word);
  return out;
}

function facetLabel(facetId, valueId) {
  const f = (taxonomy().facets || []).find((x) => x.id === facetId);
  const v = f && f.values.find((x) => x.id === valueId);
  return v ? v.label : valueId;
}

/* Per-field token lists for one preset, built once and cached: the list is
   rebuilt on every keystroke and tokenizing 800 descriptions each time would
   be felt. */
function searchFields(p) {
  let f = G.searchIndex.get(p.id);
  if (f) return f;
  const facetWords = [];
  for (const [fid, vals] of Object.entries(p.facets || {})) {
    for (const vid of vals) { facetWords.push(vid); facetWords.push(facetLabel(fid, vid)); }
  }
  f = {
    name: searchTokens(p.name),
    id: searchTokens(p.id.replace(/-/g, ' ')),
    era: eraTokens(p.era),
    family: searchTokens(p.family),
    tagline: searchTokens(p.tagline || ''),
    tags: searchTokens((p.tags || []).join(' ')),
    keywords: searchTokens((p.keywords || []).join(' ')),
    facets: searchTokens(facetWords.join(' ')),
    desc: searchTokens(p.desc || ''),
    variants: searchTokens((p.variants || []).map((v) => `${v.name} ${v.id.replace(/-/g, ' ')}`).join(' ')),
  };
  G.searchIndex.set(p.id, f);
  return f;
}

/* A query becomes one group of alternatives per token, each with how much a
   hit on it is worth: "80s" also tries "1980s" and "eighties" at full value,
   "monster" also tries "kaiju" and "creature" at a discount, so the word you
   typed always outranks the words it merely implies. */
function expandQuery(query) {
  const tx = taxonomy();
  const syn = tx.synonyms || {};
  const synFactor = tx.synonym_factor == null ? 0.7 : tx.synonym_factor;
  const decadeWords = Object.fromEntries(Object.entries(tx.decades || {}).map(([k, v]) => [v, k]));
  const groups = [];
  for (const tok of searchTokens(query)) {
    const alts = [[tok, 1]];
    const seen = new Set([tok]);
    const m = /^(\d{2}|\d{4})s$/.exec(tok);
    let dec = null;
    if (m) {
      const n = parseInt(m[1], 10);
      dec = Math.floor((n < 100 ? 1900 + n : n) / 10) * 10;
    } else if (decadeWords[tok]) {
      dec = parseInt(decadeWords[tok], 10);
    }
    /* A decade is a fact about the preset, scored against its era only: the
       keyword "eighties" must not outrank the tag "80s" for the same decade. */
    if (dec != null) {
      for (const t of eraTokens(String(dec))) {
        if (t !== String(dec) && !seen.has(t)) { seen.add(t); alts.push([t, 1]); }   // "80s" is not the year 1980
      }
      groups.push({ alts, era: true });
      continue;
    }
    for (const s of syn[tok] || []) if (!seen.has(s)) { seen.add(s); alts.push([s, synFactor]); }
    groups.push({ alts, era: false });
  }
  return groups;
}

const DEFAULT_FIELD_WEIGHTS = { name: 10, tagline: 6, keywords: 5, tags: 4, facets: 3, id: 3, era: 3,
  family: 2, variants: 1.5, desc: 1 };

/* 0 when any token group misses; otherwise the summed weighted best hits. */
function searchScore(p, groups) {
  if (!groups.length) return 1;
  const tx = taxonomy();
  const weights = Object.keys(tx.weights || {}).length ? tx.weights : DEFAULT_FIELD_WEIGHTS;
  const prefixFactor = tx.prefix_factor == null ? 0.6 : tx.prefix_factor;
  const coverageBonus = tx.name_coverage_bonus == null ? 2 : tx.name_coverage_bonus;
  const fields = searchFields(p);
  let total = 0;
  let nameHits = 0;
  for (const { alts, era } of groups) {
    let best = 0;
    for (const [fname, ftoks] of Object.entries(fields)) {
      if (era && fname !== 'era') continue;
      const w = weights[fname] == null ? 1 : weights[fname];
      if (w <= best) continue;      // nothing in this field can beat what we have
      let hit = 0;
      for (const ft of ftoks) {
        for (const [a, factor] of alts) {
          if (ft === a) hit = Math.max(hit, w * factor);
          else if (a.length >= 3 && ft.startsWith(a)) hit = Math.max(hit, w * factor * prefixFactor);
        }
        if (hit >= w) break;
      }
      if (hit > 0 && fname === 'name') nameHits++;
      best = Math.max(best, hit);
    }
    if (best <= 0) return 0;
    total += best;
  }
  // A query that covers most of a short name beats one word buried in a long
  // one: "noir" is Film Noir before it is Trip-Hop Noir Promo.
  const nName = new Set(fields.name).size || 1;
  return total + coverageBonus * nameHits / nName;
}

function passesFacets(p) {
  for (const [fid, vid] of Object.entries(G.filterFacets || {})) {
    if (vid && !((p.facets || {})[fid] || []).includes(vid)) return false;
  }
  return true;
}

/* The facet dropdowns: one native select per facet, listing only values that
   still have presets under everything ELSE that is selected, with counts, so a
   choice can never lead to an empty list. */
function buildFacetRow() {
  const row = $('facet-row');
  if (!row || !G.schema) return;
  row.innerHTML = '';
  const live = Object.values(G.filterFacets || {}).some(Boolean);
  row.classList.toggle('hidden', !(G.refineOpen || live) || G.guideOpen);
  const presets = Object.values(G.schema.presets);
  const q = ($('preset-search').value || '');
  const groups = expandQuery(q);
  for (const facet of taxonomy().facets || []) {
    const current = (G.filterFacets || {})[facet.id] || '';
    // Everything but this facet decides what is countable.
    const others = { ...(G.filterFacets || {}) };
    delete others[facet.id];
    const pool = presets.filter((p) => {
      if (G.favOnly && !G.favs.has(p.id)) return false;
      if (G.audioOnly && !isAudioOnly(p)) return false;
      if (G.filterFamilies.size && !G.filterFamilies.has(p.family)) return false;
      if (G.filterEra && decadeOf(p) !== G.filterEra) return false;
      for (const [fid, vid] of Object.entries(others)) {
        if (vid && !((p.facets || {})[fid] || []).includes(vid)) return false;
      }
      return !q || searchScore(p, groups) > 0;
    });
    const counts = {};
    for (const p of pool) for (const v of (p.facets || {})[facet.id] || []) counts[v] = (counts[v] || 0) + 1;
    const sel = document.createElement('select');
    sel.className = 'facet' + (current ? ' active' : '');
    sel.dataset.facet = facet.id;
    sel.title = facet.hint || facet.label;
    const any = document.createElement('option');
    any.value = '';
    any.textContent = `Any ${facet.label.toLowerCase()}`;
    sel.appendChild(any);
    for (const v of facet.values) {
      const n = counts[v.id] || 0;
      if (!n && v.id !== current) continue;
      const o = document.createElement('option');
      o.value = v.id;
      o.textContent = `${v.label} (${n})`;
      if (v.id === current) o.selected = true;
      sel.appendChild(o);
    }
    sel.onchange = () => {
      G.filterFacets = { ...(G.filterFacets || {}), [facet.id]: sel.value };
      G.guideOpen = false;
      buildFilterBar();
      buildPresetList();
    };
    row.appendChild(sel);
  }
}

/* ── recents ──────────────────────────────────────────────────────── */
function noteRecent(pid) {
  if (!pid || !G.schema || !G.schema.presets[pid]) return;
  G.recents = [pid, ...G.recents.filter((x) => x !== pid)].slice(0, RECENTS_MAX);
  saveStore();
}

/* ── the guide: curated collections and recipes ───────────────────── */
function collections() {
  return (G.schema && G.schema.collections) || [];
}

function findRecipe(cid, rid) {
  const c = collections().find((x) => x.id === cid);
  return c && (c.recipes || []).find((r) => r.id === rid);
}

/* A recipe is a stack the library ships: the same preset seen through a
   second carrier, applied bottom layer first, exactly like a saved stack. */
function applyRecipe(cid, rid, opts = {}) {
  const r = findRecipe(cid, rid);
  if (!r) return;
  const usable = r.layers.filter((id) => G.schema.presets[id]);
  if (!usable.length) return;
  state.layers = usable.map((id) => layerFromSaved({ base: id }));
  state.activeLayer = state.layers.length - 1;
  state.stackId = null;
  for (const id of usable) noteRecent(id);
  syncMasterDials();
  syncSelection();
  renderTabs();
  buildParamPane();
  buildLayersPanel();
  schedulePreview(true, opts.previewDelay);
}

async function pickRecipe(cid, rid) {
  const r = findRecipe(cid, rid);
  if (!r) return;
  if (!sessionHasWork()) { applyRecipe(cid, rid); return; }
  const many = (state.layers || []).filter((l) => l.presetId).length;
  const choice = await askChoice({
    title: `Apply “${r.title}” over this stack?`,
    sub: `This tab has ${many} layer${many === 1 ? '' : 's'} set up. Applying a recipe replaces all of them.`,
    choices: [
      { key: 'go', label: 'Replace stack', className: 'accent' },
      { key: null, label: 'Cancel' },
    ],
  });
  if (choice === 'go') applyRecipe(cid, rid);
}

function recipeCard(c, r) {
  const usable = r.layers.filter((id) => G.schema.presets[id]);
  const top = usable[usable.length - 1];
  const card = document.createElement('div');
  card.className = 'preset-card recipe' + (usable.length ? '' : ' broken');
  card.dataset.pid = `recipe:${c.id}/${r.id}`;
  const chain = r.layers.map((id) => (G.schema.presets[id] ? G.schema.presets[id].name : id)).join(' → ');
  card.title = `${r.title}\n\nRecipe · ${chain}${r.note ? `\n\n${r.note}` : ''}`;
  let holder;
  if (top) {
    holder = thumbFor(G.schema.presets[top]);
  } else {
    holder = document.createElement('div');
    holder.className = 'p-thumb empty';
  }
  const badge = document.createElement('span');
  badge.className = 's-badge recipe';
  badge.textContent = '✦';
  badge.title = 'Recipe: a ready-made stack';
  holder.appendChild(badge);
  card.appendChild(holder);
  const text = document.createElement('div');
  text.className = 'p-text';
  const name = document.createElement('span');
  name.className = 'p-name';
  name.textContent = r.title;
  const meta = document.createElement('span');
  meta.className = 'p-meta';
  meta.textContent = `recipe · ${usable.length} layer${usable.length === 1 ? '' : 's'}`;
  const tl = document.createElement('span');
  tl.className = 'p-tag';
  tl.textContent = chain;
  text.appendChild(name);
  text.appendChild(meta);
  text.appendChild(tl);
  card.appendChild(text);
  card.onclick = () => { if (usable.length) pickRecipe(c.id, r.id); };
  return card;
}

/* Guide mode replaces the library list with the collections, each a header
   with its blurb, its presets best-first and its recipes. The search box
   narrows collections by title, blurb or member names. */
function buildGuideList(list, q, addNav) {
  const groups = expandQuery(q);
  const ps = G.schema.presets;
  const inCollection = (c) => {
    if (!q) return true;
    const own = searchTokens(`${c.title} ${c.blurb}`);
    const okOwn = groups.every(({ alts }) => own.some((t) => alts.some(([a]) => t === a || (a.length >= 3 && t.startsWith(a)))));
    if (okOwn) return true;
    return c.presets.some((id) => ps[id] && searchScore(ps[id], groups) > 0);
  };
  const shown = collections().filter(inCollection);
  const GROUP_LABELS = { looks: 'MAKE IT LOOK LIKE', media: 'A PARTICULAR MEDIUM', eras: 'AN ERA OF TELEVISION', sound: 'A PARTICULAR SOUND' };
  let group = null;
  for (const c of shown) {
    if (c.group !== group) {
      group = c.group;
      const gl = document.createElement('div');
      gl.className = 'family-label guide-group';
      gl.textContent = GROUP_LABELS[group] || String(group).toUpperCase();
      list.appendChild(gl);
    }
    const head = document.createElement('div');
    head.className = 'guide-head';
    const title = document.createElement('div');
    title.className = 'guide-title';
    title.textContent = c.title;
    const blurb = document.createElement('div');
    blurb.className = 'guide-blurb';
    blurb.textContent = c.blurb;
    head.appendChild(title);
    head.appendChild(blurb);
    list.appendChild(head);
    for (const id of c.presets) {
      const p = ps[id];
      if (!p) continue;
      list.appendChild(presetCard(p, { showFamily: true }));
      addNav(p.id);
    }
    for (const r of c.recipes || []) list.appendChild(recipeCard(c, r));
  }
  if (!shown.length) {
    const empty = document.createElement('div');
    empty.className = 'list-empty';
    empty.textContent = q ? 'No collection matches.' : 'No collections in this build.';
    list.appendChild(empty);
  }
}

/* What to try when a search finds nothing: a few asks the library answers well. */
const SEARCH_SUGGESTIONS = ['80s adventure movie', 'kaiju', 'home video', 'security camera', 'silent film',
  'cassette', 'news 1975', 'anime vhs'];

// ── filter bar (family chips + era decades) ─────────────────────────
function decadeOf(p) {
  const y = parseInt(p.era, 10);
  return Number.isFinite(y) ? `${Math.floor(y / 10) * 10}s` : null;
}

function buildFilterBar() {
  const presets = Object.values(G.schema.presets);

  const chips = $('family-chips');
  chips.innerHTML = '';
  if (collections().length) {
    const guide = document.createElement('span');
    guide.className = 'chip guide-chip' + (G.guideOpen ? ' sel' : '');
    guide.textContent = '✦ Guide';
    guide.title = 'Starting points: “make it look like…” collections and ready-made stacks';
    guide.onclick = () => {
      G.guideOpen = !G.guideOpen;
      if (G.guideOpen) { G.favOnly = false; G.customOnly = false; G.stackOnly = false; }
      buildFilterBar(); buildPresetList();
    };
    chips.appendChild(guide);
  }
  /* The facet row is worth its height when you are narrowing and worth
     folding away when you are scrolling; a live facet keeps it open. */
  const facetsLive = Object.values(G.filterFacets || {}).some(Boolean);
  const refine = document.createElement('span');
  refine.className = 'chip refine-chip' + (facetsLive ? ' sel' : G.refineOpen ? ' open' : '');
  refine.textContent = facetsLive ? '⌕ Refine ●' : '⌕ Refine';
  refine.title = 'Narrow by medium, genre, region, condition and color';
  refine.onclick = () => {
    if (facetsLive && G.refineOpen) { G.filterFacets = {}; }
    else G.refineOpen = !G.refineOpen;
    saveStore();
    buildFilterBar(); buildPresetList();
  };
  chips.appendChild(refine);
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
      if (G.customOnly) { G.favOnly = false; G.stackOnly = false; G.audioOnly = false; }
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
      if (G.stackOnly) { G.favOnly = false; G.customOnly = false; G.audioOnly = false; }
      buildFilterBar(); buildPresetList();
    };
    chips.appendChild(sc);
  }
  const all = document.createElement('span');
  all.className = 'chip' + (G.filterFamilies.size || G.audioOnly || G.favOnly || G.customOnly || G.stackOnly || G.guideOpen ? '' : ' sel');
  all.textContent = 'All';
  all.onclick = () => {
    G.filterFamilies.clear();
    G.favOnly = false;
    G.customOnly = false;
    G.stackOnly = false;
    G.audioOnly = false;
    G.guideOpen = false;
    buildFilterBar(); buildPresetList();
  };
  chips.appendChild(all);

  const audioCount = presets.filter(isAudioOnly).length;
  const audio = document.createElement('span');
  audio.className = 'chip audio-chip' + (G.audioOnly ? ' sel' : '');
  audio.textContent = `♪ Audio ${audioCount}`;
  audio.title = 'Show presets that treat audio and leave the picture untouched';
  audio.onclick = () => {
    G.audioOnly = !G.audioOnly;
    if (G.audioOnly) {
      G.filterFamilies.clear();
      G.customOnly = false;
      G.stackOnly = false;
    }
    buildFilterBar();
    buildPresetList();
  };
  chips.appendChild(audio);

  const fams = [...new Set(presets.map((p) => p.family))]
    .filter((f) => f !== 'audio')
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
      G.audioOnly = false;
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

  $('preset-search').placeholder = G.guideOpen
    ? 'Search the guide…'
    : `Search ${presets.length} aesthetics…`;
  buildFacetRow();
}

function passesFilters(p) {
  if (G.favOnly && !G.favs.has(p.id)) return false;
  if (G.audioOnly && !isAudioOnly(p)) return false;
  if (G.filterFamilies.size && !G.filterFamilies.has(p.family)) return false;
  if (G.filterEra && decadeOf(p) !== G.filterEra) return false;
  if (!passesFacets(p)) return false;
  return true;
}

function anyFilterActive() {
  return G.favOnly || G.customOnly || G.stackOnly || G.audioOnly || G.filterFamilies.size > 0
    || !!G.filterEra || !!$('preset-search').value
    || Object.values(G.filterFacets || {}).some(Boolean) || G.guideOpen;
}

function clearFilters() {
  G.favOnly = false;
  G.customOnly = false;
  G.stackOnly = false;
  G.audioOnly = false;
  G.filterFamilies.clear();
  G.filterEra = '';
  G.filterFacets = {};
  G.guideOpen = false;
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
const FAMILY_ORDER = ['adjust', 'genre', 'channel', 'vhs', 'film', 'archive', 'western', 'arthouse',
  'modern', 'broadcast', 'cartoon', 'digital', 'social', 'world', 'process', 'decay', 'exhibition',
  'print', 'transmission', 'stylized', 'captions', 'audio'];

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
   into whichever row the pointer is over. The whole library never animates at once. */
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

function presetCard(p, opts = {}) {
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
  meta.textContent = `${p.era}${opts.showFamily ? ` · ${p.family}` : ''}${nv ? ` · ${nv} variant${nv === 1 ? '' : 's'}` : ''}`;
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
  const q = ($('preset-search').value || '').trim();
  const groups = expandQuery(q);
  const scoreOf = (p) => (q ? searchScore(p, groups) : 1);
  const matches = (p) => passesFilters(p) && scoreOf(p) > 0;

  /* ↑/↓ walk this: the ids the eye can actually see, top to bottom. A favorite
     is rendered twice (its row at the top, and again inside its family) but is
     navigated once, at the first of the two, so a run down the list never
     re-renders the same preset. */
  const nav = [];
  const navSeen = new Set();
  const addNav = (pid) => { if (!navSeen.has(pid)) { navSeen.add(pid); nav.push(pid); } };

  /* The guide is its own list: collections instead of families. */
  if (G.guideOpen) {
    buildGuideList(list, q, addNav);
    G.navOrder = nav;
    return;
  }

  /* Saved stacks lead, then saved customs: the things this user made, biggest
     arrangement first. Stacks stay out of `nav` on purpose - ↑/↓ auditions one
     aesthetic against the rest of your stack, and applying a saved stack
     replaces every layer, which is not something a held-down arrow key should
     be able to do. */
  const stackRows = G.stacks.filter((k) => {
    if (G.favOnly || G.customOnly || G.audioOnly) return false;
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
    if (G.audioOnly && !isAudioOnly(G.schema.presets[c.base])) return false;
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

  // Recently picked aesthetics lead an unfiltered list: with hundreds of rows,
  // the one you used yesterday should not need finding twice.
  const recentRows = anyFilterActive() ? [] : G.recents.map((id) => G.schema.presets[id]).filter(Boolean);
  if (recentRows.length) {
    const rl = document.createElement('div');
    rl.className = 'family-label recents';
    rl.innerHTML = `◷ RECENT <span class="count">${recentRows.length}</span>`;
    list.appendChild(rl);
    for (const p of recentRows) { list.appendChild(presetCard(p, { showFamily: true })); addNav(p.id); }
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

  /* A search is a ranked list, not a tour of the families: the best answers
     first, whatever shelf they live on, with the family named on each row. */
  if (q) {
    const hits = presets.filter(matches)
      .map((p) => [scoreOf(p), p])
      .sort((a, b) => (b[0] - a[0]) || (famRank(a[1].family) - famRank(b[1].family)) || a[1].id.localeCompare(b[1].id));
    if (hits.length) {
      const rl = document.createElement('div');
      rl.className = 'family-label results';
      rl.innerHTML = `RESULTS <span class="count">${hits.length}</span>`;
      list.appendChild(rl);
      for (const [, p] of hits) { list.appendChild(presetCard(p, { showFamily: true })); addNav(p.id); }
      shown += hits.length;
    }
  }
  for (const p of (q ? [] : presets)) {
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
    empty.textContent = q ? `Nothing matches “${q}”.` : 'No aesthetics match.';
    if (q) {
      const tip = document.createElement('div');
      tip.className = 'list-tip';
      tip.textContent = 'Try fewer words, or one of these:';
      empty.appendChild(tip);
      const row = document.createElement('div');
      row.className = 'suggest-row';
      for (const sug of SEARCH_SUGGESTIONS) {
        const c = document.createElement('span');
        c.className = 'chip';
        c.textContent = sug;
        c.onclick = () => { $('preset-search').value = sug; buildFilterBar(); buildPresetList(); };
        row.appendChild(c);
      }
      empty.appendChild(row);
    }
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
  const nc = (l.cues || []).length;
  if (isCaptionLayer(l)) bits.push(nc ? `${nc} caption${nc === 1 ? '' : 's'}` : 'no captions yet');
  if (l.variant) bits.push(l.variant);
  const n = Object.keys(l.sets || {}).length;
  if (n) bits.push(`${n} tweak${n === 1 ? '' : 's'}`);
  if (l.intensity !== 1) bits.push(`int ${l.intensity.toFixed(2)}`);
  if (l.texture !== DEFAULT_TEXTURE) bits.push(`tex ${l.texture.toFixed(2)}`);
  if (l.picture === false) bits.push('picture off');
  if (l.sound === false) bits.push('sound off');
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
    const cap = isCaptionLayer(l);
    const row = document.createElement('div');
    row.className = 'layer-row'
      + (i === state.activeLayer ? ' sel' : '')
      + (cap ? ' cap' : '')
      + (l.enabled ? '' : ' off');
    row.draggable = true;
    row.dataset.lid = l.lid;
    /* Where the caption track sits in the stack is the whole answer to "does
       the tape chew the lettering": above the look it stays crisp, below it
       gets treated along with everything else. Worth saying on the row, since
       dragging it is the only way to choose. */
    if (cap) {
      row.title = i === layers.length - 1
        ? 'Captions render last, so they stay crisp over the treated picture. '
          + 'Drag below a look to have that look chew them.'
        : 'Captions render here, so every layer above treats the lettering too. '
          + 'Drag to the bottom of the list to keep them crisp.';
    }

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
    if (cap) {
      const badge = document.createElement('span');
      badge.className = 'l-cc';
      badge.textContent = 'CC';
      badge.title = 'The caption track: the words, and whichever style is drawing them';
      name.appendChild(badge);
    }
    name.appendChild(document.createTextNode(layerLabel(l)));
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
  // A session has one caption track. Stacking a caption style onto a stack
  // that already has one restyles it instead of growing a second script.
  if (isCaptionStyle(pid) && captionLayer(state)) { applyCaptionStyle(pid, opts); return; }
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
  /* The one thing a pick does not sweep away: a script, when what is arriving
     is another way of drawing it. Everything else on the layer described the
     old style and cannot mean anything under the new one. */
  const l = activeLayer(state);
  const keepCues = isCaptionStyle(pid) && isCaptionLayer(l) && (l.cues || []).length > 0;
  state.presetId = pid;
  state.customId = null;   // picking a stock preset leaves any custom behind
  state.stackId = null;    // and the arrangement is no longer the saved one
  state.variant = null;
  state.sets = {};
  state.events = [];
  if (!keepCues) state.cues = [];
  // A fresh pick starts at the resting texture, like a fresh layer: the dial
  // was describing the old look, and most looks read best dialled back.
  state.texture = DEFAULT_TEXTURE;
  syncMasterDials();
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
    || (l.cues || []).length > 0
    || l.intensity !== 1
    || l.texture !== DEFAULT_TEXTURE;
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
  const nc = (l.cues || []).length;
  if (nc) bits.push(`${nc} caption${nc === 1 ? '' : 's'}`);
  const ne = (l.events || []).length;
  if (ne) bits.push(`${ne} timeline edit${ne === 1 ? '' : 's'}`);
  if (l.variant) bits.push(`the ${l.variant} variant`);
  if (l.intensity !== 1) bits.push(`intensity ${l.intensity.toFixed(2)}`);
  if (l.texture !== DEFAULT_TEXTURE) bits.push(`texture ${l.texture.toFixed(2)}`);
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
  if (!stack && !opts.nav && !isCustomId(id)) noteRecent(id);
  /* A caption style is a way of drawing a script, not a layer's worth of work
     to be replaced. With a track already in the stack the pick goes to it,
     wherever it sits and whatever is selected: nothing is lost, so nothing is
     asked, and one caption track never quietly becomes two. */
  if (!stack && isCaptionStyle(id) && captionLayer(state)) {
    applyCaptionStyle(id, opts);
    return;
  }
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
  // Same rule as a click: a caption style dresses the track it finds rather
  // than collapsing the stack down onto a fresh, wordless one.
  if (isCaptionStyle(id) && captionLayer(state)) { applyCaptionStyle(id); return; }
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

/* Moving the highlight is a class flip, not a rebuild of the full library - which is
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
  await pickFromList(order[next], { previewDelay: NAV_PREVIEW_MS, nav: true });
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

function variantOverridesOf(l) {
  if (!l || !l.variant) return {};
  const p = G.schema.presets[l.presetId];
  const v = p && (p.variants || []).find((x) => x.id === l.variant);
  return v ? { ...v.video, ...v.audio } : {};
}

function variantOverrides() {
  return variantOverridesOf(activeLayer(state));
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
    : presetSubline(p);
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
  /* A caption style is half aesthetic, half editor: the words are a track of
     their own, so the pane leads with the door to them. Landing on a caption
     style with nothing written yet opens that door by itself, once per layer.
     The knobs below stay exactly what they were - per-style tweaking is the
     other half of the point. */
  if (p.family === 'captions' && !state.audioSource && state.file) {
    holder.appendChild(captionLaunchCard());
    const al = activeLayer(state);
    if (al && !al.capSeen) {
      al.capSeen = true;
      if (!captionCueCount() && !damageEditorOpen()) openDamageEditor('caption');
    }
  }
  const sections = state.audioSource
    ? [['SOUND', p.audio, 'sound']]        // the video chain cannot apply here
    : [['PICTURE', p.video, 'picture'], ['SOUND', p.audio, 'sound']];
  if (state.audioSource && p.video.length) {
    const note = document.createElement('div');
    note.className = 'audio-note';
    note.textContent = `Audio source - this preset's ${p.video.length} picture effects are not applied.`;
    holder.appendChild(note);
  }
  for (const [label, chain, field] of sections) {
    if (!chain.length) continue;
    holder.appendChild(chainSection(label, chain, field, vo));
  }
  // The editor's style strip repeats what this pane says about the caption
  // track - which style, which variant, how many tweaks - so it is rebuilt from
  // the same place, and a pill or a knob touched here cannot leave it stale.
  if (captionEditorOpen()) buildCaptionStyles();
}

/* One knob-pane section - the PICTURE or SOUND chain - under a header that
   carries the section's master switch. The switch is a layer field, not a
   spray of per-effect `enabled` overrides: muting the section leaves every
   individual power switch and tweak exactly where the user set it, so turning
   the section back on restores the arrangement rather than a blank slate. */
function chainSection(label, chain, field, vo) {
  const sec = document.createElement('div');
  sec.className = 'chain-sec';
  const l = activeLayer(state);
  const on = l[field] !== false;
  sec.classList.toggle('sec-off', !on);

  const head = document.createElement('div');
  head.className = 'chain-label';
  const power = document.createElement('input');
  power.type = 'checkbox';
  power.className = 'sec-power';
  power.checked = on;
  const noun = field === 'picture' ? 'picture' : 'sound';
  const title = (isOn) => (isOn
    ? `Switch off all ${noun} processing for this layer`
    : `Switch ${noun} processing back on for this layer`);
  power.title = title(on);
  power.onchange = () => {
    l[field] = power.checked;
    sec.classList.toggle('sec-off', !power.checked);
    power.title = title(power.checked);
    offNote.classList.toggle('hidden', power.checked);
    buildLayersPanel();      // the layer row's subtitle names muted sections
    refreshTimeline();       // a muted picture chain plans no damage pins
    schedulePreview();
  };
  head.appendChild(power);
  const name = document.createElement('span');
  name.className = 'chain-name';
  name.textContent = label;
  head.appendChild(name);
  const offNote = document.createElement('span');
  offNote.className = 'sec-off-note';
  offNote.textContent = 'off - untouched';
  offNote.classList.toggle('hidden', on);
  head.appendChild(offNote);
  sec.appendChild(head);

  for (const entry of chainWithKeys(chain)) {
    sec.appendChild(effectCard(entry, vo));
  }
  return sec;
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

  const dkind = placeableKindFor(path);
  if (dkind) {
    const open = document.createElement('button');
    open.className = 'p-edit';
    open.textContent = '◷';
    open.title = `Place ${DAMAGE_KINDS[dkind].label.toLowerCase()} on the timeline`;
    open.onclick = () => openDamageEditor(dkind);
    row.appendChild(open);
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
  if (!state.file) return;
  if (!liveLayers(state).length) {
    /* Nothing left to render. If an aesthetic is picked but every layer or
       section is switched off, the preview on screen belongs to switches that
       are no longer in force - leaving it up would be the checkbox lying. */
    if ((state.layers || []).some((l) => l.presetId)) {
      clearTimeout(previewTimer);
      state.previewJob = null;   // a render already in flight is stale on arrival
      state.treatedSrc = null;
      hideStill();
      videoA.removeAttribute('src'); videoA.load();
      videoB.removeAttribute('src'); videoB.load();
      $('player-empty').classList.remove('hidden');
      $('player-empty').textContent =
        'Everything is switched off - the clip would pass through untouched.';
      refreshTimeline();
    }
    return;
  }
  if (!G.autoPreview && !immediate) return;
  clearTimeout(previewTimer);
  previewTimer = setTimeout(runPreview, delayMs != null ? delayMs : (immediate ? 40 : 550));
}

/* The stack as the engine wants it: bottom layer first, disabled ones dropped.
   Only render-affecting fields, because this is also what the preview cache is
   keyed on - anything cosmetic in here would cost a re-render for nothing.

   Cues rejoin the event diff here and nowhere else: the engine's language has
   not changed (docs/events.md), only where the app keeps the words between
   renders. */
function layerSpec(sess = state) {
  return liveLayers(sess).map((l) => ({
    preset: l.presetId,
    variant: l.variant || null,
    sets: l.sets || {},
    events: [...(l.events || []), ...cueOps(l)],
    seed: l.seed,
    intensity: l.intensity,
    texture: l.texture,
    // Only when off: absent means on, so specs (and the preview-cache keys
    // built from them) are unchanged for every layer that never touched these.
    ...(l.picture === false ? { picture: false } : {}),
    ...(l.sound === false ? { sound: false } : {}),
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
    // The user has a picture; spend the idle cores on making every future seek
    // free. Fire and forget - the window pipeline owes it nothing.
    maybeKickFullPreview();
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
  el.dataset.src = el.dataset.src && el.dataset.src.startsWith('full:') && el.dataset.src.endsWith(src)
    ? el.dataset.src : src;
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
  caption: '#f2e9c8',
};

/* CSS position only: scrubbing moves the head many times a second, and paying
   a repaint of thumbnails and ticks for a pointer move would make the slider
   feel like wading. */
function syncTimelinePlayhead() {
  const total = state.file && state.file.duration;
  if (!total) return;
  const left = (state.previewT / total) * 100;
  const width = (Math.min(G.duration, total) / total) * 100;
  $('strip-playhead').style.left = `${left}%`;
  $('strip-window').style.left = `${left}%`;
  $('strip-window').style.width = `${width}%`;
  // The editor lane carries the same cursor and preview-window span. While
  // the editor is open the main strip is display:none, so without this a
  // seek - Jump to it, the timecode box, selecting an instance - moved a
  // playhead nobody could see and looked like it did nothing.
  if (damageEditorOpen()) {
    $('de-playhead').style.left = `${left}%`;
    $('de-window').style.left = `${left}%`;
    $('de-window').style.width = `${width}%`;
  }
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

/* The default strip stays clean: thumbs, playhead, window. Damage ink lives
   in the editor's own lane now - a strip you navigate by should not look like
   a fault report. The plan still refreshes here, because the editor and the
   per-row badges read it. */
function paintTimelineMarkers(sess) {
  if (sess.id === G.activeId) paintDamageLane();
}

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

/* ── the damage editor ───────────────────────────────────────────────
   One kind of placeable damage at a time, opened from the button beside its
   knob. The panel docks low so the player stays visible - the point of moving
   an instance is watching it land - and everything on it is the engine's own
   plan for the current spec, so the lane never claims a schedule the render
   would disagree with. Spans drag, their edges stretch, empty film adds, and
   selecting an instance seeks the preview to it. */

const DAMAGE_KINDS = {
  dropout: { label: 'Dropouts', effect: 'vhs', hasDur: false },
  tracking_storm: {
    label: 'Tracking Storms', effect: 'vhs', hasDur: true,
    band: { hMin: 0.02, hMax: 0.6, auto: 'the band rolls through the frame' },
  },
  skew_tear: {
    label: 'Skew Tears', effect: 'vhs', hasDur: false,
    band: { hMin: 0.01, hMax: 0.3, auto: 'the tape picks a spot near the top' },
  },
  transport_glitch: {
    label: 'Transport Glitches', effect: 'vcr_transport', hasDur: true,
    band: { hMin: 0.05, hMax: 0.8, auto: 'the shred covers the whole frame' },
  },
  /* Captions are placeable like damage but authored unlike it: there is no
     seeded schedule to edit, every cue is an add, and the form is words and
     placement instead of intensity and bands. */
  caption: { label: 'Captions', effect: 'captions', hasDur: true, caption: true },
};

/* Which param row opens which kind, `#n` repeats included. */
const PLACEABLE_PARAMS = {
  'vhs.dropouts': 'dropout',
  'vhs.tracking_error': 'tracking_storm',
  'vhs.skew_tear': 'skew_tear',
  'vcr_transport.random_glitch_rate': 'transport_glitch',
};

function placeableKindFor(path) {
  return PLACEABLE_PARAMS[path.replace(/#\d+\./, '.')] || null;
}

G.damage = { kind: null, selected: null };

function damageEditorOpen() {
  return !$('damage-editor').classList.contains('hidden');
}

/* The plan numbers its layers by position in the *spec*, which is the live
   layers only - an empty slot or a switched-off layer is not in it. Indexing
   the session's own list with that number would land on the wrong layer the
   moment either exists. */
function evLayerOf(ev) {
  return liveLayers(state)[ev.layer] || activeLayer(state);
}

function findAddOp(l, id) {
  return (l.events || []).find((e) => e.op === 'add' && e.id === id);
}

/* One op per (op, id): re-moving a moved instance replaces its move op rather
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
  refreshTimeline();
  renderTabs();
  refreshCaptionLaunch();
  buildLayersPanel();            // the caption row carries its own cue count
  // refreshTimeline repaints the lane too, but only after it has been out to
  // the engine for a plan. Cues do not need one, so they land now.
  if (captionEditorOpen()) paintDamageLane();
}

/* The captions door in the param pane, and the button in the player controls,
   keep their counts honest without a full pane rebuild - which would yank
   focus from whatever knob or text box was being touched. */
function refreshCaptionLaunch() {
  const n = captionCueCount();
  const card = document.getElementById('cap-launch');
  if (card) {
    const labels = captionLaunchLabels(n);
    const info = card.querySelector('.cap-launch-info');
    const open = card.querySelector('button.accent');
    if (info) info.textContent = labels.info;
    if (open) open.textContent = labels.button;
  }
  const btn = $('btn-captions');
  if (!btn) return;
  btn.classList.toggle('hidden', !(state.file && state.file.path) || state.audioSource);
  btn.classList.toggle('lit', captionEditorOpen());
  const badge = $('cap-count');
  badge.textContent = n ? String(n) : '';
  badge.classList.toggle('hidden', !n);
  btn.title = n
    ? `${n} caption${n === 1 ? '' : 's'} on this clip - write, time, place and restyle them`
    : 'Write burned-in captions for this clip, then try any caption style on them';
}

/* Damage and captions share every gesture in the editor - drag a span, stretch
   an edge, type a start time - so they share these three entry points and part
   ways only at the store underneath. */
function removeEvent(ev) {
  if (ev.kind === 'caption') { removeCue(ev.detail.id); return; }
  const l = evLayerOf(ev);
  const id = ev.detail && ev.detail.id;
  const addOp = id && findAddOp(l, id);
  if (addOp) l.events = l.events.filter((e) => e !== addOp);
  else if (id) {
    l.events = (l.events || []).filter((e) => !(e.id === id && e.op !== 'add'));
    upsertOp(l, { op: 'remove', id, effect: ev.effect, kind: ev.kind });
  }
  if (G.damage.selected === id) G.damage.selected = null;
  afterEventEdit();
}

function moveEvent(ev, t) {
  if (ev.kind === 'caption') { moveCue(ev.detail.id, t); return; }
  const l = evLayerOf(ev);
  const id = ev.detail && ev.detail.id;
  const addOp = id && findAddOp(l, id);
  if (addOp) addOp.t = t;
  else if (id) upsertOp(l, { op: 'move', id, t, effect: ev.effect, kind: ev.kind });
  afterEventEdit();
}

function tuneEvent(ev, detail) {
  if (ev.kind === 'caption') { updateCue(ev.detail.id, detail); return; }
  const l = evLayerOf(ev);
  const id = ev.detail && ev.detail.id;
  const addOp = id && findAddOp(l, id);
  if (addOp) addOp.detail = { ...addOp.detail, ...detail };
  else if (id) upsertOp(l, { op: 'tune', id, detail, effect: ev.effect, kind: ev.kind });
  afterEventEdit();
}

let evAddSeq = 0;
function addEventAt(effect, kind, t, detail = {}) {
  if (kind === 'caption') return addCue(t, detail);
  const l = activeLayer(state);
  l.events = l.events || [];
  const id = `edit:add:${Date.now()}:${++evAddSeq}`;
  l.events.push({ op: 'add', id, effect, kind, t, detail });
  G.damage.selected = id;
  afterEventEdit();
  return id;
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
   commit. */
function evKnob(value, { min = 0, max = 1, step = 0.01 }, commit) {
  const r = document.createElement('input');
  r.type = 'range'; r.className = 'range-fill';
  r.min = min; r.max = max; r.step = step; r.value = value;
  paintRange(r);
  const n = document.createElement('span');
  n.className = 'de-val';
  n.textContent = Number(value).toFixed(2);
  r.oninput = () => { n.textContent = Number(r.value).toFixed(2); paintRange(r); };
  r.onchange = () => commit(parseFloat(r.value));
  return [r, n];
}

/* A knob whose resting state is the tape's own choice: the readout says auto
   until the slider is touched, and the ↺ hands the choice back. Committing
   null is how "auto" goes over the wire. */
function evAutoKnob(value, { min = 0, max = 1, step = 0.01, auto = '' }, commit) {
  const set = value != null;
  const r = document.createElement('input');
  r.type = 'range'; r.className = 'range-fill';
  r.min = min; r.max = max; r.step = step;
  r.value = set ? value : (min + max) / 2;
  paintRange(r);
  const n = document.createElement('span');
  n.className = 'de-val';
  n.textContent = set ? Number(value).toFixed(2) : 'auto';
  n.classList.toggle('auto', !set);
  const back = document.createElement('button');
  back.className = 'de-auto';
  back.textContent = '↺';
  back.title = `Back to auto - ${auto}`;
  back.classList.toggle('hidden', !set);
  if (!set) r.title = `Auto - ${auto}. Drag to take over.`;
  r.oninput = () => {
    n.classList.remove('auto');
    n.textContent = Number(r.value).toFixed(2);
    paintRange(r);
  };
  r.onchange = () => commit(parseFloat(r.value));
  back.onclick = () => commit(null);
  return [r, n, back];
}

/* Bring the preview window to a clip time, but only when it cannot already
   see it: re-rendering a window that had it in frame teaches nothing. */
function seekToShow(t) {
  if (t >= state.previewT && t <= state.previewT + G.duration - 0.2) return;
  seekPreview(Math.max(t - 0.4, 0));
}

/* Timecode: "7.5" or "1:07.5" both mean seconds on the clip. */
function fmtTimecode(t) {
  const m = Math.floor(t / 60);
  const sec = t - m * 60;
  return m ? `${m}:${sec.toFixed(1).padStart(4, '0')}` : sec.toFixed(1);
}

function parseTimecode(text) {
  const t = String(text || '').trim();
  const m = /^(?:(\d+):)?(\d+(?:\.\d+)?)$/.exec(t);
  if (!m) return null;
  return (m[1] ? parseInt(m[1], 10) * 60 : 0) + parseFloat(m[2]);
}

/* Seek to a clip time. When the background full-length preview for this exact
   spec has landed, the seek is a currentTime jump inside it - no re-render.
   Otherwise it falls back to the windowed render everyone knows. */
function seekPreview(t) {
  const max = Math.max(state.file.duration - G.duration, 0);
  state.previewT = Math.min(Math.max(t, 0), max);
  $('timecode').value = fmtTimecode(state.previewT);
  syncTimelinePlayhead();
  if (useFullPreviewSeek()) return;
  schedulePreview();
}

/* Damage is the engine's own schedule, so it can only come from the plan.
   Cues are ours, so they come from the cue list and borrow only the bbox from
   the plan - which means the lane, the form and the cue count are correct the
   moment anything changes, and only the drag handle on the picture waits for
   a render to catch up with it. */
function captionEvents() {
  const bboxes = {};
  for (const e of ((state.eventsPlan && state.eventsPlan.events) || [])) {
    if (e.kind === 'caption' && e.detail && e.detail.id) bboxes[e.detail.id] = e.detail;
  }
  return captionCues()
    .slice()
    .sort((a, b) => a.t - b.t || (a.id < b.id ? -1 : 1))
    .map((c) => {
      const planned = bboxes[c.id] || {};
      return {
        t: c.t, dur: Math.max(Number(c.dur_s) || 0, 0.05), kind: 'caption', effect: 'captions',
        detail: { ...c, bbox: planned.bbox || null, lines: planned.lines },
      };
    });
}

function damageEvents() {
  if (G.damage.kind === 'caption') return captionEvents();
  const plan = state.eventsPlan;
  return ((plan && plan.events) || []).filter((e) => e.kind === G.damage.kind);
}

function openDamageEditor(kind) {
  if (!DAMAGE_KINDS[kind] || !state.file || state.audioSource) return;
  const meta = DAMAGE_KINDS[kind];
  // Reaching for captions is reason enough to have a caption track: a first
  // one arrives wearing a plain, legible style, ready to be tried against the
  // rest of the library from the strip above the film.
  if (meta.caption) {
    if (!ensureCaptionTrack()) return;
    syncSelection();
    buildLayersPanel();
    buildParamPane();
    renderTabs();
    schedulePreview();
  }
  G.damage.kind = kind;
  G.damage.selected = null;
  $('de-dot').style.background = TICK_COLORS[kind] || 'var(--dim)';
  $('de-title').textContent = meta.label;
  $('de-script').classList.toggle('hidden', !meta.caption);
  $('de-styles').classList.toggle('hidden', !meta.caption);
  $('de-reset').textContent = meta.caption ? 'Clear all' : 'Reset kind';
  $('de-reset').title = meta.caption
    ? 'Delete every caption on this track. The style stays as it is.'
    : 'Drop every edit of this kind on this layer';
  $('de-hint').textContent = meta.caption
    ? 'Double-click empty film to add a caption · drag a span to move it · drag its edges to change '
      + 'how long it holds · drag the box on the picture to place it (Alt moves every caption)'
    : 'Drag the film to scrub the preview · double-click empty film to add · drag a span to move it '
      + '· drag its edges to stretch';
  $('damage-editor').classList.remove('hidden');
  $('damage-editor').classList.toggle('cap', !!meta.caption);
  document.body.classList.add('damage-editing');
  document.body.classList.toggle('caption-editing', !!meta.caption);
  if (meta.caption) buildCaptionStyles();
  paintDamageLane();
  refreshCaptionLaunch();
}

function captionEditorOpen() {
  return damageEditorOpen() && G.damage.kind === 'caption';
}

function closeDamageEditor() {
  $('damage-editor').classList.add('hidden');
  document.body.classList.remove('damage-editing');
  document.body.classList.remove('caption-editing');
  $('cap-drag').classList.add('hidden');
  G.damage.kind = null;
  G.damage.selected = null;
  refreshCaptionLaunch();
}

function selectDamage(id, { seek = true } = {}) {
  G.damage.selected = id;
  paintDamageLane();
  const ev = damageEvents().find((e) => e.detail && e.detail.id === id);
  // Seeing it is the point: bring the preview window over if it cannot
  // already see the instance. Jump to it re-seeks on demand from anywhere.
  if (ev && seek) seekToShow(ev.t);
}

function paintDamageLane() {
  if (!damageEditorOpen()) return;
  const lane = $('de-frames');
  const frames = (state.strip && state.strip.frames) || [];
  const fkey = `${state.id}|${frames.length}`;
  if (lane.dataset.key !== fkey) {
    lane.dataset.key = fkey;
    lane.innerHTML = '';
    for (const f of frames) {
      const img = document.createElement('img');
      img.src = fileUrl(f);
      img.draggable = false;
      lane.appendChild(img);
    }
  }
  const total = state.file.duration;
  syncTimelinePlayhead();

  const host = $('de-spans');
  host.innerHTML = '';
  const events = damageEvents();
  const isCap = G.damage.kind === 'caption';
  // Captions are all the user's own words; the seed has no say in them. What
  // does matter is which style is drawing them, so the count says so.
  const cl = isCap && captionLayer();
  $('de-count').textContent = isCap
    ? `${events.length} caption${events.length === 1 ? '' : 's'}`
      + (cl ? ` · ${layerLabel(cl)}` : '')
    : `${events.length} instance${events.length === 1 ? '' : 's'} · seed ${state.seed}`;
  for (const ev of events) {
    const id = ev.detail && ev.detail.id;
    const el = document.createElement('div');
    el.className = 'de-span';
    if (id === G.damage.selected) el.classList.add('sel');
    if (id && String(id).startsWith('edit:')) el.classList.add('added');
    el.style.left = `${(ev.t / total) * 100}%`;
    el.style.width = `${Math.max((ev.dur / total) * 100, 0.4)}%`;
    el.style.background = TICK_COLORS[ev.kind] || 'var(--dim)';
    if (ev.kind === 'caption') {
      el.classList.add('cap');
      const snip = document.createElement('span');
      snip.className = 'de-cap-snip';
      snip.textContent = String(ev.detail.text || '').replace(/\n/g, ' ');
      el.appendChild(snip);
    }
    wireSpan(el, ev, total);
    host.appendChild(el);
  }
  buildDamageForm();
  syncCapDrag();
}

/* Drag body = move; drag an edge = stretch. All of it in clip seconds, all of
   it committed on release as one op. */
function wireSpan(el, ev, total) {
  const meta = DAMAGE_KINDS[ev.kind] || {};
  if (meta.hasDur) {
    for (const side of ['l', 'r']) {
      const grip = document.createElement('div');
      grip.className = `de-grip ${side}`;
      grip.addEventListener('pointerdown', (e) => {
        e.stopPropagation(); e.preventDefault();
        const lane = $('de-lane').getBoundingClientRect();
        const t0 = ev.t, t1 = ev.t + ev.dur;
        const onMove = (m) => {
          const tm = Math.min(Math.max((m.clientX - lane.left) / lane.width, 0), 1) * total;
          let a = side === 'l' ? Math.min(tm, t1 - 0.1) : t0;
          let b = side === 'l' ? t1 : Math.max(tm, t0 + 0.1);
          el.style.left = `${(a / total) * 100}%`;
          el.style.width = `${((b - a) / total) * 100}%`;
          el.dataset.pending = JSON.stringify([a, b]);
        };
        const onUp = () => {
          window.removeEventListener('pointermove', onMove);
          window.removeEventListener('pointerup', onUp);
          const pend = el.dataset.pending && JSON.parse(el.dataset.pending);
          if (!pend) return;
          const [a, b] = pend;
          G.damage.selected = ev.detail.id;
          // Stretching the left edge is a move and a stretch in one gesture.
          if (Math.abs(a - ev.t) > 0.01) moveEvent(ev, Math.round(a * 20) / 20);
          tuneEvent(ev, { dur_s: Math.round((b - a) * 20) / 20 });
        };
        window.addEventListener('pointermove', onMove);
        window.addEventListener('pointerup', onUp);
      });
      el.appendChild(grip);
    }
  }
  el.addEventListener('pointerdown', (e) => {
    if (e.target.classList.contains('de-grip')) return;
    e.stopPropagation(); e.preventDefault();
    const lane = $('de-lane').getBoundingClientRect();
    const grabbed = e.clientX;
    let moved = false;
    const onMove = (m) => {
      if (!moved && Math.abs(m.clientX - grabbed) < 4) return;
      moved = true;
      const frac = Math.min(Math.max((m.clientX - lane.left) / lane.width, 0), 1);
      el.style.left = `${Math.min(frac * 100, 100 - parseFloat(el.style.width))}%`;
    };
    const onUp = (u) => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      if (!moved) { selectDamage(ev.detail.id); return; }
      const frac = Math.min(Math.max((u.clientX - lane.left) / lane.width, 0), 1);
      G.damage.selected = ev.detail.id;
      const t = Math.round(frac * total * 20) / 20;
      moveEvent(ev, t);
      seekToShow(t);   // the point of moving an instance is watching it land
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  });
}

function deRow(labelText, ...controls) {
  const row = document.createElement('div');
  row.className = 'de-row';
  const lab = document.createElement('label');
  lab.textContent = labelText;
  row.appendChild(lab);
  for (const c of controls) row.appendChild(c);
  return row;
}

/* The rows every instance form shares, whatever its kind: where it starts,
   and the way out. One copy, so clamping and seek behavior cannot drift. */
function evStartRow(ev) {
  const tIn = document.createElement('input');
  tIn.type = 'text';
  tIn.value = fmtTimecode(ev.t);
  tIn.onchange = () => {
    const t = parseTimecode(tIn.value);
    if (t == null) return;
    const tc = Math.min(Math.max(t, 0), state.file.duration);
    moveEvent(ev, tc);
    seekToShow(tc);   // typing a far-away time means wanting to see it there
  };
  return deRow('starts at', tIn);
}

function evActionsRow(ev, noun) {
  const actions = document.createElement('div');
  actions.className = 'de-actions';
  const jump = document.createElement('button');
  jump.textContent = 'Jump to it';
  jump.title = 'Move the preview window (the tinted span on the film) to land '
    + `just before this ${noun}`;
  jump.onclick = () => seekPreview(Math.max(ev.t - 0.4, 0));
  const del = document.createElement('button');
  del.id = 'de-del';
  del.textContent = 'Remove';
  del.onclick = () => removeEvent(ev);
  actions.appendChild(jump);
  actions.appendChild(del);
  return actions;
}

function buildDamageForm() {
  const form = $('de-form');
  const empty = $('de-empty');
  const ev = damageEvents().find((e) => e.detail && e.detail.id === G.damage.selected);
  form.classList.toggle('hidden', !ev);
  empty.classList.toggle('hidden', !!ev);
  if (G.damage.kind === 'caption') {
    empty.textContent = 'Select a caption on the timeline, double-click empty film to add one, '
      + 'or use Paste script above.';
  } else {
    empty.textContent = 'Select an instance on the timeline.';
  }
  form.innerHTML = '';
  if (!ev) return;
  if ((DAMAGE_KINDS[ev.kind] || {}).caption) { buildCaptionForm(form, ev); return; }
  const meta = DAMAGE_KINDS[ev.kind] || {};

  form.appendChild(evStartRow(ev));

  if (meta.hasDur) {
    const dIn = document.createElement('input');
    dIn.type = 'number';
    dIn.min = 0.1; dIn.step = 0.05; dIn.value = ev.dur.toFixed(2);
    dIn.onchange = () => {
      const v = parseFloat(dIn.value);
      if (Number.isFinite(v) && v > 0.05) tuneEvent(ev, { dur_s: v });
    };
    form.appendChild(deRow('lasts', dIn));
  }

  if (ev.kind !== 'dropout') {
    const maxI = ev.kind === 'skew_tear' ? 2 : 1;
    form.appendChild(deRow('intensity',
      ...evKnob(ev.detail.intensity ?? 1, { min: 0.05, max: maxI, step: 0.01 },
        (v) => tuneEvent(ev, { intensity: v }))));
  }

  /* Where the burst sits on the picture. Auto is the tape's own habit - the
     rolling band, the near-the-top tear, the whole-frame shred - and a pinned
     value is the instance's alone: 0 hugs the top edge, 1 the bottom. */
  if (meta.band) {
    const pRow = deRow('position', ...evAutoKnob(ev.detail.band_pos,
      { min: 0, max: 1, step: 0.01, auto: meta.band.auto },
      (v) => tuneEvent(ev, { band_pos: v })));
    pRow.title = 'Vertical position: 0 is the top of the frame, 1 the bottom.';
    form.appendChild(pRow);
    const hRow = deRow('height', ...evAutoKnob(ev.detail.band_height,
      { min: meta.band.hMin, max: meta.band.hMax, step: 0.01, auto: meta.band.auto },
      (v) => tuneEvent(ev, { band_height: v })));
    hRow.title = 'Band height as a share of the frame.';
    form.appendChild(hRow);
  }

  if (ev.kind === 'dropout') {
    const mk = (label, key, val, min, max) => {
      const i = document.createElement('input');
      i.type = 'number'; i.min = min; i.max = max; i.step = 1; i.value = val;
      i.onchange = () => {
        const v = parseInt(i.value, 10);
        if (Number.isFinite(v)) tuneEvent(ev, { [key]: v });
      };
      return deRow(label, i);
    };
    form.appendChild(mk('row', 'row', ev.detail.row, 0, 9999));
    form.appendChild(mk('x', 'x', ev.detail.x, 0, 9999));
    form.appendChild(mk('length', 'length_px', ev.detail.length_px, 6, 9999));
    form.appendChild(mk('thickness', 'rows', ev.detail.rows, 1, 2));
    const pol = document.createElement('select');
    for (const c of ['bright', 'dark']) {
      const o = document.createElement('option');
      o.value = c; o.textContent = c;
      if (c === ev.detail.polarity) o.selected = true;
      pol.appendChild(o);
    }
    pol.onchange = () => tuneEvent(ev, { polarity: pol.value });
    form.appendChild(deRow('polarity', pol));
  }

  form.appendChild(evActionsRow(ev, 'instance'));
}

/* ── the caption track ───────────────────────────────────────────────
   Captions come in two halves that used to be welded together, and the weld
   was the problem: the words lived in a layer's event diff, so picking a
   different caption style - which is picking a different preset for that layer
   - threw the whole script away. Nobody could try a look on their own
   subtitles without retyping them.

   So the halves are separate now. A layer's `cues` are the script: what is
   said, when, how long, and any per-cue placement. The layer's *preset* is the
   style: the face, the backing, the motion, the era. One caption track per
   session wears one style at a time, and swapping styles is a repaint, never a
   retype. layerSpec() welds them back together for the engine, which never had
   to learn any of this.

   The engine's plan still reports each cue's on-screen bbox, so the drag
   handle on the picture is exact rather than a guess - but the lane itself is
   drawn from the cues directly, so it is right the instant a style changes
   instead of a render later. */

/* A neutral, legible default for someone who reached for captions rather than
   for a caption aesthetic. Any build missing it falls back to whatever the
   library's first captions preset happens to be. */
const DEFAULT_CAPTION_STYLE = 'sdh-2007';

function captionStyleIds() {
  const ps = (G.schema && G.schema.presets) || {};
  return Object.keys(ps).filter((id) => ps[id].family === 'captions')
    .sort((a, b) => String(ps[a].era).localeCompare(String(ps[b].era)));
}

function isCaptionStyle(pid) {
  const p = pid && G.schema && G.schema.presets && G.schema.presets[pid];
  return !!(p && p.family === 'captions');
}

function isCaptionLayer(l) {
  return !!(l && isCaptionStyle(l.presetId));
}

/* The session's caption track, if it has one. Deliberately the *first* such
   layer: picking a caption style routes here rather than stacking a second
   track, because two caption tracks is almost never what anybody meant. */
function captionLayerIndex(sess = state) {
  return (sess.layers || []).findIndex(isCaptionLayer);
}

function captionLayer(sess = state) {
  const i = captionLayerIndex(sess);
  return i < 0 ? null : sess.layers[i];
}

function captionCues(sess = state) {
  const l = captionLayer(sess);
  return (l && l.cues) || [];
}

function captionCueCount(sess = state) {
  return captionCues(sess).length;
}

let cueSeq = 0;

/* Every optional field is spelled out with an explicit null rather than left
   off: null is how a cue says "the style decides" over the wire, and a missing
   key would read the same but survive a round trip differently. */
const CUE_KEYS = ['text', 'dur_s', 'pos_x', 'pos_y', 'align', 'color', 'size', 'italic'];

function newCue(t, detail = {}) {
  return {
    id: `cue:${Date.now()}:${++cueSeq}`,
    t: Math.max(Number(t) || 0, 0),
    text: '',
    dur_s: 2.5,
    pos_x: null, pos_y: null, align: null, color: null, size: null,
    italic: false,
    ...detail,
  };
}

/* Cues as the engine reads them. Only a layer actually wearing a caption style
   emits any: a script on a layer that has been switched to a tape look is kept,
   but there is nothing there to draw it. */
function cueOps(l) {
  if (!isCaptionLayer(l)) return [];
  return (l.cues || []).map((c) => {
    const detail = {};
    for (const k of CUE_KEYS) detail[k] = c[k] === undefined ? null : c[k];
    return { op: 'add', id: c.id, effect: 'captions', kind: 'caption', t: c.t, detail };
  });
}

/* Older builds saved captions as add/move/tune/remove ops inside `events`, and
   customs and stacks in the wild still carry them. Replaying that little diff
   into the cue list is the honest migration - reading only the adds would
   silently undo every edit that had been made to them. */
function migrateCues(l) {
  const ops = l.events || [];
  if (!ops.some((e) => e && e.kind === 'caption')) return l;
  const cues = [...(l.cues || [])];
  for (const e of ops) {
    if (!e || e.kind !== 'caption') continue;
    if (e.op === 'add') {
      cues.push({ ...newCue(e.t, e.detail || {}), id: e.id || `cue:legacy:${++cueSeq}` });
      continue;
    }
    const at = cues.findIndex((c) => c.id === e.id);
    if (at < 0) continue;
    if (e.op === 'remove') cues.splice(at, 1);
    else if (e.op === 'move') cues[at].t = Math.max(Number(e.t) || 0, 0);
    else if (e.op === 'tune') Object.assign(cues[at], e.detail || {});
  }
  l.cues = cues;
  l.events = ops.filter((e) => !e || e.kind !== 'caption');
  return l;
}

// ── cue edits ────────────────────────────────────────────────────────
function findCue(id) {
  return captionCues().find((c) => c.id === id) || null;
}

function updateCue(id, patch) {
  const c = findCue(id);
  if (!c) return;
  Object.assign(c, patch);
  afterEventEdit();
}

function moveCue(id, t) {
  updateCue(id, { t: Math.max(Number(t) || 0, 0) });
}

function removeCue(id) {
  const l = captionLayer();
  if (!l) return;
  l.cues = (l.cues || []).filter((c) => c.id !== id);
  if (G.damage.selected === id) G.damage.selected = null;
  afterEventEdit();
}

function addCue(t, detail = {}) {
  const l = ensureCaptionTrack();
  if (!l) return null;
  const cue = newCue(t, { text: 'Caption text', ...detail });
  l.cues = l.cues || [];
  l.cues.push(cue);
  G.damage.selected = cue.id;
  G.damage.focusText = true;   // a fresh cue arrives ready to type over
  afterEventEdit();
  return cue.id;
}

/* The session's caption track, made if it is not there yet. A blank layer is
   the obvious home for it; otherwise the track goes on top of the stack, where
   crisp lettering over a treated picture is the common case - dragging it
   under a tape layer to have the tape chew it is one gesture away. */
function ensureCaptionTrack(styleId = null) {
  let i = captionLayerIndex(state);
  if (i < 0) {
    const style = styleId
      || (isCaptionStyle(DEFAULT_CAPTION_STYLE) ? DEFAULT_CAPTION_STYLE : captionStyleIds()[0]);
    if (!style) return null;
    const cur = activeLayer(state);
    if (cur && !cur.presetId) {
      i = state.activeLayer;
    } else {
      state.layers.push(newLayer());
      i = state.layers.length - 1;
    }
    Object.assign(state.layers[i], { presetId: style, customId: null, variant: null, sets: {} });
    state.stackId = null;
  }
  state.activeLayer = i;
  // The pane follows the track, because while you are writing captions the
  // knobs worth having are the caption style's. `capSeen` is set here rather
  // than in the pane: the door it guards is the one being walked through.
  state.layers[i].capSeen = true;
  return state.layers[i];
}

/* Wearing a different style. Everything about the look is replaced - variant
   and tweaks belonged to the old style and would land on parameters the new
   one never set - and the script is left strictly alone. */
function applyCaptionStyle(pid, opts = {}) {
  const l = ensureCaptionTrack(pid);
  if (!l) return;
  if (l.presetId !== pid) {
    Object.assign(l, { presetId: pid, customId: null, variant: null, sets: {} });
    state.stackId = null;
  }
  syncSelection();
  renderTabs();
  buildParamPane();       // which relights the strip's chip and its variants
  buildLayersPanel();
  paintDamageLane();
  schedulePreview(true, opts.previewDelay);
}

/* Step through the caption styles in era order - how you audition a script
   against the whole library without leaving the editor. */
function stepCaptionStyle(delta) {
  const ids = captionStyleIds();
  if (!ids.length) return;
  const l = captionLayer();
  const at = l ? ids.indexOf(l.presetId) : -1;
  const next = at < 0 ? 0 : (at + delta + ids.length) % ids.length;
  applyCaptionStyle(ids[next]);
}

/* One source for the launch card's words, used at build and refresh alike. The
   card doubles as the editor's own switch, so it says which way it points. */
function captionLaunchLabels(n, open = captionEditorOpen()) {
  return {
    info: n ? `${n} caption${n === 1 ? '' : 's'} on this track` : 'No captions written yet',
    button: open ? 'Hide editor' : (n ? 'Edit captions' : 'Add captions'),
  };
}

/* The captions effect's resolved knobs for the caption track: preset chain
   values, variant overrides, then manual sets. The script splitter reads wrap
   width and row count from here so it packs what the style will actually show. */
function captionParams() {
  const out = {};
  const eff = G.schema.effects.captions;
  if (!eff) return out;
  for (const prm of eff.params) out[prm.name] = prm.default;
  const l = captionLayer() || activeLayer(state);
  if (!l) return out;
  const p = G.schema.presets[l.presetId];
  const entry = p && (p.video || []).find(([eid]) => eid === 'captions');
  if (entry) Object.assign(out, entry[1] || {});
  for (const [k, v] of Object.entries({ ...variantOverridesOf(l), ...(l.sets || {}) })) {
    const m = /^captions\.(.+)$/.exec(String(k).replace(/#\d+\./, '.'));
    if (m) out[m[1]] = v;
  }
  return out;
}

function captionLaunchCard() {
  const card = document.createElement('div');
  card.id = 'cap-launch';
  const labels = captionLaunchLabels(captionCueCount());
  const info = document.createElement('div');
  info.className = 'cap-launch-info';
  info.textContent = labels.info;
  const open = document.createElement('button');
  open.className = 'accent';
  open.textContent = labels.button;
  open.onclick = () => {
    if (captionEditorOpen()) closeDamageEditor();
    else openDamageEditor('caption');
  };
  const paste = document.createElement('button');
  paste.textContent = 'Paste script…';
  paste.title = 'Drop in a whole script or .srt text and spread it across the clip';
  paste.onclick = () => { openDamageEditor('caption'); openScriptModal(); };
  card.appendChild(info);
  card.appendChild(open);
  card.appendChild(paste);
  return card;
}

/* ── the style strip ─────────────────────────────────────────────────
   The editor's own aesthetic picker, sitting directly over the words it
   restyles. Every caption style in the library as a chip wearing its own
   thumbnail, the current one lit, its variants underneath. This is the thing
   the old arrangement could not do at all: one click, same script, different
   era, and the preview re-renders around it. */
function buildCaptionStyles() {
  const row = $('de-styles');
  if (!row) return;
  row.innerHTML = '';
  const l = captionLayer();
  const cur = l && l.presetId;
  const strip = document.createElement('div');
  strip.className = 'cs-strip';
  for (const id of captionStyleIds()) {
    const p = G.schema.presets[id];
    const chip = document.createElement('button');
    chip.className = 'cs-chip' + (id === cur ? ' sel' : '');
    chip.title = `${p.name} · ${p.era}\n${p.desc}`;
    const t = G.thumbs && G.thumbs[id];
    if (t && t.poster) {
      const img = document.createElement('img');
      img.src = fileUrl(t.poster);
      img.draggable = false;
      chip.appendChild(img);
    }
    const name = document.createElement('span');
    name.textContent = p.name;
    chip.appendChild(name);
    chip.onclick = () => applyCaptionStyle(id);
    strip.appendChild(chip);
  }
  row.appendChild(strip);
  // The strip is longer than the panel, and the style you are wearing is the
  // one you are navigating from - it has to be on screen without a hunt.
  const lit = strip.querySelector('.cs-chip.sel');
  if (lit) requestAnimationFrame(() => lit.scrollIntoView({ block: 'nearest', inline: 'center' }));

  const sub = document.createElement('div');
  sub.className = 'cs-sub';
  const p = cur && G.schema.presets[cur];
  if (p && p.variants.length) {
    const base = document.createElement('span');
    base.className = 'variant-pill' + (l.variant ? '' : ' sel');
    base.textContent = 'standard';
    base.onclick = () => { l.variant = null; buildParamPane(); buildCaptionStyles(); schedulePreview(true); };
    sub.appendChild(base);
    for (const v of p.variants) {
      const pill = document.createElement('span');
      pill.className = 'variant-pill' + (l.variant === v.id ? ' sel' : '');
      pill.textContent = v.name;
      pill.title = v.desc;
      pill.onclick = () => { l.variant = v.id; buildParamPane(); buildCaptionStyles(); schedulePreview(true); };
      sub.appendChild(pill);
    }
  }
  const n = Object.keys((l && l.sets) || {}).length;
  if (n) {
    const tweaks = document.createElement('button');
    tweaks.className = 'cs-tweaks';
    tweaks.textContent = `${n} tweak${n === 1 ? '' : 's'} · reset`;
    tweaks.title = 'Discard the manual changes made to this style in the parameter pane';
    tweaks.onclick = () => { l.sets = {}; buildParamPane(); buildCaptionStyles(); schedulePreview(true); };
    sub.appendChild(tweaks);
  }
  const hint = document.createElement('span');
  hint.className = 'cs-hint';
  hint.textContent = '[ and ] step styles';
  sub.appendChild(hint);
  row.appendChild(sub);
}

function buildCaptionForm(form, ev) {
  const ta = document.createElement('textarea');
  ta.id = 'de-cap-text';
  ta.rows = 3;
  ta.spellcheck = false;
  ta.placeholder = 'What this caption says…';
  ta.value = ev.detail.text || '';
  ta.onchange = () => { if (ta.value !== (ev.detail.text || '')) tuneEvent(ev, { text: ta.value }); };
  ta.addEventListener('keydown', (e) => {
    // Typing is the whole point: keys stay here. Escape backs out of the edit
    // without tearing the editor down, and Cmd/Ctrl+Enter commits.
    e.stopPropagation();
    if (e.code === 'Escape') { ta.value = ev.detail.text || ''; ta.blur(); }
    if ((e.metaKey || e.ctrlKey) && e.code === 'Enter') ta.blur();
  });
  form.appendChild(ta);
  if (G.damage.focusText) {
    G.damage.focusText = false;
    setTimeout(() => { ta.focus(); ta.select(); }, 0);
  }

  form.appendChild(evStartRow(ev));

  const dIn = document.createElement('input');
  dIn.type = 'number';
  dIn.min = 0.3; dIn.step = 0.1; dIn.value = ev.dur.toFixed(2);
  dIn.onchange = () => {
    const v = parseFloat(dIn.value);
    if (Number.isFinite(v) && v >= 0.3) tuneEvent(ev, { dur_s: v });
  };
  form.appendChild(deRow('holds for', dIn));

  /* Placement: auto means the preset's own spot (the pos knobs in the pane);
     a pinned value belongs to this cue alone. Dragging the box on the picture
     writes the same numbers. */
  const pxRow = deRow('across', ...evAutoKnob(ev.detail.pos_x,
    { min: 0, max: 1, step: 0.01, auto: 'the preset places it' },
    (v) => tuneEvent(ev, { pos_x: v })));
  pxRow.title = 'Horizontal center: 0 is the left edge, 1 the right.';
  form.appendChild(pxRow);
  const pyRow = deRow('down', ...evAutoKnob(ev.detail.pos_y,
    { min: 0, max: 1, step: 0.01, auto: 'the preset places it' },
    (v) => tuneEvent(ev, { pos_y: v })));
  pyRow.title = 'Vertical center: 0 is the top of the frame, 1 the bottom.';
  form.appendChild(pyRow);

  const szRow = deRow('size', ...evAutoKnob(ev.detail.size,
    { min: 0.02, max: 0.13, step: 0.005, auto: 'the preset sizes it' },
    (v) => tuneEvent(ev, { size: v })));
  szRow.title = 'Line height as a share of frame height, for this cue only.';
  form.appendChild(szRow);

  const alignSel = document.createElement('select');
  for (const c of ['preset', 'left', 'center', 'right']) {
    const o = document.createElement('option');
    o.value = c; o.textContent = c;
    if ((ev.detail.align || 'preset') === c) o.selected = true;
    alignSel.appendChild(o);
  }
  alignSel.onchange = () => tuneEvent(ev, { align: alignSel.value === 'preset' ? null : alignSel.value });
  form.appendChild(deRow('align', alignSel));

  const colIn = document.createElement('input');
  colIn.type = 'text';
  colIn.spellcheck = false;
  colIn.placeholder = 'preset';
  colIn.value = ev.detail.color || '';
  colIn.title = 'Hex color for this cue only, like FFD24A. Empty hands it back to the preset.';
  colIn.onchange = () => {
    const v = colIn.value.trim();
    tuneEvent(ev, { color: v === '' ? null : v });
  };
  form.appendChild(deRow('color', colIn));

  const it = document.createElement('input');
  it.type = 'checkbox';
  it.checked = !!ev.detail.italic;
  it.onchange = () => tuneEvent(ev, { italic: it.checked });
  const itRow = deRow('italic', it);
  itRow.title = 'Slant this cue - the classic voice-off-screen convention.';
  form.appendChild(itRow);

  /* Walking the cue list is how you proof a whole script without touching the
     lane: previous, next, each selection seeking the preview to its cue. */
  const nav = document.createElement('div');
  nav.className = 'de-actions';
  const caps = damageEvents();
  const at = caps.findIndex((x) => x.detail && x.detail.id === ev.detail.id);
  const prev = document.createElement('button');
  prev.textContent = '◀ Prev';
  prev.disabled = at <= 0;
  prev.onclick = () => selectDamage(caps[at - 1].detail.id);
  const next = document.createElement('button');
  next.textContent = 'Next ▶';
  next.disabled = at < 0 || at >= caps.length - 1;
  next.onclick = () => selectDamage(caps[at + 1].detail.id);
  nav.appendChild(prev);
  nav.appendChild(next);
  form.appendChild(nav);

  form.appendChild(evActionsRow(ev, 'caption'));
}

/* ── script import ───────────────────────────────────────────────────
   Paste anything: an .srt keeps its own timing, prose splits into cues that
   share the clip in proportion to how much there is to read. Both are plain
   adds, so every cue is editable the moment it lands. */

function parseSrt(text) {
  const t = String(text || '').replace(/\r/g, '');
  if (!/^\s*\d+\s*\n\s*\d{2}:\d{2}:\d{2}[,.]\d{1,3}\s*-->/m.test(t)) return null;
  const cues = [];
  const re = /(\d{2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{1,3})[^\n]*\n([\s\S]*?)(?=\n\s*\n|\n*$)/g;
  let m;
  while ((m = re.exec(t))) {
    const st = Number(m[1]) * 3600 + Number(m[2]) * 60 + Number(m[3]) + Number(m[4].padEnd(3, '0')) / 1000;
    const en = Number(m[5]) * 3600 + Number(m[6]) * 60 + Number(m[7]) + Number(m[8].padEnd(3, '0')) / 1000;
    const body = m[9].split('\n')
      .map((s) => s.replace(/<[^>]+>/g, '').trim())
      .filter((s) => s && !/^\d+$/.test(s))
      .join('\n').trim();
    if (body && en > st) {
      cues.push({ t: Math.round(st * 20) / 20, dur_s: Math.max(Math.round((en - st) * 20) / 20, 0.3), text: body });
    }
  }
  return cues.length ? cues : null;
}

function splitScriptToCues(text, duration, { lineChars = 32, maxLines = 2 } = {}) {
  const clean = String(text || '').replace(/\r/g, '');
  const chunkMax = Math.max(Number(lineChars) * Number(maxLines) || 64, 24);
  const chunks = [];
  for (const para of clean.split(/\n\s*\n+/)) {
    const flat = para.replace(/\s*\n\s*/g, ' ').trim();
    if (!flat) continue;
    const sentences = flat.match(/[^.!?]+[.!?]+["')\]]*\s*|[^.!?]+$/g) || [flat];
    let cur = '';
    for (const s of sentences) {
      const st = s.trim();
      if (!st) continue;
      if (!cur) cur = st;
      else if (cur.length + 1 + st.length <= chunkMax) cur += ' ' + st;
      else { chunks.push(cur); cur = st; }
      while (cur.length > chunkMax) {
        // a sentence longer than a caption breaks on a word, never mid-word
        let cut = cur.lastIndexOf(' ', chunkMax);
        if (cut < chunkMax * 0.4) cut = chunkMax;
        // and never strands a two-word tail as its own caption: retreat the
        // cut until what remains reads as a phrase
        if (cur.length - cut < 12) {
          const back = cur.lastIndexOf(' ', cur.length - 12);
          if (back > chunkMax * 0.4) cut = back;
        }
        chunks.push(cur.slice(0, cut).trim());
        cur = cur.slice(cut).trim();
      }
    }
    if (cur) chunks.push(cur);
  }
  if (!chunks.length) return [];
  const weights = chunks.map((c) => Math.max(c.length, 8));
  const wsum = weights.reduce((a, b) => a + b, 0);
  const usable = Math.max(Number(duration) - 0.2, 1);
  const cues = [];
  let t = 0.1;
  for (let i = 0; i < chunks.length; i++) {
    const slot = usable * (weights[i] / wsum);
    const gap = Math.min(0.35, slot * 0.12);
    const read = Math.max(1.0, chunks[i].length / 14);   // reading pace, about 14 chars a second
    const dur = Math.max(Math.min(slot - gap, read * 1.6), Math.min(0.8, slot * 0.8));
    cues.push({
      t: Math.round(t * 20) / 20,
      dur_s: Math.max(Math.round(dur * 20) / 20, 0.3),
      text: chunks[i],
    });
    t += slot;
  }
  return cues;
}

function openScriptModal() {
  $('script-text').value = '';
  $('script-modal').classList.remove('hidden');
  setTimeout(() => $('script-text').focus(), 0);
}

function closeScriptModal() {
  $('script-modal').classList.add('hidden');
}

async function applyScriptModal() {
  const raw = $('script-text').value;
  closeScriptModal();
  if (!raw.trim() || !state.file || !state.file.duration) return;
  const cp = captionParams();
  let cues = parseSrt(raw);
  const fromSrt = !!cues;
  if (cues) cues = cues.filter((c) => c.t < state.file.duration);
  else {
    cues = splitScriptToCues(raw, state.file.duration, {
      lineChars: Number(cp.line_chars) || 32,
      maxLines: Number(cp.max_lines) || 2,
    });
  }
  if (!cues.length) { flash('Nothing to caption in that text'); return; }
  let mode = 'append';
  if (captionCueCount()) {
    mode = await askChoice({
      title: 'Captions already on this track',
      sub: 'Replace them with the new script, or keep them and add these after?',
      choices: [
        { key: 'replace', label: 'Replace', className: 'accent' },
        { key: 'append', label: 'Keep and add' },
        { key: null, label: 'Cancel' },
      ],
    });
    if (!mode) return;
  }
  const l = ensureCaptionTrack();
  if (!l) return;
  l.cues = mode === 'replace' ? [] : (l.cues || []);
  for (const c of cues) l.cues.push(newCue(c.t, { text: c.text, dur_s: c.dur_s }));
  G.damage.selected = null;
  afterEventEdit();
  flash(`${cues.length} caption${cues.length === 1 ? '' : 's'} ${fromSrt ? 'kept their subtitle timing' : 'spread across the clip'}`);
}

/* ── placing captions on the picture ─────────────────────────────────
   The handle is the engine's own bbox for the selected cue, mapped onto the
   player. Dragging it writes pos_x/pos_y back: onto the cue, or with Alt held,
   onto the preset knobs so the whole track moves together. */

function playerContentRect() {
  const wrap = $('player-wrap').getBoundingClientRect();
  // Whichever surface is actually showing owns the letterbox math: the still
  // frame races the clip and often paints first.
  const still = $('still-frame');
  const stillUp = !still.classList.contains('hidden') && still.naturalWidth;
  const vw = stillUp ? still.naturalWidth : videoA.videoWidth;
  const vh = stillUp ? still.naturalHeight : videoA.videoHeight;
  let content = { left: wrap.left, top: wrap.top, width: wrap.width, height: wrap.height };
  if (vw && vh && wrap.width && wrap.height) {
    const scale = Math.min(wrap.width / vw, wrap.height / vh);
    const w = vw * scale, h = vh * scale;
    content = {
      left: wrap.left + (wrap.width - w) / 2,
      top: wrap.top + (wrap.height - h) / 2,
      width: w, height: h,
    };
  }
  return { wrap, content };
}

function syncCapDrag() {
  const el = $('cap-drag');
  const ev = captionEditorOpen() && G.damage.selected
    ? damageEvents().find((x) => x.detail && x.detail.id === G.damage.selected)
    : null;
  const bbox = ev && ev.detail && ev.detail.bbox;
  if (!bbox) { el.classList.add('hidden'); return; }
  const { wrap, content } = playerContentRect();
  el.style.left = `${content.left - wrap.left + bbox[0] * content.width}px`;
  el.style.top = `${content.top - wrap.top + bbox[1] * content.height}px`;
  el.style.width = `${Math.max((bbox[2] - bbox[0]) * content.width, 24)}px`;
  el.style.height = `${Math.max((bbox[3] - bbox[1]) * content.height, 14)}px`;
  $('cap-drag-label').textContent = String(ev.detail.text || '').replace(/\n/g, ' ');
  el.classList.remove('hidden');
}

function wireCapDrag() {
  const el = $('cap-drag');
  // The handle is placed in pixels against the player, so a resized window
  // has to re-derive it from the bbox - and so does the picture itself
  // arriving, since its aspect decides the letterbox.
  window.addEventListener('resize', syncCapDrag);
  videoA.addEventListener('loadedmetadata', syncCapDrag);
  $('still-frame').addEventListener('load', syncCapDrag);
  // The wrap's own click toggles playback; the handle is not the picture.
  el.addEventListener('click', (e) => e.stopPropagation());
  el.addEventListener('pointerdown', (e) => {
    e.stopPropagation(); e.preventDefault();
    const ev = damageEvents().find((x) => x.detail && x.detail.id === G.damage.selected);
    if (!ev || !ev.detail.bbox) return;
    const moveAll = e.altKey;
    const start = {
      x: e.clientX, y: e.clientY,
      left: parseFloat(el.style.left), top: parseFloat(el.style.top),
    };
    el.classList.add('dragging');
    const onMove = (m) => {
      el.style.left = `${start.left + (m.clientX - start.x)}px`;
      el.style.top = `${start.top + (m.clientY - start.y)}px`;
    };
    const onUp = () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      el.classList.remove('dragging');
      // Rect read at drop, not at grab: a window resized mid-drag would
      // otherwise convert the handle's position through stale geometry.
      const { wrap, content } = playerContentRect();
      const w = parseFloat(el.style.width), h = parseFloat(el.style.height);
      const cx = (parseFloat(el.style.left) + w / 2 - (content.left - wrap.left)) / content.width;
      const cy = (parseFloat(el.style.top) + h / 2 - (content.top - wrap.top)) / content.height;
      const px = Math.round(Math.min(Math.max(cx, 0), 1) * 1000) / 1000;
      const py = Math.round(Math.min(Math.max(cy, 0), 1) * 1000) / 1000;
      if (moveAll) {
        // The whole track moves: these are the style's own knobs, so every cue
        // without its own pin follows. They belong to the caption layer, which
        // is not necessarily the one selected in the pane.
        const cl = captionLayer();
        if (cl) {
          cl.sets = cl.sets || {};
          cl.sets['captions.pos_x'] = px;
          cl.sets['captions.pos_y'] = py;
        }
        buildParamPane();
        buildCaptionStyles();
        schedulePreview();
        refreshTimeline();
      } else {
        tuneEvent(ev, { pos_x: px, pos_y: py });
      }
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  });
}

/* ── full-length preview: seeks without re-renders ───────────────────
   After a window render lands, the whole clip renders quietly in the
   background at preview quality. Once it exists for the current spec, a seek
   is a currentTime jump inside that file instead of a fresh render. Guarded on
   the IPC existing, so the renderer works with or without the pipeline. */
function fullSpecKey(sess = state) {
  return JSON.stringify({ spec: layerSpec(sess), scale: G.scale });
}

async function maybeKickFullPreview() {
  if (!window.aesth.previewFull || !state.file || state.audioSource) return;
  const sess = state;
  const key = fullSpecKey(sess);
  if (sess.fullKey === key || sess.fullJob === key) return;
  sess.fullJob = key;
  try {
    const [treated, original] = await Promise.all([
      window.aesth.previewFull({
        input: sess.file.path, layers: layerSpec(sess),
        presetId: sess.presetId, variant: sess.variant, sets: sess.sets,
        seed: sess.seed, intensity: sess.intensity, texture: sess.texture,
        scale: G.scale, audioSource: sess.audioSource,
      }),
      window.aesth.snippet({ input: sess.file.path, start: 0,
        duration: sess.file.duration, scale: G.scale, audioSource: sess.audioSource }),
    ]);
    if (treated && treated.output && fullSpecKey(sess) === key) {
      sess.fullKey = key;
      sess.fullSrc = treated.output;
      sess.fullOrig = original && original.output;
    }
  } catch (_) {
    // The window pipeline still works; the background render is a luxury.
  } finally {
    if (sess.fullJob === key) sess.fullJob = null;
  }
}

function useFullPreviewSeek() {
  const sess = state;
  if (!sess.fullSrc || sess.fullKey !== fullSpecKey(sess)) return false;
  $('player-empty').classList.add('hidden');
  hideStill();
  const want = `full:${sess.fullSrc}`;
  if (videoA.dataset.src !== want) {
    videoA.dataset.src = want;
    setVideo(videoA, sess.fullSrc);
    if (sess.fullOrig) setVideo(videoB, sess.fullOrig);
  }
  const jump = () => {
    try {
      videoA.currentTime = sess.previewT;
      videoB.currentTime = sess.previewT;
    } catch (_) { /* not seekable yet; the loadeddata hook lands it */ }
  };
  if (videoA.readyState >= 1) jump();
  else videoA.addEventListener('loadedmetadata', jump, { once: true });
  return true;
}

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
    /* The paste-script sheet: Escape puts it away, typing belongs to it. */
    if (!$('script-modal').classList.contains('hidden')) {
      if (e.code === 'Escape') { e.preventDefault(); closeScriptModal(); }
      return;
    }
    /* The damage editor is typing-heavy; the keyboard is its own until Escape.
       The one exception is auditioning caption styles, which is the whole
       reason to be in there with a script already written - and [ and ] are
       not characters anybody is trying to put into a subtitle mid-word. */
    if (damageEditorOpen()) {
      if (e.code === 'Escape') { e.preventDefault(); closeDamageEditor(); }
      else if (captionEditorOpen() && !typingTarget(e) && !meta
               && (e.key === '[' || e.key === ']')) {
        e.preventDefault();
        stepCaptionStyle(e.key === ']' ? 1 : -1);
      }
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
    if (e.code === 'Escape' && !$('history-panel').classList.contains('hidden')) {
      e.preventDefault();
      toggleHistoryPanel(false);
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
  $('preset-search').addEventListener('input', () => { buildFacetRow(); buildPresetList(); });
  $('era-filter').addEventListener('change', (e) => {
    G.filterEra = e.target.value;
    e.target.classList.toggle('active', !!G.filterEra);
    buildPresetList();
  });

  /* Type a time, land on it: seconds or minutes:seconds, Enter commits. The
     strip is the pointer's timeline; this is the keyboard's. */
  $('timecode').addEventListener('keydown', (e) => {
    e.stopPropagation();
    if (e.code !== 'Enter') return;
    const t = parseTimecode($('timecode').value);
    if (t != null) seekPreview(t);
    else $('timecode').value = fmtTimecode(state.previewT);
    syncTimelinePlayhead();
  });
  /* The strip and the editor lane are the same seek surface, just map-shaped:
     x is time across the whole clip. Both borrow the slider's own max and
     0.1 s grid, so no two controls can ever disagree about where the preview
     window is allowed to sit. */
  const stripSeekAt = (el, clientX, commit) => {
    if (!state.file || !state.file.duration) return;
    const r = el.getBoundingClientRect();
    if (!r.width) return;
    const frac = Math.min(Math.max((clientX - r.left) / r.width, 0), 1);
    const max = Math.max(state.file.duration - G.duration, 0);
    const t = Math.min(frac * state.file.duration, max);
    state.previewT = parseFloat(t.toFixed(1));
    $('timecode').value = fmtTimecode(state.previewT);
    syncTimelinePlayhead();
    if (commit) {
      if (!useFullPreviewSeek()) schedulePreview();
    }
  };
  const stripSeek = (clientX, commit) => stripSeekAt($('timeline'), clientX, commit);
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
      const maxT = Math.max(state.file.duration - G.duration, 0);
      if (state.previewT > maxT) {
        state.previewT = maxT;
        $('timecode').value = fmtTimecode(state.previewT);
      }
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

  $('de-close').addEventListener('click', closeDamageEditor);
  $('de-add').addEventListener('click', () => {
    if (!G.damage.kind) return;
    const meta = DAMAGE_KINDS[G.damage.kind];
    addEventAt(meta.effect, G.damage.kind, Math.round(state.previewT * 20) / 20, {});
  });
  $('de-reset').addEventListener('click', async () => {
    const kind = G.damage.kind;
    if (!kind) return;
    if (kind === 'caption') {
      // Words are typed, not generated: throwing away a script is worth a
      // question in a way that dropping a seed's dropouts never was.
      const n = captionCueCount();
      if (!n) return;
      const go = await askChoice({
        title: `Delete ${n} caption${n === 1 ? '' : 's'}?`,
        sub: 'The whole script goes. The style stays exactly as it is.',
        choices: [
          { key: 'go', label: 'Delete them', className: 'accent' },
          { key: null, label: 'Cancel' },
        ],
      });
      if (!go) return;
      const cl = captionLayer();
      if (cl) cl.cues = [];
      G.damage.selected = null;
      afterEventEdit();
      return;
    }
    let touched = false;
    for (const l of state.layers || []) {
      const kept = (l.events || []).filter((e) => (e.kind || 'dropout') !== kind);
      if (kept.length !== (l.events || []).length) { l.events = kept; touched = true; }
    }
    G.damage.selected = null;
    if (touched) afterEventEdit();
  });
  /* The lane is a timeline before it is a canvas: press or drag on empty film
     scrubs the playhead, live, and the preview follows once on release - the
     same contract as the strip under the player. Placing an instance is the
     deliberate gesture, a double-click, so exploring the tape never leaves a
     storm behind as a souvenir. */
  $('de-lane').addEventListener('pointerdown', (e) => {
    if (e.target.closest('.de-span')) return;
    stripSeekAt($('de-lane'), e.clientX, false);
    const onMove = (m) => stripSeekAt($('de-lane'), m.clientX, false);
    const onUp = (u) => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      stripSeekAt($('de-lane'), u.clientX, true);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  });
  $('de-lane').addEventListener('dblclick', (e) => {
    if (e.target.closest('.de-span')) return;
    if (!G.damage.kind || !state.file) return;
    const r = $('de-lane').getBoundingClientRect();
    const t = Math.min(Math.max((e.clientX - r.left) / r.width, 0), 1) * state.file.duration;
    const meta = DAMAGE_KINDS[G.damage.kind];
    addEventAt(meta.effect, G.damage.kind, Math.round(t * 20) / 20, {});
  });

  /* Captions are reachable from the controls under the player, not only by
     picking one of the caption aesthetics off the list. Writing the words is
     its own job, and it now comes before choosing what they look like. */
  $('btn-captions').addEventListener('click', () => {
    if (!state.file || state.audioSource) return;
    if (captionEditorOpen()) closeDamageEditor();
    else openDamageEditor('caption');
  });

  $('de-script').addEventListener('click', openScriptModal);
  $('script-cancel').addEventListener('click', closeScriptModal);
  $('script-apply').addEventListener('click', applyScriptModal);
  $('script-modal').addEventListener('mousedown', (e) => {
    if (e.target === $('script-modal')) closeScriptModal();
  });
  wireCapDrag();

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

  $('btn-history').addEventListener('click', () => toggleHistoryPanel());
  $('btn-history-clear').addEventListener('click', clearAllHistory);
  $('btn-history-oldest').addEventListener('click', clearOldestHistory);
  document.addEventListener('mousedown', (e) => {
    if ($('history-panel').classList.contains('hidden')) return;
    // The "clear oldest…" prompt floats over the whole window; typing into it
    // must not count as clicking away from the panel underneath.
    if (!$('modal').classList.contains('hidden')) return;
    if ($('history-panel').contains(e.target) || $('btn-history').contains(e.target)) return;
    toggleHistoryPanel(false);
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
    recordHistory(job);
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
  if (open) { toggleHistoryPanel(false); renderExports(); }
}

/* ── export history panel ────────────────────────────────────────────
   The queue answers "what is rendering right now"; this answers "what have I
   ever made, and with which knobs". One entry per finished export, persisted
   across restarts, each one naming the source clip, where it lived, where the
   file went, and every layer with its settings. */
function recordHistory(job) {
  G.history.push({
    id: `h${++G.historySeq}`,
    ts: Date.now(),
    input: job.req.input,
    output: job.req.output,
    label: job.label,
    videoOnly: Boolean(job.req.videoOnly),
    audioOnly: Boolean(job.req.audioOnly),
    // A deep copy: the session keeps mutating the objects this spec points at.
    layers: JSON.parse(JSON.stringify(job.req.layers || [])),
  });
  if (G.history.length > HISTORY_MAX) G.history.splice(0, G.history.length - HISTORY_MAX);
  saveHistory();
  syncHistoryChip();
  if (!$('history-panel').classList.contains('hidden')) renderHistory();
}

function syncHistoryChip() {
  const n = G.history.length;
  const badge = $('history-count');
  badge.classList.toggle('hidden', !n);
  badge.textContent = n ? String(n) : '';
}

function fmtHistoryTime(ts) {
  const d = new Date(ts);
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

function dirnameOf(p) {
  const dir = (p || '').replace(/[\\/][^\\/]*$/, '');
  return dir || p || '';
}

/* One line per layer, in plain words rather than the raw spec. */
function describeHistoryLayer(l, i, total) {
  const bits = [presetName(l.preset)];
  if (l.variant) bits.push(l.variant);
  bits.push(`seed ${l.seed}`);
  if (typeof l.intensity === 'number' && l.intensity !== 1) bits.push(`intensity ${l.intensity.toFixed(2)}`);
  if (typeof l.texture === 'number') bits.push(`texture ${l.texture.toFixed(2)}`);
  if (l.picture === false) bits.push('picture off');
  if (l.sound === false) bits.push('sound off');
  const ne = (l.events || []).length;
  if (ne) bits.push(`${ne} timeline edit${ne === 1 ? '' : 's'}`);
  return (total > 1 ? `${i + 1}. ` : '') + bits.join(' · ');
}

function fmtSetValue(v) {
  if (typeof v === 'number') return String(Math.round(v * 1000) / 1000);
  return String(v);
}

function renderHistory() {
  syncHistoryChip();
  $('btn-history-clear').disabled = !G.history.length;
  $('btn-history-oldest').disabled = G.history.length < 2;
  const list = $('history-list');
  list.innerHTML = '';
  if (!G.history.length) {
    const empty = document.createElement('div');
    empty.className = 'ep-empty';
    empty.textContent = 'Nothing exported yet. Every export you run is remembered here.';
    list.appendChild(empty);
    return;
  }

  // Newest first: the run you just finished is the one you came looking for.
  for (const run of [...G.history].reverse()) {
    const row = document.createElement('div');
    row.className = 'hp-row';

    const head = document.createElement('div');
    head.className = 'hp-head';
    const name = document.createElement('a');
    name.className = 'hp-name';
    name.textContent = basename(run.input);
    name.title = `${run.input}\nClick to show the source clip in the Finder`;
    name.onclick = () => revealFile(run.input);
    head.appendChild(name);
    const when = document.createElement('span');
    when.className = 'hp-when';
    when.textContent = fmtHistoryTime(run.ts);
    head.appendChild(when);
    const del = document.createElement('button');
    del.className = 'ex-stop';
    del.textContent = '×';
    del.title = 'Forget this run';
    del.onclick = () => deleteHistoryRun(run.id);
    head.appendChild(del);
    row.appendChild(head);

    const from = document.createElement('div');
    from.className = 'hp-path';
    from.append('from ');
    const dirA = document.createElement('a');
    dirA.textContent = dirnameOf(run.input);
    dirA.title = 'Show the source clip in the Finder';
    dirA.onclick = () => revealFile(run.input);
    from.appendChild(dirA);
    row.appendChild(from);

    const to = document.createElement('div');
    to.className = 'hp-path';
    to.append('→ ');
    const outA = document.createElement('a');
    outA.textContent = basename(run.output);
    outA.title = `${run.output}\nShow the exported file in the Finder`;
    outA.onclick = () => revealFile(run.output);
    to.appendChild(outA);
    if (run.videoOnly) to.append(' · video only');
    else if (run.audioOnly) to.append(' · audio only');
    row.appendChild(to);

    if (run.label) {
      const sub = document.createElement('div');
      sub.className = 'hp-sub';
      sub.textContent = run.label;
      sub.title = run.label;
      row.appendChild(sub);
    }

    const lys = document.createElement('div');
    lys.className = 'hp-layers';
    (run.layers || []).forEach((l, i) => {
      const li = document.createElement('div');
      li.className = 'hp-layer';
      li.textContent = describeHistoryLayer(l, i, run.layers.length);
      lys.appendChild(li);
      const setKeys = Object.keys(l.sets || {});
      if (setKeys.length) {
        const tw = document.createElement('div');
        tw.className = 'hp-sets';
        tw.textContent = setKeys.map((k) => `${k} = ${fmtSetValue(l.sets[k])}`).join('   ');
        lys.appendChild(tw);
      }
    });
    row.appendChild(lys);

    list.appendChild(row);
  }
}

function toggleHistoryPanel(show) {
  const panel = $('history-panel');
  const open = show === undefined ? panel.classList.contains('hidden') : show;
  panel.classList.toggle('hidden', !open);
  $('btn-history').classList.toggle('open', open);
  if (open) { toggleExportsPanel(false); renderHistory(); }
}

function deleteHistoryRun(id) {
  G.history = G.history.filter((r) => r.id !== id);
  saveHistory();
  renderHistory();
}

function clearAllHistory() {
  if (!G.history.length) return;
  const n = G.history.length;
  if (!confirm(`Forget all ${n} previous export${n === 1 ? '' : 's'}?\n\nThe exported files themselves are untouched.`)) return;
  G.history = [];
  saveHistory();
  renderHistory();
}

async function clearOldestHistory() {
  const n = G.history.length;
  if (n < 2) return;
  const ans = await askName({
    title: 'Clear the oldest history',
    sub: `${n} entries right now. How many of the oldest should go? The exported files themselves are untouched.`,
    value: String(Math.min(10, n - 1)),
    okLabel: 'Remove',
  });
  if (!ans) return;
  const k = Math.min(n, Math.max(0, parseInt(ans, 10) || 0));
  if (!k) return;
  G.history.splice(0, k);   // the list is oldest-first
  saveHistory();
  renderHistory();
  setExportStatus(`Removed the ${k === 1 ? 'oldest history entry' : `${k} oldest history entries`}.`);
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
