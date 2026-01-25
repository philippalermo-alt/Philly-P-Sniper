import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time

def get_nba_refs():
    url = "https://official.nba.com/referee-assignments/"
    
    # Robust headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.google.com/'
    }
    
    print(f"🕵️‍♂️ Fetching Referee Data from {url}...")
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200:
            print(f"❌ Failed to fetch: {res.status_code}")
            return []
            
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Finding the main table
        # Based on browser inspection: <table class="table">
        table = soup.find('table', class_='table')
        
        if not table:
            print("❌ No table found with class='table'. Page structure might have changed.")
            # Debug: Print first 500 chars of body
            print(soup.body.text[:500] if soup.body else "No body content")
            return []
            
        assignments = []
        
        # Iterate Rows (skip header)
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if not cols:
                continue # Header row or empty
                
            # Expected columns: Game, Crew Chief, Referee, Umpire, Alternate
            # Game is text "Team A @ Team B"
            game_str = cols[0].get_text(strip=True)
            
            # Refs are often in <a> tags if they have links, or just text
            # We want just the names, cleaning up " (#Number)"
            
            def clean_ref(cell):
                text = cell.get_text(strip=True)
                # Remove (Number) e.g. "Scott Foster (#48)" -> "Scott Foster"
                if "(" in text:
                    text = text.split("(")[0].strip()
                return text

            chief = clean_ref(cols[1])
            ref = clean_ref(cols[2])
            umpire = clean_ref(cols[3])
            
            if game_str and chief:
                assignments.append({
                    'Game': game_str,
                    'Crew Chief': chief,
                    'Referee': ref,
                    'Umpire': umpire
                })
                
        print(f"✅ Found {len(assignments)} assignments.")
        for a in assignments:
            print(f"  🏀 {a['Game']}: {a['Crew Chief']}, {a['Referee']}, {a['Umpire']}")
            
        return assignments

    except Exception as e:
        print(f"❌ Error scraping refs: {e}")
        return []

if __name__ == "__main__":
    get_nba_refs()
