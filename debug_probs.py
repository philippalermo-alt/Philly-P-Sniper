from database import get_db
import pandas as pd

conn = get_db()
if conn:
    df = pd.read_sql("SELECT sport, selection, odds, edge, true_prob FROM intelligence_log WHERE outcome='PENDING' ORDER BY timestamp DESC LIMIT 10", conn)
    print(df)
    conn.close()
