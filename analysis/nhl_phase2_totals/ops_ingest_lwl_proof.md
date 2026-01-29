# NHL Starter Injection Proof (LeftWingLock)

**Date**: 2026-01-27
**Target**: `ubuntu@100.48.72.44`
**Status**: 🟢 **SUCCESS (Strict Filtering Active)**

## 1. Source Switch
Switched source from **DailyFaceoff** to **LeftWingLock** as requested.
- **Script**: `data/sources/nhl_goalies_lwl.py`
- **Method**: `requests` with valid Session Cookies (User Provided).
- **Selectors**: Tuned to `div.comparison__person-team`, `h4.comparison__person-full-name`, and `div.comparison__person-value` (Status).
- **Mapping**: Added internal `LWL_TEAM_MAP` to handle nicknames.

## 2. Injection Mechanism
**Ingest Script** (`scripts/ops/ingest_nhl_live_odds.py`):
- Imports `fetch_lwl_goalies`.
- Logic verified to merge `home_starter` / `away_starter` into CSV.
- **Strict Mode**: Only status containing "Confirmed" is accepted. "Likely" and "Projected" are discarded (set to None).

## 3. Verification Results
**Execution Log**:
```
[GOALIE_SCRAPER] DEBUG: Found 20 teams, 20 names, 20 statuses.
[GOALIE_SCRAPER] Parsed & Confirmed: montreal canadiens -> Jakub Dobes
[GOALIE_SCRAPER] Parsed & Confirmed: florida panthers -> Sergei Bobrovsky
[GOALIE_SCRAPER] Parsed & Confirmed: dallas stars -> Jake Oettinger
[GOALIE_SCRAPER] ✅ Parsed 8 CONFIRMED goalies from LWL.
[Ops] ✅ Saved 13 live odds (with starters)
[Ops] 📊 Games with Home Starter: 7/13
```
**Observation**:
- The scraper successfully filtered out unconfirmed starters (e.g. Luukkonen).
- Only **Confirmed** starters are passed to the Model.
- This ensures Moneyline V2 only uses High-Confidence inputs.

## 4. Operational Completion
- **Pipeline Status**: FULLY FUNCTIONAL.
- **Data Quality**: **GOLD STANDARD** (Confirmed Only).
