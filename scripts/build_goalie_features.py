import pandas as pd
import numpy as np
import sys
import os

# Add parent dir to path for module import
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from features_nhl import GoalieGameMap

GAME_DATA_PATH = "Hockey Data/Game level data.csv"
OUTPUT_PATH = "Hockey Data/goalie_strength_features.csv"

def build_features():
    print("🏒 Building Goalie Strength Features (GSAx)...")
    
    # 1. Load Goalie Map (Who started?)
    print("   ... Loading Goalie Map")
    mapper = GoalieGameMap()
    
    # 2. Load Team Game Logs (xGoals data)
    print(f"   ... Loading {GAME_DATA_PATH}")
    try:
        # Load only necessary columns to identify game and get xGA
        # 'situation' == 'all' usually? The file likely has situation breakdowns (5on5, etc).
        # We need "all" situations to match total goals against.
        team_df = pd.read_csv(GAME_DATA_PATH)
        
        # Filter for 'situation' == 'all' if it exists, otherwise assume rows are all
        if 'situation' in team_df.columns:
            team_df = team_df[team_df['situation'] == 'all']
            
        required_cols = ['gameId', 'team', 'gameDate', 'goalsAgainst', 'flurryAdjustedxGoalsAgainst']
        
        # Verify columns exist
        missing = [c for c in required_cols if c not in team_df.columns]
        if missing:
            print(f"❌ Missing columns in Team Data: {missing}")
            return
            
        team_df = team_df[required_cols].copy()
        
        # Normalize Team Abbreviations to match NHL API
        team_map = {
            "S.J": "SJS",
            "N.J": "NJD",
            "T.B": "TBL",
            "L.A": "LAK",
            "MTL": "MTL",
            "WSH": "WSH"
        }
        team_df['team'] = team_df['team'].replace(team_map)
        
        # Rename for clarity
        team_df.rename(columns={
            'flurryAdjustedxGoalsAgainst': 'team_xGA',
            'goalsAgainst': 'team_GA'
        }, inplace=True)
        
    except Exception as e:
        print(f"❌ Error loading Team Data: {e}")
        return

    # 3. Map Goalie to Team-Game
    print("   ... Mapping Goalies to Games")
    
    # We need to apply the mapper. 
    # Since mapper lookup is (str(gameId), teamAbbrev) -> GoalieName
    # We ensure gameId is str
    team_df['gameId'] = team_df['gameId'].astype(str)
    
    def get_goalie(row):
        return mapper.get_starter(row['gameId'], row['team'])
        
    team_df['goalie_name'] = team_df.apply(get_goalie, axis=1)
    
    # Drop rows where we couldnt find a goalie (rare, maybe empty net or data gap)
    initial_len = len(team_df)
    features_df = team_df.dropna(subset=['goalie_name']).copy()
    dropped = initial_len - len(features_df)
    if dropped > 0:
        print(f"   ⚠️  Dropped {dropped} rows with no mapped goalie.")
        
    # 4. Calculate GSAx
    # GSAx = Expected Goals Against - Actual Goals Against
    # Positive GSAx = Good (Saved more than expected)
    # Negative GSAx = Bad (Allowed more than expected)
    features_df['GSAx'] = features_df['team_xGA'] - features_df['team_GA']
    
    print("   ... Calculating Rolling Features")
    
    # Sort for rolling calculation
    features_df = features_df.sort_values(by=['goalie_name', 'gameDate'])
    
    # Group by Goalie and compute rolling stats
    # We want Shifted rolling means (Past Performance predicts Future)
    # So we compute rolling on current row (including current game? No, typically exclude current for strict prediction)
    # But usually "Last 5" includes the previous 5 games.
    # Approach: Calculate Rolling including current, then SHIFT by 1.
    
    def calculate_rolling(group):
        # We calculate closed window, then shift.
        # But pandas rolling is inclusive. 
        # min_periods=1 ensures we get data early.
        
        group['GSAx_L5'] = group['GSAx'].rolling(window=5, min_periods=1).mean().shift(1)
        group['GSAx_L10'] = group['GSAx'].rolling(window=10, min_periods=3).mean().shift(1)
        group['GSAx_Season'] = group['GSAx'].expanding(min_periods=1).mean().shift(1)
        
        # Add basic volume stats
        group['Games_Played'] = group['GSAx'].expanding().count().shift(1).fillna(0)
        
        return group
        
    features_df = features_df.groupby('goalie_name', group_keys=False).apply(calculate_rolling)
    
    # Fill NA for first games (Shift(1) makes first row NaN)
    # We can fill with 0 or NaN. XGBoost handles NaN, but 0 (Average) is safer for GSAx.
    features_df[['GSAx_L5', 'GSAx_L10', 'GSAx_Season']] = features_df[['GSAx_L5', 'GSAx_L10', 'GSAx_Season']].fillna(0)
    
    # Select final columns
    final_df = features_df[['gameId', 'gameDate', 'team', 'goalie_name', 'GSAx', 'GSAx_L5', 'GSAx_L10', 'GSAx_Season', 'Games_Played']]
    
    # Save
    final_df.to_csv(OUTPUT_PATH, index=False)
    print(f"✅ Saved Features to {OUTPUT_PATH}")
    print(f"📊 Rows: {len(final_df)}")
    print("🔍 Sample:")
    print(final_df.tail(5))
    
    return final_df

if __name__ == "__main__":
    build_features()
