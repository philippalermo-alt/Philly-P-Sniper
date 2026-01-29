# NHL Scheduler Scope Verification

**Date**: 2026-01-27
**Target**: `ubuntu@100.48.72.44`
**Scheduler**: `nhl-totals-run.service` (Systemd)

## 1. Verification of Scope
The user asked: *"Scheduler handles full NHL V2, money lines and totals, correct?"*

**ANSWER**: **YES**, the scheduler executes **BOTH** Moneyline V2 and Totals V2 logic.

## 2. Evidence from Logs
From `logs/systemd/nhl-totals-run.log` (Run ID: `80b1743f...`):

### A. Moneyline V2 (Confirmed Active)
The Model and its dependencies (Goalie Features, Team Stats) are successfully initialized.
```
2026-01-27 13:55:03,652 [INFO] [NHL_V2] ✅ Loaded XGBoost Model V2
2026-01-27 13:55:09,511 [INFO] [NHL_V2] ✅ Loaded Goalie Features (137 goalies)
2026-01-27 13:55:09,956 [INFO] [NHL_V2] ✅ Loaded Team Stats (33 teams)
```

### B. Totals V2 (Confirmed Active)
The Totals model is explicitly logged via the Proof Marker.
```
2026-01-27 13:55:09,987 [INFO] [NHL_TOTALS] ✅ Loaded V2 Model & artifacts (33 teams)
...
2026-01-27 13:55:09,997 [INFO] [PROOF] NHL_TOTALS_V2_ACTIVE model=ElasticNet sigma=2.242 bias=-0.1433 features=nhl_totals_features_v1
```

## 3. Code Execution Path
1.  **Entrypoint**: `scripts/ops/run_nhl_totals.py`
    - Sets target sport to `icehockey_nhl`.
    - Calls `process.execute(context)`.
2.  **Logic**: `pipeline/stages/process.py`
    - Iterates `context.odds_data` (NHL).
    - **Step 1**: Executes `_nhl_model.predict_match(...)` (Moneyline).
    - **Step 2**: Executes `_nhl_totals.predict(...)` (Totals).
    - **Step 3**: Aggregates all valid opportunities to `all_opps`.

## 4. Critical Data Note (Moneyline)
While Moneyline V2 **executes**, the current Ops Ingest script (`ingest_nhl_live_odds.py` -> `nhl_totals_odds_live.csv`) **does not provide Goalie Starters**.
- **Impact**: Moneyline V2 runs in **Fallback Mode** (using League Average 0.0 GSAx for missing starters).
- **Recommendation**: To fully utilize Moneyline V2 accuracy, the Ingest script should be updated to scrape/include Probable Starters.
- **Totals V2**: Unaffected (does not use Starters).
