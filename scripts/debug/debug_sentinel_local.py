import requests
from datetime import datetime, timedelta, timezone
import os

API_KEY = "7e6462d56d833b4f0102707ad16661e6"
leagues = ['soccer_uefa_champs_league']

now = datetime.now(timezone.utc)
limit = now + timedelta(minutes=90)

print(f"DEBUG: Now={now}, Limit={limit}")

for league in leagues:
    params = {
        'apiKey': API_KEY,
        'regions': 'us',
        'markets': 'h2h',
        'commenceTimeFrom': now.isoformat().replace('+00:00', 'Z'),
        'commenceTimeTo': limit.isoformat().replace('+00:00', 'Z')
    }
    
    url = f"https://api.the-odds-api.com/v4/sports/{league}/odds"
    print(f"DEBUG: Requesting {url} with params {params}")
    
    resp = requests.get(url, params=params)
    print(f"DEBUG: Status={resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"DEBUG: Found {len(data)} games.")
        for g in data:
            print(f" - {g['home_team']} vs {g['away_team']} @ {g['commence_time']}")
    else:
        print(f"DEBUG: Error {resp.text}")
