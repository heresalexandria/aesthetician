'use strict';

const { app, BrowserWindow, ipcMain, dialog, shell, Notification } = require('electron');
const { spawn } = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const updater = require('./updater');

const REPO_ROOT = path.resolve(__dirname, '..');

/* ── runtime resolution ──────────────────────────────────────────────────
   Dev runs against the repo's .venv and whatever ffmpeg is on PATH. A packaged
   build ships a relocatable Python runtime, static ffmpeg binaries and the
   asset packs under Resources/, so every path is resolved relative to that.
   Either can be overridden by environment variable.                        */
const PACKAGED = app.isPackaged;
const RES = PACKAGED ? process.resourcesPath : REPO_ROOT;
const EXE = process.platform === 'win32' ? '.exe' : '';

function bundled(...parts) {
  return path.join(RES, ...parts);
}

const PYTHON = process.env.AESTHETICIAN_PYTHON || (PACKAGED
  ? bundled('pyruntime', process.platform === 'win32' ? 'python.exe' : path.join('bin', 'python3'))
  : path.join(REPO_ROOT, '.venv', 'bin', 'python'));

const ASSETS_DIR = process.env.AESTHETICIAN_ASSETS || bundled('assets');
const THUMBS_DIR = path.join(ASSETS_DIR, 'thumbs');
const FFMPEG = process.env.AESTHETICIAN_FFMPEG
  || (PACKAGED ? bundled('bin', `ffmpeg${EXE}`) : 'ffmpeg');
const FFPROBE = process.env.AESTHETICIAN_FFPROBE
  || (PACKAGED ? bundled('bin', `ffprobe${EXE}`) : 'ffprobe');

/* The engine reads these; child processes inherit them. */
function childEnv() {
  const env = { ...process.env, AESTHETICIAN_ASSETS: ASSETS_DIR };
  if (PACKAGED) {
    // Never let Python write .pyc into the bundle: Resources is covered by the
    // code signature, and mutating it makes macOS refuse the next launch. The
    // build ships hash-based caches, so there is nothing to regenerate anyway.
    env.PYTHONDONTWRITEBYTECODE = '1';
  }
  if (FFMPEG !== 'ffmpeg') env.AESTHETICIAN_FFMPEG = FFMPEG;
  if (FFPROBE !== 'ffprobe') env.AESTHETICIAN_FFPROBE = FFPROBE;
  if (PACKAGED) {
    const dir = path.dirname(FFMPEG);
    env.PATH = `${dir}${path.delimiter}${env.PATH || ''}`;
  }
  return env;
}

const CHILD_OPTS = () => ({ cwd: PACKAGED ? RES : REPO_ROOT, env: childEnv() });

/* The dev harnesses get a profile of their own, set before anything reads
   userData. `--shot-js` runs arbitrary code in the renderer, which is the point
   of it, and that code can reach localStorage - where favorites, custom
   aesthetics and saved stacks live. Sharing a profile with the real app means a
   test script that seeds a few fixtures can overwrite work someone spent an
   evening on, and localStorage keeps no history to restore from. Nothing about
   these two flags is worth that risk, so they get a scratch profile: the only
   cost is that a shot re-renders its preview instead of hitting a warm cache. */
if (process.argv.includes('--smoke') || process.argv.some((a) => a.startsWith('--shot'))) {
  app.setPath('userData', path.join(app.getPath('temp'), 'aesthetician-harness'));
}

const CACHE_DIR = path.join(app.getPath('userData'), 'preview-cache');
// Layer specs are scratch handed to the CLI, not previews - keep them out of
// the cache the footer reports and the Clear button empties.
const LAYER_SPEC_DIR = path.join(app.getPath('temp'), 'aesthetician-layers');

/* Specs are unlinked as soon as their render settles, but a crash or a kill
   mid-render leaves one behind. Sweep the stale ones on the way in rather than
   letting them accumulate across a bad week. */
