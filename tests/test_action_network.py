import requests
import re
import json

headers = {'User-Agent': 'Mozilla/5.0'}

def test_fetch():
    print("Fetching home page...")
    try:
        home_res = requests.get('https://www.actionnetwork.com/', headers=headers, timeout=10)
        print(f"Home page status: {home_res.status_code}")
        match = re.search(r'"buildId":"(.*?)"', home_res.text)
        if match:
            build_id = match.group(1)
            print(f"Found buildId: {build_id}")
        else:
            print("Could not find buildId")
            return
    except Exception as e:
        print(f"Error fetching home page: {e}")
        return

    endpoints = {
        'NCAAB': 'ncaab/public-betting',
    }
    
    # Original code used suffix adding .json, let's see if that works
    # https://www.actionnetwork.com/_next/data/{build_id}/{suffix}
    
    for sport, route in endpoints.items():
        suffix = f"{route}.json"
        target_url = f"https://www.actionnetwork.com/_next/data/{build_id}/{suffix}"
        print(f"Fetching {sport} from {target_url}")
        
        try:
            res = requests.get(target_url, headers=headers, timeout=10)
            print(f"Status for {sport}: {res.status_code}")
            if res.status_code == 200:
                data = res.json()
                page_props = data.get('pageProps', {})
                if not page_props:
                    print(f"No pageProps found for {sport}")
                    print(f"Keys in data: {list(data.keys())}")
                    continue
                    
                scoreboard = page_props.get('scoreboardResponse', {})
                games = scoreboard.get('games', [])
                print(f"Found {len(games)} games for {sport}")
                if games:
                    found_game = False
                    for g in games:
                        teams = g.get('teams', [])
                        team_map = {t.get('id'): t.get('full_name') for t in teams}
                        team_names = list(team_map.values())
                        if any("Yale" in name or "Columbia" in name for name in team_names):
                            found_game = True
                            print(f"\nFound Game: {team_names}")
                            markets = g.get('markets', {})
                            if isinstance(markets, dict) and markets:
                                # Iterate over ALL markets to see if there are multiple providers
                                for m_key, m_val in markets.items():
                                    print(f"  Market Key: {m_key}")
                                    if 'event' in m_val:
                                        event = m_val['event']
                                        if 'moneyline' in event:
                                            # print("\n    --- Moneyline ---")
                                            for outcome in event['moneyline']:
                                                tid = outcome.get('team_id')
                                                book_id = outcome.get('book_id')
                                                out_id = outcome.get('outcome_id') 
                                                tname = team_map.get(tid, f"Unknown ID {tid}")
                                                bi = outcome.get('bet_info', {})
                                                money = bi.get('money', {}).get('percent')
                                                tickets = bi.get('tickets', {}).get('percent')
                                                print(f"    Team: {tname} (ID: {tid}, Book: {book_id}) -> Money: {money}%, Tickets: {tickets}%")
                                        else:
                                            print("    No moneyline in this market")
                            else:
                                print("    No markets found")
                            break
                    
                    if not found_game:
                        print("Could not find Yale vs Columbia game")
            else:
                print(f"Failed to fetch {sport}: {res.text[:200]}")
        except Exception as e:
            print(f"Exception fetching {sport}: {e}")

if __name__ == "__main__":
    test_fetch()
