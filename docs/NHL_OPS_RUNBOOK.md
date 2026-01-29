
# NHL Operations Runbook
**Version:** 1.0 (Phase 7)
**Date:** 2026-01-28

This guide details the daily operations for the NHL Edge Engine ("Philly-P-Sniper").

## 1. Prerequisites
- Run from Project Root: `/Users/purdue2k5/Documents/Philly-P-Sniper`
- Set PYTHONPATH: `export PYTHONPATH=.`

## 2. Daily Workflow
Run these commands in order every day (e.g., 9:00 AM ET).

### Step 1: Ingestion
Update the database with yesterday's games and today's roster updates.
```bash
python3 scripts/ops.py ingest
```

### Step 2: Validation
Ensure data integrity (keys, logic, missingness).
```bash
python3 scripts/ops.py validate
```
*If this fails, STOP. Check logs for Dup Keys or API errors.*

### Step 3: Scoring
Generate projections for today's slate.
```bash
python3 scripts/ops.py score
```
*Can optionally specify `--slate YYYY-MM-DD`.*

### Step 4: Recommendation
Generate +EV bets and publish to Dashboard.
```bash
python3 scripts/ops.py recommend
```
*Runs against Live Odds.*

### Step 5: Monitoring
Check calibration and drift.
```bash
python3 scripts/ops.py monitor
```

## 3. Operations Reference

### Run Modes
Configuration in `scripts/nhl_ops_config.py`.
- **FULL**: Hard blocking gates.
- **DEGRADED**: (Not yet fully utilized, but configured for future flexibility).

### Backfilling
To ingest historical data:
```bash
# Note: Currently uses the safe ingest script which logic is hardcoded for "Recent/Fill".
# Future update will expose date args.
python3 scripts/ops.py ingest
```

### Retraining
**Trigger**: When `monitor` reports consistent drift > 3% for 2 weeks.
**Process**:
1.  Run `python3 scripts/train_sog_model_nb.py` (Phase 1).
2.  Run `python3 scripts/train_goals_model.py` (Phase 2).
3.  Run `python3 scripts/train_assists_model_nb.py` (Phase 3).
4.  Run `python3 scripts/build_points_sim.py` (Phase 4).
5.  Compare `validation_report.txt` vs previous version.
6.  If better, bump Version in `nhl_ops_config.py`.

## 4. Troubleshooting

**Issue**: `Integrity Gates Failed`
- Check `[FAIL]` messages.
- If `Dup Keys`: Run `DELETE FROM nhl_player_game_logs WHERE ...`
- If `Logic Error`: Run patch SQL (e.g. `UPDATE SET shots=goals ...`).

**Issue**: `KeyError 'game_id'` in Monitor
- Ensure you are using correct matching keys (Name+Date).
- Ensure `points_projections_phase4.csv` matches DB.

**Issue**: `No Odds Found`
- Check Internet/API Key.
- Check Time of Day (Odds might be late).
