
import pandas as pd
import numpy as np
import joblib
import json
import os
from datetime import datetime
from db.connection import get_db
import logging
from xgboost import XGBClassifier, XGBRegressor
from sklearn.metrics import log_loss, mean_absolute_error

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

REGISTRY_PATH = "models/registry.json"

def load_training_data():
    """
    Load joined dataset: Predictions (Features) + Outcomes (Targets).
    Crucial: Use 'features_snapshot' from the prediction log to ensure we train on EXACTLY what the model saw.
    Differs from 'train_nba_model.py' which rebuilds features from raw stats. 
    Here we trust the snapshot.
    """
    conn = get_db()
    
    # 1. Fetch Joined Data
    query = """
        SELECT 
            p.game_id, p.game_date_est, p.features_snapshot, p.market, p.odds_home, p.odds_away,
            o.home_win, o.total_points
        FROM nba_predictions p
        JOIN nba_outcomes o ON p.game_id = o.game_id
        WHERE p.features_snapshot IS NOT NULL
        AND o.home_win IS NOT NULL
        ORDER BY p.game_date_est ASC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
        
    # 2. Parse JSON Features
    # This might be slow for massive datasets, but fine for thousands.
    feature_list = []
    meta_list = []
    
    for idx, row in df.iterrows():
        try:
            feats = row['features_snapshot']
            if isinstance(feats, str):
                feats = json.loads(feats)
            
            # Combine with Meta
            row_meta = row.to_dict()
            del row_meta['features_snapshot']
            
            # Merge
            full_row = {**row_meta, **feats}
            feature_list.append(full_row)
            
        except Exception as e:
            continue
            
    full_df = pd.DataFrame(feature_list)
    return full_df

def train_and_evaluate(df):
    """
    Train Candidate Model and Return Metrics + Artifacts.
    """
    # 1. Prepare ML Data
    # Filter to ML records or de-dupe by game_id
    df_ml = df.drop_duplicates(subset=['game_id']).copy()
    
    # Features: Exclude meta columns
    meta_cols = ['game_id', 'game_date_est', 'market', 'odds_home', 'odds_away', 'home_win', 'total_points']
    feature_cols = [c for c in df_ml.columns if c not in meta_cols]
    
    X = df_ml[feature_cols]
    y = df_ml['home_win']
    
    # Train/Test Split (Time-based: Last 20% is Test)
    split_idx = int(len(df_ml) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    df_test = df_ml.iloc[split_idx:].copy()
    
    # Train Candidate ML
    model_ml = XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.05, enable_categorical=False)
    model_ml.fit(X_train, y_train)
    
    # Evaluate ML
    preds_proba = model_ml.predict_proba(X_test)[:, 1]
    ll = log_loss(y_test, preds_proba)
    
    # ROI Logic (Simple simulation)
    # Bet Home if edge > 3%
    bets = []
    for idx, (prob, true_win) in enumerate(zip(preds_proba, y_test)):
        row = df_test.iloc[idx]
        odds = row['odds_home']
        if odds > 1.0:
            edge = (prob * odds) - 1
            if edge > 0.03:
                profit = (odds - 1) if true_win == 1 else -1
                bets.append({'profit': profit, 'bucket': 'All', 'odds': odds})
                
    roi_ml = sum(b['profit'] for b in bets) / len(bets) if bets else 0.0
    
    # Buckets
    coin_bets = [b for b in bets if b['odds'] <= 2.0]
    roi_coin = sum(b['profit'] for b in coin_bets) / len(coin_bets) if coin_bets else 0.0
    
    dog_bets = [b for b in bets if b['odds'] > 2.0 and b['odds'] <= 3.0]
    roi_dog = sum(b['profit'] for b in dog_bets) / len(dog_bets) if dog_bets else 0.0
    
    longshots = [b for b in bets if b['odds'] > 3.0]
    count_longshots = len(longshots)
    
    return {
        'model_ml': model_ml,
        'logloss': ll,
        'roi_ml': roi_ml,
        'roi_coin': roi_coin,
        'roi_dog': roi_dog,
        'longshots': count_longshots,
        'test_size': len(X_test)
    }

def update_registry(metrics, new_paths):
    """
    Update models/registry.json if gates passed.
    """
    try:
        with open(REGISTRY_PATH, 'r') as f:
            registry = json.load(f)
            
        registry['nba_ml']['active_path'] = new_paths['ml']
        registry['nba_ml']['last_updated'] = datetime.now().strftime('%Y-%m-%d')
        registry['nba_ml']['metrics'] = metrics
        
        with open(REGISTRY_PATH, 'w') as f:
            json.dump(registry, f, indent=4)
            
        logger.info("✅ Registry Updated with New Model.")
    except Exception as e:
        logger.error(f"Registry Update Failed: {e}")

def run_retrain():
    logger.info("🧠 Starting Weekly Retrain Job...")
    
    # 1. Load Data
    df = load_training_data()
    if len(df) < 100:
        logger.warning("⚠️ Insufficient data to retrain (<100 samples). Aborting.")
        return
        
    logger.info(f"📚 Dataset: {len(df)} records.")
    
    # 2. Train & Eval
    res = train_and_evaluate(df)
    
    logger.info("📊 Candidate Metrics:")
    logger.info(f"   LogLoss: {res['logloss']:.4f}")
    logger.info(f"   ROI (Global): {res['roi_ml']:.2%}")
    logger.info(f"   ROI (Coin): {res['roi_coin']:.2%}")
    logger.info(f"   Longshots (>3.0): {res['longshots']}")
    
    # 3. Check Gates
    # Validations
    passed = True
    
    if res['longshots'] > 0:
        logger.error("❌ Gate Failed: Longshot Exposure > 0")
        passed = False
        
    if res['roi_coin'] < 0.0:
        logger.error("❌ Gate Failed: Coinflip ROI Negative")
        passed = False
        
    # LogLoss Check (Tolerance)
    # Hardcoded baseline from V2: 0.58
    if res['logloss'] > 0.59: 
        logger.error("❌ Gate Failed: LogLoss Regression")
        passed = False
        
    if passed:
        logger.info("✅ All Gates Passed. Promoting Model.")
        
        # Save Artifacts
        ts = datetime.now().strftime('%Y%m%d')
        path_ml = f"models/nba_ml_{ts}.joblib"
        joblib.dump(res['model_ml'], path_ml)
        
        # Update Registry
        update_registry({
            'logloss': res['logloss'], 'roi': res['roi_ml']
        }, {'ml': path_ml})
        
    else:
        logger.warning("⛔ Model Rejected.")

if __name__ == "__main__":
    run_retrain()
