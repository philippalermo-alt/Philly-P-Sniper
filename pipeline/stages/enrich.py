from pipeline.orchestrator import PipelineContext
from data.clients.ratings import get_team_ratings
from utils.logging import log
from nba_refs import get_nba_refs
from nhl_assignments import get_nhl_assignments
from utils.ref_mapping import build_ref_map

def execute(context: PipelineContext) -> bool:
    """
    Stage 3: Enrichment
    - Fetch Team Ratings (KenPom, etc)
    - Fetch Referee Data (Optional)
    - Fetch News Sentiment (Optional)
    """
    try:
        # 1. Team Ratings
        log("ENRICH", "Fetching Team Ratings...")
        ratings = get_team_ratings()
        if ratings:
            context.ratings = ratings
            log("ENRICH", f"✅ Loaded Ratings for {len(ratings)} teams")
        else:
            log("WARN", "Ratings Fetch Failed or Empty")
            # We don't abort, but downstream might skip games
            
        # 2. Referees / News
        log("ENRICH", "Fetching Referee Assignments...")
        
        # NBA
        try:
            nba_assignments = get_nba_refs()
            context.nba_refs = build_ref_map(nba_assignments, 'Game', '@')
            log("ENRICH", f"✅ Mapped NBA Refs for {len(context.nba_refs)//2} games")
        except Exception as e:
            log("WARN", f"NBA Ref Fetch Failed: {e}")
            context.nba_refs = {}

        # NHL
        try:
            nhl_assignments = get_nhl_assignments()
            context.nhl_refs = build_ref_map(nhl_assignments, 'Game', ' at ')
            log("ENRICH", f"✅ Mapped NHL Refs for {len(context.nhl_refs)//2} games")
        except Exception as e:
            log("WARN", f"NHL Ref Fetch Failed: {e}")
            context.nhl_refs = {}
        
        return True
        
    except Exception as e:
        context.log_error("ENRICH", str(e))
        return False # Should we abort? No, maybe partial success.
