
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import time
import datetime
import random

def fetch_nhl_scores():
    # Fetch scores for recent season
    # Using Hockey-Reference Schedule
    url = "https://www.hockey-reference.com/leagues/NHL_2026_games.html"
    print(f"🏒 Fetching NHL Scores from {url}...")
    
    scraper = cloudscraper.create_scraper()
    
    try:
        res = scraper.get(url)
        if res.status_code != 200:
            print(f"❌ Failed to fetch: {res.status_code}")
            return
            
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Table id="games"
        table = soup.find('table', id='games')
        if not table:
             print("❌ No games table found.")
             # Dump debug
             with open("debug_nhl_scores.html", "w") as f:
                 f.write(soup.prettify())
             return
             
        # Parse table
        games = []
        rows = table.find_all('tr')
        for row in rows:
            cls = row.get('class', [])
            if 'thead' in cls: continue # Header
            
            # Columns: Date, Visitor, VisitorGoals, Home, HomeGoals, ...
            # Need to map specific columns
            
            date_th = row.find('th', {'data-stat': 'date_game'})
            if not date_th: continue
            date_str = date_th.get_text(strip=True) # "2025-10-04"
            
            visitor_td = row.find('td', {'data-stat': 'visitor_team_name'})
            visitor = visitor_td.get_text(strip=True) if visitor_td else ""
            
            home_td = row.find('td', {'data-stat': 'home_team_name'})
            home = home_td.get_text(strip=True) if home_td else ""
            
            v_goals_td = row.find('td', {'data-stat': 'visitor_goals'})
            v_goals = v_goals_td.get_text(strip=True) if v_goals_td else ""
            
            h_goals_td = row.find('td', {'data-stat': 'home_goals'})
            h_goals = h_goals_td.get_text(strip=True) if h_goals_td else ""
            
            if visitor and home:
                games.append({
                    'Date': date_str,
                    'Visitor': visitor,
                    'Home': home,
                    'VisitorScore': v_goals,
                    'HomeScore': h_goals
                })
                
        df = pd.DataFrame(games)
        print(f"✅ Extracted {len(df)} games.")
        
        # Enrich with "Ref_HomeWin" label later
        # For now just save raw scores
        df.to_csv("nhl_scores_2025_26.csv", index=False)
        print("💾 Saved to nhl_scores_2025_26.csv")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fetch_nhl_scores()
