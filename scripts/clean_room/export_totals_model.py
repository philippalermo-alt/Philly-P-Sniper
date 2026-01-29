import pandas as pd
import numpy as np
import scipy.stats as stats
from sklearn.linear_model import ElasticNet
from sklearn.preprocessing import StandardScaler
import joblib
import json
import os

# --- LOCKED CONFIG ---
BIAS_CORRECTION = -0.1433
SIGMA_GLOBAL = 2.2420
ODDS_ERA_START = "2022-10-01"
DATA_FILE = "Hockey Data/nhl_totals_features_v1.csv"
TARGET = "total_goals"

# Paths
MODEL_PATH = "models/nhl_totals_v2.joblib"
SCALER_PATH = "models/nhl_totals_scaler_v2.joblib"
LOOKUP_PATH = "models/nhl_totals_feature_lookup.json"

def maintain_feature_order(df):
    """
    Ensure specific feature order for production.
    """
    # 1. Identify "Static" features (Team State)
    static_cols = [c for c in df.columns if c.startswith('rolling_')]
    static_cols += ['days_rest_home', 'days_rest_away', 'is_b2b_home', 'is_b2b_away']
    
    # 2. Market features (Dynamic)
    market_cols = ['total_line_close', 'implied_prob_over']
    
    all_features = static_cols + market_cols
    return all_features, static_cols

def export():
    print("Loading data...")
    df = pd.read_csv(DATA_FILE)
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['date'] >= ODDS_ERA_START].copy()
    df = df.sort_values('date').reset_index(drop=True)
    
    # Define Features
    features, static_cols = maintain_feature_order(df)
    
    # Drop NaNs
    df_clean = df.dropna(subset=features + [TARGET])
    print(f"Training on {len(df_clean)} rows...")
    
    X = df_clean[features]
    y = df_clean[TARGET]
    
    # Train Scaler
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Train Model
    print("Training ElasticNet (Locked)...")
    model = ElasticNet(alpha=0.1, l1_ratio=0.5)
    model.fit(X_scaled, y)
    
    # Save Artifacts
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    print(f"Saved Model and Scaler to models/")
    
    # Create Feature Lookup (Latest per team)
    print("Building Feature Lookup...")
    lookup = {}
    
    generic_cols = [c.replace('_home', '') for c in static_cols if '_home' in c]
    
    teams = pd.concat([df['team_norm_home'], df['team_norm_away']]).unique()
    
    for team in teams:
        # Find latest game
        mask = (df['team_norm_home'] == team) | (df['team_norm_away'] == team)
        team_games = df[mask].sort_values('date', ascending=False)
        
        if len(team_games) == 0: continue
        
        latest = team_games.iloc[0]
        
        # Extract stats
        stats = {}
        is_home = (latest['team_norm_home'] == team)
        
        suffix = '_home' if is_home else '_away'
        
        for col in generic_cols:
            source_col = col + suffix
            if source_col in latest:
                val = latest[source_col]
                # Cast to native types for JSON
                if hasattr(val, 'item'): val = val.item()
                stats[col] = val
        
        stats['last_game_date'] = str(latest['date'].date())
        lookup[team] = stats
        
    def default_serializer(obj):
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return str(obj)

    with open(LOOKUP_PATH, "w") as f:
        json.dump(lookup, f, indent=2, default=default_serializer)
    print(f"Saved Feature Lookup for {len(lookup)} teams to {LOOKUP_PATH}")
    
    # Save Feature List (Critical for Order)
    with open("models/nhl_totals_features_list.json", "w") as f:
        json.dump(features, f)
    print("Saved Feature List order.")
    
    # Verify Load
    print("Verification Load...")
    m = joblib.load(MODEL_PATH)
    s = joblib.load(SCALER_PATH)
    with open(LOOKUP_PATH) as f:
        l = json.load(f)
    print(f"Model Coeffs: {m.coef_[:3]}...") 
    print(f"Lookup Sample (PHI): {l.get('PHI', 'Not Found')}")

if __name__ == "__main__":
    export()
