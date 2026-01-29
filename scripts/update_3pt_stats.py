import pandas as pd
from db.connection import get_db
from nba_api.stats.endpoints import leaguegamelog

def update_3par():
    conn = get_db()
    cur = conn.cursor()
    
    # Add Columns if not exist
    try:
        cur.execute("ALTER TABLE nba_historical_games ADD COLUMN IF NOT EXISTS home_3par FLOAT")
        cur.execute("ALTER TABLE nba_historical_games ADD COLUMN IF NOT EXISTS away_3par FLOAT")
        conn.commit()
    except Exception as e:
        print(f"⚠️ Column Create Error: {e}")
        conn.rollback()
        
    SEASONS = ['2021-22', '2022-23', '2023-24', '2024-25']
    
    for s in SEASONS:
        print(f"🏀 Fetching Logs for {s}...")
        log = leaguegamelog.LeagueGameLog(season=s, season_type_all_star='Regular Season')
        df = log.get_data_frames()[0]
        
        # Group by Game
        games = df.groupby('GAME_ID')
        
        updates = []
        for gid, rows in games:
            # We need to ID home and away
            home_row = None
            away_row = None
            
            for idx, r in rows.iterrows():
                if ' vs. ' in r['MATCHUP']:
                    home_row = r
                elif ' @ ' in r['MATCHUP']:
                    away_row = r
            
            if home_row is None or away_row is None:
                continue
                
            # Calc 3PAr
            # Guard div by zero
            h_fga = home_row['FGA']
            h_3pa = home_row['FG3A']
            h_rate = h_3pa / h_fga if h_fga > 0 else 0.0
            
            a_fga = away_row['FGA']
            a_3pa = away_row['FG3A']
            a_rate = a_3pa / a_fga if a_fga > 0 else 0.0
            
            # DB IDs seem to be 8 digits (stripped 00 prefix)
            # API returns 10 digits (00 + 8 digits)
            if str(gid).startswith('00'):
                gid_db = str(gid)[2:]
            else:
                gid_db = str(gid)
            
            updates.append((h_rate, a_rate, gid_db))
            
        print(f"   Updating {len(updates)} games in DB...")
        if updates:
            print(f"   Sample Update: {updates[0]}")
            
        # Bulk Update? Or Loop? Loop is safe for now.
        # Use execute_values or executemany?
        # "UPDATE ... FROM VALUES" is Postgres specific but fast.
        # Let's use simple executemany.
        
        cur.executemany("""
            UPDATE nba_historical_games 
            SET home_3par = %s, away_3par = %s
            WHERE game_id = %s
        """, updates)
        
        # Verify one update
        if updates:
             chk_id = updates[0][2]
             cur.execute("SELECT home_3par FROM nba_historical_games WHERE game_id=%s", (chk_id,))
             res = cur.fetchone()
             print(f"   Verification Read for {chk_id}: {res}")
             
        conn.commit()
        
    cur.close()
    conn.close()
    print("✅ 3PAr Update Complete.")

if __name__ == "__main__":
    update_3par()
