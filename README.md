# Google Health Plus for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41AFDF.svg)](https://github.com/hacs/integration)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![HA](https://img.shields.io/badge/Home%20Assistant-2026.8%2B-41bdf5.svg)](hacs.json)

Extended Google Health sensors for Home Assistant — heart rate variability,
oxygen saturation, respiratory rate, and sleep bed/wake timestamps — on top
of the official [`google_health`](https://www.home-assistant.io/integrations/google_health/)
integration's sensor set.

## Why this exists

**This is a stop-gap.** The official `google_health` integration is only a few
weeks old and exposes a curated set of 17 sensors, added incrementally. The
underlying [`google-health-api`](https://github.com/allenporter/python-google-health-api)
library already supports ~36 data types — including the metrics below — under
scopes you have already granted, but no one has asked upstream for them yet
(as of 2026-08, no open issue or PR requests them).

This fork exists to:

1. **Get the extra data now** — a renamed custom integration (`google_health_plus`)
   running side by side with the official one, reusing the same OAuth client.
2. **Prove the demand and the implementation** — the coordinators, sensors, and
   tests here are written against the upstream code patterns, so they can be
   lifted into an upstream feature request/PR with minimal changes.

**The intended end state is this repository becoming obsolete**: once the
official integration exposes these metrics, switch over and uninstall. Until
then, this tracks upstream (see [UPSTREAM.md](UPSTREAM.md)) and syncs at each
monthly HA release.

## Extra sensors (v0.1)

Entity names use your HA account/device name; with entry title `aurelian` they
are `sensor.aurelian_plus_*`:

| Entity suffix | Description | Unit |
|---|---|---|
| `heart_rate_variability` | Latest HRV sample (RMSSD) | ms |
| `daily_heart_rate_variability` | Daily average HRV | ms |
| `oxygen_saturation` | Latest SpO₂ sample | % |
| `daily_oxygen_saturation` | Daily average SpO₂ | % |
| `respiratory_rate` | Daily average respiratory rate | breaths/min |
| `sleep_respiratory_rate` | Sleep respiratory rate (full-sleep stats) | breaths/min |
| `bedtime` | Sleep session start | timestamp |
| `wake_time` | Sleep session end | timestamp |
| `time_in_fat_burn_zone` / `_cardio_` / `_peak_` | Minutes in each HR zone today | min |
| `calories_in_fat_burn_zone` / `_cardio_` / `_peak_` | kcal burned in each HR zone today | kcal |
| `fat_burn_zone_min_heart_rate` / `_cardio_` / `_peak_` | Zone BPM thresholds (Karvonen) | bpm |
| `sleep_skin_temperature` | Nightly skin temperature | °C |
| `sleep_skin_temperature_deviation` | Skin temp vs 30-day baseline (recovery signal) | °C |

Plus the full official sensor set (steps, distance, calories, floors, weight,
resting heart rate, body fat, sleep durations, hydration, nutrition, paired
device diagnostics) — so you can run this alone or side by side with the
official integration.

### Notes on `unknown` values

If `oxygen_saturation` (intraday) or `sleep_respiratory_rate` show `unknown`
while the daily variants have values, your data source (e.g. WHOOP via Health
Connect) only uploads daily aggregates to the Google Health cloud store —
there are no intraday samples to read. This is a data-source limitation, not
a bug.

## Setup

1. Follow the [official Google Health docs](https://www.home-assistant.io/integrations/google_health/)
   to enable the **Google Health API** and create your OAuth client (redirect
   URI `https://my.home-assistant.io/redirect_oauth`). The **same client works
   for both integrations** — no new Google Cloud setup needed.
2. Add this repository to HACS as a custom repository (category:
   **Integration**) and install it.
3. Add the **Google Health Plus** integration and authorize with your Google
   account. If your OAuth app is unverified (personal apps: expected and fine —
   see the docs on [publishing status](https://www.home-assistant.io/integrations/google_health/#limitations)),
   click **Advanced → Go to app (unsafe)** at the consent screen.

Metrics refresh hourly; activity/sleep/nutrition every 15 minutes.

## Development

```
nix develop          # python3.14 + ruff + direnv shell (creates .venv first run)
./.venv/bin/pytest   # 31 tests
```

- [UPSTREAM.md](UPSTREAM.md) records the upstream commit this fork snapshots
  from, and the sync procedure.
- `.claude/skills/google-health-sync/` automates the loop: detect unmapped
  library data types, port upstream changes at HA releases, release, deploy.

## License

MIT — see [LICENSE](LICENSE). Not affiliated with Google, WHOOP, or the
Home Assistant project.
