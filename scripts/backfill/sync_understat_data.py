import time
import logging
from understat_client import UnderstatClient
from database import get_db, safe_execute
from datetime import datetime

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("backfill_understat.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BackfillUnderstat")

def get_existing_match_ids():
    """Return a set of match IDs that have already been scraped."""
    conn = get_db()
    if not conn:
        logger.error("Could not connect to DB.")
        return set()
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT match_id FROM player_stats")
        rows = cur.fetchall()
        return {row[0] for row in rows}
    except Exception as e:
        logger.error(f"Error fetching existing match IDs: {e}")
        return set()
    finally:
        conn.close()

def save_match_data(match_data, league, season):
    """Insert match player stats into DB."""
    conn = get_db()
    if not conn:
        return False
        
    try:
        cur = conn.cursor()
        match_id = match_data['match_id']
        players = match_data.get('players', [])
        
        logger.info(f"Saving {len(players)} players for match {match_id}...")
        
        for p in players:
            sql = """
                INSERT INTO player_stats (
                    match_id, player_id, team_id, team_name, player_name, position,
                    minutes, shots, goals, assists, xg, xa, 
                    xg_chain, xg_buildup, season, league
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, 
                    %s, %s, %s, %s, %s, %s, 
                    %s, %s, %s, %s
                ) ON CONFLICT (match_id, player_id) DO UPDATE SET
                    team_name = EXCLUDED.team_name,
                    season = EXCLUDED.season, -- Ensure season is filled
                    league = EXCLUDED.league
            """
            params = (
                match_id,
                p.get('id'),
                p.get('team_id'),
                p.get('team_name'),
                p.get('player'),
                p.get('position'),
                int(p.get('time', 0)),
                int(p.get('shots', 0)),
                int(p.get('goals', 0)),
                int(p.get('assists', 0)),
                float(p.get('xG', 0)),
                float(p.get('xA', 0)),
                float(p.get('xGChain', 0)),
                float(p.get('xGBuildup', 0)),
                season,
                league
            )
            safe_execute(cur, sql, params)

        # INSERT MATCH METADATA
        try:
            # Check for flat match_info structure (Selenium)
            match_info = match_data.get('match_info')
            
            if match_info:
                # Flat Structure
                h_title = match_info.get('team_h')
                a_title = match_info.get('team_a')
                h_goals = int(match_info.get('h_goals', 0))
                a_goals = int(match_info.get('a_goals', 0))
                h_xg = float(match_info.get('h_xg', 0))
                a_xg = float(match_info.get('a_xg', 0))
                
                # Forecast (h_w = Home Win Prob)
                f_w = float(match_info.get('h_w', 0))
                f_d = float(match_info.get('h_d', 0))
                f_l = float(match_info.get('h_l', 0))
                
                date_val = match_info.get('date')

                # VALIDATION (Flat Structure)
                if h_goals == 0 and a_goals == 0 and h_xg == 0.0 and a_xg == 0.0:
                    logger.warning(f"⚠️ SUSPICIOUS DATA (Flat) for {match_id}. metrics are zero. Skipping.")
                    return False
            else:
                # Fallback to Nested Structure (Legacy/Requests)
                h = match_data.get('h', {})
                a = match_data.get('a', {})
                forecast = match_data.get('forecast', {})
                
                h_title = h.get('title')
                a_title = a.get('title')
                h_goals = int(h.get('goals', match_data.get('goals', {}).get('h', 0)))
                a_goals = int(a.get('goals', match_data.get('goals', {}).get('a', 0)))
                h_xg = float(h.get('xG', 0))
                a_xg = float(a.get('xG', 0))
                
                # VALIDATION: Reject suspicious zeros (both goals AND xG are 0)
                # Exception: 0-0 game might have non-zero xG. 
                # Exact 0.0 xG is extremely rare for a played match.
                if h_goals == 0 and a_goals == 0 and h_xg == 0.0 and a_xg == 0.0:
                    # Check if match is actually future/postponed?
                    # match_data['isResult'] should be True.
                    logger.warning(f"⚠️ SUSPICIOUS DATA for {match_id}: Goals=0, xG=0. Skipping save.")
                    return False

                f_w = float(forecast.get('w', 0))
                f_d = float(forecast.get('d', 0))
                f_l = float(forecast.get('l', 0))
                date_val = match_data.get('date')

            sql_match = """
                INSERT INTO matches (
                    match_id, league, season, date, 
                    home_team, away_team, 
                    home_goals, away_goals, 
                    home_xg, away_xg,
                    forecast_w, forecast_d, forecast_l
                ) VALUES (
                    %s, %s, %s, %s, 
                    %s, %s, 
                    %s, %s, 
                    %s, %s,
                    %s, %s, %s
                ) ON CONFLICT (match_id) DO UPDATE SET
                    league = EXCLUDED.league,
                    season = EXCLUDED.season,
                    date = EXCLUDED.date,
                    home_team = EXCLUDED.home_team,
                    away_team = EXCLUDED.away_team,
                    home_goals = EXCLUDED.home_goals,
                    away_goals = EXCLUDED.away_goals,
                    home_xg = EXCLUDED.home_xg,
                    away_xg = EXCLUDED.away_xg,
                    forecast_w = EXCLUDED.forecast_w,
                    forecast_d = EXCLUDED.forecast_d,
                    forecast_l = EXCLUDED.forecast_l
            """

            params_match = (
                str(match_id), league, str(season), date_val,
                h_title, a_title,
                h_goals, a_goals,
                h_xg, a_xg,
                f_w, f_d, f_l
            )
            safe_execute(cur, sql_match, params_match)
            
        except Exception as e:
            logger.warning(f"Metadata save failed for {match_id}: {e}")
            # Non-critical, continue since player stats are saved

        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error saving match {match_data.get('match_id')}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def sync_daily(league="EPL", season="2025"):
    logger.info(f"Starting Daily Sync for {league} {season}")
    
    # 1. Init Client (Headless)
    client = UnderstatClient(headless=True)
    
    # 2. Get Schedule
    matches = client.get_league_matches(league, season)
    if not matches:
        logger.warning(f"No matches returned for {league} {season}")
        client.quit()
        return

    completed_matches = [m for m in matches if m['is_result']]
    logger.info(f"Schedule: {len(matches)} total, {len(completed_matches)} completed.")
    
    # 3. Filter Existing
    existing_ids = get_existing_match_ids()
    to_scrape = [m for m in completed_matches if str(m['id']) not in existing_ids]
    
    if not to_scrape:
        logger.info("✅ All completed matches are already in DB. No action needed.")
        client.quit()
        return

    logger.info(f"🔄 Found {len(to_scrape)} new matches to sync.")
    
    # 4. Iterate and Scrape
    count = 0
    for match in to_scrape:
        match_id = match['id']
        logger.info(f"[{count+1}/{len(to_scrape)}] Syncing {match['home_team']} vs {match['away_team']} (ID: {match_id})")
        
        data = client.get_match_data(match_id)
        if data:
            success = save_match_data(data, league, season)
            if success:
                logger.info(f"MATCH_SAVED: {match_id}")
            else:
                logger.error(f"MATCH_FAILED: {match_id}")
        else:
            logger.error(f"FETCH_FAILED: {match_id}")
            
        count += 1
        time.sleep(1.5) # Be polite
        
    client.quit()
    logger.info("Daily Sync Complete.")

if __name__ == "__main__":
    # Ensure DB is init
    from database import init_db
    init_db()
    
    # Big 5 Leagues
    LEAGUES = ["EPL", "La_liga", "Bundesliga", "Serie_A", "Ligue_1"]
    SEASON = "2025"
    
    for league in LEAGUES:
        logger.info(f"🚀 Starting Sync for {league}...")
        try:
            sync_daily(league, SEASON)
        except Exception as e:
            logger.error(f"Failed to sync {league}: {e}")
            
        time.sleep(5) # Cool down between leagues
