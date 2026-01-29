import requests
import os
import json

API_KEY = os.getenv("ODDS_API_KEY")
SPORT = "icehockey_nhl"
# Broader regions and markets
REGIONS = "us,us2,eu,uk"
MARKETS = "h2h,totals"
ODDS_FORMAT = "decimal"

# Target: Seattle vs Nashville, Nov 9 2022, 03:00 Z.
# Snapshot: 02:45 Z. 
DATE_STR = "2022-11-09T02:45:00Z"

url = f"https://api.the-odds-api.com/v4/historical/sports/{SPORT}/odds"
params = {
    "apiKey": API_KEY,
    "regions": REGIONS,
    "markets": MARKETS,
    "oddsFormat": ODDS_FORMAT,
    "date": DATE_STR,
    "bookmakers": "all"
}

print(f"Fetching debug snapshot for {DATE_STR}...")
resp = requests.get(url, params=params)
print(f"Status: {resp.status_code}")

if resp.status_code == 200:
    data = resp.json()
    # Handle wrapper
    if isinstance(data, dict) and 'data' in data:
        data = data['data']
        
    # Find Seattle vs Nashville
    found = False
    for event in data:
        if "Seattle" in event['home_team'] or "Nashville" in event['away_team']:
            print("Found Game:")
            print(json.dumps(event, indent=2))
            found = True
            break
    
    if not found:
        print("Game not found in snapshot.")
        # Print first event to see what *is* there
        if data:
            print("First event sample:")
            print(json.dumps(data[0], indent=2))
else:
    print(resp.text)
