import cloudscraper
from bs4 import BeautifulSoup
import re

def test_hockey_ref_scraper():
    # Target: 2025-10-07 Panthers vs Blackhawks (Home: FLA)
    # URL Pattern: https://www.hockey-reference.com/boxscores/202510070FLA.html
    url = "https://www.hockey-reference.com/boxscores/202510070FLA.html"
    print(f"🏒 Fetching {url}...")
    
    scraper = cloudscraper.create_scraper()
    
    try:
        res = scraper.get(url)
        if res.status_code == 404:
             print("❌ 404 Not Found. Invalid URL/Game.")
             return
             
        if res.status_code != 200:
             print(f"❌ Status: {res.status_code}")
             return
             
        print("✅ Page fetched. Parsing...");
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Officials usually in a <div> with text "Officials:" or similar
        # Or footer?
        # Standard: Bottom of page, "Officials: RefName1, RefName2; Linesman: ..."
        
        # Look for text "Officials"
        officials_div = soup.find(string=re.compile("Officials"))
        if officials_div:
            print(f"Found 'Officials' text: {officials_div}")
            # Usually it's in a parent div
            parent = officials_div.parent
            print(f"Parent Content: {parent.get_text(strip=True)}")
        else:
            print("❌ 'Officials' section not found via text search.")
            
        # Also check Penalty Summary Table
        # id="penalty"
        pen_table = soup.find('table', id='penalty')
        if pen_table:
            print(f"✅ Penalty Table Found. Rows: {len(pen_table.find_all('tr'))}")
        else:
            print("⚠️ Penalty Table NOT found (maybe hidden in comments?).")
            # Hockey-Ref puts tables in comments sometimes to save load time
            
        # Try finding refs in 'boxscore_footer' or similar?
        # Let's dump text if needed.
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_hockey_ref_scraper()
