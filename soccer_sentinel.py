import time
import subprocess
import requests
from datetime import datetime, timedelta, timezone
from config import Config

# Sentinel Logic (Hourly Watchman)
# 1. Get Schedule
# 2. Find games starting in next 60 mins
# 3. Schedule Sniper execution (Sleep -> Fire)

def get_upcoming_soccer_games():
    """
    Fetch soccer games starting in next 60-90 mins via Odds API.
    """
    try:
        url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds" # Default EPL for prototype, usually iterates all
        # To support all soccer, we need to iterate list of soccer leagues.
        # For Sentinel V1, let's target 'upcoming' across all sports and filter by key 'soccer'
        
        # Actually better to just hit 'upcoming' for all and filter logic
        # But we need specific soccer keys.
        # Let's use a subset for now: EPL, La Liga, MLS, UCL.
        leagues = [
            'soccer_epl', 
            'soccer_spain_la_liga', 
            'soccer_uefa_champs_league',
            'soccer_usa_mls',
            'soccer_germany_bundesliga',
            'soccer_italy_serie_a',
            'soccer_france_ligue_one'
        ]
        
        games = []
        now = datetime.now(timezone.utc)
        limit = now + timedelta(minutes=90) # Look ahead 90 mins
        
        for league in leagues:
             # Odds API expects YYYY-MM-DDTHH:MM:SSZ (No microseconds)
             iso_now = now.replace(microsecond=0).isoformat().replace('+00:00', 'Z')
             iso_limit = limit.replace(microsecond=0).isoformat().replace('+00:00', 'Z')
             
             params = {
                 'apiKey': Config.ODDS_API_KEY,
                 'regions': 'us',
                 'markets': 'h2h',
                 'commenceTimeFrom': iso_now,
                 'commenceTimeTo': iso_limit
             }
             
             resp = requests.get(f"https://api.the-odds-api.com/v4/sports/{league}/odds", params=params)
             if resp.status_code == 200:
                 data = resp.json()
                 print(f"   📋 {league}: Found {len(data)} games.")
                 for g in data:
                     # Log every game found before filtering
                     start_dt = datetime.fromisoformat(g['commence_time'].replace('Z', '+00:00'))
                     print(f"      - {g['home_team']} vs {g['away_team']} @ {start_dt.strftime('%H:%M')} (ID: {g['id']})")
                     games.append(g)
             else:
                 print(f"   ⚠️ {league} Error: {resp.status_code} {resp.text}")
                     
        return games
        
    except Exception as e:
        print(f"⚠️ Sentinel Error scanning schedule: {e}")
        return []

def run_sentinel():
    print(f"🕵️ SOCCER SENTINEL: Scanning for imminent kickoffs...")
    games = get_upcoming_soccer_games()
    
    if not games:
        print("💤 No games found starting in the next 90 mins.")
        return

    print(f"👀 Found {len(games)} potential targets.")
    
    # Sort by commence time
    games.sort(key=lambda x: x['commence_time'])
    
    for g in games:
        home = g['home_team']
        away = g['away_team']
        commence = datetime.fromisoformat(g['commence_time'].replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        
        # Calculate Target Time: Kickoff - 35 mins (Give 5 mins buffer for script boot)
        target_time = commence - timedelta(minutes=35)
        
        wait_seconds = (target_time - now).total_seconds()
        
        if wait_seconds > 0:
            print(f"⏳ Game: {home} vs {away}. Kickoff: {commence}. Waiting {wait_seconds/60:.1f} mins to Snipe...")
            # We sleep? If multiple games, this blocks.
            # Ideally Sentinel should fork processes or use async.
            # Since we run hourly, and games align to :00 or :30, usually we wait for the first batch.
            # Simple V1: Sleep until the first game window, execute, then check next.
            # If wait is huge, we might block others? 
            # Solution: Sentinel runs hourly. Only picks up games where wait_seconds < 3600.
            
            time.sleep(wait_seconds)
            
        print(f"🔫 FIRE: Executing Sniper for {home} vs {away}")
        
        # Execute Sniper in Background (Don't block Sentinel if multiple games overlap)
        date_str = commence.strftime('%Y-%m-%d')
        subprocess.Popen([
            "python3", "soccer_sniper.py",
            "--home", home,
            "--away", away,
            "--date", date_str
        ])
        
        # Small stagger
        time.sleep(5)

if __name__ == "__main__":
    run_sentinel()
