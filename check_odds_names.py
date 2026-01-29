import requests
from config.settings import Config
import json

def check_odds_names():
    print("🌍 Fetching UCL Odds from API...")
    url = f"https://api.the-odds-api.com/v4/sports/soccer_uefa_champs_league/odds/?apiKey={Config.ODDS_API_KEY}&regions=us&markets=h2h"
    res = requests.get(url)
    
    if res.status_code == 200:
        data = res.json()
        print(f"✅ Found {len(data)} games.")
        print("\n📋 Team Names from API:")
        for game in data:
            h = game['home_team']
            a = game['away_team']
            print(f"   Home: '{h}'  |  Away: '{a}'")
    else:
        print(f"❌ API Error: {res.status_code}")

if __name__ == "__main__":
    check_odds_names()
