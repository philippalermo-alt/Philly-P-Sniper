from pipeline.orchestrator import PipelineContext
from processing.markets import process_match, process_nhl_props
from utils.logging import log

def execute(context: PipelineContext) -> bool:
    """
    Stage 4: Processing
    - Iterate through fetched games
    - Apply Probability Models
    - Identify Opportunities
    """
    try:
        log("PROCESS", "Running Betting Models...")
        
        # We need to collect ALL opportunities into context.opportunities
        all_opps = []
        
        for sport, games in context.odds_data.items():
            log("PROCESS", f"Analyzing {sport} ({len(games)} games)...")
            
            seen_matches = set()
            
            for game in games:
                try:
                    # 1. Core Market Processing
                    # 1. Core Market Processing
                    all_opps.extend(process_match(
                        match=game,
                        ratings=context.ratings,
                        calibration=1.0,
                        target_sport=sport,
                        seen_matches=seen_matches,
                        sharp_data=context.sharp_data,
                        existing_bets_map=context.existing_bets
                    ))
                    
                    # 2. NHL Props Processing
                    if sport == 'NHL':
                        # Placeholder for Player Stats (To be implemented in Enrich stage later)
                        # Prevents crash but yields no props for now unless we fetch stats.
                        player_stats = {} 
                        all_opps.extend(process_nhl_props(
                            match=game,
                            props_data=None, # Not used currently in function signature in old code?
                            player_stats=player_stats, 
                            calibration=1.0,
                            seen_matches=seen_matches,
                            existing_bets_map=context.existing_bets
                        ))
                        
                except Exception as ex:
                    context.log_error(f"PROCESS_GAME_{game.get('id')}", str(ex))
                    
        context.opportunities = all_opps
        log("PROCESS", f"✅ Identified {len(all_opps)} Opportunities (Ops)")
        return True
        
    except Exception as e:
        context.log_error("PROCESS", str(e))
        return False
