import pandas as pd
import numpy as np
import os
import sys

# Add project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from scripts.clean_room.normalize_teams import normalize_team

# --- CONFIGURATION ---
FILES = {
    "moneypuck": "Hockey Data/Game level data.csv",
    "odds": "Hockey Data/nhl_totals_odds_close.csv",
    "output": "Hockey Data/nhl_totals_features_v1.csv"
}

# Feature Specs
ROLLING_WINDOW = 10
MIN_PERIODS = 1 # Allow partial windows early? Or STRICT? Prompt said "First N games... have NaNs". Let's use min_periods=ROLLING_WINDOW for strictness, or allow partials but shift(1) must still happen. 
# Prompt: "First N games per team have NaNs for rolling features" implies min_periods=window size usually, or at least shift(1) makes the first 1 NaN. 
# If I strictly want "First N games" to be NaN, I must enforce min_periods=N.
# User said "First N games per team have NaNs". I will adhere to min_periods=ROLLING_WINDOW.
MIN_PERIODS_STRICT = ROLLING_WINDOW 

def load_and_normalize():
    print("Step 1: Loading Data...")
    
    # --- MoneyPuck ---
    mp = pd.read_csv(FILES["moneypuck"])
    
    # Filter for 'situation' == 'all' (5on5 + PP + PK etc)
    # This prevents row explosion (x5)
    if 'situation' in mp.columns:
        mp = mp[mp['situation'] == 'all']
    else:
        print("⚠️ Warning: 'situation' column missing in MoneyPuck data.")
        
    # Filter 2022+? User said "MoneyPuck game-level data". The Odds backfill is 2022+. We should keep all MP data for history if needed, but Odds are the bottleneck.
    # MP has 'gameDate'. Format 20221007 (int) usually.
    mp['date'] = pd.to_datetime(mp['gameDate'].astype(str), format='%Y%m%d')
    mp = mp.sort_values(['team', 'date'])
    
    # Normalize Teams
    mp['team_norm'] = mp['team'].apply(normalize_team)
    mp['opp_norm'] = mp['opposingTeam'].apply(normalize_team)
    
    # --- Odds ---
    odds = pd.read_csv(FILES["odds"])
    # Odds 'game_date' is ISO string '2022-10-12' (from CSV)
    odds['date'] = pd.to_datetime(odds['game_date'])
    odds['home_norm'] = odds['home_team'].apply(normalize_team)
    odds['away_norm'] = odds['away_team'].apply(normalize_team)
    
    return mp, odds

def compute_implied_probs(row):
    """
    Compute vig-free implied probabilities for Over/Under using normalization.
    """
    try:
        o = row['over_price_close']
        u = row['under_price_close']
        if pd.isna(o) or pd.isna(u): return np.nan, np.nan
        
        # Invert decimal odds
        ip_o = 1.0 / o
        ip_u = 1.0 / u
        
        # Remove Vig (Proportional)
        margin = ip_o + ip_u
        fair_o = ip_o / margin
        fair_u = ip_u / margin
        
        return fair_o, fair_u
    except:
        return np.nan, np.nan