function sweepLayerSpecs() {
  const cutoff = Date.now() - 60 * 60 * 1000;
  let files = [];
  try { files = fs.readdirSync(LAYER_SPEC_DIR); } catch (_) { return; }
  for (const f of files) {
    const full = path.join(LAYER_SPEC_DIR, f);
    try {
      if (fs.statSync(full).mtimeMs < cutoff) fs.unlinkSync(full);
    } catch (_) { /* vanished, or in use */ }
  }
}

function dropLayerSpec(req) {
  if (req && req._layerSpec) {
    try { fs.unlinkSync(req._layerSpec); } catch (_) { /* already gone */ }
  }
}

let win = null;
let previewProc = null; // superseded previews get killed
let stillProc = null;   // and so does the still that was racing alongside one
const exportProcs = new Map();

function ensureCacheDir() {
  fs.mkdirSync(CACHE_DIR, { recursive: true });
}

/* What a failed child said, trimmed for a human rather than for a byte count.
   The tail is the half worth keeping - Python puts the sentence that names the
   cause on the last line - but cutting at a fixed offset landed mid-word and
   opened the report with "Error: ceback (most recent call last):". So: cut to
   the next line break, and keep enough that a whole traceback survives. */
function tailOf(text, max = 8000) {
  const s = String(text || '');
  if (s.length <= max) return s;
  const cut = s.slice(-max);
  const nl = cut.indexOf('\n');
  return `…\n${nl >= 0 ? cut.slice(nl + 1) : cut}`;
}

function runCapture(args, { timeoutMs = 60000 } = {}) {
  return new Promise((resolve, reject) => {
    const p = spawn(PYTHON, ['-m', 'aesthetician.cli', ...args], CHILD_OPTS());
    let out = '';
    let err = '';
    const t = setTimeout(() => { p.kill('SIGKILL'); reject(new Error('timed out')); }, timeoutMs);
    p.stdout.on('data', (d) => (out += d));
    p.stderr.on('data', (d) => (err += d));
    p.on('close', (code) => {
      clearTimeout(t);
      if (code === 0) resolve(out);
      else reject(new Error(tailOf(err) || `exit ${code}`));
    });
    p.on('error', (e) => { clearTimeout(t); reject(e); });
  });
}

function renderArgs(req, outputPath) {
  const args = ['-m', 'aesthetician.cli', 'apply', req.input, '-o', outputPath,
    '--json-progress'];

  // A stack carries its own per-layer seed, intensity, texture, variant and
  // overrides, so none of the single-preset flags apply to it. Written to a
  // file rather than passed inline: Windows caps a command line at 32k and a
  // deep stack of overrides can get close.
  if (Array.isArray(req.layers) && req.layers.length) {
    fs.mkdirSync(LAYER_SPEC_DIR, { recursive: true });
    const spec = path.join(LAYER_SPEC_DIR, `${req.jobId || 'job'}-${process.hrtime.bigint()}.json`);
    fs.writeFileSync(spec, JSON.stringify(req.layers));
    args.push('--layers', `@${spec}`);
    req._layerSpec = spec;
  } else {
    args.push('-p', req.presetId,
      '--seed', String(req.seed ?? 1),
      '--intensity', String(req.intensity ?? 1.0),
      '--texture', String(req.texture ?? 1.0));
    if (req.variant) args.push('--variant', req.variant);
  }

  if (req.videoOnly) args.push('--video-only');
  if (req.audioOnly) args.push('--audio-only');
  if (req.start != null) args.push('--start', String(req.start));
  if (req.duration != null) args.push('--duration', String(req.duration));
  if (req.scale != null) args.push('--scale', String(req.scale));
  if (req.crf != null) args.push('--crf', String(req.crf));
  if (!(Array.isArray(req.layers) && req.layers.length)) {
    for (const [k, v] of Object.entries(req.sets || {})) args.push('--set', `${k}=${v}`);
  }
  return args;
}

/* Frame 0 of the same render, for the paused player to show while the clip is
   still encoding. Deliberately not `renderArgs`: a still has no progress to
   report, no audio to treat and no crf to honour, and folding those into one
   builder would mean four flags that only apply to one of the two callers. */
