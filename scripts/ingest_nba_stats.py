import time
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from nba_api.stats.endpoints import leaguegamelog, boxscoretraditionalv2, boxscoreadvancedv2
from db.connection import get_db

# Constants
SEASONS = ['2023-24', '2024-25'] # Reduced scope for testing
SEASON_TYPE = 'Regular Season'
BATCH_SIZE = 50

# CUSTOM HEADERS FOR NBA API
custom_headers = {
    'Host': 'stats.nba.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:61.0) Gecko/20100101 Firefox/61.0',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://stats.nba.com/',
    'Origin': 'https://stats.nba.com',
    'Connection': 'keep-alive',
    'x-nba-stats-origin': 'stats',
    'x-nba-stats-token': 'true'
}

def get_game_list(season):
    """Fetch all games for a season."""
    print(f"📅 Fetching Schedule for {season}...", flush=True)
    try:
        print(f"   (Requesting {season} from NBA API...)", flush=True)
        log = leaguegamelog.LeagueGameLog(season=season, season_type_all_star=SEASON_TYPE, headers=custom_headers)
        print("   (Request Complete)", flush=True)
        df = log.get_data_frames()[0]
        # Keep unique Game IDs
        games = df['GAME_ID'].unique()
        print(f"   found {len(games)} games.")
        return games
    except Exception as e:
        print(f"❌ Error fetching schedule: {e}")
        return []

def process_game(game_id, conn):
    """Fetch and store stats for a single game."""
    try:
        # 1. Traditional Stats (Score, Date)
        trad = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id)
        df_trad = trad.get_data_frames()[1] # Team Stats
        
        if df_trad.empty:
            print(f"   ⚠️ No Trad Data for {game_id}")
            return False

        # 2. Advanced Stats (Four Factors)
        adv = boxscoreadvancedv2.BoxScoreAdvancedV2(game_id=game_id)
        df_adv = adv.get_data_frames()[1] # Team Stats

        if df_adv.empty:
            print(f"   ⚠️ No Adv Data for {game_id}")
            return False

        # Identify Home/Away
        # In NBA API, usually row 0 is Away, row 1 is Home? OR check 'MATCHUP'
        # Usually we join on TEAM_ID.
        # Let's simplify: Sort by TEAM_ID or analyze 'MATCHUP' string containing vs/@
        # Actually df_trad has 'MATCHUP'. "GSW @ SAC" -> SAC is Home.
        
        # Merge Trad + Adv
        home_row = None
        away_row = None
        
        # We need to map team rows.
        # Let's pivot data.
        teams_data = {}
        for idx, row in df_trad.iterrows():
            tid = row['TEAM_ID']
            matchup = row['MATCHUP']
            is_home = ' vs. ' in matchup
            teams_data[tid] = {
                'is_home': is_home,
                'name': row['TEAM_NAME'],
                'score': row['PTS'],
                'trad': row
            }

        for idx, row in df_adv.iterrows():
            tid = row['TEAM_ID']
            if tid in teams_data:
                teams_data[tid]['adv'] = row
            
        home_team = next((d for d in teams_data.values() if d['is_home']), None)
        away_team = next((d for d in teams_data.values() if not d['is_home']), None)
        
        if not home_team or not away_team:
             # Fallback logic if ' vs. ' detection fails
             # If one team is home, other is away.
             pass

        if not home_team or not away_team:
            print(f"   ⚠️ Failed to identify Home/Away for {game_id}")
            return False

        # Extract Fields
        # Date comes from GameLog usually, or header. 
        # Trad stats doesn't always have date column in team view?
        # Use header info?
        # Actually easier to pass date in from GameLog or re-fetch summary.
        # Let's just use CURRENT_TIMESTAMP for now or parse from game list. 
        # ... Wait, we need accurate date for joining odds.
        # boxscoretraditionalv2 DOES NOT return date in team dict clearly.
        # We should pass metadata from the GameLog loop.
        
        # REFACTOR: Pass game_meta from main loop
        pass 
        
    except Exception as e:
        print(f"❌ Error processing {game_id}: {e}")
        return False
    return True

