---
name: google-health-sync
description: Rerunnable sync loop for the google_health_plus fork — diff library data types vs exposed sensors, port new metrics, sync upstream home-assistant/core changes at HA releases, and deploy to Home Assistant via HACS. Use when adding new Google Health metrics, checking upstream drift, or releasing/deploying a new version.
---

# Google Health Sync

Procedural checklist for evolving this fork. Run top to bottom; skip sections
that don't apply. Everything runs from the repo root
(`~/Workspace/Aurelian/ha-google-health-plus`).

## Prerequisites

- `nix develop` environment (direnv or explicit)
- `gh` authenticated to `Shuttleworth-Tech`
- `hassio` CLI on the controlling Mac, HA VM reachable via API

## Mode A — add newly available metrics

1. **Diff metric coverage** (deterministic, no Google token needed):

   ```bash
   ./.claude/skills/google-health-sync/scripts/check_metrics.py
   ```

   Parses the installed `google_health_api` accessors and the integration's
   `sensor.py`/`coordinator.py`, then lists data types that are fetchable but
   not yet exposed.

2. **Map new types** — for each unmapped type, decide and record in the PR
   description (and eventually the README sensor table):
   - shape rule: rollup → daily total, sample → latest value, interval → daily
     sum, session → timestamps + derived durations
   - unit, `device_class`, `state_class`, icon, translation key
   - which coordinator owns it (add a new one only for a new poll cadence)
3. **Implement**: extend `coordinator.py` (dataclass + fetch), `sensor.py`
   (`SensorEntityDescription` + `value_fn`), `__init__.py` scope gate,
   `strings.json` + `translations/en.json`. Scope gate reuses
   `api_client.<metric>.required_read_scopes` — never hardcode scope URLs.
4. **Verify locally**:

   ```bash
   nix develop -c bash -c './.venv/bin/pytest -q'
   nix develop -c bash -c './.venv/bin/ruff check custom_components tests'
   ```

   Add/refresh tests and run `--snapshot-update` when sensors change.

5. Continue with Mode C (release + deploy).

## Mode B — sync upstream at each HA release

1. **Check upstream drift**:

   ```bash
   ./.claude/skills/google-health-sync/scripts/sync_upstream.sh <tag>
   # e.g. sync_upstream.sh 2026.9.0
   ```

   Fetches `homeassistant/components/google_health/` at the tag and diffs
   against our snapshot. Empty diff → done, update nothing.

2. **Port worth-taking changes** by hand (OAuth/config-flow fixes, unit and
   classification corrections, new upstream sensors). Upstream additions we
   already have divergent implementations of → reconcile, don't blind-copy.
3. **Bump pins together**: `requirements_test.txt` (`homeassistant`,
   `pytest-homeassistant-custom-component`, matching PHACC release),
   `hacs.json` `homeassistant` minimum, `manifest.json` requirements if the
   library bumped, and the `UPSTREAM.md` SHA.
4. **Verify locally** (Mode A step 4), then Mode C.

## Mode C — release and deploy to HA

1. **Bump version** in `custom_components/google_health_plus/manifest.json`.
2. **Commit + push**, confirm CI green on `main`.
3. **Tag + release** (release workflow tests, validates the tag/manifest match,
   builds and attaches `google_health_plus.zip`):

   ```bash
   git tag vX.Y.Z && git push origin vX.Y.Z
   gh run watch  # release workflow
   ```

4. **Install/update on the HA VM** (first time: HACS → custom repositories →
   `Shuttleworth-Tech/ha-google-health-plus`, category Integration; HACS needs
   the GitHub account connected since the repo is private):
   - UI: HACS → Google Health Plus → redownload, pick the new version
   - Or via API: trigger HACS download websocket command, then
     `hassio call-service homeassistant restart`
5. **Verify live**: after restart, add the integration (same OAuth client as
   core `google_health`), then:

   ```bash
   hassio query "integration:google_health_plus"
   ```

   Confirm the new entities exist and report values within one poll interval
   (15 min activity / 1 h body metrics). Report a before/after entity list.

## Notes

- The paired-device and sensor universe is scope-gated; if a new metric needs
  a scope outside `OAUTH_SCOPES` in `const.py`, the user must re-auth.
- ECG / irregular-rhythm-notification need clinical scopes we deliberately do
  not request — do not add them.
- If CI snapshot tests fail with "Snapshot does not exist", check that the
  venv-prepare step and the test step are separate workflow steps (see git
  history around 2026-08-13); do not merge them back into one step.
- Release zip layout: integration FILES at the zip root (manifest.json, ...).
  HACS extracts into `/config/custom_components/<domain>/` directly — any
  wrapping folder in the zip doubles the nesting and HA never finds the
  manifest (learned the hard way across v0.1.0-v0.1.2).