function stillArgs(req, outputPath) {
  const args = ['-m', 'aesthetician.cli', 'still', req.input, '-o', outputPath];
  if (Array.isArray(req.layers) && req.layers.length) {
    fs.mkdirSync(LAYER_SPEC_DIR, { recursive: true });
    const spec = path.join(LAYER_SPEC_DIR, `${req.jobId || 'still'}-${process.hrtime.bigint()}.json`);
    fs.writeFileSync(spec, JSON.stringify(req.layers));
    args.push('--layers', `@${spec}`);
    req._layerSpec = spec;
  } else {
    args.push('-p', req.presetId,
      '--seed', String(req.seed ?? 1),
      '--intensity', String(req.intensity ?? 1.0),
      '--texture', String(req.texture ?? 1.0));
    if (req.variant) args.push('--variant', req.variant);
    for (const [k, v] of Object.entries(req.sets || {})) args.push('--set', `${k}=${v}`);
  }
  if (req.start != null) args.push('--start', String(req.start));
  if (req.duration != null) args.push('--duration', String(req.duration));
  if (req.scale != null) args.push('--scale', String(req.scale));
  return args;
}

function cacheKey(req) {
  const h = crypto.createHash('sha1');
  h.update(JSON.stringify({ ...req, jobId: undefined }));
  // A cached preview is "what the engine renders for these params", and the
  // engine's output changes across releases (the BT.709 color fix did), so the
  // version is part of the identity.
  h.update(app.getVersion());
  let stat = null;
  try { stat = fs.statSync(req.input); } catch (_) {}
  h.update(String(stat ? stat.mtimeMs : 0));
  return h.digest('hex');
}

function spawnRender(args, jobId, sender, kind, output = null) {
  return new Promise((resolve, reject) => {
    const p = spawn(PYTHON, args, CHILD_OPTS());
    if (kind === 'preview') previewProc = p;
    if (kind === 'export') exportProcs.set(jobId, p);
    let err = '';
    let buf = '';
    p.stdout.on('data', (d) => {
      buf += d.toString();
      let idx;
      while ((idx = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, idx).trim();
        buf = buf.slice(idx + 1);
        if (!line) continue;
        try {
          const msg = JSON.parse(line);
          sender.send('aesth:progress', { jobId, ...msg });
        } catch (_) { /* non-JSON line */ }
      }
    });
    p.stderr.on('data', (d) => (err += d));
    p.on('close', (code) => {
      if (kind === 'preview' && previewProc === p) previewProc = null;
      if (kind === 'export') exportProcs.delete(jobId);
      if (code === 0) resolve();
      else if (p.killed) {
        // A canceled export leaves a truncated file at the destination the user
        // chose; nobody wants that, so sweep it up.
        if (output) { try { fs.unlinkSync(output); } catch (_) { /* never written */ } }
        reject(new Error('superseded'));
      } else reject(new Error(tailOf(err) || `exit ${code}`));
    });
    p.on('error', reject);
  });
}

const SMOKE = process.argv.includes('--smoke');
const SHOT = argValue('--shot');           // dev utility: write a screenshot and exit

function argValue(flag) {
  const i = process.argv.indexOf(flag);
  return i >= 0 ? process.argv[i + 1] : null;
}

app.whenReady().then(() => {
  ensureCacheDir();
  sweepLayerSpecs();
  if (SMOKE) runSmoke();
  if (SHOT) runShot();
  const iconPng = path.join(__dirname, 'renderer', 'icon.png');
  // Packaged builds carry a proper .icns/.ico; this covers the window icon on
  // Windows/Linux and the Dock while running from a dev checkout on macOS.
  if (process.platform === 'darwin' && app.dock) {
    try { app.dock.setIcon(iconPng); } catch (_) { /* cosmetic */ }
  }
  win = new BrowserWindow({
    width: 1480,
    height: 940,
    minWidth: 1120,
    minHeight: 700,
    title: 'Aesthetician',
    backgroundColor: '#0a0b10',
    titleBarStyle: 'hiddenInset',
    icon: iconPng,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      // The renderer paints the version chip on its first frame. Passing it as
      // an argument means the preload can read it synchronously - an IPC round
      // trip, however cheap, still costs a frame of showing a placeholder.
      additionalArguments: [
        `--aesth-version=${app.getVersion()}`,
        `--aesth-packaged=${app.isPackaged ? '1' : '0'}`,
      ],
    },
  });
  win.loadFile(path.join(__dirname, 'renderer', 'index.html'));
});

