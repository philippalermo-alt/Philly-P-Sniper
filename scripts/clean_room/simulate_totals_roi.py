import pandas as pd
import numpy as np
import scipy.stats as stats
from sklearn.linear_model import ElasticNet
from sklearn.preprocessing import StandardScaler
import os

# --- LOCKED PARAMETERS ---
BIAS_CORRECTION = -0.1433
SIGMA_GLOBAL = 2.2420
LONGSHOT_CAP = 3.00

# Config
DATA_FILE = "Hockey Data/nhl_totals_features_v1.csv"
ODDS_ERA_START = "2022-10-01"
TARGET = "total_goals"
OUTPUT_FILE = "analysis/nhl_phase2_totals/totals_phase2_roi.md"

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
    # Same chronological split to isolate TEST set
    n = len(df)
    train_end = int(n * 0.6)
    val_end = int(n * 0.8)
    
    train = df.iloc[:train_end]
    val = df.iloc[train_end:val_end]
    test = df.iloc[val_end:].copy()
    
    return train, val, test, features

def calculate_ev(row):
    """
    Calculate EV for Over and Under.
    Returns: (Best Side, Best EV, Best Price)
    """
    # Odds Check
    over_price = row['over_price_close']
    under_price = row['under_price_close']
    
    if pd.isna(over_price) or pd.isna(under_price):
        return None, 0.0, 0.0
        
    # Cap check
    if over_price > LONGSHOT_CAP: over_price = LONGSHOT_CAP # Effectively ignored logic for EV selection if we assume strict cap
    # Actually user said "longshot cap: decimal odds <= 3.00". 
    # If price > 3.00, we DO NOT BET.
    
    # Probabilities
    prob_over = row['prob_over']
    prob_under = row['prob_under']
    
    # EV = (Prob * (Price - 1)) - (1 - Prob)
    # Simplify: Prob * Price - 1
    
    ev_over = (prob_over * over_price) - 1
    ev_under = (prob_under * under_price) - 1
    
    # Selection
    # Valid Bet Check: Price <= 3.00
    valid_over = over_price <= LONGSHOT_CAP
    valid_under = under_price <= LONGSHOT_CAP
    
    best_side = None
    best_ev = -1.0
    best_price = 0.0
    
    if valid_over and ev_over > ev_under and ev_over > 0:
        best_side = 'OVER'
        best_ev = ev_over
        best_price = over_price
    elif valid_under and ev_under > ev_over and ev_under > 0:
        best_side = 'UNDER'
        best_ev = ev_under
        best_price = under_price
        
    return best_side, best_ev, best_price

def simulate():
    df, features = load_and_prep()
    
    # Define Split Indices
    n = len(df)
    train_end = int(n * 0.6)
    val_end = int(n * 0.8)
    
    df['split'] = 'TEST'
    df.iloc[:train_end, df.columns.get_loc('split')] = 'TRAIN'
    df.iloc[train_end:val_end, df.columns.get_loc('split')] = 'VAL'
    
    # Train Logic (Strictly on TRAIN split)
    train_df = df[df['split'] == 'TRAIN']
    X_train = train_df[features]
    y_train = train_df[TARGET]
    
    # Scale (Fit on Train, Transform All)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_all_scaled = scaler.transform(df[features])
    
    # Train Model
    model = ElasticNet(alpha=0.1, l1_ratio=0.5)
    model.fit(X_train_scaled, y_train)
    
    # Predict on ALL data
    df['expected_total_raw'] = model.predict(X_all_scaled)
    df['expected_total'] = df['expected_total_raw'] + BIAS_CORRECTION
    
    # Derive Probs (Using Global Sigma)
    df['prob_over'] = 1 - stats.norm.cdf(df['total_line_close'], loc=df['expected_total'], scale=SIGMA_GLOBAL)
    df['prob_under'] = stats.norm.cdf(df['total_line_close'], loc=df['expected_total'], scale=SIGMA_GLOBAL)
    
    # Calculate EV
    ev_results = df.apply(calculate_ev, axis=1)
    df['bet_side'] = [x[0] for x in ev_results]
    df['bet_ev'] = [x[1] for x in ev_results]
    df['bet_price'] = [x[2] for x in ev_results]
    
    # Grade Bets
    def grade(row):
        if row['bet_side'] is None: return 0.0
        
        actual = row[TARGET]
        line = row['total_line_close']
        
        won = False
        if row['bet_side'] == 'OVER' and actual > line: won = True
        elif row['bet_side'] == 'UNDER' and actual < line: won = True
        elif actual == line: return 0.0
        
        if won: return row['bet_price'] - 1.0
        else: return -1.0
        
    df['pnl'] = df.apply(grade, axis=1)
    
    # Strategies on FULL Set
    strat_a = df[df['bet_ev'] > 0.03].copy()
    strat_b = df[df['bet_ev'] > 0.05].copy()
    
    # Aggregate Stats
    def get_stats(subset, name):
        count = len(subset)
        if count == 0: return f"## {name}\nNo bets found.\n"
        
        roi = subset['pnl'].sum() / count
        pnl = subset['pnl'].sum()
        win_rate = len(subset[subset['pnl'] > 0]) / len(subset[subset['pnl'] != 0]) if len(subset[subset['pnl'] != 0]) > 0 else 0
        
        return f"""## {name}
- **Bets**: {count}
- **ROI**: {roi:.2%}
- **PnL**: {pnl:.2f}u
- **Win Rate**: {win_rate:.1%}
"""

    report = f"""# NHL Totals Phase 2 ROI Simulation (Full Dataset)

## Simulation Parameters
- **Dataset**: Full Odds Era (2022-2026)
- **Model**: ElasticNet (Trained on First 60%)
- **Splits**: Train (In-Sample), Val+Test (Out-of-Sample)

# Strategy A (>3% EV) Analysis

{get_stats(strat_a, "1. Grand Total (All Data)")}

{get_stats(strat_a[strat_a['split'] == 'TRAIN'], "2. In-Sample (Train)")}

{get_stats(strat_a[strat_a['split'].isin(['VAL', 'TEST'])], "3. Out-of-Sample (Val + Test)")}

# Strategy B (>5% EV) Analysis

{get_stats(strat_b, "1. Grand Total (All Data)")}

{get_stats(strat_b[strat_b['split'] == 'TRAIN'], "2. In-Sample (Train)")}

{get_stats(strat_b[strat_b['split'].isin(['VAL', 'TEST'])], "3. Out-of-Sample (Val + Test)")}

## 4. Season Breakdown (Strategy A - Global ROI)
{(strat_a.groupby('season')['pnl'].mean() * 100).to_string(float_format="%.2f%%")}

## 5. Month Breakdown (Strategy A - Global ROI)
{(strat_a.groupby(strat_a['date'].dt.to_period('M'))['pnl'].mean() * 100).to_string(float_format="%.2f%%")}

## 6. Season Breakdown (Strategy B - Global ROI)
{(strat_b.groupby('season')['pnl'].mean() * 100).to_string(float_format="%.2f%%") if 'season' in strat_b.columns else "Season col missing"}

## 7. Month Breakdown (Strategy B - Global ROI)
{(strat_b.groupby(strat_b['date'].dt.to_period('M'))['pnl'].mean() * 100).to_string(float_format="%.2f%%")}
"""
    
    with open(OUTPUT_FILE, "w") as f:
        f.write(report)
    print(f"Report written to {OUTPUT_FILE}")

if __name__ == "__main__":
    simulate()
