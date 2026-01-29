
import pandas as pd
import numpy as np
import statsmodels.api as sm
from scipy.stats import nbinom

FILE = "data/nhl_processed/sog_features.parquet"

def train_model():
    print("🧠 Training SOG Phase 1 Model (Negative Binomial)...")
    df = pd.read_parquet(FILE)
    
    # Define Split
    train = df[df['game_date'] < '2025-09-01'].copy()
    test = df[df['game_date'] >= '2025-09-01'].copy()
    
    # Cast to float
    cols = ['sog_per_60_L10', 'toi_L10', 'opp_def_factor', 'is_home']
    X_train = sm.add_constant(train[cols].astype(float))
    y_train = train['shots'].astype(float)
    X_test = sm.add_constant(test[cols].astype(float))
    y_test = test['shots'].astype(float)
    
    # Fit Negative Binomial (NB2)
    # This automatically estimates alpha (dispersion)
    model = sm.NegativeBinomial(y_train, X_train).fit()
    print("\n--- Model Summary ---")
    print(model.summary())
    
    # Predictions (Mean mu)
    test['pred_mu'] = model.predict(X_test)
    
    # Retrieve estimated alpha
    alpha = model.params['alpha']
    print(f"\nEstimated Dispersion (alpha): {alpha:.4f}")
    
    # Evaluation
    mae = np.mean(np.abs(test['pred_mu'] - test['shots']))
    rmse = np.sqrt(np.mean((test['pred_mu'] - test['shots'])**2))
    print(f"\n📉 Out-of-Sample Metrics:")
    print(f"MAE: {mae:.4f}")
    print(f"RMSE: {rmse:.4f}")
    print(f"Bias: {(test['pred_mu'] - test['shots']).mean():.4f}")
    
    # --- Bucketed Calibration (The "Real" Tail Test) ---
    print("\n📊 Calibration by Predicted Bucket (P(SOG >= 5)):")
    # Bin predictions: 0-1, 1-2, 2-3, 3-4, 4-5, 5+
    bins = [0, 2, 3, 4, 5, 10]
    labels = ['<2', '2-3', '3-4', '4-5', '5+']
    test['bucket'] = pd.cut(test['pred_mu'], bins=bins, labels=labels)
    
    # Conversion Params for Scipy NB
    # Statsmodels NB2: Var = mu + alpha * mu^2
    # Scipy nbinom: n, p
    # n = 1/alpha
    # p = n / (n + mu)
    n_param = 1.0 / alpha
    
    results = []
    threshold = 5 # P(SOG >= 5)
    
    for bucket in labels:
        subset = test[test['bucket'] == bucket]
        if len(subset) == 0: continue
            
        mean_pred = subset['pred_mu'].mean()
        mean_act = subset['shots'].mean()
        
        # Actual Prob >= 5
        act_prob = (subset['shots'] >= threshold).mean()
        
        # Predicted Prob >= 5 (using Mean Mu of bucket + global Alpha)
        # P(X >= k) = 1 - CDF(k-1). P(X >= 5) = 1 - CDF(4)
        p_param = n_param / (n_param + mean_pred)
        pred_prob = 1 - nbinom.cdf(threshold-1, n_param, p_param)
        
        results.append({
            'Bucket': bucket,
            'Count': len(subset),
            'Mean_Pred': f"{mean_pred:.2f}",
            'Mean_Act': f"{mean_act:.2f}",
            'Act_P(>=5)': f"{act_prob:.3f}",
            'Pred_P(>=5)': f"{pred_prob:.3f}"
        })
        
    res_df = pd.DataFrame(results)
    print(res_df.to_string(index=False))
    
    # Save Projections with NB Probabilities
    lines = [1.5, 2.5, 3.5, 4.5]
    for line in lines:
        cutoff = int(line)
        # Row-wise probability calculation
        # Vectorized approach for efficiency
        mus = test['pred_mu']
        ps = n_param / (n_param + mus)
        test[f'prob_over_{line}'] = 1 - nbinom.cdf(cutoff, n_param, ps)

    out_cols = ['player_name', 'team', 'opponent', 'game_date', 'pred_mu'] + [f'prob_over_{l}' for l in lines]
    outfile = "data/nhl_processed/sog_projections_phase1_nb.csv"
    test[out_cols].to_csv(outfile, index=False)
    print(f"\n💾 NB Projections Saved: {outfile}")

if __name__ == "__main__":
    train_model()