app.on('window-all-closed', () => {
  if (previewProc) previewProc.kill('SIGKILL');
  if (stillProc) stillProc.kill('SIGKILL');
  for (const p of exportProcs.values()) p.kill('SIGKILL');
  app.quit();
});

async function runSmoke() {
  // `npm start -- --smoke`: boot renderer, check engine wiring, exit 0/1.
  const deadline = setTimeout(() => { console.error('[smoke] TIMEOUT'); app.exit(1); }, 45000);
  let rendererReady = false;
  let rendererErrors = [];
  app.on('web-contents-created', (_e, wc) => {
    wc.on('console-message', (_ev, level, message) => {
      if (message.includes('aesth:renderer-ready')) rendererReady = true;
      if (level >= 3) rendererErrors.push(message);
    });
  });
  try {
    const schema = JSON.parse(await runCapture(['schema']));
    const nP = Object.keys(schema.presets).length;
    const nE = Object.keys(schema.effects).length;
    console.log(`[smoke] schema ok: ${nE} effects, ${nP} presets`);
    const waitUntil = Date.now() + 30000;
    while (!rendererReady && Date.now() < waitUntil) {
      await new Promise((r) => setTimeout(r, 250));
    }
    clearTimeout(deadline);
    if (!rendererReady) { console.error('[smoke] renderer never signaled ready'); app.exit(1); return; }
    if (rendererErrors.length) { console.error('[smoke] renderer errors:', rendererErrors.join(' | ')); app.exit(1); return; }
    console.log('[smoke] renderer ready, no errors - PASS');
    app.exit(0);
  } catch (err) {
    clearTimeout(deadline);
    console.error('[smoke] FAIL:', err.message);
    app.exit(1);
  }
}

/* `npx electron . --shot out.png [--shot-file clip.mp4] [--shot-preset id]
    [--shot-js steps.js]`
   Boots the app, optionally opens a clip and applies a preset, waits for its
   preview to finish rendering, runs any extra scripted steps, captures the
   window and exits. Used to keep the README screenshot honest without a hand
   on the camera. */
async function runShot() {
  const file = argValue('--shot-file');
  const preset = argValue('--shot-preset');
  const jsFile = argValue('--shot-js');
  // Without this, macOS App Nap freezes the unfocused window's timers and the
  // shot never finishes.
  const { powerSaveBlocker } = require('electron');
  powerSaveBlocker.start('prevent-app-suspension');
  const deadline = setTimeout(() => { console.error('[shot] TIMEOUT'); app.exit(1); }, 180000);
  const js = (code) => win.webContents.executeJavaScript(code, true);
  const settle = (ms) => new Promise((r) => setTimeout(r, ms));
  try {
    await new Promise((resolve) => {
      app.on('web-contents-created', (_e, wc) => {
        wc.on('console-message', (_ev, level, message) => {
          if (message.includes('aesth:renderer-ready')) resolve();
          if (level >= 3) console.error('[shot] renderer:', message);
        });
      });
    });
    await settle(600);
    if (file) {
      await js(`loadFile(${JSON.stringify(path.resolve(file))})`);
      await settle(400);
      if (preset) {
        await js(`selectPreset(${JSON.stringify(preset)})`);
        // wait for the preview render to complete and the players to load
        for (let i = 0; i < 600; i++) {
          const done = await js(`(!!document.querySelector('#video-a[src]')
            && $('render-overlay').classList.contains('hidden'))`);
          if (done) break;
          await settle(250);
        }
        await settle(1200);   // give the <video> a frame to paint
      }
    }
    if (jsFile) {
      await js(fs.readFileSync(path.resolve(jsFile), 'utf8'));
      await settle(500);
    }
    const image = await win.webContents.capturePage();
    const out = path.resolve(SHOT);
    if (/\.jpe?g$/i.test(out)) fs.writeFileSync(out, image.toJPEG(92));
    else fs.writeFileSync(out, image.toPNG());
    console.log(`[shot] wrote ${out}`);
    clearTimeout(deadline);
    app.exit(0);
  } catch (err) {
    clearTimeout(deadline);
    console.error('[shot] FAIL:', err.message);
    app.exit(1);
  }
}

