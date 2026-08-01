'use strict';

/* Self-update against GitHub Releases.
 *
 * electron-updater is the usual answer and it is deliberately not used here:
 * Squirrel.Mac refuses any update that is not signed with a Developer ID, and
 * this project only ad-hoc signs (see docs/packaging.md). So the flow is
 * explicit instead - read the latest release, download this platform's asset,
 * verify it against the release's SHA256SUMS.txt, swap the installed copy and
 * relaunch. Nothing downloads or installs without the user asking for it.
 *
 * A side benefit of doing it ourselves: a file this process downloads is not
 * quarantined, so the updated bundle does not hit the Gatekeeper prompt that a
 * browser-downloaded DMG does.
 */

let app = null;
try {
  ({ app } = require('electron'));
} catch (err) {
  // Only reachable under plain node, where tests/test_updater.js exercises the
  // pure helpers at the bottom of this file and never touches `app`. A real
  // Electron process always has this module, so anything other than "it is not
  // installed" is a genuine fault and must not be swallowed here.
  if (err.code !== 'MODULE_NOT_FOUND') throw err;
}

const { execFile, spawn } = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const https = require('https');
const path = require('path');

const REPO = 'heresalexandria/aesthetician';
const RELEASES_URL = `https://api.github.com/repos/${REPO}/releases/latest`;
const RELEASES_PAGE = `https://github.com/${REPO}/releases/latest`;
const CHECK_INTERVAL_MS = 24 * 60 * 60 * 1000;

// Everything we fetch has to come from GitHub over TLS. Release JSON is data
// from the network like any other, so the download URL inside it is checked
// rather than trusted.
const ALLOWED_HOSTS = [
  'api.github.com',
  'github.com',
  'objects.githubusercontent.com',
  'release-assets.githubusercontent.com',
  'codeload.github.com',
];

// Lazy: the pure helpers below are unit-tested under plain node, where the
// electron module resolves to a path string and `app` is undefined.
const userAgent = () => `Aesthetician/${app.getVersion()} (+https://github.com/${REPO})`;

function statePath() {
  return path.join(app.getPath('userData'), 'update-state.json');
}

function readState() {
  try {
    const s = JSON.parse(fs.readFileSync(statePath(), 'utf8'));
    return (s && typeof s === 'object') ? s : {};
  } catch (_) {
    return {};                     // first run, or the file got mangled
  }
}

function writeState(patch) {
  const next = { ...readState(), ...patch };
  try {
    fs.mkdirSync(path.dirname(statePath()), { recursive: true });
    fs.writeFileSync(statePath(), JSON.stringify(next, null, 2));
  } catch (_) { /* a lost timestamp only costs an extra check */ }
  return next;
}

function allowedUrl(url) {
  let u;
  try { u = new URL(url); } catch (_) { return false; }
  return u.protocol === 'https:' && ALLOWED_HOSTS.includes(u.hostname);
}

/* ── plain HTTPS with redirects ──────────────────────────────────────────
   GitHub hands asset downloads off to a storage host with a 302, and neither
   https.get nor Electron's net follows those for us.                       */
function request(url, { headers = {}, redirects = 5 } = {}) {
  return new Promise((resolve, reject) => {
    if (!allowedUrl(url)) { reject(new Error(`refusing to fetch ${url}`)); return; }
    const req = https.get(url, {
      headers: { 'User-Agent': userAgent(), ...headers },
      timeout: 30000,
    }, (res) => {
      const { statusCode, headers: h } = res;
      if (statusCode >= 300 && statusCode < 400 && h.location) {
        res.resume();
        if (redirects <= 0) { reject(new Error('too many redirects')); return; }
        const next = new URL(h.location, url).toString();
        resolve(request(next, { headers, redirects: redirects - 1 }));
        return;
      }
      if (statusCode !== 200) {
        res.resume();
        reject(new Error(`HTTP ${statusCode} from ${new URL(url).hostname}`));
        return;
      }
      resolve(res);
    });
    req.on('timeout', () => { req.destroy(new Error('timed out')); });
    req.on('error', reject);
  });
}

async function getText(url, headers) {
  const res = await request(url, { headers });
  const chunks = [];
  let bytes = 0;
  for await (const chunk of res) {
    bytes += chunk.length;
    if (bytes > 8 * 1024 * 1024) throw new Error('response too large');
    chunks.push(chunk);
  }
  return Buffer.concat(chunks).toString('utf8');
}

