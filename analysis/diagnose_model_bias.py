import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import log_loss
from db.connection import get_db

# --- CONFIG ---
TARGET_COL = 'target_win'
ODDS_COLS = ['ml_home', 'ml_away']
SPLIT_DATE = '2024-10-01'

def load_data():
    conn = get_db()
    # Sort by H_date
    query = "SELECT * FROM nba_model_train ORDER BY \"game_date_H\""
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def train_get_preds(df):
    # Add Implied Prob Feature (Same as Training)
    df['implied_prob_home'] = 1 / df['ml_home']
    df['implied_prob_away'] = 1 / df['ml_away']

    # Same logic as current production model
    cols = df.columns
    features = [c for c in cols if (
        '_roll_' in c or 
        '_sea_' in c or
        c == 'h_rest_days' or 
        c == 'a_rest_days' or
        c == 'h_is_home' or
        'implied_prob_' in c 
    )]
    
    # Drop NaNs
    df_clean = df.dropna(subset=features + ODDS_COLS + [TARGET_COL])
    
    train = df_clean[df_clean['game_date_H'] < SPLIT_DATE]
    test = df_clean[df_clean['game_date_H'] >= SPLIT_DATE]
    
    X_train = train[features]
    y_train = train[TARGET_COL]
    X_test = test[features]
    y_test = test[TARGET_COL]
    
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.05,
        eval_metric='logloss',
        use_label_encoder=False
    )
    model.fit(X_train, y_train)
    
    probs = model.predict_proba(X_test)[:, 1]
    
    # Return DataFrame with Probs + Odds + Outcome
    res = test.copy()
    res['model_prob_home'] = probs
    res['model_prob_away'] = 1 - probs
    return res

def analyze_calibration(df):
    print("\n--- 1. CALIBRATION & RESIDUALS BY ODDS BUCKET ---")
    
    # We analyze from HOME team perspective for simplicity, or melt?
    # Let's melt to get 2 rows per game (Home view, Away view) for full calibration
    # Actually, simpler to just analyze 'Home Bets' and 'Away Bets' that WOULD be made?
    # No, request asks for bucket analysis of ALL opportunities.
    
    records = []
    
    rows = []
    for idx, row in df.iterrows():
        # Home Perspective
        imp_h = 1 / row['ml_home']
        rows.append({
            'odds': row['ml_home'],
            'model_prob': row['model_prob_home'],
            'book_prob': imp_h, # Raw implied
            'win': 1 if row['target_win'] == 1 else 0,
            'residual': row['model_prob_home'] - imp_h,
            'type': 'Home'
        })
        # Away Perspective
        imp_a = 1 / row['ml_away']
        rows.append({
            'odds': row['ml_away'],
            'model_prob': row['model_prob_away'],
            'book_prob': imp_a,
            'win': 1 if row['target_win'] == 0 else 0,
            'residual': row['model_prob_away'] - imp_a,
            'type': 'Away'
        })
        
    data = pd.DataFrame(rows)
    
    # Bucket by Odds
    data['bucket'] = pd.cut(data['odds'], bins=[0, 1.5, 2.0, 100], labels=['Fav (<1.5)', 'Coin (1.5-2)', 'Dog (>2)'])
    
    summary = data.groupby('bucket', observed=False).agg(
        Count=('win', 'count'),
        Avg_Model=('model_prob', 'mean'),
        Avg_Book=('book_prob', 'mean'),
        Actual_Win=('win', 'mean'),
        Avg_Residual=('residual', 'mean'),
        Std_Residual=('residual', 'std')
    )
    
    summary['Calib_Error'] = summary['Avg_Model'] - summary['Actual_Win']
    print(summary.to_string())
    
    return data

def get_ev_threshold(odds):
    """Bucketed EV thresholds per contract."""
    if odds > 3.0: return 999.0 # Hard Cap (Reject)
    if odds < 1.5: return 0.02
    if odds < 2.2: return 0.03
    return 0.05

def show_top_bets(data):
    print("\n--- 2. TOP 50 BETS (POST-GUARDRAILS) ---")
    
    # Calculate EV
    data['ev'] = (data['model_prob'] * data['odds']) - 1
    
    # Apply Guardrails
    data['threshold'] = data['odds'].apply(get_ev_threshold)
    valid_bets = data[data['ev'] > data['threshold']].copy()
    
    # Filter only positive EV and within safe bounds
    bets = valid_bets.sort_values('ev', ascending=False).head(50)
    
    cols = ['type', 'odds', 'model_prob', 'book_prob', 'ev', 'win']
    print(bets[cols].to_string(index=False))
    
    # Stats on Top 50
    if not bets.empty:
        print("\n[Top 50 Stats (Safe)]")
        print(f"Avg Odds: {bets['odds'].mean():.2f}")
        print(f"Longshots (>2.0): {len(bets[bets['odds']>2])} / 50")
        print(f"ROI: {bets.apply(lambda x: (x['odds']-1) if x['win']==1 else -1, axis=1).sum() / len(bets):.2%}")
        
    # Check 1.5-2.2 Bucket
    coin_bets = valid_bets[(valid_bets['odds'] >= 1.5) & (valid_bets['odds'] <= 2.2)]
    print(f"\n[Coin Flip Bucket (1.5-2.2)] Count: {len(coin_bets)}")
    if not coin_bets.empty:
        roi_coin = coin_bets.apply(lambda x: (x['odds']-1) if x['win']==1 else -1, axis=1).sum() / len(coin_bets)
        print(f"ROI: {roi_coin:.2%}")

def main():
    print("🚀 Running Diagnostics...")
    df = load_data()
    res = train_get_preds(df)
    
    data = analyze_calibration(res)
    show_top_bets(data)

if __name__ == "__main__":
    main()
