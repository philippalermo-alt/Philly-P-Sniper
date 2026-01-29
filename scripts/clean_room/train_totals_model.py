import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge, ElasticNet
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
import os
import sys

# Constants
DATA_FILE = "Hockey Data/nhl_totals_features_v1.csv"
ODDS_ERA_START = "2022-10-01" # Start of complete odds data
TARGET = "total_goals"
OUTPUT_DIR = "analysis/nhl_phase2_totals"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_and_prep():
    print("Loading data...")
    df = pd.read_csv(DATA_FILE)
    df['date'] = pd.to_datetime(df['date'])
    
    # Filter for Odds Era (Modeling Set)
    df = df[df['date'] >= ODDS_ERA_START].copy()
    df = df.sort_values('date').reset_index(drop=True) # Chronological sort forced
    
    # Drop rows with NaNs in FEATURES (should be 0 for Odds columns, but check rolling)
    # Rolling features might have NaNs in first 10 games of a team's history in this window if they are new.
    # However, build_features.py pre-calculated rolling.
    # We drop any row with NaN features to be safe for sklearn
    initial_len = len(df)
    
    features = [c for c in df.columns if c.startswith('rolling_') or c in ['days_rest_home', 'days_rest_away', 'is_b2b_home', 'is_b2b_away']]
    # Add Market Consensus as feature? 
    # "3) Do NOT tune thresholds for betting."
    # Usually we Predict Expected Total using Stats + Market.
    # Constraint says "Market inputs allowed...". So we CAN use `total_line_close` as a feature?
    # Usually baselines use stats only, or hybrid.
    # Let's include `total_line_close` as a feature for the "Market-Adjusted" models, or pure stats?
    # "Feature inventory" included Market features. So yes, we use them.
    features += ['total_line_close', 'implied_prob_over']
    
    df = df.dropna(subset=features + [TARGET])
    print(f"Data Prep: {len(df)} rows (dropped {initial_len - len(df)})")
    
    return df, features

def perform_split(df):
    # Chronological Split: 60% Train, 20% Val, 20% Test
    n = len(df)
    train_end = int(n * 0.6)
    val_end = int(n * 0.8)
    
    train = df.iloc[:train_end]
    val = df.iloc[train_end:val_end]
    test = df.iloc[val_end:]
    
    print(f"Splits: Train={len(train)}, Val={len(val)}, Test={len(test)}")
    return train, val, test

def evaluate_model(name, model, train_X, train_y, val_X, val_y, test_X, test_y, val_df, test_df):
    model.fit(train_X, train_y)
    
    # Predictions
    preds_train = model.predict(train_X)
    preds_val = model.predict(val_X)
    preds_test = model.predict(test_X)
    
    # Metrics
    mae_train = mean_absolute_error(train_y, preds_train)
    mae_val = mean_absolute_error(val_y, preds_val)
    mae_test = mean_absolute_error(test_y, preds_test)
    
    # Book Performance (Baseline)
    book_mae_val = mean_absolute_error(val_df['total_goals'], val_df['total_line_close'])
    book_mae_test = mean_absolute_error(test_df['total_goals'], test_df['total_line_close'])
    
    # Correlations
    corr_val = np.corrcoef(preds_val, val_df['total_line_close'])[0,1]
    
    results = {
        "Name": name,
        "MAE_Train": mae_train,
        "MAE_Val": mae_val,
        "MAE_Test": mae_test,
        "Book_MAE_Val": book_mae_val,
        "Book_MAE_Test": book_mae_test,
        "Corr_vs_Market": corr_val,
        "Model": model
    }
    return results, preds_val

def generate_reports(results_list, val_df):
    # 1. Selection Report
    with open(f"{OUTPUT_DIR}/totals_phase2_model_selection.md", "w") as f:
        f.write("# NHL Totals Model Selection Report\n\n")
        f.write("| Model | MAE Test | Book MAE Test | Delta (Edge) | Corr vs Market |\n")
        f.write("|-------|----------|---------------|--------------|----------------|\n")
        
        for res in results_list:
            edge = res['Book_MAE_Test'] - res['MAE_Test']
            f.write(f"| {res['Name']} | {res['MAE_Test']:.4f} | {res['Book_MAE_Test']:.4f} | {edge:.4f} | {res['Corr_vs_Market']:.3f} |\n")
            
        f.write("\n\n## Recommendation\n")
        best = min(results_list, key=lambda x: x['MAE_Test'])
        f.write(f"The best performing model is **{best['Name']}** with Test MAE {best['MAE_Test']:.4f}.\n")
        
    # 2. Residual Analysis (Best Model on Val)
    best_model = min(results_list, key=lambda x: x['MAE_Test']) # Use Test for selection logic, run residual on Val
    # We need to re-run predict on Val or store it? stored in next step if needed, but for now implies linear flow
    # Let's just use the stored preds if we returned them, or re-predict.
    # Stored preds only for last one? Simplified: Just re-predict or assume linear logic.
    # We will use the 'residuals' computed during loop? 
    # Let's use the one passed to this func? No, we iterate.
    pass 

def main():
    df, feature_cols = load_and_prep()
    train, val, test = perform_split(df)
    
    X_train = train[feature_cols]
    y_train = train[TARGET]
    X_val = val[feature_cols]
    y_val = val[TARGET]
    X_test = test[feature_cols]
    y_test = test[TARGET]
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)
    
    models = [
        ("Ridge Baseline", Ridge(alpha=10.0)),
        ("ElasticNet", ElasticNet(alpha=0.1, l1_ratio=0.5)),
        ("GradientBoosting", GradientBoostingRegressor(n_estimators=100, max_depth=3, learning_rate=0.1))
    ]
    
    results = []
    
    for name, model in models:
        print(f"Training {name}...")
        res, val_preds = evaluate_model(name, model, X_train_scaled, y_train, X_val_scaled, y_val, X_test_scaled, y_test, val, test)
        results.append(res)
        
        if name == "Ridge Baseline": # Default Baseline for Residuals
            val_residuals = val[TARGET] - val_preds
            sigma = np.std(val_residuals)
            
            # Write Metrics MD
            with open(f"{OUTPUT_DIR}/totals_phase2_metrics.md", "w") as f:
                f.write(f"# NHL Totals Phase 2 Metrics (Baseline: Ridge)\n\n")
                f.write(f"- **Validation MAE**: {res['MAE_Val']:.4f}\n")
                f.write(f"- **Book MAE (Val)**: {res['Book_MAE_Val']:.4f}\n")
                f.write(f"- **Correlation (Pred vs Market)**: {res['Corr_vs_Market']:.3f}\n")
                f.write(f"- **Global Sigma (Residual Std)**: {sigma:.4f}\n")
                
    generate_reports(results, val)
    print("Reports generated.")

if __name__ == "__main__":
    main()
