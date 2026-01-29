import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import log_loss, accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
import joblib

DATA_PATH = "Hockey Data/training_set_v2.csv"
MODEL_OUTPUT = "models/nhl_v2.pkl"

def train_model():
    print("🏒 Starting NHL V2 Model Training...")
    
    # 1. Load Data
    df = pd.read_csv(DATA_PATH)
    print(f"   Loaded {len(df)} games.")
    
    # 2. Define Target (Home Win)
    # goalsFor_home > goalsFor_away -> 1
    # Note: 'goalsFor' might be total goals. Let's verify goals columns.
    # In MoneyPuck: 'goalsFor' is goals scored by the team.
    df['home_win'] = (df['goalsFor_home'] > df['goalsFor_away']).astype(int)
    
    # 3. Feature Selection
    # Team features (Home & Away)
    team_features = [
        'xGoalsPercentage_home', 'corsiPercentage_home', 'fenwickPercentage_home',
        'xGoalsPercentage_away', 'corsiPercentage_away', 'fenwickPercentage_away',
        # Differentials usually help trees but they can learn them too.
        # Let's add explicit diffs for key stats
    ]
    
    # Engineer Team Diffs on the fly
    df['diff_xGoals'] = df['xGoalsPercentage_home'] - df['xGoalsPercentage_away']
    df['diff_corsi'] = df['corsiPercentage_home'] - df['corsiPercentage_away']
    
    team_diffs = ['diff_xGoals', 'diff_corsi']
    
    # Goalie Features (The new stuff!)
    goalie_features = [
        'diff_goalie_GSAx_L5',
        'diff_goalie_GSAx_L10',
        'diff_goalie_GSAx_Season',
        'home_goalie_GP',
        'away_goalie_GP'
    ]
    
    features = team_diffs + goalie_features + team_features
    
    # Drop NAs (games with missing goalie mapping or stats)
    df_clean = df.dropna(subset=features).copy()
    dropped = len(df) - len(df_clean)
    print(f"   Dropped {dropped} rows due to missing features (Empty Net/Missing Map).")
    print(f"   Training Rows: {len(df_clean)}")
    
    X = df_clean[features]
    y = df_clean['home_win']
    
    # 4. Split (Time Based)
    # Sort by date
    df_clean = df_clean.sort_values('gameDate_home')
    
    # Split: Last 20% is test set
    split_idx = int(len(df_clean) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    print(f"   Train Set: {len(X_train)} | Test Set: {len(X_test)}")
    
    # 5. Train XGBoost
    print("   ... Training XGBoost Classifier")
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.05,
        objective='binary:logistic',
        eval_metric='logloss',
        use_label_encoder=False
    )
    
    model.fit(X_train, y_train)
    
    # 6. Evaluate
    probs = model.predict_proba(X_test)[:, 1]
    preds = model.predict(X_test)
    
    loss = log_loss(y_test, probs)
    acc = accuracy_score(y_test, preds)
    auc = roc_auc_score(y_test, probs)
    
    print("\n📊 Model Evaluation (Test Set):")
    print(f"   📉 LogLoss:  {loss:.4f} (Baseline ~0.67-0.69)")
    print(f"   🎯 Accuracy: {acc:.4f}")
    print(f"   📈 AUC:      {auc:.4f}")
    
    # 7. Feature Importance
    print("\n🔑 Feature Importance (Top 10):")
    importance = pd.DataFrame({
        'feature': features,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print(importance.head(10))
    
    # 8. Save
    joblib.dump(model, MODEL_OUTPUT)
    print(f"\n💾 Model saved to {MODEL_OUTPUT}")

if __name__ == "__main__":
    train_model()
