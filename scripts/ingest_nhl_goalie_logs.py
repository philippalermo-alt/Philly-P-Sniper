import requests
import pandas as pd
import os
import time

# Configuration
BASE_URL = "https://api.nhle.com/stats/rest/en/goalie/summary"
OUTPUT_DIR = "/Users/purdue2k5/Documents/Philly-P-Sniper/Hockey Data"

# Season definitions (Start Date, End Date, Folder Name)
SEASONS = [
    ("2022-10-01", "2023-06-30", "2022-23"),
    ("2023-10-10", "2024-06-30", "2023-24"),
    ("2024-10-04", "2025-06-30", "2024-25"),
    ("2025-10-01", "2026-06-30", "2025-26") # Current simulated future season
]

def fetch_season_logs(start_date, end_date, folder_name):
    print(f"\n🏒 Fetching Goalie Logs for {folder_name} ({start_date} to {end_date})...")
    
    # Ensure directory exists
    season_path = os.path.join(OUTPUT_DIR, folder_name)
    os.makedirs(season_path, exist_ok=True)
    
    # Construct Cayenne Expression for Date Range and Game Type (2 = Regular Season, 3 = Playoffs)
    # Fetching Regular Season (2)
    cayenne_exp = f'gameDate>="{start_date}" and gameDate<="{end_date}" and gameTypeId=2'
    
    all_records = []
    start = 0
    limit = 100
    
    # Updated Headers with User-Agent
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    while True:
        params = {
            "isAggregate": "false",
            "isGame": "true",
            "sort": '[{"property":"gameDate","direction":"DESC"}]',
            "start": start,
            "limit": limit,
            "factCayenneExp": "gamesPlayed>=1",
            "cayenneExp": cayenne_exp
        }
        
        retries = 3
        success = False
        
        for attempt in range(retries):
            try:
                r = requests.get(BASE_URL, params=params, headers=headers)
                if r.status_code == 200:
                    success = True
                    break
                else:
                    print(f"   ⚠️  API Error {r.status_code}. Retrying ({attempt + 1}/{retries})...")
                    time.sleep(2 * (attempt + 1)) # Exponential backoff
            except Exception as e:
                print(f"   ⚠️  Network Error: {e}. Retrying...")
                time.sleep(2)
        
        if not success:
            print(f"   ❌ Failed to fetch page starting at {start}. Stopping season.")
            break

        try:
            data = r.json()
            records = data.get('data', [])
            total = data.get('total', 0)
            
            if not records:
                break
                
            all_records.extend(records)
            print(f"   Fetched {len(records)} records (Total so far: {len(all_records)} / {total})")
            
            start += len(records)
            time.sleep(0.5) # Polite pacing per page
            
            if len(all_records) >= total:
                break
        except Exception as e:
            print(f"   ❌ Error Parsing JSON: {e}")
            break
            
    print(f"   ✅ Finished fetching {len(all_records)} records for {folder_name}")
            
    if len(all_records) > 0:
        df = pd.DataFrame(all_records)
        output_file = os.path.join(season_path, "goalie_game_logs.csv")
        df.to_csv(output_file, index=False)
        print(f"   💾 Saved to: {output_file}")
        
        # Validation Snippet
        print(f"   📊 Sample: {df.iloc[0]['goalieFullName']} on {df.iloc[0]['gameDate']} (GameID: {df.iloc[0]['gameId']})")
    else:
        print("   ⚠️  No records found for this period.")

def main():
    print("🚀 Starting NHL Goalie Log Ingestion...")
    
    for start, end, folder in SEASONS:
        fetch_season_logs(start, end, folder)
        time.sleep(1) # Polite delay
        
    print("\n✅ Ingestion Complete.")

if __name__ == "__main__":
    main()
