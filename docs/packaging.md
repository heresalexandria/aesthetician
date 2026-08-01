# Packaging Aesthetician as a desktop app

Aesthetician is an Electron shell driving a Python engine that drives ffmpeg. A
packaged build has to carry all three, so that someone with no Python, no
Homebrew and no ffmpeg can mount a disk image, drag the app across, and work.

## Build it

```bash
python3 scripts/package/build.py --target mac
```

```bash
python3 scripts/package/build.py --target win
```

Prerequisites: Python 3 on the build machine, `npm install` already run in
`app/`, and network access for the first build (it downloads a Python runtime and
ffmpeg). `rsync` is used for staging when it is there and a slower Python copy
when it is not, so Windows runners work too. Artifacts land in `app/dist/`.

The macOS build produces both a `.dmg` and a `.zip` of the same bundle. The DMG
is for people; the zip is what the in-app updater downloads, because it can be
unpacked with `ditto` and swapped into place without mounting anything. See
[updates.md](updates.md).

CI builds all three targets on merge, from `.github/workflows/release.yml` - see
[releases.md](releases.md). Everything below still applies to a build by hand.

Useful flags:

| flag | effect |
|---|---|
| `--clean` | discard the download/runtime cache and rebuild from scratch |
| `--stage-only` | build `app/build-resources/` but do not run electron-builder |
| `--dir-only` | produce the unpacked `.app` / directory but skip the DMG/installer |
| `--force-runtime`, `--force-ffmpeg` | rebuild or re-fetch just that piece |
| `--no-assets` | skip the asset packs (much smaller; effects fall back to procedural) |
| `--target mac-both` | build both Apple-silicon and Intel |

Targets: `mac` (= `mac-arm64`), `mac-x64`, `mac-both`, `win` (= `win-x64`).

## What ends up inside

The build stages a payload into `app/build-resources/`, which electron-builder
copies to `Contents/Resources` (macOS) or `resources/` (Windows). `app/main.js`
resolves everything against that directory when `app.isPackaged` is true, and
against the repo `.venv` plus your PATH otherwise - so the same code runs in dev
and in the bundle.

```
Resources/
  pyruntime/     relocatable CPython + aesthetician + numpy/scipy/OpenCV/click/rich/requests
  bin/           ffmpeg, ffprobe (static)
  assets/        packs/, thumbs/, audio-beds/
  app.asar       the Electron front end
```

The engine is told where to look through three environment variables the main
process sets on every child: `AESTHETICIAN_ASSETS`, `AESTHETICIAN_FFMPEG` and
`AESTHETICIAN_FFPROBE`. All three also work in a dev checkout, which is handy for
testing a bundle by hand.

### Why a standalone CPython and not the venv

