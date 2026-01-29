# NHL Phase 2 Totals - Feature Design & Leakage Audit (Clean Room)

## 1. Objective
Define the feature engineering strategy for the NHL Totals v2 model. 
**Constraint**: Strict clean-room implementation. No features may contain data from the *current* game being predicted (Leakage 0).

## 2. Target Variable
- **Name**: `total_goals`
- **Source**: MoneyPuck `games` table.
- **Formula**: `goalsFor + goalsAgainst` (From the perspective of Home Team). inclusive of OT/SO.
- **Leakage Status**: **TARGET** (Forbidden as input).

## 3. Feature Inventory

### A. Advanced Metrics (Rolling Windows)
*Calculated for Home and Away teams separately, then joined.*
*Windows: Last 10 Games (L10) and Season-to-Date (STD).*

| Feature Name | Source Column (MoneyPuck) | Formula (Rolling Mean) | Shift Rule | Leakage Risk |
|--------------|---------------------------|------------------------|------------|--------------|
| `rolling_xg_L10` | `xGoalsFor` | Mean(L10) | **SHIFT 1** | LOW |
| `rolling_xga_L10` | `xGoalsAgainst` | Mean(L10) | **SHIFT 1** | LOW |
| `rolling_goals_L10` | `goalsFor` | Mean(L10) | **SHIFT 1** | LOW |
| `rolling_ga_L10` | `goalsAgainst` | Mean(L10) | **SHIFT 1** | LOW |
| `rolling_corsi_pct_L10` | `corsiPercentage` | Mean(L10) | **SHIFT 1** | LOW |
| `rolling_fenwick_pct_L10` | `fenwickPercentage` | Mean(L10) | **SHIFT 1** | LOW |
| `rolling_high_danger_xG_L10` | `highDangerxGoalsFor` | Mean(L10) | **SHIFT 1** | LOW |
| `rolling_high_danger_goals_L10` | `highDangerGoalsFor` | Mean(L10) | **SHIFT 1** | LOW |
| `rolling_powerplay_opportunities_L10` | `penaltiesAgainst` (drawn) | Mean(L10) | **SHIFT 1** | LOW |
| `rolling_save_pct_L10` | `savedShotsOnGoalFor` / `shotsOnGoalAgainst` | Calc(L10) | **SHIFT 1** | LOW |
| `rolling_shooting_pct_L10` | `goalsFor` / `shotsOnGoalFor` | Calc(L10) | **SHIFT 1** | LOW |

### B. Schedule & Context Features (Static/Pre-Match)
*Derived from Game Metadata.*

| Feature Name | Formula | Leakage Risk |
|--------------|---------|--------------|
| `days_rest_home` | `Date(Game) - Date(PrevGame_Home)` | NONE |
| `days_rest_away` | `Date(Game) - Date(PrevGame_Away)` | NONE |
| `is_b2b_home` | `days_rest_home == 1` | NONE |
| `is_b2b_away` | `days_rest_away == 1` | NONE |
| `season_month` | Month(Date) | NONE |
| `home_is_traveling_b2b` | `is_b2b_home` AND `PrevGame_Home != Home` | NONE |

### C. Market Features (Reference)
*Derived from Odds API Closing Lines.*

| Feature Name | Source | Leakage Risk |
|--------------|--------|--------------|
| `obs_total_line` | `total_line_close` | NONE (Pre-Puck Drop) |
| `obs_over_price` | `over_price_close` | NONE |
| `obs_under_price` | `under_price_close` | NONE |
| `implied_total_prob` | Derived from prices | NONE |

## 4. Leakage Prevention Strategy
### Rule 1: The "Shift 1" Invariant
All rolling features must be calculated on the dataframe sorted by Date.
`df['feature'] = df['raw_stat'].rolling(window).mean().shift(1)`
- **Verification**: `df.iloc[0]['feature']` MUST be NaN (First game of season has no history).

### Rule 2: Blind Date Join
Pre-match features must be joined to the Target dataframe on `GameID` (or `Date` + `Team`).
The feature calculation pipeline must strictly separate "Inputs" (Past Games) from "Target" (Current Game).

## 5. Implementation Plan
1. **Load**: MoneyPuck Data.
2. **Sort**: By Team, then Date.
3. **Compute**: Rolling features with `shift(1)`.
4. **Join**: Merge Home Features + Away Features + Odds/Apparent Target.
5. **Output**: `Hockey Data/nhl_totals_features_v1.csv`
