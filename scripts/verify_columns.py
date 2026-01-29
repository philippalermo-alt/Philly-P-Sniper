import pandas as pd

FILE_PATH = "/Users/purdue2k5/Documents/Philly-P-Sniper/Hockey Data/all_teams.csv"

def verify():
    print(f"🔬 Verifying Schema of {FILE_PATH}...")
    try:
        # Load just headers and first 100 rows
        df = pd.read_csv(FILE_PATH, nrows=100)
        cols = list(df.columns)
        
        required = ['gameId', 'gameDate', 'name', 'position', 'team']
        missing = [c for c in required if c not in cols]
        
        if missing:
            print(f"❌ MISSING COLUMNS: {missing}")
            # Try to match fuzzy
            print("   Available columns similar to missing:")
            for m in missing:
                similar = [c for c in cols if m.lower() in c.lower()]
                print(f"   - For '{m}': {similar}")
        else:
            print("✅ All Critical Columns Present!")
            print(f"   Columns: {required}")
            
            # Check content
            print("\n👀 Sample Data:")
            print(df[required].head(5))
            
            # Check Positions
            if 'position' in df.columns:
                print(f"   Unique Positions (first 100 rows): {df['position'].unique()}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verify()