A virtualenv bakes an absolute path to the interpreter that created it, so
copying `.venv` into an app produces something that only runs on the machine that
built it. Instead the build downloads an
[astral-sh/python-build-standalone](https://github.com/astral-sh/python-build-standalone)
`install_only` archive - a genuinely relocatable CPython - and pip-installs the
project and its dependencies into it. Because real `.py` files sit on a real
filesystem, the engine's `pkgutil`-based effect and preset discovery keeps working
(a frozen single-file build would break it).

Size is then cut back hard: test suites, headers, static libraries, `.pyi`/`.pyx`
stubs, `__pycache__` and unused stdlib corners are pruned. The result for
macOS arm64 is roughly **960 MB installed / 495 MB compressed**, most of it
NumPy, SciPy and OpenCV.

### Pinned versions

Everything upstream is pinned in one place, `scripts/package/targets.py`:
`PY_VERSION` / `PBS_RELEASE` for the interpreter, `FFMPEG_MAC_URL` and
`FFMPEG_WIN_TAG` / `FFMPEG_WIN_URL` for ffmpeg, and `DEPS` for the Python
dependencies (keep that in step with `[project.dependencies]` in
`pyproject.toml`). After bumping a pin, rebuild with `--force-runtime` or
`--force-ffmpeg` and re-run the verification below.

## ffmpeg licensing - read before redistributing

The bundled ffmpeg builds are **GPLv3** (configured `--enable-gpl
--enable-version3`; no `--enable-nonfree`, so redistribution is permitted). If
you ship this app to anyone else, the GPL obligations travel with it: convey the
licence text and make the corresponding ffmpeg source available. Aesthetician's
own code is MIT, and dynamic use of a separate ffmpeg binary is a different
situation from bundling one - bundling is what triggers this. If you would rather
not take that on, build with an LGPL ffmpeg instead and expect to lose some
encoders (several era codec presets depend on GPL-only ones).

## macOS signing and first run

There is no Developer ID in this project, so `app/build/after-pack.js`
**ad-hoc signs** the bundle (`codesign --force --deep --sign -`) and then verifies
the seal. That step has to happen after packing, because a signature covers
`Contents/Resources` and the Python runtime, ffmpeg and assets are copied in
during packing - signing earlier would immediately be invalidated. An arm64
bundle with a missing or stale signature is killed outright by macOS, so this is
not optional.

An ad-hoc signature is enough to run the app locally. It is **not** enough for
Gatekeeper once the DMG has been downloaded or copied between machines, which
shows up as *"Aesthetician is damaged and can't be opened"* or a plain refusal.
On first open, either:

- right-click (or Control-click) the app → **Open** → **Open** again, or
- clear the quarantine flag:

```bash
xattr -dr com.apple.quarantine /Applications/Aesthetician.app
```

For real distribution you need an Apple Developer ID Application certificate plus
notarization: set `identity` in the `mac` block of `app/package.json` (it is
currently `null` so electron-builder does not go hunting for a certificate) and
add notarization credentials. Hardened-runtime entitlements are already present
in `app/build/entitlements.mac.plist`.

This is also the reason the app updates itself by hand rather than through
`electron-updater`: Squirrel.Mac refuses an unsigned update outright. A Developer
ID would make `electron-updater` the better answer and let `app/updater.js` go.

Windows builds are unsigned. Users will see a SmartScreen warning; an
Authenticode certificate is the fix.

## Verifying a build

The bar the macOS build was held to, and worth repeating after any change:

```bash
R="app/dist/mac-arm64/Aesthetician.app/Contents/Resources"

# 1. the bundled interpreter, with NOTHING inherited from your shell
env -i HOME=/tmp PATH=/usr/bin:/bin \
  AESTHETICIAN_ASSETS="$PWD/$R/assets" \
  AESTHETICIAN_FFMPEG="$PWD/$R/bin/ffmpeg" \
  AESTHETICIAN_FFPROBE="$PWD/$R/bin/ffprobe" \
  "$PWD/$R/pyruntime/bin/python3" -c \
  "from aesthetician.engine.graph import all_effects; \
   from aesthetician.engine.presets import all_presets; \
   print(len(all_effects()), 'effects', len(all_presets()), 'presets')"
# expect: 103 effects 192 presets

# 2. a real render, from a COPY of the app, to prove relocatability
cp -R app/dist/mac-arm64/Aesthetician.app /tmp/AesthRelo/
```

Then render through the copy with the same scrubbed environment. Cover three
cases, because they exercise different paths:

- `super8-1974` - grain, overlay plates, audio chain
- `vcd-1997` - a real-codec file pass, i.e. it must shell out to bundled ffmpeg
- `audio-8track-1974` - the audio device library

Probe each result with the **bundled** `ffprobe` and confirm duration plus video
and audio streams. Finally `open -a` the copied app and confirm the window comes
up and the preset list populates; catching
`Resources/pyruntime/bin/python3 -m aesthetician.cli` in `pgrep` proves the GUI
really is reaching its own engine rather than a stray system Python.

## Known limitations

- **The Windows target is scripted but has never been built or run.** It is
  correct by construction - pinned `x86_64-pc-windows-msvc` runtime, `win_amd64`
  wheels, NSIS installer, `python.exe` and `.exe` suffixes handled in
  `targets.py` - but treat it as unverified until someone builds it on Windows.
- Cross-building macOS Intel from Apple silicon installs x86_64 wheels but cannot
  execute them during the build, so `mac-x64` is likewise unverified here.
- The app is large, and almost all of it is scientific Python. `--no-assets`
  trims the overlay packs and audio beds if you need a smaller build.
- The app icons (`app/build/icon.png` for the .icns/.ico conversion,
  `app/renderer/icon.png` for the in-app mark) are generated by
  `scripts/package/make_icon.py` from the `icon.png` artwork at the repo root:
  it cuts the artwork's white page away so the corners are truly transparent,
  and insets the Dock icon to the macOS icon grid. Regenerate there rather
  than editing the PNGs.
