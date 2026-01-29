
import psycopg2
from db.connection import get_db

def fix_schema():
    print("🛠 Fixing Schema via Python...")
    conn = get_db()
    cur = conn.cursor()
    
    # 1. Add Columns to Player Log
    print("Adding columns to nhl_player_game_logs...")
    try:
        cur.execute("ALTER TABLE public.nhl_player_game_logs ADD COLUMN IF NOT EXISTS ixg FLOAT DEFAULT 0.0")
        cur.execute("ALTER TABLE public.nhl_player_game_logs ADD COLUMN IF NOT EXISTS pp_toi INT DEFAULT 0")
        cur.execute("ALTER TABLE public.nhl_player_game_logs ADD COLUMN IF NOT EXISTS pp_goals INT DEFAULT 0")
        conn.commit()
        print("✅ Columns Added.")
    except Exception as e:
        print(f"⚠️ Error altering table: {e}")
        conn.rollback()

    # 2. Create Goalie Table
    print("Creating nhl_goalie_game_logs...")
    ddl = """
    CREATE TABLE IF NOT EXISTS public.nhl_goalie_game_logs (
        game_id VARCHAR(20) NOT NULL,
        team VARCHAR(10),
        opponent VARCHAR(10),
        goalie_id INT NOT NULL,
        goalie_name VARCHAR(100),
        game_date DATE,
        
        is_starter BOOLEAN DEFAULT FALSE,
        toi_seconds INT DEFAULT 0,
        shots_against INT DEFAULT 0,
        goals_against INT DEFAULT 0,
        saves INT DEFAULT 0,
        save_pct FLOAT,
        
        created_at TIMESTAMP DEFAULT NOW(),
        
        PRIMARY KEY (game_id, goalie_id)
    );
    """
    try:
        cur.execute(ddl)
        conn.commit()
        print("✅ Goalie Table Created.")
    except Exception as e:
        print(f"⚠️ Error creating table: {e}")
        conn.rollback()
        
    conn.close()

if __name__ == "__main__":
    fix_schema()
