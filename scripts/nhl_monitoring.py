
import pandas as pd
import numpy as np
from db.connection import get_db
import scripts.nhl_ops_config as cfg
from datetime import datetime

class NHLMonitor:
    def __init__(self, lookback_days=30):
        self.lookback = lookback_days
        self.conn = get_db()
        self.alerts = []
        
    def run(self):
        print("📊 Starting Monitoring Report...")
        
        # 1. Load Projections (Historical/Test Set)
        # In Prod, we would load from daily archive. 
        # For now, using Phase 4 output which covers the test period.
        path = cfg.ARTIFACTS['points'] 
        print(f"  Loading projections from {path}")
        df_proj = pd.read_csv(path)
        
        # 2. Get Actuals
        print("  Fetching Actual Results...")
        # Sort out dates
        dates = pd.to_datetime(df_proj['game_date']).dt.strftime('%Y-%m-%d').unique()
        if len(dates) == 0:
            print("  No dates found.")
            return

        min_date = min(dates)
        max_date = max(dates)
        
        q = f"""
        SELECT player_name, game_date, goals, assists, shots, (goals + assists) as points
        FROM nhl_player_game_logs
        WHERE game_date >= '{min_date}' AND game_date <= '{max_date}'
        """
        df_act = pd.read_sql(q, self.conn)
        # Ensure date string format matches
        df_act['game_date'] = pd.to_datetime(df_act['game_date']).dt.strftime('%Y-%m-%d')
        df_proj['game_date'] = pd.to_datetime(df_proj['game_date']).dt.strftime('%Y-%m-%d')
        
        # 3. Join
        # Key: player_name, game_date
        df = pd.merge(df_proj, df_act, on=['player_name', 'game_date'], how='inner')
        print(f"  Matched {len(df)} player-games.")
        
        # 4. Check Calibration (Points)
        self.check_calibration(df, 'proj_points_mean', 'points', 'Points Mean')
        self.check_prob_calibration(df, 'prob_points_1plus', 'points', 1, 'Points 1+')
        
        # 5. Check Tiers
        self.check_tiers(df)
        
        # 6. Report Alerts
        if self.alerts:
            print("\n🚨 ALERTS TRIGGERED:")
            for a in self.alerts:
                print(f"  - {a}")
        else:
            print("\n✅ System Healthy. No Drift Detected.")

    def check_calibration(self, df, pred_col, act_col, label):
        mae = (df[pred_col] - df[act_col]).abs().mean()
        bias = (df[pred_col] - df[act_col]).mean()
        print(f"\n[{label}] MAE: {mae:.3f}, Bias: {bias:.3f}")
        
        if abs(bias) > cfg.DRIFT_THRESHOLDS['calibration_mae']:
            self.alerts.append(f"{label} Bias {bias:.3f} exceeds threshold {cfg.DRIFT_THRESHOLDS['calibration_mae']}")

    def check_prob_calibration(self, df, prob_col, act_col, threshold, label):
        # Buckets: 0-0.2, 0.2-0.4, ...
        df['bucket'] = pd.cut(df[prob_col], bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0])
        df['target'] = (df[act_col] >= threshold).astype(int)
        
        calib = df.groupby('bucket')[['target', prob_col]].mean()
        calib['diff'] = calib[prob_col] - calib['target']
        print(f"\n[{label}] Calibration:")
        print(calib)
        
        # Check specific buckets for large drift
        for idx, row in calib.iterrows():
            if abs(row['diff']) > 0.05: # 5% tolerance per bucket
                print(f"  ⚠️ Warning: Bucket {idx} drift {row['diff']:.1%} (Pred {row[prob_col]:.2f} vs Act {row['target']:.2f})")

    def check_tiers(self, df):
        # Bias by Tier
        print("\n[Tiers] Bias:")
        grp = df.groupby('tier')[['proj_points_mean', 'points']].mean()
        grp['bias'] = grp['proj_points_mean'] - grp['points']
        print(grp)
        
        # Alert if Tier B/A drift > 3%
        if 'bias' in grp.columns:
            for t in ['A', 'B']:
                if t in grp.index and abs(grp.loc[t, 'bias']) > 0.05: # 5% tolerance
                    self.alerts.append(f"Tier {t} Bias {grp.loc[t, 'bias']:.3f} High")

if __name__ == "__main__":
    monitor = NHLMonitor()
    monitor.run()
