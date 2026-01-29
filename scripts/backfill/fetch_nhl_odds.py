import pandas as pd
import requests
import time
import os
import json
from datetime import datetime, timedelta
import sys

# Add parent to path to get settings if needed, or just hardcode key if it's in env
# Assuming we can get key from Config or Envar
try:
    from config.settings import Config
    API_KEY = Config.ODDS_API_KEY
except:
    # Fallback to env or hardcoded placeholder (User to replace if needed)
    API_KEY = os.getenv("ODDS_API_KEY", "7e6462d56d833b4f0102707ad16661e6")

DATA_PATH = "Hockey Data/training_set_v2.csv"
OUTPUT_PATH = "Hockey Data/nhl_odds_history.csv"
SPORT = "icehockey_nhl"

def backfill_odds():
    print("💰 Starting NHL Odds Backfill...")
    
    # 1. Load Dates from Training Set
    if not os.path.exists(DATA_PATH):
        print("❌ Training set not found.")
        return
        
    df = pd.read_csv(DATA_PATH)
    # gameDate_home is int YYYYMMDD
    dates = sorted(df['gameDate_home'].unique())
    print(f"📅 Found {len(dates)} unique game days in training set.")
    
    # 2. Setup Output
    mode = 'a' if os.path.exists(OUTPUT_PATH) else 'w'
    header = not os.path.exists(OUTPUT_PATH)
    
    # We will append row by row or batch
    
    # 3. Iterate Dates
    # Convert YYYYMMDD to YYYY-MM-DD
    processed = 0
    errors = 0
    
    # Check existing dates to skip
    existing_dates = set()
    if os.path.exists(OUTPUT_PATH):
        try:
            # Read only date col
            existing = pd.read_csv(OUTPUT_PATH, usecols=['date_str'])
            existing_dates = set(existing['date_str'].unique())
            print(f"   Skipping {len(existing_dates)} days already fetched.")
        except:
            pass

    for d_int in dates:
        d_str = str(d_int)
        fmt_date = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}" # YYYY-MM-DD
        
        if fmt_date in existing_dates:
            continue
            
        # Timestamp: 23:00:00Z (7PM ET) - captures lines just before main slate lock
        # Note: For strict closing line, this is approximate.
        # But rigorous enough for Phase 1.
        snapshot = f"{fmt_date}T23:00:00Z"
        
        print(f"📡 Fetching {snapshot} ({processed+1}/{len(dates) - len(existing_dates)} left)...")
        
        url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds-history"
        params = {
            'apiKey': API_KEY,
            'regions': 'us,eu', # Get Pinnacle (eu/us2 usually have it? EU has Pinny)
            'markets': 'h2h',
            'date': snapshot,
            'oddsFormat': 'decimal'
        }
        
        try:
            res = requests.get(url, params=params, timeout=10)
            
            if res.status_code == 429:
                print("   ⏳ Rate Limit. Sleeping 10s...")
                time.sleep(10)
                # Retry once
                res = requests.get(url, params=params, timeout=10)
            
            if res.status_code == 200:
                data = res.json()
                data_list = data.get('data', [])
                
                rows = []
                for game in data_list:
                    # Simplify: Just save the specific bookmakers classes
                    # Pinnacle, Circa??, DraftKings
                    # We want 'Average' and 'Sharpest'
                    
                    row = {
                        'date_str': fmt_date,
                        'sport': SPORT,
                        'game_id_api': game.get('id'),
                        'home_team': game.get('home_team'),
                        'away_team': game.get('away_team'),
                        'commence_time': game.get('commence_time')
                    }
                    
                    # Extract Bookmakers
                    bookmakers = game.get('bookmakers', [])
                    for bk in bookmakers:
                        key = bk['key']
                        if key in ['pinnacle', 'williamhill', 'draftkings', 'fanduel']:
                            # Get h2h prices
                            for mkt in bk.get('markets', []):
                                if mkt['key'] == 'h2h':
                                    for out in mkt.get('outcomes', []):
                                        name = out['name']
                                        price = out['price']
                                        
                                        if name == row['home_team']:
                                            row[f"{key}_home"] = price
                                        elif name == row['away_team']:
                                            row[f"{key}_away"] = price
                                            
                    rows.append(row)
                
                if rows:
                    out_df = pd.DataFrame(rows)
                    out_df.to_csv(OUTPUT_PATH, mode='a', header=header, index=False)
                    header = False # Only write header once
                    print(f"   ✅ Saved {len(rows)} games.")
                else:
                    # Save a dummy row to record we checked this date?
                    # Or just rely on re-running.
                    print("   ⚠️ No games found for date.")
                    
            else:
                print(f"   ❌ API Error {res.status_code}: {res.text}")
                errors += 1
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            errors += 1
            
        processed += 1
        # Sleep to be nice / bucket rate limit
        time.sleep(1.5)
        
        # Safety break for dev (Remove for full run)
        if processed >= 10:
           print("🛑 Stopping after 10 days for verification.")
           break

if __name__ == "__main__":
    backfill_odds()
