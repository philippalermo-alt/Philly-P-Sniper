import pandas as pd
from database import get_db
import sys

def analyze_ncaab():
    conn = get_db()
    if not conn:
        print("❌ DB Connection Failed")
        return

    print("📊 NCAAB Performance and Data Analysis")
    print("="*40)

    try:
        # Load all NCAAB bets
        query = """
        SELECT outcome, edge, odds, stake, true_prob, selection, closing_odds
        FROM intelligence_log
        WHERE sport LIKE '%NCAAB%' OR sport LIKE '%ncaab%'
        """
        df = pd.read_sql(query, conn)
        
        if df.empty:
            print("⚠️ No NCAAB data found in intelligence_log.")
            return

        total_bets = len(df)
        print(f"Total NCAAB Rows Logged: {total_bets}")

        # 1. Performance W/L
        completed = df[df['outcome'].isin(['WON', 'LOST'])]
        if not completed.empty:
            wins = len(completed[completed['outcome'] == 'WON'])
            losses = len(completed[completed['outcome'] == 'LOST'])
            win_rate = (wins / len(completed)) * 100
            print(f"\n🏆 Record: {wins}W - {losses}L")
            print(f"   Win Rate: {win_rate:.1f}%")
            
            # Avg Edge on Winners vs Losers
            avg_edge_w = completed[completed['outcome'] == 'WON']['edge'].mean()
            avg_edge_l = completed[completed['outcome'] == 'LOST']['edge'].mean()
            print(f"   Avg Edge (Wins):   {avg_edge_w*100:.2f}%")
            print(f"   Avg Edge (Losses): {avg_edge_l*100:.2f}%")
        else:
            print("\n🏆 Record: 0W - 0L (No completed bets)")

        # 2. Edge Distribution
        print("\n📈 Edge Distribution (All Logged Opportunities):")
        # Buckets: <0%, 0-2%, 2-4%, 4-6%, 6-10%, >10%
        bins = [-1.0, 0.0, 0.02, 0.04, 0.06, 0.10, 1.0]
        labels = ['Negative', '0-2%', '2-4%', '4-6%', '6-10%', '10%+']
        try:
           df['bucket'] = pd.cut(df['edge'], bins=bins, labels=labels)
           print(df['bucket'].value_counts().sort_index().to_string())
        except Exception as e:
           print(f"Error binning: {e}")

        # 3. Pending Bets
        pending = df[df['outcome'] == 'PENDING']
        print(f"\n⏳ Pending Bets: {len(pending)}")
        if not pending.empty:
            print(f"   Avg Edge: {pending['edge'].mean()*100:.2f}%")

    except Exception as e:
        print(f"❌ Analysis Logic Failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    analyze_ncaab()
