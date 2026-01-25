import pandas as pd
import joblib
import numpy as np
import math
from scipy.stats import nbinom

# Config
ODDS_FILE = "mlb_odds_2024.csv"
FEATURES_FILE = "mlb_rolling_features_with_targets.csv"
MODEL_FILE = "models/mlb_k_prop_model.pkl"

def calculate_probs(side, line, mu, alpha):
    """
    Computes P(Win), P(Loss), P(Push) using precise Floor/Ceil logic.
    """
    # NB Params
    n_p = 1.0 / alpha
    p_p = n_p / (n_p + mu)
    
    # Push Probability (Only if line is integer)
    is_integer = (line % 1) == 0
    if is_integer:
        p_push = nbinom.pmf(int(line), n_p, p_p)
    else:
        p_push = 0.0
    
    p_win = 0.0
    
    if side == 'Over':
        # Win if K >= floor(line) + 1
        # Example 6.5 -> floor(6)+1 = 7. Win if K>=7.
        # Example 6.0 -> floor(6)+1 = 7. Win if K>=7. (6 is Push).
        k_win = math.floor(line) + 1
        # sf(k) is P(X > k) -> P(X >= k+1).
        # We want P(X >= k_win).
        # So we need sf(k_win - 1).
        p_win = nbinom.sf(k_win - 1, n_p, p_p)
        
    elif side == 'Under':
        # Win if K <= ceil(line) - 1
        # Example 6.5 -> ceil(7)-1 = 6. Win if K<=6.
        # Example 6.0 -> ceil(6)-1 = 5. Win if K<=5. (6 is Push).
        k_win = math.ceil(line) - 1
        p_win = nbinom.cdf(k_win, n_p, p_p)
        
    p_loss = 1.0 - p_win - p_push
    return p_win, p_loss, p_push

def run_debug():
    print("🔍 Starting Deep Diagnostic (Logic V2: Floor/Ceil)...")
    
    try:
        odds_df = pd.read_csv(ODDS_FILE)
        feat_df = pd.read_csv(FEATURES_FILE)
    except FileNotFoundError:
        print("❌ File miss.")
        return

    odds_df['game_date'] = pd.to_datetime(odds_df['game_date'])
    feat_df['game_date'] = pd.to_datetime(feat_df['game_date'])
    
    # Feature Engineering
    feat_df = feat_df.sort_values(['pitcher', 'game_date'])
    feat_df['rolling_leash'] = feat_df.groupby('pitcher')['pitch_count'].rolling(window=5, min_periods=1).mean().shift(1).reset_index(0, drop=True)
    feat_df = feat_df.dropna(subset=['rolling_leash'])
    feat_df = feat_df[feat_df['game_date'].dt.year == 2024]
    
    raw_df = pd.read_csv("mlb_statcast_2023_2025.csv", usecols=['pitcher', 'player_name'])
    id_map = raw_df.drop_duplicates('pitcher').set_index('pitcher')['player_name'].to_dict()
    feat_df['player_name'] = feat_df['pitcher'].map(id_map)
    
    def fix_name(n):
        if not isinstance(n, str): return ""
        if ',' in n:
            last, first = n.split(',', 1)
            return f"{first.strip()} {last.strip()}".lower()
        return n.lower()
        
    feat_df['join_name'] = feat_df['player_name'].apply(fix_name)
    odds_df['join_name'] = odds_df['pitcher'].str.lower().str.strip()
    
    merged = pd.merge(feat_df, odds_df, left_on=['game_date', 'join_name'], right_on=['game_date', 'join_name'], how='inner')
    
    model = joblib.load(MODEL_FILE)
    features = ['stuff_quality', 'whiff_oe', 'rolling_leash', 'roll_actual_whiff', 'opp_x_whiff', 'opp_actual_whiff']
    merged['pred_mu'] = model.predict(merged[features])
    
    # CONFIG
    MAX_JUICE = -120 
    MIN_LEASH = 75
    
    debug_rows = []
    
    def to_decimal(us_odds):
        if us_odds > 0: return (us_odds / 100) + 1
        else: return (100 / abs(us_odds)) + 1
        
    grouped = merged.groupby(['game_id', 'pitcher_x', 'line'])
    
    print(f"   Analyzing {len(grouped)} markets...")
    
    count_high_ev = 0
    
    for (gid, pitcher, line), group in grouped:
        row = group.iloc[0]
        mu = row['pred_mu']
        leash = row['rolling_leash']
        
        if leash < MIN_LEASH: continue
        
        # Alpha Logic
        if leash < 45: alpha = 0.0808
        elif leash <= 75: alpha = 0.1992
        else: alpha = 0.0502
        
        # --- EV EVAL ---
        
        # Check OVER Offers
        ov_offers = group[group['label'] == 'Over']
        if not ov_offers.empty:
            best = ov_offers.loc[ov_offers['price'].idxmax()]
            price = best['price']
            
            if price >= MAX_JUICE:
                # Use Adjusted Mu for Over
                mu_adj_ov = max(0.1, mu - 0.25)
                p_win, p_loss, p_push = calculate_probs('Over', line, mu_adj_ov, alpha)
                
                dec = to_decimal(price)
                profit_unit = dec - 1
                ev = (p_win * profit_unit) - (p_loss * 1)
                
                if ev > 0.08:
                    count_high_ev += 1
                    debug_rows.append({
                        'Side': 'Over', 'Line': line, 'Odds': price, 'Mu': mu, 'MuAdj': mu_adj_ov,
                        'P_Win': p_win, 'P_Loss': p_loss, 'EV': ev, 'SumProb': p_win+p_loss+p_push
                    })
                    if count_high_ev >= 5: break

        # Check UNDER Offers_
        if count_high_ev >= 5: break
        
        un_offers = group[group['label'] == 'Under']
        if not un_offers.empty:
            best = un_offers.loc[un_offers['price'].idxmax()]
            price = best['price']
            
            if price >= MAX_JUICE:
                # Use Standard Mu for Under (or should we?) Use standard Mu per logic.
                p_win, p_loss, p_push = calculate_probs('Under', line, mu, alpha)
                
                dec = to_decimal(price)
                profit_unit = dec - 1
                ev = (p_win * profit_unit) - (p_loss * 1)
                
                if ev > 0.08:
                    count_high_ev += 1
                    debug_rows.append({
                        'Side': 'Under', 'Line': line, 'Odds': price, 'Mu': mu, 'MuAdj': mu,
                        'P_Win': p_win, 'P_Loss': p_loss, 'EV': ev, 'SumProb': p_win+p_loss+p_push
                    })

    # Print
    print("\n🔍 DEBUG: Top 5 High EV Bets (>8%) Details:")
    if debug_rows:
        df = pd.DataFrame(debug_rows)
        cols = ['Side', 'Line', 'Odds', 'Mu', 'P_Win', 'P_Loss', 'EV', 'SumProb']
        print(df[cols].to_string())
    else:
        print("   No bets found.")

if __name__ == "__main__":
    run_debug()
