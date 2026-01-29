import pandas as pd
import numpy as np
import os

TEAM_LOGS_PATH = "Hockey Data/Game level data.csv"
GOALIE_FEATURES_PATH = "Hockey Data/goalie_strength_features.csv"
OUTPUT_PATH = "Hockey Data/training_set_v2.csv"

def assemble_dataset():
    print("🏗️  Assembling NHL Training Set (v2)...")
    
    # 1. Load Team Logs
    print(f"   ... Loading Team Logs: {TEAM_LOGS_PATH}")
    try:
        df = pd.read_csv(TEAM_LOGS_PATH)
        # Filter for 'situation' == 'all'
        if 'situation' in df.columns:
            df = df[df['situation'] == 'all']
            
        # Normalize Team Abbreviations to match NHL API
        team_map = {
            "S.J": "SJS",
            "N.J": "NJD",
            "T.B": "TBL",
            "L.A": "LAK",
            "MTL": "MTL", # Consistent
            "WSH": "WSH"
        }
        # Apply mapping where exists, else keep original
        df['team'] = df['team'].replace(team_map)
        
        # Filter for Target Seasons (2022-2023 onwards)
        # Season is likely int (e.g. 20222023)
        if 'season' in df.columns:
            df = df[df['season'] >= 2022]
            print(f"   ... Filtered to {len(df)} rows (Season >= 2022)")
        
    except Exception as e:
        print(f"❌ Error loading Team Logs: {e}")
        return

    # 2. Prepare Home/Away Split
    # The logs have one row per team per game. We want one row per GAME (Home vs Away).
    # Filter for Home Rows
    home_df = df[df['home_or_away'] == 'HOME'].copy()
    away_df = df[df['home_or_away'] == 'AWAY'].copy()
    
    # Select cols to keep (we don't need all 100+ cols for now, but keeping key ones helps)
    # Key Join Keys: gameId
    
    print(f"   ... Joining Home ({len(home_df)}) and Away ({len(away_df)}) rows")
    
    # Use suffixes to distinguish
    game_df = pd.merge(home_df, away_df, on='gameId', suffixes=('_home', '_away'))
    
    # 3. Load Goalie Features
    print(f"   ... Loading Goalie Features: {GOALIE_FEATURES_PATH}")
    gdf = pd.read_csv(GOALIE_FEATURES_PATH)
    
    # Ensure gameId types match
    game_df['gameId'] = game_df['gameId'].astype(str)
    gdf['gameId'] = gdf['gameId'].astype(str)
    
    # 4. Join Goalie Features (Home)
    # Join on gameId + team_home
    print("   ... Merging Home Goalie Stats")
    game_df = pd.merge(game_df, gdf, 
                       left_on=['gameId', 'team_home'], 
                       right_on=['gameId', 'team'], 
                       how='left')
    
    # Rename columns to avoid collision with next merge (and clear 'team' col from merge)
    game_df = game_df.drop(columns=['team'])
    game_df.rename(columns={
        'goalie_name': 'goalie_name_home',
        'GSAx_L5': 'home_goalie_GSAx_L5',
        'GSAx_L10': 'home_goalie_GSAx_L10',
        'GSAx_Season': 'home_goalie_GSAx_Season',
        'Games_Played': 'home_goalie_GP'
    }, inplace=True)
    
    # 5. Join Goalie Features (Away)
    print("   ... Merging Away Goalie Stats")
    game_df = pd.merge(game_df, gdf, 
                       left_on=['gameId', 'team_away'], 
                       right_on=['gameId', 'team'], 
                       how='left')
    
    game_df = game_df.drop(columns=['team'])
    game_df.rename(columns={
        'goalie_name': 'goalie_name_away',
        'GSAx_L5': 'away_goalie_GSAx_L5',
        'GSAx_L10': 'away_goalie_GSAx_L10',
        'GSAx_Season': 'away_goalie_GSAx_Season',
        'Games_Played': 'away_goalie_GP'
    }, inplace=True)
    
    # 6. Compute Differentials
    print("   ... Calculating Feature Differentials")
    
    # Goalie Diff (Home - Away) => Positive means Home Goalie is better
    for metric in ['GSAx_L5', 'GSAx_L10', 'GSAx_Season']:
        home_col = f"home_goalie_{metric}"
        away_col = f"away_goalie_{metric}"
        diff_col = f"diff_goalie_{metric}"
        
        # Fill NaNs with 0 (Average) for calc
        game_df[diff_col] = game_df[home_col].fillna(0) - game_df[away_col].fillna(0)

    # 7. Save
    print(f"   💾 Saving to {OUTPUT_PATH}")
    game_df.to_csv(OUTPUT_PATH, index=False)
    
    # Validation
    print(f"   📊 Final Rows: {len(game_df)}")
    
    # Check Coverage
    missing_home = game_df['goalie_name_home'].isna().sum()
    print(f"   ⚠️  Games missing Home Goalie: {missing_home}")
    
    # Sample
    sample_cols = ['gameDate_home', 'team_home', 'team_away', 'goalie_name_home', 'goalie_name_away', 'diff_goalie_GSAx_Season']
    print("\n🔍 Sample Rows:")
    print(game_df[sample_cols].sort_values('gameDate_home').tail(5))

    return game_df

if __name__ == "__main__":
    assemble_dataset()