/* ── versions ────────────────────────────────────────────────────────────
   Releases are tagged vMAJOR.MINOR.PATCH. Anything with a prerelease suffix is
   ignored: /releases/latest already skips drafts and prereleases, and this is
   the belt to that suspenders.                                              */
function parseVersion(raw) {
  const m = /^v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$/.exec(String(raw || '').trim());
  return m ? [Number(m[1]), Number(m[2]), Number(m[3])] : null;
}

function isNewer(candidate, current) {
  const a = parseVersion(candidate);
  const b = parseVersion(current);
  if (!a || !b) return false;
  for (let i = 0; i < 3; i++) {
    if (a[i] !== b[i]) return a[i] > b[i];
  }
  return false;
}

/* ── platform asset ──────────────────────────────────────────────────────
   macOS updates from the .zip rather than the .dmg: it is the same bundle
   without a disk image to mount, and `ditto` restores the symlinks and the
   signature that a plain unzip would flatten. Windows re-runs the installer. */
function assetFor(assets, platform = process.platform, arch = process.arch) {
  const list = (Array.isArray(assets) ? assets : []).filter((a) => a && typeof a.name === 'string');
  if (platform === 'darwin') {
    // Aesthetician-0.6.0-mac-arm64.zip
    return list.find((a) => a.name.endsWith(`-mac-${arch}.zip`)) || null;
  }
  if (platform === 'win32') {
    // Aesthetician-0.6.0-win-x64-setup.exe
    return list.find((a) => /win-x64-setup\.exe$/i.test(a.name)) || null;
  }
  return null;
}

function platformNote() {
  if (process.platform === 'darwin' || process.platform === 'win32') return '';
  return `There is no packaged build for ${process.platform} yet - update from source instead.`;
}

/* ── check ───────────────────────────────────────────────────────────────  */
let lastResult = null;

async function check({ force = false } = {}) {
  const state = readState();
  const current = app.getVersion();
  const stale = !state.lastCheckAt || (Date.now() - state.lastCheckAt) >= CHECK_INTERVAL_MS;
  if (!force && !stale && lastResult) return lastResult;

  let release;
  try {
    release = JSON.parse(await getText(RELEASES_URL, {
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
    }));
  } catch (err) {
    // A failed check is not an error state worth shouting about; the button
    // simply does not appear.
    const result = {
      ok: false,
      current,
      error: String(err.message || err),
      checkedAt: Date.now(),
      available: false,
      releasesUrl: RELEASES_PAGE,
    };
    writeState({ lastCheckAt: result.checkedAt, lastError: result.error });
    lastResult = result;
    return result;
  }

  const latest = String(release.tag_name || '').replace(/^v/, '');
  const asset = assetFor(release.assets);
  const available = isNewer(latest, current);
  const result = {
    ok: true,
    current,
    latest,
    available,
    // Release notes are text off the network: the renderer prints them with
    // textContent, never as markup.
    notes: String(release.body || '').slice(0, 20000),
    name: String(release.name || ''),
    publishedAt: release.published_at || null,
    htmlUrl: typeof release.html_url === 'string' && allowedUrl(release.html_url)
      ? release.html_url : RELEASES_PAGE,
    releasesUrl: RELEASES_PAGE,
    asset: asset ? { name: asset.name, url: asset.browser_download_url, size: asset.size } : null,
    // Whether this build can actually replace itself, as opposed to merely
    // noticing that it is out of date.
    installable: Boolean(asset) && app.isPackaged,
    note: !app.isPackaged
      ? 'Running from a dev checkout - `git pull` instead of updating in place.'
      : (asset ? '' : (platformNote() || `That release has no ${process.platform}/${process.arch} build attached.`)),
    checkedAt: Date.now(),
  };
  writeState({ lastCheckAt: result.checkedAt, latestSeen: latest, lastError: null });
  lastResult = result;
  return result;
}

