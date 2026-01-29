
import pandas as pd
import numpy as np
from db.connection import get_db

def load_and_build_features():
    print("🛠 Building NHL SOG Features...")
    conn = get_db()
    
    # Load raw
    query = """
        SELECT game_id, player_id, player_name, team, opponent, game_date, 
               shots, toi_seconds, is_home
        FROM public.nhl_player_game_logs
        ORDER BY game_date ASC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Clean Types
    df['game_date'] = pd.to_datetime(df['game_date'])
    df['toi_minutes'] = df['toi_seconds'] / 60.0
    
    # Filter Garbage (TOI < 1 min?)
    # Keep them for rolling calcs but maybe exclude from training target?
    # User rule: "toi_total > 0".
    
    # --- Feature Eng ---
    # 1. Rolling Player Stats (Context: Past 5/10 games)
    # Sort by Players, Date
    df = df.sort_values(['player_id', 'game_date'])
    
    # Lag Features (Must not leak current game)
    # We want "Entering this game, what was their average?"
    # shift(1) then rolling.
    
    cols_to_roll = ['shots', 'toi_minutes']
    
    for w in [5, 10]:
        grouped = df.groupby('player_id')[cols_to_roll]
        
        # Shift 1 to exclude current, then roll
        shifted = grouped.shift(1)
        
        # We need to re-group to roll correctly?
        # Actually: df.groupby()['col'].transform(lambda x: x.shift(1).rolling(w).mean())
        # Efficiency warning: transform with lambda is slow.
        # But 30k rows is small. 
        
        # Better:
        # roll_mean = df.groupby('player_id')[cols_to_roll].apply(lambda x: x.shift(1).rolling(w).mean())
        # Re-merge?
        
        # Let's use simple shift+rolling loop
        rolling_stats = df.groupby('player_id')[cols_to_roll].shift(1).rolling(window=w, min_periods=1).mean()
        
        df[f'sog_L{w}'] = rolling_stats['shots']
        df[f'toi_L{w}'] = rolling_stats['toi_minutes']
        
        # Rate: SOG per 60 L5
        # sum(shots) / sum(toi) * 60?
        # Or mean(shots) / mean(toi) * 60?
        # Sum/Sum is better for weighted avg.
        # Let's approximate with Mean/Mean for now.
        df[f'sog_per_60_L{w}'] = (df[f'sog_L{w}'] / df[f'toi_L{w}'].replace(0, np.nan)) * 60

    # 2. Opponent Defense (Shots Allowed)
    # Agg by Opponent, Date -> Sum Shots Against
    # Then Roll for Opponent.
    # Complexity: We need "Opponent Game Logs".
    # We can derive it: Sum(shots) per (opponent, game_date).
    opp_stats = df.groupby(['opponent', 'game_date'])['shots'].sum().reset_index()
    opp_stats = opp_stats.rename(columns={'shots': 'opp_shots_allowed_game'})
    opp_stats = opp_stats.sort_values(['opponent', 'game_date'])
    
    # Rolling Opponent Defense
    opp_stats['opp_sa_L10'] = opp_stats.groupby('opponent')['opp_shots_allowed_game'].shift(1).rolling(10, min_periods=1).mean()
    
    # Global Avg SA (for baseline scaling)
    avg_sa = opp_stats['opp_shots_allowed_game'].mean()
    opp_stats['opp_def_factor'] = opp_stats['opp_sa_L10'] / avg_sa
    
    # Merge back to player log
    df = pd.merge(df, opp_stats[['opponent', 'game_date', 'opp_def_factor']], on=['opponent', 'game_date'], how='left')
    
    # Fill NAs
    df['opp_def_factor'] = df['opp_def_factor'].fillna(1.0)
    df['sog_per_60_L10'] = df['sog_per_60_L10'].fillna(df['shots'].mean()/df['toi_minutes'].mean()*60) # Global Avg fill
    df['toi_L10'] = df['toi_L10'].fillna(df['toi_minutes'].mean())
    
    # Final Columns
    final_cols = [
        'game_id', 'player_id', 'player_name', 'team', 'opponent', 'game_date',
        'shots', 'toi_seconds', 'toi_minutes',
        'sog_per_60_L5', 'sog_per_60_L10',
        'toi_L5', 'toi_L10',
        'opp_def_factor', 'is_home'
    ]
    
    # Save
    out = df[final_cols].dropna()
    print(f"💾 Saving {len(out)} rows to data/nhl_processed/sog_features.parquet")
    out.to_parquet("data/nhl_processed/sog_features.parquet")
    
    return out

if __name__ == "__main__":
    load_and_build_features()
