from database import get_db
import pandas as pd

def inspect_wrexham():
    conn = get_db()
    # Use generic SQL LIKE
    query = "SELECT * FROM intelligence_log WHERE teams ILIKE '%%Wrexham%%'"
    try:
        df = pd.read_sql(query, conn)
        if df.empty:
            print("No Wrexham bets found.")
        else:
            print(df.to_string())
    except Exception as e:
        print(e)
        
if __name__ == "__main__":
    inspect_wrexham()
