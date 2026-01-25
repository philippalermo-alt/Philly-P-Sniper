
import pandas as pd
from database import get_db

def inspect_player(player_name):
    conn = get_db()
    if not conn:
        print("No DB Connection")
        return

    query = """
        SELECT match_id, player_name, team_name, minutes, shots, goals, league 
        FROM player_stats 
        WHERE player_name ILIKE %s
        ORDER BY scraped_at DESC
    """
    df = pd.read_sql(query, conn, params=(f"%{player_name}%",))
    print(df.to_string())
    conn.close()

if __name__ == "__main__":
    inspect_player("Nicolas Jackson")
