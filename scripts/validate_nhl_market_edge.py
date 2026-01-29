import pandas as pd
import numpy as np
import joblib
import difflib
from sklearn.metrics import log_loss

# Paths
TRAIN_SET = "Hockey Data/training_set_v2.csv"
ODDS_DATA = "Hockey Data/nhl_odds_closing.csv"
MODEL_PATH = "models/nhl_v2.pkl"

def normalize_name(name):
    # Normalize generic NHL names to match Training Set abbreviations or standard names
    # Training Set uses Abbrevs (NYR, BOS). Odds uses Full Names (New York Rangers).
    # We need a robust mapper or fuzzy match.
    
    # Map Full Names to Abbrevs
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

def validate_market_edge():
    print("⚖️  Starting NHL Market Validation (Real Odds)...")
    
    # 1. Load Data
    try:
        df_train = pd.read_csv(TRAIN_SET)
        df_odds = pd.read_csv(ODDS_DATA)
        model = joblib.load(MODEL_PATH)
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return

    # 2. Predict on Training Set (Test Portion)
    # We need to recreate the features and predictions for the *same games* we have odds for.
    # Actually, let's predict on everything and then join.
    
    # Re-engineer features (COPY PASTE logic to ensure consistency)
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
    
    # Predict
    model_probs = model.predict_proba(df_clean[features])[:, 1]
    df_clean['model_prob'] = model_probs
    
    print(f"   Generated Predictions for {len(df_clean)} games.")
    
    # 3. Prepare Odds Data for Join
    # Odds has: date_query (YYYY-MM-DD), home_team (Full), home_odds, away_odds
    # Train has: gameDate_home (YYYYMMDD), team_home (Abbrev)
    
    # Format dates
    df_odds['date_str'] = df_odds['date_query']
    df_clean['date_str'] = pd.to_datetime(df_clean['gameDate_home'].astype(str), format='%Y%m%d').dt.strftime('%Y-%m-%d')
    
    # Map Teams in Odds to Abbrevs
    df_odds['team_home_abbr'] = df_odds['home_team'].apply(normalize_name)
    
    # FILTER CHRONOLOGY (Strict Audit)
    # Ensure Snapshot < Commence Time (Pre-Game Odds only)
    # Parse times
    try:
        # Assuming date_query + 'T23:30:00Z' is the snapshot used.
        # But wait, df_odds doesn't have snapshot time column explicitly, but we know the strategy.
        # However, we DO have 'commence_time'.
        # We also have 'date_query' which is the day we pulled for.
        
        # Actually, best proxy: Filter out games where commence_time < [date_query]T23:30:00Z
        # If the game started BEFORE 6:30 PM ET (23:30 Z), exclude it.
        
        df_odds['snapshot_ts'] = pd.to_datetime(df_odds['date_query'] + 'T23:30:00Z').dt.tz_convert(None) # UTC naive
        # commence_time has Z or offset
        df_odds['commence_ts'] = pd.to_datetime(df_odds['commence_time']).dt.tz_convert(None) # UTC naive
        
        # Buffer: Allow 5 mins? No, strict.
        # Valid if snapshot_ts < commence_ts
        valid_mask = df_odds['snapshot_ts'] < df_odds['commence_ts']
        
        n_dropped = (~valid_mask).sum()
        df_odds = df_odds[valid_mask].copy()
        print(f"   🛡️ Chronology Filter: Dropped {n_dropped} High-Risk Games (Early Starts). Remaining: {len(df_odds)}")
        
    except Exception as e:
        print(f"   ⚠️ Chronology Filter Error: {e}")
    
    # 4. Join
    # Join on Date + Home Team
    print("   Joining with Real Odds...")
    merged = pd.merge(df_clean, df_odds, 
                      left_on=['date_str', 'team_home'], 
                      right_on=['date_str', 'team_home_abbr'], 
                      how='inner')
    
    print(f"   ✅ Matched {len(merged)} games with Closing Odds.")
    
    if len(merged) == 0:
        print("   ❌ No matches found. Check date formats/team names.")
        print(f"   Train Date Sample: {df_clean['date_str'].iloc[0]}")
        print(f"   Odds Date Sample: {df_odds['date_str'].iloc[0]}")
        return

    # 5. Market LogLoss
    # Implied Prob = 1 / Odds (No, usually we remove vig, but for simple comparison 1/Odds is OK baseline)
    # Market Prob (Vig-Free):
    #   InvHome = 1/HomeOdds
    #   InvAway = 1/AwayOdds
    #   Vig = InvHome + InvAway
    #   TrueProbHome = InvHome / Vig
    
    def get_implied(row):
        ih = 1 / row['home_odds']
        ia = 1 / row['away_odds']
        vig = ih + ia
        return ih / vig
        
    merged['market_prob'] = merged.apply(get_implied, axis=1)
    
    # Calculate LogLoss
    y_true = merged['home_win']
    loss_model = log_loss(y_true, merged['model_prob'])
    loss_market = log_loss(y_true, merged['market_prob'])
    
    print("\n📉 LogLoss Comparison:")
    print(f"   🤖 Model V2 LogLoss:  {loss_model:.4f}")
    print(f"   🏦 Market LogLoss:    {loss_market:.4f}")
    
    if loss_model < loss_market:
        print("   ✅ MODEL BEATS MARKET (Signal Detected)")
    else:
        print(f"   ⚠️  Market is Sharper (Gap: {loss_model - loss_market:.4f})")

    # 6. Real ROI Simulation
    print("\n💰 Real ROI Simulation (Using Closing Odds):")
    
    # Define Edge Thresholds
    # Bet if Model Edge > X%
    
    strategies = [
        ("Any Edge (>0%)", 0.0),
        ("Strong Edge (>5%)", 0.05),
        ("Super Edge (>10%)", 0.10)
    ]
    
    for name, threshold in strategies:
        # Check Home Bets
        # Edge = ModelProb - MarketProb? Or Expected Value?
        # EV = (ModelProb * (Odds - 1)) - (1 - ModelProb)
        # EV > 0 is the criterion.
        
        # Calculate EV for Home Bet
        # EV_Home = (ModelProb * (HomeOdds - 1)) - (1 - ModelProb)
        # Note: We must use the BOOK ODDS (with vig) for PnL, not vig-free.
        
        merged['ev_home'] = (merged['model_prob'] * (merged['home_odds'] - 1)) - (1 - merged['model_prob'])
        
        # Filter bets
        bets = merged[merged['ev_home'] > threshold]
        
        if len(bets) == 0:
            print(f"   {name}: No Bets.")
            continue
            
        wins = bets['home_win'].sum()
        total = len(bets)
        win_rate = wins / total
        
        # Profit
        # Winnings = sum(Odds - 1) for winners - sum(1) for losers?
        # Actually standard implementation:
        # PnL = (Odds * Bet) - Bet if win, -Bet if loss.
        # Assuming 1 Unit bets
        
        pnl = 0
        for _, row in bets.iterrows():
            if row['home_win'] == 1:
                pnl += (row['home_odds'] - 1)
            else:
                pnl -= 1.0
                
        roi = pnl / total
        
        print(f"\n   📊 Strategy: {name}")
        print(f"      Bets: {total} | Wins: {wins} ({win_rate:.1%})")
        print(f"      Profit: {pnl:.2f}u")
        print(f"      ROI: {roi:.2%}")

if __name__ == "__main__":
    validate_market_edge()
