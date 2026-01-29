
import requests
import pandas as pd
import time
import os

SEASONS = [20222023, 20232024, 20242025, 20252026]
OUTPUT_DIR = "data/nhl_processed"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_season(season_id):
    print(f"📥 Fetching Season {season_id}...")
    all_rows = []
    start = 0
    limit = 10000 # Max allowed by API usually
    
    while True:
        url = (
            f"https://api.nhle.com/stats/rest/en/skater/summary?"
            f"isAggregate=false&isGame=true&"
            f"sort=[{{%22property%22:%22gameDate%22,%22direction%22:%22DESC%22}}]&"
            f"start={start}&limit={limit}&"
            f"cayenneExp=seasonId={season_id}%20and%20gameTypeId=2"
        )
        
        try:
            t0 = time.time()
            res = requests.get(url, timeout=30).json()
            
            if 'data' not in res:
                print(f"❌ No data key for {season_id}")
                break
                
            data = res['data']
            fetched = len(data)
            total_available = res.get('total', 0)
            
            if fetched == 0:
                break
                
            all_rows.extend(data)
            print(f"   + Loaded {fetched} rows (Offset {start}). Total: {len(all_rows)}/{total_available}")
            
            if len(all_rows) >= total_available or fetched < limit:
                print(f"✅ Season {season_id} Complete: {len(all_rows)} rows.")
                break
            
            start += fetched
            time.sleep(0.5) # Be nice
            
        except Exception as e:
            print(f"❌ Error fetching {season_id} at offset {start}: {e}")
            break
            
    return pd.DataFrame(all_rows) if all_rows else None

def main():
    all_data = []
    
    for season in SEASONS:
        df = fetch_season(season)
        if df is not None:
            df['season_id'] = season
            all_data.append(df)
        time.sleep(1)

    if all_data:
        full_df = pd.concat(all_data, ignore_index=True)
        print(f"\n📊 Total History Rows: {len(full_df)}")
        
        outfile = f"{OUTPUT_DIR}/nhl_boxscores_4seasons.parquet"
        full_df.to_parquet(outfile)
        print(f"💾 Saved to {outfile}")
        
    else:
        print("❌ No data collected.")

if __name__ == "__main__":
    main()
