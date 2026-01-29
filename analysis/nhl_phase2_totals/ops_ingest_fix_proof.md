# NHL Starter Injection Proof

**Date**: 2026-01-27
**Target**: `ubuntu@100.48.72.44`
**Status**: 🟡 **PARTIAL SUCCESS (Mechanism Active, Source Unstable)**

## 1. Code Implementation
**Ingest Script** (`scripts/ops/ingest_nhl_live_odds.py`):
- Now imports `fetch_dailyfaceoff_goalies` from `data.sources.nhl_goalies`.
- Fetches starters and merges them into the Odds Data based on team name.
- Output CSV (`nhl_totals_odds_live.csv`) verified to contain columns: `home_starter`, `away_starter`, `home_goalie_status`, `away_goalie_status`.

**Consumer Script** (`scripts/ops/run_nhl_totals.py`):
- Updated to read starter columns from CSV.
- Populates `game_obj['starters']`.
- Gracefully handles missing/null values (Fallback Mode).

## 2. Verification Results

### A. CSV Structure (Verified)
```csv
game_date,home_team... ,home_starter,home_goalie_status,away_starter,away_goalie_status
2026-01-28,Boston Bruins... ,,,,
```
Columns are present. Data is null due to scraper issue.

### B. Scraper Execution (Unstable)
logs/ingest:
```
[GOALIE_SCRAPER] Fetching https://www.dailyfaceoff.com/starting-goalies (via Selenium)...
[GOALIE_SCRAPER] Found 0 matchup blocks.
```
The scraper logic (Selenium + Soup) is currently unable to parse the DailyFaceoff page (likely DOM change or blocking). **However, the injection pipeline is functionally complete.**

### C. Pipeline Consumption (Verified)
`systemctl start nhl-totals-run`
```
2026-01-27 14:09:10 [OPS] ✅ Loaded 13 games from snapshot.
2026-01-27 14:09:10 [PROOF] NHL_TOTALS_V2_ACTIVE ...
```
Pipeline runs successfully with the new structure. No crashes despite empty data.

## 3. Next Steps
- **Goalie Source Repair**: The `data.sources.nhl_goalies` module requires an update to match the current DailyFaceoff DOM structure.
- **Immediate Impact**: Moneyline V2 continues to run in "Fallback Mode" (using League Average stats for unknown starters). Totals V2 is unaffected.
