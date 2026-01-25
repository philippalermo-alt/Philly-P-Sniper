import requests
import difflib
import scipy.stats as stats
import logging
from datetime import datetime, timezone, timedelta
from config import Config
from api_clients import get_nhl_player_stats
from dotenv import load_dotenv
import os

# Setup simple logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

load_dotenv()
# Ensure API key is set
if not Config.ODDS_API_KEY:
    Config.ODDS_API_KEY = os.getenv('ODDS_API_KEY')

print("🚀 Starting NHL Model Trace...")

# 1. Load Player Stats
print("📊 Fetching Official NHL Stats...")
player_stats = get_nhl_player_stats()
if not player_stats:
    print("❌ Failed to load player stats.")
    exit()
print(f"✅ Loaded {len(player_stats)} players.")

# 2. Fetch Odds
print("🎲 Fetching NHL Odds (H2H + SOG)...")
api_key = Config.ODDS_API_KEY
sport = 'icehockey_nhl'
regions = 'us,us2'
markets = 'player_shots_on_goal'

# Fetch list of events first
h2h_url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/?apiKey={api_key}&regions={regions}&markets=h2h"
res = requests.get(h2h_url).json()

if not isinstance(res, list):
    print(f"❌ API Error: {res}")
    exit()

print(f"found {len(res)} games.")

processed_count = 0
bet_candidates = 0

for game in res:
    game_id = game['id']
    home_team = game['home_team']
    away_team = game['away_team']
    commence_time = game['commence_time']
    
    # Check if game is tonight/soon
    mdt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
    now_utc = datetime.now(timezone.utc)
    time_diff = (mdt - now_utc).total_seconds() / 3600
    
    if not (-2 < time_diff < 30):
        continue
        
    print(f"\n🏒 Checking {away_team} @ {home_team} (In {time_diff:.1f}h)")
    
    # Fetch SOG odds for this game
    prop_url = f"https://api.the-odds-api.com/v4/sports/{sport}/events/{game_id}/odds?apiKey={api_key}&regions={regions}&markets={markets}&oddsFormat=decimal"
    prop_res = requests.get(prop_url).json()
    
    bookmakers = prop_res.get('bookmakers', [])
    if not bookmakers:
        print("   ⚠️ No bookmakers with SOG props.")
        continue
        
    print(f"   found {len(bookmakers)} bookmakers with props.")
    
    # Process Props
    for bookie in bookmakers:
        if bookie['key'] not in Config.PREFERRED_BOOKS:
            continue
            
        # print(f"   📖 Checking {bookie['title']}...")
        
        for market in bookie['markets']:
            if market['key'] != 'player_shots_on_goal':
                continue
                
            for outcome in market['outcomes']:
                processed_count += 1
                
                # Handling Odds API variations
                raw_name = outcome.get('name', '')
                raw_desc = outcome.get('description', '')
                
                # Check which one is the player name
                # Simple heuristic: "Over"/"Under" is not the player
                if raw_name in ['Over', 'Under'] and raw_desc:
                    player_name = raw_desc
                    bet_type_desc = raw_name
                else:
                    player_name = raw_name
                    bet_type_desc = raw_desc if raw_desc else 'Over' # Default if missing?
                
                price = outcome['price']
                point = outcome.get('point')
                
                if not point:
                    continue

                # 1. Name Match
                match = difflib.get_close_matches(player_name, player_stats.keys(), n=1, cutoff=0.85)
                if not match:
                    # Only print mismatches if it's not a common weird one
                    # print(f"      ❌ Name Mismatch: {player_name} (Closest: {difflib.get_close_matches(player_name, player_stats.keys(), n=1, cutoff=0.6)})")
                    continue
                
                p_stat = player_stats[match[0]]
                avg = p_stat['avg_shots']
                
                # 2. Edge Calc
                mu = avg
                line = point
                
                if bet_type_desc == 'Over':
                    prob = 1 - stats.poisson.cdf(int(line), mu)
                else: # Under
                    prob = stats.poisson.cdf(int(line), mu)
                    
                # Calibration (0.9 in code?)
                true_prob = prob * 0.90 # Conservatism
                true_prob = min(true_prob, 0.85)
                
                edge = (true_prob * price) - 1
                
                if edge > 0:
                    print(f"   👀 {player_name} {bet_type_desc} {line} @ {price} | Avg: {avg:.2f} | Prob: {true_prob:.2f} | Edge: {edge*100:.1f}%")
                    
                    if edge >= 0.04:
                        print(f"      ✅ BET CANDIDATE!")
                        bet_candidates += 1
                # else:
                #    print(f"      📉 {player_name} {bet_type_desc} {line} @ {price} | Avg: {avg:.2f} | Prob: {true_prob:.2f} | Edge: {edge*100:.1f}%")

print(f"\n🏁 Trace Complete. Found {bet_candidates} candidates out of {processed_count} props checked.")
