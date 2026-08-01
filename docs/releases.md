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

**4. Publish the asset bundle.** `assets/` is 210 MB of generated media and is
gitignored, so a runner has none of it. Build the bundle and attach it to a
release that exists only to hold it:

```bash
python3 scripts/release/pack_assets.py
```

Then create a release tagged `assets-v1` (any commit, mark it a pre-release so it
never shows as Latest) and attach `dist/aesthetician-assets.tar.gz`. Every build
downloads it from there.

Skipping this step does not break the release: the build logs a warning, passes
`--no-assets`, and ships procedural overlays with placeholder preset thumbnails
instead. It is a visibly lesser build, so do the upload.

To refresh the packs later, re-run `pack_assets.py`, attach the new tarball to a
release tagged `assets-v2`, and set the repository variable
`ASSETS_RELEASE_TAG` to `assets-v2`.

## Targets, and which of them can fail

| target | runner | blocking |
|---|---|---|
| `mac-arm64` | `macos-15` | yes |
| `mac-x64` | `macos-15-intel` | yes |
| `win-x64` | `windows-2022` | yes |

All three have built and run, so a failure in any of them is a regression worth
stopping the release for rather than a known gap to route around.

The mechanism for letting a target drop out is still there for the next
unproven one: set `optional: true` on its matrix entry in
`.github/workflows/release.yml`. The release then publishes without it, and the
download table lists only what actually built.

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
