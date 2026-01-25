from database import get_db
import pandas as pd

def audit_ncaab_data():
    conn = get_db()
    
    # Query recent NCAAB games
    query = """
    SELECT 
        event_id, teams, kickoff,
        home_adj_em, away_adj_em,
        home_adj_o, away_adj_o,
        home_tempo, away_tempo
    FROM intelligence_log
    WHERE sport = 'NCAAB'
    ORDER BY kickoff DESC
    LIMIT 20
    """
    try:
        df = pd.read_sql(query, conn)
        if df.empty:
            print("No NCAAB data found.")
        else:
            print(df.to_string())
            
            # Count nulls
            nulls = df['home_adj_em'].isnull().sum()
            print(f"\nNull KenPom stats in last 20 games: {nulls}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    audit_ncaab_data()
