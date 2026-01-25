
import os
import psycopg2
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def analyze_rlm():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL missing")
        return

    conn = psycopg2.connect(db_url)
    
    query = """
        SELECT 
            sport,
            selection,
            edge,
            sharp_score,
            outcome,
            odds
        FROM intelligence_log
        WHERE edge >= 0.10
          AND outcome IN ('WON', 'LOST')
          AND sharp_score IS NOT NULL
    """
    
    print("running query...")
    df = pd.read_sql(query, conn)
    conn.close()
    
    if df.empty:
        print("⚠️ No graded bets found with Edge >= 10% and Sharp Score.")
        return

    print(f"📊 Total High Edge Bets (10%+): {len(df)}")
    
    # Define Groups
    # Group A: The "Trap" (Low Sharp Score)
    trap_df = df[df['sharp_score'] < 30].copy()
    
    # Group B: The "Valid" (High Sharp Score)
    valid_df = df[df['sharp_score'] >= 30].copy()
    
    def calc_roi(dbox):
        if dbox.empty: return 0.0, 0, 0
        
        # Assume 1 unit flat stake for comparison
        dbox['units_won'] = dbox.apply(lambda x: (x['odds'] - 1) if x['outcome'] == 'WON' else -1, axis=1)
        
        total_bets = len(dbox)
        total_profit = dbox['units_won'].sum()
        roi = (total_profit / total_bets) * 100
        return roi, total_profit, total_bets

    # Calculate Stats
    roi_trap, prof_trap, n_trap = calc_roi(trap_df)
    roi_valid, prof_valid, n_valid = calc_roi(valid_df)
    
    print("\n🧐 **Hypothesis Check: 'Trap' vs 'Valid'**")
    print("-" * 40)
    print(f"📉 **The Proposed Filter (Sharp < 30)**:")
    print(f"   Bets: {n_trap}")
    print(f"   Profit: {prof_trap:.2f}u")
    print(f"   ROI: {roi_trap:.1f}%")
    print("-" * 40)
    print(f"📈 **The Keepers (Sharp >= 30)**:")
    print(f"   Bets: {n_valid}")
    print(f"   Profit: {prof_valid:.2f}u")
    print(f"   ROI: {roi_valid:.1f}%")
    print("-" * 40)
    
    if roi_trap < 0 and roi_valid > roi_trap:
        print("✅ VERDICT: The filter WOOKS. Blocking low sharp score improves results.")
    elif roi_trap > 0:
        print("❌ VERDICT: The filter FAILS. Low sharp score bets are profitable!")
    else:
        print("❓ VERDICT: Inconclusive difference.")

if __name__ == "__main__":
    analyze_rlm()
