
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os

def train_ref_model():
    print("🚀 Training Referee Impact Model...")
    
    # 1. Load Data
    if not os.path.exists("nba_scores_2025_26.csv"):
        print("❌ Scores file not found. Wait for fetcher.")
        return
        
    scores = pd.read_csv("nba_scores_2025_26.csv")
    refs = pd.read_csv("training_data_refs.csv") # Assignments + Stats
    
    print(f"Scores: {len(scores)} games")
    print(f"Refs:   {len(refs)} games")
    
    # 2. Merge
    # Join on Date, Home, Away
    # Verify column names first
    # scores: Date, Home, Away, HomeScore, AwayScore
    # refs: Date, Home, Away, ... Ref_HomeWin ...
    
    merged = pd.merge(refs, scores, on=['Date', 'Home', 'Away'], how='inner')
    print(f"Merged: {len(merged)} games (Matches found)")
    
    if len(merged) < 50:
        print("⚠️ Not enough data to train.")
        return

    # 3. Feature Engineering
    # Target: Home Win
    merged['Target'] = (merged['HomeScore'] > merged['AwayScore']).astype(int)
    
    features = ['Ref_HomeWin', 'Ref_Fouls', 'Ref_HomeFoulPct']
    X = merged[features].fillna(0)
    y = merged['Target']
    
    # 4. Train
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = LogisticRegression(class_weight='balanced')
    model.fit(X_train, y_train)
    
    # 5. Evaluate
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    
    print(f"\n✅ Model Trained.")
    print(f"   Accuracy: {acc:.2f}")
    print("\n📊 Coefficients (Impact on Home Win Probability):")
    for f, c in zip(features, model.coef_[0]):
        print(f"   {f}: {c:.4f}")
        
    # Save
    joblib.dump(model, "models/ref_impact_model.pkl")
    print("\n💾 Saved to models/ref_impact_model.pkl")
    
if __name__ == "__main__":
    train_ref_model()
