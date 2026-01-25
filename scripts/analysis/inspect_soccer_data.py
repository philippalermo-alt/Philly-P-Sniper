from database import get_db
import pandas as pd

conn = get_db()
df = pd.read_sql("SELECT * FROM matches LIMIT 5", conn)
print(df[['home_team', 'away_team', 'home_goals', 'away_goals']])
print("\nStats:")
df_stats = pd.read_sql("SELECT count(*) as total, count(home_goals) as with_goals FROM matches", conn)
print(df_stats)
conn.close()
