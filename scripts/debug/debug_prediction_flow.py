
from soccer_client import SoccerClient
from config import Config

def test_rolling_logic():
    print("⚽️ Testing SoccerClient Rolling xG Logic...")
    
    if not Config.FOOTBALL_API_KEY:
        print("❌ Missing API Key")
        return

    sc = SoccerClient()
    
    # Man City ID = 50
    team_id = 50
    print(f"   Fetching Last 3 Games for Team ID {team_id} (Man City)...")
    
    data = sc.get_team_rolling_xg(team_id, last_n=3)
    
    print("\n📊 Results:")
    print(f"   Games Found: {data['games_count']}")
    print(f"   Avg xG:  {data['avg_xg']}")
    print(f"   Avg xGA: {data['avg_xga']}")
    
    if data['games_count'] > 0:
        print("✅ SUCCESS: Rolling Data Calculated.")
    else:
        print("❌ FAILURE: No data returned.")

if __name__ == "__main__":
    test_rolling_logic()
