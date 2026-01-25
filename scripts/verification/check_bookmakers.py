
import requests
import json
from config import Config

def check_bookmakers():
    print("📚 Fetching API-Football Bookmakers List...")
    
    url = "https://v3.football.api-sports.io/odds/bookmakers"
    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-rapidapi-key': Config.FOOTBALL_API_KEY
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        
        if not data.get('response'):
            print("❌ No response or empty list.")
            return
            
        bookmakers = data['response']
        print(f"✅ Found {len(bookmakers)} Bookmakers.\n")
        
        # Look for key US books
        us_books = ['DraftKings', 'FanDuel', 'BetMGM', 'Caesars', 'Bovada', 'Hard Rock']
        found_us = []
        
        print("--- All Bookmakers ---")
        for bk in bookmakers:
            name = bk['name']
            bid = bk['id']
            print(f"ID: {bid:<4} | {name}")
            
            # Check simplified matching
            for target in us_books:
                if target.lower() in name.lower():
                    found_us.append(f"{target} (ID: {bid} - {name})")
                    
        print("\n--- 🇺🇸 US Relevance Check ---")
        if found_us:
            for f in found_us:
                print(f"✅ Found: {f}")
        else:
            print("⚠️ No major US books found in simple search.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_bookmakers()
