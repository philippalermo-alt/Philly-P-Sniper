# System Scheduler Docker Fix Proof

**Date**: 2026-01-27
**Target**: `ubuntu@100.48.72.44`
**Scope**: Dockerization of Cron Wrappers.

## 1. Discovery Evidence
**Container**: `philly_p_api` (Image: `philly-sniper-backend:latest`)
**Status**: Up 13+ minutes.

## 2. Applied Fixes (Docker Execution)
Updated `PYTHON_EXEC` to run inside the container, preserving host logging.

**File**: `scripts/wrappers/run_pipeline_hourly.sh` (and others)
```diff
-PYTHON_EXEC="python3"
+PYTHON_EXEC="sudo docker exec -i philly_p_api python3"
+command -v docker >/dev/null || { echo "Docker missing"; exit 1; }
```

## 3. Execution Proof (Manual Run)

| Script | Exit Code | Result | Note |
| :--- | :--- | :--- | :--- |
| `run_pipeline_hourly.sh` | **0** | ✅ **PASS** | Runs `main.py` in Docker. |
| `run_settle_daily.sh` | **0** | ✅ **PASS** | Runs `settle_props.py` in Docker. |
| `run_retrain_weekly.sh` | **0** | ✅ **PASS** | Runs `retrain_nba_weekly.py` in Docker. |
| `run_recap_daily.sh` | **0** | ✅ **PASS** | Runs `daily_email_recap.py` in Docker. |
| `backup_restore.sh` | **255** | ⚠️ **FAIL (Logic)** | Path fixed, but script attempts to SSH to itself (`100.48.72.44`) causing Host Key Failure. Requires logic refactor to "Local Mode". |

## 4. Conclusion
The Scheduler is now **FUNCTIONAL** for all core application tasks (Pipeline, Metrics, Settle, Retrain).
The core python scripts are correctly executing inside the production container.

The Backup job remains broken due to recursive SSH logic, distinct from the path/env issues.

**Stop Condition Met.**
Do you want me to proceed with Migrating to Systemd (Recommended) or Fix the Backup Script Logic?
