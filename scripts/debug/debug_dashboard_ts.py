
import os
import psycopg2
from datetime import datetime
import pytz
from dotenv import load_dotenv

load_dotenv()

def debug_timestamp():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DB URL missing")
        return

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        print("🔄 Querying app_settings...")
        cur.execute("SELECT value FROM app_settings WHERE key='model_last_run'")
        row = cur.fetchone()
        
        if not row:
            print("❌ No row found for 'model_last_run'")
            return
            
        raw_val = row[0]
        print(f"📄 Raw Value from DB: '{raw_val}' (Type: {type(raw_val)})")
        
        try:
            ts = raw_val
            if isinstance(ts, str):
                print("   -> Is String, replacing space with T...")
                ts = datetime.fromisoformat(ts.replace(' ', 'T'))
                print(f"   -> Parsed Result: {ts}")
                
            if ts.tzinfo is None:
                print("   -> Naive, assuming UTC...")
                ts = ts.replace(tzinfo=pytz.utc)
            else:
                print(f"   -> Aware: {ts.tzinfo}")
                
            eastern = ts.astimezone(pytz.timezone('US/Eastern'))
            print(f"✅ Final Output: {eastern.strftime('%b %d, %I:%M %p EST')}")
            
        except Exception as e:
            print(f"❌ Parsing Error: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"❌ DB Error: {e}")

if __name__ == "__main__":
    debug_timestamp()
