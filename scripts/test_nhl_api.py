import requests
import json
import pandas as pd

def fetch_nhl_goalie_sample():
    # NHL API Endpoint for Goalie Summary (Game-by-Game)
    # limit=5 just to verify schema
    url = "https://api.nhle.com/stats/rest/en/goalie/summary"
    params = {
        "isAggregate": "false",
        "isGame": "true",
        "sort": '[{"property":"gameDate","direction":"DESC"}]',
        "start": 0,
        "limit": 5,
        "factCayenneExp": "gamesPlayed>=1",
        "cayenneExp": 'gameDate>="2022-10-01" and gameDate<="2023-04-15" and gameTypeId=2' # Regular season 22-23
    }
    
    print(f"🕵️‍♂️ Fetching sample from NHL API: {url}")
    try:
        r = requests.get(url, params=params)
        print(f"Status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            if 'data' in data and len(data['data']) > 0:
                print(f"✅ Success! Got {len(data['data'])} records.")
                df = pd.DataFrame(data['data'])
                print("\n📊 Sample Columns:")
                print(list(df.columns))
                print("\n📝 Sample Row:")
                print(df[['gameDate', 'goalieFullName', 'teamAbbrev', 'saves', 'goalsAgainst', 'decision']].to_string(index=False))
                
                # Check for critical ID columns
                if 'playerId' in df.columns and 'gameId' in df.columns:
                    print("\n✅ Critical IDs found: playerId, gameId")
                else:
                    print("\n⚠️  Missing critical IDs!")
            else:
                print("⚠️  No data returned.")
        else:
            print(f"❌ API Error: {r.text}")

    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    fetch_nhl_goalie_sample()
