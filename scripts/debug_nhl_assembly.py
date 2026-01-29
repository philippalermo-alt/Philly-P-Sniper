import pandas as pd

TEAM_LOGS_PATH = "Hockey Data/Game level data.csv"
GOALIE_FEATURES_PATH = "Hockey Data/goalie_strength_features.csv"

def debug_keys():
    print("🕵️‍♂️ Debugging Assembly Join Keys...")
    
    # Load Team Logs
    tdf = pd.read_csv(TEAM_LOGS_PATH)
    if 'situation' in tdf.columns:
        tdf = tdf[tdf['situation'] == 'all']
        
    # Load Goalie Stats
    gdf = pd.read_csv(GOALIE_FEATURES_PATH)
    
    print("\n📊 Dataframe Shapes:")
    print(f"   Team Logs: {tdf.shape}")
    print(f"   Goalie Feats: {gdf.shape}")
    
    print("\n🔑 Team Logs Sample Keys:")
    tdf_sample = tdf[['gameId', 'team']].head(5)
    print(tdf_sample)
    print(f"   GameId Type: {tdf['gameId'].dtype}")
    
    print("\n🔑 Goalie Features Sample Keys:")
    gdf_sample = gdf[['gameId', 'team']].head(5)
    print(gdf_sample)
    print(f"   GameId Type: {gdf['gameId'].dtype}")
    
    # Check Team Abbrev Overlap
    t_teams = set(tdf['team'].unique())
    g_teams = set(gdf['team'].unique())
    
    only_in_t = sorted(list(t_teams - g_teams))
    only_in_g = sorted(list(g_teams - t_teams))
    
    print(f"\n🇺🇸 Team Mismatch Check:")
    print(f"   Only in Team Logs: {only_in_t}")
    print(f"   Only in Goalie Logs: {only_in_g}")
    
    # Check Game ID Overlap (cast to string first)
    t_games = set(tdf['gameId'].astype(str).unique())
    g_games = set(gdf['gameId'].astype(str).unique())
    
    common = len(t_games.intersection(g_games))
    print(f"\n🆔 Game ID Overlap:")
    print(f"   Team Logs Unique Games: {len(t_games)}")
    print(f"   Goalie Logs Unique Games: {len(g_games)}")
    print(f"   Common: {common}")

if __name__ == "__main__":
    debug_keys()