function info() {
  const state = readState();
  // The smoke test and the screenshot harness boot the whole renderer; neither
  // should be reaching out to GitHub to do it.
  const headless = process.argv.includes('--smoke') || process.argv.includes('--shot');
  const stale = !state.lastCheckAt || (Date.now() - state.lastCheckAt) >= CHECK_INTERVAL_MS;
  return {
    version: app.getVersion(),
    packaged: app.isPackaged,
    platform: process.platform,
    arch: process.arch,
    repoUrl: `https://github.com/${REPO}`,
    releasesUrl: RELEASES_PAGE,
    lastCheckAt: state.lastCheckAt || null,
    checkIntervalMs: CHECK_INTERVAL_MS,
    stale: stale && !headless,
    last: lastResult,
  };
}

/* ── download ────────────────────────────────────────────────────────────  */
function downloadDir() {
  return path.join(app.getPath('temp'), 'aesthetician-update');
}

let inFlight = null;    // the live response stream, so a cancel has something to kill
let downloading = false; // set before the first await: two clicks must not both run

async function fetchChecksum(release, assetName) {
  const sums = (release.assets || []).find((a) => a.name === 'SHA256SUMS.txt');
  if (!sums) return null;
  const text = await getText(sums.browser_download_url);
  for (const line of text.split('\n')) {
    const m = /^([0-9a-f]{64})\s+\*?(.+?)\s*$/i.exec(line.trim());
    if (m && path.basename(m[2]) === assetName) return m[1].toLowerCase();
  }
  return null;
}

async function download(sender) {
  if (downloading) throw new Error('an update is already downloading');
  downloading = true;
  try {
    return await runDownload(sender);
  } finally {
    downloading = false;
    inFlight = null;
  }
}

async function runDownload(sender) {
  const result = lastResult && lastResult.ok ? lastResult : await check({ force: true });
  if (!result.ok) throw new Error(result.error || 'could not reach GitHub');
  if (!result.available) throw new Error('already up to date');
  if (!result.asset) throw new Error(result.note || 'no build for this platform');
  if (!app.isPackaged) throw new Error('running from a dev checkout - use git pull');

  // Fetch the release again purely for its checksum list: the cached result
  // does not carry it, and it is small.
  let expected = null;
  try {
    const release = JSON.parse(await getText(RELEASES_URL, { Accept: 'application/vnd.github+json' }));
    expected = await fetchChecksum(release, result.asset.name);
  } catch (_) { /* fall through: verified below only if we got a digest */ }

  const dir = downloadDir();
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  const dest = path.join(dir, result.asset.name);

  const emit = (msg) => {
    if (sender && !sender.isDestroyed()) sender.send('aesth:update-progress', msg);
  };
  emit({ stage: 'download', received: 0, total: result.asset.size || 0, frac: 0 });

  const res = await request(result.asset.url);
  inFlight = res;
  const total = Number(res.headers['content-length']) || result.asset.size || 0;
  const hash = crypto.createHash('sha256');
  let received = 0;
  let lastEmit = 0;

  try {
    await new Promise((resolve, reject) => {
      const out = fs.createWriteStream(dest);
      res.on('data', (chunk) => {
        received += chunk.length;
        hash.update(chunk);
        const now = Date.now();
        if (now - lastEmit > 200) {
          lastEmit = now;
          emit({ stage: 'download', received, total, frac: total ? received / total : 0 });
        }
      });
      res.on('error', reject);
      out.on('error', reject);
      out.on('finish', resolve);
      res.pipe(out);
    });
  } finally {
    inFlight = null;
  }

  const digest = hash.digest('hex');
  if (expected && digest !== expected) {
    fs.rmSync(dir, { recursive: true, force: true });
    throw new Error('checksum mismatch - the download was corrupt or tampered with');
  }
  emit({ stage: 'download', received, total, frac: 1, verified: Boolean(expected) });

  const state = writeState({
    staged: { version: result.latest, file: dest, sha256: digest, verified: Boolean(expected) },
  });
  return state.staged;
}

function cancelDownload() {
  if (!inFlight) return false;
  try { inFlight.destroy(new Error('canceled')); } catch (_) { /* already gone */ }
  inFlight = null;
  fs.rmSync(downloadDir(), { recursive: true, force: true });
  writeState({ staged: null });
  return true;
}

/* ── install ─────────────────────────────────────────────────────────────  */
function installedBundle() {
  // /Applications/Aesthetician.app/Contents/MacOS/Aesthetician -> the .app
  return path.resolve(process.execPath, '..', '..', '..');
}

