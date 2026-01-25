
import pandas as pd
import joblib
import os

class NHLRefModel:
    def __init__(self, model_path="models/nhl_ref_impact_model.pkl", stats_path="models/nhl_ref_stats.pkl"):
        self.model = None
        self.ref_bias_map = {}
        self.load_artifacts(model_path, stats_path)
        
    def load_artifacts(self, model_path, stats_path):
        """Loads the trained Logistic Regression model and ref stats."""
        try:
            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
                # PATCH: Handle sklearn version mismatch (missing multi_class attribute)
                if not hasattr(self.model, 'multi_class'):
                    self.model.multi_class = 'auto'
                print(f"📊 Loaded NHL Ref Model from {model_path}")
            else:
                 print(f"⚠️ Model not found at {model_path}")
                 
            if os.path.exists(stats_path):
                self.ref_bias_map = joblib.load(stats_path)
                print(f"📊 Loaded NHL Ref Stats for {len(self.ref_bias_map)} refs.")
            else:
                print(f"⚠️ Stats map not found at {stats_path}")
                
        except Exception as e:
            print(f"⚠️ Failed to load NHL Ref artifacts: {e}")
            
        # 3. Load Fresh CSV Data (Override/Supplement PKL)
        csv_path = "nhl_ref_stats_2025_26.csv"
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                # Headers: #,Name,ATS H,ATS H$,O/U...
                count = 0
                for _, row in df.iterrows():
                    name = str(row.get('Name', '')).strip()
                    ats_record = str(row.get('ATS H', ''))
                    
                    if name and '-' in ats_record:
                        try:
                            w, l = map(int, ats_record.split('-'))
                            total = w + l
                            if total > 0:
                                win_pct = w / total
                                self.ref_bias_map[name] = win_pct
                                count += 1
                        except:
                            pass
                print(f"✅ Loaded {count} refs from fresh CSV ({csv_path})")
            except Exception as e:
                print(f"❌ Failed to load fresh CSV: {e}")
            
    def get_game_impact(self, home_team, away_team, refs_list):
        """
        Calculates impact on Home Win Probability using trained model.
        Returns: impact_prob_shift (e.g. +0.02)
        """
        if not refs_list or not self.model:
            return 0.0
            
        # 1. Calculate Average Home Win Prob for this Crew
        biases = []
        
        # Debug: Print loaded map keys to see what we have
        # print(f"DEBUG REF MAP KEYS: {list(self.ref_bias_map.keys())[:5]}")

        for r in refs_list:
            # Normalize Input Name
            # "Jon Mclsaac" -> "Jon McIsaac" match attempt
            # "Ecuyer" -> "Frederick L'Ecuyer"
            
            match_found = None
            
            # A. Direct Match
            if r in self.ref_bias_map:
                match_found = r
            
            # B. Fuzzy / Partial Match
            if not match_found:
                normalized_input = r.lower().replace("mclsaac", "mcisaac").replace("'", "")
                
                for key in self.ref_bias_map:
                    normalized_key = key.lower().replace("'", "")
                    
                    # Check for "Ecuyer" in "Frederick L'Ecuyer"
                    if normalized_input in normalized_key or normalized_key in normalized_input:
                        match_found = key
                        break
                        
            if match_found:
                bias = self.ref_bias_map[match_found]
                biases.append(bias)
                # print(f"   ✅ Ref Match: '{r}' -> '{match_found}' ({bias:.3f})")
            else:
                # print(f"   ❌ Ref Mismatch: '{r}' not in map")
                biases.append(0.54) # Fallback to League Avg
                    
        if not biases:
            return 0.0
            
        avg_bias_input = sum(biases) / len(biases)
        
        # 2. Predict using Model
        # Feature: [avg_bias]
        try:
            # Debug: Ensure model expects 2D array
            prob = self.model.predict_proba([[avg_bias_input]])[0][1]
            return prob - 0.50
        except Exception as e:
            print(f"⚠️ Model Predict Error: {e}")
            return 0.0

if __name__ == "__main__":
    # Test
    m = NHLRefModel()
    print(m.ref_data.get('Wes McCauley', 'Not Found'))
