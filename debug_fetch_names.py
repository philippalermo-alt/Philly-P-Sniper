from data.clients.espn import fetch_espn_scores
from datetime import datetime, timedelta
import pytz

def debug_names():
    tz = pytz.timezone('US/Eastern')
    yesterday = (datetime.now(tz) - timedelta(days=1)).strftime('%Y%m%d')
    print(f"Fetching for {yesterday}...")
    
    games = fetch_espn_scores(['NCAAB', 'NHL'], specific_date=yesterday)
    print(f"Fetched {len(games)} games.")
    
    for g in games:
        print(f"[{g['status']}] {g['away']} @ {g['home']}")

if __name__ == "__main__":
    debug_names()
