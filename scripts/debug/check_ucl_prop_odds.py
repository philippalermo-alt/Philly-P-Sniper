from data.clients.odds_api import fetch_prop_odds
import json

SPORT = "soccer_uefa_champs_league"
MARKETS = "player_goal_scorer_anytime,player_shots"

print(f"🕵️ Checking Prop Odds for {SPORT}...", flush=True)
data = fetch_prop_odds(SPORT, markets=MARKETS)

if not data:
    print("❌ NO ODDS DATA RETURNED.")
else:
    print(f"✅ Found Odds for {len(data)} players.")
    # Print sample
    keys = list(data.keys())
    if keys:
        p1 = keys[0]
        print(f"   Sample Player: {p1}")
        print(f"   Markets: {data[p1].keys()}")
