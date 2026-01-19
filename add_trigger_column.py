import os
import psycopg2

DATABASE_URL = os.getenv('DATABASE_URL')

try:
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()
    
    print("🔧 Adding trigger_type column to intelligence_log table...")
    
    try:
        cur.execute("ALTER TABLE intelligence_log ADD COLUMN trigger_type TEXT")
        conn.commit()
        print("✅ Column added successfully!")
    except Exception as e:
        if "already exists" in str(e):
            print("✅ Column already exists!")
        else:
            print(f"❌ Error: {e}")
        conn.rollback()
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"❌ Database connection error: {e}")
