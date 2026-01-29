import sys
import os
import difflib
import json
sys.path.append(os.getcwd())

from data.clients.action_network import get_action_network_data
from utils.team_names import normalize_team_name
from config.settings import Config

# Mock Context/Odds data (or fetch if possible, but let's assume we can fetch)
# Actually, let's use the pipelines fetch logic 
from pipeline.stages.fetch import execute as fetch_execute
from pipeline.orchestrator import PipelineContext

def debug_matching():
    print("🔍 [DIAGNOSTIC] Starting Sharp Data Matching Audit...")
    
    # 1. Fetch Real Sharp Data
    print("   -> Fetching Action Network Data...")
    sharp_data = get_action_network_data()
    print(f"   -> Loaded {len(sharp_data)} Sharp Records.")
    
    if not sharp_data:
        print("❌ CRITICAL: Sharp Data is EMPTY. Aborting.")
        return

    # 2. Print Sample Sharp Keys for comparison
    print("\n📋 Sample Sharp Keys (Normalized from Source):")
    for k in list(sharp_data.keys())[:10]:
        print(f"   - '{k}'")

    # 3. Fetch Real Odds Data (Simulated Pipeline Context)
    print("\n   -> Fetching Odds API Data (Target Sports: NHL, NBA, NCAAB)...")
    context = PipelineContext("DEBUG_RUN", ['NHL', 'NBA', 'NCAAB'])
    # Minimal mock of fetch execution
    # We can't easily call fetch.execute because it modifies context heavily and might require API keys in env
    # Let's try to just use the client directly if possible, or rely on cache?
    # Better: Use the main pipeline's fetch logic but trap the results.
    
    # We will simulate the matching loop for a few 'known' matchups if we can't fetch live odds easily without main.py structure
    # Actually, main.py structure is available. 
    
    # from data.clients.odds_api import get_odds # DOES NOT EXIST
    import requests
    from datetime import datetime, timedelta, timezone

    def _map_sport_to_key(sport):
        idx = {
            'NBA': 'basketball_nba',
            'NCAAB': 'basketball_ncaab',
            'NHL': 'icehockey_nhl',
        }
        return idx.get(sport)
    
    # Analyze sports
    for sport_display in ['NHL', 'NBA', 'NCAAB']:
        sport_key = _map_sport_to_key(sport_display)
        print(f"\n🏆 Analyzing {sport_display} ({sport_key})...")
        
        # 36-Hour Window (Strict)
        now_utc = datetime.now(timezone.utc)
        limit_time = now_utc + timedelta(hours=36)
        iso_limit = limit_time.replace(microsecond=0).isoformat().replace('+00:00', 'Z')
        
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={Config.ODDS_API_KEY}&regions=us,us2&markets=h2h,spreads,totals&oddsFormat=decimal&commenceTimeTo={iso_limit}"
        res = requests.get(url, timeout=15)
        
        if res.status_code != 200:
            print(f"   ⚠️ Failed to fetch {sport_display}: {res.status_code}")
            continue
            
        odds_data = res.json()
        print(f"   -> Found {len(odds_data)} games.")
        
        failures = 0
        successes = 0
        
        for match in odds_data:
            home = match.get('home_team')
            away = match.get('away_team')
            
            # --- THE MATCHING LOGIC (COPIED FROM markets.py) ---
            matched_key = None
            n_home = normalize_team_name(home)
            n_away = normalize_team_name(away)
            
            # 1. Containment
            for sk in sharp_data.keys():
                try:
                    s_away, s_home = sk.split(' @ ')
                except:
                    continue
                match_h = (s_home in n_home) or (n_home in s_home)
                match_a = (s_away in n_away) or (n_away in s_away)
                if match_h and match_a:
                    matched_key = sk
                    break
            
            # 2. Difflib Fallback
            if not matched_key:
                search_key = f"{n_away} @ {n_home}"
                # Use strict cutoff from markets.py (0.85) to verify failure
                m_match = difflib.get_close_matches(search_key, sharp_data.keys(), n=1, cutoff=0.85) 
                if m_match:
                    matched_key = m_match[0]
            
            # --- REPORTING ---
            if matched_key:
                successes += 1
                s_data = sharp_data.get(matched_key)
                print(f"   ✅ MATCH: {away} @ {home} (Time: {match.get('commence_time')})")
                print(f"      -> Key:   {matched_key}")
                print(f"      -> Data:  {json.dumps(s_data, indent=2)}")
            else:
                failures += 1
                # Only print failures if they are NOT clearly future games (optional, but let's see all)
                ct = match.get('commence_time')
                print(f"   ❌ FAIL:  {away} @ {home} (Time: {ct})")
                print(f"      - Norm:   {n_away} @ {n_home}")
                print(f"      - Closest Sharp Keys (Difflib): {difflib.get_close_matches(f'{n_away} @ {n_home}', sharp_data.keys(), n=3, cutoff=0.6)}")

        print(f"   📊 Summary for {sport_display}: {successes} matched, {failures} failed.")

if __name__ == "__main__":
    debug_matching()
