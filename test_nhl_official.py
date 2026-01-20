import requests
import json

# The "New" NHL Edge API (2024 standard)
# Endpoint for Connor McDavid (Player ID 8478402) or just team stats
# Let's try to get comprehensive stats.
# The new API is split by player.
# A robust scraper would hit the "Summary" endpoint if it exists, or iterate teams.

print("🏒 Testing Official NHL API...")

# Try the "Stats API" (older but often still active or redirected)
url_old = "https://api.nhle.com/stats/rest/en/skater/summary?isAggregate=false&isGame=false&sort=[{%22property%22:%22points%22,%22direction%22:%22DESC%22}]&start=0&limit=5&cayenneExp=seasonId=20242025%20and%20gameTypeId=2"
print(f"\n🌐 Requesting (Stats API): {url_old}")
try:
    r = requests.get(url_old, timeout=10)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"Top Scorer: {data['data'][0]['skaterFullName']} - {data['data'][0]['points']} pts")
    else:
        print("Failed.")
except Exception as e:
    print(f"❌ Error: {e}")

# Try the "Edge API" (New, v1) - Roster endpoint
# https://api-web.nhle.com/v1/roster/{team_abbr}/current
url_new = "https://api-web.nhle.com/v1/roster/EDM/current"
print(f"\n🌐 Requesting (Edge API - EDM Roster): {url_new}")
try:
    r = requests.get(url_new, timeout=10)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"First Forward: {data['forwards'][0]['firstName']['default']} {data['forwards'][0]['lastName']['default']}")
    else:
        print("Failed.")
except Exception as e:
    print(f"❌ Error: {e}")
