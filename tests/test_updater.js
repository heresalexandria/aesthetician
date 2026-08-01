'use strict';

/* Unit tests for the updater's decisions (run: node tests/test_updater.js).
 *
 * Only the pure half is covered here - which release counts as newer, which
 * asset belongs to this machine, which URLs we are willing to fetch. The
 * download and the on-disk swap need a real packaged app and are exercised by
 * hand; see docs/updates.md.
 *
 * This runs under plain node with no `app/node_modules` present, which is also
 * the point: requiring app/updater.js here is what proves it reaches for
 * Electron lazily rather than at load. Do not "fix" a failure by installing
 * Electron in the test job - that would hide the regression this catches. */

const assert = require('assert');
const path = require('path');

const u = require(path.join(__dirname, '..', 'app', 'updater.js'));

function test_parse_version() {
  assert.deepStrictEqual(u.parseVersion('0.5.0'), [0, 5, 0]);
  assert.deepStrictEqual(u.parseVersion('v1.2.3'), [1, 2, 3]);
  assert.deepStrictEqual(u.parseVersion(' v10.0.11 '), [10, 0, 11]);
  assert.deepStrictEqual(u.parseVersion('v1.2.3-rc1'), [1, 2, 3]);
  for (const bad of ['', null, undefined, '1.2', 'latest', 'v1.2.3.4', 'vX.Y.Z']) {
    assert.strictEqual(u.parseVersion(bad), null, `${bad} must not parse`);
  }
}

function test_is_newer() {
  assert.ok(u.isNewer('0.6.0', '0.5.0'));
  assert.ok(u.isNewer('v0.5.1', '0.5.0'));
  assert.ok(u.isNewer('1.0.0', '0.99.99'));
  assert.ok(u.isNewer('0.10.0', '0.9.0'), 'numeric, not lexical');

  assert.ok(!u.isNewer('0.5.0', '0.5.0'), 'equal is not newer');
  assert.ok(!u.isNewer('0.4.9', '0.5.0'), 'older is not newer');
  assert.ok(!u.isNewer('0.9.0', '0.10.0'), 'numeric, not lexical');
  // A tag we cannot read must never look like an upgrade.
  assert.ok(!u.isNewer('garbage', '0.5.0'));
  assert.ok(!u.isNewer('0.6.0', 'garbage'));
}

function test_asset_selection() {
  const assets = [
    { name: 'Aesthetician-0.6.0-mac-arm64.dmg' },
    { name: 'Aesthetician-0.6.0-mac-arm64.zip' },
    { name: 'Aesthetician-0.6.0-mac-x64.dmg' },
    { name: 'Aesthetician-0.6.0-mac-x64.zip' },
    { name: 'Aesthetician-0.6.0-win-x64-setup.exe' },
    { name: 'SHA256SUMS.txt' },
  ];
  // macOS updates from the zip, never the disk image.
  assert.strictEqual(u.assetFor(assets, 'darwin', 'arm64').name,
    'Aesthetician-0.6.0-mac-arm64.zip');
  assert.strictEqual(u.assetFor(assets, 'darwin', 'x64').name,
    'Aesthetician-0.6.0-mac-x64.zip');
  assert.strictEqual(u.assetFor(assets, 'win32', 'x64').name,
    'Aesthetician-0.6.0-win-x64-setup.exe');

  // No build for this machine is a normal answer, not a crash.
  assert.strictEqual(u.assetFor(assets, 'linux', 'x64'), null);
  assert.strictEqual(u.assetFor([], 'darwin', 'arm64'), null);
  assert.strictEqual(u.assetFor(null, 'darwin', 'arm64'), null);
  assert.strictEqual(u.assetFor([{}, { name: 5 }], 'darwin', 'arm64'), null);
  // An Intel machine must not be handed the Apple-silicon build.
  assert.strictEqual(
    u.assetFor([{ name: 'Aesthetician-0.6.0-mac-arm64.zip' }], 'darwin', 'x64'), null);
  // ...nor the reverse, and no platform may ever be handed another's format.
  assert.strictEqual(
    u.assetFor([{ name: 'Aesthetician-0.6.0-mac-x64.zip' }], 'darwin', 'arm64'), null);
  assert.strictEqual(
    u.assetFor([{ name: 'Aesthetician-0.6.0-win-x64-setup.exe' }], 'darwin', 'arm64'), null);
  assert.strictEqual(
    u.assetFor([{ name: 'Aesthetician-0.6.0-mac-arm64.zip' },
                { name: 'Aesthetician-0.6.0-mac-arm64.dmg' }], 'win32', 'x64'), null);

  // Windows on ARM has no build of its own and runs the x64 installer under
  // emulation - that is a decision, so pin it.
  assert.strictEqual(u.assetFor(assets, 'win32', 'arm64').name,
    'Aesthetician-0.6.0-win-x64-setup.exe');
}

