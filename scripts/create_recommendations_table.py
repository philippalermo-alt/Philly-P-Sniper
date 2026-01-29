from db.connection import get_db

def create_table():
    print("🛠️ Creating `recommendations` table...")
    conn = get_db()
    cur = conn.cursor()
    
    schema = """
    CREATE TABLE IF NOT EXISTS recommendations (
        id SERIAL PRIMARY KEY,
        run_id TEXT,
        sport TEXT,
        game_id TEXT,
        game_date TIMESTAMP,
        team TEXT,
        market TEXT,
        selection TEXT,
        book TEXT,
        odds DECIMAL,
        implied_prob DECIMAL,
        model_prob DECIMAL,
        edge DECIMAL,
        bucket TEXT,
        stake_units DECIMAL DEFAULT 1.0,
        status TEXT DEFAULT 'Pending' CHECK (status IN ('Pending', 'Won', 'Lost', 'Push', 'Void')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        metadata JSONB
    );
    
    CREATE INDEX IF NOT EXISTS idx_recs_run_id ON recommendations(run_id);
    CREATE INDEX IF NOT EXISTS idx_recs_created ON recommendations(created_at);
    CREATE INDEX IF NOT EXISTS idx_recs_status ON recommendations(status);
    """
    
    cur.execute(schema)
    conn.commit()
    conn.close()
    print("✅ Table `recommendations` ready.")

if __name__ == "__main__":
    create_table()