ipcMain.handle('aesth:schema', async () => JSON.parse(await runCapture(['schema'])));
ipcMain.handle('aesth:probe', async (_e, file) => JSON.parse(await runCapture(['probe', file])));

ipcMain.handle('aesth:preview', async (e, req) => {
  const key = cacheKey({ ...req, kind: 'preview' });
  // An audio source produces audio: keep the cache honest about that.
  const ext = req.audioSource ? '.m4a' : '.mp4';
  const output = path.join(CACHE_DIR, `${key}${ext}`);
  // Whatever is in flight was asked for by a state the user has since left, so
  // it goes - and it goes before the cache is consulted. Letting a cache hit
  // return without stopping it left the old render running to completion and
  // reporting back *after* the answer the user is looking at, which is one
  // knob-flick away any time a preview takes longer than the next tweak.
  if (previewProc) { try { previewProc.kill('SIGKILL'); } catch (_) {} previewProc = null; }
  // The still is not this render's predecessor, it is its partner: the renderer
  // asks for both at once and the still is the half that answers first. Killing
  // it here killed it every time, roughly a millisecond after it started.
  if (fs.existsSync(output)) return { output, cached: true };
  const args = renderArgs(req, output + '.part' + ext);
  try {
    await spawnRender(args, req.jobId, e.sender, 'preview');
  } finally {
    dropLayerSpec(req);
  }
  fs.renameSync(output + '.part' + ext, output);
  return { output, cached: false };
});

/* The paused player's fast first look. Same cache directory as the clips, keyed
   the same way, so a still costs nothing the second time you land on a setting. */
ipcMain.handle('aesth:still', async (_e, req) => {
  const key = cacheKey({ ...req, kind: 'still' });
  const output = path.join(CACHE_DIR, `${key}.png`);
  const meta = `${output}.json`;
  if (stillProc) { try { stillProc.kill('SIGKILL'); } catch (_) {} stillProc = null; }
  if (fs.existsSync(output) && fs.existsSync(meta)) {
    try { return { output, ...JSON.parse(fs.readFileSync(meta, 'utf8')), cached: true }; } catch (_) { /* rewrite it */ }
  }
  const part = `${output}.part.png`;
  const args = stillArgs(req, part);
  let out = '';
  try {
    out = await new Promise((resolve, reject) => {
      const p = spawn(PYTHON, args, CHILD_OPTS());
      stillProc = p;
      let so = '';
      let se = '';
      p.stdout.on('data', (d) => (so += d));
      p.stderr.on('data', (d) => (se += d));
      p.on('close', (code) => {
        if (stillProc === p) stillProc = null;
        if (code === 0) resolve(so);
        else if (p.killed) reject(new Error('superseded'));
        else reject(new Error(tailOf(se) || `exit ${code}`));
      });
      p.on('error', reject);
    });
  } catch (err) {
    try { fs.unlinkSync(part); } catch (_) { /* never written */ }
    throw err;
  } finally {
    dropLayerSpec(req);
  }
  const info = JSON.parse(out.trim().split('\n').pop());
  fs.renameSync(part, output);
  fs.writeFileSync(meta, JSON.stringify({ exact: info.exact }));
  return { output, exact: info.exact, cached: false };
});

