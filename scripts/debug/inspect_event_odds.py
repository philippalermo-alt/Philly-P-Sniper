import requests
import json
from config.settings import Config

def inspect_event():
    EVENT_ID = "c3660e36f59975281119b7c3da4a9a87" 
    print(f"🌍 Fetching Event Odds for {EVENT_ID}...")
    
    # Requesting alternate_totals
    url = f"https://api.the-odds-api.com/v4/sports/soccer_uefa_champs_league/events/{EVENT_ID}/odds?apiKey={Config.ODDS_API_KEY}&regions=us&markets=alternate_totals&oddsFormat=decimal"
    
    res = requests.get(url)
    if res.status_code != 200:
        print(f"❌ API Error: {res.text}")
        return
        
    g = res.json()
    print(f"⚽ Game: {g['home_team']} vs {g['away_team']}")
    
    print("\n🔍 MARKETS FOUND:")
    
    for bk in g['bookmakers']:
        print(f"  📖 Bookie: {bk['key']}")
        for m in bk['markets']:
            print(f"     - {m['key']}")
            if m['key'] == 'alternate_totals':
                print("       VALUES (First 5):")
                sorted_outcomes = sorted(m['outcomes'], key=lambda x: float(x.get('point', 0)))
                for o in sorted_outcomes[:5]:
                    print(f"         {o['name']} {o.get('point')}: {o['price']}")

if __name__ == "__main__":
    inspect_event()
