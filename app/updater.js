'use strict';

/* Self-update against GitHub Releases.
 *
 * electron-updater is the usual answer and it is deliberately not used here:
 * Squirrel.Mac refuses any update that is not signed with a Developer ID, and
 * this project only ad-hoc signs (see docs/packaging.md). So the flow is
 * explicit instead - read a release, download this platform's asset, verify it
 * against the release's SHA256SUMS.txt, swap the installed copy and relaunch.
 * Nothing downloads or installs without the user asking for it.
 *
 * Usually that release is the newest one, but any published release will do:
 * the picker in the About dialog lists them all so a specific version can be
 * put back on, and the install path does not care which direction it moves.
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
const RELEASE_LIST_URL = `https://api.github.com/repos/${REPO}/releases?per_page=30`;
const RELEASES_PAGE = `https://github.com/${REPO}/releases/latest`;
const CHECK_INTERVAL_MS = 24 * 60 * 60 * 1000;

// How many releases the version picker offers, and how long the list is good
// for. Unauthenticated GitHub allows 60 API calls an hour per address, so
// opening the picker twice in a row must not cost two of them.
const MAX_RELEASES = 30;
const RELEASE_LIST_TTL_MS = 10 * 60 * 1000;
const MAX_NOTES = 4000;

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

/* -1, 0 or 1, and null when either side is not a version we can read. A
   prerelease suffix does not order: v1.2.3-rc1 and v1.2.3 compare equal, which
   is fine for labelling a list and is why the update check ignores prereleases
   rather than trying to rank them. */
function compareVersions(a, b) {
  const x = parseVersion(a);
  const y = parseVersion(b);
  if (!x || !y) return null;
  for (let i = 0; i < 3; i++) {
    if (x[i] !== y[i]) return x[i] > y[i] ? 1 : -1;
  }
  return 0;
}

