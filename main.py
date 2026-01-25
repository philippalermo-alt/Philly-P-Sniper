
"""
Philly P Sniper - Automated Sports Betting Intelligence System

Main orchestrator that coordinates all modules to identify profitable betting opportunities.
REFACTORED 2026-01-25: Moving to Pipeline Architecture.
"""

import requests
import pandas as pd
import joblib
import os
import pytz
import uuid
from datetime import datetime, timedelta, timezone

from config.settings import Config
from utils.logging import log
from pipeline.orchestrator import PipelineOrchestrator, PipelineContext
from pipeline.stages import init, fetch, enrich, process, persist, notify

def run_sniper():
    """Main execution function that orchestrates the betting intelligence pipeline."""
    
    # Generate unique Run ID
    run_id = str(uuid.uuid4())[:8]
    log("INIT", f"Starting PhillyEdge Pipeline (Run ID: {run_id})...")

    # Define Target Sports
    # Dynamic based on date? For now, include active winter sports.
    # Could be moved to Config or Stage Init.
    target_sports = ['NCAAB', 'NBA', 'NHL', 'NFL'] 

    # Initialize Context
    ctx = PipelineContext(
        run_id=run_id,
        target_sports=target_sports,
        config=Config
    )
    
    # Define Pipeline Stages
    stages = [
        init,     # DB & Config Check
        fetch,    # API Calls (Odds & Sharps)
        enrich,   # Ratings & News
        process,  # Betting Models
        persist,  # DB Write
        notify    # Alerts
    ]
    
    # Execute Pipeline
    orchestrator = PipelineOrchestrator(stages)
    success = orchestrator.run(ctx)
    
    if success:
        log("MAIN", "✅ Pipeline Execution Successful.")
    else:
        log("MAIN", "❌ Pipeline Execution Failed or Aborted.")
        
if __name__ == "__main__":
    run_sniper()
