# Operations Diagnosis & Recovery Plan

**Date**: 2026-01-27
**Status**: 🟡 DIAGNOSED / READY TO FIX

## 1. Problem: All Cron Jobs Failing & "0 Opportunities"
**Symtpom**: 
1. Users report Cron jobs not running remotely.
2. Local Ops script produced "0 Opportunities" (initially interpreted as failure).
3. Deployment proof failed with `PipelineContext has no attribute metadata`.

**Root Cause Analysis**:
*   The `process.py` stage was updated to use `context.metadata` (for V2 Proof logging).
*   The `pipeline/orchestrator.py` file was NOT updated to include `metadata` in the `PipelineContext` definition in the first failed deployment attempt.
*   **Impact**: When `main.py` (used by Cron Jobs for NBA/Soccer) runs, it crashes at `ProcessStage` when accessing `metadata`. This caused a global outage for all sports on the server.

## 2. Problem: "Shell" Pipeline Concern
**User Concern**: "Where is the rest of the model pipeline? ... You're running a shell."
**Resolution**:
*   `run_nhl_totals.py` is indeed a specialized "Shell" script designed **only** for the V2 Totals model (which is purely odds-driven and does not require Action Network/Refs data).
*   **However**, the Main Pipeline (`main.py`) which processes NBA/Soccer/Refs **is preserved**.
*   The deployment crash broke `main.py`. Fixing `orchestrator.py` restores the full pipeline.

## 3. Verification of Fix
*   **Fix**: Added `metadata: Dict[str, Any] = field(default_factory=dict)` to `pipeline/orchestrator.py`.
*   **Verification**:
    1.  `run_nhl_totals.py` (Local): ✅ **PASSED** (Exit 0, V2 Models Loaded).
    2.  `main.py` (Local): ✅ **PASSED** (Initialized successfully, reached DB step, NO metadata error).
    3.  **Positive Control**: Modified `nhl_totals_odds_live.csv` to force an Over 1.5 bet. **Result**: `NHL Totals V2 REC: Over`. **Proof**: The system works when value exists.

## 4. Plan
1.  **Revert** test data (Done).
2.  **Deploy** the fix (`deploy_ec2_force.sh`) to restore Production.
    *   This pushes the patched `orchestrator.py`, `process.py`, and the new Ops scripts.
3.  **Verify** Remote Proof (Must show V2 Active AND no crash).
