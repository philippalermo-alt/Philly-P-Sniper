import sys
import os
sys.path.append(os.getcwd())

from models.soccer import SoccerModelV2
import requests
from config.settings import Config
from utils.team_names import normalize_team_name

def scan_raw():
    print("🚀 Starting Raw UCL Scan...")
    
    # 1. Fetch Odds
    print("🌍 Fetching Live Odds...")
    url = f"https://api.the-odds-api.com/v4/sports/soccer_uefa_champs_league/odds/?apiKey={Config.ODDS_API_KEY}&regions=us&markets=h2h,totals&oddsFormat=decimal"
    res = requests.get(url)
    if res.status_code != 200:
        print(f"❌ API Error: {res.text}")
        return
        
    games = res.json()
    print(f"✅ Found {len(games)} Games.\n")
    
    # 2. Load Model
    model = SoccerModelV2()
    print(f"🧠 Model Loaded (Teams: {len(model.team_stats)})\n")
    
    print(f"{'HOME':<20} | {'AWAY':<20} | {'PROB':<6} | {'FAIR':<6} | {'BOOK':<6} | {'EDGE':<6} | {'STATUS'}")
    print("-" * 100)
    
    for g in games:
        h = g['home_team']
        a = g['away_team']
        
        # Extract Market Odds
        odds_totals = 0.0
        odds_home = 0.0
        odds_draw = 0.0
        odds_away = 0.0
        bookie_name = "None"
        
        for bk in g['bookmakers']:
            if bk['key'] in ['pinnacle', 'fanduel', 'draftkings']:
                # Totals
                for m in bk['markets']:
                    if m['key'] == 'totals':
                        for out in m['outcomes']:
                            if out['name'] == 'Over' and out['point'] == 2.5:
                                odds_totals = out['price']
                                bookie_name = bk['key']
                    # Moneyline (H2H)
                    elif m['key'] == 'h2h':
                        for out in m['outcomes']:
                            if out['name'] == h: 
                                odds_home = out['price']
                                bookie_name = bk['key']
                            elif out['name'] == a: odds_away = out['price']
                            elif out['name'] == 'Draw': odds_draw = out['price']
                            
            if odds_totals > 0 and odds_home > 0: break
            
        # Run Model
        current_odds = {'over': odds_totals if odds_totals > 0 else 1.90, 'under': 1.90, 'line': 2.5}

        
        pred = model.predict_match(h, a, "soccer_uefa_champs_league", current_odds)
        
        if pred:
            # Totals Data
            p_over = pred['prob_over']
            e_over = p_over - (1/odds_totals) if odds_totals > 0 else 0.0
            
            # Sides Data
            p_home = pred['home_win']
            p_away = pred['away_win']
            p_draw = pred['draw']
            
            total_prob = p_home + p_away + p_draw
            
            # Normalize
            n_home = p_home / total_prob
            n_away = p_away / total_prob
            n_draw = p_draw / total_prob
            
            # Recalculate Edge (Normalized)
            e_home_norm = n_home - (1/odds_home) if odds_home > 0 else 0.0
            
            # Print Sides (Home)
            status_h = "✅ EDGE" if e_home_norm > 0.02 else "❌"
            if odds_home == 0: status_h = "⚠️ NO ODDS"
            
            print(f"SIDE  | {h[:15]:<15} | Home Win        | {n_home:.1%} (Raw {p_home:.1%}) | {odds_home:.2f} | {e_home_norm:.1%} | {status_h} | {bookie_name}")
            print(f"      | Sum: {total_prob:.3f} | Draw: {n_draw:.1%} | Away: {n_away:.1%}")
            
            print("-" * 100)
            
        else:
            print(f"{h[:20]:<20} | {a[:20]:<20} | MODEL FAIL")

if __name__ == "__main__":
    scan_raw()
