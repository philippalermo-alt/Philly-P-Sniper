
import os
import psycopg2
from db.connection import get_db

def fix_table():
    print("🛠 Fix Table via Python...")
    conn = get_db()
    cur = conn.cursor()
    
    # DDL
    ddl = """
    CREATE TABLE IF NOT EXISTS public.nhl_player_game_logs (
        game_id VARCHAR(20) NOT NULL,
        player_id INT NOT NULL,
        player_name VARCHAR(100),
        team VARCHAR(10),
        opponent VARCHAR(10),
        game_date DATE,
        goals INT DEFAULT 0,
        assists INT DEFAULT 0,
        points INT DEFAULT 0,
        shots INT DEFAULT 0,
        toi_seconds INT DEFAULT 0,
        pp_points INT DEFAULT 0,
        plus_minus INT DEFAULT 0,
        is_home BOOLEAN,
        created_at TIMESTAMP DEFAULT NOW(),
        
        PRIMARY KEY (game_id, player_id)
    );
    """
    try:
        cur.execute(ddl)
        conn.commit()
        print("✅ Table Created (or Existed).")
        
        # Verify Visibility
        cur.execute("SELECT count(*) FROM public.nhl_player_game_logs")
        cnt = cur.fetchone()[0]
        print(f"✅ Count visible to Python: {cnt}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    
    conn.close()

if __name__ == "__main__":
    fix_table()
