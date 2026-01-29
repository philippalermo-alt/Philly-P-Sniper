
import requests
import pandas as pd
import time
import os

SEASONS = [20222023, 20232024, 20242025, 20252026]
TEAMS = [
    "ANA", "ARI", "BOS", "BUF", "CGY", "CAR", "CHI", "COL", "CBJ", "DAL",
    "DET", "EDM", "FLA", "LAK", "MIN", "MTL", "NSH", "NJD", "NYI", "NYR",
    "OTT", "PHI", "PIT", "SJS", "SEA", "STL", "TBL", "TOR", "UTA", "VAN",
    "VGK", "WSH", "WPG"
]

OUTPUT_DIR = "data/nhl_processed"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_season_team(season_id, team):
    start = 0
    limit = 100 
    all_rows = []
    errors = 0
    
    while True:
        url = (
            f"https://api.nhle.com/stats/rest/en/skater/summary?"
            f"isAggregate=false&isGame=true&"
            f"sort=[{{%22property%22:%22gameDate%22,%22direction%22:%22DESC%22}}]&"
            f"start={start}&limit={limit}&"
            f"cayenneExp=seasonId={season_id}%20and%20gameTypeId=2%20and%20teamAbbrev=\"{team}\""
        )
        
        try:
            # Retry Loop
            for attempt in range(3):
                try:
                    res = requests.get(url, timeout=10)
                    if res.status_code != 200:
                        print(f"⚠️ {res.status_code} for {team} offset {start}")
                        time.sleep(2 * (attempt + 1))
                        continue
                        
                    data_json = res.json()
                    break
                except ValueError:
                    # JSON Decode Error
                    print(f"⚠️ JSON Error {team} offset {start} (Attempt {attempt+1})")
                    time.sleep(2 * (attempt + 1))
                    if attempt == 2: raise
            
            if 'data' not in data_json: break
            
            data = data_json['data']
            fetched = len(data)
            
            if fetched == 0:
                break
                
            all_rows.extend(data)
            start += fetched
            
            # Rate Limit Protection
            time.sleep(0.3) 
            
        except Exception as e:
            print(f"❌ Failed {season_id} {team}: {e}")
            break
            
    return all_rows

def main():
    final_rows = []
    
    for season in SEASONS:
        print(f"📥 Processing Season {season}...")
        season_rows = []
        for team in TEAMS:
            print(f"   > Fetching {team}...", end="\r")
            rows = fetch_season_team(season, team)
            if rows:
                season_rows.extend(rows)
            time.sleep(0.5) # Gap between teams
        
        print(f"   ✅ Season {season} Total: {len(season_rows)}")
        final_rows.extend(season_rows)

    if final_rows:
        df = pd.DataFrame(final_rows)
        print(f"\n📊 Grand Total: {len(df)} rows")
        
        outfile = f"{OUTPUT_DIR}/nhl_boxscores_4seasons_full.parquet"
        df.to_parquet(outfile)
        print(f"💾 Saved to {outfile}")
        
    else:
        print("❌ No data.")

if __name__ == "__main__":
    main()
