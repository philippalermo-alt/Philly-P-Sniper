from data.clients.odds_api import fetch_prop_odds
import json

def test():
    leagues = [
        'soccer_epl', 
        'soccer_germany_bundesliga',
        'soccer_italy_serie_a',
        'soccer_spain_la_liga',
        'soccer_france_ligue_one'
    ]
    
    for league in leagues:
        print(f"\n🚀 Fetching {league} (Props Test)...")
        data = fetch_prop_odds(league, markets="player_goal_scorer_anytime")
        
        if data:
            print(f"✅ Success! Found data for {len(data)} players.")
            # Print first 2
            keys = list(data.keys())[:2]
            for k in keys:
                print(f"{k}: {data[k]}")
            return # Stop after first success
        else:
            print(f"❌ No data for {league}")
            
    print("\n⚠️ No data found in ANY league. Check API Key or Date Window.")

if __name__ == "__main__":
    test()
