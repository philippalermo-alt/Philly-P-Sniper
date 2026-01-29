import requests
from config import Config
import json

def get_live_odds():
    sport_key = 'soccer_france_ligue_one'
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    
    params = {
        'apiKey': Config.ODDS_API_KEY,
        'regions': 'us',
        'markets': 'totals',
        'oddsFormat': 'decimal'
    }
    
    print(f"📡 Fetching Live Odds for {sport_key}...")
    try:
        from datetime import datetime, timezone 
        # API returns UTC ISO8601
        
        res = requests.get(url, params=params)
        data = res.json()
        
        target_game = "Auxerre" # Match Auxerre vs PSG
        
        found = False
        for event in data:
            home = event['home_team']
            away = event['away_team']
            commence = event['commence_time']
            
            # FILTER: Skip Started
            try:
                dt_commence = datetime.strptime(commence, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                if dt_commence < datetime.now(timezone.utc):
                    # print(f"Skipping Started: {home} vs {away}") 
                    continue
            except:
                pass

            if target_game in home or target_game in away:
                print(f"✅ Found Match: {home} vs {away}")
                found = True
                
                # Get Totals
                books = event.get('bookmakers', [])
                # Prefer DraftKings/FanDuel
                best_book = next((b for b in books if b['key'] in ['draftkings', 'fanduel', 'bovada']), None) or (books[0] if books else None)
                
                if best_book:
                    print(f"📖 Bookmaker: {best_book['title']}")
                    markets = best_book.get('markets', [])
                    totals = next((m for m in markets if m['key'] == 'totals'), None)
                    
                    if totals:
                        # Find 2.5 line or closest
                        line_25 = next((x for x in totals['outcomes'] if abs(x.get('point', 0) - 2.5) < 0.1 and x['name'] == 'Over'), None)
                        
                        if line_25:
                            o_price = line_25['price']
                            u_price = next((x['price'] for x in totals['outcomes'] if abs(x.get('point', 0) - 2.5) < 0.1 and x['name'] == 'Under'), 0.0)
                            print(f"💰 Line: 2.5 | Over: {o_price} | Under: {u_price}")
                        else:
                            # Print whatever line they have
                            first = totals['outcomes'][0]
                            pt = first.get('point')
                            print(f"⚠️ Main line is {pt}, not 2.5. Using closest.")
                            
                            o_price = next((x['price'] for x in totals['outcomes'] if x['name'] == 'Over'), 0.0)
                            u_price = next((x['price'] for x in totals['outcomes'] if x['name'] == 'Under'), 0.0)
                            print(f"💰 Line: {pt} | Over: {o_price} | Under: {u_price}")
                            
                else:
                    print("❌ No odds available yet.")
                    
        if not found:
            print("❌ Match not found in live odds.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_live_odds()
