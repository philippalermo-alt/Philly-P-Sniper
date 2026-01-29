def simulate_filters():
    # Constants from Settings/Code (TUNED)
    MARKET_WEIGHT = 0.70 # Was 0.80
    MIN_EDGE = 0.02
    MAX_RAW_EDGE = 0.18 # Was 0.12
    
    # Data from previous debug run
    games = [
        {'team': 'AS Monaco', 'model': 0.343, 'odds': 3.90},
        {'team': 'Ajax',      'model': 0.371, 'odds': 3.15},
        {'team': 'Frankfurt', 'model': 0.499, 'odds': 4.90},
        {'team': 'Napoli',    'model': 0.406, 'odds': 3.55},
        {'team': 'PSV',       'model': 0.225, 'odds': 5.25}
    ]
    
    print(f"{'TEAM':<15} | {'MODEL':<6} | {'ODDS':<6} | {'IMPLIED':<6} | {'RAW EDGE':<8} | {'ACTION':<10}")
    print("-" * 80)
    
    for g in games:
        m_prob = g['model']
        odds = g['odds']
        implied = 1.0 / odds
        
        # 1. Raw Edge (Used for Safety Filter)
        raw_edge = m_prob - implied
        
        # 2. Safety Filter
        if raw_edge >= MAX_RAW_EDGE:
            print(f"{g['team']:<15} | {m_prob:.1%} | {odds:.2f} | {implied:.1%}   | {raw_edge:.1%}   | ❌ BLOCKED (Safety > 12%)")
            continue
            
        # 3. Market Weighting (Used for Min Edge)
        # tp = (Weight * Implied) + ((1-Weight) * Model)
        weighted_prob = (MARKET_WEIGHT * implied) + ((1 - MARKET_WEIGHT) * m_prob)
        
        # 4. Weighted Edge
        # In code, edge for Kelly is typically checked against Min Edge? 
        # Wait, markets.py line 678 checks 'edge' which is RAW EDGE against MIN_EDGE.
        # But 'true_prob' (TP) is stored for something? 
        # Actually markets.py calculates 'tp' (Line 667) but uses 'edge' (Line 670 which is Raw Edge) for checks.
        
        # Let's re-read markets.py CAREFULLY. 
        # Line 670: edge = true_prob - (1.0/price). 
        # WHERE true_prob comes from Line 663: true_prob = norm_probs.get(key).
        # WAIIIIIIT. 
        # Line 667 calculates 'tp' (Weighted) but assigns it to a variable 'tp'.
        # Line 670 calculates 'edge' using 'true_prob' (Unweighted Normalized Model Prob).
        # So Market Weighting IS NOT APPLIED to the Edge used for Filtering?!
        
        # If Market Weight is NOT applied to Edge, then Ajax (5.3% Edge) SHOULD PASS.
        # Why did it fail?
        pass

if __name__ == "__main__":
    simulate_filters()
