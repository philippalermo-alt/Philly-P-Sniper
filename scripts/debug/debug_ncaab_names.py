from api_clients import fetch_espn_scores
import datetime

def debug_ncaab_names():
    # Dates: Jan 22, Jan 23, 2026
    dates = ['20260122', '20260123']
    
    for d in dates:
        print(f"\n🏀 Checking NCAAB Scores for {d}...")
        games = fetch_espn_scores(['NCAAB'], specific_date=d)
        
        found_target = False
        for g in games:
            h = g['home']
            a = g['away']
            
            # Check for our hanging suspects
            suspects = ['IUPUI', 'Indianapolis', 'IU Indy', 'Tenn', 'SIU', 'Edwardsville', 'Arkansas', 'Southern']
            
            is_suspect = False
            for s in suspects:
                if s.lower() in h.lower() or s.lower() in a.lower():
                    is_suspect = True
            
            if is_suspect:
                print(f"  Found Potential Match: {a} vs {h} ({g['score_text']})")
                found_target = True
        
        if not found_target:
            print("  ❌ No matches found for suspects.")
            
if __name__ == "__main__":
    debug_ncaab_names()
