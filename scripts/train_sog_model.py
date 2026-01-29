
import pandas as pd
import numpy as np
import statsmodels.api as sm
from scipy.stats import poisson

FILE = "data/nhl_processed/sog_features.parquet"

def train_model():
    print("🧠 Training SOG Phase 1 Model...")
    df = pd.read_parquet(FILE)
    
    # Define Split
    train = df[df['game_date'] < '2025-09-01'].copy()
    test = df[df['game_date'] >= '2025-09-01'].copy()
    
    print(f"Train: {len(train)} | Test: {len(test)}")
    
    # Formula features
    # SOG ~ const + SOG_Rate_L10 + Opp_Def + Home
    # Offset: log(TOI_L10) -> We assume usage is sticky.
    # Note: If we use log(TOI_L10) as offset, we predict Rate.
    # If we use TOI_L10 as feature, we predict Count directly.
    # Let's use Count regression with TOI as feature (easier interpretation for Phase 1).
    
    cols = ['sog_per_60_L10', 'toi_L10', 'opp_def_factor', 'is_home']
    
    X_train = sm.add_constant(train[cols].astype(float))
    y_train = train['shots'].astype(float)
    
    X_test = sm.add_constant(test[cols].astype(float))
    y_test = test['shots'].astype(float) # Testing y can be whatever, but consistent
    
    # Fit Poisson
    model = sm.GLM(y_train, X_train, family=sm.families.Poisson()).fit()
    print("\n--- Model Summary ---")
    print(model.summary())
    
    # Predict
    test['pred_mu'] = model.predict(X_test)
    
    # Evaluation
    mae = np.mean(np.abs(test['pred_mu'] - test['shots']))
    rmse = np.sqrt(np.mean((test['pred_mu'] - test['shots'])**2))
    
    print(f"\n📉 Out-of-Sample Metrics:")
    print(f"MAE: {mae:.4f}")
    print(f"RMSE: {rmse:.4f}")
    
    # Calibration Check (Mean Pred vs Mean Actual)
    mean_pred = test['pred_mu'].mean()
    mean_act = test['shots'].mean()
    bias = mean_pred - mean_act
    print(f"Bias: {bias:.4f} (Pos=Overpredict)")
    
    # Generate Probabilities
    # P(SOG > Line) = 1 - CDF(Line)
    lines = [1.5, 2.5, 3.5, 4.5]
    for line in lines:
        prob = 1 - poisson.cdf(line, test['pred_mu']) # P(X > k) = 1 - P(X <= k)
        # Note: Line 2.5 => Over 2.5 means 3,4,5...
        # cdf(2.5) isn't right for discrete. cdf(floor(2.5)) = cdf(2).
        # P(X > 2.5) = P(X >= 3) = 1 - P(X <= 2).
        cutoff = int(line) 
        prob = 1 - poisson.cdf(cutoff, test['pred_mu'])
        test[f'prob_over_{line}'] = prob
        
    # Save Projections
    out_cols = ['player_name', 'team', 'opponent', 'game_date', 'pred_mu'] + [f'prob_over_{l}' for l in lines]
    outfile = "data/nhl_processed/sog_projections_phase1.csv"
    test[out_cols].to_csv(outfile, index=False)
    print(f"\n💾 Validation Projections Saved: {outfile}")
    
    # Tail Check
    high_sog = test[test['shots']>=6]
    pred_high = test.loc[test['shots']>=6, 'pred_mu'].mean()
    print(f"Tail Check (Act >= 6): Mean Actual={high_sog['shots'].mean():.2f}, Mean Pred={pred_high:.2f}")

if __name__ == "__main__":
    train_model()