# ...
# NOTE: Writing efficient bulk script is tricky in one go. 
# I will write a concise version that fetches GameLog first (which has date/teams/score), 
# then enriches with Advanced Stats.

def run_ingestion():
    conn = get_db()
    cur = conn.cursor()
    
    for season in SEASONS:
        print(f"\n🏀 Processing {season}...")
        try:
            log = leaguegamelog.LeagueGameLog(season=season, season_type_all_star=SEASON_TYPE)
            df_log = log.get_data_frames()[0]
        except:
            print("Failed to fetch log")
            continue
            
        # Group by GameID to get one row per game (Log has 2 rows per game)
        # We need to reconstruct the matchup
        # Group by GAME_ID
        games = df_log.groupby('GAME_ID')
        
        count = 0
        for game_id, rows in games:
            # Check if exists
            cur.execute("SELECT 1 FROM nba_historical_games WHERE game_id=%s", (game_id,))
            if cur.fetchone():
                continue # Skip if exists
            
            try:
                # 1. Parse Basic Info from Log
                # Row with ' vs. ' is Home Team perspective usually?
                # or just parse MATCHUP column
                
                row_home = None
                row_away = None
                
                for idx, r in rows.iterrows():
                    if ' vs. ' in r['MATCHUP']:
                        row_home = r
                    elif ' @ ' in r['MATCHUP']:
                        row_away = r
                
                if row_home is None or row_away is None:
                    continue
                    
                game_date_str = row_home['GAME_DATE'] # '2023-10-24'
                game_date_est = datetime.strptime(game_date_str, '%Y-%m-%d')
                
                # 2. Fetch Advanced Stats (API Call)
                time.sleep(0.600) # Rate Limit (avoid ban)
                adv = boxscoreadvancedv2.BoxScoreAdvancedV2(game_id=game_id, headers=custom_headers)
                df_adv = adv.get_data_frames()[1]
                
                if df_adv.empty: continue
                
                # Match Advanced stats to Home/Away Team IDs
                hid = row_home['TEAM_ID']
                aid = row_away['TEAM_ID']
                
                home_adv = df_adv[df_adv['TEAM_ID'] == hid].iloc[0]
                away_adv = df_adv[df_adv['TEAM_ID'] == aid].iloc[0]
                
                # 3. Insert
                cur.execute("""
                    INSERT INTO nba_historical_games (
                        game_id, season_id, game_date, game_date_est,
                        home_team_id, home_team_name, away_team_id, away_team_name,
                        home_score, away_score,
                        home_efg_pct, away_efg_pct,
                        home_tov_pct, away_tov_pct,
                        home_orb_pct, away_orb_pct,
                        home_ft_rate, away_ft_rate,
                        pace
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    game_id, season, game_date_est, game_date_est,
                    str(hid), row_home['TEAM_NAME'], str(aid), row_away['TEAM_NAME'],
                    int(row_home['PTS']), int(row_away['PTS']),
                    float(home_adv.get('EFG_PCT', 0)), float(away_adv.get('EFG_PCT', 0)),
                    float(home_adv.get('TM_TOV_PCT', 0)), float(away_adv.get('TM_TOV_PCT', 0)),
                    float(home_adv.get('OREB_PCT', 0)), float(away_adv.get('OREB_PCT', 0)),
                    float(home_adv.get('FTA_RATE', 0)), float(away_adv.get('FTA_RATE', 0)),
                    float(home_adv.get('PACE', 0))
                ))
                conn.commit()
                count += 1
                if count % 10 == 0: print(f"   Saved {count} games...")
                
            except Exception as e:
                print(f"❌ Failed {game_id}: {e}")
                # continue without stopping
                
    cur.close()
    conn.close()

if __name__ == "__main__":
    run_ingestion()
