import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Config
# Note: ODDS_API_KEY must be exported in shell or loaded from env
API_KEY = os.getenv("ODDS_API_KEY") 
SPORT = "baseball_mlb"
MARKETS = "pitcher_strikeouts"
REGIONS = "us"
DATE_FORMAT = "%Y-%m-%dT12:00:00Z"
OUTPUT_FILE = "mlb_odds_2024.csv"
MAX_WORKERS = 8 # Adjust based on Plan (Trial: 5, Paid: 10-20)

def fetch_events_for_date(date_str):
    url = f"https://api.the-odds-api.com/v4/historical/sports/{SPORT}/events"
    params = {'apiKey': API_KEY, 'date': date_str}
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            return date_str, resp.json().get('data', [])
        elif resp.status_code == 429:
            print(f"⚠️ Quota limit matching schedule {date_str}")
            return date_str, []
    except Exception as e:
        print(f"❌ Error fetching schedule {date_str}: {e}")
    return date_str, []

def fetch_game_odds(game_tuple):
    gid, date_str = game_tuple
    url = f"https://api.the-odds-api.com/v4/historical/sports/{SPORT}/events/{gid}/odds"
    params = {
        'apiKey': API_KEY,
        'regions': REGIONS,
        'markets': MARKETS,
        'date': date_str,
        'oddsFormat': 'american'
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 429:
            print("🛑 Quota Hit on Game Odds")
            return None
    except:
        pass
    return None

def process_odds_response(data, date_str, gid):
    parsed = []
    if not data: return parsed
    
    # Handle single dict or list wrapper
    event_data = data.get('data', data)
    if isinstance(event_data, list): 
        event_data = event_data[0] if event_data else {}
        
    home = event_data.get('home_team')
    away = event_data.get('away_team')
    
    # Filter Books
    target_books = ['draftkings', 'fanduel', 'pinnacle', 'betmgm']
    
    for book in event_data.get('bookmakers', []):
        if book['key'] not in target_books: continue
        
        for market in book.get('markets', []):
            if market['key'] == MARKETS:
                for outcome in market.get('outcomes', []):
                    parsed.append({
                        'game_date': date_str[:10],
                        'game_id': gid,
                        'home': home, 'away': away,
                        'pitcher': outcome.get('description'),
                        'book': book['key'],
                        'label': outcome.get('name'), # Over/Under
                        'line': outcome.get('point'),
                        'price': outcome.get('price')
                    })
    return parsed

def run_fast_fetch():
    if not API_KEY:
        print("❌ Error: ODDS_API_KEY environment variable not set.")
        return

    print(f"🚀 Starting Parallel Fetch (Workers={MAX_WORKERS})...")
    
    start_date = datetime(2024, 4, 1)
    end_date = datetime(2024, 10, 1)
    # end_date = datetime(2024, 4, 10) # Test range
    
    dates = []
    curr = start_date
    while curr <= end_date:
        dates.append(curr.strftime(DATE_FORMAT))
        curr += timedelta(days=1)
        
    all_game_tasks = []
    all_rows = []
    
    # Phase 1: Schedules
    print(f"📅 Fetching Schedules for {len(dates)} days...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_date = {executor.submit(fetch_events_for_date, d): d for d in dates}
        
        for future in as_completed(future_to_date):
            d_str, games = future.result()
            for g in games:
                all_game_tasks.append((g['id'], d_str))
                
    print(f"✅ Found {len(all_game_tasks)} games total. Fetching odds...")
    
    # Phase 2: Odds
    # We might have 2500 games. Parallelize carefully.
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # submit all
        future_to_game = {executor.submit(fetch_game_odds, g): g for g in all_game_tasks}
        
        completed = 0
        total = len(all_game_tasks)
        
        for future in as_completed(future_to_game):
            gid, d_str = future_to_game[future]
            data = future.result()
            if data:
                rows = process_odds_response(data, d_str, gid)
                all_rows.extend(rows)
            
            completed += 1
            if completed % 100 == 0:
                print(f"   Progress: {completed}/{total} games ({len(all_rows)} odds found)")
                
    # Save
    if all_rows:
        df = pd.DataFrame(all_rows)
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"✅ DONE. Saved {len(df):,} odds lines to {OUTPUT_FILE}")
    else:
        print("❌ No odds found.")

if __name__ == "__main__":
    run_fast_fetch()
