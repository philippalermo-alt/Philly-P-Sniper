
import pandas as pd
import numpy as np

def merge_refs():
    # 1. Load Data
    assigns = pd.read_csv("nba_ref_assignments_2025_26.csv")
    stats = pd.read_csv("nba_ref_stats_2025_26.csv")
    
    print(f"Assigns: {len(assigns)} games")
    print(f"Stats: {len(stats)} refs")
    
    # 2. Clean Names & Prepare Lookups
    # Stats file has "REFEREE" col
    # Assigns file has "Ref1", "Ref2", "Ref3"
    
    # Create dict for fast lookup
    # Metrics we care about: HOME TEAM WIN%, CALLED FOULS PER GAME, FOUL% AGAINST HOME TEAMS
    
    ref_map = {}
    for _, row in stats.iterrows():
        name = row['REFEREE'].strip()
        ref_map[name] = {
            'HomeWinPct': row.get('HOME TEAM WIN%', 0.5),
            'FoulsPerGame': row.get('CALLED FOULS PER GAME', 40.0),
            'HomeFoulPct': row.get('FOUL% AGAINST HOME TEAMS', 0.5)
        }
        
    print(f"Built map for {len(ref_map)} refs.")
    
    # 3. Calculate Crew Metrics
    crew_home_win = []
    crew_fouls = []
    crew_home_foul_pct = []
    
    misses = 0
    
    for _, row in assigns.iterrows():
        crew_stats = {'hw': [], 'fpg': [], 'hfp': []}
        
        for r_col in ['Ref1', 'Ref2', 'Ref3']:
            r_name = str(row[r_col]).strip()
            if r_name in ref_map:
                s = ref_map[r_name]
                crew_stats['hw'].append(s['HomeWinPct'])
                crew_stats['fpg'].append(s['FoulsPerGame'])
                crew_stats['hfp'].append(s['HomeFoulPct'])
            else:
                # If ref is missing, assume average/neutral
                # print(f"Miss: {r_name}")
                pass
                
        if len(crew_stats['hw']) > 0:
            crew_home_win.append(np.mean(crew_stats['hw']))
            crew_fouls.append(np.mean(crew_stats['fpg']))
            crew_home_foul_pct.append(np.mean(crew_stats['hfp']))
        else:
            misses += 1
            crew_home_win.append(0.5) # Neutral
            crew_fouls.append(40.0)
            crew_home_foul_pct.append(0.5)
            
    assigns['Ref_HomeWin'] = crew_home_win
    assigns['Ref_Fouls'] = crew_fouls
    assigns['Ref_HomeFoulPct'] = crew_home_foul_pct
    
    print(f"Processed 641 games. {misses} games had 0 known refs.")
    
    # Save
    assigns.to_csv("training_data_refs.csv", index=False)
    print("✅ Saved to training_data_refs.csv")

if __name__ == "__main__":
    merge_refs()
