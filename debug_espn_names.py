from data.clients.espn import fetch_espn_scores
from datetime import datetime, timedelta
import pytz

def main():
    tz = pytz.timezone('US/Eastern')
    now_et = datetime.now(tz)
    
    # Check last 3 days
    dates = [
        now_et.strftime('%Y%m%d'),
        (now_et - timedelta(days=1)).strftime('%Y%m%d'),
        (now_et - timedelta(days=2)).strftime('%Y%m%d')
    ]
    
    print("--- FETCHING ESPN GAMES (NCAAB, NBA, NHL) ---")
    games = fetch_espn_scores(['NCAAB', 'NBA', 'NHL'], specific_date=dates[1]) # Check yesterday mainly
    
    print(f"\nFetched {len(games)} games for {dates[1]}.")
    
    print("\n--- NCAAB GAMES ---")
    for g in games:
        if 'college-basketball' in g.get('sport_key', ''):
            print(f"{g['away']} @ {g['home']}")
            
    print("\n--- NBA GAMES ---")
    for g in games:
        if 'nba' in g.get('sport_key', ''):
            print(f"{g['away']} @ {g['home']}")

if __name__ == "__main__":
    main()