ipcMain.handle('aesth:snippet', async (_e, req) => {
  const key = cacheKey({ ...req, kind: 'snippet' });
  const output = path.join(CACHE_DIR, `${key}${req.audioSource ? '.m4a' : '.mp4'}`);
  if (fs.existsSync(output)) return { output };
  await runCapture(['snippet', req.input, '-o', output,
    '--start', String(req.start ?? 0), '--duration', String(req.duration ?? 3),
    '--scale', String(req.scale ?? 0.5)], { timeoutMs: 120000 });
  return { output };
});

ipcMain.handle('aesth:pick-input', async () => {
  const r = await dialog.showOpenDialog(win, {
    title: 'Open a video or audio file',
    properties: ['openFile'],
    filters: [
      { name: 'Media', extensions: ['mp4', 'mov', 'mkv', 'avi', 'webm', 'm4v', 'mpg', 'mpeg', 'ts',
        'wav', 'mp3', 'm4a', 'aac', 'flac', 'aiff', 'ogg'] },
      { name: 'All Files', extensions: ['*'] },
    ],
  });
  return r.canceled || !r.filePaths.length ? null : r.filePaths[0];
});

ipcMain.handle('aesth:pick-export-path', async (_e, suggestion, audioOnly = false) => {
  const r = await dialog.showSaveDialog(win, {
    title: audioOnly ? 'Export treated audio' : 'Export treated video',
    defaultPath: suggestion,
    filters: audioOnly
      ? [{ name: 'Audio', extensions: ['wav', 'flac', 'm4a', 'aac', 'mp3', 'aiff'] }]
      : [{ name: 'Video', extensions: ['mp4'] }],
  });
  return r.canceled ? null : r.filePath;
});

ipcMain.handle('aesth:export', async (e, req) => {
  const args = renderArgs(req, req.output);
  try {
    await spawnRender(args, req.jobId, e.sender, 'export', req.output);
  } finally {
    dropLayerSpec(req);
  }
  return { output: req.output };
});

ipcMain.handle('aesth:cancel-export', async (_e, jobId) => {
  const p = exportProcs.get(jobId);
  if (p) { p.kill('SIGKILL'); exportProcs.delete(jobId); return true; }
  return false;
});

/* Reports whether it found anything: showItemInFolder on a path that has since
   moved does nothing at all, and a button that silently does nothing is worse
   than one that explains itself. */
ipcMain.handle('aesth:reveal', (_e, file) => {
  if (!file || !fs.existsSync(file)) return { ok: false };
  shell.showItemInFolder(file);
  return { ok: true };
});

/* ── desktop notifications ───────────────────────────────────────────────
   An export is the one thing here worth interrupting someone for: it takes
   minutes, and the whole point is that you go and do something else. This
   lives in main rather than the renderer because a renderer Notification is
   tied to a page that may be backgrounded or throttled, which is exactly when
   the notification matters most.

   `reveal` carries the finished file, so clicking the banner shows it in the
   Finder rather than just raising a window over whatever you moved on to. */
ipcMain.handle('aesth:notify', (_e, opts = {}) => {
  if (!Notification.isSupported()) return { ok: false };
  const { title = '', body = '', reveal = '' } = opts;
  if (!title) return { ok: false };
  const note = new Notification({ title, body, silent: false });
  note.on('click', () => {
    if (reveal && fs.existsSync(reveal)) { shell.showItemInFolder(reveal); return; }
    if (win && !win.isDestroyed()) {
      if (win.isMinimized()) win.restore();
      win.show();
      win.focus();
    }
  });
  note.show();
  return { ok: true };
});

/* ── preview cache ───────────────────────────────────────────────────────
   Every preview render is kept on disk keyed by its full parameter set, which
   is what makes flipping back to earlier settings instant. It is disposable:
   deleting it only costs re-render time.                                    */
function cacheEntries() {
  let files = [];
  try { files = fs.readdirSync(CACHE_DIR); } catch (_) { return []; }
  const out = [];
  for (const f of files) {
    const full = path.join(CACHE_DIR, f);
    try {
      const st = fs.statSync(full);
      if (st.isFile()) out.push({ path: full, bytes: st.size, mtime: st.mtimeMs });
    } catch (_) { /* vanished mid-scan */ }
  }
  return out;
}

