from models.soccer import SoccerModelV2
from db.connection import get_db
import pandas as pd

def debug_cross_league():
    print("🔎 Initializing Manager...")
    model = SoccerModelV2()
    
    # 1. Check if we have stats for big teams
    targets = ["Manchester City", "Man City", "Real Madrid", "Arsenal", "Liverpool"]
    
    print("\n📊 Checking Team Stats in Memory:")
    for t in targets:
        if t in model.team_stats:
            s = model.team_stats[t]
            print(f"   ✅ {t}: Att={s['home_att']:.2f}, Def={s['home_def']:.2f}")
        else:
            print(f"   ❌ {t}: NOT FOUND (will default to 1.35)")

    # 2. Check Database Names
    conn = get_db()
    try:
        cur = conn.cursor()
        print("\n🗄 Checking DB Team Names (Sample):")
        cur.execute("SELECT DISTINCT home_team FROM matches WHERE home_team ILIKE '%Man%' OR home_team ILIKE '%Real%' LIMIT 10")
        rows = cur.fetchall()
        for r in rows:
            print(f"   DB: {r[0]}")
    finally:
        conn.close()

if __name__ == "__main__":
    debug_cross_league()
