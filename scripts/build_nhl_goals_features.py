
import pandas as pd
import numpy as np
from db.connection import get_db

def build_goals_features():
    print("🛠 Building NHL Goal Features...")
    conn = get_db()
    
    # 1. Load Player Logs
    print("  Loading Player Logs...")
    p_query = """
        SELECT game_id, player_id, player_name, team, opponent, game_date, 
               goals, shots, toi_seconds, ixg, pp_toi, is_home
        FROM public.nhl_player_game_logs
        WHERE toi_seconds > 0
    """
    df = pd.read_sql(p_query, conn)
    
    # 2. Load Goalie Logs (Starters)
    print("  Loading Goalie Logs...")
    g_query = """
        SELECT game_id, team, goalie_name, game_date, saves, shots_against
        FROM public.nhl_goalie_game_logs
        WHERE is_starter = TRUE
    """
    g_df = pd.read_sql(g_query, conn)
    g_df['game_date'] = pd.to_datetime(g_df['game_date'])
    
    conn.close()
    
    # 3. Derive Goalie Prior Context (Rolling L10)
    print("  Computing Goalie Priors...")
    g_df = g_df.sort_values(['goalie_name', 'game_date'])
    
    g_df['rolling_saves'] = g_df.groupby('goalie_name')['saves'].shift(1).rolling(10, min_periods=1).sum()
    g_df['rolling_sa'] = g_df.groupby('goalie_name')['shots_against'].shift(1).rolling(10, min_periods=1).sum()
    
    g_df['opp_goalie_sv_pct'] = g_df['rolling_saves'] / g_df['rolling_sa'].replace(0, np.nan)
    
    # Fill defaults (League avg .900 if no history)
    g_df['opp_goalie_sv_pct'] = g_df['opp_goalie_sv_pct'].fillna(0.900)
    
    # Prepare for Merge
    # We join on GameID and Team (Limit to Starters)
    # G_DF columns: game_id, team, opp_goalie_sv_pct
    g_context = g_df[['game_id', 'team', 'opp_goalie_sv_pct', 'goalie_name']].rename(columns={
        'team': 'opponent', 
        'goalie_name': 'opp_goalie'
    })
    
    # Dedupe (in case multiple goalies marked starter? shouldn't happen but be safe)
    g_context = g_context.drop_duplicates(subset=['game_id', 'opponent'])
    
    # Merge
    print("  Merging Context...")
    merged = pd.merge(df, g_context, on=['game_id', 'opponent'], how='left')
    
    # Fill missing goalie info (League Avg)
    merged['opp_goalie_sv_pct'] = merged['opp_goalie_sv_pct'].fillna(0.900)
    merged['opp_goalie'] = merged['opp_goalie'].fillna("Unknown")
    
    # 4. Feature Eng
    # ixg_per_shot (Shot Quality)
    # If shots=0, ixg/shot = 0.
    merged['ixg_per_shot'] = merged['ixg'] / merged['shots'].replace(0, np.nan)
    merged['ixg_per_shot'] = merged['ixg_per_shot'].fillna(0)
    
    # Rolling ixg_per_shot (Talent)
    # Group by Player, Rolling 10
    merged = merged.sort_values(['player_id', 'game_date'])
    merged['ixg_per_shot_L10'] = merged.groupby('player_id')['ixg_per_shot'].shift(1).rolling(10, min_periods=1).mean()
    
    # Shooting Percentage L10 (Actual Conversion Talent)
    # Sum(Goals)/Sum(Shots)
    # Rolling Sums
    # r_goals = merged.groupby('player_id')['goals'].shift(1).rolling(10).sum()
    # r_shots = merged.groupby('player_id')['shots'].shift(1).rolling(10).sum()
    # merged['sh_pct_L10'] = r_goals / r_shots.replace(0, np.nan)
    
    # PP Share
    merged['pp_share'] = merged['pp_toi'] / merged['toi_seconds']
    # Rolling PP Share
    merged['pp_share_L10'] = merged.groupby('player_id')['pp_share'].shift(1).rolling(10, min_periods=1).mean()
    
    # Fill NAs
    merged['ixg_per_shot_L10'] = merged['ixg_per_shot_L10'].fillna(merged['ixg_per_shot'].mean())
    merged['pp_share_L10'] = merged['pp_share_L10'].fillna(0)
    
    # 5. Save
    cols = [
        'game_id', 'player_id', 'player_name', 'game_date',
        'goals', 'shots', 'ixg', 
        'ixg_per_shot_L10', 'pp_share_L10', 'opp_goalie_sv_pct', 'is_home'
    ]
    
    out = merged[cols]
    outfile = "data/nhl_processed/goals_features.parquet"
    out.to_parquet(outfile)
    print(f"💾 Goal Features Saved: {len(out)} rows.")

if __name__ == "__main__":
    build_goals_features()
