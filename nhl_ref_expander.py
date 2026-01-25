import pandas as pd
import requests
import time
import os
import ast

INPUT_FILE = "nhl_backfill_final.csv"
OUTPUT_FILE = "nhl_ref_game_logs_v2.csv"

def fetch_espn_game_stats(game_id):
    url = f"https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/summary?event={game_id}"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            print(f"❌ Failed {game_id}: {r.status_code}")
            return None
        
        data = r.json()
        box = data.get('boxscore', {})
        teams = box.get('teams', [])
        
        competition = data.get('header', {}).get('competitions', [{}])[0]
        competitors = competition.get('competitors', [])
        
        stats = {
            'home_penalties': 0, 'away_penalties': 0,
            'home_ppo': 0, 'away_ppo': 0,
            'total_penalties': 0, 'total_ppo': 0,
            'home_score': 0, 'away_score': 0
        }

        # Parse Scores from Header -> Competitors
        for c in competitors:
            s = 'home' if c['homeAway'] == 'home' else 'away'
            stats[f'{s}_score'] = int(c.get('score', 0))

        # Parse Penalties from Boxscore -> Teams
        for t in teams:
            side = 'home' if t['homeAway'] == 'home' else 'away'
            for s in t.get('statistics', []):
                val = float(s['displayValue'])
                if s['name'] == 'penalties':
                    stats[f'{side}_penalties'] = val
                elif s['name'] == 'powerPlayOpportunities':
                    stats[f'{side}_ppo'] = val
                    
        stats['total_penalties'] = stats['home_penalties'] + stats['away_penalties']
        stats['total_ppo'] = stats['home_ppo'] + stats['away_ppo']
        stats['home_pp_diff'] = stats['home_ppo'] - stats['away_ppo']
        
        return stats
        
    except Exception as e:
        print(f"❌ Error {game_id}: {e}")
        return None

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Input file {INPUT_FILE} not found.")
        return

    print(f"📖 Reading {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE)
    
    # Check if we already have progress
    if os.path.exists(OUTPUT_FILE):
        print("🔄 Resuming from existing output...")
        existing = pd.read_csv(OUTPUT_FILE)
        processed_ids = set(existing['GameID'].astype(str))
    else:
        existing = pd.DataFrame()
        processed_ids = set()

    results = []
    
    total = len(df)
    for i, row in df.iterrows():
        g_id = str(row['GameID'])
        
        if g_id in processed_ids:
            continue
            
        print(f"[{i+1}/{total}] Processing Game {g_id}...")
        
        stats = fetch_espn_game_stats(g_id)
        if stats:
            # Parse Refs
            refs = row['Referees']
            try:
                ref_list = ast.literal_eval(refs)
                ref1 = ref_list[0] if len(ref_list) > 0 else None
                ref2 = ref_list[1] if len(ref_list) > 1 else None
            except:
                ref1, ref2 = None, None
            
            entry = {
                'GameID': g_id,
                'Date': row['Date'],
                'Game': row['Game'],
                'Ref1': ref1,
                'Ref2': ref2,
                **stats
            }
            results.append(entry)
            
        # Rate limit friendly
        time.sleep(0.5)
        
        # Incremental Save
        if len(results) >= 10:
            new_df = pd.DataFrame(results)
            if not os.path.exists(OUTPUT_FILE) and existing.empty:
                 new_df.to_csv(OUTPUT_FILE, index=False)
            else:
                 new_df.to_csv(OUTPUT_FILE, mode='a', header=False, index=False)
            results = []
            print("💾 Saved batch.")

    # Final Save
    if results:
        new_df = pd.DataFrame(results)
        if not os.path.exists(OUTPUT_FILE) and existing.empty:
             new_df.to_csv(OUTPUT_FILE, index=False)
        else:
             new_df.to_csv(OUTPUT_FILE, mode='a', header=False, index=False)
        print("✅ Done.")

if __name__ == "__main__":
    main()
