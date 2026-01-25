from database import get_db
import pandas as pd

try:
    conn = get_db()
    # Use raw SQL to avoid any pandas/dependency issues, though pandas is cleaner for display
    query = "SELECT kickoff, sport, selection, teams FROM intelligence_log WHERE outcome = 'PENDING' AND kickoff < NOW() ORDER BY kickoff ASC"
    df = pd.read_sql(query, conn)
    
    if df.empty:
        print("No pending bets found.")
    else:
        print(f"\n📝 FOUND {len(df)} PENDING BETS:")
        print("-" * 120)
        print(f"{'KICKOFF':<20} | {'SPORT':<12} | {'SELECTION':<35} | {'TEAMS'}")
        print("-" * 120)
        for _, row in df.iterrows():
            # Truncate long strings for display
            sel = (row['selection'][:32] + '..') if len(row['selection']) > 32 else row['selection']
            print(f"{str(row['kickoff']):<20} | {row['sport']:<12} | {sel:<35} | {row['teams']}")
        print("-" * 120)

except Exception as e:
    print(f"Error: {e}")
