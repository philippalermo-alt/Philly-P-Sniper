
import cloudscraper

scraper = cloudscraper.create_scraper()
url = "https://www.basketball-reference.com/boxscores/?month=10&day=22&year=2025"

print(f"Fetching {url} with Cloudscraper...")
try:
    r = scraper.get(url)
    print(f"Status: {r.status_code}")
    if "game_summary" in r.text:
        print("✅ Found 'game_summary'")
        print(r.text[:500])
    else:
        print("❌ 'game_summary' NOT found")
        print("Page Title:", r.text.split('<title>')[1].split('</title>')[0] if '<title>' in r.text else "No Title")
except Exception as e:
    print(f"❌ Error: {e}")
