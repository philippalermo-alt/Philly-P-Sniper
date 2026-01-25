
from utils import normalize_team_name

def test_parsing():
    print("🧪 Testing Matchup Parsing Logic...")
    
    # Mock Data
    player_team = "Chelsea"
    matchup_str = "Arsenal vs Chelsea"
    
    # Logic from prop_sniper.py
    parts = matchup_str.split(' vs ')
    opponent_name = None
    
    if len(parts) == 2:
        t1, t2 = parts[0], parts[1]
        if normalize_team_name(player_team) in normalize_team_name(t1):
            opponent_name = t2
        elif normalize_team_name(player_team) in normalize_team_name(t2):
            opponent_name = t1
            
    print(f"Hero: {player_team}")
    print(f"Matchup: {matchup_str}")
    print(f"Detected Opponent: {opponent_name}")
    
    if opponent_name == "Arsenal":
        print("✅ PASS: Correctly identified Arsenal as opponent.")
    else:
        print(f"❌ FAIL: Expected Arsenal, got {opponent_name}")

    # Test 2: Reverse
    matchup_str_2 = "Chelsea vs Liverpool"
    parts = matchup_str_2.split(' vs ')
    opp_2 = None
    if len(parts) == 2:
        t1, t2 = parts[0], parts[1]
        if normalize_team_name(player_team) in normalize_team_name(t1):
            opp_2 = t2
        elif normalize_team_name(player_team) in normalize_team_name(t2):
            opp_2 = t1
            
    if opp_2 == "Liverpool":
        print("✅ PASS: Correctly identified Liverpool as opponent.")
    else:
        print(f"❌ FAIL: Expected Liverpool, got {opp_2}")

if __name__ == "__main__":
    test_parsing()
