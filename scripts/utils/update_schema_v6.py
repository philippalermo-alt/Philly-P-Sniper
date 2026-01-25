from database import get_db

def run_migration():
    conn = get_db()
    if not conn:
        print("❌ Could not connect to DB via get_db()")
        return
        
    # Postgres needs autocommit for some ops, or explicit commit
    # PooledConnection proxies most things
    cur = conn.cursor()
    
    cols = [
        ("market_avg_over", "REAL"),
        ("market_avg_under", "REAL"),
        ("closing_total", "REAL"),
        ("market_implied_prob", "REAL"),
        ("odds_over_2_5", "REAL"), # Explicitly what user asked for
        ("odds_under_2_5", "REAL")
    ]
    
    print("🛠 Migrating 'matches' table (Postgres) for V6 Market Data...")
    
    # Check existing columns
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='matches'")
    existing_cols = [row[0] for row in cur.fetchall()]
    
    for col_name, col_type in cols:
        if col_name not in existing_cols:
            print(f"  + Adding column: {col_name} ({col_type})")
            cur.execute(f"ALTER TABLE matches ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
        else:
            print(f"  = Column {col_name} already exists.")
            
    conn.commit()
    conn.close()
    print("✅ Migration Complete.")

if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"❌ Error: {e}")
