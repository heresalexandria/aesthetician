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
  filterFamilies: new Set(),  // family chips currently selected (empty = all)
  filterEra: '',       // decade string like "1980s" (empty = any)
  favOnly: false,      // the ★ chip: show favorites only
  customOnly: false,   // the ✎ chip: show saved customs only
};

/* Update state. Declared up here with G rather than beside the update code:
   boot() runs while the script is still being parsed, and it paints the version
   chip first, so a `const` further down the file is still in its dead zone. */
const U = {
  info: null,        // { version, packaged, platform, arch, ... }
  latest: null,      // the last check result
  busy: '',          // '', 'checking', 'downloading', 'installing'
  staged: false,     // a verified download is sitting on disk
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
    }));
  } catch (_) { /* storage full or unavailable: cosmetic only */ }
}

function newSession(info) {
  return {
    id: `s${++G.seq}`,
    file: info,
    audioSource: info.has_video === false,  // a WAV/MP3/stem: no picture to treat
    presetId: null,
    customId: null,      // set when the pick came from a saved custom aesthetic
    variant: null,
    sets: {},
    seed: 1 + Math.floor(Math.random() * 99999),
    intensity: 1.0,
    texture: 1.0,
    previewT: Math.max((info.duration - G.duration) / 2, 0),
    treatedSrc: null,
    originalSrc: null,
    originalT: null,
  };
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
  if (sess.presetId) buildParamPane();
  else {
    $('preset-title').textContent = '-';
    $('preset-sub').textContent = '';
    $('btn-fav').classList.add('hidden');
    $('override-row').classList.add('hidden');
    $('variant-row').innerHTML = '';
    $('param-list').innerHTML = '<div class="hint">Pick an aesthetic on the left.</div>';
  }

  // Restore this tab's already-rendered preview if it has one; the files live in
  // the preview cache, so switching back is instant and costs no re-render.
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
    const wearing = sess.customId ? customName(sess.customId) : (sess.presetId ? presetName(sess.presetId) : null);
    tab.title = `${sess.file.path}\n${wearing || 'no aesthetic yet'}`;

    const name = document.createElement('span');
    name.className = 't-name';
    name.textContent = (sess.audioSource ? '♪ ' : '') + basename(sess.file.path);
    tab.appendChild(name);

    if (wearing) {
      const badge = document.createElement('span');
      badge.className = 't-preset' + (sess.customId ? ' custom' : '');
      badge.textContent = (sess.customId ? '✎ ' : '') + wearing;
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

function showTipAt(anchor, { title, desc, facts = [], path = '' }) {
  const el = tipNode();
  el.innerHTML = '';
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
  if (NOISE_HINT.has(path.split('.').pop()) ) facts.push('follows Texture');
  return { title: prm.label, desc: prm.desc || '', facts, path };
}

/* Params the master Texture dial scales (mirrors engine/texture.py). Used only
   to annotate tooltips. */
const NOISE_HINT = new Set(['amount', 'luma_noise', 'chroma_noise', 'fm_sparkle',
  'azimuth_error', 'phase_noise', 'snow', 'impulse_noise', 'noise_floor',
  'retrace_lines', 'moire_cam', 'agc_gain_noise', 'density', 'toner', 'grain_ink',
  'intermittent', 'mottle']);

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

/* What the list highlights and ↑/↓ walk: a custom masquerades as a preset id. */
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
  renderTabs();
  setExportStatus(`Saved “${name}”.`);
}

function applyCustom(cid, opts = {}) {
  const c = customById(cid);
  if (!c || !G.schema.presets[c.base]) return;
  state.presetId = c.base;
  state.customId = c.id;
  state.variant = c.variant || null;
  state.sets = { ...(c.sets || {}) };
  state.intensity = typeof c.intensity === 'number' ? c.intensity : 1;
  state.texture = typeof c.texture === 'number' ? c.texture : 1;
  if (typeof c.seed === 'number') state.seed = c.seed;
  syncMasterDials();
  syncSelection();
  renderTabs();
  buildParamPane();
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
    || JSON.stringify(c.sets || {}) !== JSON.stringify(state.sets);
}

/* Names go into filenames, so keep them to something a filesystem enjoys. */
function slugify(s) {
  return (s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60)
    || 'custom';
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
  const show = Boolean(U.latest && U.latest.available);
  btn.classList.toggle('hidden', !show);
  btn.classList.remove('blocked');
  if (!show) return;
  btn.textContent = U.staged ? 'Install update' : 'Update available';
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

/* One dialog covers up to date, out of date, downloaded, and every way those
   can fail, so the button label and the status line are derived rather than
   set at each call site. */
function paintAbout() {
  const notes = $('about-notes');
  const action = $('about-action');
  const r = U.latest;

  notes.classList.add('hidden');
  action.disabled = false;
  action.textContent = 'Check for updates';

  if (U.busy === 'checking') { setAboutStatus('Checking for updates…', 'busy'); action.disabled = true; return; }
  if (U.busy === 'downloading') { action.textContent = 'Cancel'; return; }
  if (U.busy === 'installing') { setAboutStatus('Installing…', 'busy'); action.disabled = true; return; }

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

  if (r.notes) {
    // Release notes come off the network. Text only, never markup.
    notes.textContent = r.notes;
    notes.classList.remove('hidden');
  }
  if (!r.installable) {
    setAboutStatus(`Version ${r.latest} is available. ${r.note}`, 'warn');
    action.textContent = 'View releases';
    return;
  }
  if (U.staged) {
    setAboutStatus(`Version ${r.latest} is downloaded and ready to install. `
      + 'Aesthetician will restart.', 'ok');
    action.textContent = 'Install and restart';
    return;
  }
  const size = r.asset && r.asset.size ? ` (${formatBytes(r.asset.size)})` : '';
  setAboutStatus(`Version ${r.latest} is available - you have ${r.current}.`);
  action.textContent = `Download${size}`;
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
  U.staged = false;
  syncUpdateButton();
  paintAbout();
}

async function downloadUpdate() {
  U.busy = 'downloading';
  $('about-bar').classList.remove('hidden');
  $('about-bar-fill').style.width = '0%';
  paintAbout();
  try {
    await window.aesth.updateDownload();
    U.staged = true;
    U.busy = '';
    $('about-bar').classList.add('hidden');
  } catch (err) {
    U.busy = '';
    U.staged = false;
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
    window.aesth.openExternal((U.latest && U.latest.htmlUrl)
      || (U.info && U.info.releasesUrl)
      || 'https://github.com/heresalexandria/aesthetician/releases');
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
      if (G.customOnly) G.favOnly = false;
      buildFilterBar(); buildPresetList();
    };
    chips.appendChild(cc);
  }
  const all = document.createElement('span');
  all.className = 'chip' + (G.filterFamilies.size || G.favOnly || G.customOnly ? '' : ' sel');
  all.textContent = 'All';
  all.onclick = () => {
    G.filterFamilies.clear();
    G.favOnly = false;
    G.customOnly = false;
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
  return G.favOnly || G.customOnly || G.filterFamilies.size > 0 || !!G.filterEra || !!$('preset-search').value;
}

function clearFilters() {
  G.favOnly = false;
  G.customOnly = false;
  G.filterFamilies.clear();
  G.filterEra = '';
  $('preset-search').value = '';
  buildFilterBar();
  buildPresetList();
}

// ── preset list ─────────────────────────────────────────────────────
const BLANK_PX = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';

/* Families lead with the looks people reach for most; audio-only sits last
   because those rows leave the picture untouched (their thumbnails are all the
   same untreated frame, so alphabetical order opened the app on 29 of them). */
const FAMILY_ORDER = ['vhs', 'film', 'broadcast', 'cartoon', 'digital', 'world',
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

  const t = G.thumbs[p.id];
  if (t && t.anim && !isAudioOnly(p)) armHoverAnim(card, holder, t.anim);
  card.onclick = () => selectPreset(p.id);
  return card;
}

/* A saved custom borrows its base preset's thumbnail - it is the same chain
   underneath - and wears a badge so it never reads as a stock aesthetic. */
function customCard(c) {
  const base = G.schema.presets[c.base];
  const card = document.createElement('div');
  card.className = 'preset-card custom' + (c.id === selectionId() ? ' sel' : '');
  card.dataset.pid = c.id;
  card.title = `Custom aesthetic based on ${base.name}`;

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

  card.onclick = () => applyCustom(c.id);
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

  /* Saved customs sit above everything: they are the things this user made. */
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
  let shown = favRows.length + customRows.length;
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

function selectPreset(pid, opts = {}) {
  state.presetId = pid;
  state.customId = null;   // picking a stock preset leaves any custom behind
  state.variant = null;
  state.sets = {};
  syncSelection();       // the rows themselves have not changed, only which one is lit
  renderTabs();          // the tab shows which aesthetic the clip is wearing
  buildParamPane();
  schedulePreview(true, opts.previewDelay);
}

/* One entry point for both kinds of row, so ↑/↓ does not care which it lands on. */
function selectById(id, opts = {}) {
  if (isCustomId(id)) applyCustom(id, opts);
  else selectPreset(id, opts);
}

/* Moving the highlight is a class flip, not a rebuild of 192 rows - which is
   what makes holding ↓ feel like scrubbing rather than stuttering. A favorited
   preset owns two rows and both light up. */
function syncSelection() {
  const id = selectionId();
  for (const card of $('preset-list').querySelectorAll('.preset-card')) {
    card.classList.toggle('sel', card.dataset.pid === id);
  }
}

/* ↑/↓ step through the visible list. Hold the key and the whole list runs past
   the player; the preview is debounced by this much, so only the row you
   actually settle on is rendered. */
const NAV_PREVIEW_MS = 260;

function navPreset(delta) {
  const order = G.navOrder;
  if (!order.length) return;
  const at = order.indexOf(selectionId());
  // Nothing picked yet (or the current pick is filtered out of view): enter the
  // list from whichever end the key points at.
  const next = at < 0
    ? (delta > 0 ? 0 : order.length - 1)
    : Math.max(0, Math.min(order.length - 1, at + delta));
  if (order[next] === selectionId()) return;   // already against the end
  selectById(order[next], { previewDelay: NAV_PREVIEW_MS });
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

function buildParamPane() {
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

  const commit = (val) => {
    if (val === baseVal || String(val) === String(baseVal)) delete state.sets[path];
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
    slider.step = prm.kind === 'int' ? 1 : (prm.step || (prm.hi - prm.lo) / 200);
    slider.value = curVal;
    paintRange(slider);
    const val = document.createElement('span');
    val.className = 'pval';
    val.textContent = fmtVal(curVal, prm);
    slider.oninput = () => { val.textContent = fmtVal(parseFloat(slider.value), prm); paintRange(slider); };
    slider.onchange = () => commit(prm.kind === 'int' ? parseInt(slider.value, 10) : parseFloat(slider.value));
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

function fmtVal(v, prm) {
  if (typeof v !== 'number') return String(v);
  const s = prm.kind === 'int' ? String(v) : (Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(2));
  return prm.unit ? `${s}${prm.unit === '°' ? '' : ' '}${prm.unit}` : s;
}

// ── preview rendering ───────────────────────────────────────────────
let previewTimer = null;
/* `immediate` means "render even with auto off" - a deliberate pick, not a knob
   twiddle. `delayMs` overrides the wait: keyboard navigation passes a longer one
   so running down the list does not start a render per row. */
function schedulePreview(immediate = false, delayMs = null) {
  if (!state.file || !state.presetId) return;
  if (!G.autoPreview && !immediate) return;
  clearTimeout(previewTimer);
  previewTimer = setTimeout(runPreview, delayMs != null ? delayMs : (immediate ? 40 : 550));
}

async function runPreview() {
  if (!state.file || !state.presetId) return;
  const sess = state;                    // this render belongs to THIS tab
  const jobId = `job${++G.jobCounter}`;
  G.activeJob = jobId;
  showRenderOverlay(true, 'rendering preview…', 0);
  const req = {
    jobId,
    input: state.file.path,
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
  try {
    const [treated, original] = await Promise.all([
      window.aesth.preview(req),
      state.originalSrc && state.originalT === state.previewT
        ? Promise.resolve({ output: state.originalSrc })
        : window.aesth.snippet({ input: state.file.path, start: state.previewT, duration: G.duration, scale: G.scale, audioSource: state.audioSource }),
    ]);
    // Record the result on its own session even if the user has moved on, so
    // coming back to that tab costs nothing.
    sess.treatedSrc = treated.output;
    sess.originalSrc = original.output;
    sess.originalT = req.start;
    if (sess.id !== G.activeId) return;  // a different tab is on screen now
    if (G.activeJob !== jobId) return;   // superseded by a newer render
    $('player-empty').classList.add('hidden');
    setVideo(videoA, treated.output);
    setVideo(videoB, original.output);
  } catch (err) {
    if (String(err.message || '').includes('superseded')) return;
    setExportStatus(`Preview failed: ${err.message.slice(0, 300)}`, true);
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
    try { el.currentTime = Math.min(t, el.duration - 0.05) || 0; } catch (_) {}
    el.muted = el === videoB ? true : G.muted;
    // A held pause survives re-renders: the new take arrives on a still frame
    // rather than restarting the loop under the user.
    if (!G.paused) el.play().catch(() => {});
  };
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
  if (!videoA.getAttribute('src')) return;
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
    if (meta && e.code === 'KeyO') { e.preventDefault(); browseForFile(); return; }
    // The about dialog owns the keyboard while it is up, the same way the name
    // prompt does - Cmd+O behind a modal is nobody's intent.
    if (!$('about-modal').classList.contains('hidden')) {
      if (e.code === 'Escape' && !U.busy) closeAbout();
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
  });
  scrub.addEventListener('change', () => schedulePreview());

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
    ab.classList.toggle('held', on);
    $('ab-badge').classList.toggle('hidden', !on);
    if (on) { videoB.currentTime = videoA.currentTime; videoB.muted = G.muted; videoA.muted = true; }
    else { videoA.muted = G.muted; videoB.muted = true; }
  };
  ab.addEventListener('mousedown', () => showOriginal(true));
  ab.addEventListener('mouseup', () => showOriginal(false));
  ab.addEventListener('mouseleave', () => showOriginal(false));
  G.showOriginal = showOriginal;   // the B-key shortcut shares this

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

  $('modal-cancel').addEventListener('click', () => closeModal(null));
  $('modal-ok').addEventListener('click', () => closeModal($('modal-input').value.trim() || null));
  $('modal-input').addEventListener('keydown', (e) => {
    if (e.code === 'Enter') { e.preventDefault(); closeModal($('modal-input').value.trim() || null); }
    if (e.code === 'Escape') { e.preventDefault(); closeModal(null); }
    e.stopPropagation();   // the modal owns the keyboard while it is up
  });
  $('modal').addEventListener('mousedown', (e) => { if (e.target === $('modal')) closeModal(null); });
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
  if (!sess || !sess.file || !sess.presetId) return;

  // Freeze everything now: the save dialog is modal, but the export outlives it.
  const req = {
    input: sess.file.path,
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
  // A custom names the file after itself; the base preset id is still what the
  // engine renders, but "my-look" beats "vhs-1985-sp" on disk.
  const tag = sess.customId
    ? slugify(customName(sess.customId))
    : sess.presetId.replace('/', '-') + variantTag;
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
    label: (sess.customId ? customName(sess.customId) : presetName(sess.presetId))
      + (sess.variant ? ` · ${sess.variant}` : ''),
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
      job.error = msg.slice(0, 300);
      setExportStatus(`Export failed: ${job.error}`, true);
      flash('Export failed', { sub: basename(job.req.output), kind: 'error', ms: 8000 });
    }
  } finally {
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
