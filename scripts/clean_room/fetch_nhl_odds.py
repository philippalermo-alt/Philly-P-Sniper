import pandas as pd
import requests
import os
import time
import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
API_KEY = os.getenv("ODDS_API_KEY")
SPORT = "icehockey_nhl"
REGIONS = "us,us2,eu" # Broad regions to find Pinnacle if needed
MARKETS = "totals"
ODDS_FORMAT = "decimal"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
OUTPUT_FILE = "Hockey Data/nhl_totals_odds_close.csv"
SOURCE_DATA_FILE = "Hockey Data/Game level data.csv"
CACHE_DIR = "cache/odds_api_granular"
MAX_WORKERS = 12 # Adjusted to reduce 429s

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

if not API_KEY:
    raise ValueError("ODDS_API_KEY not found in environment variables.")

def log(msg):
    # Thread-safe logging not strictly needed for print, but good practice to keep simple
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def fetch_url_with_retry(url, params, max_retries=5):
    """
    Robust fetcher with exponential backoff for 429s and 5xx.
    """
    delay = 1.0
    for i in range(max_retries):
        try:
            resp = requests.get(url, params=params, timeout=15)
            
            if resp.status_code == 200:
                return resp
            
            if resp.status_code == 429:
                log(f"⚠️ 429 Rate Limit. Sleeping {delay}s...")
                time.sleep(delay)
                delay *= 2 # Exponential backoff
                continue
                
            if 500 <= resp.status_code < 600:
                log(f"⚠️ Server Error {resp.status_code}. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
                continue
                
            # Other errors (400, 401, 403, 404) - logic error, don't retry
            log(f"❌ Error {resp.status_code} for URL")
            return resp
            
        except requests.RequestException as e:
            log(f"⚠️ Network check failed: {e}. Retrying...")
            time.sleep(delay)
            delay *= 2
            
    log(f"❌ Failed after {max_retries} attempts.")
    return None

def get_unique_dates(csv_path):
    log(f"Reading dates from {csv_path}...")
    try:
        df = pd.read_csv(csv_path)
        if 'gameDate' not in df.columns:
            return []
        
        unique_raw_dates = sorted(df['gameDate'].unique())
        formatted_dates = []
        for d in unique_raw_dates:
            d_str = str(d)
            if len(d_str) == 8:
                fmt = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}"
                formatted_dates.append(fmt)
        
        # Filter for 2022-23 season start (Oct 2022) onwards
        filtered_dates = [d for d in formatted_dates if d >= "2022-10-01"]
        return sorted(list(set(filtered_dates)))
    except Exception as e:
        log(f"Error reading dates: {e}")
        return []

def fetch_events_for_date(date_str):
    """
    Get the schedule (list of games) for a given date.
    CACHE: events_{date_str}.json
    """
    noon_timestamp = f"{date_str}T17:00:00Z"
    cache_path = f"{CACHE_DIR}/events_{date_str}.json"
    
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
            try:
                return json.load(f)
            except:
                pass # Corrupt, re-fetch
            
    url = f"https://api.the-odds-api.com/v4/historical/sports/{SPORT}/events"
    params = {
        "apiKey": API_KEY,
        "date": noon_timestamp
    }
    
    resp = fetch_url_with_retry(url, params)
    
    if resp and resp.status_code == 200:
        data = resp.json()
        with open(cache_path, 'w') as f:
            json.dump(data, f)
        return data
        
    log(f"Final failure fetching events for {date_str}")
    return None

