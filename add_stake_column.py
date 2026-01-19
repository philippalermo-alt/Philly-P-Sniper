import os
import psycopg2

DATABASE_URL = os.getenv('DATABASE_URL')

try:
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()
    
    print("🔧 Adding 'stake' column to intelligence_log table...")
    
    try:
        # Add column as REAL (float) to store the dollar amount
        cur.execute("ALTER TABLE intelligence_log ADD COLUMN stake REAL")
        conn.commit()
        print("✅ Column 'stake' added successfully!")
    except Exception as e:
        if "already exists" in str(e):
            print("✅ Column 'stake' already exists!")
        else:
            print(f"❌ Error adding column: {e}")
        conn.rollback()
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"❌ Database connection error: {e}")