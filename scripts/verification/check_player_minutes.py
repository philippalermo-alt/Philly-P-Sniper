from player_props_model import PlayerPropsPredictor
from utils import log
import pandas as pd

def check_minutes():
    # Players found in diagnostic with high edges
    targets = [
        ("EPL", "Ollie Watkins"),
        ("EPL", "David Brooks"),
        ("La_liga", "Vedat Muriqi"),
        ("Bundesliga", "Ragnar Ache"),
        ("Serie_A", "Gabriele Piccinini")
    ]

    print("🔍 Checking Eligibility (Filter: Avg Mins L5 >= 45 AND Sample >= 5)...")
    
    for league, player in targets:
        try:
            predictor = PlayerPropsPredictor(league=league, season="2025")
            stats = predictor.get_player_rolling_stats(player)
            
            if not stats:
                print(f"❌ {player} ({league}): Not found in model data.")
                continue
                
            l5 = stats.get('avg_mins_l5', 0)
            sample = stats.get('sample_matches', 0)
            
            passes = l5 >= 45 and sample >= 5
            
            status = "✅ PASS" if passes else "⛔ FAIL"
            print(f"{status} {player}: L5 Mins={l5:.1f}, Sample={sample}")
            
        except Exception as e:
            print(f"⚠️ Error checking {player}: {e}")

if __name__ == "__main__":
    check_minutes()
