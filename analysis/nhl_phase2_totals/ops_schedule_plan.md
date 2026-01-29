# NHL Totals V2 Operations Schedule

## Timers (Local Time)

| Timer | Service | Frequency | Script |
|:------|:--------|:----------|:-------|
| `nhl-odds-ingest.timer` | `nhl-odds-ingest.service` | **Every 60 min** | `scripts/ops/ingest_nhl_live_odds.py` |
| `nhl-totals-run.timer` | `nhl-totals-run.service` | **Daily 15:00** | `scripts/ops/run_nhl_totals.py` |
| `nhl-totals-kpi.timer` | `nhl-totals-kpi.service` | **Daily 07:00** | `scripts/ops/generate_nhl_kpi.py` |
| `nhl-totals-retrain.timer` | `nhl-totals-retrain.service` | **Mon 05:00** | `scripts/ops/retrain_nhl_totals.py` |

## Deployment
*   **Installer**: `scripts/ops/install_systemd_timers.sh`
*   **Location**: `/etc/systemd/system/`
*   **User**: `ubuntu`
*   **Logs**: `journalctl -u <service>`
