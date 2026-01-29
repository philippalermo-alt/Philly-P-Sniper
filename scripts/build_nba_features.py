import pandas as pd
import numpy as np
from db.connection import get_db, safe_execute
from config.settings import Config
from datetime import timedelta

# Usage: python3 scripts/build_nba_features.py

def load_data():
    print("⏳ Loading Games & Odds...")
    conn = get_db()
    
    # Load Games
    # We need: game_id, date, teams, basic box score stats (efg, tov, orb, etc)
    query_games = """
        SELECT 
            game_id, game_date, season_id, game_start_time,
            home_team_id, home_team_name, away_team_id, away_team_name,
            home_score, away_score, 
            home_efg_pct, away_efg_pct, home_tov_pct, away_tov_pct, 
            home_orb_pct, away_orb_pct, pace,
            home_3par, away_3par
        FROM nba_historical_games
        ORDER BY game_date ASC
    """
    df_games = pd.read_sql(query_games, conn)
    # We want ONE row per game_id.
    # Logic: Prioritize Pinnacle. If missing, take DraftKings.
    # We do this via DISTINCT ON game_id ORDER BY preference.
    query_odds = """
        SELECT DISTINCT ON (game_id)
            game_id, 
            bookmaker,
            -- Pivot markets if possible, or just raw rows?
            -- It's easier to verify coverage if we join in Python or careful SQL.
            -- Let's fetch all relevant odds and process in Pandas.
            market_key, home_price, home_point, away_price, away_point
        FROM nba_historical_odds
        WHERE bookmaker IN ('pinnacle', 'draftkings')
        ORDER BY game_id, 
                 CASE WHEN bookmaker='pinnacle' THEN 1 ELSE 2 END
    """
    # Wait, fetching "DISTINCT ON game_id" only gives ONE market (e.g. h2h) per game.
    # We need ALL markets (h2h, spreads, totals) for the preferred book.
    # Correct SQL:
    query_odds_full = """
        SELECT 
            game_id, bookmaker, market_key, 
            home_price, home_point, away_price, away_point
        FROM nba_historical_odds
        WHERE bookmaker IN ('pinnacle', 'draftkings')
    """
    df_odds = pd.read_sql(query_odds_full, conn)
    
    conn.close()
    print(f"   Games: {len(df_games)}, Odds Rows: {len(df_odds)}")
    return df_games, df_odds

def process_odds(df_odds):
    """
    Pivot odds to get ONE row per game with columns using best available bookmaker.
    """
    # Filter: Map priority
    df_odds['priority'] = df_odds['bookmaker'].map({'pinnacle': 1, 'draftkings': 2, 'fanduel': 3}).fillna(99)
    
    # Robust Selection: Sort by Game, Market, Priority (Ascending)
    # This brings the best bookmaker for each market to the top.
    df_sorted = df_odds.sort_values(['game_id', 'market_key', 'priority'])
    
    # Deduplicate: Keep FIRST occurrence (Best Book) for each market type per game
    df_best = df_sorted.drop_duplicates(subset=['game_id', 'market_key'], keep='first')
    
    # Pivot to Wide Format
    # We want columns like: h2h_home_price, spreads_home_point, etc.
    # Pivot table is cleanest.
    pivot = df_best.pivot(index='game_id', columns='market_key', values=['home_price', 'away_price', 'home_point', 'away_point', 'bookmaker'])
    
    # Flatten Hierarchical Index
    pivot.columns = [f"{c[1]}_{c[0]}" if c[1] else c[0] for c in pivot.columns]
    pivot.reset_index(inplace=True)
    
    # Rename for clarity to match expected schema
    # Expected: ml_home, ml_away, spread_line, total_line, etc.
    # Current Mappings from Pivot:
    # h2h_home_price -> ml_home
    # spreads_home_point -> spread_line
    # totals_home_point -> total_line (Be careful with Over/Under mapping fixed in fetcher)
    
    clean_df = pd.DataFrame()
    clean_df['game_id'] = pivot['game_id']
    
    # Moneyline
    if 'h2h_home_price' in pivot:
        clean_df['ml_home'] = pivot.get('h2h_home_price')
        clean_df['ml_away'] = pivot.get('h2h_away_price')
        clean_df['ml_book'] = pivot.get('h2h_bookmaker')
        
    # Spreads
    if 'spreads_home_point' in pivot:
        clean_df['spread_line'] = pivot.get('spreads_home_point')
        clean_df['spread_home_odds'] = pivot.get('spreads_home_price')
        clean_df['spread_away_odds'] = pivot.get('spreads_away_price')
        clean_df['spread_book'] = pivot.get('spreads_bookmaker')
        
    # Totals
    if 'totals_home_point' in pivot:
        # Note: In fetcher, we mapped Over -> Home Price/Point.
        # So totals_home_point IS the Over Line? Usually Total Line is same for O/U.
        clean_df['total_line'] = pivot.get('totals_home_point')
        clean_df['total_over_odds'] = pivot.get('totals_home_price')
        clean_df['total_under_odds'] = pivot.get('totals_away_price')
        clean_df['total_book'] = pivot.get('totals_bookmaker')
        
    return clean_df