function isNewer(candidate, current) {
  return compareVersions(candidate, current) === 1;
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
    // Aesthetician-0.6.0-win-x64-setup.exe. There is no arm64 Windows build;
    // Windows on ARM runs the x64 installer under emulation, so handing it over
    // is deliberate rather than an accident of loose matching.
    return list.find((a) => /-win-x64-setup\.exe$/i.test(a.name)) || null;
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
    // The tag as GitHub spells it, so a staged download can be matched against
    // the version picker's list without guessing the `v`.
    tag: String(release.tag_name || ''),
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

/* ── every release, not just the newest ──────────────────────────────────
   Going backwards is a normal thing to want: to find out which release a bug
   arrived in, or to get off one that broke something while it is being fixed.
   So the whole list is offered rather than only the tip, and installing from it
   is the same download-verify-swap the update path already does.

   Nothing here trusts the payload any further than `check` does. Tags are
   matched against the list GitHub returned rather than pasted into a URL, so a
   tag coming from the renderer never decides what gets fetched.               */
let releaseList = null;      // { at, raw } - so opening the picker twice is one request

async function fetchReleaseList(force = false) {
  if (!force && releaseList && (Date.now() - releaseList.at) < RELEASE_LIST_TTL_MS) {
    return releaseList.raw;
  }
  const raw = JSON.parse(await getText(RELEASE_LIST_URL, {
    Accept: 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
  }));
  releaseList = { at: Date.now(), raw: Array.isArray(raw) ? raw : [] };
  return releaseList.raw;
}

function truncateNotes(body) {
  return body.length <= MAX_NOTES ? body : `${body.slice(0, MAX_NOTES - 2).trimEnd()} …`;
}

/* Release JSON as the picker needs it: newest first, one entry per published
   release, each carrying this machine's asset if the release has one. Drafts
   and tags we cannot parse are dropped - an unreadable tag cannot be compared
   against the running version, and every release this project cuts is vX.Y.Z. */
function summarizeReleases(raw, {
  current = '',
  platform = process.platform,
  arch = process.arch,
  limit = MAX_RELEASES,
} = {}) {
  const out = (Array.isArray(raw) ? raw : [])
    .filter((r) => r && !r.draft && parseVersion(r.tag_name))
    .map((r) => {
      const asset = assetFor(r.assets, platform, arch);
      const version = String(r.tag_name).replace(/^v/, '');
      const rel = compareVersions(version, current);
      return {
        tag: String(r.tag_name),
        version,
        name: String(r.name || ''),
        publishedAt: r.published_at || null,
        prerelease: Boolean(r.prerelease),
        htmlUrl: typeof r.html_url === 'string' && allowedUrl(r.html_url)
          ? r.html_url : RELEASES_PAGE,
        // Text off the network; the renderer prints it with textContent. Thirty
        // sets of release notes cross at once, so each one is capped - and says
        // when it has been.
        notes: truncateNotes(String(r.body || '')),
        // No download URL: the renderer names a tag and the main process looks
        // the asset up again, so a URL never makes the round trip.
        asset: asset ? { name: asset.name, size: asset.size || 0 } : null,
        direction: rel === null ? 'unknown'
          : rel > 0 ? 'newer' : rel < 0 ? 'older' : 'current',
      };
    });
  out.sort((a, b) => compareVersions(b.version, a.version) || 0);
  return out.slice(0, limit);
}

async function releases({ force = false } = {}) {
  const current = app.getVersion();
  try {
    const raw = await fetchReleaseList(force);
    return {
      ok: true,
      current,
      packaged: app.isPackaged,
      platform: process.platform,
      arch: process.arch,
      releasesUrl: RELEASES_PAGE,
      note: app.isPackaged
        ? platformNote()
        : 'Running from a dev checkout - check out the tag you want instead.',
      releases: summarizeReleases(raw, { current }),
    };
  } catch (err) {
    return {
      ok: false,
      current,
      error: String(err.message || err),
      releases: [],
      releasesUrl: RELEASES_PAGE,
    };
  }
}

async function releaseByTag(tag) {
  const want = String(tag || '').trim();
  if (!want) return null;
  const find = (raw) => raw.find((r) => r && !r.draft && r.tag_name === want) || null;
  const hit = find(await fetchReleaseList(false));
  // A tag the cached list does not know about is worth one refetch: the list
  // may simply predate the release.
  return hit || find(await fetchReleaseList(true));
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

async function download(sender, opts = {}) {
  if (downloading) throw new Error('an update is already downloading');
  downloading = true;
  try {
    return await runDownload(sender, opts || {});
  } finally {
    downloading = false;
    inFlight = null;
  }
}

/* Which release the bytes are coming from. A tag means the user picked a
   version out of the list; without one this is the ordinary "take the latest"
   path, and the two only differ in how the asset is found. */
async function resolveTarget(tag) {
  if (!app.isPackaged) throw new Error('running from a dev checkout - use git pull');
  if (!tag) {
    const result = lastResult && lastResult.ok ? lastResult : await check({ force: true });
    if (!result.ok) throw new Error(result.error || 'could not reach GitHub');
    if (!result.available) throw new Error('already up to date');
    if (!result.asset) throw new Error(result.note || 'no build for this platform');
    return {
      tag: result.tag || `v${result.latest}`,
      version: result.latest,
      asset: result.asset,
      release: null,
    };
  }
  const release = await releaseByTag(tag);
  if (!release) throw new Error(`no release tagged ${tag}`);
  const asset = assetFor(release.assets);
  if (!asset) {
    throw new Error(`${release.tag_name} has no ${process.platform}/${process.arch} build attached`);
  }
  return {
    tag: String(release.tag_name),
    version: String(release.tag_name).replace(/^v/, ''),
    asset: { name: asset.name, url: asset.browser_download_url, size: asset.size },
    release,
  };
}

async function runDownload(sender, { tag = '' } = {}) {
  const target = await resolveTarget(String(tag || '').trim());

  // The checksum list hangs off the release. A picked release is already in
  // hand; the latest has to be fetched again, because the cached check result
  // does not carry it and it is small.
  let expected = null;
  try {
    const release = target.release
      || JSON.parse(await getText(RELEASES_URL, { Accept: 'application/vnd.github+json' }));
    expected = await fetchChecksum(release, target.asset.name);
  } catch (_) { /* fall through: verified below only if we got a digest */ }

  const dir = downloadDir();
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  const dest = path.join(dir, target.asset.name);

  const emit = (msg) => {
    if (sender && !sender.isDestroyed()) sender.send('aesth:update-progress', msg);
  };
  emit({ stage: 'download', received: 0, total: target.asset.size || 0, frac: 0 });

  const res = await request(target.asset.url);
  inFlight = res;
  const total = Number(res.headers['content-length']) || target.asset.size || 0;
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

  writeState({
    staged: {
      version: target.version,
      tag: target.tag,
      file: dest,
      sha256: digest,
      verified: Boolean(expected),
    },
  });
  // The renderer gets what it needs to say which version is waiting, and not
  // the path it is waiting at.
  return { version: target.version, tag: target.tag, verified: Boolean(expected) };
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

/* ── release-note images ─────────────────────────────────────────────
   Screenshots in release notes are served from github.com/user-attachments,
   which 302s to a signed URL on GitHub's S3 asset bucket. Rather than widen the
   renderer's CSP to cover that (and every other bucket on s3.amazonaws.com with
   it), the main process fetches the bytes and hands back a data: URL. The
   renderer then makes no network requests of its own at all, which is a tighter
   position than it was in before any of this. */
const NOTE_IMAGE_HOSTS = [
  'github.com',
  'objects.githubusercontent.com',
  'raw.githubusercontent.com',
  'user-images.githubusercontent.com',
];
const MAX_NOTE_IMAGE = 8 * 1024 * 1024;

function noteImageAllowed(url) {
  let u;
  try { u = new URL(url); } catch (_) { return false; }
  if (u.protocol !== 'https:') return false;
  if (u.hostname === 'github.com') return u.pathname.startsWith('/user-attachments/');
  if (NOTE_IMAGE_HOSTS.includes(u.hostname)) return true;
  if (u.hostname.endsWith('.githubusercontent.com')) return true;
  // Where user-attachments actually redirects to.
  return /^github-production-user-asset-[a-z0-9]+\.s3\.amazonaws\.com$/.test(u.hostname);
}

function getImage(url, redirects = 4) {
  return new Promise((resolve, reject) => {
    if (!noteImageAllowed(url)) { reject(new Error('refused host')); return; }
    const req = https.get(url, { headers: { 'User-Agent': userAgent() }, timeout: 20000 }, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        res.resume();
        if (redirects <= 0) { reject(new Error('too many redirects')); return; }
        resolve(getImage(new URL(res.headers.location, url).toString(), redirects - 1));
        return;
      }
      if (res.statusCode !== 200) { res.resume(); reject(new Error(`HTTP ${res.statusCode}`)); return; }
      const type = String(res.headers['content-type'] || '').split(';')[0].trim();
      if (!/^image\/(png|jpeg|gif|webp)$/.test(type)) {
        res.resume();
        reject(new Error(`not an image (${type})`));
        return;
      }
      const chunks = [];
      let bytes = 0;
      res.on('data', (c) => {
        bytes += c.length;
        if (bytes > MAX_NOTE_IMAGE) { req.destroy(new Error('image too large')); return; }
        chunks.push(c);
      });
      res.on('error', reject);
      res.on('end', () => resolve(`data:${type};base64,${Buffer.concat(chunks).toString('base64')}`));
    });
    req.on('timeout', () => req.destroy(new Error('timed out')));
    req.on('error', reject);
  });
}

async function noteImage(url) {
  try {
    return await getImage(String(url || ''));
  } catch (_) {
    return null;      // a screenshot that will not load is not worth an error
  }
}

/* Where the download landed, for the "install it yourself" escape hatch. */
function stagedFile() {
  const staged = readState().staged;
  return staged && staged.file && fs.existsSync(staged.file) ? staged.file : null;
}

module.exports = {
  check,
  info,
  releases,
  download,
  cancelDownload,
  install,
  stagedFile,
  noteImage,
  noteImageAllowed,
  // Pure helpers, exercised by tests/test_updater.js under plain node.
  isNewer,
  compareVersions,
  parseVersion,
  assetFor,
  allowedUrl,
  summarizeReleases,
  CHECK_INTERVAL_MS,
};
