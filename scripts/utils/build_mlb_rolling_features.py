import pandas as pd
import joblib
import lightgbm as lgb
import numpy as np

# Config
DATA_FILE = "mlb_statcast_2023_2025.csv"
OUTPUT_FILE = "mlb_pitcher_rolling_features.csv"

MODELS = {
    'swing': 'models/mlb_swing_model.pkl',
    'whiff': 'models/mlb_whiff_model.pkl',
    'cstrike': 'models/mlb_called_strike_model.pkl'
}

def build_rolling_features():
    print(f"⚾ Loading Full History: {DATA_FILE}...")
    
    # Load Necessary Columns
    cols = [
        'game_date', 'pitcher', 'batter', 'pitch_type', 
        'release_speed', 'pfx_x', 'pfx_z', 'plate_x', 'plate_z',
        'balls', 'strikes', 'description', 'stand', 'p_throws', 'spin_axis',
        'home_team', 'away_team', 'inning_topbot'
    ]
    
    df = pd.read_csv(DATA_FILE, usecols=cols, dtype={
        'release_speed': 'float32', 'pfx_x': 'float32', 'pfx_z': 'float32',
        'plate_x': 'float32', 'plate_z': 'float32',
        'balls': 'int8', 'strikes': 'int8', 'spin_axis': 'float32',
        'pitcher': 'int32'
    })
    df['game_date'] = pd.to_datetime(df['game_date'])
    
    # Feature Prep
    df['stand_R'] = (df['stand'] == 'R').astype(int)
    df['p_throws_R'] = (df['p_throws'] == 'R').astype(int)
    df['pitch_type'] = df['pitch_type'].astype('category')
    
    # Feature List (Must match training!)
    features = [
        'release_speed', 'pfx_x', 'pfx_z', 'plate_x', 'plate_z', 
        'balls', 'strikes', 'spin_axis', 'stand_R', 'p_throws_R', 'pitch_type'
    ]
    df_clean = df.dropna(subset=features).copy() # Copy to avoid slice warnings
    
    # --- INFERENCE ---
    print("🚀 Running Inference (Generating Expected Stats)...")
    clf_swing = joblib.load(MODELS['swing'])
    clf_whiff = joblib.load(MODELS['whiff'])
    
    # P(Swing) for ALL pitches
    df_clean['x_swing'] = clf_swing.predict_proba(df_clean[features])[:, 1]
    
    # P(Whiff) for ALL pitches (Conditional)
    df_clean['x_whiff'] = clf_whiff.predict_proba(df_clean[features])[:, 1]
    
    # ACTUAL Outcomes
    swing_events = [
        'swinging_strike', 'swinging_strike_blocked', 'foul_tip', 
        'hit_into_play', 'foul', 'foul_bunt', 'missed_bunt'
    ]
    whiff_events = ['swinging_strike', 'swinging_strike_blocked', 'missed_bunt']
    
    df_clean['actual_swing'] = df_clean['description'].isin(swing_events).astype(int)
    # Actual Whiff is only defined on swings, but for rolling calc we care about accumulated misses
    df_clean['actual_whiff'] = df_clean['description'].isin(whiff_events).astype(int)
    
    # --- OPPONENT FEATURES (Batting Team Context) ---
    print("🔄 Calculating Opponent Lineup Context...")
    
    # Determine Batting Team
    # Top = Away Batting, Bot = Home Batting
    df_clean['batting_team'] = np.where(df_clean['inning_topbot'] == 'Top', df_clean['away_team'], df_clean['home_team'])
    
    # Sort for Team Rolling
    df_clean = df_clean.sort_values(['batting_team', 'game_date'])
    
    team_features = []
    team_grouped = df_clean.groupby('batting_team')
    
    for tid, group in team_grouped:
        # Team Rolling Window (Last 500 pitches faced ~ 3-4 games)
        # We need to know if they are whiff-happy
        group['opp_x_whiff'] = group['x_whiff'].rolling(window=500, min_periods=100).mean().shift(1)
        group['opp_actual_whiff'] = group['actual_whiff'].rolling(window=500, min_periods=100).mean().shift(1)
        
        # Take snapshot per game
        team_game_log = group.groupby('game_date').first().reset_index()
        team_features.append(team_game_log[['game_date', 'batting_team', 'opp_x_whiff', 'opp_actual_whiff']])
        
    df_team_stats = pd.concat(team_features)
    
    # --- PITCHER FEATURES ---
    print("🔄 Calculating Pitcher Stuff+...")
    df_clean = df_clean.sort_values(['pitcher', 'game_date'])
    pitcher_features = []
    
    grouped = df_clean.groupby('pitcher')
    
    for pid, group in grouped:
        # Rolling Pitcher Stats
        group['roll_x_whiff'] = group['x_whiff'].rolling(window=150, min_periods=50).mean().shift(1)
        group['roll_actual_whiff'] = group['actual_whiff'].rolling(window=150, min_periods=50).mean().shift(1)
        group['roll_x_swing'] = group['x_swing'].rolling(window=150, min_periods=50).mean().shift(1)
        
        group['stuff_quality'] = group['roll_x_whiff']
        group['whiff_oe'] = group['roll_actual_whiff'] - group['roll_x_whiff']
        
        # Identify Opponent for this game
        # If pitcher is Home, Opponent = Away. If Away, Home.
        # However, simpler: look at the batting team he faced in the game row
        # In Statcast, a pitcher usually faces ONE team per game (unless traded mid-game, rare).
        # We take the mode() or first() of batting_team
        
        game_log = group.groupby('game_date').agg({
            'roll_x_whiff': 'first',
            'roll_actual_whiff': 'first',
            'whiff_oe': 'first',
            'stuff_quality': 'first',
            'batting_team': 'first', # The team he faced
            'pitcher': 'first'       # Preserve Pitcher ID
        }).reset_index()
        
        pitcher_features.append(game_log)

    df_pitcher = pd.concat(pitcher_features)
    
    # --- MERGE Context ---
    print("🔗 Merging Pitcher vs Opponent...")
    # Join on game_date and Batting Team (Opponent)
    final_df = pd.merge(
        df_pitcher, 
        df_team_stats, 
        left_on=['game_date', 'batting_team'],
        right_on=['game_date', 'batting_team'],
        how='inner'
    )
    
    # Drop rows with no history
    final_df = final_df.dropna(subset=['stuff_quality', 'opp_x_whiff'])
    
    print(f"✅ Generated Full Features for {len(final_df):,} pitcher-games.")
    final_df.to_csv(OUTPUT_FILE, index=False)
    print(f"💾 Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    build_rolling_features()
