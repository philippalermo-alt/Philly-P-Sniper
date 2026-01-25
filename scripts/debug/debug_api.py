import requests
from config import Config

headers = {'x-apisports-key': Config.FOOTBALL_API_KEY}
print(f"🔑 Key ends with: ...{Config.FOOTBALL_API_KEY[-4:] if Config.FOOTBALL_API_KEY else 'NONE'}")

# Check Status
url = "https://v1.hockey.api-sports.io/status"
print(f"🌐 Requesting: {url}")
try:
    r = requests.get(url, headers=headers)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.json()}")
except Exception as e:
    print(f"❌ Error: {e}")

# Check Game Statistics
url = "https://v1.hockey.api-sports.io/games/statistics?game=370289"
print(f"🌐 Requesting: {url}")
try:
    r = requests.get(url, headers=headers)
    print(f"Status: {r.status_code}")
    data = r.json()
    print(f"Results: {data.get('results')}")
    if data.get('results', 0) > 0:
        print(f"First Item: {data['response'][0]}")
except Exception as e:
    print(f"❌ Error: {e}")
