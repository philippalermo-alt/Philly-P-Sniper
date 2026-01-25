import pandas as pd
import lightgbm as lgb
import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report

# Config
DATA_FILE = "mlb_statcast_2023_2025.csv"
MODEL_SWING = "models/mlb_swing_model.pkl"
MODEL_WHIFF = "models/mlb_whiff_model.pkl"
MODEL_CSTRIKE = "models/mlb_called_strike_model.pkl"

def train_physics_models():
    print(f"⚾ Loading Data: {DATA_FILE}...")
    
    # Load Date for splitting
    cols = [
        'pitch_type', 'release_speed', 'pfx_x', 'pfx_z', 'plate_x', 'plate_z',
        'balls', 'strikes', 'description', 'stand', 'p_throws', 'spin_axis', 'game_date'
    ]
    
    df = pd.read_csv(DATA_FILE, usecols=cols, dtype={
        'release_speed': 'float32',
        'pfx_x': 'float32',
        'pfx_z': 'float32',
        'plate_x': 'float32',
        'plate_z': 'float32',
        'balls': 'int8',
        'strikes': 'int8',
        'spin_axis': 'float32'
    })
    
    # Pre-processing (Shared)
    df['stand_R'] = (df['stand'] == 'R').astype(int)
    df['p_throws_R'] = (df['p_throws'] == 'R').astype(int)
    df['pitch_type'] = df['pitch_type'].astype('category')
    
    # ensure date format
    df['game_date'] = pd.to_datetime(df['game_date'])
    
    swing_events = [
        'swinging_strike', 'swinging_strike_blocked', 'foul_tip', 
        'hit_into_play', 'foul', 'foul_bunt', 'missed_bunt'
    ]
    
    # Explicit features as requested
    features = [
        'release_speed', 'pfx_x', 'pfx_z', 'plate_x', 'plate_z', 
        'balls', 'strikes', 'spin_axis', 'stand_R', 'p_throws_R', 'pitch_type'
    ]
    
    # --- MODEL 1: SWING PROBABILITY (P(Swing)) ---
    print("\nTraining Model 1: P(Swing)...")
    df['is_swing'] = df['description'].isin(swing_events).astype(int)
    df_clean = df.dropna(subset=features)
    train_and_save_time_split(df_clean, features, 'is_swing', MODEL_SWING)

    # --- MODEL 2: WHIFF PROBABILITY (P(Whiff | Swing)) ---
    print("\nTraining Model 2: P(Whiff | Swing)...")
    df_swing = df[df['is_swing'] == 1].copy()
    whiff_events = ['swinging_strike', 'swinging_strike_blocked', 'missed_bunt']
    df_swing['is_whiff'] = df_swing['description'].isin(whiff_events).astype(int)
    
    df_clean_w = df_swing.dropna(subset=features)
    train_and_save_time_split(df_clean_w, features, 'is_whiff', MODEL_WHIFF)

    # --- MODEL 3: CALLED STRIKE PROBABILITY (P(Call | Take)) ---
    print("\nTraining Model 3: P(Called Strike | Take)...")
    df_take = df[df['is_swing'] == 0].copy()
    df_take['is_cstrike'] = (df_take['description'] == 'called_strike').astype(int)
    
    df_clean_c = df_take.dropna(subset=features)
    train_and_save_time_split(df_clean_c, features, 'is_cstrike', MODEL_CSTRIKE)

def train_and_save_time_split(df, features, target_col, save_path):
    # TIME SPLIT: Train 2023-2024, Test 2025
    # Strict temporal separation prevents leakage of pitcher form
    split_date = '2025-01-01'
    
    train_mask = df['game_date'] < split_date
    test_mask = df['game_date'] >= split_date
    
    X_train = df.loc[train_mask, features]
    y_train = df.loc[train_mask, target_col]
    
    X_test = df.loc[test_mask, features]
    y_test = df.loc[test_mask, target_col]
    
    print(f"   Split: Train {len(X_train):,} / Test {len(X_test):,}")
    
    clf = lgb.LGBMClassifier(
        n_estimators=300, 
        learning_rate=0.05,
        num_leaves=31,
        random_state=42,
        n_jobs=-1
    )
    
    clf.fit(X_train, y_train, categorical_feature=['pitch_type'])
    
    preds_prob = clf.predict_proba(X_test)[:, 1]
    preds_class = clf.predict(X_test)
    
    roc = roc_auc_score(y_test, preds_prob)
    acc = accuracy_score(y_test, preds_class)
    
    print(f"   [{target_col}] AUC: {roc:.4f} | Acc: {acc:.4f}")
    
    import os
    os.makedirs('models', exist_ok=True)
    joblib.dump(clf, save_path)
    print(f"   💾 Saved to {save_path}")

if __name__ == "__main__":
    train_physics_models()
