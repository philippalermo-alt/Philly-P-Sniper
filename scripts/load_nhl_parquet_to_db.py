
import pandas as pd
import os
import psycopg2
from psycopg2.extras import execute_values
from db.connection import get_db

DATA_DIR = "data/nhl_processed"

def load_parquet_to_db():
    print("🚀 Starting Database Load...")
    conn = get_db()
    if not conn:
        print("❌ DB Connection Failed")
        return
        
    # params
    dsn = conn.get_dsn_parameters()
    print(f"🔌 Connected to: {dsn.get('dbname')} @ {dsn.get('host')}:{dsn.get('port')} User: {dsn.get('user')}")

    cursor = conn.cursor()
    
    files = [f for f in os.listdir(DATA_DIR) if f.startswith("nhl_boxscores_") and f.endswith(".parquet")]
    print(f"📂 Found {len(files)} files: {files}")
    
    for f in files:
        path = os.path.join(DATA_DIR, f)
        print(f"📖 Reading {f}...")
        try:
            df = pd.read_parquet(path)
        except Exception as e:
            print(f"❌ Read Error {f}: {e}")
            continue
        
        db_rows = []
        for _, row in df.iterrows():
            is_home = True if row.get('homeRoad') == 'H' else False
            val_toi = row.get('timeOnIcePerGame', 0)
            
            db_rows.append((
                str(row['gameId']),
                int(row['playerId']),
                row['skaterFullName'],
                row['teamAbbrev'],
                row['opponentTeamAbbrev'],
                row['gameDate'],
                int(row['goals']),
                int(row['assists']),
                int(row['points']),
                int(row['shots']),
                int(val_toi) if pd.notnull(val_toi) else 0,
                int(row.get('ppPoints', 0)),
                int(row.get('plusMinus', 0)),
                is_home
            ))
            
        print(f"⚡ Inserting {len(db_rows)} rows...")
        
        query = """
            INSERT INTO public.nhl_player_game_logs 
            (game_id, player_id, player_name, team, opponent, game_date, goals, assists, points, shots, toi_seconds, pp_points, plus_minus, is_home)
            VALUES %s
            ON CONFLICT (game_id, player_id) DO UPDATE SET
            goals=EXCLUDED.goals, assists=EXCLUDED.assists, points=EXCLUDED.points, shots=EXCLUDED.shots, toi_seconds=EXCLUDED.toi_seconds
        """
        
        try:
            execute_values(cursor, query, db_rows, page_size=1000)
            conn.commit()
            print("✅ Commit Successful.")
        except Exception as e:
            print(f"❌ Error inserting {f}: {e}")
            conn.rollback()

    conn.close()
    print("🎉 All files loaded.")

if __name__ == "__main__":
    load_parquet_to_db()
