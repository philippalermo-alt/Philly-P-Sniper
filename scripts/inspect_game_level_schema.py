import pandas as pd

FILE_PATH = "/Users/purdue2k5/Documents/Philly-P-Sniper/Hockey Data/Game level data.csv"

def inspect_file():
    print(f"🕵️‍♂️ Inspecting {FILE_PATH}...")
    
    # Read first 100k lines (to speed up if file is huge, though 123MB is manageable)
    try:
        df = pd.read_csv(FILE_PATH, nrows=50000)
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return

    print(f"📊 Rows loaded: {len(df)}")
    print(f"columns: {list(df.columns)}")
    
    # Check unique positions
    if 'position' in df.columns:
        positions = df['position'].unique()
        print(f"📍 Unique Positions found: {positions}")
        
        if 'G' in positions:
            print("✅ FOUND GOALIES! ('G' is in positions)")
            
            # Show a sample goalie row
            goalie_df = df[df['position'] == 'G']
            print("\n🥅 Sample Goalie Row:")
            print(goalie_df[['gameId', 'gameDate', 'name', 'team', 'position', 'situation']].head(5))
            
            # Verify Granularity: Unique Games for a specific Goalie
            sample_goalie = goalie_df.iloc[0]['name']
            sg_df = df[df['name'] == sample_goalie]
            print(f"\n🔎 Checking Granularity for {sample_goalie}:")
            print(f"   - Total Rows: {len(sg_df)}")
            print(f"   - Unique Games: {sg_df['gameId'].nunique()}")
            
            if len(sg_df) > 1 and sg_df['gameId'].nunique() > 1:
                print("🚀 CONCLUSION: We have GAME LOGS. Goalie Mapping is POSSIBLE.")
            else:
                print("⚠️  Conclusion unsure. Avg rows per game might be aggregation.")
                
        else:
            print("❌ NO GOALIES FOUND in first 50k rows. Checking if file is Team-Only...")
            # Check if there are ANY player names or just team names
            names = df['name'].unique()
            print(f"Names sample: {names[:10]}")
    else:
        print("❌ 'position' column missing.")

if __name__ == "__main__":
    inspect_file()
