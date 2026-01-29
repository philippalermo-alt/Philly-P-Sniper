
import requests
import pandas as pd
import time
import os
import random

SEASONS = [20222023, 20232024, 20242025, 20252026]
TEAMS = [
    "ANA", "ARI", "BOS", "BUF", "CGY", "CAR", "CHI", "COL", "CBJ", "DAL",
    "DET", "EDM", "FLA", "LAK", "MIN", "MTL", "NSH", "NJD", "NYI", "NYR",
    "OTT", "PHI", "PIT", "SJS", "SEA", "STL", "TBL", "TOR", "UTA", "VAN",
    "VGK", "WSH", "WPG"
]

OUTPUT_DIR = "data/nhl_processed"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_season_team_safe(season_id, team):
    start = 0
    limit = 100 # API seems to cap at 100, so we align with it
    all_rows = []
    
    while True:
        url = (
            f"https://api.nhle.com/stats/rest/en/skater/summary?"
            f"isAggregate=false&isGame=true&"
            f"sort=[{{%22property%22:%22gameDate%22,%22direction%22:%22DESC%22}}]&"
            f"start={start}&limit={limit}&"
            f"cayenneExp=seasonId={season_id}%20and%20gameTypeId=2%20and%20teamAbbrev=\"{team}\""
        )
        
        try:
            # Exponential Backoff for 429s
            for attempt in range(5):
                res = requests.get(url, timeout=15)
                if res.status_code == 200:
                    break
                elif res.status_code == 429:
                    wait = 10 * (attempt + 1)
                    print(f"⚠️ 429 Limit {team} (Attempt {attempt+1}). Waiting {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"⚠️ Status {res.status_code} {team}. Retrying...")
                    time.sleep(5)
            
            if res.status_code != 200:
                print(f"❌ Failed to fetch {team} offset {start} after retries.")
                break

            data_json = res.json()
            if 'data' not in data_json: 
                break
            
            data = data_json['data']
            fetched = len(data)
            
            if fetched == 0:
                break
                
            all_rows.extend(data)
            start += fetched
            
            # Anti-Ban Sleep via Jitter
            time.sleep(random.uniform(2.0, 4.0)) 
            
        except Exception as e:
            print(f"❌ Exception {season_id} {team}: {e}")
            break
            
    return all_rows

def main():
    print("🚀 Starting NHL History Ingestion (Safe Mode)...")
    
    for season in SEASONS:
        print(f"\n📥 Processing Season {season}...")
        season_rows = []
        
        for i, team in enumerate(TEAMS):
            print(f"   [{i+1}/{len(TEAMS)}] Fetching {team}...", end="", flush=True)
            rows = fetch_season_team_safe(season, team)
            if rows:
                season_rows.extend(rows)
                print(f" ✅ {len(rows)} rows")
            else:
                print(f" ⚠️ 0 rows")
            
            # Extra buffer between teams
            time.sleep(2)
        
        # Save Season Checkpoint
        if season_rows:
            df = pd.DataFrame(season_rows)
            outfile = f"{OUTPUT_DIR}/nhl_boxscores_{season}.parquet"
            df.to_parquet(outfile)
            print(f"💾 Saved Season {season}: {len(df)} rows to {outfile}")
            
    print("\n✅ Ingestion Complete.")

if __name__ == "__main__":
    main()
