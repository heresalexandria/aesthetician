# How the app updates itself

The title bar carries the running version. Clicking it opens a dialog with a
**Check for updates** button; when a newer release exists, a blue outlined
**Update available** button appears next to the version and downloads and
installs it in place.

```
[ v0.5.0 ] [ ● Update available ] [ ⭳ 2 exporting ]
```

## Why not electron-updater

The obvious answer is `electron-updater`, and it does not work here.
Squirrel.Mac refuses to install an update whose bundle is not signed with an
Apple Developer ID, and this project ad-hoc signs (`docs/packaging.md`). Rather
than ship an update button that silently never works on macOS, `app/updater.js`
does the four steps by hand:

1. `GET /repos/heresalexandria/aesthetician/releases/latest`
2. pick the asset for this platform and architecture
3. download it, checking the digest against the release's `SHA256SUMS.txt`
4. swap the installed copy and relaunch

A side effect worth having: a file *this process* downloads is not quarantined,
so an in-app update never hits the Gatekeeper prompt that a browser-downloaded
DMG does.

If a Developer ID ever appears, `electron-updater` becomes the better answer and
this can go.

## What runs when

| when | what |
|---|---|
| every launch | read the version, paint the chip |
| launch, if the last check was over 24 h ago | check GitHub in the background |
| clicking the version chip | open the dialog; check on demand |
| `--smoke` / `--shot` | no check at all |

The last check time lives in `update-state.json` under the app's user-data
directory, so a restart does not mean a fresh check. A failed check is quiet -
the button just does not appear - because a background check that shouts about
being offline is a worse app.

## Installing

macOS updates from the `.zip`, not the `.dmg`: same bundle, no disk image to
mount, and `ditto` restores the symlinks and the signature that a plain unzip
would flatten. The swap cannot run from inside the app being swapped, so it is
handed to a detached shell script that waits for the process to exit, moves the
old bundle aside, copies the new one in, and reopens it. If the copy fails the
old bundle goes back. Writability of the install directory is checked *before*
the app quits, so a copy in a folder you do not own fails with a message rather
than an app that exits and never returns.

Windows re-runs the NSIS installer, visibly rather than silently, and quits so
the installer can replace files it would otherwise find locked. The installer is
per-user (`perMachine: false`), so it needs no elevation, and electron-builder's
NSIS detects a running copy and offers to close it.

**That Windows path has not been run by hand.** CI proves the installer builds
and the packaged app starts; nobody has watched an installed copy update itself
on Windows the way macOS has been watched. Treat it as the least-tested corner
of this file until someone does.

**Exports block updates.** If anything is still rendering, the update button
turns red, says `Finish exports first`, and opens the export panel. Killing
someone's half-finished render to install an update is not a trade the app gets
to make on their behalf.

## Testing a change to it

The pure decisions - version comparison, asset selection, URL allow-listing -
are unit tested and need no Electron:

```bash
node tests/test_updater.js
```

The download and the on-disk swap need a real packaged app, and are worth
exercising by hand after any change to `installMac`:

1. Build two releases, an older and a newer, and publish both.
2. Install the older one into `/Applications`.
3. Launch it, click the version chip, and take the update.
4. Confirm the app reopens on the new version and that
   `/Applications/Aesthetician.app.old` is gone.

Test the refusal path too, by putting the app somewhere unwritable: the dialog
should explain rather than quit.

## Release notes in the dialog

Notes are rendered by a small parser in the renderer, not by anything that
touches `innerHTML`. Headings become headings, screenshots become images, and
everything else stays text - so the raw `<img>` tags the notes actually contain
no longer sit in the dialog as literal markup.

The images take a detour worth knowing about. `github.com/user-attachments/...`
redirects to a signed URL on GitHub's S3 asset bucket, so allowing it in the
renderer's `img-src` would mean allowing `*.s3.amazonaws.com` - every bucket on
it. Instead the **main process fetches the bytes** and hands back a `data:` URL:
the renderer's CSP still forbids remote images entirely, which is a tighter
position than before the feature existed. The fetch checks the host, follows at
most four redirects, requires an `image/*` content type and caps the response at
8 MB.

## Trust boundary

Release JSON is data off the network, so it is treated that way. Only `https` to
`api.github.com`, `github.com` and GitHub's asset hosts is fetched, whatever URL
the payload contains. Release notes are rendered with `textContent`, never as
markup. `Open releases` is restricted to this repository's own URLs. The
download is verified against `SHA256SUMS.txt` when the release publishes one -
every release cut by `.github/workflows/release.yml` does.
