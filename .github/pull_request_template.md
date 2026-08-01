<!--
This description becomes the release notes, verbatim, when the PR is merged.
Write it for whoever lands on the release page - not for the reviewer.

Label the PR `major`, `minor` or `patch` to say how the version moves, or
`no-release` to merge without shipping. The `release label` check enforces it.
See docs/releases.md.
-->

## What changed

-

## Screenshots

<!--
Drag images in here. They are pulled into the release notes automatically, and
so are any images in the comments below. Delete this section if there is nothing
visual to show.
-->

## Checked

- [ ] `.venv/bin/python tests/test_engine.py`
- [ ] `node tests/test_updater.js`
- [ ] `.venv/bin/python tests/test_smoke.py`
- [ ] `.venv/bin/python scripts/validate_presets.py`
- [ ] `.venv/bin/python scripts/audit_calibration.py`
- [ ] `cd app && npx electron . --smoke`
