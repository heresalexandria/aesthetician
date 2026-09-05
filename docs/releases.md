# Cutting a release

The intended loop is: write code, open a pull request, label it, merge it. The
release happens by itself.

```
PR labelled `minor`  ──merge──▶  version 0.5.0 → 0.6.0 in all four files
                                 commit pushed to main
                                 mac-arm64 / mac-x64 / win-x64 built in parallel
                                 tag v0.6.0 created at that commit
                                 release published, marked Latest, notes from the PR
```

Every running copy of the app notices within a day and offers to install it.

The public download page at
[heresalexandria.github.io/aesthetician](https://heresalexandria.github.io/aesthetician/)
links straight to stable release asset names. Each release publishes those
rolling aliases alongside the versioned files:

- `Aesthetician-mac-arm64.dmg`
- `Aesthetician-mac-x64.dmg`
- `Aesthetician-win-x64-setup.exe`

That keeps every download button current without rebuilding the page when the
version changes. `.github/workflows/pages.yml` publishes the static page from
`site/` after changes land on `main`.

## The label is the whole interface

One of these has to be on the pull request, and only one:

| label | 0.5.0 becomes | for |
|---|---|---|
| `major` | 1.0.0 | a breaking change |
| `minor` | 0.6.0 | a new feature |
| `patch` | 0.5.1 | a fix or a small change |
| `no-release` | unchanged | docs, chores, anything you do not want to ship |

The `release label` check on every PR fails until exactly one is there, so a
merge cannot quietly skip the decision. `scripts/release/select_bump.py` holds
the rule and both workflows call it, which is why they cannot drift apart.

## What ends up in the notes

`scripts/release/release_notes.py` builds them from the merged PR:

- the **description**, minus any `<!-- template comments -->`
- **screenshots** pulled out of the description *and* the PR's comments and
  review comments - anything already inline in the description is not repeated
- a **download table** listing the files that actually built, with sizes
- the install caveats, and a compare link to the previous tag

So a good PR description is a good changelog. Write it for whoever reads the
release page.

### Lead with the bullets

The description **must open with a flat bullet list of what changed**, one line
per user-visible change, before any heading or prose. That list is the whole
release note for most people: the app renders these notes in its own About
dialog, where there is no room to scroll through reasoning to find out what is
new.

- One bullet per change, written from the outside in - what someone can now do,
  or what stopped being broken. Not which function was touched.
- Lead the line with the change in **bold**, then the detail.
- Prefix a fix with **Fixed:** so the list separates at a glance.
- Anything a user cannot see - refactors, test scaffolding, tooling - stays out
  of the list. Put it under a later heading if it is worth saying at all.
- Then `---`, and below it as much detail, reasoning and verification as the
  reviewer needs. None of that competes with the summary.

The bullets are for whoever installs the update; everything under the rule is
for whoever reviews the diff.

## First-time setup

None of this is automatic, and the release will fail in a specific way without
each piece.

**1. Let Actions write to the repo.** Settings → Actions → General → Workflow
permissions → **Read and write permissions**. Without it the `prepare` job fails
at `git push` with a 403.

**2. Do not require a PR for main, or exempt the bot.** The release pushes the
version-bump commit straight to `main`. If a branch protection rule blocks that,
either drop the rule or add `github-actions[bot]` to its bypass list.

**3. Create the labels.** Actions → **Create release labels** → *Run workflow*.
It is safe to re-run.

**4. Publish the asset bundle.** Generated assets are gitignored, so runners
fetch the exact tag and SHA-256 recorded in
[`scripts/release/asset_bundle.json`](../scripts/release/asset_bundle.json).
PR validation, release and build-check workflows use that pin. The old
`ASSETS_RELEASE_TAG` repository variable is no longer consulted, so a stale
setting cannot silently select an earlier thumbnail catalog.

The current bundle is **assets-v5**, containing **1,000 poster thumbnails and
886 animated previews**, plus the overlay plates and 10 audio beds. It includes
the 211 added aesthetics and refreshed thumbnails for 392 older framing recipes.

Before publishing a new bundle:

```bash
.venv/bin/python scripts/make_thumbs.py
# Use --force / --only when existing recipes changed, not just for new IDs.
.venv/bin/python scripts/release/asset_bundle.py verify
python3 scripts/release/pack_assets.py
```

Upload `dist/aesthetician-assets.tar.gz` to a **new** `assets-vN` release, mark
it as a pre-release and not Latest, and update the pin with that tag and the
printed SHA-256. Keep existing bundles immutable. Include the pin change in a
`patch` PR so merging cuts a new desktop release with the complete thumbnails.
Do not bump the app version manually; the release workflow owns that.

Verify the published bytes in isolation before opening the PR:

```bash
python3 scripts/release/asset_bundle.py fetch --assets /tmp/aesthetician-assets-check
```

The destination must be empty. Fetch checks the checksum before extraction,
rejects nonportable links, and requires a poster for every registered preset
plus an animation for every picture entry. The source registry is read with
AST parsing so this runs before the build installs the Python engine. Unit
tests compare that parser against the real registry.

Missing downloads, stale manifests, missing image files and checksum mismatches
**fail the release**. There is no automatic fallback to a thumbnail-free build.
An intentional development build can still use `--no-assets`, or turn assets
off in the Build check workflow. The bundle packer follows shared asset links
and stores regular files so worktree paths never escape into the archive.

## Targets, and which of them can fail

| target | runner | blocking |
|---|---|---|
| `mac-arm64` | `macos-15` | yes |
| `mac-x64` | `macos-15-intel` | yes |
| `win-x64` | `windows-2022` | yes |

All three have built and run, so a failure in any of them is a regression worth
stopping the release for rather than a known gap to route around. This also
keeps the direct download page honest: it never points at a partial release.

## Debugging a build without cutting a release

Packaging is only otherwise exercised during a release, which is a terrible
moment to find it broken - the version has already been bumped by then. Push to
any `ci/**` branch to run the **Build check** workflow, which packages a target
and attaches the result to the run with no release involved:

```bash
git push -f origin HEAD:ci/windows
```

It defaults to `win-x64` and skips the asset packs for speed. Put `[assets]` in
the commit message to include them - worth doing at least once before merging,
because the packs are what exercise the hardlink and symlink paths in staging.
`Run workflow` from the Actions tab takes a target and an assets toggle
directly.

## If something goes wrong

The tag is created by the **publish** job, not up front, so a failed build never
leaves a tag pointing at a release that is not coming. What it does leave is a
version-bump commit on `main`. That is harmless: the next release bumps past it,
and a version with no release simply never appears to the updater.

To re-run a release for a version that failed to build, fix the build and merge
another labelled PR. To reuse the exact number, revert the bump commit first.

`workflow_dispatch` on the Release workflow cuts a release with no PR behind it -
useful for a first release, or after a manual fix. The notes are then just the
download table.

## Signing

Nothing here is signed with a Developer ID, so downloaded builds hit Gatekeeper
and SmartScreen on first launch. `docs/packaging.md` covers what that looks like
and what a real certificate would change. Updates installed from inside the app
are not affected, because the app downloads them itself rather than through a
browser.
