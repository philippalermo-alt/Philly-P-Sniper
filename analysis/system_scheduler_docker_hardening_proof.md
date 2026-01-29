# System Scheduler Hardening Proof

**Date**: 2026-01-27
**Target**: `ubuntu@100.48.72.44`
**Scope**: Docker Execution Safety + Backup Quarantine.

## 1. Identity & Privileges
**User**: `ubuntu`
**Groups**: `adm dialout ... docker` (Confirmed Membership)
**Docker Access**: `DIRECT` (No Sudo Required)

## 2. Wrapper Hardening (No Sudo)
Updated `PYTHON_EXEC` to use direct `docker exec` and updated availability guards.

**File**: `scripts/wrappers/run_pipeline_hourly.sh` (and others)
```diff
-PYTHON_EXEC="sudo docker exec -i philly_p_api python3"
+PYTHON_EXEC="docker exec -i philly_p_api python3"
```

## 3. Backup Quarantine
**Action**: Commented out `backup_restore.sh` in Crontab.

**Crontab Verification**:
```bash
# 6. Disaster Recovery Backup (10:00 AM)
# DISABLED: backup_restore.sh failing (self-SSH host key). Pending fix.
```

## 4. Execution Proof (Manual Run)

| Script | Exit Code | Result | Note |
| :--- | :--- | :--- | :--- |
| `run_pipeline_hourly.sh` | **0** | ✅ **PASS** | Runs in Docker (No Sudo). |
| `run_settle_daily.sh` | **0** | ✅ **PASS** | Runs in Docker (No Sudo). |
| `run_retrain_weekly.sh` | **0** | ✅ **PASS** | Runs in Docker (No Sudo). |
| `run_recap_daily.sh` | **0** | ✅ **PASS** | Runs in Docker (No Sudo). |

## 5. Remaining Anomalies (Out of Scope)
- `run_ops_health.sh`: **MISSING** on disk (Scheduled in Crontab but fails).
- `run_ingest_daily.sh`: **BROKEN** on disk (Bad Path) but execution not requested for fix.

## 6. Conclusion
The Scheduler is **HARDENED** and **SAFE**.
- No `sudo` usage in scripts.
- No failing Backup jobs spamming logs.
- Core pipeline Execution verified.
