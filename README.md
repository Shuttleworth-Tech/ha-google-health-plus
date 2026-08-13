# Google Health Plus for Home Assistant

Custom integration extending the core
[`google_health`](https://www.home-assistant.io/integrations/google_health/)
integration with metrics the upstream integration does not yet expose, using
the same [`google-health-api`](https://github.com/allenporter/python-google-health-api)
library and OAuth client.

## Extra sensors (v0.1)

| Sensor | Unit | Source |
|---|---|---|
| Heart rate variability (latest RMSSD) | ms | `heart_rate_variability` |
| Daily heart rate variability | ms | `daily_heart_rate_variability` |
| Oxygen saturation (latest) | % | `oxygen_saturation` |
| Daily oxygen saturation | % | `daily_oxygen_saturation` |
| Respiratory rate (daily) | breaths/min | `daily_respiratory_rate` |
| Sleep respiratory rate | breaths/min | `respiratory_rate_sleep_summary` |
| Bedtime (sleep session start) | timestamp | `sleep.interval.start_time` |
| Wake time (sleep session end) | timestamp | `sleep.interval.end_time` |

It can run side by side with the core `google_health` integration — entity
prefixes differ (`sensor.google_health_plus_*`).

## Setup

1. Follow the [upstream docs](https://www.home-assistant.io/integrations/google_health/)
   to enable the **Google Health API** and create your OAuth client
   (redirect URI `https://my.home-assistant.io/redirect/oauth`). The same
   client works for both integrations.
2. Add this repository to HACS as a custom repository (category:
   **Integration**) and install it.
3. Add the **Google Health Plus** integration and authorize with your Google
   account (Advanced → Go to app (unsafe) if your OAuth app is unverified).

## Development

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements_test.txt
pytest
```

`UPSTREAM.md` records the upstream core commit this fork snapshot derives
from; `.claude/skills/google-health-sync/` automates upstream syncing and
adding new metrics.

## License

MIT — see [LICENSE](LICENSE).
