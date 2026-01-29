# Operations Proof Run: NHL Totals V2

**Date**: 2026-01-27
**Status**: ✅ VERIFIED
**Contract Status**:
*   **Stage 1 (Local Verification)**: ✅ PASSED (All scripts executed successfully).

## 1. Odds Ingest (Continuous)
**Command**: `python3 scripts/ops/ingest_nhl_live_odds.py`
**Output**: 
```text
[12:38:32] Starting NHL Totals Live Ingest -> Hockey Data/nhl_totals_odds_live.csv
[12:38:33] ✅ Saved 13 live odds to Hockey Data/nhl_totals_odds_live.csv
```
**Verify**: `Hockey Data/nhl_totals_odds_live.csv` updated.

## 2. Totals Run (Nightly)
**Command**: `export NHL_TOTALS_V2_ENABLED=true && python3 scripts/ops/run_nhl_totals.py`
**Output**:
```text
[INFO] [NHL_V2] ✅ Loaded XGBoost Model V2
[INFO] [NHL_V2] ✅ Loaded Goalie Features (137 goalies)
[INFO] [NHL_V2] ✅ Loaded Team Stats (33 teams)
[INFO] [NHL_TOTALS] ✅ Loaded V2 Model & artifacts (33 teams)
[INFO] [OPS] 🚀 Starting NHL Totals Run for 2026-01-27
[INFO] [PROCESS] Running Betting Models...
[INFO] [PROCESS] ✅ Identified 0 Opportunities (Ops)
[INFO] [OPS] ℹ️ No opportunities context populated.
```
**Verify**: Pipeline executed, V2 models loaded. No failures.

## 3. KPI Report (Daily)
**Command**: `export NHL_TOTALS_V2_ENABLED=true && python3 scripts/ops/generate_nhl_kpi.py`
**Output**:
```text
KPI Report Generated: analysis/nhl_phase2_totals/live_kpis/2026-01-27.json
```
**Verify**: File exists.

## 4. Retrain (Weekly)
**Command**: `export NHL_TOTALS_V2_ENABLED=true && python3 scripts/ops/retrain_nhl_totals.py`
**Output**:
```text
Starting Retrain Candidate Generation for 20260127...
✅ Retrain Candidate Generated.
```
**Verify**: Candidate joblib created in `models/candidates/`.

## Conclusion
All systems operational. Systemd Timers ready for deployment.
