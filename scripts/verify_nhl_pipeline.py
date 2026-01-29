import sys
import os
sys.path.append(os.getcwd())

from pipeline.orchestrator import PipelineContext
from pipeline.stages import fetch, process
from config.settings import Config
from utils.logging import log

def verify_nhl():
    print("🧪 Starting NHL V2 Verification Run (No DB)...")
    
    # 1. Setup Context
    ctx = PipelineContext(
        run_id="TEST_VERIFY",
        target_sports=['NHL'],
        config=Config
    )
    
    # 2. Run Fetch (Should scrape DFO)
    print("\n[STAGE: FETCH]")
    success_fetch = fetch.execute(ctx)
    if not success_fetch:
        print("❌ Fetch failed.")
        return
        
    print(f"✅ Fetch Complete. Odds data keys: {list(ctx.odds_data.keys())}")
    
    if 'NHL' in ctx.odds_data:
        nhl_games = ctx.odds_data['NHL']
        print(f"🏒 Parsed {len(nhl_games)} NHL Games.")
        for g in nhl_games[:3]: # Show first 3
            starters = g.get('starters', {})
            print(f"   - {g['away_team']} @ {g['home_team']}")
            print(f"     🥅 Starters: {starters.get('away_starter')} vs {starters.get('home_starter')}")
            print(f"     ✅ Status: {starters.get('away_status')} / {starters.get('home_status')}")
            
    # 3. Run Process (Should Run V2 Inference)
    print("\n[STAGE: PROCESS]")
    success_process = process.execute(ctx)
    
    print("\n[RESULTS]")
    nhl_opps = [op for op in ctx.opportunities if op.sport == 'NHL' or op.sport == 'NHL_PROP']
    print(f"Generated {len(nhl_opps)} NHL Opportunities.")
    
    for op in nhl_opps:
        print(f"💰 {op.selection} | Odds: {op.odds} | P(Win): {op.true_prob:.3f} | Edge: {op.edge*100:.1f}%")

if __name__ == "__main__":
    verify_nhl()
