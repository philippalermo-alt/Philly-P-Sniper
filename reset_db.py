import os
import psycopg2

DATABASE_URL = os.getenv('DATABASE_URL')

try:
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()
    
    print("🔥 [RESET] Dropping corrupted 'intelligence_log' table...")
    cur.execute("DROP TABLE IF EXISTS intelligence_log;")
    conn.commit()
    
    print("✨ [RESET] Database is clean. The next scan will rebuild the schema correctly.")
    cur.close()
    conn.close()
except Exception as e:
    print(f"❌ Error: {e}")