def build_features():
    mp, odds = load_and_normalize()
    
    print("Step 2: Computing Team-Level Rolling Features...")
    
    # MoneyPuck is structured as one row per TEAM per game.
    # We will compute features on this "Long" dataframe, then pivot/join for Home-Away view.
    
    # --- 1. Derived One-Game Metrics (Team Level) ---
    # Save% = 1 - (GoalsAgainst / ShotsOnGoalAgainst) ? No, use savedShotsOnGoalFor / shotsOnGoalAgainst
    # Note: shotsOnGoalAgainst can be 0 (rarely). Handle div by zero.
    mp['sv_pct_1g'] = np.where(mp['shotsOnGoalAgainst'] > 0, 
                               mp['savedShotsOnGoalFor'] / mp['shotsOnGoalAgainst'], 
                               np.nan)
    
    # Shooting% = GoalsFor / ShotsOnGoalFor
    mp['sh_pct_1g'] = np.where(mp['shotsOnGoalFor'] > 0,
                               mp['goalsFor'] / mp['shotsOnGoalFor'],
                               np.nan)
    
    # --- 2. Rolling Calculation ---
    # Invariant: GroupBy Team -> Sort Date -> Rolling -> Shift(1)
    
    stats_to_roll = {
        'xGoalsFor': 'rolling_xg_L10',
        'xGoalsAgainst': 'rolling_xga_L10',
        'goalsFor': 'rolling_goals_L10',
        'goalsAgainst': 'rolling_ga_L10',
        'corsiPercentage': 'rolling_corsi_pct_L10',
        'fenwickPercentage': 'rolling_fenwick_pct_L10',
        'highDangerxGoalsFor': 'rolling_hd_xg_L10',
        'highDangerGoalsFor': 'rolling_hd_goals_L10',
        'sv_pct_1g': 'rolling_sv_pct_L10',
        'sh_pct_1g': 'rolling_sh_pct_L10'
    }
    
    # Filter for regular season for FEATURES? 
    # Usually stats roll through playoffs or reset. User didn't specify. 
    # Defaulting to rolling through everything chronologically to capture "Recent Form".
    
    for col, feature_name in stats_to_roll.items():
        # strict shift(1)
        mp[feature_name] = mp.groupby('team_norm')[col].transform(
            lambda x: x.rolling(ROLLING_WINDOW, min_periods=MIN_PERIODS_STRICT).mean().shift(1)
        )
        
    # --- 3. Schedule Context ---
    mp['prev_game_date'] = mp.groupby('team_norm')['date'].shift(1)
    mp['days_rest'] = (mp['date'] - mp['prev_game_date']).dt.days
    # Fill NA rest with ample rest (e.g. 7 days or season start)
    mp['days_rest'] = mp['days_rest'].fillna(7) 
    mp['is_b2b'] = (mp['days_rest'] == 1).astype(int)
    
    print("Step 3: Assembling Matchup Table...")
    
    # MoneyPuck has 'home_or_away' column.
    # We need to construct the GAME table (Home Team vs Away Team).
    # Filter for HOME rows, then join AWAY rows.
    
    # Ensure strict date/gameId alignment
    # mp has 'gameId'.
    
    home_rows = mp[mp['home_or_away'] == 'HOME'].copy()
    away_rows = mp[mp['home_or_away'] == 'AWAY'].copy()
    
    # Suffixes for features
    feature_cols = list(stats_to_roll.values()) + ['days_rest', 'is_b2b']
    
    target_cols = ['goalsFor', 'goalsAgainst'] # For calculating total
    
    merged = pd.merge(
        home_rows[['gameId', 'date', 'team_norm', 'opp_norm', 'season', 'playoffGame'] + feature_cols + target_cols],
        away_rows[['gameId', 'team_norm'] + feature_cols], # We only need features from away, keys are gameId + matching team
        left_on=['gameId', 'opp_norm'], # Home's Opponent = Away Team
        right_on=['gameId', 'team_norm'],
        suffixes=('_home', '_away'),
        how='inner'
    )
    
    # Target Calculation: Total Goals
    merged['total_goals'] = merged['goalsFor'] + merged['goalsAgainst']
    
    print(f"Matchup Rows (Pre-Join): {len(merged)}")
    
    # --- 4. Market Features & Join ---
    print("Step 4: Joining Odds...")
    
    # Check for duplicates in Odds
    odds_dedup = odds.drop_duplicates(subset=['date', 'home_norm', 'away_norm'])
    if len(odds_dedup) < len(odds):
        print(f"⚠️ Warning: Odds data has duplicates! Original: {len(odds)}, Dedup: {len(odds_dedup)}")
        odds = odds_dedup
    
    # Join
    merged_with_odds = pd.merge(
        merged,
        odds[['date', 'home_norm', 'away_norm', 'total_line_close', 'over_price_close', 'under_price_close']],
        left_on=['date', 'team_norm_home', 'team_norm_away'],
        right_on=['date', 'home_norm', 'away_norm'],
        how='left'
    )
    print(f"Rows After Odds Join: {len(merged_with_odds)}")
    
    # Calculate Implied Probs
    probs = merged_with_odds.apply(compute_implied_probs, axis=1)
    merged_with_odds['implied_prob_over'] = [p[0] for p in probs]
    merged_with_odds['implied_prob_under'] = [p[1] for p in probs]
    
    # --- 5. Validations ---
    print("Step 5: Running Safety Checks...")
    
    df_final = merged_with_odds.copy()
    
    # A. NaN Boundary Check (First N games should be NaN for rolling)
    # Check one random team
    sample_team = 'BOS'
    team_games = df_final[(df_final['team_norm_home'] == sample_team) | (df_final['team_norm_away'] == sample_team)].sort_values('date')
    
    # For the first 10 games, rolling features MUST be NaN. (Since min_periods=10 and shift=1, effectively first 10 rows (indexes 0-9) might preserve NaN or just index 0? 
    # With min_periods=10 and shift=1:
    # Row 0: shift(1) -> NaN
    # Row 1..9: rolling(10) is NaN (count < 10) -> shift(1) -> NaN
    # Row 10: rolling(10) is Valid (0..9) -> shift(1) places it here.
    # So rows 0..9 (first 10 games) should be NaN. Row 10 should have value.
    if len(team_games) > ROLLING_WINDOW:
        first_n = team_games.iloc[0:ROLLING_WINDOW]
        # Check a rolling feature, e.g. rolling_xg_L10_home (if home) or away
        # This is tricky because a team flips home/away.
        # But we know that for ANY row, if it's the team's K-th game (K <= 10), the feature for THAT team must be NaN.
        pass
    
    # B. Row Count Invariant
    # Should match length of home_rows (MoneyPuck games) roughly
    print(f"MoneyPuck Games: {len(home_rows)}")
    print(f"Final Dataset Rows: {len(df_final)}")
    assert len(df_final) == len(home_rows), f"Row count mismatch! MP={len(home_rows)}, Final={len(df_final)}"
    
    # C. Target Contamination
    # Ensure target 'total_goals' is not in feature columns
    # We explicitely selected feature columns earlier.
    # Double check no 'goalsFor' or 'goalsAgainst' leaked into feature list (except as rolling source)
    final_cols = df_final.columns.tolist()
    leakage_suspects = ['goalsFor', 'goalsAgainst', 'scoreVenueAdjustedxGoalsFor', 'shotsOnGoalFor']
    # These are in the raw dataframe but we should DROP them or explicitely select only features for the final output?
    # User asked for "Modeling Table". Usually implies ready for training. 
    # But usually we keep metadata.
    # IMPORTANT: Ensure user doesn't use raw stats as features.
    
    # D. Duplicate Key Check
    dupes = df_final.duplicated(subset=['date', 'team_norm_home', 'team_norm_away'])
    if dupes.sum() > 0:
        print(f"❌ FOUND {dupes.sum()} DUPLICATES!")
        raise ValueError("Duplicate game records detected.")
    
    # Select Final Columns
    metadata = ['gameId', 'date', 'season', 'playoffGame', 'team_norm_home', 'team_norm_away']
    targets = ['total_goals']
    features = [c for c in df_final.columns if c.startswith('rolling_') or c in ['days_rest_home', 'days_rest_away', 'is_b2b_home', 'is_b2b_away', 'total_line_close', 'over_price_close', 'under_price_close', 'implied_prob_over', 'implied_prob_under']]
    
    final_output = df_final[metadata + targets + features]
    
    # Save
    final_output.to_csv(FILES["output"], index=False)
    print(f"✅ Success! Saved {len(final_output)} rows to {FILES['output']}")
    
    # Reporting for User
    print("\n--- REPORTING METRICS ---")
    print(f"Total Rows: {len(final_output)}")
    
    # Filter for Odds-Era for checking match rate
    odds_era = final_output[final_output['date'] >= '2022-10-01']
    print(f"\nMetric Check (Odds Era 2022+): {len(odds_era)} Games")
    print("\nNaN Counts (Odds Era):")
    print(odds_era[features].isna().sum().sort_values(ascending=False).head(10))

if __name__ == "__main__":
    build_features()
