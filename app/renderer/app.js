'use strict';

/* Aesthetician renderer — schema-driven UI, no framework. */

const $ = (id) => document.getElementById(id);

const state = {
  schema: null,
  file: null,          // {path, width, height, fps, duration, has_audio}
  presetId: null,
  variant: null,
  sets: {},            // "effectKey.param" -> value (user overrides)
  seed: 1,
  intensity: 1.0,
  texture: 1.0,
  previewT: 0,
  duration: 3.0,
  scale: 0.5,
  autoPreview: true,
  muted: true,
  jobCounter: 0,
  activeJob: null,
  exportJob: null,
  originalSrc: null,
  treatedSrc: null,
  thumbs: {},          // presetId -> {poster, anim|null}  (absolute paths)
};

const videoA = $('video-a'); // treated
const videoB = $('video-b'); // original

// ── boot ────────────────────────────────────────────────────────────
(async function boot() {
  const env = await window.aesth.checkEnv();
  if (!env.ok) {
    const w = $('env-warning');
    w.classList.remove('hidden');
    w.textContent = env.problems.join('\n\n');
  }
  state.seed = 1 + Math.floor(Math.random() * 99999);
  try {
    state.thumbs = (await window.aesth.thumbs()).thumbs || {};
  } catch (_) {
    state.thumbs = {}; // thumbs are optional: rows fall back to a placeholder
  }
  try {
    state.schema = await window.aesth.schema();
    buildPresetList();
  } catch (err) {
    const w = $('env-warning');
    w.classList.remove('hidden');
    w.textContent = 'Could not load the engine schema:\n' + err.message;
  }
  window.aesth.onProgress(onProgress);
  wireDrop();
  wireControls();
  if (state.schema) console.log('aesth:renderer-ready');
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
}

async function loadFile(p) {
  try {
    const info = await window.aesth.probe(p);
    state.file = info;
    state.previewT = Math.max((info.duration - state.duration) / 2, 0);
    $('file-chip').textContent = `${p.split('/').pop()} · ${info.width}×${info.height} · ${info.duration.toFixed(1)}s`;
    $('file-chip').classList.remove('hidden');
    $('drop-screen').classList.add('hidden');
    $('workspace').classList.remove('hidden');
    const scrub = $('scrub');
    scrub.max = Math.max(info.duration - state.duration, 0).toFixed(1);
    scrub.value = state.previewT.toFixed(1);
    $('scrub-label').textContent = `preview at ${state.previewT.toFixed(1)}s`;
    state.originalSrc = null; state.treatedSrc = null;
    if (state.presetId) schedulePreview(true);
  } catch (err) {
    alert('Could not read that file:\n' + err.message);
  }
}

// ── preset list ─────────────────────────────────────────────────────
const BLANK_PX = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';

/* Families lead with the looks people reach for most; audio-only sits last
   because those rows leave the picture untouched (their thumbnails are all the
   same untreated frame, so alphabetical order opened the app on 29 of them). */
const FAMILY_ORDER = ['vhs', 'film', 'broadcast', 'cartoon', 'digital', 'world',
  'decay', 'exhibition', 'print', 'transmission', 'stylized', 'audio'];

function famRank(f) {
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
  const t = state.thumbs[p.id];
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
    badge.title = 'Audio-only preset — the picture is untouched';
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

  const t = state.thumbs[p.id];
  if (t && t.anim && !isAudioOnly(p)) armHoverAnim(card, holder, t.anim);
  card.onclick = () => selectPreset(p.id);
  return card;
}

function buildPresetList() {
  const list = $('preset-list');
  stopHoverAnim(); // the row that owned it is about to be discarded
  list.innerHTML = '';
  const presets = Object.values(state.schema.presets)
    .sort((a, b) => (famRank(a.family) - famRank(b.family)) || a.id.localeCompare(b.id));
  const q = ($('preset-search').value || '').toLowerCase();
  state.collapsed = state.collapsed || new Set();
  let family = null;
  let familyBody = null;
  for (const p of presets) {
    const hay = `${p.id} ${p.name} ${p.era} ${p.family} ${p.tagline || ''} ${(p.tags || []).join(' ')}`.toLowerCase();
    if (q && !hay.includes(q)) continue;
    if (p.family !== family) {
      family = p.family;
      const count = presets.filter((x) => x.family === family).length;
      const fl = document.createElement('div');
      fl.className = 'family-label clickable';
      const isCollapsed = !q && state.collapsed.has(family);
      fl.innerHTML = `<span class="chev">${isCollapsed ? '▸' : '▾'}</span> ${family.toUpperCase()} <span class="count">${count}</span>`;
      const fam = family;
      fl.onclick = () => {
        if (state.collapsed.has(fam)) state.collapsed.delete(fam);
        else state.collapsed.add(fam);
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
}

function selectPreset(pid) {
  state.presetId = pid;
  state.variant = null;
  state.sets = {};
  buildPresetList();
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
  const p = state.schema.presets[state.presetId];
  const v = p.variants.find((x) => x.id === state.variant);
  return v ? { ...v.video, ...v.audio } : {};
}

function buildParamPane() {
  const p = state.schema.presets[state.presetId];
  $('preset-title').textContent = p.name;
  $('preset-title').title = p.desc;

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
  const sections = [['PICTURE', p.video], ['SOUND', p.audio]];
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

function effectCard({ eid, key, params }, variantOv) {
  const eff = state.schema.effects[eid];
  const card = document.createElement('div');
  card.className = 'effect-card';
  const head = document.createElement('div');
  head.className = 'effect-head';
  head.innerHTML = `<span class="chev">▶</span><span>${eff.label}</span>`;
  head.title = eff.desc;
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
  label.title = `${path}\n${prm.desc || ''}${prm.unit ? `\nUnit: ${prm.unit}` : ''}`;
  row.appendChild(label);

  const commit = (val) => {
    if (val === baseVal || String(val) === String(baseVal)) delete state.sets[path];
    else state.sets[path] = val;
    row.classList.toggle('overridden', path in state.sets);
    schedulePreview();
  };

  if (prm.kind === 'float' || prm.kind === 'int') {
    const slider = document.createElement('input');
    slider.type = 'range';
    slider.min = prm.lo; slider.max = prm.hi;
    slider.step = prm.kind === 'int' ? 1 : (prm.step || (prm.hi - prm.lo) / 200);
    slider.value = curVal;
    const val = document.createElement('span');
    val.className = 'pval';
    val.textContent = fmtVal(curVal, prm);
    slider.oninput = () => { val.textContent = fmtVal(parseFloat(slider.value), prm); };
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
  if (!state.autoPreview && !immediate) return;
  clearTimeout(previewTimer);
  previewTimer = setTimeout(runPreview, immediate ? 40 : 550);
}

async function runPreview() {
  if (!state.file || !state.presetId) return;
  const jobId = `job${++state.jobCounter}`;
  state.activeJob = jobId;
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
    duration: state.duration,
    scale: state.scale,
    crf: 19,
    videoOnly: $('exp-video-only').checked,
    audioOnly: $('exp-audio-only').checked,
  };
  try {
    const [treated, original] = await Promise.all([
      window.aesth.preview(req),
      state.originalSrc && state.originalT === state.previewT
        ? Promise.resolve({ output: state.originalSrc })
        : window.aesth.snippet({ input: state.file.path, start: state.previewT, duration: state.duration, scale: state.scale }),
    ]);
    if (state.activeJob !== jobId) return; // superseded
    state.treatedSrc = treated.output;
    state.originalSrc = original.output;
    state.originalT = state.previewT;
    $('player-empty').classList.add('hidden');
    setVideo(videoA, treated.output);
    setVideo(videoB, original.output);
  } catch (err) {
    if (String(err.message || '').includes('superseded')) return;
    setExportStatus(`Preview failed: ${err.message.slice(0, 300)}`, true);
  } finally {
    if (state.activeJob === jobId) showRenderOverlay(false);
  }
}

function setVideo(el, src) {
  const t = el === videoA ? (videoB.currentTime || 0) : (videoA.currentTime || 0);
  el.src = `file://${src}?t=${Date.now()}`;
  el.load();
  el.onloadeddata = () => {
    try { el.currentTime = Math.min(t, el.duration - 0.05) || 0; } catch (_) {}
    el.muted = el === videoB ? true : state.muted;
    el.play().catch(() => {});
  };
}

function showRenderOverlay(show, phase = '', frac = 0) {
  $('render-overlay').classList.toggle('hidden', !show);
  if (show) { $('render-phase').textContent = phase; $('render-bar').style.width = `${frac * 100}%`; }
}

function onProgress(msg) {
  if (msg.jobId === state.activeJob) {
    showRenderOverlay(true, `${msg.phase} ${(msg.progress * 100).toFixed(0)}%`, msg.progress);
  } else if (msg.jobId === state.exportJob) {
    setExportStatus(`Exporting… ${msg.phase} ${(msg.progress * 100).toFixed(0)}%`);
    $('btn-export').textContent = `Exporting ${(msg.progress * 100).toFixed(0)}%`;
  }
}

// ── controls ────────────────────────────────────────────────────────
function wireControls() {
  $('preset-search').addEventListener('input', buildPresetList);

  const scrub = $('scrub');
  scrub.addEventListener('input', () => {
    state.previewT = parseFloat(scrub.value);
    $('scrub-label').textContent = `preview at ${state.previewT.toFixed(1)}s`;
  });
  scrub.addEventListener('change', () => schedulePreview());

  $('auto-preview').addEventListener('change', (e) => { state.autoPreview = e.target.checked; });
  $('btn-render').addEventListener('click', () => { clearTimeout(previewTimer); runPreview(); });

  const ab = $('btn-ab');
  const showOriginal = (on) => {
    videoA.style.opacity = on ? '0' : '1';
    $('ab-badge').classList.toggle('hidden', !on);
    if (on) { videoB.currentTime = videoA.currentTime; videoB.muted = state.muted; videoA.muted = true; }
    else { videoA.muted = state.muted; videoB.muted = true; }
  };
  ab.addEventListener('mousedown', () => showOriginal(true));
  ab.addEventListener('mouseup', () => showOriginal(false));
  ab.addEventListener('mouseleave', () => showOriginal(false));

  $('btn-mute').addEventListener('click', () => {
    state.muted = !state.muted;
    videoA.muted = state.muted;
    $('btn-mute').textContent = state.muted ? '🔇' : '🔊';
  });

  $('intensity').addEventListener('input', (e) => {
    state.intensity = parseFloat(e.target.value);
    $('intensity-val').textContent = state.intensity.toFixed(2);
  });
  $('intensity').addEventListener('change', () => schedulePreview());

  $('texture').addEventListener('input', (e) => {
    state.texture = parseFloat(e.target.value);
    $('texture-val').textContent = state.texture.toFixed(2);
  });
  $('texture').addEventListener('change', () => schedulePreview());

  $('seed').value = state.seed;
  $('seed').addEventListener('change', (e) => { state.seed = parseInt(e.target.value || '1', 10); schedulePreview(); });
  $('btn-dice').addEventListener('click', () => {
    state.seed = 1 + Math.floor(Math.random() * 99999);
    $('seed').value = state.seed;
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
}

async function doExport() {
  if (!state.file || !state.presetId) return;
  const base = state.file.path.replace(/\.[^.]+$/, '');
  const variantTag = state.variant ? `-${state.variant}` : '';
  const suggestion = `${base}.${state.presetId.replace('/', '-')}${variantTag}.mp4`;
  const out = await window.aesth.pickExportPath(suggestion);
  if (!out) return;
  const jobId = `job${++state.jobCounter}`;
  state.exportJob = jobId;
  $('btn-export').disabled = true;
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
    texture: state.texture,
      crf: 17,
      videoOnly: $('exp-video-only').checked,
      audioOnly: $('exp-audio-only').checked,
    };
    const res = await window.aesth.exportRender(req);
    setExportStatusLink('Exported ', res.output);
  } catch (err) {
    setExportStatus(`Export failed: ${err.message.slice(0, 300)}`, true);
  } finally {
    state.exportJob = null;
    $('btn-export').disabled = false;
    $('btn-export').textContent = 'Export Full Video';
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
  el.append(' — click to reveal');
}
