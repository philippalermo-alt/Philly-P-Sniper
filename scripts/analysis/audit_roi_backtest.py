import pandas as pd
import joblib
import numpy as np
from scipy.stats import nbinom

# Files
ODDS_FILE = "mlb_odds_2024.csv"
FEATURES_FILE = "mlb_rolling_features_with_targets.csv"
MODEL_FILE = "models/mlb_k_prop_model.pkl"

def run_backtest():
    print("📉 Loading Assets for Backtest (Diagnostic V5)...")
    
    try:
        odds_df = pd.read_csv(ODDS_FILE)
    except FileNotFoundError:
        print("❌ Odds file not found.")
        return

    odds_df['game_date'] = pd.to_datetime(odds_df['game_date'])
    
    feat_df = pd.read_csv(FEATURES_FILE)
    feat_df['game_date'] = pd.to_datetime(feat_df['game_date'])
    
    print("   Building Pitcher Name Map...")
    raw_df = pd.read_csv("mlb_statcast_2023_2025.csv", usecols=['pitcher', 'player_name'])
    id_map = raw_df.drop_duplicates('pitcher').set_index('pitcher')['player_name'].to_dict()
    
    feat_df['player_name'] = feat_df['pitcher'].map(id_map)
    
    # Feature Engineering (Leash)
    feat_df = feat_df.sort_values(['pitcher', 'game_date'])
    feat_df['rolling_leash'] = feat_df.groupby('pitcher')['pitch_count'].rolling(window=5, min_periods=1).mean().shift(1).reset_index(0, drop=True)
    feat_df = feat_df.dropna(subset=['rolling_leash'])
    feat_df = feat_df[feat_df['game_date'].dt.year == 2024]
    
    # Normalization
    def fix_name(n):
        if not isinstance(n, str): return ""
        if ',' in n:
            last, first = n.split(',', 1)
            return f"{first.strip()} {last.strip()}".lower()
        return n.lower()
        
    feat_df['join_name'] = feat_df['player_name'].apply(fix_name)
    odds_df['join_name'] = odds_df['pitcher'].str.lower().str.strip()
    
    # Merge (All Books)
    merged = pd.merge(
        feat_df, odds_df,
        left_on=['game_date', 'join_name'],
        right_on=['game_date', 'join_name'],
        how='inner' 
    )
    
    print(f"   Matched {len(merged):,} odds lines.")
    
    # Predict
    model = joblib.load(MODEL_FILE)
    features = [
        'stuff_quality', 'whiff_oe', 'rolling_leash', 
        'roll_actual_whiff', 'opp_x_whiff', 'opp_actual_whiff'
    ]
    preds = model.predict(merged[features])
    merged['pred_mu'] = preds
    
    print("💰 Simulating Bets (Diagnostic Mode)...")
    
    # CONFIG
    MAX_JUICE = -120  # Price must be >= -120
    MIN_LEASH = 75    # Stable Only
    
    results = []
    
    def to_decimal(us_odds):
        if us_odds > 0: return (us_odds / 100) + 1
        else: return (100 / abs(us_odds)) + 1
        
    # Group by Unique Market
    grouped = merged.groupby(['game_id', 'pitcher_x', 'line'])
    
    for (gid, pitcher, line), group in grouped:
        row = group.iloc[0]
        mu = row['pred_mu']
        leash = row['rolling_leash']
        actual = row['actual_K']
        
        if leash < MIN_LEASH: continue
        
        # Alpha
        if leash < 45: alpha = 0.0808
        elif leash <= 75: alpha = 0.1992
        else: alpha = 0.0502
        n_p = 1.0/alpha
        
        # Push Check
        is_integer = (line % 1) == 0
        
        # 1. OVER (Bias Corrected)
        mu_adj = max(0.1, mu - 0.25)
        p_param_ov = n_p / (n_p + mu_adj)
        
        if is_integer:
            push_ov = nbinom.pmf(int(line), n_p, p_param_ov)
            win_ov = nbinom.sf(int(line), n_p, p_param_ov)
        else:
            push_ov = 0
            win_ov = nbinom.sf(int(line), n_p, p_param_ov)
        loss_ov = 1 - win_ov - push_ov
        
        # Shop Over
        ov_offers = group[group['label'] == 'Over']
        if not ov_offers.empty:
            best = ov_offers.loc[ov_offers['price'].idxmax()]
            price = best['price']
            
            if price >= MAX_JUICE:
                dec = to_decimal(price)
                ev = (win_ov * (dec - 1)) - (loss_ov * 1)
                
                if ev > 0:
                    prof = 0
                    if actual > line: prof = dec - 1
                    elif actual == line: prof = 0
                    else: prof = -1
                    results.append({'Type': 'Over', 'EV': ev, 'Profit': prof})

        # 2. UNDER (Standard)
        p_param_un = n_p / (n_p + mu)
        
        if is_integer:
            push_un = nbinom.pmf(int(line), n_p, p_param_un)
            win_un = nbinom.cdf(int(line)-1, n_p, p_param_un)
        else:
            push_un = 0
            win_un = nbinom.cdf(int(line), n_p, p_param_un)
        loss_un = 1 - win_un - push_un
        
        # Shop Under
        un_offers = group[group['label'] == 'Under']
        if not un_offers.empty:
            best = un_offers.loc[un_offers['price'].idxmax()]
            price = best['price']
            
            if price >= MAX_JUICE:
                dec = to_decimal(price)
                ev = (win_un * (dec - 1)) - (loss_un * 1)
                
                if ev > 0:
                    prof = 0
                    if actual < line: prof = dec - 1
                    elif actual == line: prof = 0
                    else: prof = -1
                    results.append({'Type': 'Under', 'EV': ev, 'Profit': prof})

    # Summary
    res_df = pd.DataFrame(results)
    if len(res_df) == 0:
        print("⚠️ No bets found.")
        return

    # Buckets
    bins = [0, 0.03, 0.05, 0.08, 1.0]
    labels = ['0-3%', '3-5%', '5-8%', '8%+']
    res_df['Bucket'] = pd.cut(res_df['EV'], bins=bins, labels=labels)
    
    print("\n📊 ROI by EV BUCKET (Odds >= -120, Leash >= 75):")
    summary = res_df.groupby('Bucket', observed=False).agg(
        Bets=('Profit', 'count'),
        Units=('Profit', 'sum'),
        ROI=('Profit', lambda x: x.sum() / x.count() if x.count() > 0 else 0)
    )
    summary['ROI'] = summary['ROI'].apply(lambda x: f"{x:.1%}")
    print(summary)
    
    print(f"\n   Total Profit: {res_df['Profit'].sum():.2f}u")

if __name__ == "__main__":
    run_backtest()
