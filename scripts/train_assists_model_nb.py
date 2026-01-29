
import pandas as pd
import numpy as np
import statsmodels.api as sm
from scipy.stats import nbinom

FILE = "data/nhl_processed/assists_features.parquet"

def train_assists():
    print("🍎 Training Assist Model (Phase 3 NB)...")
    df = pd.read_parquet(FILE)
    
    train = df[df['game_date'] < '2025-09-01'].copy()
    test = df[df['game_date'] >= '2025-09-01'].copy()
    
    print(f"Train: {len(train)} | Test: {len(test)}")
    
    cols = ['assists_per_60_L10', 'toi_L10', 'team_goals_L10', 'is_home']
    
    X_train = sm.add_constant(train[cols].astype(float))
    y_train = train['assists'].astype(float)
    X_test = sm.add_constant(test[cols].astype(float))
    y_test = test['assists'].astype(float)
    
    # Fit Negative Binomial
    model = sm.NegativeBinomial(y_train, X_train).fit()
    print("\n--- Model Summary ---")
    print(model.summary())
    
    # Predict Mu
    test['pred_mu'] = model.predict(X_test)
    alpha = model.params['alpha']
    n_param = 1.0 / alpha
    
    # Evaluation
    mae = np.mean(np.abs(test['pred_mu'] - test['assists']))
    print(f"\n📉 Out-of-Sample Metrics:")
    print(f"MAE: {mae:.4f}")
    
    # P(Assist >= 1)
    # p = n / (n + mu)
    ps = n_param / (n_param + test['pred_mu'])
    test['prob_ast_1plus'] = 1 - nbinom.pmf(0, n_param, ps)
    test['prob_ast_2plus'] = 1 - nbinom.cdf(1, n_param, ps)
    
    test['act_ast_1plus'] = (test['assists'] >= 1).astype(int)
    
    # Calibration
    test['bucket'] = pd.cut(test['prob_ast_1plus'], bins=[0, 0.1, 0.2, 0.35, 0.5, 1.0])
    calib = test.groupby('bucket')[['prob_ast_1plus', 'act_ast_1plus']].mean()
    calib['count'] = test.groupby('bucket')['prob_ast_1plus'].count()
    
    print("\n📊 Assist Calibration:")
    print(calib)
    
    # Save
    out_cols = ['player_name', 'game_date', 'pred_mu', 'prob_ast_1plus', 'prob_ast_2plus']
    outfile = "data/nhl_processed/assist_projections_phase3.csv"
    test[out_cols].to_csv(outfile, index=False)
    print(f"\n💾 Projections Saved: {outfile}")

if __name__ == "__main__":
    train_assists()
