
import requests
import pandas as pd
import datetime
import time
import random

def backfill_espn():
    start_date = datetime.date(2025, 10, 7)
    end_date = datetime.date.today() - datetime.timedelta(days=1)
    
    print(f"⏳ Starting ESPN API Backfill ({start_date} to {end_date})...", flush=True)
    
    assignments = []
    
    current_date = start_date
    while current_date <= end_date:
        d_str = current_date.strftime("%Y%m%d")
        print(f"📅 Processing {d_str}...", flush=True)
        
        try:
            # 1. Get Schedule
            url_score = f"http://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard?dates={d_str}"
            res = requests.get(url_score)
            data = res.json()
            
            events = data.get('events', [])
            print(f"   Found {len(events)} games.", flush=True)
            
            for evt in events:
                game_id = evt['id']
                name = evt['name']
                
                # 2. Get Summary (Officials)
                # Don't hammer API too hard
                time.sleep(0.5) 
                
                sum_url = f"http://site.api.espn.com/apis/site/v2/sports/hockey/nhl/summary?event={game_id}"
                try:
                    s_res = requests.get(sum_url, timeout=10)
                    s_data = s_res.json()
                    
                    officials = s_data.get('gameInfo', {}).get('officials', [])
                    
                    if officials:
                        # Extract names
                        refs = []
                        for off in officials:
                            # Position: "Referee" or "Linesman"
                            pos = off.get('position', {}).get('name', 'Unknown')
                            name_ref = off.get('displayName', off.get('fullName'))
                            
                            if pos == 'Referee':
                                refs.append(name_ref)
                        
                        if refs:
                            assignments.append({
                                'Date': current_date,
                                'Game': name,
                                'GameID': game_id,
                                'Referees': refs
                            })
                            print(f"      ✅ {name} -> {refs}", flush=True)
                        else:
                             print(f"      ⚠️ No Referees listed for {name}", flush=True)
                    else:
                        print(f"      ❌ No official data for {name}", flush=True)
                        
                except Exception as e:
                    print(f"      ❌ Error fetching summary {game_id}: {e}", flush=True)
                    
        except Exception as e:
            print(f"   ❌ Error fetching schedule {d_str}: {e}", flush=True)
            
        current_date += datetime.timedelta(days=1)
        time.sleep(1.0)
        
    # Save
    df = pd.DataFrame(assignments)
    df.to_csv("nhl_backfill_final.csv", index=False)
    print(f"💾 Saved {len(df)} games to nhl_backfill_final.csv", flush=True)

if __name__ == "__main__":
    backfill_espn()
