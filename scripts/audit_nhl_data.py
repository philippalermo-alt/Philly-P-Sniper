
import pandas as pd
import os

PROJECT_DIR = "/Users/purdue2k5/Documents/Philly-P-Sniper"
files = [
    "nhl_backfill_final.csv",
    "nhl_backfill_str.csv"
]

def audit_file(rel_path):
    path = os.path.join(PROJECT_DIR, rel_path)
    print(f"\n{'='*20} {rel_path} {'='*20}")
    
    if not os.path.exists(path):
        print("❌ File not found.")
        return

    try:
        # Read snippet
        df = pd.read_csv(path, nrows=5)
        print(f"Columns: {list(df.columns)}")
        
        # Read full description
        df = pd.read_csv(path)
        print(f"Rows: {len(df)}")
        
        # Date Check
        date_col = next((c for c in df.columns if 'date' in c.lower()), None)
        if date_col:
            print(f"Date Range: {pd.to_datetime(df[date_col]).min()} to {pd.to_datetime(df[date_col]).max()}")
        
        # Game Level Check
        # Does it have 'home_team', 'away_team' and stats?
        stats = ['corsi', 'fenwick', 'xg', 'shots', 'goals']
        found = [c for c in df.columns if any(s in c.lower() for s in stats)]
        print(f"Stats Found: {found}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

for f in files:
    audit_file(f)
