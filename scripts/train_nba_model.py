import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import accuracy_score, log_loss
from db.connection import get_db

def load_data():
    conn = get_db()
    # Sort by H_date since game_date is ambiguous
    query = "SELECT * FROM nba_model_train ORDER BY \"game_date_H\""
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def validate_odds(df, cols):
    print("🔍 Validating Odds Format...")
    for c in cols:
        if c in df.columns:
            mn, mx = df[c].min(), df[c].max()
            print(f"  -> {c}: Min={mn}, Max={mx}")
            if mn < 1.0 or mx > 100:
                print(f"  ⚠️ WARNING: {c} might be American Odds! (Min < 1 or Max > 100)")
            else:
                print(f"  ✅ {c} looks like Decimal.")

def calculate_book_logloss(y_true, odds_home, odds_away):
    """
    Calculate LogLoss of the Bookmaker's implied probabilities (Devigged).
    """
    # Implied Probs
    imp_h = 1 / odds_home
    imp_a = 1 / odds_away
    
    # Devig (Normalization)
    total_imp = imp_h + imp_a
    fair_h = imp_h / total_imp
    
    # Clip to avoid log(0) - although fair value usually safe
    fair_h = fair_h.clip(0.01, 0.99)
    
    ll = log_loss(y_true, fair_h)
    return ll

def train_and_eval(target_col, feature_cols, train_df, test_df, model_name="Model", odds_cols=None):
    print(f"\n🧠 Training {model_name}...")
    
    X_train = train_df[feature_cols]
    y_train = train_df[target_col]
    
    X_test = test_df[feature_cols]
    y_test = test_df[target_col]
    
    # XGBoost Classifier
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.05,
        eval_metric='logloss',
        use_label_encoder=False
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate
    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1]
    
    acc = accuracy_score(y_test, preds)
    ll_model = log_loss(y_test, probs)
    
    print(f"✅ Accuracy: {acc:.2%}")
    print(f"📉 Model LogLoss: {ll_model:.4f}")
    
    # Book Comparison
    if odds_cols:
        # Assuming odds_cols = [home, away] (or Over, Under)
        ll_book = calculate_book_logloss(y_test, test_df[odds_cols[0]], test_df[odds_cols[1]])
        print(f"📖 Book  LogLoss: {ll_book:.4f} (Lower = Better)")
        
        if ll_model < ll_book:
             print(f"🏆 BEATING THE BOOK! (Delta: {ll_book - ll_model:.4f})")
        else:
             print(f"❌ Worse than Book. (Delta: {ll_model - ll_book:.4f})")
    
    return model, probs

def get_ev_threshold(odds):
    """Bucketed EV thresholds per contract."""
    if odds > 3.0: return 999.0 # Hard Cap (Reject)
    if odds < 1.5: return 0.02
    if odds < 2.2: return 0.03
    return 0.05

def simulate_betting_moneyline(test_df, probs):
    """
    Simulate betting with Odds Buckets & Caps.
    """
    df = test_df.copy()
    df['prob_home'] = probs
    df['prob_away'] = 1 - probs
    
    bets = []
    
    for idx, row in df.iterrows():
        # Home Bet
        if row['ml_home'] > 0:
            thresh_h = get_ev_threshold(row['ml_home'])
            ev_h = (row['prob_home'] * row['ml_home']) - 1
            
            if ev_h > thresh_h:
                profit = (row['ml_home'] - 1) if row['target_win'] == 1 else -1
                bets.append({'type': 'Home', 'edge': ev_h, 'profit': profit, 'odds': row['ml_home']})
                
        # Away Bet
        if row['ml_away'] > 0:
            thresh_a = get_ev_threshold(row['ml_away'])
            ev_a = (row['prob_away'] * row['ml_away']) - 1
            
            if ev_a > thresh_a:
                # Target win=0 means Away Won
                profit = (row['ml_away'] - 1) if row['target_win'] == 0 else -1
                bets.append({'type': 'Away', 'edge': ev_a, 'profit': profit, 'odds': row['ml_away']})

    if not bets:
        print("  -> No bets.")
        return

    res = pd.DataFrame(bets)
    
    # Analyze by Bucket
    res['bucket'] = pd.cut(res['odds'], bins=[0, 1.5, 2.0, 3.0, 100], labels=['Heavy Fav (<1.5)', 'Coin (1.5-2)', 'Dog (2-3)', 'Cap (>3)'])
    
    print(f"💰 ML Sim (Contract Rules):")
    
    # Detailed Aggregation
    grouped = res.groupby('bucket', observed=False).agg({
        'profit': ['count', 'sum', 'mean'],
        'odds': 'mean'
    })
    
    # Flatten
    grouped.columns = ['count', 'pnl', 'roi', 'avg_odds']
    
    print(f"  -> Total: {len(res)} bets | ROI: {res['profit'].sum()/len(res):.2%}")
    print("  -> By Odds Bucket:")
    print(grouped)
    
    # Validation Check
    longshots = grouped.loc['Cap (>3)', 'count']
    if longshots > 0:
         print(f"⚠️ SAFETY WARN: {longshots} bets > 3.0 odds!")

