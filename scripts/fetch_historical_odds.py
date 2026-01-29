import requests
import time
import sys
from datetime import datetime, timedelta
import pytz
from db.connection import get_db, safe_execute
from config.settings import Config

# Usage: python3 scripts/fetch_historical_odds.py
# Strategy: High-Precision (Snapshot = Start Time)

API_KEY = Config.ODDS_API_KEY
BASE_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds-history"

def setup_odds_table():
    """Create the odds table if it doesn't exist."""
    print("🛠️ Setting up Odds Table...")
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nba_historical_odds (
            id SERIAL PRIMARY KEY,
            game_id TEXT, -- fk to nba_historical_games
            bookmaker TEXT,
            market_key TEXT, -- h2h, spreads, totals
            timestamp TIMESTAMP,
            
            -- Home
            home_price REAL,
            home_point REAL, -- for spread/total
            
            -- Away
            away_price REAL,
            away_point REAL,
            
            CONSTRAINT unique_odds UNIQUE (game_id, bookmaker, market_key)
        );
    """)
    conn.commit()
    conn.close()

def fetch_odds_precision():
    setup_odds_table()
    
    conn = get_db()
    cur = conn.cursor()
    
    # 1. Get Distinct Start Times (UTC)
    # Group games by start time to batch API calls.
    # Exclude games with NULL start time (should be none now).
    print("⏳ Fetching game schedule from DB...")
    cur.execute("""
        SELECT DISTINCT game_start_time 
        FROM nba_historical_games g
        WHERE game_start_time > '2021-01-01' -- Ensure we cover all history
        AND NOT EXISTS (
            SELECT 1 FROM nba_historical_odds o 
            WHERE o.game_id = g.game_id
            AND o.market_key = 'totals'
            AND o.home_price IS NOT NULL
        )
        ORDER BY game_start_time DESC
    """)
    times = [r[0] for r in cur.fetchall()]
    conn.close()
    
    print(f"📅 Found {len(times)} distinct start times (batches) for ~4000 games.")
    print(f"💰 Estimated Cost: {len(times) * 10} Credits.")
    
    batch_count = 0
    total_saved = 0
    
    for start_time in times:
        # start_time is datetime object (likely naive from DB, but represents UTC or Offset?)
        # Kaggle CSV had offset (e.g. -04:00). Postgres stores TIMESTAMP (no tz) or TIMESTAMPTZ?
        # My loader used `to_pydatetime()`. If `raw_ts` had offset, it might be preserved?
        # Let's assume `game_start_time` is accurately capturing the moment.
        # We need to format it as ISO8601 for API.
        
        # If naive, assume it implies the correct absolute time (or UTC).
        # Actually API needs ISO8601 with Z or offset.
        # Let's format it.
        
        # Timezone Handling (Critical for High Precision)
        # DB stores "Wall Time" (ET) based on 'gameDateTimeEst'.
        # Example: 20:30:00 (8:30 PM ET).
        # We need to convert this to UTC for the API. 
        # 8:30 PM ET -> 1:30 AM UTC (Next Day).
        
        if start_time.tzinfo is None:
            # Localize to Eastern
            eastern = pytz.timezone('US/Eastern')
            try:
                # Use is_dst=None to raise error if ambiguous, or False to pick standard?
                # Kaggle data is usually standard? Or clock time?
                # Best effort.
                loc_dt = eastern.localize(start_time)
                utc_dt = loc_dt.astimezone(pytz.utc)
            except Exception as e:
                # Fallback
                print(f"   ⚠️ TZ Error for {start_time}: {e}. Assuming UTC.")
                utc_dt = start_time
        else:
             utc_dt = start_time.astimezone(pytz.utc)
             
        iso_str = utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ") # Explicit format
        
        print(f"📡 Batch {batch_count+1}/{len(times)}: Snapshot at {iso_str} (Game Time: {start_time} ET)...")
        
        try:
            params = {
                'apiKey': API_KEY,
                'regions': 'us,eu', 
                'markets': 'h2h,spreads,totals',
                'date': iso_str
            }
            
            resp = requests.get(BASE_URL, params=params)
            
            if resp.status_code == 429:
                print("   ⏳ Rate Limited. Sleeping 5s...")
                time.sleep(5)
                continue
                
            if resp.status_code != 200:
                print(f"   ⚠️ API Error {resp.status_code}: {resp.text}")
                continue
                
            data = resp.json()
            events = data.get('data', [])
            
            # Map events to games starting AT THIS TIME
            # Fuzzy match team names
            conn = get_db()
            cur = conn.cursor()
            
            mapped_in_batch = 0
            
            for evt in events:
                home_team = evt['home_team']
                away_team = evt['away_team']
                
                # Normalize Names
                abbr_map = {
                    'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN', 'Charlotte Hornets': 'CHA',
                    'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE', 'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN',
                    'Detroit Pistons': 'DET', 'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
                    'Los Angeles Clippers': 'LAC', 'LA Clippers': 'LAC', 'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM',
                    'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN', 'New Orleans Pelicans': 'NOP',
                    'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC', 'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI',
                    'Phoenix Suns': 'PHX', 'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS',
                    'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS'
                }
                
                h_abbr = abbr_map.get(home_team)
                a_abbr = abbr_map.get(away_team)
                
                if not h_abbr or not a_abbr: continue
                
                # Find Game ID matching this exact time or close to it
                # We use the fuzzy +/- 1 day just in case date mismatch, BUT check mostly for team match
                cur.execute("""
                    SELECT game_id FROM nba_historical_games 
                    WHERE (home_team_name = %s OR home_team_name = %s)
                    AND game_start_time >= %s - INTERVAL '4 HOURS'
                    AND game_start_time <= %s + INTERVAL '4 HOURS'
                """, (h_abbr, a_abbr, start_time, start_time))
                row = cur.fetchone()
                
                if not row: continue
                gid = row[0]
                
                # Insert Odds (Same logic as before)
                bookmakers = evt.get('bookmakers', [])
                for book in bookmakers:
                    bk_key = book['key']
                    if bk_key not in ['pinnacle', 'draftkings', 'fanduel']: continue
                    
                    for mkt in book['markets']:
                        mkt_key = mkt['key']
                        h_price, a_price, h_point, a_point = None, None, None, None
                        
                        for out in mkt['outcomes']:
                            name = out['name']
                            
                            # Logic: H2H/Spreads use Team Name. Totals use Over/Under.
                            is_home = (name == home_team) or (name == 'Over')
                            is_away = (name == away_team) or (name == 'Under')
                            
                            if is_home:
                                h_price = out['price']
                                h_point = out.get('point')
                            elif is_away:
                                a_price = out['price']
                                a_point = out.get('point')
                                
                        cur.execute("""
                            INSERT INTO nba_historical_odds 
                            (game_id, bookmaker, market_key, timestamp, home_price, home_point, away_price, away_point)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (game_id, bookmaker, market_key) 
                            DO UPDATE SET timestamp = EXCLUDED.timestamp, home_price = EXCLUDED.home_price, home_point = EXCLUDED.home_point, 
                                          away_price = EXCLUDED.away_price, away_point = EXCLUDED.away_point
                        """, (gid, bk_key, mkt_key, iso_str, h_price, h_point, a_price, a_point))
                        
                mapped_in_batch += 1
                
            conn.commit()
            conn.close()
            
            if mapped_in_batch > 0:
                print(f"   ✅ Saved odds for {mapped_in_batch} games.")
                total_saved += mapped_in_batch
            else:
                print(f"   ⚠️ Batch Empty (No matches for {len(events)} events).")
                
                
            # Rate Limit Protection (User Approved 0.2s for this run)
            time.sleep(0.2) 
            
        except Exception as e:
            print(f"❌ Error in batch: {e}")
            time.sleep(1)
            
        batch_count += 1

    print(f"🎉 DONE. Saved odds for {total_saved} total games.")

if __name__ == "__main__":
    fetch_odds_precision()
