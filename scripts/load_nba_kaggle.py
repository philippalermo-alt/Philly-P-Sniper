import pandas as pd
import numpy as np
from db.connection import get_db
from datetime import datetime
import sys

# Usage: python3 scripts/load_nba_kaggle.py

def load_data():
    print("📂 Loading NBA Data...")
    
    # 1. Load Games (Scores + Meta)
    try:
        df_games = pd.read_csv('games.csv')
        # Columns: gameId,gameDateTimeEst,hometeamName,awayteamName,homeScore,awayScore...
        print(f"   Games: {df_games.shape}")
    except Exception as e:
        print(f"❌ Failed to load games.csv: {e}")
        return

    # 2. Load Advanced Stats
    try:
        df_adv = pd.read_csv('team_advanced.csv')
        # Columns: gameid,date,team,home,away,OFFRTG,EFG%,TOV%,OREB%,PACE...
        print(f"   Advanced: {df_adv.shape}")
    except Exception as e:
        print(f"❌ Failed to load team_advanced.csv: {e}")
        return

    # 3. Prepare for Merge
    # We join on (Date, HomeTeam). GameID might differ or be missing in one.
    
    # Normalize Dates
    df_games['date_norm'] = pd.to_datetime(df_games['gameDateTimeEst'], format='mixed', utc=True).dt.strftime('%Y-%m-%d')
    df_adv['date_norm'] = pd.to_datetime(df_adv['date'], format='mixed', utc=True).dt.strftime('%Y-%m-%d')
    
    # Normalize Team Names (Games has "Clippers", Adv has "LAC"?)
    team_map = {
        'Hawks': 'ATL', 'Celtics': 'BOS', 'Nets': 'BKN', 'Hornets': 'CHA', 'Bulls': 'CHI',
        'Cavaliers': 'CLE', 'Mavericks': 'DAL', 'Nuggets': 'DEN', 'Pistons': 'DET', 'Warriors': 'GSW',
        'Rockets': 'HOU', 'Pacers': 'IND', 'Clippers': 'LAC', 'Lakers': 'LAL', 'Grizzlies': 'MEM',
        'Heat': 'MIA', 'Bucks': 'MIL', 'Timberwolves': 'MIN', 'Pelicans': 'NOP', 'Knicks': 'NYK',
        'Thunder': 'OKC', 'Magic': 'ORL', '76ers': 'PHI', 'Suns': 'PHX', 'Trail Blazers': 'POR',
        'Kings': 'SAC', 'Spurs': 'SAS', 'Raptors': 'TOR', 'Jazz': 'UTA', 'Wizards': 'WAS'
    }
    
    df_games['home_abbr'] = df_games['hometeamName'].map(team_map)
    df_games['away_abbr'] = df_games['awayteamName'].map(team_map)
    
    # Filter valid games (Recent 3 COMPLETED Seasons + Current 2024-25)
    # Start: Oct 2021. End: July 2025.
    df_games = df_games[(df_games['date_norm'] >= '2021-10-01') & (df_games['date_norm'] <= '2025-07-01')]
    df_games = df_games.dropna(subset=['home_abbr', 'away_abbr'])
    
    print(f"   Games (Filtered 2021+): {df_games.shape}")

    # Prepare Advanced Data (Pivot Home/Away)
    df_adv_sub = df_adv.copy()
    
    # Isolate Home/Away stats within Adv dataset
    # If df_adv['team'] == df_adv['home'], it's home stats.
    df_adv_sub['is_home'] = df_adv_sub['team'] == df_adv_sub['home']
    
    # Split & Index
    adv_home = df_adv_sub[df_adv_sub['is_home']].set_index(['date_norm', 'team'])
    adv_away = df_adv_sub[~df_adv_sub['is_home']].set_index(['date_norm', 'team'])
    
    print("\n🔍 DEBUG KEYS:")
    print("   Adv Home Keys (First 5):", adv_home.index[:5].tolist())
    
    print("🚀 Ingesting...")
    
    conn = get_db()
    cur = conn.cursor()
    
    # Create Table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nba_historical_games (
            game_id TEXT PRIMARY KEY,
            season_id TEXT,
            game_date DATE,
            game_date_est DATE,
            game_start_time TIMESTAMP, -- New precise column
            home_team_id TEXT,
            home_team_name TEXT,
            away_team_id TEXT,
            away_team_name TEXT,
            home_score INTEGER,
            away_score INTEGER,
            home_efg_pct REAL,
            away_efg_pct REAL,
            home_tov_pct REAL,
            away_tov_pct REAL,
            home_orb_pct REAL,
            away_orb_pct REAL,
            pace REAL
        );
    """)
    # Add column if missing (Migration)
    try:
        cur.execute("ALTER TABLE nba_historical_games ADD COLUMN IF NOT EXISTS game_start_time TIMESTAMP")
    except:
        conn.rollback()
        
    conn.commit()
    
    debug_misses = 0
    skipped = 0
    count = 0
    
    for idx, row in df_games.iterrows():
        try:
            g_date = row['date_norm']
            
            # Precise Time Parsing
            # Format in CSV: 2021-10-19T19:30:00-04:00 (ISO-like)
            # We want to store it as TIMESTAMP (UTC preference, or offset-aware)
            raw_ts = row['gameDateTimeEst']
            try:
                g_start = pd.to_datetime(raw_ts).to_pydatetime()
            except:
                g_start = None

            h_team = row['home_abbr']
            a_team = row['away_abbr']
            gid = str(row['gameId'])
            
            # Lookup Stats
            h_stats = None
            a_stats = None
            
            try:
                h_stats = adv_home.loc[(g_date, h_team)]
                a_stats = adv_away.loc[(g_date, a_team)]
            except KeyError:
                skipped += 1
                if debug_misses < 5:
                    print(f"❌ Missing Key: ({g_date}, {h_team}) OR ({g_date}, {a_team})")
                    debug_misses += 1
                continue

            # Extract Values
            # Handle duplicate index (rare double headers?) -> take first
            if isinstance(h_stats, pd.DataFrame): h_stats = h_stats.iloc[0]
            if isinstance(a_stats, pd.DataFrame): a_stats = a_stats.iloc[0]
            
            h_efg = float(h_stats.get('EFG%', 0))
            a_efg = float(a_stats.get('EFG%', 0))
            h_tov = float(h_stats.get('TOV%', 0))
            a_tov = float(a_stats.get('TOV%', 0))
            h_orb = float(h_stats.get('OREB%', 0))
            a_orb = float(a_stats.get('OREB%', 0))
            pace = float(h_stats.get('PACE', 0))

            cur.execute("""
                INSERT INTO nba_historical_games (
                    game_id, season_id, game_date, game_date_est, game_start_time,
                    home_team_id, home_team_name, away_team_id, away_team_name,
                    home_score, away_score,
                    home_efg_pct, away_efg_pct,
                    home_tov_pct, away_tov_pct,
                    home_orb_pct, away_orb_pct,
                    pace
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (game_id) DO UPDATE SET
                    game_start_time = EXCLUDED.game_start_time -- Backfill time
            """, (
                gid, '2024', g_date, g_date, g_start,
                str(row['hometeamId']), h_team, str(row['awayteamId']), a_team,
                int(row['homeScore']), int(row['awayScore']),
                h_efg, a_efg,
                h_tov, a_tov,
                h_orb, a_orb,
                pace
            ))
            count += 1
            if count % 500 == 0:
                conn.commit()
                print(f"   Saved {count} games...")
                
        except Exception as e:
            conn.rollback() # Reset transaction so next row can try
            # Only print first few errors
            if count == 0 and skipped < 10:
                 print(f"❌ SQL/Code Error {gid}: {e}")
            pass
            
    conn.commit()
    print(f"✅ Ingestion Complete. Saved {count} games. Skipped {skipped} (missing advanced stats).")
    cur.close()
    conn.close()

if __name__ == "__main__":
    load_data()
