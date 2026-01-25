
import json
import os
from features_soccer import compute_match_features

def test_classifier():
    # Load sample data
    with open("Brighton-Bournemouth.json", "r", encoding="utf-8-sig") as f:
        brighton_rows = json.load(f)
        
    # For testing, we'll use the same data for both teams to create a symmetric match
    # In reality, you'd load home_rows and away_rows separately
    home_rows = brighton_rows
    away_rows = brighton_rows # Duplicate for test
    
    print("📊 Computing Match Features...")
    features = compute_match_features(home_rows, away_rows)
    
    # Print Key Features
    print("\n--- Feature Vector (Subset) ---")
    keys_to_show = [
        "xG_sum", "chain_sum", "buildup_sum", "shots_sum", 
        "fragility_sum_top1xG", "home_buildup_ratio", "balance_xG_abs"
    ]
    for k in keys_to_show:
        print(f"{k}: {features.get(k, 0):.4f}")
        
    # --- 4) Rules-Based Scorer Implementation ---
    # As defined in the proposal:
    # OverScore = 
    # 35% weight: xG_sum
    # 20% weight: shots_sum
    # 15% weight: chain_sum
    # 10% weight: buildup_sum
    # 10% weight: (1 - fragility_sum normalized)
    # 10% weight: (1 - balance normalized)
    
    # Normalization factors (approximate max values for scaling 0-1)
    MAX_XG_SUM = 5.0
    MAX_SHOTS_SUM = 40.0
    MAX_CHAIN_SUM = 6.0
    MAX_BUILDUP_SUM = 4.0
    MAX_FRAGILITY = 1.0 # Sum of two shares could be up to 2.0, but usually around 0.6-1.0
    MAX_BALANCE = 2.0
    
    # Normalize
    n_xg = min(features['xG_sum'] / MAX_XG_SUM, 1.0)
    n_shots = min(features['shots_sum'] / MAX_SHOTS_SUM, 1.0)
    n_chain = min(features['chain_sum'] / MAX_CHAIN_SUM, 1.0)
    n_buildup = min(features['buildup_sum'] / MAX_BUILDUP_SUM, 1.0)
    
    # Inverted metrics (High is bad for Over)
    # Fragility: High fragility -> lower score (boom/bust)
    # Should check proposal logic. "High fragility_sum -> more boom/bust".
    # Proposal says: "10% weight: (1 - fragility_sum normalized)"
    n_fragility = min(features['fragility_sum_top1xG'] / 1.5, 1.0) # 1.5 is a reasonable max
    score_fragility = 1.0 - n_fragility
    
    # Balance: Low balance (even match) -> Higher score (more scoring chances usually)
    # Proposal says: "10% weight: (1 - balance normalized)"
    n_balance = min(features['balance_xG_abs'] / MAX_BALANCE, 1.0)
    score_balance = 1.0 - n_balance
    
    # Weighted Sum
    # Weights: 35, 20, 15, 10, 10, 10
    raw_score = (
        (0.35 * n_xg) +
        (0.20 * n_shots) +
        (0.15 * n_chain) +
        (0.10 * n_buildup) +
        (0.10 * score_fragility) +
        (0.10 * score_balance)
    ) * 100
    
    print("\n--- 🧠 Model Classification ---")
    print(f"Over Score: {raw_score:.1f} / 100")
    
    print("\nInterpretation:")
    if raw_score > 70:
        print("✅ PLAY OVER 2.5 (High Confidence)")
    elif raw_score >= 55:
        print("🤔 LEAN OVER (Moderate)")
    elif raw_score >= 45:
        print("🤷 STAY AWAY / PASS")
    else:
        print("🛑 LEAN UNDER")

if __name__ == "__main__":
    test_classifier()
