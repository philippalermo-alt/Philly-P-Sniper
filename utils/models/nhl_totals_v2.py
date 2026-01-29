import joblib
import pandas as pd
import numpy as np
import json
import os
import scipy.stats as stats
from datetime import datetime
from utils.logging import log
from utils.team_names import normalize_team_name

class NHLTotalsV2:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.lookup = None
        self.feature_list = None
        
        self.model_path = "models/nhl_totals_v2.joblib"
        self.scaler_path = "models/nhl_totals_scaler_v2.joblib"
        self.lookup_path = "models/nhl_totals_feature_lookup.json"
        self.feature_list_path = "models/nhl_totals_features_list.json"
        
        # Locked Config (Strategy B)
        self.BIAS = -0.1433
        self.SIGMA = 2.2420
        self.EV_THRESHOLD = 0.05
        self.ODDS_CAP = 3.00
        
        self.load_artifacts()
        
    def load_artifacts(self):
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
            if os.path.exists(self.scaler_path):
                self.scaler = joblib.load(self.scaler_path)
            if os.path.exists(self.lookup_path):
                with open(self.lookup_path) as f:
                    self.lookup = json.load(f)
            if os.path.exists(self.feature_list_path):
                with open(self.feature_list_path) as f:
                    self.feature_list = json.load(f)
            
            if self.model and self.lookup and self.feature_list:
                log("NHL_TOTALS", f"✅ Loaded V2 Model & artifacts ({len(self.lookup)} teams)")
            else:
                log("NHL_TOTALS", "⚠️ Missing artifacts for Totals V2")
        except Exception as e:
            log("NHL_TOTALS", f"❌ Error loading artifacts: {e}")

    def predict(self, home_team, away_team, line, over_price, under_price, date_str):
        """
        Generate Totals Recommendation with Audit Trace.
        Returns dict with keys: decision, reject_reasons, debug_data, etc.
        """
        # Base Trace Object
        trace = {
            'home_team': home_team,
            'away_team': away_team,
            'total_line': line,
            'over_price': over_price,
            'under_price': under_price,
            'date': date_str,
            'decision': 'REJECT',
            'reject_reasons': [],
            'expected_total': None,
            'sigma': self.SIGMA,
            'bias_applied': self.BIAS,
            'prob_over': 0,
            'prob_under': 0,
            'ev_over': 0,
            'ev_under': 0,
            'ev': 0,
            'rec_side': None,
            'longshot_cap_pass': False
        }

        if not self.model or not self.lookup or not self.feature_list:
            trace['reject_reasons'].append("MISSING_ARTIFACTS")
            return trace
            
        # 1. Normalize Teams
        # Map Full Names to Abbrevs used in JSON Lookup
        # Lookup keys are: NSH, SJS, NYR, LAK, ANA, WSH, MTL, CAR, COL, EDM, TOR, VGK, CGY, NYI, PHI, PIT, MIN, BUF, WPG, CBJ, DET, STL, NJD, BOS, SEA, DAL, TBL, OTT, FLA, CHI, VAN, ARI, UTA
        
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

        h_norm, a_norm = None, None
        h_key, a_key = None, None
        
        try:
            h_norm = normalize_team_name(home_team)
            a_norm = normalize_team_name(away_team)
            
            # Map to Abbrev
            h_key = NAME_MAP.get(h_norm, h_norm.upper()) # Default to upper if not found (e.g. key is already abbrev but lowercase?)
            a_key = NAME_MAP.get(a_norm, a_norm.upper())
            
            # Direct Lookup 
            # (JSON keys are Uppercase Abbrevs directly)
            h_stats = self.lookup.get(h_key)
            a_stats = self.lookup.get(a_key)
            
            # Fallback: Try raw input if map failed
            if not h_stats: h_stats = self.lookup.get(home_team)
            if not a_stats: a_stats = self.lookup.get(away_team)
            
        except Exception:
            h_stats = self.lookup.get(home_team)
            a_stats = self.lookup.get(away_team)
        
        if not h_stats or not a_stats:
            trace['reject_reasons'].append(f"MISSING_STATS (Keys: {h_key}, {a_key})")
            return trace
            
        # 2. Market Inputs (Vig-Free Prob)
        if not line or not over_price or not under_price:
             trace['reject_reasons'].append("MISSING_ODDS")
             return trace
            
        # Feature: implied_prob_over (Vig-Free)
        try:
            p_o = 1.0 / over_price
            p_u = 1.0 / under_price
            margin = p_o + p_u
            implied_prob_over = p_o / margin
            
            trace['implied_over'] = round(p_o, 4) # Raw implied
            trace['implied_under'] = round(p_u, 4)
        except:
             trace['reject_reasons'].append("ODDS_CALC_ERROR")
             return trace
        
        # 3. Dynamic Rest Calculation
        try:
            game_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            # Home Rest
            h_last = datetime.strptime(h_stats.get('last_game_date', date_str), "%Y-%m-%d").date()
            days_rest_home = (game_date - h_last).days
            if days_rest_home < 1: days_rest_home = 1 # Sanitization
            is_b2b_home = 1 if days_rest_home == 1 else 0
            
            # Away Rest
            a_last = datetime.strptime(a_stats.get('last_game_date', date_str), "%Y-%m-%d").date()
            days_rest_away = (game_date - a_last).days
            if days_rest_away < 1: days_rest_away = 1
            is_b2b_away = 1 if days_rest_away == 1 else 0
            
        except Exception as e:
            # Fallback
            days_rest_home = 2
            days_rest_away = 2
            is_b2b_home = 0
            is_b2b_away = 0
            # log("NHL_TOTALS", f"Rest Calc Error: {e}")
            
        # 4. Construct Feature Vector
        input_data = {}
        
        # Populate Home Stats
        for k, v in h_stats.items():
            input_data[f"{k}_home"] = v
            
        # Populate Away Stats
        for k, v in a_stats.items():
            input_data[f"{k}_away"] = v
            
        # Dynamic Features
        input_data['days_rest_home'] = days_rest_home
        input_data['days_rest_away'] = days_rest_away
        input_data['is_b2b_home'] = is_b2b_home
        input_data['is_b2b_away'] = is_b2b_away
        input_data['total_line_close'] = line
        input_data['implied_prob_over'] = implied_prob_over
        
        # Build Ordered List
        try:
            X_vec = []
            for feat in self.feature_list:
                if feat in input_data:
                    X_vec.append(input_data[feat])
                else:
                    trace['reject_reasons'].append(f"MISSING_FEATURE_{feat}")
                    return trace
                    
            X_arr = np.array([X_vec])
            
            # 5. Scale & Predict
            X_scaled = self.scaler.transform(X_arr)
            expected_total_raw = self.model.predict(X_scaled)[0]
            
            # 6. Apply Bias Correction
            expected_total = expected_total_raw + self.BIAS
            trace['expected_total'] = round(expected_total, 4)
            
            # 7. Probability Derivation
            prob_over = 1 - stats.norm.cdf(line, loc=expected_total, scale=self.SIGMA)
            prob_under = stats.norm.cdf(line, loc=expected_total, scale=self.SIGMA)
            
            trace['prob_over'] = round(prob_over, 4)
            trace['prob_under'] = round(prob_under, 4)
            
            # 8. EV Calculation (Strategy B)
            # EV = (Prob * Price) - 1
            ev_over = (prob_over * over_price) - 1
            ev_under = (prob_under * under_price) - 1
            
            trace['ev_over'] = round(ev_over, 4)
            trace['ev_under'] = round(ev_under, 4)
            
            recommendation = None
            ev_value = 0.0
            side = None
            
            # Check Caps
            valid_over = over_price <= self.ODDS_CAP
            valid_under = under_price <= self.ODDS_CAP
            
            # Audit Caps
            if not valid_over and ev_over > self.EV_THRESHOLD:
                 # Would have bet over but capped
                 # Not strictly a reject reason for the *Under* side, but relevant for Over side analysis.
                 # The decision is mutually exclusive (Recommend ONE or NONE).
                 pass
            
            trace['longshot_cap_pass'] = (valid_over or valid_under)
            
            # Decision Logic
            if valid_over and ev_over > self.EV_THRESHOLD and ev_over > ev_under:
                recommendation = "Over"
                ev_value = ev_over
                side = 'OVER'
                trace['decision'] = "RECOMMEND"
            elif valid_under and ev_under > self.EV_THRESHOLD and ev_under > ev_over:
                recommendation = "Under"
                ev_value = ev_under
                side = 'UNDER'
                trace['decision'] = "RECOMMEND"
            else:
                 # Why rejected?
                 reasons = []
                 if max(ev_over, ev_under) <= self.EV_THRESHOLD:
                     reasons.append("EV_BELOW_THRESHOLD")
                 
                 # Check if high EV but capped
                 if ev_over > self.EV_THRESHOLD and not valid_over:
                      reasons.append("ODDS_CAP_EXCEEDED_OVER")
                 if ev_under > self.EV_THRESHOLD and not valid_under:
                      reasons.append("ODDS_CAP_EXCEEDED_UNDER")
                 
                 trace['reject_reasons'].extend(reasons)
                
            # Populate Result for Return
            # We maintain legacy keys for compatibility but add raw traces
            trace['recommendation'] = recommendation
            trace['bet_side'] = side
            trace['ev'] = round(ev_value, 4)
            
            return trace
            
        except Exception as e:
            trace['reject_reasons'].append(f"PREDICTION_ERROR: {str(e)}")
            return trace
