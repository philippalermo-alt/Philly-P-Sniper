import requests
from bs4 import BeautifulSoup
from utils.logging import log

def get_nba_refs():
    """
    Scrape official NBA referee assignments from official.nba.com.
    """
    url = "https://official.nba.com/referee-assignments/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.google.com/'
    }
    
    log("REFS", f"Fetching NBA Referee Data from {url}...")
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200:
            log("WARN", f"Failed to fetch refs: {res.status_code}")
            return []
            
        soup = BeautifulSoup(res.text, 'html.parser')
        table = soup.find('table', class_='table')
        
        if not table:
            log("WARN", "No table found with class='table' on ref page.")
            return []
            
        assignments = []
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if not cols:
                continue
                
            game_str = cols[0].get_text(strip=True)
            
            def clean_ref(cell):
                text = cell.get_text(strip=True)
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
                
        log("REFS", f"Found {len(assignments)} referee assignments.")
        return assignments

    except Exception as e:
        log("ERROR", f"Error scraping refs: {e}")
        return []
