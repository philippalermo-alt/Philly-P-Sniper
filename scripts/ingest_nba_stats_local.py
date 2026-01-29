import argparse
import pandas as pd
import time
import json
import os
import random
from datetime import datetime
from nba_api.stats.endpoints import leaguegamelog, boxscoreadvancedv2

# --- Configuration ---
DEFAULT_SEASONS = ['2021-22', '2022-23', '2023-24', '2024-25']
# Updated Modern Headers
HEADERS = {
    'Host': 'stats.nba.com',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.nba.com/',
    'Origin': 'https://www.nba.com',
    'Connection': 'keep-alive',
    'x-nba-stats-origin': 'stats',
    'x-nba-stats-token': 'true',
    'Sec-Fetch-Site': 'same-site',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Dest': 'empty',
}

class CheckpointManager:
    def __init__(self, filename=".nba_ingest_checkpoint.json"):
        self.filename = filename
        self.processed_games = set()
        self.load()

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    data = json.load(f)
                    self.processed_games = set(data.get('processed_games', []))
                print(f"🔄 Loaded Checkpoint: {len(self.processed_games)} games already processed.")
            except Exception as e:
                print(f"⚠️ Checkpoint Corrupt: {e}")

    def add(self, game_id):
        self.processed_games.add(str(game_id))
        self._save()

    def is_processed(self, game_id):
        return str(game_id) in self.processed_games

    def _save(self):
        with open(self.filename, 'w') as f:
            json.dump({'processed_games': list(self.processed_games)}, f)

def fetch_with_retry(api_call_func, max_retries=3, base_delay=2.0, **kwargs):
    """Execute generic API call with exponential backoff and debug."""
    for attempt in range(max_retries):
        try:
            # Add timeout to kwargs if not present (handled by requests inside nba_api)
            # nba_api kwargs are passed to Endpoint.__init__
            return api_call_func(**kwargs, headers=HEADERS, timeout=10)
        except Exception as e:
            wait = base_delay * (2 ** attempt) + random.uniform(0, 1)
            print(f"   ⚠️ API Fail (Attempt {attempt+1}/{max_retries}): {e}")
            
            # If it's a JSON decode error, it often means we got HTML (Block page)
            if 'Expecting value' in str(e) or 'resultSet' in str(e):
                print("      [Blocker Detected] Likely Cloudflare Challenge. Increasing wait.")
                wait += 5.0
            
            print(f"      Waiting {wait:.1f}s...")
            time.sleep(wait)
    raise Exception("Max Retry Exceeded")

