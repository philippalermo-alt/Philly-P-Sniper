
import logging
from lineup_client import get_confirmed_lineup
from config import Config

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_lineup_fetch():
    print(f"Testing Lineup Fetch with API Key: {Config.FOOTBALL_API_KEY[:5]}...")
    
    # Test Case 1: Known fixture (need a real example or just see if it hits API and fails gracefully vs crashes)
    # We will try a fuzzy match that likely exists today or handled gracefully
    # "Rennes" vs "Lorient" was the user case.
    # Note: If game isn't today, it returns None (which is correct behavior, not crash).
    
    # Let's try to fetch a game from a league we support (EPL or Ligue 1)
    # If no games today, it should return None nicely.
    
    print("\nTest 1: Rennes vs Lorient (User Case)")
    # league_key='soccer_france_ligue_one' -> ID 61
    res = get_confirmed_lineup('soccer_france_ligue_one', 'Rennes', 'Lorient')
    print(f"Result: {res}")
    
    # Test 2: Man City vs Arsenal (Hypothetical)
    print("\nTest 2: Man City vs Arsenal (EPL)")
    res2 = get_confirmed_lineup('soccer_epl', 'Man City', 'Arsenal')
    print(f"Result 2: {res2}")

if __name__ == "__main__":
    test_lineup_fetch()
