import pandas as pd
import joblib
import matplotlib.pyplot as plt
from sklearn.metrics import log_loss

# Paths
TRAIN_SET = "Hockey Data/training_set_v2.csv"
ODDS_DATA = "Hockey Data/nhl_odds_closing.csv"
MODEL_PATH = "models/nhl_v2.pkl"

def normalize_name(name):
    # Same normalizer as before
    mapper = {
        'New York Rangers': 'NYR', 'Boston Bruins': 'BOS', 'Tampa Bay Lightning': 'TBL',
        'Vegas Golden Knights': 'VGK', 'Los Angeles Kings': 'LAK', 'Nashville Predators': 'NSH',
        'San Jose Sharks': 'SJS', 'Washington Capitals': 'WSH', 'Colorado Avalanche': 'COL',
        'Chicago Blackhawks': 'CHI', 'Columbus Blue Jackets': 'CBJ', 'Carolina Hurricanes': 'CAR',
        'Pittsburgh Penguins': 'PIT', 'Montreal Canadiens': 'MTL', 'Toronto Maple Leafs': 'TOR',
        'Arizona Coyotes': 'ARI', 'Utah Hockey Club': 'UTA', 'Anaheim Ducks': 'ANA',
        'Philadelphia Flyers': 'PHI', 'New York Islanders': 'NYI', 'New Jersey Devils': 'NJD',
        'St. Louis Blues': 'STL', 'Vancouver Canucks': 'VAN', 'Edmonton Oilers': 'EDM',
        'Calgary Flames': 'CGY', 'Winnipeg Jets': 'WPG', 'Florida Panthers': 'FLA',
        'Dallas Stars': 'DAL', 'Minnesota Wild': 'MIN', 'Ottawa Senators': 'OTT',
        'Buffalo Sabres': 'BUF', 'Detroit Red Wings': 'DET', 'Seattle Kraken': 'SEA'
    }
    return mapper.get(name, name)

def analyze_stability():
    print("🛡️  Starting NHL Stability & Robustness Analysis...")
    
    # 1. Load
    try:
        df_train = pd.read_csv(TRAIN_SET)
        df_odds = pd.read_csv(ODDS_DATA)
        model = joblib.load(MODEL_PATH)
    except Exception as e:
        print(f"❌ Waiting for data... {e}")
        return

    # 2. Predict (Same Logic)
    df_train['home_win'] = (df_train['goalsFor_home'] > df_train['goalsFor_away']).astype(int)
    features = [
        'diff_xGoals', 'diff_corsi', 
        'diff_goalie_GSAx_L5', 'diff_goalie_GSAx_L10', 'diff_goalie_GSAx_Season',
        'home_goalie_GP', 'away_goalie_GP',
        'xGoalsPercentage_home', 'corsiPercentage_home', 'fenwickPercentage_home',
        'xGoalsPercentage_away', 'corsiPercentage_away', 'fenwickPercentage_away'
    ]
    df_train['diff_xGoals'] = df_train['xGoalsPercentage_home'] - df_train['xGoalsPercentage_away']
    df_train['diff_corsi'] = df_train['corsiPercentage_home'] - df_train['corsiPercentage_away']
    
    df_clean = df_train.dropna(subset=features).copy()
    df_clean['model_prob'] = model.predict_proba(df_clean[features])[:, 1]
    
    # 3. Join Odds
    df_odds['date_str'] = df_odds['date_query']
    df_clean['date_str'] = pd.to_datetime(df_clean['gameDate_home'].astype(str), format='%Y%m%d').dt.strftime('%Y-%m-%d')
    df_odds['team_home_abbr'] = df_odds['home_team'].apply(normalize_name)
    
    merged = pd.merge(df_clean, df_odds, 
                      left_on=['date_str', 'team_home'], 
                      right_on=['date_str', 'team_home_abbr'], 
                      how='inner')
    
    print(f"   📊 Matched {len(merged)} games with Odds (of {len(df_clean)} predicted).")
    
    if len(merged) < 100:
        print("   ⚠️  Sample too small for stability analysis. Waiting for backfill...")
        return

    # 4. Calculate PnL per Game (Strategy: Any Edge > 0)
    # Check Edge
    merged['ev_home'] = (merged['model_prob'] * (merged['home_odds'] - 1)) - (1 - merged['model_prob'])
    
    # Flag Qualified Bets (Home and Away?)
    # For now, let's stick to Home bets for simplicity or check both sides?
    # Actually, we should check Home Edge > 5% as prime strategy
    strategy_mask = merged['ev_home'] > 0.05
    
    bets = merged[strategy_mask].copy()
    
    bets['pnl'] = bets.apply(lambda r: (r['home_odds'] - 1) if r['home_win'] else -1.0, axis=1)
    
    print("\n📈 Season-by-Season Stability:")
    # Season column in train set is usually like 2022
    bets['season_lbl'] = bets['season_home']
    
    season_stats = bets.groupby('season_lbl')['pnl'].agg(['count', 'sum', 'mean'])
    season_stats['roi'] = season_stats['sum'] / season_stats['count']
    print(season_stats)
    
    print("\n📅 Monthly Stability (Last 12 Months):")
    bets['month_lbl'] = bets['date_str'].str[:7] # YYYY-MM
    monthly = bets.groupby('month_lbl')['pnl'].agg(['count', 'sum']).tail(12)
    monthly['roi'] = monthly['sum'] / monthly['count']
    print(monthly)
    
    print("\n🔍 Cumulative Profit:")
    total_profit = bets['pnl'].sum()
    total_roi = total_profit / len(bets)
    print(f"   Total Bets: {len(bets)}")
    print(f"   Total Profit: {total_profit:.2f}u")
    print(f"   Total ROI: {total_roi:.2%}")
    
    if total_roi > 0.05 and len(bets) > 500:
        print("   ✅ PASSED STABILITY: >500 bets with >5% ROI.")
    else:
        print("   ⚠️  NOT YET STABLE (Need more bets or higher ROI).")

if __name__ == "__main__":
    analyze_stability()
