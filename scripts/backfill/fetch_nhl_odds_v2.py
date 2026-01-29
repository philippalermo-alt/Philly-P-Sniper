import pandas as pd
import requests
import time
import os
import difflib
import sys
from datetime import datetime, timedelta

# User requested "Model this after the NBA script".
# The NBA script uses efficient batching by start time.
# Since we lack exact start times in our CSV, we use a high-fidelity "Daily Closing" snapshot.
# 23:30 Z = 6:30 PM ET (Just before 7 PM puck drops).

try:
    from config.settings import Config
    API_KEY = Config.ODDS_API_KEY
except:
    API_KEY = os.getenv("ODDS_API_KEY", "7e6462d56d833b4f0102707ad16661e6")

INPUT_CSV = "Hockey Data/training_set_v2.csv"
OUTPUT_CSV = "Hockey Data/nhl_odds_closing.csv"
SPORT = "icehockey_nhl"

# NHL Team Map for consistent fuzzy matching
TEAM_ALIASES = {
    'Montreal Canadiens': ['Montreal', 'Canadiens', 'Habs'],
    'Tampa Bay Lightning': ['Tampa', 'Lightning', 'Tampa Bay'],
    'Florida Panthers': ['Florida', 'Panthers'],
    'Toronto Maple Leafs': ['Toronto', 'Leafs', 'Maple Leafs'],
    'Ottawa Senators': ['Ottawa', 'Senators'],
    'Buffalo Sabres': ['Buffalo', 'Sabres'],
    'Boston Bruins': ['Boston', 'Bruins'],
    'Detroit Red Wings': ['Detroit', 'Red Wings'],
    'New York Rangers': ['NY Rangers', 'Rangers'],
    'New York Islanders': ['NY Islanders', 'Islanders'],
    'New Jersey Devils': ['New Jersey', 'Devils'],
    'Pittsburgh Penguins': ['Pittsburgh', 'Penguins'],
    'Washington Capitals': ['Washington', 'Capitals'],
    'Philadelphia Flyers': ['Philadelphia', 'Flyers'],
    'Carolina Hurricanes': ['Carolina', 'Hurricanes'],
    'Columbus Blue Jackets': ['Columbus', 'Blue Jackets'],
    'St. Louis Blues': ['St Louis', 'Blues'],
    'Chicago Blackhawks': ['Chicago', 'Blackhawks'],
    'Nashville Predators': ['Nashville', 'Predators'],
    'Minnesota Wild': ['Minnesota', 'Wild'],
    'Dallas Stars': ['Dallas', 'Stars'],
    'Winnipeg Jets': ['Winnipeg', 'Jets'],
    'Colorado Avalanche': ['Colorado', 'Avalanche'],
    'Arizona Coyotes': ['Arizona', 'Coyotes', 'Utah', 'Utah Mammoth'], # Handle relocation
    'Utah Hockey Club': ['Utah', 'Utah Mammoth', 'Arizona', 'Coyotes'], # 2024+ name
    'Vegas Golden Knights': ['Vegas', 'Golden Knights'],
    'Edmonton Oilers': ['Edmonton', 'Oilers'],
    'Calgary Flames': ['Calgary', 'Flames'],
    'Vancouver Canucks': ['Vancouver', 'Canucks'],
    'Seattle Kraken': ['Seattle', 'Kraken'],
    'Los Angeles Kings': ['LA Kings', 'Los Angeles', 'Kings'],
    'Anaheim Ducks': ['Anaheim', 'Ducks'],
    'San Jose Sharks': ['San Jose', 'Sharks']
}

def normalize_team(name):
    # Basic normalization
    return name.replace('.', '').replace('é', 'e').strip()

