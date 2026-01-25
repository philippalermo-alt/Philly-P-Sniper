
from player_props_model import PlayerPropsPredictor
import pandas as pd

def test_math_fix():
    print("🧪 Testing Math Fix for Nicolas Jackson...")
    
    # 1. Mock Data (Jackson-like profile)
    # 5 games: 15 mins, 2 shots... 20 mins, 3 shots... etc.
    data = [
        {'player_name': 'Test Jackson', 'team_name': 'Mock FC', 'minutes': 15, 'shots': 2, 'xg': 0.7, 'xa': 0.0, 'xg_chain': 0.1, 'match_id': 1, 'position': 'FW', 'scraped_at': '2025-01-01'},
        {'player_name': 'Test Jackson', 'team_name': 'Mock FC', 'minutes': 20, 'shots': 1, 'xg': 0.2, 'xa': 0.0, 'xg_chain': 0.1, 'match_id': 2, 'position': 'FW', 'scraped_at': '2025-01-02'},
        {'player_name': 'Test Jackson', 'team_name': 'Mock FC', 'minutes': 10, 'shots': 1, 'xg': 0.1, 'xa': 0.0, 'xg_chain': 0.0, 'match_id': 3, 'position': 'FW', 'scraped_at': '2025-01-03'},
        {'player_name': 'Test Jackson', 'team_name': 'Mock FC', 'minutes': 25, 'shots': 2, 'xg': 0.5, 'xa': 0.0, 'xg_chain': 0.2, 'match_id': 4, 'position': 'FW', 'scraped_at': '2025-01-04'},
        {'player_name': 'Test Jackson', 'team_name': 'Mock FC', 'minutes': 12, 'shots': 1, 'xg': 0.2, 'xa': 0.0, 'xg_chain': 0.1, 'match_id': 5, 'position': 'FW', 'scraped_at': '2025-01-05'},
    ]
    
    # Instantiate with Mock Data override
    predictor = PlayerPropsPredictor(league="EPL", season="2025")
    predictor.data = pd.DataFrame(data)
    
    # 2. Run Algo
    stats = predictor.get_player_rolling_stats('Test Jackson')
    
    # 3. Print Results
    print("\n📊 Results:")
    print(f"Per 90 Pace (Shots): {stats['proj_shots_p90']}")
    print(f"Exp Minutes:         {stats['avg_mins_l5']}")
    print(f"Game Projection:     {stats['proj_shots_game']}")
    print(f"Prob 2+ Shots:       {stats['prob_2_shots']}%")
    
    # 4. Assert reasonableness
    if stats['proj_shots_game'] < 2.5 and stats['prob_2_shots'] < 80:
        print("\n✅ PASS: Math correctly scaled based on low minutes.")
    else:
        print("\n❌ FAIL: Probabilities equal to Per 90 pace (Too High).")

if __name__ == "__main__":
    test_math_fix()
