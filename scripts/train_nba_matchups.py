import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import log_loss
from db.connection import get_db

# --- CONFIG ---
TARGET_COL = 'target_win'
SPLIT_DATE = '2024-10-01'

def get_ev_threshold(odds):
    if odds > 3.0: return 999.0 
    if odds < 1.5: return 0.02
    if odds < 2.2: return 0.03
    return 0.05

def load_data():
    conn = get_db()
    df = pd.read_sql('SELECT * FROM nba_model_train', conn)
    conn.close()
    
    # Add Implied Prob
    df['implied_prob_home'] = 1 / df['ml_home']
    df['implied_prob_away'] = 1 / df['ml_away']
    return df

def ab_test_eval(df):
    # Calculate all potential matchup features first
    # 1. Reb Mismatch: Home ORB + Away Allowed ORB (Strength vs Weakness)
    # Rationale: h_orb - a_drb ~= h_orb - (1 - a_opp_orb) = h_orb + a_opp_orb - 1
    df['reb_mismatch'] = df['h_sea_orb'] + df['a_sea_opp_orb']
    
    # 2. TOV Mismatch: Home TOV - Away Forced TOV
    df['tov_mismatch'] = df['h_sea_tov'] - df['a_sea_opp_tov']
    
    # 3. Pace Interaction
    df['pace_interaction'] = df['h_sea_pace'] * df['a_sea_pace']
    
    # Base Features
    cols = df.columns
    base_feats = [c for c in cols if (
        '_roll_' in c or '_sea_' in c or 'rest_days' in c or '_is_home' in c or 'implied_prob_' in c or
        'is_b2b' in c or 'games_in_' in c
    )]
    
    configs = {
        'Baseline': [],
        'REB': ['reb_mismatch'],
        'PACE': ['pace_interaction'],
        'TOV': ['tov_mismatch']
    }
    
    print(f"ℹ️ Base Features: {len(base_feats)}")
    
    # Common Data
    all_req_cols = base_feats + ['reb_mismatch', 'tov_mismatch', 'pace_interaction', 'target_win', 'ml_home', 'ml_away']
    df_clean = df.dropna(subset=all_req_cols)
    train = df_clean[df_clean['game_date_H'] < SPLIT_DATE]
    test = df_clean[df_clean['game_date_H'] >= SPLIT_DATE]
    
    print(f"📅 Train: {len(train)} | Test: {len(test)}")
    
    # 1. Train Baseline First (Reference)
    print(f"\n🧠 Training Baseline...")
    m_base = xgb.XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.05, eval_metric='logloss', use_label_encoder=False)
    m_base.fit(train[base_feats], train[TARGET_COL])
    p_base = m_base.predict_proba(test[base_feats])[:, 1]
    
    ll_base = log_loss(test[TARGET_COL], p_base)
    
    # Helper to get Coin Bets
    def get_coin_bets(probs):
        bets = []
        # Zip dataframe rows (as dicts or tuples) with probs
        # We need index for Mech? Yes.
        # Use simple iteration
        
        # Reset index of test for alignment if we use iloc, but iteration is safer with zip
        for (idx, row), p in zip(test.iterrows(), probs):
            # Home
            if 1.5 <= row['ml_home'] <= 2.2:
                ev = (p * row['ml_home']) - 1
                if ev > 0.03:
                    prof = (row['ml_home'] - 1) if row['target_win']==1 else -1
                    bets.append({'idx': idx, 'side': 'H', 'profit': prof})
            # Away
            if 1.5 <= row['ml_away'] <= 2.2:
                ev = ((1-p) * row['ml_away']) - 1
                if ev > 0.03:
                    prof = (row['ml_away'] - 1) if row['target_win']==0 else -1
                    bets.append({'idx': idx, 'side': 'A', 'profit': prof})
        return pd.DataFrame(bets)

    b_base = get_coin_bets(p_base) # p_base is already 1D array
    roi_base = b_base['profit'].mean() if len(b_base) else 0
    print(f"  -> Baseline LogLoss: {ll_base:.4f} | Coin ROI: {roi_base:.2%} ({len(b_base)})")

    # 2. Iterate Configs
    results = []
    
    for name, feats in configs.items():
        if name == 'Baseline': continue
        
        print(f"\n🧪 Testing {name}...")
        curr_feats = base_feats + feats
        
        m_curr = xgb.XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.05, eval_metric='logloss', use_label_encoder=False)
        m_curr.fit(train[curr_feats], train[TARGET_COL])
        p_curr = m_curr.predict_proba(test[curr_feats])[:, 1]
        
        ll = log_loss(test[TARGET_COL], p_curr)
        b_curr = get_coin_bets(p_curr)
        roi = b_curr['profit'].mean() if len(b_curr) else 0
        
        # Mechanism
        set_b = set(zip(b_base['idx'], b_base['side']))
        set_c = set(zip(b_curr['idx'], b_curr['side']))
        
        kept = len(set_b.intersection(set_c))
        avoided = len(set_b - set_c)
        gained = len(set_c - set_b)
        
        delta_ll = ll - ll_base
        
        print(f"  -> LogLoss: {ll:.4f} (Delta: {delta_ll:+.4f})")
        print(f"  -> ROI: {roi:.2%} ({len(b_curr)})")
        print(f"  -> Mech: Kept {kept}, Avoided {avoided}, Gained {gained}")

if __name__ == "__main__":
    df = load_data()
    ab_test_eval(df)
