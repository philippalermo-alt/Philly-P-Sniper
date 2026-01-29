# NHL Totals V2 Operations: Job Entrypoints

## 1. Odds Ingest (Continuous)
Fetches live/upcoming NHL totals odds from The-Odds-API and updates the "Live" snapshot.
*   **Command**: `python3 scripts/ops/ingest_nhl_live_odds.py`
*   **Env Vars**:
    *   `ODDS_API_KEY` (Required)
*   **Output**: `Hockey Data/nhl_totals_odds_live.csv` (Overwrites previous live snapshot, distinct from historical close).

## 2. Totals Prediction Run (Nightly)
Executes the V2 Model Pipeline for upcoming games w/ Strict Verification.
*   **Command**: `python3 scripts/ops/run_nhl_totals.py`
*   **Env Vars**:
    *   `NHL_TOTALS_V2_ENABLED=true` (Required)
*   **Output**:
    *   `predictions/nhl_totals_v2/YYYY-MM-DD/predictions.csv`
    *   `predictions/nhl_totals_v2/YYYY-MM-DD/recommendations.csv`
*   **Verification**:
    *   MUST Log: `NHL_TOTALS_V2_ACTIVE model=... sigma=... bias=...`
    *   MUST NOT Log: `NHL_TOTALS_LEGACY_ACTIVE`

## 3. KPI Reporting (Daily)
Generates the 24h performance report (Live vs Model).
*   **Command**: `python3 scripts/ops/generate_nhl_kpi.py`
*   **Env Vars**:
    *   `NHL_TOTALS_V2_ENABLED=true`
*   **Output**: `analysis/nhl_phase2_totals/live_kpis/YYYY-MM-DD.json`

## 4. Retraining (Weekly)
Re-trains the ElasticNet model on the latest dataset (2022-Present).
*   **Command**: `python3 scripts/ops/retrain_nhl_totals.py`
*   **Env Vars**:
    *   `NHL_TOTALS_V2_ENABLED=true`
*   **Output**: 
    *   **Candidate**: `models/candidates/nhl_totals_v2_YYYYMMDD.joblib`
    *   **Report**: `analysis/nhl_phase2_totals/retrain_reports/retrain_report_YYYY-MM-DD.md`
    *   **No Auto-Promotion**: Current model symlink untouched.
