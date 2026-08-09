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

/* ── the version picker ───────────────────────────────────────────────
   The list the picker offers is built here, so what it hides is as much a
   decision as what it shows. */
const LIST = [
  {
    tag_name: 'v0.13.1',
    name: 'Aesthetician 0.13.1',
    body: 'the newest one',
    published_at: '2026-07-02T10:00:00Z',
    html_url: 'https://github.com/heresalexandria/aesthetician/releases/tag/v0.13.1',
    assets: [
      { name: 'Aesthetician-0.13.1-mac-arm64.zip', size: 120, browser_download_url: 'https://github.com/x' },
      { name: 'Aesthetician-0.13.1-win-x64-setup.exe', size: 130, browser_download_url: 'https://github.com/y' },
    ],
  },
  // Out of order on purpose: GitHub sorts by creation date, and a re-cut tag
  // can land after a newer one.
  { tag_name: 'v0.9.0', published_at: '2026-01-02T10:00:00Z', assets: [] },
  {
    tag_name: 'v0.10.0',
    published_at: '2026-02-02T10:00:00Z',
    assets: [{ name: 'Aesthetician-0.10.0-mac-arm64.zip', size: 100, browser_download_url: 'https://github.com/z' }],
  },
  { tag_name: 'v0.13.2', draft: true, assets: [] },
  { tag_name: 'nightly', assets: [] },
];

function test_release_list_shape() {
  const list = u.summarizeReleases(LIST, { current: '0.10.0', platform: 'darwin', arch: 'arm64' });

  // Newest first, whatever order the API returned them in. Drafts and tags we
  // cannot compare against the running version never reach the dropdown.
  assert.deepStrictEqual(list.map((r) => r.tag), ['v0.13.1', 'v0.10.0', 'v0.9.0']);
  assert.deepStrictEqual(list.map((r) => r.direction), ['newer', 'current', 'older']);
  assert.strictEqual(list[0].version, '0.13.1');
  assert.strictEqual(list[0].notes, 'the newest one');

  // Each entry carries this machine's asset and no download URL: the renderer
  // asks for a tag, and the main process looks the URL up again itself.
  assert.deepStrictEqual(list[0].asset, { name: 'Aesthetician-0.13.1-mac-arm64.zip', size: 120 });
  assert.strictEqual(list[2].asset, null, 'a release with no build must say so, not vanish');
  assert.ok(!('url' in list[0].asset));

  const win = u.summarizeReleases(LIST, { current: '0.10.0', platform: 'win32', arch: 'x64' });
  assert.strictEqual(win[0].asset.name, 'Aesthetician-0.13.1-win-x64-setup.exe');
  assert.strictEqual(win[1].asset, null, 'the macOS zip is not a Windows build');
}

function test_release_list_is_not_trusted() {
  const nasty = [
    {
      tag_name: 'v1.0.0',
      html_url: 'javascript:alert(1)',
      body: 'x'.repeat(9000),
      published_at: '2026-03-02T10:00:00Z',
      assets: [{ name: 'Aesthetician-1.0.0-mac-arm64.zip', size: 1 }],
    },
  ];
  const [rel] = u.summarizeReleases(nasty, { current: '0.10.0', platform: 'darwin', arch: 'arm64' });
  assert.ok(rel.htmlUrl.startsWith('https://github.com/heresalexandria/aesthetician'),
    `a bad html_url must fall back to the releases page, got ${rel.htmlUrl}`);
  assert.ok(rel.notes.length <= 4000, 'release notes are capped before they cross to the renderer');
  assert.ok(rel.notes.endsWith('…'), 'a capped note says it was cut rather than stopping dead');

  // Nothing about a malformed payload is allowed to throw: the picker has to
  // open even when GitHub answers with something unexpected.
  for (const junk of [null, undefined, {}, 'nope', [null, {}, { tag_name: 5 }]]) {
    assert.deepStrictEqual(u.summarizeReleases(junk, { current: '0.1.0' }), []);
  }
}

function test_release_list_limit() {
  const many = Array.from({ length: 40 }, (_, i) => ({ tag_name: `v0.${i}.0`, assets: [] }));
  assert.strictEqual(u.summarizeReleases(many, { current: '0.1.0' }).length, 30);
  assert.strictEqual(u.summarizeReleases(many, { current: '0.1.0', limit: 4 })[0].tag, 'v0.39.0',
    'the cap keeps the newest, not the first the API happened to list');
}

function test_compare_versions() {
  assert.strictEqual(u.compareVersions('0.6.0', '0.5.0'), 1);
  assert.strictEqual(u.compareVersions('0.5.0', '0.6.0'), -1);
  assert.strictEqual(u.compareVersions('v0.5.0', '0.5.0'), 0);
  assert.strictEqual(u.compareVersions('0.10.0', '0.9.0'), 1, 'numeric, not lexical');
  // Unreadable on either side means "no answer", never a silent ordering.
  assert.strictEqual(u.compareVersions('garbage', '0.5.0'), null);
  assert.strictEqual(u.compareVersions('0.5.0', ''), null);
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
  test_compare_versions,
  test_asset_selection,
  test_asset_selection_against_a_real_release,
  test_release_list_shape,
  test_release_list_is_not_trusted,
  test_release_list_limit,
  test_allowed_urls,
  test_note_image_hosts,
});

for (const [name, fn] of tests) {
  fn();
  console.log(`  ok ${name}`);
}
console.log(`${tests.length} updater tests passed`);
