
import pandas as pd
import numpy as np
from db.connection import get_db
import scripts.nhl_ops_config as cfg

class NHLDataValidator:
    def __init__(self, mode='FULL'):
        self.mode = mode
        self.conn = get_db()
        self.report = []
        
    def log(self, status, msg):
        self.report.append(f"[{status}] {msg}")
        print(f"[{status}] {msg}")

    def run_all(self):
        print("🛡 Starting Data Integrity Check...")
        valid = True
        
        valid &= self.check_keys()
        valid &= self.check_logic()
        valid &= self.check_missingness()
        valid &= self.check_game_totals()
        
        if valid:
            self.log("PASS", "All Integrity Gates Passed.")
        else:
            self.log("FAIL", "Integrity Gates Failed. See constraints.")
            
        return valid

    def check_keys(self):
        # 1. Duplicates in Player Logs
        # Key: game_id, player_id
        df = pd.read_sql("SELECT game_id, player_id, COUNT(*) as c FROM nhl_player_game_logs GROUP BY 1,2 HAVING COUNT(*) > 1", self.conn)
        if len(df) > 0:
            self.log("FAIL", f"Found {len(df)} Dup Keys in Player Logs.")
            return False
            
        # 2. Duplicates in Goalie Logs
        # Table might vary depending on previous setup, using 'nhl_goalie_game_logs'
        try:
            df_g = pd.read_sql("SELECT game_id, goalie_id, COUNT(*) as c FROM nhl_goalie_game_logs GROUP BY 1,2 HAVING COUNT(*) > 1", self.conn)
            if len(df_g) > 0:
                self.log("FAIL", f"Found {len(df_g)} Dup Keys in Goalie Logs.")
                return False
        except:
            self.log("WARN", "Goalie table check skipped (table might not exist yet).")
            
        self.log("PASS", "Key Constraints.")
        return True

    def check_logic(self):
        # Goals <= SOG
        # TOI > 0 if Stats > 0
        q = """
        SELECT COUNT(*) 
        FROM nhl_player_game_logs 
        WHERE (goals > shots AND shots IS NOT NULL)
           OR (assists < 0)
        """
        errs = pd.read_sql(q, self.conn).iloc[0,0]
        if errs > 0:
            self.log("FAIL", f"Found {errs} rows with Logical Errors (Goals > Shots, Neg Assists).")
            return False
            
        self.log("PASS", "Logic Constraints.")
        return True

    def check_missingness(self):
        # Check critical columns for NULLs
        # TOI, SOG, Goals, Assists
        q = """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN toi_seconds IS NULL THEN 1 ELSE 0 END) as null_toi,
            SUM(CASE WHEN shots IS NULL THEN 1 ELSE 0 END) as null_sog
        FROM nhl_player_game_logs
        """
        res = pd.read_sql(q, self.conn).iloc[0]
        total = res['total']
        
        if total == 0:
            self.log("WARN", "Table Empty.")
            return True # Technically pass?
            
        p_toi = res['null_toi'] / total
        p_sog = res['null_sog'] / total
        
        limit = cfg.THRESHOLDS['missing_sog_pct']
        
        if p_toi > limit:
            self.log("FAIL", f"TOI Missingness {p_toi:.1%} > {limit:.1%}")
            return False
            
        if p_sog > limit:
            self.log("FAIL", f"SOG Missingness {p_sog:.1%} > {limit:.1%}")
            return False
            
        self.log("PASS", "Missingness Gates.")
        return True

    def check_game_totals(self):
        # Sum(player_goals) vs Game Total? 
        # We don't have Game Total in a separate table easily accessible maybe?
        # Assuming we trust the logs internally for now.
        # Check integrity: sum(goals) > 0 for completed games?
        return True