def calculate_rolling_stats(df_games):
    """
    Calculate Pre-Match rolling stats for every game.
    """
    # 1. Melt to Team-Game level (2 rows per game: 1 for Home, 1 for Away)
    # This makes rolling easy.
    
    # Home Perspective
    df_h = df_games.copy()
    df_h['team_id'] = df_h['home_team_id']
    df_h['opp_id'] = df_h['away_team_id']
    df_h['is_home'] = 1
    df_h['points'] = df_h['home_score']
    df_h['opp_points'] = df_h['away_score']
    df_h['efg'] = df_h['home_efg_pct']
    df_h['tov'] = df_h['home_tov_pct']
    df_h['orb'] = df_h['home_orb_pct']
    df_h['pace'] = df_h['pace']
    df_h['3par'] = df_h['home_3par'] # New
    df_h['opp_efg'] = df_h['away_efg_pct'] # Opponent defense
    df_h['opp_tov'] = df_h['away_tov_pct'] # For Matchups
    df_h['opp_orb'] = df_h['away_orb_pct'] # For Matchups
    df_h['opp_3par'] = df_h['away_3par'] # Opponent 3PAr Allowed
    
    # Away Perspective
    df_a = df_games.copy()
    df_a['team_id'] = df_a['away_team_id']
    df_a['opp_id'] = df_a['home_team_id']
    df_a['is_home'] = 0
    df_a['points'] = df_a['away_score']
    df_a['opp_points'] = df_a['home_score']
    df_a['efg'] = df_a['away_efg_pct']
    df_a['tov'] = df_a['away_tov_pct']
    df_a['orb'] = df_a['away_orb_pct']
    df_a['pace'] = df_a['pace'] # Game pace is same
    df_a['3par'] = df_a['away_3par'] # New
    df_a['opp_efg'] = df_a['home_efg_pct']
    df_a['opp_tov'] = df_a['home_tov_pct']
    df_a['opp_orb'] = df_a['home_orb_pct']
    df_a['opp_3par'] = df_a['home_3par'] # Opponent 3PAr Allowed

    # Stack
    cols = ['game_id', 'game_date', 'season_id', 'team_id', 'is_home', 
            'points', 'opp_points', 'efg', 'tov', 'orb', 'pace', 
            'opp_efg', 'opp_tov', 'opp_orb', '3par', 'opp_3par']
    df_long = pd.concat([df_h[cols], df_a[cols]]).sort_values(['team_id', 'game_date'])
    
    # Force Datetime
    df_long['game_date'] = pd.to_datetime(df_long['game_date'])
    
    # 2. Rolling Calculations
    # Group by Team, shift(1) to ensure we only see PAST games.
    
    metrics = ['efg', 'tov', 'orb', 'pace', 'points', 'opp_points', 'opp_efg', 'opp_tov', 'opp_orb', '3par', 'opp_3par']
    windows = [3, 5, 10]
    
    for w in windows:
        for m in metrics:
            col_name = f'roll_{w}_{m}'
            # Shift 1 to exclude current, then roll
            df_long[col_name] = df_long.groupby('team_id')[m].transform(lambda x: x.shift(1).rolling(window=w, min_periods=1).mean())
            
    # Season-to-Date Avg (expanding)
    for m in metrics:
        col_name = f'sea_{m}'
        df_long[col_name] = df_long.groupby(['team_id', 'season_id'])[m].transform(lambda x: x.shift(1).expanding().mean())
    
    # Rest Days
    df_long['prev_date'] = df_long.groupby('team_id')['game_date'].shift(1)
    df_long['rest_days'] = (df_long['game_date'] - df_long['prev_date']).dt.days.fillna(7) # Default 7 for opener
    
    # --- PHASE 5: SCHEDULE STRESS FEATURES ---
    # 1. Back-to-Back
    df_long['is_b2b'] = (df_long['rest_days'] == 1).astype(int)
    
    # 2. Games Frequency (3 in 4, 5 in 7, etc)
    # Use rolling time window. Requires Datetime Index.
    # We must operate per group.
    
    def calc_freq(x, days):
        # Rolling count of games in last 'days'. Closed='right' (includes today).
        # We want to know stress ENTERING the game. 
        # So we should shift? No, "Games in last 5 days including today" is the metric.
        # If I played today, yesterday, and 2 days ago -> 3 games in 3 days.
        return x.rolling(window=f'{days}D', min_periods=0).count()

    # Set index for rolling
    df_long = df_long.set_index('game_date')
    
    df_long['games_in_5'] = df_long.groupby('team_id')['game_id'].transform(lambda x: calc_freq(x, 5))
    df_long['games_in_7'] = df_long.groupby('team_id')['game_id'].transform(lambda x: calc_freq(x, 7))
    
    # Reset index to keep game_date as column
    df_long = df_long.reset_index()
    
    return df_long

