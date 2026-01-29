import pandas as pd
import numpy as np
import joblib
import sys

# Paths
DATA_PATH = "Hockey Data/training_set_v2.csv"
MODEL_PATH = "models/nhl_v2.pkl"

def simulate_roi():
    print("💰 Starting NHL V2 Bucketed ROI Simulation...")
    print("   (Note: Using implied Market Lines since historical odds are unavailable in training set)")
    
    # 1. Load Data/Model
    try:
        df = pd.read_csv(DATA_PATH)
        model = joblib.load(MODEL_PATH)
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # Setup (Identical to Training)
    df['home_win'] = (df['goalsFor_home'] > df['goalsFor_away']).astype(int)
    features = [
        'diff_xGoals', 'diff_corsi', 
        'diff_goalie_GSAx_L5', 'diff_goalie_GSAx_L10', 'diff_goalie_GSAx_Season',
        'home_goalie_GP', 'away_goalie_GP',
        'xGoalsPercentage_home', 'corsiPercentage_home', 'fenwickPercentage_home',
        'xGoalsPercentage_away', 'corsiPercentage_away', 'fenwickPercentage_away'
    ]
    df['diff_xGoals'] = df['xGoalsPercentage_home'] - df['xGoalsPercentage_away']
    df['diff_corsi'] = df['corsiPercentage_home'] - df['corsiPercentage_away']
    
    df_clean = df.dropna(subset=features).sort_values('gameDate_home').copy()
    
    # Test Set Only
    split_idx = int(len(df_clean) * 0.8)
    test_df = df_clean.iloc[split_idx:].copy()
    
    # 2. Predict
    probs = model.predict_proba(test_df[features])[:, 1]
    test_df['model_prob'] = probs
    
    print(f"   Simulating {len(test_df)} Games (Test Set)")
    
    # 3. Define Buckets & Simulate
    # Assumption: User wants to know if "Coinflip" bets (prob ~50%) or "Favorites" (prob > 60%) are profitable.
    # Without Odds, we test "Win Rate" vs "Implied Breakeven".
    
    # Bucket 1: Coinflips (Prob 0.48 to 0.53 - aka 1.90 to 2.10 implied)
    # Actually User said: Coinflip (1.90-2.15) => Implied Prob 0.465 - 0.526
    # Let's say Odds ~ 2.00 (+100). Breakeven = 50%.
    
    # We simulate betting on Home when Prob is in range.
    
    buckets = [
        ("Favorites (<1.60)", 0.625, 1.00, 1.55), # Implied Odds 1.55
        ("Coinflip (1.90-2.15)", 0.465, 0.526, 2.00), # Implied Odds 2.00 (Even money)
        ("Underdogs (>2.20)", 0.0, 0.45, 2.40) # Implied Odds 2.40
    ]
    
    for name, p_min, p_max, sim_odds in buckets:
        print(f"\n📊 {name} Simulation:")
        
        # Identify Qualifying Bets (Bet HOME if prob in range)
        # Note: For underdogs/coinflips, usually we bet if Model > Market.
        # Here we just check reliability of the bucket.
        
        mask = (test_df['model_prob'] >= p_min) & (test_df['model_prob'] <= p_max)
        subset = test_df[mask]
        
        if len(subset) == 0:
            print("   No games in this bucket.")
            continue
            
        wins = subset['home_win'].sum()
        total = len(subset)
        win_rate = wins / total
        
        # ROI Calculation (Flat Bet)
        # Profit = (Wins * (Odds - 1)) - (Losses * 1)
        profit_units = (wins * (sim_odds - 1)) - (total - wins)
        roi = profit_units / total
        
        print(f"   Games: {total}")
        print(f"   Win Rate: {win_rate:.4f}")
        print(f"   Simulated Odds: {sim_odds}")
        print(f"   Profit (Units): {profit_units:.2f}")
        print(f"   ROI: {roi:.2%}")
        
        if roi > 0.05:
            print("   ✅ STRONG EDGE")
        elif roi > 0:
            print("   ✅ POSITIVE EDGE")
        else:
            print("   ❌ NEGATIVE ROI (Market likely efficient here)")

if __name__ == "__main__":
    simulate_roi()
