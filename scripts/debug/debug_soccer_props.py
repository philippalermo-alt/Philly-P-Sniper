
import requests
import json
import os
from dotenv import load_dotenv

# Try loading from .env, but usually env vars are injected in Docker
load_dotenv()
API_KEY = os.getenv("ODDS_API_KEY")

if not API_KEY:
    print("❌ NO API KEY FOUND IN ENV")
    exit(1)

SPORT = "soccer_epl"
REGIONS = "us"
MARKETS = "player_goal_scorer_anytime,player_shots_on_goal,player_shots_total_over_under"

def inspect_odds():
    print(f"🕵️‍♂️ INSPECTING {SPORT} PROPS...")
    
    # 1. Get Events
    url_events = f"https://api.the-odds-api.com/v4/sports/{SPORT}/events"
    params_events = {
        'apiKey': API_KEY,
        'regions': REGIONS,
        'commenceTimeFrom': None, # Default to now
        'commenceTimeTo': None    # Default to unspecified (next 7 days? or default)
    }
    
    print(f"👉 Fetching Events from {url_events}")
    res = requests.get(url_events, params=params_events)
    events = res.json()
    
    if not isinstance(events, list):
        print(f"❌ Error getting events: {events}")
        return

    print(f"✅ Found {len(events)} events.")
    if len(events) == 0:
        return

    # Pick the first one
    event = events[0]
    print(f"🔬 Drilling into Event: {event['home_team']} vs {event['away_team']} ({event['id']})")
    
    # 2. Get Odds - Try Individual Markets to see what works
    # PDF Confirmations:
    # - player_goal_scorer_anytime (Anytime Goal)
    # - player_shots (Total Shots O/U) - replaces player_shots_total_over_under
    # - player_shots_on_target (Shots on Target O/U) - replaces player_shots_on_goal
    
    url_odds = f"https://api.the-odds-api.com/v4/sports/{SPORT}/events/{event['id']}/odds"
    market_list = ["player_goal_scorer_anytime", "player_shots", "player_shots_on_target"]
    
    for m in market_list:
        print(f"\n👉 Testing Market Key: {m}")
        params_odds = {
            'apiKey': API_KEY,
            'regions': REGIONS,
            'markets': m,
            'oddsFormat': 'american'
        }
        
        try:
            r_odds = requests.get(url_odds, params=params_odds)
            data = r_odds.json()
            
            bookmakers = data.get('bookmakers', [])
            print(f"   ✅ Found {len(bookmakers)} bookmakers for {m}")
            
            if len(bookmakers) > 0:
                print(f"      Books: {[b['key'] for b in bookmakers]}")
                # Dump one outcome
                for b in bookmakers:
                    if b.get('markets'):
                        print(f"      Sample ({b['key']}): {b['markets'][0]['outcomes'][0]}")
                        break
        except Exception as e:
            print(f"   ❌ Error fetching {m}: {e}")

if __name__ == "__main__":
    inspect_odds()
