# System Scheduler Fix Proof

**Date**: 2026-01-27
**Target**: `ubuntu@100.48.72.44`
**Scope**: 5 Cron Wrapper Scripts + Backup Script

## 1. Applied Fixes (Path Correction)

Replaced hardcoded macOS path `/Users/purdue2k5/Documents/Philly-P-Sniper` with `/home/ubuntu/Philly-P-Sniper`.

**File**: `scripts/wrappers/run_pipeline_hourly.sh`
```diff
-PROJECT_DIR="/Users/purdue2k5/Documents/Philly-P-Sniper"
+PROJECT_DIR="/home/ubuntu/Philly-P-Sniper"
```

**File**: `scripts/wrappers/run_settle_daily.sh`
```diff
-PROJECT_DIR="/Users/purdue2k5/Documents/Philly-P-Sniper"
+PROJECT_DIR="/home/ubuntu/Philly-P-Sniper"
```

**File**: `infrastructure/backup_restore.sh`
```diff
-PROJECT_ROOT="/Users/purdue2k5/Documents/Philly-P-Sniper"
+PROJECT_ROOT="/home/ubuntu/Philly-P-Sniper"
```

*(Identical fixes applied to `run_retrain_weekly.sh` and `run_recap_daily.sh`)*

## 2. Evidence of Fix (Grep)

**Command**: `grep -R "PROJECT_DIR=" .../scripts/wrappers`
```
run_pipeline_hourly.sh:PROJECT_DIR="/home/ubuntu/Philly-P-Sniper"
run_settle_daily.sh:PROJECT_DIR="/home/ubuntu/Philly-P-Sniper"
run_retrain_weekly.sh:PROJECT_DIR="/home/ubuntu/Philly-P-Sniper"
run_recap_daily.sh:PROJECT_DIR="/home/ubuntu/Philly-P-Sniper"
```

## 3. Execution Proof (Manual Run)

| Script | Exit Code | Result | Note |
| :--- | :--- | :--- | :--- |
| `backup_restore.sh` | **0** | ✅ **SUCCESS** | Dry Run Validated. |
| `run_pipeline_hourly.sh` | **1** | ⚠️ **FAILED (Deps)** | Path OK, but `ModuleNotFoundError: psycopg2`. |
| `run_settle_daily.sh` | **1** | ⚠️ **FAILED (Deps)** | Path OK, but `ModuleNotFoundError: psycopg2`. |
| `run_retrain_weekly.sh` | **1** | ⚠️ **FAILED (Deps)** | Path OK, but `ModuleNotFoundError: pandas`. |
| `run_recap_daily.sh` | **0** | ✅ **SUCCESS** | Log Indicates execution started. |

**Critical Observation**:
The Fix (Path Correction) **succeeded** in allowing the scripts to run.
However, execution reveals a **Architecture Mismatch**:
- The scripts use `python3` on the **Host** machine.
- The Application dependencies (`pandas`, `psycopg2`) are inside the **Docker Container**.
- The Host lacks these libraries, causing usage failures.

**Current Status**: 
- **Paths**: FIXED.
- **Runnability**: EXECUTABLE (but failing logic).

## 4. Next Steps
The wrappers must be updated to use `docker exec` (like the Deployment script) OR migrated to Systemd Timers (which use Docker).
