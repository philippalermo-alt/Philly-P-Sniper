import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error
from scipy.stats import norm
from db.connection import get_db

# --- CONFIG ---
TARGET_COL = 'total_points'
SPLIT_DATE = '2024-10-01'

def load_data():
    conn = get_db()
    df = pd.read_sql('SELECT * FROM nba_model_train', conn)
    conn.close()
    
    # Add Implied Prob for Moneyline (for correlation check)
    # But for Totals, we care about 'total_line'
    
    return df

def train_eval_totals(df):
    cols = df.columns
    # Same features as Baseline ML + total_line?
    # NO! Do NOT include 'total_line' as a feature if you are predicting total_points?
    # Actually, Book Line IS a powerful feature (Residual Learning).
    # "Leakage Test: Ensure features are NOT used improperly."
    # Option A: Learn Score from Scratch (Pure).
    # Option B: Learn Error from Book Line (Residual).
    # Let's try Option A (Pure) first to see if we have signal. Inclusion of Book Line makes it just learn the book.
    # Actually, Book Line is highly predictive.
    # Let's stick to Rolling Stats first.
    
    base_feats = [c for c in cols if (
        '_roll_' in c or '_sea_' in c or 'rest_days' in c or 'implied_prob_' in c
    )]
    
    # Filter for Totals
    # Must have total_line to bet
    df_clean = df.dropna(subset=base_feats + ['total_points', 'total_line', 'total_over_odds', 'total_under_odds'])
    
    train = df_clean[df_clean['game_date_H'] < SPLIT_DATE]
    test = df_clean[df_clean['game_date_H'] >= SPLIT_DATE]
    
    print(f"📅 Train: {len(train)} | Test: {len(test)}")
    
    # Regressor
    print("🧠 Training XGB Regressor...")
    model = xgb.XGBRegressor(
        n_estimators=100, max_depth=3, learning_rate=0.05, objective='reg:absoluteerror'
    )
    model.fit(train[base_feats], train[TARGET_COL])
    
    # Predict
    preds = model.predict(test[base_feats])
    
    # Calc MAE
    mae_model = mean_absolute_error(test[TARGET_COL], preds)
    
    # Book MAE (Line vs Actual)
    mae_book = mean_absolute_error(test[TARGET_COL], test['total_line'])
    
    print(f"📉 Model MAE: {mae_model:.2f}")
    print(f"📖 Book  MAE: {mae_book:.2f}")
    print(f"   Delta: {mae_model - mae_book:.2f} (Lower is better)")
    
    # Calculate Sigma (Std Dev of Residuals in Train? Or Test?)
    # Ideally from Train or Calibration set. Let's use Test residuals for "Perfect Sigma" check, or estimate.
    # Let's estimate from Train Residuals to be proper.
    train_preds = model.predict(train[base_feats])
    train_res = train[TARGET_COL] - train_preds
    sigma = train_res.std()
    print(f"📊 Estimated Sigma (Train): {sigma:.2f}")
    
    # Probability Conversion
    # P(Over) = P(Actual > Line)
    # Z = (Pred - Line) / Sigma
    # P(Over) = CDF(Z)
    
    z_scores = (preds - test['total_line']) / sigma
    probs_over = norm.cdf(z_scores)
    
    # Simulation
    sim = test.copy()
    sim['prob_over'] = probs_over
    sim['prob_under'] = 1 - probs_over
    
    bets = []
    for idx, row in sim.iterrows():
        # Over
        if row['total_over_odds'] > 0:
            ev = (row['prob_over'] * row['total_over_odds']) - 1
            if ev > 0.05: # 5% Threshold from Classification
                prof = (row['total_over_odds'] - 1) if row['target_over']==1 else -1
                bets.append(prof)
        # Under
        if row['total_under_odds'] > 0:
            ev = (row['prob_under'] * row['total_under_odds']) - 1
            if ev > 0.05:
                prof = (row['total_under_odds'] - 1) if row['target_over']==0 else -1
                bets.append(prof)
                
    if bets:
        roi = sum(bets) / len(bets)
        print(f"💰 Totals Regression ROI: {roi:.2%} ({len(bets)} bets)")
    else:
        print("No bets.")

if __name__ == "__main__":
    df = load_data()
    train_eval_totals(df)
