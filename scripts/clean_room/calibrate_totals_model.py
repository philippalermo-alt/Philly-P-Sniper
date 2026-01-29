import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats
from sklearn.linear_model import ElasticNet
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error
import os

# Configuration
DATA_FILE = "Hockey Data/nhl_totals_features_v1.csv"
ODDS_ERA_START = "2022-10-01"
TARGET = "total_goals"
OUTPUT_DIR = "analysis/nhl_phase2_totals"

def load_and_prep():
    print("Loading data...")
    df = pd.read_csv(DATA_FILE)
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['date'] >= ODDS_ERA_START].copy()
    df = df.sort_values('date').reset_index(drop=True)
    
    features = [c for c in df.columns if c.startswith('rolling_') or c in ['days_rest_home', 'days_rest_away', 'is_b2b_home', 'is_b2b_away']]
    features += ['total_line_close', 'implied_prob_over']
    
    df = df.dropna(subset=features + [TARGET])
    return df, features

def perform_split(df, features):
    n = len(df)
    train_end = int(n * 0.6)
    val_end = int(n * 0.8)
    
    train = df.iloc[:train_end]
    val = df.iloc[train_end:val_end].copy()
    test = df.iloc[val_end:] # Not used for calibration
    
    return train, val, features

def calibrate_model():
    df, features = load_and_prep()
    train, val, _ = perform_split(df, features)
    
    X_train = train[features]
    y_train = train[TARGET]
    X_val = val[features]
    
    # Scale
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    # Train ElasticNet (Locked Params)
    print("Training ElasticNet (Locked)...")
    model = ElasticNet(alpha=0.1, l1_ratio=0.5)
    model.fit(X_train_scaled, y_train)
    
    # Predict on Val
    val['expected_total_raw'] = model.predict(X_val_scaled)
    # Calculate Bias
    raw_residual = val[TARGET] - val['expected_total_raw']
    bias = raw_residual.mean()
    print(f"Initial Bias: {bias:.4f}")
    
    # Apply Correction (Locked)
    val['expected_total'] = val['expected_total_raw'] + bias
    val['residual'] = val[TARGET] - val['expected_total']
    
    # 1. Global Sigma (Corrected)
    sigma_global = val['residual'].std()
    mu_residual = val['residual'].mean()
    
    print(f"Global Sigma (Corrected): {sigma_global:.4f}")
    print(f"Mean Residual (Corrected): {mu_residual:.4f}")
    
    # 2. Bucketed Sigma (Check for Heteroscedasticity)
    # Bucket by Closing Line (e.g. <5.5, 6.0, 6.5, >7.0)
    def bucket_line(line):
        if line <= 5.5: return "<= 5.5"
        elif line == 6.0: return "6.0"
        elif line == 6.5: return "6.5"
        elif line >= 7.0: return ">= 7.0"
        return "Other"
        
    val['line_bucket'] = val['total_line_close'].apply(bucket_line)
    bucket_stats = val.groupby('line_bucket')['residual'].agg(['count', 'std', 'mean'])
    
    # 3. Derive Probabilities using Global Sigma (Safest)
    val['prob_over'] = 1 - stats.norm.cdf(val['total_line_close'], loc=val['expected_total'], scale=sigma_global)
    val['prob_under'] = stats.norm.cdf(val['total_line_close'], loc=val['expected_total'], scale=sigma_global)
    
    # Write Calibration Report
    report = f"""# NHL Totals Phase 2 Calibration Report

## 1. Global Parameters (Validation Set)
- **Model**: ElasticNet (alpha=0.1, l1=0.5)
- **Bias Correction Applied**: {bias:.4f}
- **Global Sigma (Std Dev)**: {sigma_global:.4f}
- **Final Bias**: {mu_residual:.4f} (Expected ~0)

## 2. Bucket Analysis (Sigma Stability)
{bucket_stats.to_string()}

## 3. Histogram of Residuals
(Residuals distribution assumed roughly Normal around 0 with sigma={sigma_global:.2f})

## 4. Probability Check (Sample)
First 5 Validation Rows:
{val[['date', 'total_line_close', 'expected_total', 'prob_over', 'prob_under', 'total_goals']].head().to_string()}

## 5. Decision
Recommended Sigma: **{sigma_global:.4f}** (Global).
Bucketed Sigmas show {"STABILITY" if bucket_stats['std'].std() < 0.2 else "VARIANCE"}.
"""
    
    with open(f"{OUTPUT_DIR}/totals_phase2_calibration.md", "w") as f:
        f.write(report)
        
    print(f"Calibration Report written to {OUTPUT_DIR}/totals_phase2_calibration.md")

if __name__ == "__main__":
    calibrate_model()
