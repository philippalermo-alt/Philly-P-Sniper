from understat_client import UnderstatClient
from sync_understat_data import save_match_data
import logging

# Configure basic logging to see everything
logging.basicConfig(level=logging.INFO)

def test_single_insert(match_id="22296", league="EPL", season="2023"):
    print(f"🕵️‍♀️ Debugging Insert for Match {match_id}")
    
    from config import Config
    print(f"🔌 Connecting to: {Config.DATABASE_URL}")
    
    client = UnderstatClient(headless=False) # See the browser
    try:
        print("Scraping...")
        data = client.get_match_data(match_id)
        if not data:
            print("❌ No data returned from Client!")
            return
            
        print(f"Data Keys: {data.keys()}")
        if 'h' in data:
            print(f"Home Data: {data['h']}")
        elif 'match_info' in data:
            print(f"Match Info: {data['match_info']}")
        else:
            print("❌ 'h' key missing!")
            
        print("Attempting Save...")
        result = save_match_data(data, league, season)
        if result:
            print("✅ save_match_data returned TRUE")
        else:
            print("❌ save_match_data returned FALSE")
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
    finally:
        client.quit()

if __name__ == "__main__":
    test_single_insert()
