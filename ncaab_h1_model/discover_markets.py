import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('ODDS_API_KEY')
SPORT = 'basketball_ncaab'

def discover():
    # 1. Get Events
    print(f"Fetching events for {SPORT}...")
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/events"
    res = requests.get(url, params={'apiKey': API_KEY, 'regions': 'us'})
    
    if res.status_code != 200:
        print(f"Failed to get events: {res.status_code}")
        return

    events = res.json()
    if not events:
        print("No upcoming events found.")
        return

    # Pick a FUTURE game
    import datetime
    now = datetime.datetime.utcnow().isoformat()
    
    future_events = [e for e in events if e['commence_time'] > now]
    if not future_events:
        print("No future events found.")
        return
        
    game = future_events[0]
    game_id = game['id']
    print(f"\nChecking markets for: {game['home_team']} vs {game['away_team']}")
    print(f"Start Time: {game['commence_time']}")
    
    # 2. Discover Available Markets
    print(f"Discovering market keys for game: {game_id}")
    url_markets = f"https://api.the-odds-api.com/v4/sports/{SPORT}/events/{game_id}/markets"
    params = {'apiKey': API_KEY, 'regions': 'us'}
    
    res = requests.get(url_markets, params=params)
    
    if res.status_code == 200:
        data = res.json()
        print(f"\n✅ Success! Found the following market keys for {game['home_team']} vs {game['away_team']}:")
        
        # Aggregate keys across bookmakers
        found_keys = set()
        for book in data.get('bookmakers', []):
            for market in book.get('markets', []):
                found_keys.add(market['key'])
        
        for k in sorted(found_keys):
            print(f"- {k}")
            
    else:
        print(f"\n❌ Failed: {res.status_code}")
        print(res.text)

if __name__ == "__main__":
    discover()
