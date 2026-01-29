import sys
import os
import logging
from unittest.mock import MagicMock

# Add root
sys.path.append(os.getcwd())

from config.settings import Config
from pipeline.orchestrator import PipelineContext
from pipeline.stages import process

# Setup Logging to Stdout for Capture
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(message)s')

def run_proof():
    print(f"--- PROOF RUN: NHL_TOTALS_V2_ENABLED={Config.NHL_TOTALS_V2_ENABLED} ---")
    
    # Mock Data
    mock_game = {
        'id': 'mock_1',
        'sport_key': 'icehockey_nhl',
        'home_team': 'Philadelphia Flyers',
        'away_team': 'New York Rangers',
        'commence_time': '2026-01-27T19:00:00Z',
        'bookmakers': [
            {
                'key': 'draftkings',
                'markets': [
                    {
                        'key': 'totals',
                        'outcomes': [
                            {'name': 'Over', 'point': 6.5, 'price': 2.00},
                            {'name': 'Under', 'point': 6.5, 'price': 1.80}
                        ]
                    }
                ]
            }
        ],
        'home_stats': {}, # needed?
        'away_stats': {}
    }
    
    # Mock Context
    ctx = MagicMock(spec=PipelineContext)
    ctx.run_id = "PROOF_RUN"
    ctx.odds_data = {'NHL': [mock_game]}
    ctx.opportunities = []
    ctx.metadata = {}
    ctx.errors = []
    
    # Execute Process Stage
    process.execute(ctx)
    
    print("--- PROOF COMPLETE ---\n")

if __name__ == "__main__":
    run_proof()
