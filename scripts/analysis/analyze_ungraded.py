from database import get_db
import pandas as pd
from datetime import datetime, timedelta
import pytz

def analyze():
    conn = get_db()
    cur = conn.cursor()
    
    print("📊 Analyzing PENDING bets...")
    
    # Get all pending past-due
    query = "SELECT event_id, sport, teams, kickoff, selection FROM intelligence_log WHERE outcome = 'PENDING' AND kickoff < NOW() ORDER BY kickoff ASC"
    df = pd.read_sql(query, conn)
    
    if df.empty:
        print("✅ No pending bets found?!")
        return

    print(f"found {len(df)} pending bets.")
    print(f"📅 Date Range: {df['kickoff'].min()} to {df['kickoff'].max()}")
    
    # Group by Sport
    print("\n🏆 Valid Pending by Sport:")
    print(df['sport'].value_counts())
    
    print(f"\n📝 Full List of {len(df)} Pending Bets:")
    print("-" * 80)
    for i, row in df.iterrows():
        print(f"[{row['kickoff']}] {row['sport']:<12} | {row['selection']:<30} | {row['teams']}")
    print("-" * 80)

    print("\n🏀 ANALYZING NCAAB MISMATCHES SPECIFICALLY:")
    ncaab_df = df[df['sport'] == 'NCAAB']
    if not ncaab_df.empty:
        print(f"Found {len(ncaab_df)} NCAAB bets.")
        # Print top 5 to see names
        for i, row in ncaab_df.head(10).iterrows():
             print(f"   DB: '{row['teams']}'")
    else:
        print("No NCAAB bets pending.")

    # Check against ESPN for today/yesterday (simulation)
    print("\n🔎 Checking mismatch Potential...")
    from api_clients import fetch_espn_scores
    
    # Get unique sports
    sports = df['sport'].unique().tolist()
    # Map them if necessary (simple pass for now)
    
    # We'll just fetch whatever the grading script would fetch
    # Note: Using the mapping logic from bet_grading.py would be ideal but let's just use the raw column first
    # bet_grading maps 'EPL' -> 'SOCCER', so let's do a quick manual map for the fetch
    fetch_list = []
    sport_map = {
        'EPL': 'SOCCER', 'LALIGA': 'LALIGA', 'BUNDESLIGA': 'BUNDESLIGA',
        'SERIEA': 'SERIEA', 'LIGUE1': 'LIGUE1', 'CHAMPIONS': 'CHAMPIONS',
        'NBA': 'NBA', 'NCAAB': 'NCAAB', 'NHL': 'NHL', 'NFL': 'NFL', 'MLB': 'MLB'
    }
    for s in sports:
        fetch_list.append(sport_map.get(s, 'SOCCER')) # default soccer
    
    fetch_list = list(set(fetch_list))
    print(f"Fetching scores for: {fetch_list}")
    
    # DEBUG: explicit date check
    tz = pytz.timezone('US/Eastern')
    now_et = datetime.now(tz)
    dates = [now_et.strftime('%Y%m%d'), (now_et - timedelta(days=1)).strftime('%Y%m%d'), (now_et - timedelta(days=2)).strftime('%Y%m%d')]
    print(f"📅 Debug: Checking dates {dates}")
    
    # Force fetch for these 3 days
    games = []
    for d in dates:
        print(f"   > Fetching {d}...")
        g_day = fetch_espn_scores(fetch_list, specific_date=d)
        print(f"     - Got {len(g_day)} games.")
        games.extend(g_day)
        
    print(f"Fetched {len(games)} TOTAL games from ESPN ({dates}).")
    
    # DEBUG: Print sample fetched games for NCAAB/NHL to compare
    print("\n🕵️ DEBUG: Sample Fetched Games from ESPN:")
    ncaab_games = [g for g in games if 'basketball' in g['sport_key'] or 'NCAAB' in g['sport_key']]
    nhl_games = [g for g in games if 'hockey' in g['sport_key'] or 'NHL' in g['sport_key']]
    
    print(f"   > Found {len(ncaab_games)} NCAAB outcomes.")
    if ncaab_games:
        for g in ncaab_games[:5]:
            print(f"     - {g['away']} vs {g['home']} ({g['status']})")

    print(f"   > Found {len(nhl_games)} NHL outcomes.")
    if nhl_games:
         for g in nhl_games[:5]:
            print(f"     - {g['away']} vs {g['home']} ({g['status']})")
            
    # DEBUG: Print ALL Jan 20 games to debug name matching
    print("\n🕵️ DEBUG: FULL GAME LIST FOR Jan 20/21 (20260120, 20260121):")
    for g in games:
         # Print EVERYTHING to be safe
         print(f"   [{g['commence']}] {g.get('sport_key', '???'):<15} | {g['away']} @ {g['home']} ({g['status']})")

    print("\n   Checking specific failures against fetched list:")
    failed_teams = ['Wrexham', 'Leicester']
    for g in games:
        h = g['home']
        a = g['away']
        # Check if any part of our failed teams is in the game names
        if any(t in h for t in failed_teams) or any(t in a for t in failed_teams):
             print(f"   > MATCH CANDIDATE: {a} vs {h} (Date: {g['commence']}, Status: {g['status']}, ID: {g['id']})")
    matches = 0
    for _, row in df.iterrows():
        teams = row['teams']
        found = False
        for g in games:
            h = g['home']
            a = g['away']
            if h in teams and a in teams:
                found = True
                break
            elif a in teams and h in teams:
                found = True
                break
        if found:
            matches += 1
            
    print(f"\n📉 Matches found in CURRENT 2-day window: {matches}/{len(df)}")
    print(f"❌ Unmatched: {len(df) - matches}")

    if matches < len(df):
        print("\n💡 Recommendation: Implement fuzzy matching or name normalization.")

if __name__ == "__main__":
    analyze()
