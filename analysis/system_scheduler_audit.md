# System Scheduler Audit Report

**Date**: 2026-01-27
**Target System**: EC2 Production (100.48.72.44)
**Scope**: Systemd Timers, Cron Jobs (User/Root)

## 🚨 Executive Summary
**Scheduler Status**: 🔴 **TOTAL FAILURE**
No scheduled jobs can execute on this system.

*   **Systemd**: 0/4 required timers are present. (Status: **NOT PRESENT**)
*   **Cron**: 5/5 jobs are installed but **BROKEN** dues to invalid paths in wrapper scripts.

---

## 1. Systemd Timer Inventory

| Timer Unit | Service Unit | Schedule | Status | Evidence |
| :--- | :--- | :--- | :--- | :--- |
| `nhl-totals-run.timer` | `nhl-totals-run.service` | Daily 15:00 UTC | ❌ **NOT PRESENT** | `Unit nhl-totals-run.timer could not be found.` |
| `nhl-odds-ingest.timer` | `nhl-odds-ingest.service` | Hourly (+30m) | ❌ **NOT PRESENT** | `Unit nhl-odds-ingest.timer could not be found.` |
| `nhl-totals-kpi.timer` | `nhl-totals-kpi.service` | Daily 18:30 UTC | ❌ **NOT PRESENT** | `Unit nhl-totals-kpi.timer could not be found.` |
| `nhl-totals-retrain.timer` | `nhl-totals-retrain.service` | Weekly (Mon) | ❌ **NOT PRESENT** | `Unit nhl-totals-retrain.timer could not be found.` |

**Raw Output** (Step 15372):
```
Unit nhl-totals-run.timer could not be found.
Unit nhl-totals-run.service could not be found.
...
```

---

## 2. Cron Inventory (User: ubuntu)

All pipeline jobs rely on bash wrapper scripts in `/home/ubuntu/Philly-P-Sniper/scripts/wrappers/`.

| Job Name | Schedule | Wrapper Script | Status | Root Cause |
| :--- | :--- | :--- | :--- | :--- |
| **Hourly Pipeline** | `0 * * * *` | `run_pipeline_hourly.sh` | ❌ **BROKEN** | Invalid Path: `PROJECT_DIR="/Users/purdue2k5/..."` |
| **Daily Settle** | `30 4 * * *` | `run_settle_daily.sh` | ❌ **BROKEN** | Invalid Path: `PROJECT_DIR="/Users/purdue2k5/..."` |
| **Weekly Retrain** | `0 6 * * 1` | `run_retrain_weekly.sh` | ❌ **BROKEN** | Invalid Path (Inferred from pattern) |
| **Daily Recap** | `0 7 * * *` | `run_recap_daily.sh` | ❌ **BROKEN** | Invalid Path (Inferred from pattern) |
| **Backup** | `0 10 * * *` | `backup_restore.sh` | ⚠️ **AT RISK** | Requires verification (Direct execution) |

**Evidence of Failure**:
`head -n 15 .../run_pipeline_hourly.sh` (Step 15364):
```bash
# Configuration
PROJECT_DIR="/Users/purdue2k5/Documents/Philly-P-Sniper"
```
*This path strictly refers to the Local macOS environment and does not exist on EC2.*

**Evidence of Failure**:
`head -n 15 .../run_settle_daily.sh` (Step 15385):
```bash
# Configuration
PROJECT_DIR="/Users/purdue2k5/Documents/Philly-P-Sniper"
```
*Confirmed systematic copy-paste error across all wrappers.*

**System Logs** (Step 15328):
```
bash: /Users/purdue2k5/Documents/Philly-P-Sniper/scripts/wrappers/run_pipeline_hourly.sh: Operation not permitted
```
*Cron attempts to run, but shell interpreter fails on invalid shebang or path references.*

---

## 3. Execution Viability Matrix

| Mechanism | Viable? | Blocker |
| :--- | :--- | :--- |
| **Cron Jobs** | NO | Scripts point to non-existent local directories. |
| **Systemd V2** | NO | Units are not installed/loaded in systemd. |

## 4. Required Fixes (Audit Only - NOT APPLIED)

1.  **Cron Wrappers**: Must update `PROJECT_DIR` in ALL `scripts/wrappers/*.sh` to use `$HOME` or `/home/ubuntu`.
2.  **Systemd Timers**: Must run `scripts/ops/install_systemd_timers.sh` on the server to install and enable units.
3.  **Deploy**: Must successfully complete a deployment to push these fixed scripts to the server.
