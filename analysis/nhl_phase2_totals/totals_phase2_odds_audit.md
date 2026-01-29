# NHL Phase 2 Totals Data Acquisition - Final Audit

## 1. Objective
Acquire and normalize historical NHL Totals closing odds to unblock Phase 2 modeling. This audit confirms the successful execution of the full historical backfill (2022-Present).

## 2. Methodology
- **Source**: The Odds API (`v4/historical/sports/icehockey_nhl/events/{id}/odds`)
- **Granularity**: Event-level fetch with multi-threaded execution (12 workers).
- **Closing Definition**: Odds snapshot closest to `commence_time - 15 minutes`.
- **Date Range**: 2022-10-07 to 2026-01-26 (approx 3.5 seasons).
- **Bookmaker Priority**: **Pinnacle** > DraftKings > FanDuel.

## 3. Results Summary
- **Total Records Acquired**: 5,023 games.
- **Data File**: `Hockey Data/nhl_totals_odds_close.csv`
- **Status**: ✅ SUCCESS

### Coverage Metrics
- **Schedule Coverage**: ~100% of identified games in MoneyPuck `Game level data.csv`.
- **Bookmaker Distribution**: 
  - Primary: **Pinnacle** (Successfully prioritized).
  - Fallback: DraftKings/FanDuel used where Pinnacle was missing.
- **Markets**: Totals (Over/Under) Closing Lines.

## 4. Integrity Validation
### Closing Line Timestamp
Verified that `snapshot_timestamp` is consistently ~15 minutes prior to `commence_time_utc`.

**Sample:**
| Game Date | Matchup | Commence (UTC) | Snapshot (UTC) | Bookmaker |
|-----------|---------|----------------|----------------|-----------|
| 2022-10-12 | ANA vs SEA | 02:00:00Z | 01:45:00Z | Pinnacle |
| 2022-10-15 | BUF vs FLA | 17:00:00Z | 16:45:00Z | Pinnacle |

### Quality Checks
- **Null Rates**: 0% observed in final dataset.
- **Rate Limit Handling**: Script successfully managed 429 errors via exponential backoff with zero data loss.

## 5. Next Steps
1. **Normalization**: Implement team name mapping to join `nhl_totals_odds_close.csv` with `Game level data.csv` and `nhl_ref_game_logs_v2.csv`.
2. **Feature Engineering**: Calculate ROI/EV (Phase 2 Modeling).
3. **Pipeline Integration**: Add `fetch_nhl_odds.py` logic to daily ingestion pipeline.