def simulate_betting_total(test_df, probs, threshold=0.05):
    """
    Simulate OVER and UNDER betting (EV).
    """
    df = test_df.copy()
    df['prob_over'] = probs
    df['prob_under'] = 1 - probs
    
    bets = []
    
    for idx, row in df.iterrows():
        # Over Bet
        if row['total_over_odds'] > 0:
            ev_o = (row['prob_over'] * row['total_over_odds']) - 1
            if ev_o > threshold:
                profit = (row['total_over_odds'] - 1) if row['target_over'] == 1 else -1
                bets.append({'type': 'Over', 'edge': ev_o, 'profit': profit, 'odds': row['total_over_odds']})
                
        # Under Bet
        if row['total_under_odds'] > 0:
            ev_u = (row['prob_under'] * row['total_under_odds']) - 1
            if ev_u > threshold:
                profit = (row['total_under_odds'] - 1) if row['target_over'] == 0 else -1
                bets.append({'type': 'Under', 'edge': ev_u, 'profit': profit, 'odds': row['total_under_odds']})

    if not bets:
        print("  -> No bets.")
        return

    res = pd.DataFrame(bets)
    roi = res['profit'].sum() / len(res)
    print(f"💰 Total Sim (EV > {threshold:.1%}):")
    print(f"  -> Total: {len(res)} bets | ROI: {roi:.2%}")

