'use strict';

const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const { spawn } = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '..');
const PYTHON = process.env.AESTHETICIAN_PYTHON || path.join(REPO_ROOT, '.venv', 'bin', 'python');
const CACHE_DIR = path.join(app.getPath('userData'), 'preview-cache');

let win = null;
let previewProc = null; // superseded previews get killed
const exportProcs = new Map();

function ensureCacheDir() {
  fs.mkdirSync(CACHE_DIR, { recursive: true });
}

function runCapture(args, { timeoutMs = 60000 } = {}) {
  return new Promise((resolve, reject) => {
    const p = spawn(PYTHON, ['-m', 'aesthetician.cli', ...args], { cwd: REPO_ROOT });
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
    '--intensity', String(req.intensity ?? 1.0)];
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

function spawnRender(args, jobId, sender, kind) {
  return new Promise((resolve, reject) => {
    const p = spawn(PYTHON, args, { cwd: REPO_ROOT });
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
      else if (p.killed) reject(new Error('superseded'));
      else reject(new Error(err.slice(-2000) || `exit ${code}`));
    });
    p.on('error', reject);
  });
}

const SMOKE = process.argv.includes('--smoke');

app.whenReady().then(() => {
  ensureCacheDir();
  if (SMOKE) runSmoke();
  win = new BrowserWindow({
    width: 1480,
    height: 940,
    minWidth: 1120,
    minHeight: 700,
    title: 'Aesthetician',
    backgroundColor: '#0d0e11',
    titleBarStyle: 'hiddenInset',
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
    console.log('[smoke] renderer ready, no errors — PASS');
    app.exit(0);
  } catch (err) {
    clearTimeout(deadline);
    console.error('[smoke] FAIL:', err.message);
    app.exit(1);
  }
}

ipcMain.handle('aesth:schema', async () => JSON.parse(await runCapture(['schema'])));
ipcMain.handle('aesth:probe', async (_e, file) => JSON.parse(await runCapture(['probe', file])));

ipcMain.handle('aesth:preview', async (e, req) => {
  const key = cacheKey({ ...req, kind: 'preview' });
  const output = path.join(CACHE_DIR, `${key}.mp4`);
  if (fs.existsSync(output)) return { output, cached: true };
  if (previewProc) { try { previewProc.kill('SIGKILL'); } catch (_) {} previewProc = null; }
  const args = renderArgs(req, output + '.part.mp4');
  await spawnRender(args, req.jobId, e.sender, 'preview');
  fs.renameSync(output + '.part.mp4', output);
  return { output, cached: false };
});

ipcMain.handle('aesth:snippet', async (_e, req) => {
  const key = cacheKey({ ...req, kind: 'snippet' });
  const output = path.join(CACHE_DIR, `${key}.mp4`);
  if (fs.existsSync(output)) return { output };
  await runCapture(['snippet', req.input, '-o', output,
    '--start', String(req.start ?? 0), '--duration', String(req.duration ?? 3),
    '--scale', String(req.scale ?? 0.5)], { timeoutMs: 120000 });
  return { output };
});

ipcMain.handle('aesth:pick-export-path', async (_e, suggestion) => {
  const r = await dialog.showSaveDialog(win, {
    title: 'Export treated video',
    defaultPath: suggestion,
    filters: [{ name: 'Video', extensions: ['mp4'] }],
  });
  return r.canceled ? null : r.filePath;
});

ipcMain.handle('aesth:export', async (e, req) => {
  const args = renderArgs(req, req.output);
  await spawnRender(args, req.jobId, e.sender, 'export');
  return { output: req.output };
});

ipcMain.handle('aesth:cancel-export', async (_e, jobId) => {
  const p = exportProcs.get(jobId);
  if (p) { p.kill('SIGKILL'); exportProcs.delete(jobId); return true; }
  return false;
});

ipcMain.handle('aesth:reveal', (_e, file) => shell.showItemInFolder(file));

ipcMain.handle('aesth:check-env', async () => {
  const problems = [];
  if (!fs.existsSync(PYTHON)) problems.push(`Python not found at ${PYTHON} — create the venv (see README) or set AESTHETICIAN_PYTHON.`);
  try { await runCapture(['effects', '--json'], { timeoutMs: 30000 }); }
  catch (err) { problems.push(`Engine check failed: ${String(err.message).slice(0, 400)}`); }
  return { ok: problems.length === 0, problems, python: PYTHON };
});
