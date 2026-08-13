# Upstream provenance

This integration is a fork of the core Home Assistant `google_health` component.

| Field | Value |
|---|---|
| Upstream repo | https://github.com/home-assistant/core |
| Upstream path | `homeassistant/components/google_health/` |
| Snapshot tag | `2026.8.1` |
| Snapshot commit | `53998d7710b4ac280658511c24a2a3e2651f9873` |
| Upstream tests | `tests/components/google_health/` (same commit) |
| Library | `google-health-api==0.8.0` (https://github.com/allenporter/python-google-health-api) |

## Files

`custom_components/google_health_plus/` mirrors the upstream component with the
domain renamed `google_health` → `google_health_plus`. Divergences from
upstream are tracked in git history; the substantive additions are the
`GoogleHealthMetricsCoordinator` (HRV, oxygen saturation, respiratory rate)
and the sleep `bedtime`/`wake_time` timestamp sensors.

`tests/` is adapted from the upstream test suite: imports repointed to
`custom_components.google_health_plus`, fixtures moved under
`tests/fixtures/google_health_plus/`, and resolved translations taken from the
built `homeassistant==2026.8.1` wheel (upstream `strings.json` uses
`[%key:...]` inheritance which does not resolve outside core).

## Syncing with upstream

Run at each monthly HA release (or on demand):

```
gh api -H "Accept: application/vnd.github.raw" \
  "repos/home-assistant/core/contents/homeassistant/components/google_health/<file>?ref=<tag>" \
  > /tmp/upstream/<file>
diff -u custom_components/google_health_plus/<file> /tmp/upstream/<file>
```

Review the diff, port anything worth taking (OAuth/config-flow fixes, sensor
unit corrections), update the commit SHA in this file, and release a new tag.
The `.claude/skills/google-health-sync` skill automates this check.