def main():
    print("🚀 Loading Data...")
    df = load_data()
    print(f"Loaded {len(df)} rows.")
    
    # 1. Validate Odds
    validate_odds(df, ['ml_home', 'ml_away', 'spread_home_odds', 'total_over_odds'])
    
    # 1. Add Market-Aware Features (Implied Prob)
    # This anchors the model to the book's efficient price
    df['implied_prob_home'] = 1 / df['ml_home']
    df['implied_prob_away'] = 1 / df['ml_away']
    
    # 2. Explicit Feature Selection (Anti-Leak)
    cols = df.columns
    features = [c for c in cols if (
        '_roll_' in c or 
        '_sea_' in c or
        c == 'h_rest_days' or 
        c == 'a_rest_days' or
        c == 'h_is_home' or
        'implied_prob_' in c or
        # Phase 5 Features
        'games_in_' in c or
        # Phase 6 Features (Final Selection)
        # reb_mismatch: FAILED (Excluded)
        # tov_adv: FAILED (Excluded)
        c == 'threept_mismatch' # ACCEPTED (Track C)
    )]
    
    print("\n🔍 LEAKAGE CHECK:")
    print(f"Features used ({len(features)}): {features}")
    if 'total_points' in features:
        print("🚨 CRITICAL LEAKAGE DETECTED: 'total_points' in features!")
        import sys; sys.exit(1)
    if 'target_residual' in features:
        print("🚨 CRITICAL LEAKAGE DETECTED: 'target_residual' in features!")
        import sys; sys.exit(1)
        
    # Drop NaNs
    # Ensure numeric
    for col in features:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df_clean = df.dropna(subset=features).copy()
    
    # 3. Walk-Forward Split
    # We want to train on Past, Test on Future.
    # Current Dataset spans: 
    d_min, d_max = df_clean['game_date_H'].min(), df_clean['game_date_H'].max()
    print(f"📅 Dataset Range: {d_min.date()} to {d_max.date()}")
    
    # Validation Split: Production Default (Dec 1st - Recent Form Focus)
    split_date = pd.Timestamp('2024-12-01')
    
    train_df = df_clean[df_clean['game_date_H'] < split_date].copy()
    test_df = df_clean[df_clean['game_date_H'] >= split_date].copy()
    
    print(f"✂️  Split Date: {split_date.date()}")
    print(f"📅 Train: {len(train_df)} | Test: {len(test_df)}")
    
    if len(test_df) < 100:
        print("⚠️ Warning: Test set too small. Reverting to Oct 2024 split.")
        split_date = pd.Timestamp('2024-10-01')
        train_df = df_clean[df_clean['game_date_H'] < split_date].copy()
        test_df = df_clean[df_clean['game_date_H'] >= split_date].copy()
        print(f"📅 Train: {len(train_df)} | Test: {len(test_df)}")

    # 4. Moneyline
    print("\n--- MONEYLINE ---")
    t_train = train_df.dropna(subset=['target_win', 'ml_home', 'ml_away'])
    t_test = test_df.dropna(subset=['target_win', 'ml_home', 'ml_away'])
    
    model_win, probs_ml = train_and_eval('target_win', features, t_train, t_test, "Winner Model", odds_cols=['ml_home', 'ml_away'])
    
    # Pass Guardrails: Cap=3.0, Bucketed EV
    simulate_betting_moneyline(t_test, probs_ml)

    # 5. Totals
    # Note: Totals implied prob is usually 50% (-110), so less impact, but worth trying if we had raw prices. 
    # Current dataset has 'total_over_odds' ~ 1.91.
    
    print("\n--- TOTALS (REGRESSION) ---\n")
    # Totals (Using same split/features? Yes)
    t_train_t = train_df.dropna(subset=['target_over', 'total_over_odds', 'total_under_odds', 'total_points', 'total_line']).copy()
    t_test_t = test_df.dropna(subset=['target_over', 'total_over_odds', 'total_under_odds', 'total_points', 'total_line']).copy()
    
    # 5a. Feature Engineering for Regression
    # Calculate Residual Target
    # Pos Residual = Over (Actual > Line)
    # Neg Residual = Under (Actual < Line)
    t_train_t['target_residual'] = t_train_t['total_points'] - t_train_t['total_line']
    t_test_t['target_residual'] = t_test_t['total_points'] - t_test_t['total_line']
    
    # Add 'total_line' as a feature if not present, as it captures game state expectation
    # But be careful of leakage. The line is known pre-game. It is safe.
    # However, 'target_residual' is derived from it.
    if 'total_line' not in features:
        features_reg = features + ['total_line']
    else:
        features_reg = features

    print(f"📉 Training Regression Model on {len(t_train_t)} samples...")
    
    reg_model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.05,
        objective='reg:absoluteerror', # Optimize MAE directly
        n_jobs=-1
    )
    
    reg_model.fit(t_train_t[features_reg], t_train_t['target_residual'])
    
    # 5b. Evaluation
    preds_resid = reg_model.predict(t_test_t[features_reg])
    preds_total = t_test_t['total_line'] + preds_resid
    
    from sklearn.metrics import mean_absolute_error, mean_squared_error
    
    mae = mean_absolute_error(t_test_t['total_points'], preds_total)
    rmse = np.sqrt(mean_squared_error(t_test_t['total_points'], preds_total))
    
    # Book Performance (Perfect Line Prediction would be Line itself)
    # Book Error = |Actual - Line|
    book_mae = mean_absolute_error(t_test_t['total_points'], t_test_t['total_line'])
    
    print(f"📊 Model MAE: {mae:.2f}")
    print(f"📖 Book  MAE: {book_mae:.2f}")
    print(f"📉 RMSE: {rmse:.2f}")
    
    if mae < book_mae:
        print(f"🏆 BEATING THE BOOK! (Delta: {book_mae - mae:.2f} pts)")
    else:
        print(f"❌ Worse than Book. (Delta: {mae - book_mae:.2f} pts)")
        
    # 5c. Sigma Estimation (Bucketed)
    # Residuals of the MODEL (Actual - Predicted)
    # NOT the Target Residual (Actual - Line)
    model_residuals = t_test_t['total_points'] - preds_total
    
    # 5c. Empirical Residual Estimation (Bucketed)
    # Residuals = Actual - Predicted
    # We want to know P(Actual > Line)
    # Actual = Pred + Resid
    # P(Pred + Resid > Line) = P(Resid > Line - Pred)
    # Let Diff = Line - Pred. We want P(Resid > Diff).
    
    t_test_t['resid'] = t_test_t['total_points'] - preds_total
    
    # Bucketing (Low/Med/High)
    t_test_t['line_bucket'] = pd.qcut(t_test_t['total_line'], q=3, labels=['Low', 'Med', 'High'])
    t_test_t['line_bucket'] = t_test_t['line_bucket'].astype(str)
    
    # Store Sorted Residuals per Bucket
    residuals_dict = {}
    for bucket in ['Low', 'Med', 'High', 'Global']:
        if bucket == 'Global':
            resids = t_test_t['resid'].values
        else:
            resids = t_test_t[t_test_t['line_bucket'] == bucket]['resid'].values
            
        # Sort for fast CDF lookup (searchsorted)
        resids = np.sort(resids)
        # Store as list for JSON (downsample if huge? 1.3k is fine)
        residuals_dict[bucket] = resids.tolist()
        
    print(f"📐 Residual Counts: { {k: len(v) for k,v in residuals_dict.items()} }")
    
    # 5d. Simulation with Empirical Prob
    def get_empirical_prob_over(pred, line, bucket, res_dict):
        # We need P(Resid > Line - Pred)
        diff = line - pred
        
        # Lookup proper residuals
        r_list = res_dict.get(bucket, res_dict['Global'])
        r_arr = np.array(r_list) # Inefficient loop, but vectorizing next
        
        # Count how many residuals are > diff
        # np.searchsorted finds index where diff would go to maintain order
        # Since r_sort is ascending:
        # P(X > val) is (N - idx) / N ?
        # searchsorted returns index `i` such that r[:i] < val and r[i:] >= val (side='left')
        # We want > diff.
        # side='right' (r[:i] <= val, r[i:] > val)
        
        idx = np.searchsorted(r_arr, diff, side='right')
        count_above = len(r_arr) - idx
        return count_above / len(r_arr)

    # Vectorized Apply (fast enough for 1.3k)
    t_test_t['pred_total'] = preds_total
    t_test_t['prob_over'] = t_test_t.apply(
        lambda x: get_empirical_prob_over(x['pred_total'], x['total_line'], x['line_bucket'], residuals_dict),
        axis=1
    )
    
    print("\n💰 Simulation Results (Empirical):")
    simulate_betting_total(t_test_t, t_test_t['prob_over'].values, 0.03)
    simulate_betting_total(t_test_t, t_test_t['prob_over'].values, 0.05)
    simulate_betting_total(t_test_t, t_test_t['prob_over'].values, 0.07)

    # Save Models for Production
    print("💾 Saving Production Artifacts...")
    import joblib
    import json
    
    # Save Models
    # Save Models
    joblib.dump(model_win, 'models/nba_model_ml_v2.joblib')
    joblib.dump(reg_model, 'models/nba_model_total_v2.joblib') # Regression Model
    
    # Save Feature List
    with open('models/nba_features_v2.json', 'w') as f:
        json.dump(features, f)
        
    # Save Residuals (Empirical)
    with open('models/nba_total_residuals.json', 'w') as f:
        # Convert list to JSON safe if needed (it is already list of floats)
        json.dump(residuals_dict, f)
        
    print("✅ Model Artifacts Saved (ML, Totals, Features, Residuals)")

if __name__ == "__main__":
    main()
