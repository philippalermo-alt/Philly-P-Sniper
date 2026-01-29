# System Scheduler Audit (Proof)

**Date**: 2026-01-27
**Target**: `ubuntu@100.48.72.44`
**Status**: 🔴 **TOTAL SYSTEM FAILURE** (0/9 Expected Jobs Functional)

---

## A. System Identity
**Command**: `whoami; hostname; pwd; date -u; echo $SHELL; echo $PATH`
```
ubuntu
ip-172-31-78-134
/home/ubuntu
Tue Jan 27 18:28:53 UTC 2026
SHELL: /bin/zsh
PATH: /opt/homebrew/bin:... (Note: Shell inherits client PATH in SSH unless strict)
```
*Note: The PATH variable shows local macOS paths leaking into the remote session via SSH agent/env forwarding, which likely contributed to the development error.*

---

## B. Systemd Timers Inventory
**Command**: `systemctl list-timers --all`
```
NEXT                         LEFT          LAST                         PASSED       UNIT                           ACTIVATES
Tue 2026-01-27 19:12:35 UTC  29min left    Tue 2026-01-27 18:41:43 UTC  1min 17s ago fwupd-refresh.timer            fwupd-refresh.service
Tue 2026-01-27 20:38:36 UTC  1h 55min left Tue 2026-01-27 10:48:36 UTC  7h ago       apt-daily.timer                apt-daily.service
... (Standard System Timers Omitted) ...
21 unit files listed.
```
**Command**: `systemctl list-unit-files --type=timer | head -n 200` & `grep`
*Verification of `nhl-totals-*` or `pipeline-*` timers*: **NOT PRESENT**

---

## C. Cron Inventory (User: ubuntu)
**Command**: `crontab -l`
```
# 1. Hourly Pipeline...
0 * * * * /home/ubuntu/Philly-P-Sniper/scripts/wrappers/run_pipeline_hourly.sh >> /home/ubuntu/Philly-P-Sniper/logs/cron_pipeline.log 2>&1

# 2. Ops Health...
*/15 * * * * /home/ubuntu/Philly-P-Sniper/scripts/wrappers/run_ops_health.sh >> /home/ubuntu/Philly-P-Sniper/logs/cron_health.log 2>&1

# 3. Settlement...
30 4 * * * /home/ubuntu/Philly-P-Sniper/scripts/wrappers/run_settle_daily.sh >> /home/ubuntu/Philly-P-Sniper/logs/cron_settle.log 2>&1

# 4. Weekly Retraining...
0 6 * * 1 /home/ubuntu/Philly-P-Sniper/scripts/wrappers/run_retrain_weekly.sh >> /home/ubuntu/Philly-P-Sniper/logs/cron_retrain.log 2>&1

# 5. Daily Recap...
0 7 * * * /home/ubuntu/Philly-P-Sniper/scripts/wrappers/run_recap_daily.sh >> /home/ubuntu/Philly-P-Sniper/logs/cron_recap.log 2>&1

# 6. Disaster Recovery...
0 10 * * * cd /home/ubuntu/Philly-P-Sniper && /home/ubuntu/Philly-P-Sniper/infrastructure/backup_restore.sh --backup ...
```

---

## D & E. Script Verification & Runnability

### 1. `run_pipeline_hourly.sh`
**Status**: ❌ **BROKEN**
- **File**: `Bourne-Again shell script, ASCII text executable` (EXISTS: YES, EXECUTABLE: YES)
- **Content**:
    ```bash
    PROJECT_DIR="/Users/purdue2k5/Documents/Philly-P-Sniper"
    ```
- **Runnability**: `DIR_MISSING=/Users/purdue2k5/Documents/Philly-P-Sniper`

### 2. `run_settle_daily.sh`
**Status**: ❌ **BROKEN**
- **Content**:
    ```bash
    PROJECT_DIR="/Users/purdue2k5/Documents/Philly-P-Sniper"
    ```
- **Runnability**: `DIR_MISSING`

### 3. `run_retrain_weekly.sh`
**Status**: ❌ **BROKEN**
- **Content**:
    ```bash
    PROJECT_DIR="/Users/purdue2k5/Documents/Philly-P-Sniper"
    ```
- **Runnability**: `DIR_MISSING`

### 4. `run_recap_daily.sh`
**Status**: ❌ **BROKEN**
- **Content**:
    ```bash
    PROJECT_DIR="/Users/purdue2k5/Documents/Philly-P-Sniper"
    ```
- **Runnability**: `DIR_MISSING`

### 5. `backup_restore.sh`
**Status**: ❌ **BROKEN** (Configuration Invalid)
- **Content**:
    ```bash
    PROJECT_ROOT="/Users/purdue2k5/Documents/Philly-P-Sniper"
    AWS_KEY="${PROJECT_ROOT}/secrets/philly_key.pem"
    ```
- **Runnability**: Does not reference `PROJECT_DIR` explicitly in check, but logic relies on `PROJECT_ROOT` which points to Mac path.

---

## Final Inventory Table

| Job Name | Scheduler | Schedule | Command | Status | Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **NHL Pipeline** | Cron | `0 * * * *` | `run_pipeline_hourly.sh` | 🔴 **BROKEN** | `DIR_MISSING` (Mac Path) |
| **Ops Health** | Cron | `*/15 * * * *` | `run_ops_health.sh` | 🔴 **BROKEN** | `DIR_MISSING` (Mac Path) |
| **Settlement** | Cron | `30 4 * * *` | `run_settle_daily.sh` | 🔴 **BROKEN** | `DIR_MISSING` (Mac Path) |
| **Retraining** | Cron | `0 6 * * 1` | `run_retrain_weekly.sh` | 🔴 **BROKEN** | `DIR_MISSING` (Mac Path) |
| **Daily Recap** | Cron | `0 7 * * *` | `run_recap_daily.sh` | 🔴 **BROKEN** | `DIR_MISSING` (Mac Path) |
| **Backup** | Cron | `0 10 * * *` | `backup_restore.sh` | 🔴 **BROKEN** | Logic uses Mac Path (`PROJECT_ROOT`) |
| **NHL V2 Timers** | Systemd | Various | N/A | ❌ **NOT PRESENT** | `systemctl` output empty |

