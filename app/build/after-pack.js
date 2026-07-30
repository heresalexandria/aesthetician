'use strict';

/* electron-builder afterPack hook.
 *
 * Runs after extraResources have been copied and before the DMG/installer is
 * assembled, which is exactly when the bundle must be sealed: a code signature
 * covers Contents/Resources, so signing any earlier would be invalidated by the
 * bundled Python runtime, ffmpeg and asset packs landing afterwards.
 *
 * We have no Developer ID here, so this is an *ad-hoc* signature (`--sign -`).
 * That is enough for macOS to load the app locally — an arm64 bundle whose
 * signature is missing or stale is killed outright — but it is not enough for
 * Gatekeeper on a downloaded copy. See docs/packaging.md.
 */

const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

function chmodExec(file) {
  try { fs.chmodSync(file, 0o755); } catch (_) { /* not present on this target */ }
}

module.exports = async function afterPack(context) {
  const res = context.electronPlatformName === 'darwin'
    ? path.join(context.appOutDir,
        `${context.packager.appInfo.productFilename}.app`, 'Contents', 'Resources')
    : path.join(context.appOutDir, 'resources');

  // rsync/electron-builder normally preserve the mode; make sure regardless,
  // because a non-executable interpreter fails in a very confusing way.
  for (const rel of ['bin/ffmpeg', 'bin/ffprobe', 'pyruntime/bin/python3',
                     'pyruntime/bin/python3.12']) {
    chmodExec(path.join(res, rel));
  }

  if (context.electronPlatformName !== 'darwin') return;

  const appPath = path.join(context.appOutDir,
    `${context.packager.appInfo.productFilename}.app`);
  console.log(`  • ad-hoc signing ${path.basename(appPath)} (no Developer ID available)`);
  execFileSync('codesign', ['--force', '--deep', '--sign', '-', appPath],
    { stdio: 'inherit' });
  // Surface the result in the build log so a broken seal is obvious immediately.
  execFileSync('codesign', ['--verify', '--verbose=2', appPath], { stdio: 'inherit' });
};