def main():
    df_games, df_odds = load_data()
    
    # 1. Process Odds
    print("🎲 Processing Odds...")
    df_odds_clean = process_odds(df_odds)
    
    # 2. Process Features
    print("⚙️ Engineering Features...")
    df_features = calculate_rolling_stats(df_games)
    
    # 3. Join Back to Game Level (Home Features + Away Features)
    # We want a row per game: game_id, Home_Roll5_EFG, Away_Roll5_EFG...
    
    flat_home = df_features[df_features['is_home'] == 1].set_index('game_id')
    flat_away = df_features[df_features['is_home'] == 0].set_index('game_id')
    
    # Rename Cols to distinguish
    flat_home.columns = [f'h_{c}' if c not in ['game_date', 'season_id'] else c for c in flat_home.columns]
    flat_away.columns = [f'a_{c}' if c not in ['game_date', 'season_id'] else c for c in flat_away.columns]
    
    # Merge (Left Join to keep all games, even if odds missing)
    # We keep game_date from home
    model_df = flat_home.join(flat_away, lsuffix='_H', rsuffix='_A')
    
    # Phase 6: MATCHUP FEATURES
    # 1. Rebound Mismatch: h_sea_orb + a_sea_opp_orb
    # (Proxy for Home ORB strength vs Away Defensive Rebounding weakness)
    model_df['reb_mismatch'] = model_df['h_sea_orb'] + model_df['a_sea_opp_orb']
    
    # 2. Turnover Advantage (Phase 2 - FAILED): h_sea_opp_tov + a_sea_tov
    # High Home Pressure (Forced TOV) + High Away Sloppiness (TOV) = High Home Advantage (Chaos/Steals)
    model_df['tov_adv'] = model_df['h_sea_opp_tov'] + model_df['a_sea_tov']
    
    # 3. 3-Point Mismatch (Phase 3): h_sea_3par + a_sea_opp_3par
    # Home Vol + Away Allowed Vol = Shootout Advantage?
    model_df['threept_mismatch'] = model_df['h_sea_3par'] + model_df['a_sea_opp_3par']
    
    # 4. Join Odds
    print("🔗 Joining Odds & Targets...")
    final_df = model_df.join(df_odds_clean.set_index('game_id'), how='left')
    
    # 5. Determine Targets
    # Margin
    final_df['margin'] = final_df['h_points'] - final_df['a_points']
    final_df['total_points'] = final_df['h_points'] + final_df['a_points']
    
    # Win (Moneyline)
    final_df['target_win'] = (final_df['margin'] > 0).astype(int)
    
    # Cover (Spread) - Only if line exists
    # If spread_line is NaN, target_cover will be False (0) or NaN?
    # Pandas Series comparison with NaN results in False usually.
    # We want it to be NaN if line is missing, so we can filter during training.
    # But for now let's just calc it.
    
    has_spread = final_df['spread_line'].notna()
    final_df.loc[has_spread, 'target_cover'] = ((final_df.loc[has_spread, 'margin'] + final_df.loc[has_spread, 'spread_line']) > 0).astype(int)
    
    # Total Target
    has_total = final_df['total_line'].notna()
    final_df.loc[has_total, 'target_over'] = (final_df.loc[has_total, 'total_points'] > final_df.loc[has_total, 'total_line']).astype(int)
    
    # Push handling? For now binary.
    
    # Push handling? For now binary.
    
    # Save to DB (Use SQLAlchemy for robust types)
    print(f"💾 Saving {len(final_df)} rows to 'nba_model_train'...")
    
    from sqlalchemy import create_engine
    engine = create_engine(Config.DATABASE_URL)
    
    # Create Table Schema if needed (Automated by to_sql if mostly numeric, but safer to specify PK)
    final_df.to_sql('nba_model_train', engine, if_exists='replace', index=True)
    
    # Add Primary Key
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("ALTER TABLE nba_model_train ADD PRIMARY KEY (game_id)")
        conn.commit()
    except:
        pass
        
    print("✅ Feature Engineering Complete.")

if __name__ == "__main__":
    main()
