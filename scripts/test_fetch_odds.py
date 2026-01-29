import requests
import time
import sys
from datetime import datetime
from db.connection import get_db
from config.settings import Config

# Usage: python3 scripts/test_fetch_odds.py

API_KEY = Config.ODDS_API_KEY
BASE_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds-history"

def test_fetch():
    print("🧪 Starting 5-Game/1-Day Test Pull...")
    
    conn = get_db()
    cur = conn.cursor()
    
    # 1. Pick a random recent date (e.g. from Nov 2023)
    # This ensures we get real data.
    cur.execute("SELECT DISTINCT game_date FROM nba_historical_games WHERE game_date >= '2023-11-01' LIMIT 1")
    row = cur.fetchone()
    
    if not row:
        print("❌ No games found in DB to test with.")
        return

    test_date = row[0] # datetime.date
    date_str = test_date.strftime("%Y-%m-%d")
    snapshot_iso = f"{date_str}T23:30:00Z"
    
    print(f"📅 Selected Test Date: {date_str}")
    print(f"📡 Requesting Snapshot: {snapshot_iso}")
    
    params = {
        'apiKey': API_KEY,
        'regions': 'us,eu',
        'markets': 'h2h,spreads,totals',
        'date': snapshot_iso
    }
    
    resp = requests.get(BASE_URL, params=params)
    
    print(f"🔄 API Status Code: {resp.status_code}")
    print(f"📉 Quota Cost (Header): {resp.headers.get('x-requests-used', '?')}/{resp.headers.get('x-requests-remaining', '?')}")
    
    if resp.status_code != 200:
        print(f"❌ Error: {resp.text}")
        return
        
    data = resp.json()
    events = data.get('data', [])
    print(f"✅ Received {len(events)} events (Targeting ~5-10)")
    
    # Check mappings
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
    
    print("\n🧐 Inspecting Games:")
    
    matched_count = 0
    
    for i, evt in enumerate(events):
        home_team = evt['home_team']
        away_team = evt['away_team']
        commence_iso = evt['commence_time'] # e.g. 2024-04-28T19:30:00Z
        
        # Calculate Delta
        # snapshot_iso is string, commence_iso is string
        # Parse
        c_dt = datetime.fromisoformat(commence_iso.replace('Z', '+00:00'))
        s_dt = datetime.fromisoformat(snapshot_iso.replace('Z', '+00:00'))
        
        delta = c_dt - s_dt
        minutes = delta.total_seconds() / 60
        
        print(f"   Game {i+1}: {home_team} vs {away_team}")
        print(f"      🕒 Start: {commence_iso} | Snapshot: {snapshot_iso}")
        print(f"      ⏱️ Time Until Tip: {minutes:.1f} minutes")
        
        h_abbr = abbr_map.get(home_team, '???')
        a_abbr = abbr_map.get(away_team, '???')
        
        # Check DB Match (Fuzzy +/- 1 Day)
        # API Date usually matches, but DB might be "Day After" (UTC vs Local)
        # or API returns "Upcoming" for tomorrow.
        # Check DB Match (Robust: Fuzzy Date + Either Team as Home)
        # API might have Home/Away swapped or different convention.
        # We just need to find the game involving these two teams on this date.
        cur.execute("""
            SELECT game_id, home_team_name FROM nba_historical_games 
            WHERE (home_team_name = %s OR home_team_name = %s)
            AND game_date >= %s - INTERVAL '1 DAY' 
            AND game_date <= %s + INTERVAL '1 DAY'
        """, (h_abbr, a_abbr, test_date, test_date))
        db_game = cur.fetchone()
        
        if db_game:
            print(f"      ✅ DB Match Found! Game ID: {db_game[0]}")
            matched_count += 1
            
            # Show Odds Sample
            pinnacle = next((b for b in evt['bookmakers'] if b['key'] == 'pinnacle'), None)
            dk = next((b for b in evt['bookmakers'] if b['key'] == 'draftkings'), None)
            
            if pinnacle:
                print(f"      🔹 Pinnacle Lines: Found {len(pinnacle['markets'])} markets")
            else:
                print(f"      🔸 Pinnacle Missing (Check Region?)")
                
            if dk:
                print(f"      🔹 DraftKings Lines: Found {len(dk['markets'])} markets")
        else:
            print(f"      ❌ NO DB Match for {h_abbr} on {date_str}")

    print(f"\n📊 Result: {matched_count}/{len(events)} Games Matched.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    test_fetch()
