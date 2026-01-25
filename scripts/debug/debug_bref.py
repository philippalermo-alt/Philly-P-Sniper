
import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}
# Oct 22, 2025
url = "https://www.basketball-reference.com/boxscores/?month=10&day=22&year=2025"
print(f"Fetching {url}...")
r = requests.get(url, headers=headers)
print(f"Status: {r.status_code}")
if "game_summary" in r.text:
    print("✅ Found 'game_summary'")
else:
    print("❌ 'game_summary' NOT found")
    print(r.text[:2000])
