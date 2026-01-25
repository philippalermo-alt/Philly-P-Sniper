
from utils import normalize_team_name
import difflib

def test_matching():
    # Simulation Data
    # 1. Action Network Source (Key in sharp_data)
    # Original: "OK State" @ "TCU"
    an_away = "OK State"
    an_home = "TCU"
    
    # In api_clients.py, we normalize this when building key
    norm_an_away = normalize_team_name(an_away)
    norm_an_home = normalize_team_name(an_home)
    an_key = f"{norm_an_away} @ {norm_an_home}"
    
    print(f"Action Network Key: '{an_key}'")
    # Expected: "oklahoma st @ tcu"
    
    # 2. Dashboard Source (Inputs to process_markets)
    dash_away = "Oklahoma St Cowboys"
    dash_home = "TCU Horned Frogs"
    
    # In probability_models.py, we normalize inputs
    n_dash_away = normalize_team_name(dash_away)
    n_dash_home = normalize_team_name(dash_home)
    
    print(f"Dashboard Norm: '{n_dash_away}' @ '{n_dash_home}'")
    # Expected: "oklahoma st cowboys @ tcu horned frogs"
    
    # 3. Matching Logic (from probability_models.py)
    matched = False
    
    # Mocking sharp_data keys
    sharp_keys = [an_key, "some other @ game"]
    
    for sk in sharp_keys:
        try:
            s_away, s_home = sk.split(' @ ')
        except: continue
        
        # Check overlap
        match_h = (s_home in n_dash_home) or (n_dash_home in s_home)
        match_a = (s_away in n_dash_away) or (n_dash_away in s_away)
        
        print(f"Check against '{sk}': HomeMatch={match_h}, AwayMatch={match_a}")
        
        if match_h and match_a:
            matched = True
            print("✅ MATCH FOUND!")
            break
            
    if not matched:
        print("❌ MATCH FAILED")

if __name__ == "__main__":
    test_matching()
