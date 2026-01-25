
import cloudscraper
import requests

scraper = cloudscraper.create_scraper()
# Oct 22, 2025: DET @ IND (example) or TOR @ ATL
# https://www.basketball-reference.com/boxscores/202510220DET.html
url = "https://www.basketball-reference.com/boxscores/202510220DET.html"

print(f"Fetching {url}...")
try:
    r = scraper.get(url)
    print(f"Status: {r.status_code}")
    if "Officials" in r.text:
        print("✅ Found 'Officials' in text")
        # Print context around "Officials"
        idx = r.text.find("Officials")
        print(r.text[idx:idx+500])
    else:
        print("❌ 'Officials' NOT found in text")
        # maybe it's "Referees"?
        if "Referees" in r.text:
             print("✅ Found 'Referees'")
             idx = r.text.find("Referees")
             print(r.text[idx:idx+500])
except Exception as e:
    print(f"❌ Error: {e}")
