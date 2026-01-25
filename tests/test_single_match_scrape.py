import logging
from understat_client import UnderstatClient
from database import get_db, safe_execute

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestScrape")

def test_single_match(match_id):
    logger.info(f"Testing scrape for Match ID: {match_id}")
    
    # 1. Scrape
    client = UnderstatClient(headless=True)
    try:
        data = client.get_match_data(match_id)
    except Exception as e:
        logger.error(f"Scrape failed: {e}")
        client.quit()
        return

    client.quit()

    if not data:
        logger.error("No data returned.")
        return

    # 2. Inspect Raw Data
    print("\n📦 RAW DATA SNAPSHOT:")
    print(f"Keys: {data.keys()}")
    
    match_info = data.get('match_info', {})
    print(f"\nMatch Info: {match_info}")
    
    h_title = match_info.get('team_h') or data.get('h', {}).get('title')
    h_goals = match_info.get('h_goals')
    
    print(f"\nEXTRACTED:")
    print(f"Home Team: {h_title}")
    print(f"Home Goals: {h_goals} (Type: {type(h_goals)})")
    
    if str(h_goals) == '0' and str(match_info.get('h_xg')) == '0':
        logger.error("⚠️ DATA LOOKS EMPTY (Zeros detected)")
    else:
        logger.info("✅ Data looks valid.")

    # 3. Simulate DB Save
    logger.info("Saving to DB for verification...")
    from sync_understat_data import save_match_data
    save_match_data(data, "TEST_LEAGUE", "2024")
    
    # 4. Verify DB
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT home_team, home_goals, home_xg FROM matches WHERE match_id = %s", (str(match_id),))
    row = cursor.fetchone()
    conn.close()
    
    print(f"\n🔍 DB ROW VERIFICATION:")
    print(row)

if __name__ == "__main__":
    # Use a real match ID from the logs (e.g. 28351 - PSG vs Auxerre)
    test_single_match(28351)
