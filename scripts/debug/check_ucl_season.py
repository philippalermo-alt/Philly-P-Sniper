import requests
from config import Config
from datetime import datetime

# UCL League ID = 2
LID = 2
HEADERS = {'x-apisports-key': Config.FOOTBALL_API_KEY}

def check_season(season_year):
    print(f"🕵️ Checking UCL (League {LID}) for Season {season_year}...", flush=True)
    url = f"https://v3.football.api-sports.io/fixtures?league={LID}&season={season_year}&date=2026-01-28"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()
        count = data.get('results', 0)
        print(f"   RESULTS: {count} fixtures.", flush=True)
        if count > 0:
            print(f"   SAMPLE: {data['response'][0]['teams']['home']['name']} vs {data['response'][0]['teams']['away']['name']}")
            return True
    except Exception as e:
        print(f"   ERROR: {e}")
    return False

print("--- DIAGNOSING UCL SEASON ---")
current_date = datetime.now().strftime('%Y-%m-%d')
print(f"Date: {current_date}")

s24 = check_season(2024)
s25 = check_season(2025)

if s24 and not s25:
    print("🚨 FINDING: UCL Data is under Season 2024 (Not 2025!)")
elif s25 and not s24:
    print("✅ FINDING: UCL Data is correctly under Season 2025.")
elif s24 and s25:
    print("❓ FINDING: Both seasons return data? Likely overlap.")
else:
    print("❌ FINDING: No data found for either season! (Check Date/API)")
