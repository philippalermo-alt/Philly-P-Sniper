import pandas as pd
import lightgbm as lgb
import joblib
import numpy as np
from sklearn.metrics import mean_absolute_error, r2_score
from scipy.stats import poisson, nbinom

DATA_FILE = "mlb_rolling_features_with_targets.csv"
MODEL_FILE = "models/mlb_k_prop_model.pkl"

def train_final_model():
    print("📉 Loading Training Data...")
    df = pd.read_csv(DATA_FILE)
    df['game_date'] = pd.to_datetime(df['game_date'])
    
    # Feature Engineering: Rolling Leash (re-calc to be safe)
    df = df.sort_values(['pitcher', 'game_date'])
    df['rolling_leash'] = df.groupby('pitcher')['pitch_count'].rolling(window=5, min_periods=1).mean().shift(1).reset_index(0, drop=True)
    df = df.dropna(subset=['rolling_leash', 'opp_x_whiff'])
    
    features = [
        'stuff_quality',       # Pitcher xWhiff
        'whiff_oe',            # Pitcher Overperformance
        'rolling_leash',       # Pitch Count Expectation
        'roll_actual_whiff',   # Pitcher Raw Whiff
        'opp_x_whiff',         # Opponent Vulnerability (xWhiff against them)
        'opp_actual_whiff'     # Opponent Actual Whiff history
    ]
    target = 'actual_K'
    
    split_date = '2025-01-01'
    X_train = df.loc[df['game_date'] < split_date, features]
    y_train = df.loc[df['game_date'] < split_date, target]
    X_test = df.loc[df['game_date'] >= split_date, features]
    y_test = df.loc[df['game_date'] >= split_date, target]
    
    print(f"📊 Training on {len(X_train):,} | Testing on {len(X_test):,}")
    
    model = lgb.LGBMRegressor(
        objective='poisson',
        n_estimators=600,
        learning_rate=0.02,
        num_leaves=31,
        random_state=42
    )
    
    model.fit(X_train, y_train)
    
    # --- EVALUATION ---
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)
    
    print("\n🎯 Final Model Stats:")
    print(f"   MAE: {mae:.2f} Ks")
    print(f"   R2:  {r2:.3f}")
    
    # --- ROBUST DISPERSION (Method of Moments) ---
    print("\n📉 Estimating Dispersion (Method of Moments, Mu >= 2.0)...")
    
    test_df = X_test.copy()
    test_df['actual'] = y_test
    test_df['pred'] = preds
    
    def get_moments_alpha(sub_df):
        valid = sub_df[sub_df['pred'] >= 2.0].copy()
        if len(valid) < 10: return 0.05
        
        y = valid['actual']
        mu = valid['pred']
        resid = y - mu
        
        var_resid = np.var(resid)
        mean_mu = np.mean(mu)
        mean_mu_sq = np.mean(mu**2)
        
        alpha = (var_resid - mean_mu) / mean_mu_sq
        # Safety Bump: Add 0.10 to fatten tails (Combat Overconfidence)
        return max(0.15, alpha + 0.10) 

    # 3 Regimes
    mask_low = test_df['rolling_leash'] < 45
    mask_mid = test_df['rolling_leash'].between(45, 75)
    mask_high = test_df['rolling_leash'] > 75
    
    alpha_low  = get_moments_alpha(test_df[mask_low])
    alpha_mid  = get_moments_alpha(test_df[mask_mid])
    alpha_high = get_moments_alpha(test_df[mask_high])
    
    print(f"   Alpha (Leash < 45):  {alpha_low:.4f} (Short)")
    print(f"   Alpha (45-75):       {alpha_mid:.4f} (Volatile)")
    print(f"   Alpha (Leash > 75):  {alpha_high:.4f} (Starter)")
    
    # --- PROBABILITY EXAMPLE (SHARP LOGIC) ---
    print("\n🎲 Prop Decision Example (Line = 4.5, Odds = -110):")
    
    # Logic Parameters
    EDGE_REQ_OVER = 0.07  # High barrier for Overs
    EDGE_REQ_UNDER = 0.04 # Lower barrier for Unders
    OVER_LEASH_MIN = 85   # Only deep starters for Overs
    OVER_MU_ADJ = -0.25   # Penalty for Model Optimism
    IMPLIED_PROB = 0.5238
    
    sample = pd.DataFrame({
        'pred': preds[:10],
        'actual': y_test[:10].values,
        'leash': X_test['rolling_leash'][:10].values
    })
    
    for i, row in sample.iterrows():
        mu = row['pred']
        leash = row['leash']
        actual = row['actual']
        line = 4.5
        
        # Select Dispersion
        if leash < 45: alpha = alpha_low
        elif leash <= 75: alpha = alpha_mid
        else: alpha = alpha_high
        
        # NB Params (Base)
        n_p = 1.0 / alpha
        
        # 1. Standard Prob (For Unders/Ref)
        p_std = n_p / (n_p + mu)
        prob_over_std = nbinom.sf(int(line), n_p, p_std)
        
        # 2. Adjusted Prob (For Overs)
        mu_adj = max(0.1, mu + OVER_MU_ADJ)
        p_adj = n_p / (n_p + mu_adj)
        prob_over_adj = nbinom.sf(int(line), n_p, p_adj)
        
        decision = "NO PLAY"
        note = ""
        
        # CHECK OVER
        # Must meet strict adjusted criteria
        edge_over = prob_over_adj - IMPLIED_PROB
        if edge_over > EDGE_REQ_OVER:
            if leash >= OVER_LEASH_MIN:
                decision = "BET OVER"
            else:
                note = "Skip (Leash < 85)"
        
        # CHECK UNDER
        # Standard criteria
        edge_under = (1 - prob_over_std) - IMPLIED_PROB
        if decision == "NO PLAY" and edge_under > EDGE_REQ_UNDER:
            decision = "BET UNDER"
            
        result = "N/A"
        if decision == "BET OVER": result = "WIN" if actual > line else "LOSS"
        elif decision == "BET UNDER": result = "WIN" if actual < line else "LOSS"
            
        print(f"   Pred: {mu:.2f} | Leash: {leash:.0f} | P(>4.5): {prob_over_std:.1%} | Action: {decision:10} | Actual: {actual} ({result}) {note}")

    joblib.dump(model, MODEL_FILE)
    print(f"\n💾 Saved to {MODEL_FILE}")

if __name__ == "__main__":
    train_final_model()
