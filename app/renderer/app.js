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
  exportJob: null,
  duration: 3.0,       // preview length
  scale: 0.5,          // preview scale
  autoPreview: true,
  muted: true,
  favs: new Set(),     // favorited preset ids (persisted)
  filterFamilies: new Set(),  // family chips currently selected (empty = all)
  filterEra: '',       // decade string like "1980s" (empty = any)
  favOnly: false,      // the ★ chip: show favorites only
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
    }));
  } catch (_) { /* storage full or unavailable: cosmetic only */ }
}

function newSession(info) {
  return {
    id: `s${++G.seq}`,
    file: info,
    audioSource: info.has_video === false,  // a WAV/MP3/stem: no picture to treat
    presetId: null,
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
  renderTabs();
  refreshCacheInfo();
  if (G.schema) console.log('aesth:renderer-ready');
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
  $('file-chip').textContent = sess.audioSource
    ? `${basename(sess.file.path)} · audio · ${(sess.file.sr / 1000).toFixed(1)} kHz ${sess.file.channels === 1 ? 'mono' : 'stereo'} · ${sess.file.duration.toFixed(1)}s`
    : `${basename(sess.file.path)} · ${sess.file.width}×${sess.file.height} · ${sess.file.duration.toFixed(1)}s`;
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
      ? 'Press Preview to render this clip'
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

function basename(p) {
  return (p || '').split('/').pop();
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
    tab.title = `${sess.file.path}\n${sess.presetId ? presetName(sess.presetId) : 'no aesthetic yet'}`;

    const name = document.createElement('span');
    name.className = 't-name';
    name.textContent = (sess.audioSource ? '♪ ' : '') + basename(sess.file.path);
    tab.appendChild(name);

    if (sess.presetId) {
      const badge = document.createElement('span');
      badge.className = 't-preset';
      badge.textContent = presetName(sess.presetId);
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
    star.onclick = () => { G.favOnly = !G.favOnly; buildFilterBar(); buildPresetList(); };
    chips.appendChild(star);
  }
  const all = document.createElement('span');
  all.className = 'chip' + (G.filterFamilies.size || G.favOnly ? '' : ' sel');
  all.textContent = 'All';
  all.onclick = () => { G.filterFamilies.clear(); G.favOnly = false; buildFilterBar(); buildPresetList(); };
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
  return G.favOnly || G.filterFamilies.size > 0 || !!G.filterEra || !!$('preset-search').value;
}

function clearFilters() {
  G.favOnly = false;
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
   into whichever row the pointer is over. 191 rows never animate at once. */
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
  card.className = 'preset-card' + (p.id === state.presetId ? ' sel' : '');
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

  // Favorites lead the list (unless the ★ chip already narrows to them, which
  // would render every row twice).
  const favRows = G.favOnly ? [] : presets.filter((p) => G.favs.has(p.id) && matches(p));
  if (favRows.length) {
    const fl = document.createElement('div');
    fl.className = 'family-label favorites';
    fl.innerHTML = `★ FAVORITES <span class="count">${favRows.length}</span>`;
    list.appendChild(fl);
    for (const p of favRows) list.appendChild(presetCard(p));
  }

  let family = null;
  let familyBody = null;
  let shown = favRows.length;
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
      list.appendChild(familyBody);
    }
    (familyBody || list).appendChild(presetCard(p));
  }

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

function selectPreset(pid) {
  state.presetId = pid;
  state.variant = null;
  state.sets = {};
  buildPresetList();
  renderTabs();          // the tab shows which aesthetic the clip is wearing
  buildParamPane();
  schedulePreview(true);
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
  $('preset-title').textContent = p.name;
  $('preset-title').title = p.desc;
  $('preset-sub').textContent = `${p.era} · ${p.family}`;
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
}

function effectCard({ eid, key, params }, variantOv) {
  const eff = G.schema.effects[eid];
  const card = document.createElement('div');
  card.className = 'effect-card';
  const head = document.createElement('div');
  head.className = 'effect-head';
  const tweaked = Object.keys(state.sets).some((s) => s.startsWith(`${key}.`));
  head.innerHTML = `<span class="chev">▶</span><span>${eff.label}</span>${tweaked ? '<span class="e-tweaks" title="Has manual tweaks"></span>' : ''}`;
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
  row.className = 'prow' + (path in state.sets ? ' overridden' : '');
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
  } else if (prm.kind === 'str') {
    const inp = document.createElement('input');
    inp.type = 'text';
    inp.value = String(curVal);
    inp.spellcheck = false;
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
function schedulePreview(immediate = false) {
  if (!state.file || !state.presetId) return;
  if (!G.autoPreview && !immediate) return;
  clearTimeout(previewTimer);
  previewTimer = setTimeout(runPreview, immediate ? 40 : 550);
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
    el.play().catch(() => {});
  };
}

function showRenderOverlay(show, phase = '', frac = 0) {
  $('render-overlay').classList.toggle('hidden', !show);
  if (show) { $('render-phase').textContent = phase; $('render-bar').style.width = `${frac * 100}%`; }
}

function onProgress(msg) {
  if (msg.jobId === G.activeJob) {
    showRenderOverlay(true, `${msg.phase} ${(msg.progress * 100).toFixed(0)}%`, msg.progress);
  } else if (msg.jobId === G.exportJob) {
    setExportStatus(`Exporting… ${msg.phase} ${(msg.progress * 100).toFixed(0)}%`);
    $('btn-export').textContent = `Exporting ${(msg.progress * 100).toFixed(0)}%`;
  }
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
    if (typingTarget(e)) return;
    if (meta && e.code === 'KeyE') {
      e.preventDefault();
      if (G.activeId && state.presetId && !G.exportJob) doExport();
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
      if (!videoA.src) return;
      const play = videoA.paused;
      for (const v of [videoA, videoB]) {
        if (play) v.play().catch(() => {});
        else v.pause();
      }
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
  $('auto-preview').addEventListener('change', (e) => { G.autoPreview = e.target.checked; saveStore(); });
  $('btn-render').addEventListener('click', () => { clearTimeout(previewTimer); runPreview(); });

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

  $('intensity').addEventListener('input', (e) => {
    state.intensity = parseFloat(e.target.value);
    $('intensity-val').textContent = state.intensity.toFixed(2);
    paintRange(e.target);
  });
  $('intensity').addEventListener('change', () => schedulePreview());

  $('texture').addEventListener('input', (e) => {
    state.texture = parseFloat(e.target.value);
    $('texture-val').textContent = state.texture.toFixed(2);
    paintRange(e.target);
  });
  $('texture').addEventListener('change', () => schedulePreview());

  $('seed').value = state.seed;
  $('seed').addEventListener('change', (e) => { state.seed = parseInt(e.target.value || '1', 10); schedulePreview(); });
  $('btn-dice').addEventListener('click', () => {
    state.seed = 1 + Math.floor(Math.random() * 999998);
    $('seed').value = state.seed;
    schedulePreview();
  });

  $('btn-fav').addEventListener('click', () => { if (state.presetId) toggleFav(state.presetId); });
  $('btn-reset-overrides').addEventListener('click', () => {
    state.sets = {};
    buildParamPane();
    schedulePreview();
  });
  $('btn-export-cancel').addEventListener('click', async () => {
    if (!G.exportJob) return;
    $('btn-export-cancel').disabled = true;
    await window.aesth.cancelExport(G.exportJob);
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
      $('player-empty').textContent = 'Cache cleared - press Preview to render again';
      setExportStatus(`Cleared ${r.removed} cached preview${r.removed === 1 ? '' : 's'} (${fmtBytes(r.bytes)}).`);
      await refreshCacheInfo();
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

async function doExport() {
  if (!state.file || !state.presetId) return;
  const base = state.file.path.replace(/\.[^.]+$/, '');
  const variantTag = state.variant ? `-${state.variant}` : '';
  const srcExt = (state.file.path.match(/\.[^.\/]+$/) || ['.mp4'])[0];
  const outExt = state.audioSource ? srcExt : '.mp4';
  const suggestion = `${base}.${state.presetId.replace('/', '-')}${variantTag}${outExt}`;
  const out = await window.aesth.pickExportPath(suggestion, state.audioSource);
  if (!out) return;
  const jobId = `job${++G.jobCounter}`;
  G.exportJob = jobId;
  $('btn-export').disabled = true;
  $('btn-export-cancel').disabled = false;
  $('btn-export-cancel').classList.remove('hidden');
  setExportStatus('Exporting…');
  try {
    const req = {
      jobId,
      input: state.file.path,
      output: out,
      presetId: state.presetId,
      variant: state.variant,
      sets: state.sets,
      seed: state.seed,
      intensity: state.intensity,
      texture: state.texture,
      crf: 17,
      videoOnly: $('exp-video-only').checked,
      audioOnly: $('exp-audio-only').checked,
    };
    const res = await window.aesth.exportRender(req);
    setExportStatusLink('Exported ', res.output);
  } catch (err) {
    if (String(err.message || '').includes('superseded')) {
      setExportStatus('Export canceled - the partial file was removed.');
    } else {
      setExportStatus(`Export failed: ${err.message.slice(0, 300)}`, true);
    }
  } finally {
    G.exportJob = null;
    $('btn-export').disabled = false;
    $('btn-export-cancel').classList.add('hidden');
    $('btn-export').textContent = state.audioSource ? 'Export Full Audio' : 'Export Full Video';
  }
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
  a.onclick = () => window.aesth.reveal(file);
  el.appendChild(a);
  el.append(' - click to reveal');
}