function run(cmd, args) {
  return new Promise((resolve, reject) => {
    execFile(cmd, args, { maxBuffer: 8 << 20 }, (err, stdout, stderr) => {
      if (err) reject(new Error(`${cmd} failed: ${String(stderr || err.message).slice(-400)}`));
      else resolve(stdout);
    });
  });
}

async function installMac(staged) {
  const bundle = installedBundle();
  if (!bundle.endsWith('.app')) {
    throw new Error(`cannot locate the installed app (got ${bundle})`);
  }
  // Fail before quitting, not after: an app that exits and then cannot write to
  // /Applications leaves the user staring at nothing.
  try {
    fs.accessSync(path.dirname(bundle), fs.constants.W_OK);
  } catch (_) {
    throw new Error(`no permission to write ${path.dirname(bundle)} - `
      + 'move Aesthetician somewhere you own, or install the download by hand');
  }

  const stage = path.join(downloadDir(), 'unpacked');
  fs.rmSync(stage, { recursive: true, force: true });
  fs.mkdirSync(stage, { recursive: true });
  // ditto, not unzip: an .app is full of symlinks and carries a code signature,
  // and unzip flattens both.
  await run('/usr/bin/ditto', ['-x', '-k', staged.file, stage]);

  const fresh = fs.readdirSync(stage).find((f) => f.endsWith('.app'));
  if (!fresh) throw new Error('the downloaded archive contained no .app');
  const freshPath = path.join(stage, fresh);
  const plist = path.join(freshPath, 'Contents', 'Info.plist');
  if (!fs.existsSync(plist)) throw new Error('the downloaded app looks incomplete');

  /* The swap cannot happen from inside the app being swapped, so it is handed
     to a detached script that waits for this process to exit first. It moves
     the old bundle aside rather than deleting it, and puts it back if the copy
     fails, so a bad update is not a lost install. */
  const script = path.join(downloadDir(), 'swap.sh');
  fs.writeFileSync(script, `#!/bin/sh
set -u
pid="$1"; fresh="$2"; dest="$3"
for _ in $(seq 1 150); do
  kill -0 "$pid" 2>/dev/null || break
  sleep 0.2
done
rm -rf "$dest.old"
mv "$dest" "$dest.old" || exit 1
if ! /usr/bin/ditto "$fresh" "$dest"; then
  rm -rf "$dest"
  mv "$dest.old" "$dest"
  exit 1
fi
rm -rf "$dest.old"
xattr -dr com.apple.quarantine "$dest" 2>/dev/null
open "$dest"
`, { mode: 0o755 });

  const child = spawn('/bin/sh', [script, String(process.pid), freshPath, bundle], {
    detached: true,
    stdio: 'ignore',
  });
  child.unref();
  return { restarting: true };
}

async function installWindows(staged) {
  // The NSIS installer cannot overwrite files this process holds open, so it is
  // launched detached and the app steps out of its way. It is deliberately not
  // silent: an unsigned installer that runs invisibly is worse, not better.
  const child = spawn(staged.file, [], { detached: true, stdio: 'ignore' });
  child.unref();
  return { restarting: false };
}

async function install() {
  const staged = readState().staged;
  if (!staged || !staged.file || !fs.existsSync(staged.file)) {
    throw new Error('nothing downloaded to install');
  }
  if (!app.isPackaged) throw new Error('running from a dev checkout - use git pull');

  const res = process.platform === 'darwin'
    ? await installMac(staged)
    : process.platform === 'win32'
      ? await installWindows(staged)
      : (() => { throw new Error(platformNote() || 'unsupported platform'); })();

  writeState({ staged: null, lastCheckAt: 0 });
  // Give the detached helper a moment to be scheduled before the process that
  // spawned it disappears.
  setTimeout(() => app.exit(0), 400);
  return res;
}

/* Where the download landed, for the "install it yourself" escape hatch. */
function stagedFile() {
  const staged = readState().staged;
  return staged && staged.file && fs.existsSync(staged.file) ? staged.file : null;
}

module.exports = {
  check,
  info,
  download,
  cancelDownload,
  install,
  stagedFile,
  // Pure helpers, exercised by tests/test_updater.js under plain node.
  isNewer,
  parseVersion,
  assetFor,
  allowedUrl,
  CHECK_INTERVAL_MS,
};
