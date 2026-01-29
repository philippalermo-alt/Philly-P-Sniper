import pandas as pd
import requests
import os
import sys
import time
import json
from datetime import datetime, timedelta, timezone

# Ensure project root is in path
sys.path.append(os.getcwd())

from data.sources.nhl_goalies_lwl import fetch_lwl_goalies
from utils.team_names import normalize_team_name

# Configuration
API_KEY = os.getenv("ODDS_API_KEY")
SPORT = "icehockey_nhl"
REGIONS = "us,us2" 
MARKETS = "totals"
ODDS_FORMAT = "decimal"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
OUTPUT_FILE = "Hockey Data/nhl_totals_odds_live.csv" 

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def fetch_nhl_odds():
    log(f"Starting NHL Totals Live Ingest -> {OUTPUT_FILE}")
    
    if not API_KEY:
        log("❌ FATAL: ODDS_API_KEY not found.")
        sys.exit(1)
        
    # 1. Fetch Starters (LeftWingLock)
    log("Fetching Starters from LeftWingLock...")
    goalie_map = {}
    try:
        goalie_map = fetch_lwl_goalies()
    except Exception as e:
        log(f"⚠️ Starter Fetch Failed: {e}. Proceeding without goalies.")
        
    # 2. Fetch upcoming games (Odds API)
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": REGIONS,
        "markets": "h2h,totals", # FETCH BOTH
        "oddsFormat": ODDS_FORMAT
    }
    
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        log(f"❌ API Error: {resp.status_code} {resp.text}")
        sys.exit(1)
        
    data = resp.json()
    if not isinstance(data, list):
        log("❌ Unexpected API response format")
        sys.exit(1)
        
    results = []
    
    # Priority: DraftKings > FanDuel > Pinnacle > Bovada > Others
    PREFERRED = ['draftkings', 'fanduel', 'pinnacle', 'bovada', 'betmgm']
    
    for event in data:
        game_id = event['id']
        home = event['home_team']
        away = event['away_team']
        commence = event['commence_time']

        # -------------------------------------------------------------
        # FILTER: Skip Started Games (Prevent Live Odds Leakage)
        # -------------------------------------------------------------
        try:
            # API Format: 2026-01-29T00:00:00Z
            dt_commence = datetime.strptime(commence, DATE_FORMAT).replace(tzinfo=timezone.utc)
            if dt_commence < datetime.now(timezone.utc):
                log(f"⚠️ Skipping Started Game: {home} vs {away} (Commence: {commence})")
                continue
        except Exception as e:
            log(f"⚠️ Date Parse Warn: {commence} - {e}")
            # If parse fails, default to processed or skip? 
            # Safer to process if unsure, but for robustness skip.
            pass
        # -------------------------------------------------------------
        
        # Determine best book
        books = event.get('bookmakers', [])
        best_book = None
        
        # Sort books by preference
        avail_books = {b['key']: b for b in books}
        for p in PREFERRED:
            if p in avail_books:
                best_book = avail_books[p]
                break
        
        if not best_book and books:
            best_book = books[0] # Fallback
            
        if best_book:
            markets = best_book.get('markets', [])
            
            # Extract Totals
            totals = next((m for m in markets if m['key'] == 'totals'), None)
            total_line, over_price, under_price = None, None, None
            
            if totals and totals.get('outcomes'):
                total_line = totals['outcomes'][0].get('point')
                over_price = next((o['price'] for o in totals['outcomes'] if o['name'] == 'Over'), None)
                under_price = next((o['price'] for o in totals['outcomes'] if o['name'] == 'Under'), None)
                
            # Extract Moneyline (H2H)
            h2h = next((m for m in markets if m['key'] == 'h2h'), None)
            home_price, away_price = None, None
            
            if h2h and h2h.get('outcomes'):
                home_price = next((o['price'] for o in h2h['outcomes'] if o['name'] == home), None)
                away_price = next((o['price'] for o in h2h['outcomes'] if o['name'] == away), None)

            # We need at least one valid market to proceed with a row
            if (total_line and over_price) or (home_price and away_price):
                # Resolve Starters
                n_home = normalize_team_name(home)
                n_away = normalize_team_name(away)
                
                h_info = goalie_map.get(n_home, {})
                a_info = goalie_map.get(n_away, {})
                
                results.append({
                    "game_id": game_id, # Stable ID from Odds API
                    "game_date": commence[:10],
                    "home_team": home,
                    "away_team": away,
                    "total_line_close": total_line,
                    "over_price_close": over_price,
                    "under_price_close": under_price,
                    "home_moneyline": home_price,
                    "away_moneyline": away_price,
                    "bookmaker": best_book['title'],
                    "snapshot_timestamp": datetime.now().isoformat(),
                    "commence_time_utc": commence,
                    # Starters
                    "home_starter": h_info.get('starter'),
                    "home_goalie_status": h_info.get('status'),
                    "away_starter": a_info.get('starter'),
                    "away_goalie_status": a_info.get('status')
                })

    if results:
        df = pd.DataFrame(results)
        df.to_csv(OUTPUT_FILE, index=False)
        log(f"✅ Saved {len(df)} live odds (with starters) to {OUTPUT_FILE}")
        
        # Stats
        with_starters = df['home_starter'].notna().sum()
        log(f"📊 Games with Home Starter: {with_starters}/{len(df)}")
    else:
        log("⚠️ No active odds found.")

if __name__ == "__main__":
    fetch_nhl_odds()
