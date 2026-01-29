import pandas as pd
import numpy as np
import joblib
from sklearn.calibration import calibration_curve
from sklearn.linear_model import LinearRegression
from sklearn.metrics import log_loss, brier_score_loss
import sys
import os

# Paths
DATA_PATH = "Hockey Data/training_set_v2.csv"
MODEL_PATH = "models/nhl_v2.pkl"

def analyze_calibration():
    print("🔬 Starting NHL V2 Calibration Analysis...")
    
    # 1. Load Data & Model
    try:
        df = pd.read_csv(DATA_PATH)
        model = joblib.load(MODEL_PATH)
    except Exception as e:
        print(f"❌ Error loading assets: {e}")
        return

    # Re-create Target & Drop NAs identical to training
    df['home_win'] = (df['goalsFor_home'] > df['goalsFor_away']).astype(int)
    
    # Same Features as Training (Must match exactly)
    features = [
        'diff_xGoals', 'diff_corsi', 
        'diff_goalie_GSAx_L5', 'diff_goalie_GSAx_L10', 'diff_goalie_GSAx_Season',
        'home_goalie_GP', 'away_goalie_GP',
        'xGoalsPercentage_home', 'corsiPercentage_home', 'fenwickPercentage_home',
        'xGoalsPercentage_away', 'corsiPercentage_away', 'fenwickPercentage_away'
    ]
    
    # Re-engineer Diffs locally to ensure consistency
    df['diff_xGoals'] = df['xGoalsPercentage_home'] - df['xGoalsPercentage_away']
    df['diff_corsi'] = df['corsiPercentage_home'] - df['corsiPercentage_away']
    
    df_clean = df.dropna(subset=features).copy()
    
    # Split Test Set (Same logic: Last 20%)
    df_clean = df_clean.sort_values('gameDate_home')
    split_idx = int(len(df_clean) * 0.8)
    
    X_test = df_clean[features].iloc[split_idx:]
    y_test = df_clean['home_win'].iloc[split_idx:]
    
    print(f"   Analyzing Test Set: {len(X_test)} games")
    
    # 2. Get Probabilities
    probs = model.predict_proba(X_test)[:, 1]
    
    # 3. Calibration Curve
    prob_true, prob_pred = calibration_curve(y_test, probs, n_bins=10, strategy='uniform')
    
    print("\n📉 Reliability Table (10 Bins):")
    print(f"{'Mean Pred':<10} | {'Fraction Pos':<12} | {'Count':<8} | {'Error':<8}")
    print("-" * 45)
    
    # Recalculate counts per bin manually for detail
    bins = np.linspace(0, 1, 11)
    binids = np.digitize(probs, bins) - 1
    
    max_deviation = 0
    weighted_dev = 0
    total_samples = len(y_test)
    
    for i in range(10):
        mask = binids == i
        if np.sum(mask) > 0:
            count = np.sum(mask)
            mean_p = np.mean(probs[mask])
            fraction = np.mean(y_test[mask])
            error = fraction - mean_p
            
            # Track deviations
            max_deviation = max(max_deviation, abs(error))
            weighted_dev += abs(error) * count
            
            print(f"{mean_p:.4f}     | {fraction:.4f}       | {count:<8} | {error:+.4f}")
            
    avg_recalibration_error = weighted_dev / total_samples
    
    # 4. Slope / Regression
    # Regress Actual Outcome (0/1) on Probability? Or binned points?
    # Standard practice: Calibration Slope (Beta) from Prob_Pred to Prob_True
    # Linear Reg on the binned points weighted by count is a good proxy.
    
    lr = LinearRegression()
    # Handle empty bins if any
    mask = ~np.isnan(prob_true)
    lr.fit(prob_pred[mask].reshape(-1, 1), prob_true[mask])
    slope = lr.coef_[0]
    intercept = lr.intercept_
    
    print("\n📐 Calibration Metrics:")
    print(f"   Slope (Target ~1.0):   {slope:.4f}")
    if abs(1.0 - slope) < 0.1:
        print("   ✅ Slope is Good (Close to 1.0)")
    else:
        print("   ⚠️  Slope Deviation > 0.1")

    print(f"   Max Deviation:         {max_deviation:.4f}")
    if max_deviation < 0.1:
         print("   ✅ Max Dev is Safe (< 0.1)")
    else:
         print("   ⚠️  Max Dev High (> 0.1) - Check bin sizes")

    print(f"   ECE (Est. Calib Error): {avg_recalibration_error:.4f}")

    print(f"   Intercept:             {intercept:.4f}")
    
    # 5. Bet Sizing Safety Check
    print("\n💰 Bet Sizing Safety Check:")
    if 0.9 < slope < 1.1 and max_deviation < 0.15:
        print("   ✅ PASS: Probabilities are safe for Kelly/Fractional betting.")
    elif slope < 0.8:
        print("   ❌ FAIL: Model is Overconfident (Slope < 0.8). Shrink bets.")
    elif slope > 1.2:
        print("   ⚠️  FAIL: Model is Underconfident. Opportunity lost.")
    else:
        print("   ⚠️  CAUTION: Marginal metrics. Use conservative sizing.")

if __name__ == "__main__":
    analyze_calibration()
