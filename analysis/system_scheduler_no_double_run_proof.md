# System Scheduler: Elimination of NHL Double-Run

**Date**: 2026-01-27
**Target**: `ubuntu@100.48.72.44`
**Status**: ✅ **DOUBLE-RUN PREVENTED**

## 1. Mechanisms Implemented
1.  **Code Gate**: `pipeline/stages/process.py` (Line 84)
    - Checks `os.environ.get("SKIP_NHL")`.
    - If "1", skips ALL NHL logic (ML, Totals, Props).
2.  **Cron Config**: `scripts/wrappers/run_pipeline_hourly.sh`
    - Updated to: `PYTHON_EXEC="docker exec -i -e SKIP_NHL=1 philly_p_api python3"`

## 2. Verification Proofs

### A. Cron Run (Hourly Pipeline)
**Command**: `bash run_pipeline_hourly.sh`
**Log**: `logs/pipeline_execution.log`
```
2026-01-27 13:56:14,459 [INFO] [PROCESS] SKIP_NHL=1 -> NHL pipelines disabled in hourly run
```
**Result**: NHL Totals V2 **DID NOT RUN** (No `NHL_TOTALS_V2_ACTIVE` marker).

### B. Systemd Run (Dedicated Ops)
**Command**: `systemctl start nhl-totals-run.service`
**Log**: `logs/systemd/nhl-totals-run.log`
```
2026-01-27 13:55:09,997 [INFO] [PROOF] NHL_TOTALS_V2_ACTIVE model=ElasticNet ...
```
**Result**: NHL Totals V2 **RAN SUCCESSFULLY**.

## 3. Conclusion
- The **Hourly Pipeline** handling NBA/Soccer/etc. now EXPLICITLY skips NHL.
- The **Systemd Timers** exclusive handle NHL Ingest, Runs, and Reporting.
- **Risk of Double-Execution Avoided.**