function test_asset_selection_against_a_real_release() {
  // Exactly what the v0.7.1 release carries, plus the Windows installer the
  // build is about to start producing. Guards the naming contract between
  // electron-builder's artifactName and what the updater goes looking for.
  const real = [
    { name: 'Aesthetician-0.7.1-mac-arm64.dmg' },
    { name: 'Aesthetician-0.7.1-mac-arm64.zip' },
    { name: 'Aesthetician-0.7.1-mac-x64.dmg' },
    { name: 'Aesthetician-0.7.1-mac-x64.zip' },
    { name: 'Aesthetician-0.7.1-win-x64-setup.exe' },
    { name: 'SHA256SUMS.txt' },
  ];
  const picks = {
    'darwin/arm64': 'Aesthetician-0.7.1-mac-arm64.zip',
    'darwin/x64': 'Aesthetician-0.7.1-mac-x64.zip',
    'win32/x64': 'Aesthetician-0.7.1-win-x64-setup.exe',
  };
  for (const [key, want] of Object.entries(picks)) {
    const [platform, arch] = key.split('/');
    const got = u.assetFor(real, platform, arch);
    assert.ok(got, `${key} found nothing`);
    assert.strictEqual(got.name, want, `${key} picked ${got.name}`);
  }
  // The checksum file is never mistaken for a build.
  assert.strictEqual(u.assetFor([{ name: 'SHA256SUMS.txt' }], 'win32', 'x64'), null);
}

function test_note_image_hosts() {
  // Release notes carry screenshots. The main process fetches them so the
  // renderer never makes a remote request, which means this list is the whole
  // trust boundary for that fetch.
  for (const ok of [
    'https://github.com/user-attachments/assets/abc-123',
    'https://objects.githubusercontent.com/x.png',
    'https://user-images.githubusercontent.com/1/a.png',
    'https://raw.githubusercontent.com/o/r/main/a.png',
    // Where user-attachments actually 302s to - discovered the hard way, when
    // CSP blocked the real load after the unit tests were already passing.
    'https://github-production-user-asset-6210df.s3.amazonaws.com/70348962/x.png?X-Amz-Signature=a',
  ]) {
    assert.ok(u.noteImageAllowed(ok), ok);
  }
  for (const bad of [
    'http://github.com/user-attachments/assets/x',   // plaintext
    'https://github.com/heresalexandria/aesthetician',  // github, but not an attachment
    'https://github.com.evil.test/user-attachments/assets/x',
    'https://evil.s3.amazonaws.com/x.png',           // some other bucket
    'https://github-production-user-asset.evil.test/x.png',
    'https://githubusercontent.com.evil.test/x.png',
    'https://evil.test/x.png',
    'file:///etc/passwd',
    '',
    null,
  ]) {
    assert.ok(!u.noteImageAllowed(bad), `must refuse ${bad}`);
  }
}

function test_allowed_urls() {
  for (const ok of [
    'https://api.github.com/repos/heresalexandria/aesthetician/releases/latest',
    'https://github.com/heresalexandria/aesthetician/releases/download/v1.0.0/x.zip',
    'https://objects.githubusercontent.com/whatever',
  ]) {
    assert.ok(u.allowedUrl(ok), ok);
  }
  for (const bad of [
    'http://github.com/x',                      // plaintext
    'https://github.com.evil.test/x',           // lookalike host
    'https://evil.test/github.com',
    'file:///etc/passwd',
    'javascript:alert(1)',
    '',
    null,
  ]) {
    assert.ok(!u.allowedUrl(bad), `must refuse ${bad}`);
  }
}

const tests = Object.entries({
  test_parse_version,
  test_is_newer,
  test_asset_selection,
  test_asset_selection_against_a_real_release,
  test_allowed_urls,
  test_note_image_hosts,
});

for (const [name, fn] of tests) {
  fn();
  console.log(`  ok ${name}`);
}
console.log(`${tests.length} updater tests passed`);
