import joblib
import pandas as pd
import numpy as np
import os
import sys
from utils.logging import log
from features_nhl import GoalieGameMap

# Paths
MODEL_PATH = "models/nhl_v2.pkl"
GOALIE_FEATURES_PATH = "Hockey Data/goalie_strength_features.csv"
TEAM_STATS_PATH = "Hockey Data/training_set_v2.csv" # Or a dedicated team stats file?
# Actually, we need a source for "Current Team Stats". 
# For now, let's assume we can derive or load them. 
# Training set has 'xGoalsPercentage_home' etc. derived from MoneyPuck.
# We might need to load the LATEST stats from MoneyPuck or similar.

class NHLModelV2:
    def __init__(self):
        self.model = None
        self.goalie_map = None
        self.goalie_features = None
        self.team_stats = None
        self._load_artifacts()
        
    def _load_artifacts(self):
        try:
            # 1. Load XGBoost Model
            if os.path.exists(MODEL_PATH):
                self.model = joblib.load(MODEL_PATH)
                log("NHL_V2", "✅ Loaded XGBoost Model V2")
            else:
                log("NHL_V2", "❌ Model file not found")
                
            # 2. Load Goalie Map (Helper)
            self.goalie_map = GoalieGameMap()
            
            # 3. Load Goalie Feature Store (Historical/Recent GSAx)
            if os.path.exists(GOALIE_FEATURES_PATH):
                df = pd.read_csv(GOALIE_FEATURES_PATH)
                # Keep only latest per goalie? Or full history?
                # We need lookup by Goalie Name -> Latest Stats.
                # Sort by Date descending, drop duplicates on Name
                df = df.sort_values('gameDate', ascending=False)
                self.goalie_features = df.drop_duplicates(subset=['goalie_name']).set_index('goalie_name')
                log("NHL_V2", f"✅ Loaded Goalie Features ({len(self.goalie_features)} goalies)")
            else:
                log("NHL_V2", "❌ Goalie Features not found")

            # 4. Load Team Stats (Proxy: Use latest from training set for now)
            # Ideally this comes from a Live Scrape of MoneyPuck.
            if os.path.exists(TEAM_STATS_PATH):
                t_df = pd.read_csv(TEAM_STATS_PATH)
                # Sort by date
                t_df = t_df.sort_values('gameDate_home', ascending=False)
                
                # Distinct by team
                # We need xGoalsPercentage, corsiPercentage, fenwickPercentage
                # For Home and Away. 
                # Let's create a Team Lookup Dict.
                stats_cols = ['xGoalsPercentage', 'corsiPercentage', 'fenwickPercentage'] # base names
                
                self.team_stats = {}
                
                # Iterate and cache latest per team
                # Team codes in training set are usually standardized (e.g. SJS, NYR)
                for _, row in t_df.iterrows():
                    h_team = row['team_home']
                    a_team = row['team_away']
                    
                    if h_team not in self.team_stats:
                        self.team_stats[h_team] = {
                            'xGoalsPercentage': row['xGoalsPercentage_home'],
                            'corsiPercentage': row['corsiPercentage_home'],
                            'fenwickPercentage': row['fenwickPercentage_home']
                        }
                    
                    if a_team not in self.team_stats:
                        self.team_stats[a_team] = {
                            'xGoalsPercentage': row['xGoalsPercentage_away'],
                            'corsiPercentage': row['corsiPercentage_away'],
                            'fenwickPercentage': row['fenwickPercentage_away']
                        }
                log("NHL_V2", f"✅ Loaded Team Stats ({len(self.team_stats)} teams)")
                
        except Exception as e:
            log("NHL_V2", f"❌ Error loading artifacts: {e}")

    def get_goalie_stats(self, goalie_name):
        if self.goalie_features is not None and goalie_name in self.goalie_features.index:
            return self.goalie_features.loc[goalie_name]
        return None

    def predict_match(self, home_team, away_team, home_starter=None, away_starter=None, home_dec_odds=None, away_dec_odds=None, date_str=None):
        """
        Run V2 Inference with Audit Trace.
        Returns dict with keys: decision, reject_reasons, prob_home, ev_home, etc.
        """
        # Base Trace
        trace = {
            'home_team': home_team,
            'away_team': away_team,
            'home_starter': home_starter,
            'away_starter': away_starter,
            'home_odds': home_dec_odds,
            'away_odds': away_dec_odds,
            'date': date_str,
            'decision': 'REJECT',
            'reject_reasons': [],
            'prob_home': 0,
            'prob_away': 0,
            'ev_home': 0,
            'ev_away': 0,
            'bet_side': None
        }

        if not self.model or not self.team_stats:
            trace['reject_reasons'].append("MISSING_ARTIFACTS")
            return trace
            
        # 1. Resolve Teams (Abbrev Lookup)
        # Robust Name Mapping (Mirrors NHLTotalsV2)
        NAME_MAP = {
            'nashville predators': 'NSH', 'predators': 'NSH',
            'san jose sharks': 'SJS', 'sharks': 'SJS',
            'new york rangers': 'NYR', 'rangers': 'NYR',
            'los angeles kings': 'LAK', 'kings': 'LAK',
            'anaheim ducks': 'ANA', 'ducks': 'ANA',
            'washington capitals': 'WSH', 'capitals': 'WSH',
            'montreal canadiens': 'MTL', 'canadiens': 'MTL', 'montréal canadiens': 'MTL',
            'carolina hurricanes': 'CAR', 'hurricanes': 'CAR',
            'colorado avalanche': 'COL', 'avalanche': 'COL',
            'edmonton oilers': 'EDM', 'oilers': 'EDM',
            'toronto maple leafs': 'TOR', 'leafs': 'TOR', 'maple leafs': 'TOR',
            'vegas golden knights': 'VGK', 'golden knights': 'VGK', 'knights': 'VGK',
            'calgary flames': 'CGY', 'flames': 'CGY',
            'new york islanders': 'NYI', 'islanders': 'NYI',
            'philadelphia flyers': 'PHI', 'flyers': 'PHI',
            'pittsburgh penguins': 'PIT', 'penguins': 'PIT',
            'minnesota wild': 'MIN', 'wild': 'MIN',
            'buffalo sabres': 'BUF', 'sabres': 'BUF',
            'winnipeg jets': 'WPG', 'jets': 'WPG',
            'columbus blue jackets': 'CBJ', 'blue jackets': 'CBJ',
            'detroit red wings': 'DET', 'red wings': 'DET',
            'st. louis blues': 'STL', 'blues': 'STL', 'st louis blues': 'STL',
            'new jersey devils': 'NJD', 'devils': 'NJD',
            'boston bruins': 'BOS', 'bruins': 'BOS',
            'seattle kraken': 'SEA', 'kraken': 'SEA',
            'dallas stars': 'DAL', 'stars': 'DAL',
            'tampa bay lightning': 'TBL', 'lightning': 'TBL',
            'ottawa senators': 'OTT', 'senators': 'OTT', 
            'florida panthers': 'FLA', 'panthers': 'FLA',
            'chicago blackhawks': 'CHI', 'blackhawks': 'CHI',
            'vancouver canucks': 'VAN', 'canucks': 'VAN',
            'arizona coyotes': 'ARI', 'coyotes': 'ARI', 'utah hockey club': 'UTA', 'utah mammoth': 'UTA', 'utah': 'UTA'
        }
        
        # Normalize
        from utils.team_names import normalize_team_name
        h_norm = normalize_team_name(home_team)
        a_norm = normalize_team_name(away_team)
        
        home_abbr = NAME_MAP.get(h_norm, NAME_MAP.get(home_team, home_team)) # Try norm, then raw
        away_abbr = NAME_MAP.get(a_norm, NAME_MAP.get(away_team, away_team))
        
        trace['home_abbr'] = home_abbr
        trace['away_abbr'] = away_abbr
        
        if home_abbr not in self.team_stats or away_abbr not in self.team_stats:
            trace['reject_reasons'].append(f"MISSING_STATS (Keys: {home_abbr}, {away_abbr})")
            return trace
            
        # 2. Resolve Goalies
        # Logic: Require starters for valid prediction? Or fallback?
        # Trace should show if fallback used.
        h_gsax_L5, h_gsax_L10, h_gsax_S, h_gp = 0.0, 0.0, 0.0, 0
        a_gsax_L5, a_gsax_L10, a_gsax_S, a_gp = 0.0, 0.0, 0.0, 0
        
        if home_starter:
             g = self.get_goalie_stats(home_starter)
             if g is not None:
                 h_gsax_L5 = g['GSAx_L5']
                 h_gsax_L10 = g['GSAx_L10']
                 h_gsax_S = g['GSAx_Season']
                 h_gp = g['Games_Played']
        else:
             trace['reject_reasons'].append("MISSING_STARTER_HOME") # Warning-level?
             
        if away_starter:
             g = self.get_goalie_stats(away_starter)
             if g is not None:
                 a_gsax_L5 = g['GSAx_L5']
                 a_gsax_L10 = g['GSAx_L10']
                 a_gsax_S = g['GSAx_Season']
                 a_gp = g['Games_Played']
        else:
             trace['reject_reasons'].append("MISSING_STARTER_AWAY")

        # 3. Build Feature Vector
        h_stats = self.team_stats[home_abbr]
        a_stats = self.team_stats[away_abbr]
        
        feat = {}
        feat['xGoalsPercentage_home'] = h_stats['xGoalsPercentage']
        feat['corsiPercentage_home'] = h_stats['corsiPercentage']
        feat['fenwickPercentage_home'] = h_stats['fenwickPercentage']
        feat['xGoalsPercentage_away'] = a_stats['xGoalsPercentage']
        feat['corsiPercentage_away'] = a_stats['corsiPercentage']
        feat['fenwickPercentage_away'] = a_stats['fenwickPercentage']
        
        feat['diff_xGoals'] = feat['xGoalsPercentage_home'] - feat['xGoalsPercentage_away']
        feat['diff_corsi'] = feat['corsiPercentage_home'] - feat['corsiPercentage_away']
        
        feat['diff_goalie_GSAx_L5'] = h_gsax_L5 - a_gsax_L5
        feat['diff_goalie_GSAx_L10'] = h_gsax_L10 - a_gsax_L10
        feat['diff_goalie_GSAx_Season'] = h_gsax_S - a_gsax_S
        feat['home_goalie_GP'] = h_gp
        feat['away_goalie_GP'] = a_gp
        
        df_in = pd.DataFrame([feat])
        
        model_cols = [
            'diff_xGoals', 'diff_corsi', 
            'diff_goalie_GSAx_L5', 'diff_goalie_GSAx_L10', 'diff_goalie_GSAx_Season',
            'home_goalie_GP', 'away_goalie_GP',
            'xGoalsPercentage_home', 'corsiPercentage_home', 'fenwickPercentage_home',
            'xGoalsPercentage_away', 'corsiPercentage_away', 'fenwickPercentage_away'
        ]
        
        # 4. Predict
        try:
            prob_home = self.model.predict_proba(df_in[model_cols])[0, 1]
            prob_away = 1.0 - prob_home
            
            trace['prob_home'] = round(prob_home, 4)
            trace['prob_away'] = round(prob_away, 4)
            
            # EV Calculation
            home_ev, away_ev = 0, 0
            if home_dec_odds:
                home_ev = (prob_home * home_dec_odds) - 1
            if away_dec_odds:
                away_ev = (prob_away * away_dec_odds) - 1
                
            trace['ev_home'] = round(home_ev, 4)
            trace['ev_away'] = round(away_ev, 4)
            
            # Decision Logic (Min Edge 2.5% for ML?)
            # Using settings default or local override?
            # Config.MIN_EDGE passed in? No. Use 0.025 as safe default for trace.
            EDGE_THRESH = 0.0
            
            if home_ev > EDGE_THRESH and home_ev > away_ev:
                trace['decision'] = "RECOMMEND"
                trace['bet_side'] = "HOME"
            elif away_ev > EDGE_THRESH and away_ev > home_ev:
                trace['decision'] = "RECOMMEND"
                trace['bet_side'] = "AWAY"
            else:
                 if max(home_ev, away_ev) <= EDGE_THRESH:
                     trace['reject_reasons'].append("EV_BELOW_THRESHOLD")
            
            # Compatibility Return
            # Consumers expect {prob_home, prob_away, features}
            # We return Trace, which HAS these keys.
            trace['features'] = feat
            return trace
            
        except Exception as e:
            trace['reject_reasons'].append(f"INFERENCE_ERROR: {e}")
            log("NHL_V2", f"Inference Error: {e}")
            return trace
