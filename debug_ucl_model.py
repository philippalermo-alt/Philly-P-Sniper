from db.connection import get_db
from models.soccer import SoccerModelV2
import pandas as pd

def check_ucl_status():
    print("search_ucl_status...")
    
    # 1. Check Historical Data
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM matches WHERE league='ChampionsLeague' OR league='soccer_uefa_champs_league'")
        count, min_d, max_d = cur.fetchone()
        print(f"📚 Historical UCL Matches in DB: {count}")
        print(f"   Range: {min_d} to {max_d}")
    except Exception as e:
        print(f"❌ DB Check Failed: {e}")
    finally:
        conn.close()

    # 2. Test Model Prediction (Alias Check)
    model = SoccerModelV2()
    
    # "Inter Milan" -> "inter" (Alias) -> matches DB "Inter" (normalized)
    # "Atletico Madrid" -> "atletico madrid" (Alias) -> matches DB "Atletico Madrid"
    h, a = "Inter Milan", "Atletico Madrid"
    print(f"\n🔮 Testing Prediction (Alias): {h} vs {a}")
    
    # Fake odds
    current_odds = {'over': 1.90, 'under': 1.90, 'line': 2.5}
    
    res = model.predict_match(h, a, "soccer_uefa_champs_league", current_odds)
    
    if res:
        print(f"   Prob Over 2.5: {res['prob_over']:.1%}")
        print(f"   Fair Odds:     {res['fair_odds']:.2f}")
        print(f"   Exp Score:     {res['exp_score']}")
        print(f"   Home Win:      {res['home_win']:.1%}")
    else:
        print("❌ Model returned None (Prediction Failed)")

if __name__ == "__main__":
    check_ucl_status()
