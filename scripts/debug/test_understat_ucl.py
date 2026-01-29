from understat_client import UnderstatClient

print("🕵️ Testing Understat Client for UCL support...")
client = UnderstatClient(headless=True)

# Try 'Champions_League' (Common slug)
LEAGUE = "Champions_League" # Understat often uses this, or 'ChampionsLeague'
SEASON = "2024" # Understat seasons are weird. 2024 might be active.

print(f"   Fetching matches for {LEAGUE} {SEASON}...")
matches = client.get_league_matches(LEAGUE, SEASON)

if matches:
    print(f"✅ Success! Found {len(matches)} matches.")
    print(f"   Sample: {matches[0]}")
else:
    print("❌ No matches found. Trying invalid league name?")

client.quit()
