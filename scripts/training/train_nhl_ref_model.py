import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import os

INPUT_FILE = "nhl_ref_game_logs_v2.csv"

def train_coefficients():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ {INPUT_FILE} not found. Wait for expander.")
        return

    df = pd.read_csv(INPUT_FILE)
    if 'home_score' not in df.columns:
        print("❌ 'home_score' missing. Old CSV format?")
        return
        
    print(f"📊 Training on {len(df)} games...")
    
    # Feature Engineering
    df['total_goals'] = df['home_score'] + df['away_score']
    df['margin'] = df['home_score'] - df['away_score']
    
    # 1. Regression: Total Goals ~ Total Penalties
    # Hypothesis: More penalties = More PP = More Goals
    X_total = df[['total_penalties']]
    y_total = df['total_goals']
    
    reg_total = LinearRegression()
    reg_total.fit(X_total, y_total)
    
    coef_total = reg_total.coef_[0]
    intercept_total = reg_total.intercept_
    r2_total = reg_total.score(X_total, y_total)
    
    print("\n📈 [Model 1] Total Goals ~ Penalties")
    print(f"   Coefficient: {coef_total:.4f} (Goals per Penalty)")
    print(f"   Intercept:   {intercept_total:.2f}")
    print(f"   R²:          {r2_total:.4f}")
    
    # 2. Regression: Margin ~ Home PP Diff
    # Hypothesis: Home PP Adtg = Home Margin Adtg
    X_margin = df[['home_pp_diff']]
    y_margin = df['margin']
    
    reg_margin = LinearRegression()
    reg_margin.fit(X_margin, y_margin)
    
    coef_margin = reg_margin.coef_[0]
    
    print("\n📈 [Model 2] Margin ~ Home PP Diff")
    print(f"   Coefficient: {coef_margin:.4f} (Margin pts per PP Diff)")
    
    print("\n✅ RECOMMENDATION:")
    print(f"   Update TOTAL_ADJ_FACTOR to {coef_total:.3f}")
    print(f"   Update MARGIN_ADJ_FACTOR to {coef_margin:.3f}")

if __name__ == "__main__":
    train_coefficients()
