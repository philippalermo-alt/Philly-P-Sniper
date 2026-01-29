
import json
import sys
import os
from datetime import datetime

# Add root to path for imports
sys.path.append(os.getcwd())

from ncaab_h1_model.ncaab_h1_scraper import NCAAB_H1_Scraper

DATA_FILE = 'ncaab_h1_model/data/historical_games.json'

def patch_dates():
    print(f"🔧 Patching dates for {DATA_FILE}...")
    
    if not os.path.exists(DATA_FILE):
        print(f"❌ File not found: {DATA_FILE}")
        return

    with open(DATA_FILE, 'r') as f:
        games = json.load(f)
    
    total_games = len(games)
    print(f"   Loaded {total_games} games.")
    
    # Check coverage
    missing_date = [g for g in games if 'date' not in g]
    print(f"   Missing dates: {len(missing_date)}/{total_games}")
    
    if len(missing_date) == 0:
        print("✅ All games have dates. Nothing to do.")
        return

    # Initialize Scraper
    scraper = NCAAB_H1_Scraper()
    
    # Fetch Schedule (This season)
    print("   Fetching schedule to map IDs to Dates...")
    schedule_games = scraper.fetch_schedule() # Defaults to current season
    
    # Build Map
    id_date_map = {str(g['id']): g['date'] for g in schedule_games}
    
    # Also Map for Int IDs just in case
    for g in schedule_games:
        id_date_map[int(g['id'])] = g['date']
        
    print(f"   Map built with {len(id_date_map)} entries.")
    
    # Patch
    patched_count = 0
    not_found_count = 0
    
    for g in games:
        if 'date' not in g:
            gid = g['game_id'] # Use 'game_id' from json
            
            # Try str and int
            date_val = id_date_map.get(str(gid)) or id_date_map.get(int(gid))
            
            if date_val:
                g['date'] = date_val
                patched_count += 1
            else:
                not_found_count += 1
                # print(f"Warning: ID {gid} not found in fetch.")

    print(f"   Patched: {patched_count}")
    print(f"   Still Missing: {not_found_count}")
    
    # Save
    with open(DATA_FILE, 'w') as f:
        json.dump(games, f, indent=2)
        
    print("✅ Patch Complete.")

if __name__ == "__main__":
    patch_dates()