def fetch_game_odds(game):
    """
    Fetch ODDS for a specific game dict (id, commence_time).
    Returns parsed row dict or None.
    """
    game_id = game['id']
    commence_time_str = game['commence_time']
    c_dt = datetime.strptime(commence_time_str, DATE_FORMAT)
    snapshot_dt = c_dt - timedelta(minutes=15)
    snapshot_str = snapshot_dt.strftime(DATE_FORMAT)
    
    cache_key = f"odds_{game_id}_{snapshot_str.replace(':', '')}"
    cache_path = f"{CACHE_DIR}/{cache_key}.json"
    
    data = None
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
            try:
                data = json.load(f)
            except:
                data = None
    
    if data is None:
        url = f"https://api.the-odds-api.com/v4/historical/sports/{SPORT}/events/{game_id}/odds"
        params = {
            "apiKey": API_KEY,
            "regions": REGIONS,
            "markets": MARKETS,
            "oddsFormat": ODDS_FORMAT,
            "date": snapshot_str
        }
        
        resp = fetch_url_with_retry(url, params)
        if resp and resp.status_code == 200:
            data = resp.json()
            with open(cache_path, 'w') as f:
                json.dump(data, f)
        else:
            return None

    # Process Data
    if not data: return None
    
    evt_data = data
    if isinstance(data, dict) and 'data' in data:
        evt_data = data['data']
    
    if isinstance(evt_data, list) and len(evt_data) > 0:
        evt_data = evt_data[0]
        
    if not isinstance(evt_data, dict): return None
    
    # Extract Line
    # Priority: Pinnacle > DraftKings > FanDuel > Others
    PREFERRED_BOOKS = ['pinnacle', 'draftkings', 'fanduel', 'pointsbetus', 'betmgm', 'bovada']
    selected_book = None
    total_line = None
    over_price = None
    under_price = None
    
    bookmakers = evt_data.get('bookmakers', [])
    available = {b['key']: b for b in bookmakers}
    
    for bk in PREFERRED_BOOKS:
        if bk in available:
            for mkt in available[bk]['markets']:
                if mkt['key'] == 'totals':
                    points = {}
                    for oc in mkt['outcomes']:
                        p = oc.get('point')
                        n = oc.get('name')
                        if p not in points: points[p] = {}
                        points[p][n] = oc.get('price')
                    
                    # Select first valid pair (usually main line)
                    for p, prices in points.items():
                        if 'Over' in prices and 'Under' in prices:
                            total_line = p
                            over_price = prices['Over']
                            under_price = prices['Under']
                            selected_book = bk
                            break
                if selected_book: break
        if selected_book: break
        
    if selected_book and total_line:
        # We need the game_date from the caller context or derive it?
        # We passed 'game' dict, we can assume caller handles date mapping or we return enough info.
        return {
            "game_id": game_id,
            "commence_time_utc": commence_time_str,
            "home_team": game['home_team'],
            "away_team": game['away_team'],
            "total_line_close": total_line,
            "over_price_close": over_price,
            "under_price_close": under_price,
            "bookmaker": selected_book,
            "snapshot_timestamp": snapshot_str,
            "source": "odds_api_granular"
        }
    return None

def main():
    log(f"Starting High-Performance NHL Totals Fetch (Workers={MAX_WORKERS})")
    dates = get_unique_dates(SOURCE_DATA_FILE)
    log(f"Targeting {len(dates)} dates: {dates[0]} to {dates[-1]}")
    
    # Reset Output File
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
    
    all_game_tasks = []
    
    # Phase 1: Collect all Game IDs to fetch (Multithreaded Schedule Fetch)
    # We can fetch schedules in parallel roughly.
    
    log("Phase 1: Fetching Schedules...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_date = {executor.submit(fetch_events_for_date, d): d for d in dates}
        
        for future in as_completed(future_to_date):
            d_str = future_to_date[future]
            data = future.result()
            
            # Extract games for this date
            if data:
                events_list = data
                if isinstance(data, dict) and 'data' in data:
                    events_list = data['data']
                    
                if isinstance(events_list, list):
                    for evt in events_list:
                        c_dt = datetime.strptime(evt['commence_time'], DATE_FORMAT)
                        # Local Date Logic (UTC-5)
                        local_dt = c_dt - timedelta(hours=5)
                        if local_dt.strftime('%Y-%m-%d') == d_str:
                            # Attach the 'target_date' to the event so we know which date bucket it belongs to (for CSV)
                            evt['target_date'] = d_str
                            all_game_tasks.append(evt)

    # Deduplicate games by ID (in case of overlaps across date queries)
    unique_games = {}
    for g in all_game_tasks:
        unique_games[g['id']] = g
    
    game_list = list(unique_games.values())
    # Sort by time
    game_list.sort(key=lambda x: x['commence_time'])
    
    log(f"Phase 1 Complete. Found {len(game_list)} unique games.")
    
    # Phase 2: Fetch Odds in Parallel
    log("Phase 2: Fetching Odds...")
    
    total_games = len(game_list)
    completed = 0
    results = []
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_game = {executor.submit(fetch_game_odds, g): g for g in game_list}
        
        for future in as_completed(future_to_game):
            g = future_to_game[future]
            res = future.result()
            if res:
                # Add back the target_date
                res['game_date'] = g['target_date']
                results.append(res)
            
            completed += 1
            if completed % 100 == 0:
                print(f"   Progress: {completed}/{total_games} ({len(results)} valid odds)")
                
    # Save Results
    if results:
        df = pd.DataFrame(results)
        # Reorder columns matches Step 4 reqs
        cols = ["game_date", "home_team", "away_team", "total_line_close", 
                "over_price_close", "under_price_close", "snapshot_timestamp", 
                "bookmaker", "source", "commence_time_utc"]
        # Ensure cols exist
        final_cols = [c for c in cols if c in df.columns]
        df = df[final_cols]
        # Add constant
        df["close_definition"] = "last snapshot <= 30 min pregame"
        
        df.to_csv(OUTPUT_FILE, index=False)
        log(f"✅ DONE. Saved {len(df)} totals records to {OUTPUT_FILE}")
    else:
        log("❌ No odds found.")

if __name__ == "__main__":
    main()
