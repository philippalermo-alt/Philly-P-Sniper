import itertools
import pandas as pd
from datetime import datetime
from config.settings import Config

def generate_parlays(df, max_legs=3, min_edge=0.01, max_edge=0.10, min_odds=1.4, max_odds=3.0, min_sharp_score=30):
    """
    Generates recommended parlays from a DataFrame of single bets.
    
    Strategy: "The Sniper Triples"
    1. Filter: Edge between 1% and 10% (Goldilocks Zone).
    2. Filter: Odds between -250 (1.4) and +200 (3.0).
    3. Filter: Sharp Score >= 30 (Strict Quality Control).
    4. Independence: Group by EventID and pick ONLY the single best edge per event.
    5. Combine: Generate 3-leg combinations.
    """
    
    # 1. Validation
    if df.empty:
        return []
    
    required_cols = ['Event', 'Selection', 'Edge_Val', 'Dec_Odds', 'Sport']
    if not all(col in df.columns for col in required_cols):
        return [] # Missing data
        
    # 2. Filtering
    # Copy to avoid settingWithCopy warnings
    candidates = df.copy()
    
    # Edge Filter
    candidates = candidates[
        (candidates['Edge_Val'] >= min_edge) & 
        (candidates['Edge_Val'] <= max_edge)
    ]
    
    # Sharp Score Filter (User Request: >= 30)
    if 'sharp_score' in candidates.columns:
        candidates['sharp_score'] = pd.to_numeric(candidates['sharp_score'], errors='coerce').fillna(0)
        candidates = candidates[candidates['sharp_score'] >= min_sharp_score]
    
    # Odds Filter (Dec_Odds)
    candidates = candidates[
        (candidates['Dec_Odds'] >= min_odds) & 
        (candidates['Dec_Odds'] <= max_odds)
    ]
    
    if candidates.empty:
        return []

    # 3. Independence Enforcement (1 Leg Per Game)
    # We assume 'Event' string is unique enough per game. 
    # Pick the bet with the HIGHEST edge for each unique Event.
    best_per_event = candidates.sort_values('Edge_Val', ascending=False).groupby('Event').first().reset_index()
    
    # Need at least 3 distinct games to make a triple
    if len(best_per_event) < 3:
        return []

    # 4. Combinatorial Generation
    # We convert to a list of dicts for iteration
    pool = best_per_event.to_dict('records')
    
    combos = list(itertools.combinations(pool, max_legs))
    
    recommendations = []
    
    for legs in combos:
        # legs is a tuple of 3 bet dicts
        
        # Calculate Parlay Metrics
        # Odds = O1 * O2 * O3
        combined_odds = 1.0
        for leg in legs:
            combined_odds *= leg['Dec_Odds']
            
        # EV Approximation (rough): (1+E1)*(1+E2)*(1+E3) - 1
        # Ideally: True Prob = P1*P2*P3. Fair Odds = 1/TrueProb. EV = (Odds/FairOdds) - 1.
        
        combined_prob = 1.0
        for leg in legs:
            # implied_prob = 1 / leg['Dec_Odds'] 
            # true_prob = implied_prob + (implied_prob * leg['Edge_Val']) # roughly
            # Let's use the model's True_Prob if available, else derive it?
            # Model usually has 'True_Prob' in it.
            if 'True_Prob' in leg:
                combined_prob *= leg['True_Prob']
            else:
                # Fallback estimation
                imp = 1 / leg['Dec_Odds']
                true_p = imp / (1 - leg['Edge_Val']) # E = (P*O)-1 => P = (E+1)/O
                combined_prob *= true_p
                
        # EV Calculation
        # ROI = (Probability * Odds) - 1
        parlay_ev = (combined_prob * combined_odds) - 1
        
        # Smart Staking (Kelly Criterion for Parlay)
        # b = combined_odds - 1
        # p = combined_prob
        # q = 1 - p
        # f = (bp - q) / b
        bankroll = 1000.0 # Default fallback, dashboard should override or we return percentage
        
        if parlay_ev > 0:
            b = combined_odds - 1
            p = combined_prob
            q = 1 - p
            kelly_fraction = (b*p - q) / b
            # Conservative Parlay Factor (0.25 Kelly) due to high variance
            kelly_stake_pct = max(0, kelly_fraction * 0.25)
        else:
            kelly_stake_pct = 0
            
        rec = {
            'legs': legs,
            'combined_odds': round(combined_odds, 2),
            'expected_value': parlay_ev,
            'kelly_pct': kelly_stake_pct,
            'diversity_score': len(set(leg['Sport'] for leg in legs)) # Count unique sports
        }
        recommendations.append(rec)
        
    # 5. Sorting
    # Sort by Expected Value (descending)
    recommendations.sort(key=lambda x: x['expected_value'], reverse=True)
    
    return recommendations[:5] # Return top 5
