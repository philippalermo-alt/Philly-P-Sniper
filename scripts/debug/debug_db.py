
import os
import psycopg2
from database import get_db

conn = get_db()
cur = conn.cursor()
cur.execute("SELECT teams, kickoff, event_id FROM intelligence_log WHERE sport='NBA' LIMIT 5;")
rows = cur.fetchall()
for r in rows:
    print(r)
conn.close()
