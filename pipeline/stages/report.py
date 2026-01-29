from pipeline.orchestrator import PipelineContext
from config.settings import Config
from utils.logging import log
import pandas as pd
import os
from datetime import datetime

def execute(context: PipelineContext) -> bool:
    """
    Stage 6: Reporting (Optional)
    Generates CSV artifacts for debugging and KPI tracking.
    Triggered only if 'report_csv' is set in context or config.
    """
    # Check flag
    if not getattr(context, 'report_csv', False):
        return True

    log("REPORT", "Generating Analysis Artifacts...")
    
    today = datetime.now().strftime("%Y-%m-%d")
    

    # ---------------------------------------------------------
    # NHL TOTALS V2 ARTIFACTS
    # ---------------------------------------------------------
    if 'icehockey_nhl' in context.target_sports or 'NHL' in context.target_sports:
        # Check if we have V2 logic active
        if getattr(context.config, 'NHL_TOTALS_V2_ENABLED', False):
             _generate_nhl_artifacts(context, today)

    # ---------------------------------------------------------
    # NBA TOTALS V2 ARTIFACTS
    # ---------------------------------------------------------
    if 'NBA' in context.target_sports or 'basketball_nba' in context.target_sports:
        if getattr(context.config, 'ENABLE_NBA_V2', False):
             _generate_nba_artifacts(context, today)

    return True

def _generate_nhl_artifacts(context: PipelineContext, date_str: str):
    # Matches logic from scripts/ops/run_nhl_totals.py
    output_dir = f"predictions/nhl_totals_v2/{date_str}"
    
    # 1. Recommendations (Crucial for KPIs)
    if context.opportunities:
        # Filter for NHL only
        nhl_ops = [op for op in context.opportunities if op.get('Sport') == 'icehockey_nhl']
        
        if nhl_ops:
            os.makedirs(output_dir, exist_ok=True)
            df = pd.DataFrame(nhl_ops)
            out_path = f"{output_dir}/recommendations.csv"
            df.to_csv(out_path, index=False)
            log("REPORT", f"✅ Saved {len(df)} NHL recommendations to {out_path}")
            
    # 2. Raw Decision Trace (Audit)
    audit_log = context.metadata.get('nhl_audit_log', [])
    if audit_log:
        os.makedirs(output_dir, exist_ok=True)
        df_audit = pd.DataFrame(audit_log)
        
        # Ensure standard columns for debugging ease
        cols = [
            'game_id', 'date', 'home_team', 'away_team', 'commence_time',
            'total_line', 'over_price', 'under_price',
            'implied_over', 'implied_under',
            'expected_total', 'sigma', 'bias_applied',
            'prob_over', 'prob_under',
            'ev_over', 'ev_under',
            'bet_side', 'decision', 'reject_reasons'
        ]
        
        # Fill missing cols
        valid_cols = [c for c in cols if c in df_audit.columns]
        
        out_path_raw = f"{output_dir}/decisions_raw.csv"
        df_audit[valid_cols].to_csv(out_path_raw, index=False)
        log("REPORT", f"✅ Saved Raw Decisions Trace to {out_path_raw}")

    # 3. Moneyline Trace (Audit)
    ml_log = context.metadata.get('nhl_ml_audit_log', [])
    if ml_log:
        os.makedirs(output_dir, exist_ok=True)
        df_ml = pd.DataFrame(ml_log)
        out_path_ml = f"{output_dir}/decisions_moneyline_raw.csv"
        df_ml.to_csv(out_path_ml, index=False)
        log("REPORT", f"✅ Saved Moneyline Trace to {out_path_ml}")

def _generate_nba_artifacts(context: PipelineContext, date_str: str):
    output_dir = f"predictions/nba_model_v2/{date_str}"
    
    # 1. Recommendations
    if context.opportunities:
        nba_ops = [op for op in context.opportunities if op.get('Sport') == 'basketball_nba' or op.get('Sport') == 'NBA']
        
        if nba_ops:
            os.makedirs(output_dir, exist_ok=True)
            df = pd.DataFrame(nba_ops)
            out_path = f"{output_dir}/recommendations.csv"
            df.to_csv(out_path, index=False)
            log("REPORT", f"✅ Saved {len(df)} NBA recommendations to {out_path}")

    # 2. Audit Log (Predictions)
    # Context.nba_predictions contains the raw model output before filtering
    if hasattr(context, 'nba_predictions') and context.nba_predictions:
        os.makedirs(output_dir, exist_ok=True)
        df_preds = pd.DataFrame(context.nba_predictions)
        
        # Dump all cols for deeper analysis
        out_path_preds = f"{output_dir}/predictions.csv"
        df_preds.to_csv(out_path_preds, index=False)
        log("REPORT", f"✅ Saved {len(df_preds)} NBA Predictions to {out_path_preds}")