def get_season_schedule(season):
    """Fetch schedule for a single season."""
    print(f"📅 Fetching Schedule for {season}...")
    try:
        log = fetch_with_retry(
            leaguegamelog.LeagueGameLog, 
            season=season, 
            season_type_all_star='Regular Season'
        )
        df = log.get_data_frames()[0]
        records = df[['GAME_ID', 'GAME_DATE', 'MATCHUP', 'TEAM_ID', 'TEAM_NAME', 'PTS']].to_dict('records')
        
        # Deduplicate (GameLog has 2 rows per game)
        games = {}
        for r in records:
            gid = r['GAME_ID']
            if gid not in games: games[gid] = []
            games[gid].append(r)
            
        valid_games = []
        for gid, parts in games.items():
            if len(parts) >= 2:
                # Identify Home/Away
                home = next((x for x in parts if ' vs. ' in x['MATCHUP']), None)
                away = next((x for x in parts if ' @ ' in x['MATCHUP']), None)
                if home and away:
                    valid_games.append({
                        'game_id': gid,
                        'date': home['GAME_DATE'],
                        'home_id': home['TEAM_ID'],
                        'home_name': home['TEAM_NAME'],
                        'home_score': home['PTS'],
                        'away_id': away['TEAM_ID'],
                        'away_name': away['TEAM_NAME'],
                        'away_score': away['PTS']
                    })
        
        # Sort by Date -> GameID
        valid_games.sort(key=lambda x: (x['date'], x['game_id']))
        print(f"✅ Found {len(valid_games)} games for {season}.")
        return valid_games
    except Exception as e:
        print(f"❌ Schedule Fetch Error: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Ingest NBA Stats Locally (Batch Mode)")
    parser.add_argument('--season', type=str, required=True, help="Season ID (e.g. 2023-24)")
    parser.add_argument('--start', type=int, default=0, help="Start Game Index")
    parser.add_argument('--end', type=int, default=None, help="End Game Index")
    parser.add_argument('--batch-size', type=int, default=50, help="Games per CSV fragment")
    parser.add_argument('--cache-dir', type=str, default="data/cache", help="Directory for partial saves")
    parser.add_argument('--merge', action='store_true', help="Merge all parts into final CSV at the end")
    
    args = parser.parse_args()
    
    # Setup Cache
    os.makedirs(args.cache_dir, exist_ok=True)
    
    # 1. Fetch Schedule
    all_games = get_season_schedule(args.season)
    if not all_games: return

    # 2. Slice Logic
    end_idx = args.end if args.end is not None else len(all_games)
    target_games = all_games[args.start : end_idx]
    
    print(f"🚀 Processing range [{args.start}:{end_idx}] ({len(target_games)} games)...")
    
    # 3. Batch Processing
    current_batch = []
    batch_idx = (args.start // args.batch_size) + 1
    
    for i, game in enumerate(target_games):
        global_idx = args.start + i
        gid = game['game_id']
        
        # Determine Batch File Name
        # We align files to 0-49, 50-99 boundaries for consistency
        current_batch_num = (global_idx // args.batch_size) + 1
        batch_filename = os.path.join(args.cache_dir, f"nba_{args.season}_part_{current_batch_num:03d}.csv")
        
        # Resume Mode: If batch file exists and looks full/processed, skip heavy API calls
        # Optimization: Check if this specific GAME is in the batch file?
        # Simpler: If batch file exists, load it to checking for duplicates.
        
        # For simplicity in this script:
        # We process linearly. If we cross a batch boundary, we dump.
        
        # Checkpoint Check
        # If the file for this batch already exists, we might implicitly skip?
        # User asked for "Resume Mode".
        # Better strategy: Check if game_id is already in the target batch file.
        
        already_done = False
        if os.path.exists(batch_filename):
            try:
                df_existing = pd.read_csv(batch_filename)
                if 'game_id' in df_existing.columns and int(gid) in df_existing['game_id'].values:
                    already_done = True
                elif 'game_id' in df_existing.columns and str(gid) in df_existing['game_id'].astype(str).values:
                    already_done = True
            except: pass
            
        if already_done:
            # print(f"⏩ {gid} already cached.")
            continue

        try:
            # Rate Limit (Safer)
            time.sleep(random.uniform(1.5, 3.0))
            
            # API Call
            adv = fetch_with_retry(boxscoreadvancedv2.BoxScoreAdvancedV2, game_id=gid)
            df_adv = adv.get_data_frames()[1]
            
            if df_adv.empty:
                print(f"⚠️ Empty stats {gid}")
                continue

            h = df_adv[df_adv['TEAM_ID'] == game['home_id']]
            a = df_adv[df_adv['TEAM_ID'] == game['away_id']]
            
            if h.empty or a.empty: continue
            
            h, a = h.iloc[0], a.iloc[0]
            
            record = {
                'game_id': gid,
                'date': game['date'],
                'season': args.season,
                'home_team': game['home_name'],
                'away_team': game['away_name'],
                'home_score': game['home_score'],
                'away_score': game['away_score'],
                'home_efg': h.get('EFG_PCT'), 'away_efg': a.get('EFG_PCT'),
                'home_tov': h.get('TM_TOV_PCT'), 'away_tov': a.get('TM_TOV_PCT'),
                'home_orb': h.get('OREB_PCT'), 'away_orb': a.get('OREB_PCT'),
                'home_ftr': h.get('FTA_RATE'), 'away_ftr': a.get('FTA_RATE'),
                'pace': h.get('PACE')
            }
            
            # Append to file IMMEDIATELY (Safety) or Batch?
            # User asked: "auto-save every batch".
            # We will append to list, then save list when batch fills.
            # actually better: Append to CSV mode.
            
            df_new = pd.DataFrame([record])
            if not os.path.exists(batch_filename):
                df_new.to_csv(batch_filename, index=False)
            else:
                df_new.to_csv(batch_filename, mode='a', header=False, index=False)
                
            print(f"✅ [{global_idx}] Saved {gid} -> part_{current_batch_num:03d}")
            
        except Exception as e:
            print(f"❌ Error {gid}: {e}")

    # Merge Step
    if args.merge:
        print("\n🧹 Merging all parts...")
        parts = [os.path.join(args.cache_dir, f) for f in os.listdir(args.cache_dir) if f.startswith(f"nba_{args.season}_part")]
        parts.sort()
        
        if parts:
            full_df = pd.concat([pd.read_csv(f) for f in parts])
            out_file = f"nba_stats_{args.season}.csv"
            full_df.drop_duplicates(subset=['game_id'], inplace=True)
            full_df.to_csv(out_file, index=False)
            print(f"🎉 Merged {len(full_df)} games into {out_file}")

if __name__ == "__main__":
    main()