ipcMain.handle('aesth:cache-info', () => {
  const entries = cacheEntries();
  return {
    dir: CACHE_DIR,
    count: entries.length,
    bytes: entries.reduce((n, e) => n + e.bytes, 0),
    newest: entries.reduce((t, e) => Math.max(t, e.mtime), 0) || null,
  };
});

ipcMain.handle('aesth:cache-clear', () => {
  let removed = 0;
  let bytes = 0;
  for (const e of cacheEntries()) {
    try { fs.unlinkSync(e.path); removed++; bytes += e.bytes; } catch (_) { /* in use */ }
  }
  return { removed, bytes };
});

ipcMain.handle('aesth:cache-reveal', () => {
  fs.mkdirSync(CACHE_DIR, { recursive: true });
  shell.openPath(CACHE_DIR);
  return { dir: CACHE_DIR };
});

// Preset thumbnails (scripts/make_thumbs.py). Returns absolute paths the
// renderer loads over file://; presets without a rendered thumb are omitted.
ipcMain.handle('aesth:thumbs', () => {
  const result = { dir: THUMBS_DIR, thumbs: {} };
  let files;
  try { files = fs.readdirSync(THUMBS_DIR); } catch (_) { return result; }
  const posters = new Map();
  const anims = new Map();
  for (const f of files) {
    const ext = path.extname(f).toLowerCase();
    const id = f.slice(0, f.length - ext.length);
    if (!id) continue;
    if (ext === '.png') posters.set(id, path.join(THUMBS_DIR, f));
    else if (ext === '.webp' || ext === '.gif') anims.set(id, path.join(THUMBS_DIR, f));
  }
  for (const [id, poster] of posters) {
    result.thumbs[id] = { poster, anim: anims.get(id) || null };
  }
  return result;
});

/* ── updates ─────────────────────────────────────────────────────────────
   See app/updater.js for why this is hand-rolled rather than electron-updater.
   The renderer drives all of it: nothing is fetched or installed on a timer. */
ipcMain.handle('aesth:update-info', () => updater.info());
ipcMain.handle('aesth:update-check', (_e, opts) => updater.check(opts || {}));
ipcMain.handle('aesth:update-releases', (_e, opts) => updater.releases(opts || {}));
// opts.tag picks a specific release; without one this takes the latest.
ipcMain.handle('aesth:update-download', (e, opts) => updater.download(e.sender, opts || {}));
ipcMain.handle('aesth:update-cancel', () => updater.cancelDownload());
ipcMain.handle('aesth:update-install', () => updater.install());
ipcMain.handle('aesth:update-reveal', () => {
  const file = updater.stagedFile();
  if (file) shell.showItemInFolder(file);
  return { file };
});
ipcMain.handle('aesth:note-image', (_e, url) => updater.noteImage(url));
ipcMain.handle('aesth:open-external', (_e, url) => {
  // Only ever our own repo: a URL from a release payload does not get to pick
  // what the browser opens.
  const raw = String(url || '');
  const ok = /^https:\/\/github\.com\/heresalexandria\/aesthetician(\/|$)/.test(raw)
    // Screenshots in release notes live on GitHub's attachment host, not under
    // the repo path. Still GitHub, still https, still only ever handed to the
    // user's own browser.
    || /^https:\/\/github\.com\/user-attachments\/assets\//.test(raw)
    || /^https:\/\/[a-z0-9-]+\.githubusercontent\.com\//.test(raw);
  if (ok) shell.openExternal(url);
  return ok;
});

ipcMain.handle('aesth:check-env', async () => {
  const problems = [];
  if (!fs.existsSync(PYTHON)) problems.push(`Python not found at ${PYTHON} - create the venv (see README) or set AESTHETICIAN_PYTHON.`);
  try { await runCapture(['effects', '--json'], { timeoutMs: 30000 }); }
  catch (err) { problems.push(`Engine check failed: ${String(err.message).slice(0, 400)}`); }
  return { ok: problems.length === 0, problems, python: PYTHON };
});
