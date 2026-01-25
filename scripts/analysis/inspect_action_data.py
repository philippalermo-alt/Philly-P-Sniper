
import requests
import re
import json
from config import Config

def inspect_action():
    # 1. Get Build ID
    headers = {
        'authority': 'www.actionnetwork.com',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    print("Fetching Build ID...")
    try:
        home_res = requests.get('https://www.actionnetwork.com/', headers=headers, timeout=10)
        match = re.search(r'"buildId":"(.*?)"', home_res.text)
        if not match:
            print("❌ Could not find buildId")
            return
        build_id = match.group(1)
        print(f"✅ Build ID: {build_id}")
    except Exception as e:
        print(f"❌ Error fetching home: {e}")
        return

    # 2. Get NCAAB Data
    url = f"https://www.actionnetwork.com/_next/data/{build_id}/ncaab/public-betting.json"
    print(f"Fetching Data from: {url}")
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        games = data.get('pageProps', {}).get('scoreboardResponse', {}).get('games', [])
        
        print(f"Found {len(games)} games.")
        
        found = False
        for g in games:
            teams = g.get('teams', [])
            team_map = {t.get('id'): t.get('full_name') for t in teams}
            
            # Look for TCU or OK State
            names = list(team_map.values())
            # Check if relevant game
            if any("TCU" in n or "OK State" in n or "Oklahoma" in n for n in names):
                found = True
                print("\n==============================================")
                print(f"MATCH FOUND: {names}")
                print("==============================================")
                
                # Inspect Markets
                markets = g.get('markets', {})
                # Find the one with event
                picked_event = None
                for _, book_data in markets.items():
                    ev = book_data.get('event', {})
                    if ev:
                        picked_event = ev
                        break
                
                if not picked_event:
                    print("No event data in markets.")
                    continue
                    
                # 1. Spread
                print("\n--- SPREAD ---")
                for outcome in picked_event.get('spread', []):
                    tid = outcome.get('team_id')
                    tname = team_map.get(tid)
                    bi = outcome.get('bet_info', {})
                    print(f"Team: '{tname}'")
                    print(f"  Money: {bi.get('money', {}).get('percent')}%")
                    print(f"  Bets:  {bi.get('tickets', {}).get('percent')}%")
                    
                # 2. Total
                print("\n--- TOTAL ---")
                for outcome in picked_event.get('total', []):
                    name = outcome.get('name')
                    side = outcome.get('side')
                    bi = outcome.get('bet_info', {})
                    print(f"Side: '{name}' ({side})")
                    print(f"  Money: {bi.get('money', {}).get('percent')}%")
                    print(f"  Bets:  {bi.get('tickets', {}).get('percent')}%")
                    
    except Exception as e:
        print(f"❌ Error details: {e}")

if __name__ == "__main__":
    inspect_action()
