import pandas as pd
import joblib
import lightgbm as lgb
from sklearn.metrics import roc_auc_score
import numpy as np

# Config
DATA_FILE = "mlb_statcast_2023_2025.csv"
MODEL_CSTRIKE = "models/mlb_called_strike_model.pkl"

def validate_borderline():
    print(f"⚾ Loading Test Data (2025)...")
    cols = [
        'pitch_type', 'release_speed', 'pfx_x', 'pfx_z', 'plate_x', 'plate_z',
        'balls', 'strikes', 'description', 'stand', 'p_throws', 'spin_axis', 'game_date'
    ]
    
    df = pd.read_csv(DATA_FILE, usecols=cols, dtype={
        'plate_x': 'float32', 'plate_z': 'float32'
    })
    df['game_date'] = pd.to_datetime(df['game_date'])
    
    # Filter 2025 (Test Set) + Takes Only
    df = df[df['game_date'] >= '2025-01-01'].copy()
    df = df[~df['description'].isin(['swinging_strike', 'foul', 'hit_into_play'])] # Takes
    
    # Target
    df['is_cstrike'] = (df['description'] == 'called_strike').astype(int)
    
    # Pre-process
    df['stand_R'] = (df['stand'] == 'R').astype(int)
    df['p_throws_R'] = (df['p_throws'] == 'R').astype(int)
    df['pitch_type'] = df['pitch_type'].astype('category')
    
    features = [
        'release_speed', 'pfx_x', 'pfx_z', 'plate_x', 'plate_z', 
        'balls', 'strikes', 'spin_axis', 'stand_R', 'p_throws_R', 'pitch_type'
    ]
    df_clean = df.dropna(subset=features)
    
    # Predict
    print(f"🔮 Predicting on {len(df_clean):,} pitches...")
    clf = joblib.load(MODEL_CSTRIKE)
    probs = clf.predict_proba(df_clean[features])[:, 1]
    df_clean['prob_strike'] = probs
    
    # --- CHECK 1: FULL AUC ---
    full_auc = roc_auc_score(df_clean['is_cstrike'], df_clean['prob_strike'])
    print(f"✅ Full Test AUC: {full_auc:.4f}")
    
    # --- CHECK 2: BORDERLINE (Shadow Zone) ---
    # Definition: Edges of plate (~0.7 to 1.0 ft) and Top/Bottom (~1.5/3.5)
    # Simplified Shadow Zone Logic:
    # Width: 0.55 < |plate_x| < 1.1  (Approx 1 ball width around edge)
    # Height: 1.3 < plate_z < 3.7 (Rough vertical zone bounds)
    # But usually borderline is defined by the PREDICTION UNCERTAINTY too.
    
    print("\n--- BORDERLINE CHECKS ---")
    
    # Method A: Geometry (Shadow Zone)
    mask_shadow = (
        (df_clean['plate_x'].abs().between(0.7, 1.0)) | 
        (df_clean['plate_z'].between(1.3, 1.7) | df_clean['plate_z'].between(3.2, 3.6))
    )
    df_shadow = df_clean[mask_shadow]
    
    if len(df_shadow) > 0:
        shadow_auc = roc_auc_score(df_shadow['is_cstrike'], df_shadow['prob_strike'])
        print(f"📍 Geometry Shadow Zone AUC ({len(df_shadow):,} pitches): {shadow_auc:.4f}")
    else:
        print("⚠️ No predictions in Shadow Zone geometry.")

    # Method B: Model Uncertainty (0.25 < p < 0.75)
    mask_uncertain = df_clean['prob_strike'].between(0.25, 0.75)
    df_uncertain = df_clean[mask_uncertain]
    
    if len(df_uncertain) > 0:
        uncertain_auc = roc_auc_score(df_uncertain['is_cstrike'], df_uncertain['prob_strike'])
        print(f"❓ High Uncertainty AUC (0.25 < p < 0.75) ({len(df_uncertain):,} pitches): {uncertain_auc:.4f}")
        print(f"   (If this is ~0.60-0.70, model is legit. If 0.90+, it's leaking.)")
    else:
        print("⚠️ No predictions with high uncertainty.")

if __name__ == "__main__":
    validate_borderline()
