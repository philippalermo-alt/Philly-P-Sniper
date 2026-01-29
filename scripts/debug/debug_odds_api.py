import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('ODDS_API_KEY')

# 1. Fetch Games (H2H) to get IDs and Times
url = f"https://api.the-odds-api.com/v4/sports/icehockey_nhl/odds/?apiKey={api_key}&regions=us,us2&markets=h2h"
print(f"🌐 Fetching Games from: {url}")

try:
    res = requests.get(url, timeout=15).json()
    if isinstance(res, dict) and 'message' in res:
        print(f"❌ API Error: {res['message']}")
        exit()
        
    print(f"Status: {len(res)} games found.")
    now_utc = datetime.now(timezone.utc)
    est_now = now_utc.astimezone(timezone(timedelta(hours=-5)))
    print(f"🕒 Current UTC Time: {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🕒 Current EST Time: {est_now.strftime('%I:%M %p')}")

    # Filter: Show ALL games
    print("\n📅 API Schedule Audit:")
    for g in res:
        commence = g['commence_time'] # UTC string
        mdt = datetime.fromisoformat(commence.replace('Z', '+00:00'))
        
        # Convert to EST (UTC-5) approx for logging
        est_time = mdt.astimezone(timezone(timedelta(hours=-5)))
        est_str = est_time.strftime('%I:%M %p')
        
        time_diff = (mdt - now_utc).total_seconds() / 3600
        
        home = g['home_team']
        away = g['away_team']
        game_id = g['id']
        
        status = "✅ FUTURE" if time_diff > 0 else "❌ STARTED"
        if -2.0 < time_diff < 2.0:
            status += " (NEAR KICKOFF)"
            
        print(f"[{est_str} EST] {away} @ {home} ({status}, Diff: {time_diff:.1f}h)")
        
        # Check props for games starting SOON or recently started
        # STRICT FILTER: Future Games Only (Prevent live/past leakage)
        if 0.1 < time_diff < 5:
            prop_url = f"https://api.the-odds-api.com/v4/sports/icehockey_nhl/events/{game_id}/odds?apiKey={api_key}&regions=us,us2&markets=player_shots_on_goal"
            try:
                p_res = requests.get(prop_url, timeout=10).json()
                if 'bookmakers' in p_res:
                    bk_count = len(p_res['bookmakers'])
                    print(f"      -> Props: {bk_count} bookmakers found.")
                else:
                    print(f"      -> Props: 0 bookmakers.")
            except:
                print("      -> Props: Error fetching.")
                
except Exception as e:
    print(f"❌ Error: {e}")
