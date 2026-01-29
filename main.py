
"""
Philly P Sniper - Automated Sports Betting Intelligence System

Main orchestrator that coordinates all modules to identify profitable betting opportunities.
REFACTORED 2026-01-25: Moving to Pipeline Architecture.
UPDATED 2026-01-27: CLI Support for Targeted Runs (NHL V2 Reintegration).
"""

import requests
import pandas as pd
import joblib
import os
import pytz
import uuid
import argparse
from datetime import datetime, timedelta, timezone

from config.settings import Config
from utils.logging import log
from pipeline.orchestrator import PipelineOrchestrator, PipelineContext
from pipeline.stages import init, fetch, enrich, process, persist, notify, report

def run_sniper():
    """Main execution function that orchestrates the betting intelligence pipeline."""
    
    # CLI Parsing
    parser = argparse.ArgumentParser(description="Philly P Sniper Pipeline")
    parser.add_argument("--sports", type=str, default="ALL", help="Comma-separated list of sports (e.g. NHL,NBA) or ALL")
    parser.add_argument("--report-csv", type=str, default="false", help="Generate CSV artifacts (True/False)")
    parser.add_argument("--dry-run", type=str, default="false", help="Dry Run Mode (No Telegram)")
    args, _ = parser.parse_known_args()

    # Generate unique Run ID
    # Generate unique Run ID
    run_id = str(uuid.uuid4())[:8]
    log("INIT", f"Starting PhillyEdge Pipeline (Run ID: {run_id})...")

    # Dynamic Target Sports
    default_sports = ['NCAAB', 'NBA', 'NHL', 'NFL', 'EPL', 'LaLiga', 'Bundesliga', 'SerieA', 'Ligue1', 'ChampionsLeague']
    
    if args.sports.upper() != "ALL":
        # Targeted Run
        target_sports = [s.strip() for s in args.sports.split(',')]
        log("INIT", f"🎯 Targeted Run for: {target_sports}")
        
        # SAFETY: If NHL is explicitly requested, FORCE ENABLE
        if 'NHL' in target_sports or 'icehockey_nhl' in target_sports:
            log("INIT", "🏒 NHL Explicitly Requested -> Overriding SKIP_NHL safeguards.")
            os.environ['SKIP_NHL'] = "0"
            # Ensure V2 Enabled if configured
            if Config.NHL_TOTALS_V2_ENABLED:
                log("INIT", "🏒 NHL V2 Logic Active.")
    else:
        target_sports = default_sports

    # Initialize Context
    ctx = PipelineContext(
        run_id=run_id,
        target_sports=target_sports,
        config=Config
    )
    
    # Inject CLI Flags
    if args.report_csv.lower() == "true":
        ctx.report_csv = True
        
    if args.dry_run.lower() == "true":
        ctx.config.TELEGRAM_DRY_RUN = True
        log("INIT", "⚠️ DRY RUN MODE: Telegram alerts suppressed.")
    
    # Define Pipeline Stages
    stages = [
        init,     # DB & Config Check
        fetch,    # API Calls (Odds & Sharps)
        enrich,   # Ratings & News
        process,  # Betting Models
        persist,  # DB Write
        report,   # artifacts (New)
        notify    # Alerts
    ]
    
    # Execute Pipeline
    orchestrator = PipelineOrchestrator(stages)
    success = orchestrator.run(ctx)
    
    if success:
        # Check for Partial Failures (User Request: "Not successful if 0 ops and errors")
        if ctx.errors:
            log("MAIN", f"⚠️ Pipeline Completed with {len(ctx.errors)} Errors.")
            print("\n" + "="*60)
            print("❌ PIPELINE ERRORS DETECTED")
            print("="*60)
            for e in ctx.errors:
                print(f" - {e}")
            print("="*60 + "\n")
            
            if not ctx.opportunities:
                 log("MAIN", "❌ 0 Opportunities Found AND Errors Detected -> Marked as FAILURE.")
                 return # Exit without printing "Success"

        if not ctx.errors:
            log("MAIN", "✅ Pipeline Execution Successful.")
        
        # --- NEW BLOCK: PRETTY PRINT RECOMMENDATIONS ---
        if ctx.opportunities:
            df_ops = pd.DataFrame(ctx.opportunities)
            
            # Ensure edge_val is numeric
            if 'Edge_Val' in df_ops.columns:
                 df_ops['Edge_Val'] = pd.to_numeric(df_ops['Edge_Val'], errors='coerce').fillna(0)
            else:
                 df_ops['Edge_Val'] = 0.0

            # Filter: Recommendations Only (Edge > 0)
            df_recs = df_ops[df_ops['Edge_Val'] > 0].copy()
            
            print("\n" + "="*60)
            if not df_recs.empty:
                print(f"📊 RECOMMENDATIONS ({len(df_recs)} Found)")
                print("="*60)
                
                # Smart Column Selection
                desired_cols = ['Sport', 'Event', 'Selection', 'Dec_Odds', 'Edge_Val', 'Kickoff']
                final_cols = [c for c in desired_cols if c in df_recs.columns]
                
                # Fallback
                if not final_cols:
                    final_cols = df_recs.columns.tolist()
                    
                # Sort
                if 'Kickoff' in df_recs.columns:
                    df_recs = df_recs.sort_values('Kickoff')
                else:
                    df_recs = df_recs.sort_values('Edge_Val', ascending=False)
                    
                print(df_recs[final_cols].to_string(index=False))
            else:
                print("📊 RECOMMENDATIONS: None (No opportunities > 0 EV)")
                
            print("="*60 + "\n")
        else:
            if not ctx.errors:
                print("\n⚠️ Pipeline ran successfully but found 0 opportunities.\n")

    else:
        log("MAIN", "❌ Pipeline Execution Failed or Aborted.")
        
if __name__ == "__main__":
    run_sniper()
