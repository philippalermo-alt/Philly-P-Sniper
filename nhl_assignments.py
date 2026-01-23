
import cloudscraper
from bs4 import BeautifulSoup
import datetime
import re
import time

def get_nhl_assignments():
    """
    Scrape 'Today's NHL Referees' from ScoutingTheRefs.com
    Optimized for daily production use.
    """
    url = "https://scoutingtherefs.com/"
    print(f"🕵️‍♂️ Checking ScoutingTheRefs Homepage for assignments...")
    
    scraper = cloudscraper.create_scraper()
    
    try:
        # 1. Get List of Posts
        res = scraper.get(url)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        latest_link = None
        articles = soup.find_all('article')
        
        # Find the "Today's Referees" post
        for art in articles:
            link = art.find('a')
            if link:
                title = link.get_text(strip=True)
                href = link.get('href', '')
                
                if "nhl-referees" in href.lower() or "nhl referees" in title.lower():
                    # Optional: Check if date matches today? 
                    # Usually the latest one is today's.
                    # We can print standard debug.
                    print(f"   ✅ Found Target Post: '{title}'")
                    latest_link = href
                    break
                
        if not latest_link:
            print("❌ No 'NHL Referees' post found on first page.")
            return []
            
        # 2. Get the Daily Post
        print(f"   Fetching details from {latest_link}...")
        res_post = scraper.get(latest_link)
        soup_post = BeautifulSoup(res_post.text, 'html.parser')
        
        
        # 3. Parse Tables with Back-Search for Game Title
        tables = soup_post.find_all('table')
        assignments = []
        
        for table in tables:
            # Check if this is a Ref table (has "REFEREES" header row)
            text_content = table.get_text()
            if "REFEREES" not in text_content and "Linesmen" not in text_content:
                 continue
                 
            # Search backwards for Game Title
            game_title = "Unknown Game"
            prev = table.previous_element
            steps = 0
            while prev and steps < 50:
                name = getattr(prev, 'name', None)
                if name in ['h1','h2','h3','h4','p', 'div', 'span', 'strong']:
                    txt = prev.get_text(strip=True)
                    # "Team A at Team B" or "Team A vs Team B"
                    if (" at " in txt or " vs " in txt) and len(txt) < 100:
                        game_title = txt
                        break
                prev = getattr(prev, 'previous_element', None)
                steps += 1
                
            # Extract Refs
            refs = []
            rows = table.find_all('tr')
            for row in rows:
                txts = [c.get_text(separator=' ', strip=True) for c in row.find_all('td')]
                full_row_text = " ".join(txts)
                # Regex for "Name #Num"
                matches = re.findall(r"([A-Za-z\.\-\' ]+)\s+#\d+", full_row_text)
                for m in matches:
                    name = m.strip()
                    if name and name not in refs:
                        if "Referees" not in name and "Linesmen" not in name:
                            refs.append(name)
                            
            # Deduplicate
            refs = list(set(refs))
            
            if len(refs) >= 2:
                # Strip time from title if present "7:00 PM ET"
                # "Boston Bruins at Dallas Stars7:30 PM ET"
                # Simple logic: split by number?
                clean_title = game_title
                time_match = re.search(r'\d{1,2}:\d{2}', game_title)
                if time_match:
                    clean_title = game_title[:time_match.start()].strip()
                    
                assignments.append({
                    'Game': clean_title,
                    'Officials': refs
                })
                print(f"   ✅ Match: {clean_title} -> {refs}")
                
        return assignments

    except Exception as e:
        print(f"❌ Error: {e}")
        return []

if __name__ == "__main__":
    get_nhl_assignments()
