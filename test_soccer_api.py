import requests
from datetime import datetime, timedelta
import os

FOOTBALL_API_KEY = os.getenv('FOOTBALL_API_KEY', '63c7309e5d52482af750f2ac188f62d3')

print("🔍 TESTING API-FOOTBALL API\n")

# Test API status
print("1️⃣ Testing API Status...")
status_url = "https://v3.football.api-sports.io/status"
headers = {'x-apisports-key': FOOTBALL_API_KEY}

try:
    response = requests.get(status_url, headers=headers, timeout=10).json()
    print(f"   Account: {response.get('response', {})}")
    print(f"   Requests Today: {response.get('response', {}).get('requests', {})}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n2️⃣ Testing EPL Fixtures (League ID 39)...")

# Test current season fixtures
today = datetime.now().strftime('%Y-%m-%d')
tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

for season in [2025, 2024]:
    print(f"\n   Trying Season {season}:")
    for date in [today, tomorrow]:
        url = f"https://v3.football.api-sports.io/fixtures?league=39&season={season}&date={date}"
        
        try:
            response = requests.get(url, headers=headers, timeout=10).json()
            results = response.get('results', 0)
            print(f"      {date}: {results} fixtures")
            
            if results > 0:
                fixtures = response.get('response', [])
                for fixture in fixtures[:2]:  # Show first 2
                    home = fixture['teams']['home']['name']
                    away = fixture['teams']['away']['name']
                    fid = fixture['fixture']['id']
                    print(f"         • {away} @ {home} (ID: {fid})")
        except Exception as e:
            print(f"      ❌ Error: {e}")

print("\n3️⃣ Testing Predictions API...")
# Try to get prediction for a fixture
test_fixture_id = "1234567"  # We'll get real ID from above
url = f"https://v3.football.api-sports.io/predictions?fixture={test_fixture_id}"

try:
    response = requests.get(url, headers=headers, timeout=10).json()
    print(f"   Response: {response.get('results', 0)} predictions")
    if 'errors' in response:
        print(f"   ⚠️ Errors: {response['errors']}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n✅ Debug complete!")
print("\nNEXT STEPS:")
print("- If 'Requests Today' shows you're at limit → wait 24h or upgrade plan")
print("- If Season 2025 shows 0 fixtures → leagues haven't started 2025 season yet")
print("- If Season 2024 shows fixtures → need to adjust code to use 2024-2025 season")