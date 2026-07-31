'use strict';

const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
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
const CACHE_DIR = path.join(app.getPath('userData'), 'preview-cache');

let win = null;
let previewProc = null; // superseded previews get killed
const exportProcs = new Map();

function ensureCacheDir() {
  fs.mkdirSync(CACHE_DIR, { recursive: true });
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
      else reject(new Error(err.slice(-2000) || `exit ${code}`));
    });
    p.on('error', (e) => { clearTimeout(t); reject(e); });
  });
}

function renderArgs(req, outputPath) {
  const args = ['-m', 'aesthetician.cli', 'apply', req.input, '-o', outputPath,
    '-p', req.presetId, '--json-progress', '--seed', String(req.seed ?? 1),
    '--intensity', String(req.intensity ?? 1.0),
    '--texture', String(req.texture ?? 1.0)];
  if (req.variant) args.push('--variant', req.variant);
  if (req.videoOnly) args.push('--video-only');
  if (req.audioOnly) args.push('--audio-only');
  if (req.start != null) args.push('--start', String(req.start));
  if (req.duration != null) args.push('--duration', String(req.duration));
  if (req.scale != null) args.push('--scale', String(req.scale));
  if (req.crf != null) args.push('--crf', String(req.crf));
  for (const [k, v] of Object.entries(req.sets || {})) args.push('--set', `${k}=${v}`);
  return args;
}

function cacheKey(req) {
  const h = crypto.createHash('sha1');
  h.update(JSON.stringify({ ...req, jobId: undefined }));
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
      } else reject(new Error(err.slice(-2000) || `exit ${code}`));
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
    },
  });
  win.loadFile(path.join(__dirname, 'renderer', 'index.html'));
});

app.on('window-all-closed', () => {
  if (previewProc) previewProc.kill('SIGKILL');
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
  if (fs.existsSync(output)) return { output, cached: true };
  if (previewProc) { try { previewProc.kill('SIGKILL'); } catch (_) {} previewProc = null; }
  const args = renderArgs(req, output + '.part' + ext);
  await spawnRender(args, req.jobId, e.sender, 'preview');
  fs.renameSync(output + '.part' + ext, output);
  return { output, cached: false };
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
  await spawnRender(args, req.jobId, e.sender, 'export', req.output);
  return { output: req.output };
});

ipcMain.handle('aesth:cancel-export', async (_e, jobId) => {
  const p = exportProcs.get(jobId);
  if (p) { p.kill('SIGKILL'); exportProcs.delete(jobId); return true; }
  return false;
});

ipcMain.handle('aesth:reveal', (_e, file) => shell.showItemInFolder(file));

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
ipcMain.handle('aesth:update-download', (e) => updater.download(e.sender));
ipcMain.handle('aesth:update-cancel', () => updater.cancelDownload());
ipcMain.handle('aesth:update-install', () => updater.install());
ipcMain.handle('aesth:update-reveal', () => {
  const file = updater.stagedFile();
  if (file) shell.showItemInFolder(file);
  return { file };
});
ipcMain.handle('aesth:open-external', (_e, url) => {
  // Only ever our own repo: a URL from a release payload does not get to pick
  // what the browser opens.
  const ok = /^https:\/\/github\.com\/heresalexandria\/aesthetician(\/|$)/.test(String(url || ''));
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
