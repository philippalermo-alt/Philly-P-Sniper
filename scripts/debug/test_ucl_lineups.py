from lineup_client import get_confirmed_lineup
from config import Config
from datetime import datetime

# Test Params (Based on verified pipeline output: Barcelona vs FC Copenhagen)
league_key = "soccer_uefa_champs_league"
home_team = "Barcelona"
away_team = "FC Copenhagen"

print(f"🧪 TESTING UCL LINEUP FETCH for {home_team} vs {away_team}...")
print(f"   League Key: {league_key}")
print(f"   Mapped ID: {Config.SOCCER_LEAGUE_IDS.get(league_key)}")
print(f"   Date: {datetime.now().strftime('%Y-%m-%d')}")

# Execute
lineup = get_confirmed_lineup(league_key, home_team, away_team)

if lineup:
    print(f"✅ SUCCESS! Found {len(lineup)} starters.")
    print(f"   Sample: {list(lineup)[:5]}")
else:
    print("❌ FAILURE: No lineup returned.")
