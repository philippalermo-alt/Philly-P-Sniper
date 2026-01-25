from database import get_db
import pandas as pd
import re

def parse_odds(selection_str):
    # Extract odds from string like "Team (-110)" or "Over 2.5 (-105)"
    # Returns decimal odds if possible, or None
    try:
        match = re.search(r'\(([-+]?\d+)\)$', selection_str.strip())
        if match:
            us_odds = int(match.group(1))
            if us_odds > 0:
                return 1 + (us_odds / 100)
            else:
                return 1 + (100 / abs(us_odds))
        return 2.0 # Default/Fallback
    except:
        return 2.0

def analyze_performance():
    conn = get_db()
    
    # query all finalized bets
    query = "SELECT * FROM intelligence_log WHERE outcome IN ('WON', 'LOST', 'PUSH') ORDER BY kickoff ASC"
    df = pd.read_sql(query, conn)
    
    if df.empty:
        print("No finalized bets to analyze.")
        return

    print(f"📊 Analyzing {len(df)} finalized bets...")
    
    results = []
    
    for i, row in df.iterrows():
        # Parse Odds
        # DB 'odds' column is decimal, use that if available, else parse selection
        decimal_odds = row.get('odds')
        if not decimal_odds or pd.isna(decimal_odds):
            decimal_odds = parse_odds(row['selection'])
        else:
            decimal_odds = float(decimal_odds)
            
        stake = float(row.get('stake', 1.0) or 1.0) # Default 1 unit
        
        profit = 0
        if row['outcome'] == 'WON':
            profit = stake * (decimal_odds - 1)
        elif row['outcome'] == 'LOST':
            profit = -stake
        elif row['outcome'] == 'PUSH':
            profit = 0
            
        # Flag suspicious Draw ML => PUSH
        suspicious = False
        if "Draw ML" in row['selection'] and row['outcome'] == 'PUSH':
            suspicious = True
            
        results.append({
            'date': pd.to_datetime(row['kickoff']).date(),
            'sport': row['sport'],
            'outcome': row['outcome'],
            'profit': profit,
            'stake': stake,
            'suspicious': suspicious,
            'selection': row['selection']
        })
        
    res_df = pd.DataFrame(results)
    
    # 1. Global Stats
    total_bets = len(res_df)
    total_won = len(res_df[res_df['outcome'] == 'WON'])
    win_rate = (total_won / total_bets) * 100 if total_bets else 0
    total_profit = res_df['profit'].sum()
    roi = (total_profit / res_df['stake'].sum()) * 100 if res_df['stake'].sum() else 0
    
    print("\n🌍 GLOBAL PERFORMANCE")
    print("-" * 40)
    print(f"Bets: {total_bets}")
    print(f"Wins: {total_won}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Total Profit (Units): {total_profit:.2f}")
    print(f"ROI: {roi:.2f}%")
    
    # 2. By Sport
    print("\n🏆 PERFORMANCE BY SPORT")
    print("-" * 60)
    sport_grp = res_df.groupby('sport').agg({
        'outcome': 'count',
        'profit': 'sum',
        'stake': 'sum'
    }).rename(columns={'outcome': 'bets'})
    
    # Calculate wins per sport manually
    wins_per_sport = res_df[res_df['outcome'] == 'WON'].groupby('sport').size()
    sport_grp['wins'] = wins_per_sport
    sport_grp['wins'] = sport_grp['wins'].fillna(0)
    sport_grp['win_rate'] = (sport_grp['wins'] / sport_grp['bets']) * 100
    sport_grp['roi'] = (sport_grp['profit'] / sport_grp['stake']) * 100
    
    print(sport_grp[['bets', 'wins', 'win_rate', 'profit', 'roi']].round(2))
    
    # 3. By Date (Trend)
    print("\n📈 PERFORMANCE BY DATE (Last 7 Days)")
    print("-" * 60)
    date_grp = res_df.groupby('date').agg({
        'outcome': 'count',
        'profit': 'sum'
    }).tail(7)
    print(date_grp)

    # 4. Suspicious Draws
    suspicious_df = res_df[res_df['suspicious']]
    if not suspicious_df.empty:
        print(f"\n⚠️ FOUND {len(suspicious_df)} SUSPICIOUS 'Draw ML' => 'PUSH' BETS:")
        for i, row in suspicious_df.iterrows():
            print(f" - {row['date']} | {row['sport']} | {row['selection']} | PUSH (Should be WIN/LOST?)")
        
        # Determine fix
        print("\n💡 Recommendation: Verify these games. If Draws, update to WON.")

if __name__ == "__main__":
    analyze_performance()
