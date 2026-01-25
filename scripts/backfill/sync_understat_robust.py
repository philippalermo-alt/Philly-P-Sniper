import time
import logging
import random
from understat_client import UnderstatClient
from database import get_db, safe_execute
from sync_understat_data import get_existing_match_ids, save_match_data

logger = logging.getLogger("BackfillHistory")

def sync_daily_robust(league, season, restart_every=10):
    logger.info(f"🛡️ Starting ROBUST Sync for {league} {season}")
    
    # 1. Init Client (Headless)
    client = UnderstatClient(headless=True)
    
    try:
        # 2. Get Schedule
        matches = client.get_league_matches(league, season)
        if not matches:
            logger.warning(f"No matches returned for {league} {season}")
            return

        completed_matches = [m for m in matches if m['is_result']]
        
        # 3. Filter Existing
        existing_ids = get_existing_match_ids()
        to_scrape = [m for m in completed_matches if str(m['id']) not in existing_ids]
        
        if not to_scrape:
            logger.info("✅ All completed matches are already in DB.")
            return

        logger.info(f"🔄 Found {len(to_scrape)} new matches to sync.")
        
        # 4. Iterate and Scrape with Restarts
        count = 0
        for match in to_scrape:
            match_id = match['id']
            logger.info(f"[{count+1}/{len(to_scrape)}] Syncing {match['home_team']} vs {match['away_team']} (ID: {match_id})")
            
            # Restart Driver Check
            if count > 0 and count % restart_every == 0:
                logger.info("♻️ Restarting WebDriver to free memory...")
                client.quit()
                time.sleep(2)
                client = UnderstatClient(headless=True)
            
            try:
                data = client.get_match_data(match_id)
                if data:
                    success = save_match_data(data, league, season)
                    if success:
                        logger.info(f"MATCH_SAVED: {match_id}")
                    else:
                        logger.error(f"MATCH_FAILED: {match_id}")
                else:
                    logger.error(f"FETCH_FAILED: {match_id}")
            except Exception as e:
                logger.error(f"CRITICAL FETCH ERROR {match_id}: {e}")
                # Force restart on error
                client.quit()
                time.sleep(5)
                client = UnderstatClient(headless=True)
                
            count += 1
            # Variable sleep to avoid patterns
            # Accelerated logic for critical deadline
            # sleep_time = 2.0 + random.random() * 2.0
            time.sleep(0.4) 
            
    finally:
        if client:
            client.quit()
    
    logger.info("Robust Sync Complete.")
