import psycopg2
from config import Config

def fix_props():
    print("Connecting to DB...")
    conn = psycopg2.connect(Config.DATABASE_URL, sslmode='prefer')
    cur = conn.cursor()
    
    # 1. Check current counts
    cur.execute("SELECT sport, count(*) FROM intelligence_log GROUP BY sport")
    before = cur.fetchall()
    print("--- Before ---")
    for row in before:
        print(row)
        
    # 2. Update NHL Props
    # Criteria: Sport='NHL' (or 'icehockey_nhl' if used) AND Selection contains 'SOG'
    query = """
        UPDATE intelligence_log
        SET sport = 'NHL_PROP'
        WHERE (sport = 'NHL' OR sport = 'icehockey_nhl')
        AND selection LIKE '%SOG'
    """
    
    cur.execute(query)
    updated = cur.rowcount
    
    print(f"\n✅ Updated {updated} rows to 'NHL_PROP'")
    
    conn.commit()
    
    # 3. Check new counts
    cur.execute("SELECT sport, count(*) FROM intelligence_log GROUP BY sport")
    after = cur.fetchall()
    print("\n--- After ---")
    for row in after:
        print(row)
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    fix_props()
