import pandas as pd
import os

FILE_PATH = "/Users/purdue2k5/Documents/Philly-P-Sniper/Hockey Data/all_teams.csv"

def inspect_download():
    if not os.path.exists(FILE_PATH):
        print(f"❌ File not found: {FILE_PATH}")
        return

    print(f"🕵️‍♂️ Inspecting {FILE_PATH}...")
    try:
        # Read header only first to show columns
        header = pd.read_csv(FILE_PATH, nrows=0)
        print(f"📋 Columns found ({len(header.columns)}):")
        print(list(header.columns))
        
        # Check for key player identifiers
        player_cols = [c for c in header.columns if 'player' in c.lower() or 'name' in c.lower() or 'goalie' in c.lower()]
        print(f"\n👤 Potential Player Columns: {player_cols}")
        
        if not player_cols:
            print("⚠️  No obvious player columns found. This might be Team-Level only.")
        else:
            print("✅ Player columns detected!")
            
        # Sample data
        df = pd.read_csv(FILE_PATH, nrows=5)
        print("\n📊 Sample Data:")
        print(df.head())
        
    except Exception as e:
        print(f"❌ Error reading file: {e}")

if __name__ == "__main__":
    inspect_download()
