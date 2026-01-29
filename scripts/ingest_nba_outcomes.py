
import pandas as pd
from datetime import datetime, timedelta
import requests
from db.connection import get_db
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def ingest_nba_outcomes():
    """
    Fetch outcome data for pending NBA games in `nba_predictions`.
    Sources:
    1. Internal `nba_scores_2025_26.csv` (if updated via nightly scan).
    2. Fallback to scraping or external API (Using simple scrape for now).
    
    Populates `nba_outcomes` table.
    """
    logger.info("🏀 Starting NBA Outcome Ingestion...")
    
    conn = get_db()
    if not conn:
        logger.error("❌ DB Connection Failed.")
        return
        
    try:
        cur = conn.cursor()
        
        # 1. Identity Pending Games (in Predictions but not in Outcomes)
        # We look for distinct game_ids in predictions that are missing in outcomes
        query = """
            SELECT DISTINCT p.game_id, p.game_date_est, p.home_team, p.away_team 
            FROM nba_predictions p
            LEFT JOIN nba_outcomes o ON p.game_id = o.game_id
            WHERE o.game_id IS NULL
            AND p.game_date_est < CURRENT_DATE
        """
        cur.execute(query)
        pending = cur.fetchall()
        
        if not pending:
            logger.info("✅ No pending NBA outcomes to ingest.")
            return

        logger.info(f"📋 Found {len(pending)} pending games to resolve.")
        
        # 2. Fetch Scores (Reuse existing scoring source logic if possible)
        # For simplicity in this script, we'll try to use the CSV first, 
        # or implement a lightweight scrape of BBRef or usage of 'nba_scores_*.csv'
        
        SCORE_FILE = "data/nba_scores_2025_26.csv"
        try:
            scores_df = pd.read_csv(SCORE_FILE)
            # Normalize dates
            scores_df['Date'] = pd.to_datetime(scores_df['Date']).dt.date
        except Exception as e:
            logger.warning(f"⚠️ Could not load {SCORE_FILE}: {e}")
            scores_df = pd.DataFrame()

        # 3. Resolve
        resolved_count = 0
        
        for row in pending:
            game_id, game_date, home, away = row
            
            # Match in Scores DF
            # Logic: Match Date + Team Names (Fuzzy or Exact)
            
            # Filter by date
            day_scores = scores_df[scores_df['Date'] == game_date] if not scores_df.empty else pd.DataFrame()
            
            match = None
            if not day_scores.empty:
                # Simple containment match
                for _, s_row in day_scores.iterrows():
                    # Visitor/Home columns
                    if (s_row['Visitor'] in away or away in s_row['Visitor']) and \
                       (s_row['Home'] in home or home in s_row['Home']):
                           match = s_row
                           break
            
            if match is not None:
                # Extract Scores
                try:
                    home_score = int(match['PTS.1']) # Home Points
                    away_score = int(match['PTS'])   # Visitor Points
                    total = home_score + away_score
                    home_win = 1 if home_score > away_score else 0
                    
                    logger.info(f"✅ Resolved {home} vs {away}: {home_score}-{away_score}")
                    
                    # Upsert Outcome
                    cur.execute("""
                        INSERT INTO nba_outcomes 
                        (game_id, game_date_est, home_team, away_team, home_score, away_score, total_points, home_win)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (game_id) DO UPDATE SET
                        home_score=EXCLUDED.home_score, away_score=EXCLUDED.away_score, 
                        total_points=EXCLUDED.total_points, home_win=EXCLUDED.home_win
                    """, (game_id, game_date, home, away, home_score, away_score, total, home_win))
                    
                    resolved_count += 1
                except ValueError:
                    logger.error(f"❌ Error parsing scores for {game_id}")
            else:
                logger.debug(f"⏳ Score not found for {home} vs {away} ({game_date})")
        
        conn.commit()
        logger.info(f"💾 Persisted {resolved_count} outcomes.")
        
    except Exception as e:
        logger.error(f"Outcome Ingestion Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    ingest_nba_outcomes()
