
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime, timedelta
import random
import os

def get_scores(start_date="2025-10-22"):
    base_url = "https://www.basketball-reference.com"
    output_file = "nba_scores_2025_26.csv"
    
    scraper = cloudscraper.create_scraper()
    
    # Check resume
    if os.path.exists(output_file):
        existing_df = pd.read_csv(output_file)
        processed_dates = set(existing_df['Date'].unique())
    else:
        processed_dates = set()
        df = pd.DataFrame(columns=['Date', 'Home', 'Away', 'HomeScore', 'AwayScore'])
        df.to_csv(output_file, index=False)
        
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.now() - timedelta(days=1)
    
    current_dt = start_dt
    while current_dt <= end_dt:
        date_str = current_dt.strftime("%Y-%m-%d")
        
        if date_str in processed_dates:
            print(f"⏩ {date_str} done.")
            current_dt += timedelta(days=1)
            continue
            
        print(f"📅 Fetching scores for {date_str}...")
        url = f"{base_url}/boxscores/?month={current_dt.month}&day={current_dt.day}&year={current_dt.year}"
        
        try:
            r = scraper.get(url)
            if r.status_code == 429:
                time.sleep(60)
                continue
                
            soup = BeautifulSoup(r.content, 'html.parser')
            summaries = soup.find_all('div', class_='game_summary')
            
            day_games = []
            for s in summaries:
                try:
                    # Teams and Scores
                    # structure: table -> tr (winner), tr (loser)
                    # or tr (visitor), tr (home)
                    
                    # We need to distinguish Home vs Away.
                    # B-Ref summary usually lists Visitor first, Home second?
                    # Let's verify standard B-Ref behavior: Top is Visitor, Bottom is Home.
                    # class="winner" might be present.
                    
                    rows = s.find_all('tr')
                    if len(rows) < 2: continue
                    
                    team1_row = rows[0]
                    team2_row = rows[1]
                    
                    # Name is in <a>
                    t1_name = team1_row.find('a').text
                    t2_name = team2_row.find('a').text
                    
                    # Score is in <td class="right">
                    t1_score = team1_row.find('td', class_='right').text
                    t2_score = team2_row.find('td', class_='right').text
                    
                    # If empty score, game hasn't happened or error
                    if not t1_score or not t2_score: continue
                    
                    # Who is home? B-Ref daily summary typically puts Visitor on Top.
                    # But verifying is safer. 
                    # Actually B-Ref standard IS Visitor @ Home.
                    
                    visit_name = t1_name
                    visit_score = int(t1_score)
                    home_name = t2_name
                    home_score = int(t2_score)
                    
                    day_games.append({
                        'Date': date_str,
                        'Home': home_name,
                        'Away': visit_name,
                        'HomeScore': home_score,
                        'AwayScore': visit_score
                    })
                except Exception as e:
                    # e.g. game preview only
                    continue
            
            if day_games:
                pd.DataFrame(day_games).to_csv(output_file, mode='a', header=False, index=False)
                print(f"   ✅ Saved {len(day_games)} scores.")
            else:
                print("   ⚠️ No games found.")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            
        current_dt += timedelta(days=1)
        time.sleep(2) # moderate delay

if __name__ == "__main__":
    get_scores()
