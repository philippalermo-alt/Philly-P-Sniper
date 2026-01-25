import logging
import time
import argparse
import sys
from sync_understat_robust import sync_daily_robust

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BackfillHistory")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill historic soccer data")
    parser.add_argument("--league", type=str, help="Specific league (EPL, La_liga, etc). If omitted, runs all.")
    parser.add_argument("--season", type=str, help="Specific season (2023, 2024). If omitted, runs both.")
    
    args = parser.parse_args()
    
    # Ensure DB is init
    from database import init_db
    init_db()
    
    ALL_LEAGUES = ["EPL", "La_liga", "Bundesliga", "Serie_A", "Ligue_1"]
    ALL_SEASONS = ["2023", "2024"]
    
    # Determine scope
    target_leagues = [args.league] if args.league else ALL_LEAGUES
    target_seasons = [args.season] if args.season else ALL_SEASONS
    
    logger.info(f"🚀 STARTING BACKFILL | Leagues: {target_leagues} | Seasons: {target_seasons}")
    
    for season in target_seasons:
        for league in target_leagues:
            if league not in ALL_LEAGUES:
                logger.warning(f"⚠️ Skipping unknown league: {league}")
                continue
                
            logger.info(f"📅 PROCESSING: {league} {season}")
            try:
                sync_daily_robust(league, season)
            except Exception as e:
                logger.error(f"❌ Failed to sync {league} {season}: {e}")
                
            logger.info(f"zzz Sleeping 5s before next batch...")
            time.sleep(5)
            
    logger.info("🏁 BATCH COMPLETE.")
