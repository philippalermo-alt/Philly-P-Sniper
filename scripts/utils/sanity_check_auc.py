from train_soccer_model_v4 import SoccerModelTrainerV4
from sklearn.metrics import roc_auc_score
import pandas as pd

def run_sanity_check():
    print("🧪 Running Single Feature Sanity Check...")
    
    trainer = SoccerModelTrainerV4()
    df = trainer.load_and_engineer()
    
    if df.empty:
        print("❌ No data.")
        return

    # Split (Same as Training)
    split = int(len(df) * 0.8)
    test_df = df.iloc[split:]
    
    y_test = test_df['over_2_5']
    
    # 1. Feature: exp_total_xg
    # Higher xG = Higher prob of Over
    feature_score = test_df['exp_total_xg']
    auc_feature = roc_auc_score(y_test, feature_score)
    
    # 2. Feature: league_avg_xg
    auc_league = roc_auc_score(y_test, test_df['league_avg_xg'])
    
    # 3. Full Model (Load Saved)
    import pickle
    try:
        with open('soccer_model_v4.pkl', 'rb') as f:
            model = pickle.load(f)
        preds = model.predict_proba(test_df[trainer.features])[:, 1]
        auc_model = roc_auc_score(y_test, preds)
    except:
        auc_model = 0.0
        print("Could not load saved model for comparison")

    print("\n" + "="*40)
    print("📊 SANITY CHECK RESULTS")
    print("="*40)
    print(f"1. Single Feature (exp_total_xg): AUC {auc_feature:.4f}")
    print(f"2. Single Feature (league_avg):   AUC {auc_league:.4f}")
    print(f"3. Full XGBoost Model (V4):       AUC {auc_model:.4f}")
    print("-" * 40)
    
    if auc_feature > auc_model:
        print("🚨 WARNING: Simple additive feature beats the complex model!")
        print("    -> Overfitting or Noise in other features.")
    else:
        print("✅ PASS: Model adds value over raw sum.")

if __name__ == "__main__":
    run_sanity_check()
