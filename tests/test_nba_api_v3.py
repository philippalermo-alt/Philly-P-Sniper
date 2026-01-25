
from nba_api.stats.endpoints import boxscoresummaryv2
import requests

# Manual V3 check because nba_api might not have a dedicated V3 class wrapped perfectly yet,
# or we can try to invoke the endpoint URL directly if the wrapper is old.
# But let's check if there is a V3 wrapper available in the installed version.
# Actually, the warning said "Users should moving to BoxScoreSummaryV3".

try:
    from nba_api.stats.endpoints import BoxScoreSummaryV3
    print("✅ Found BoxScoreSummaryV3 class!")
except ImportError:
    print("⚠️ BoxScoreSummaryV3 class NOT found in nba_api wrapper.")
    print("Trying direct request to V3 endpoint...")

# Direct Request to stats.nba.com/stats/boxscoresummaryv3
game_id = "0022500017"
url = f"https://stats.nba.com/stats/boxscoresummaryv3?GameID={game_id}"
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.nba.com/',
    'Origin': 'https://www.nba.com',
    'x-nba-stats-origin': 'stats',
    'x-nba-stats-token': 'true'
}

print(f"🕵️‍♂️ Fetching {url}...")
try:
    r = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    data = r.json()
    
    # Inspect structure
    # V3 often returns 'boxScoreSummary' dictionary
    if 'boxScoreSummary' in data:
        summary = data['boxScoreSummary']
        if 'officials' in summary:
            print("✅ Found 'officials' in boxScoreSummary!")
            print(summary['officials'])
        else:
            print("❌ 'officials' key NOT found in summary.")
            print("Keys:", summary.keys())
    else:
        print("❌ 'boxScoreSummary' key not found in root.")
        print("Root Keys:", data.keys())

except Exception as e:
    print(f"❌ Error: {e}")
