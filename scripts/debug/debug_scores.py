import logging
from api_clients import fetch_espn_scores

# Setup basic logging
logging.basicConfig(level=logging.INFO)

sports = ['NBA', 'NCAAB', 'NHL', 'SOCCER']
print(f"Fetching scores for: {sports}")

try:
    games = fetch_espn_scores(sports)
    print(f"\nFound {len(games)} games.")
    
    for g in games[:10]: # Print first 10
        print(f" - {g.get('sport')} | {g.get('home')} vs {g.get('away')} | Status: {g.get('status')} | Completed: {g.get('is_complete')}")
        
except Exception as e:
    print(f"Error: {e}")