def get_h2h_odds(game_data, target_books=['pinnacle', 'circa', 'bodog', 'draftkings', 'fanduel']):
    # Find list of books
    books = game_data.get('bookmakers', [])
    
    # Priority Fetch
    found_book = None
    for target in target_books:
        for b in books:
            if b['key'] == target:
                found_book = b
                break
        if found_book: break
        
    if not found_book and books:
        found_book = books[0] # Fallback
        
    if not found_book:
        return None, None, None

    # Get Markets
    odds = {}
    odds['bookmaker'] = found_book['key']
    
    for m in found_book.get('markets', []):
        if m['key'] == 'h2h':
            for o in m['outcomes']:
                odds[o['name']] = o['price']
                
    return odds, found_book['key'], found_book['key']

def run_backfill():
    print("💰 Starting NHL Closing Odds Backfill (NBA-Style Precision)...")
    
    # 1. Load Games
    if not os.path.exists(INPUT_CSV):
        print("❌ Input CSV not found.")
        return
        
    df = pd.read_csv(INPUT_CSV)
    # Get unique dates strings YYYYMMDD -> YYYY-MM-DD
    dates = sorted(df['gameDate_home'].unique())
    
    print(f"📅 found {len(dates)} game dates to query.")
    
    # 2. Check Existing
    existing_dates = set()
    if os.path.exists(OUTPUT_CSV):
        try:
            ex_df = pd.read_csv(OUTPUT_CSV)
            existing_dates = set(ex_df['date_query'].unique())
            print(f"   Skipping {len(existing_dates)} dates already in output.")
        except:
            pass

    # 3. Iterate & Fetch
    count = 0
    header = not os.path.exists(OUTPUT_CSV)
    
    for d_int in dates:
        d_str = str(d_int)
        iso_date = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}"
        
        if iso_date in existing_dates:
            continue
            
        # SNAPSHOT TIME: 23:30 UTC = 6:30 PM ET
        # This is the "Closing" snapshot for the daily slate
        snapshot = f"{iso_date}T23:30:00Z"
        
        print(f"📡 {count+1} | Fetching Snapshot: {snapshot} ...")
        
        url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds-history"
        params = {
            'apiKey': API_KEY,
            'regions': 'us,eu,uk', # Maximises chance of finding Pinnacle
            'markets': 'h2h',
            'date': snapshot,
            'oddsFormat': 'decimal'
        }
        
        try:
            r = requests.get(url, params=params, timeout=15)
            
            if r.status_code == 429:
                print("   ⏳ Rate Limit. Sleeping 10s...")
                time.sleep(10)
                r = requests.get(url, params=params, timeout=15)
                
            if r.status_code == 200:
                data = r.json()
                api_games = data.get('data', [])
                
                rows = []
                for g in api_games:
                    # Parse Odds
                    odds_map, book, _ = get_h2h_odds(g)
                    if not odds_map: continue
                    
                    row = {
                        'date_query': iso_date,
                        'game_id_api': g['id'],
                        'commence_time': g['commence_time'],
                        'home_team': g['home_team'],
                        'away_team': g['away_team'],
                        'bookmaker': book
                    }
                    
                    # Fuzzy / Exact Match prices to Home/Away columns
                    # The odds_map keys are Team Names.
                    # We map them to 'home_odds' and 'away_odds'
                    
                    h_name = g['home_team']
                    a_name = g['away_team']
                    
                    row['home_odds'] = odds_map.get(h_name)
                    row['away_odds'] = odds_map.get(a_name)
                    
                    rows.append(row)
                
                if rows:
                    save_df = pd.DataFrame(rows)
                    # Filter for valid odds
                    save_df = save_df.dropna(subset=['home_odds', 'away_odds'])
                    
                    save_df.to_csv(OUTPUT_CSV, mode='a', header=header, index=False)
                    header = False
                    print(f"   ✅ Saved {len(save_df)} games for {iso_date}")
                else:
                    print(f"   ⚠️  No games found/parsed for {iso_date}")
                    
            else:
                print(f"   ❌ API Error: {r.status_code}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            
        count += 1
        time.sleep(1.2) # Conservative rate limit
        
        # Log progress every 10 batches
        if count % 10 == 0:
             print(f"   ... Processed {count} days.")

if __name__ == "__main__":
    run_backfill()
