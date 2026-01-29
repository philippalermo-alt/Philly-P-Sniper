from player_props_model import PlayerPropsPredictor
from db.connection import get_db
import pandas as pd

print("🕵️ Testing UCL Cross-Reference Logic on Remote...")

# 1. Instantiate Model with UCL
model = PlayerPropsPredictor(league="Champions_League", season="2025")

# 2. Test specific player known to be in DB (e.g. Salah, Vinicius Jr)
# Check DB for a valid player first
conn = get_db()
cur = conn.cursor()
cur.execute("SELECT player_name FROM player_stats WHERE league='EPL' LIMIT 1")
test_player = cur.fetchone()[0]
cur.close()
conn.close()

print(f"👉 Testing with known player: {test_player}")

# 3. Call the method directly
stats = model.get_player_stats_any_league(test_player)

if stats is not None and not stats.empty:
    print(f"✅ SUCCESS: Found {len(stats)} rows for {test_player}.")
    print(f"   Leagues found: {stats['league'].unique()}")
else:
    print(f"❌ FAILURE: No stats found for {test_player} using cross-ref.")

# 4. Integrate with regular flow
print("👉 Testing integration into get_player_rolling_stats...")
rolling = model.get_player_rolling_stats(test_player)
if rolling:
    print("✅ Integration SUCCESS: Rolling stats generated.")
    print(rolling)
else:
    print("❌ Integration FAILURE: get_player_rolling_stats returned None.")
