import requests
import json
from config.settings import Config

def inspect_json():
    print("🌍 Fetching Live Odds JSON...")
    # Requesting standard markets
    url = f"https://api.the-odds-api.com/v4/sports/soccer_uefa_champs_league/odds/?apiKey={Config.ODDS_API_KEY}&regions=us&markets=h2h,totals&oddsFormat=decimal"
    
    res = requests.get(url)
    if res.status_code != 200:
        print(f"❌ API Error: {res.text}")
        return
        
    games = res.json()
    if not games:
        print("❌ No games found.")
        return
        
    # Pick the first game
    g = games[0]
    print(f"⚽ Game: {g['home_team']} vs {g['away_team']} (ID: {g['id']})")
    
    print("\n🔍 MARKETS FOUND:")
    found_totals = False
    
    for bk in g['bookmakers']:
        print(f"  📖 Bookie: {bk['key']}")
        for m in bk['markets']:
            print(f"     - {m['key']}")
            if m['key'] == 'totals':
                found_totals = True
                print("       VALUES:")
                for o in m['outcomes']:
                    print(f"         {o['name']} {o.get('point')}: {o['price']}")
                    
    if not found_totals:
        print("\n❌ NO 'totals' MARKET FOUND in Main Response.")
        print("💡 Suggestion: Check if 'alternate_totals' is needed or 'us' region has lines.")

if __name__ == "__main__":
    inspect_json()
