
import pandas as pd
import numpy as np
from db.connection import get_db

def build_assist_features():
    print("🛠 Building NHL Assist Features...")
    conn = get_db()
    
    # 1. Load Player Logs
    query = """
        SELECT game_id, player_id, player_name, team, opponent, game_date, 
               assists, toi_seconds, pp_toi, is_home, goals
        FROM public.nhl_player_game_logs
        ORDER BY game_date ASC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    
    df['game_date'] = pd.to_datetime(df['game_date'])
    df['toi_minutes'] = df['toi_seconds'] / 60.0
    
    # 2. Team Scoring Context (Rolling)
    # Agg Team Goals per Game
    team_stats = df.groupby(['team', 'game_date'])['goals'].sum().reset_index()
    team_stats = team_stats.rename(columns={'goals': 'team_goals'})
    team_stats = team_stats.sort_values(['team', 'game_date'])
    
    # Rolling Team Goals L10
    team_stats['team_goals_L10'] = team_stats.groupby('team')['team_goals'].shift(1).rolling(10, min_periods=1).mean()
    
    # Merge back to Player
    df = pd.merge(df, team_stats[['team', 'game_date', 'team_goals_L10']], on=['team', 'game_date'], how='left')
    
    # 3. Player Rolling Stats
    df = df.sort_values(['player_id', 'game_date'])
    
    cols_to_roll = ['assists', 'toi_minutes', 'pp_toi']
    
    rolling = df.groupby('player_id')[cols_to_roll].shift(1).rolling(10, min_periods=1)
    
    df['assists_L10'] = rolling['assists'].mean() # Count per game
    df['toi_L10'] = rolling['toi_minutes'].mean()
    df['pp_toi_L10'] = rolling['pp_toi'].mean()
    
    # Rate: Assists / 60
    # Note: Sum(Assists) / Sum(TOI) * 60 is better than Mean(Assists/TOI)
    # Let's do Sum Rolls
    r_sum = df.groupby('player_id')[cols_to_roll].shift(1).rolling(10, min_periods=1).sum()
    
    df['assists_per_60_L10'] = (r_sum['assists'] / r_sum['toi_minutes'].replace(0, np.nan)) * 60
    
    # Fill NAs
    df['assists_per_60_L10'] = df['assists_per_60_L10'].fillna(0) # Rookie assumption
    df['team_goals_L10'] = df['team_goals_L10'].fillna(3.0) # League avg
    df['toi_L10'] = df['toi_L10'].fillna(15.0)
    
    # 4. Save
    cols = [
        'game_id', 'player_id', 'player_name', 'game_date',
        'assists', 'assists_per_60_L10', 'toi_L10', 'team_goals_L10', 'is_home'
    ]
    
    out = df[cols].dropna(subset=['game_date'])
    outfile = "data/nhl_processed/assists_features.parquet"
    out.to_parquet(outfile)
    print(f"💾 Assist Features Saved: {len(out)} rows.")

if __name__ == "__main__":
    build_assist_features()
