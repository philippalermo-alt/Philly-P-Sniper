
import cloudscraper
from bs4 import BeautifulSoup
import time

def debug_pagination():
    scraper = cloudscraper.create_scraper()
    
    
    # Try Search URL (Pagination usually reliable)
    base_search_url = "https://scoutingtherefs.com/page/{}/?s=todays+nhl+referees"
    
    pages = [1, 2, 3]
    
    for p in pages:
        url = base_search_url.format(p)
        print(f"Fetching {url}...")
        
        try:
            res = scraper.get(url)
            print(f"   Final URL: {res.url}")
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Print first 3 article titles
            articles = soup.find_all('article')
            print(f"   Found {len(articles)} articles.")
            for i, art in enumerate(articles[:3]):
                 link = art.find('a')
                 if link:
                     href = link.get('href', 'No Href')
                     print(f"   [{i}] {href}")
                 
        except Exception as e:
            print(f"   Error: {e}")
            
        time.sleep(2)

if __name__ == "__main__":
    debug_pagination()
