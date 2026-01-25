from ratings import get_team_ratings
import os
from config import Config

def check_ratings():
    if not Config.KENPOM_API_KEY:
        print("❌ No API Key found.")
        return

    print(f"Checking Ratings (Key: {Config.KENPOM_API_KEY[:4]}...)...")
    ratings = get_team_ratings()
    
    ncaab = {k:v for k,v in ratings.items() if v.get('sport') == 'NCAAB'}
    print(f"Found {len(ncaab)} NCAAB teams.")
    
    if ncaab:
        sample = list(ncaab.keys())[0]
        print(f"Sample ({sample}): {ncaab[sample]}")
    else:
        print("❌ No NCAAB ratings returned.")

if __name__ == "__main__":
    check_ratings()
