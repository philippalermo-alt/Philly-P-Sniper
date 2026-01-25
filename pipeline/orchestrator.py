from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import time
import traceback
from datetime import datetime, timezone
from utils import log

# Dynamic Context to pass data between stages
@dataclass
class PipelineContext:
    run_id: str
    target_sports: List[str]
    config: Any = None
    
    # State
    db_conn: Any = None
    db_cursor: Any = None
    
    # Data Containers
    games_map: Dict[str, Any] = field(default_factory=dict) # MatchID -> MatchData
    odds_data: Dict[str, Any] = field(default_factory=dict) # Sport -> Odds
    ratings: Dict[str, Any] = field(default_factory=dict)
    sharp_data: Dict[str, Any] = field(default_factory=dict)
    pro_systems: Dict[str, Any] = field(default_factory=dict)
    
    # State Tracking (Atomic Writes support)
    existing_bets: Dict[str, List[Any]] = field(default_factory=dict) # MatchID -> List[(EventID, Selection, Edge)]
    
    # Results
    opportunities: List[Dict] = field(default_factory=list)
    
    # Error Tracking
    errors: List[str] = field(default_factory=list)
    partial_failures: Dict[str, str] = field(default_factory=dict) # Stage -> Error

    def log_error(self, stage: str, error: str):
        self.errors.append(f"[{stage}] {error}")
        self.partial_failures[stage] = error
        log("ERROR", f"Pipeline Error in {stage}: {error}")

class PipelineOrchestrator:
    def __init__(self, stages: List[Any]):
        self.stages = stages
        
    def run(self, context: PipelineContext) -> bool:
        """
        Execute the pipeline stages in order.
        Returns True if pipeline completed (even with partial failures), False if aborted.
        """
        log("PIPELINE", f"🚀 Starting Run {context.run_id}")
        start_time = time.time()
        
        try:
            for stage in self.stages:
                stage_name = stage.__name__.split('.')[-1].upper()
                log("PIPELINE", f"▶️  Stage: {stage_name}")
                
                try:
                    # Execute Stage
                    success = stage.execute(context)
                    
                    if not success:
                        # Logic: Should we abort? 
                        # INIT phase failures are fatal.
                        if stage_name == "INIT":
                            log("FATAL", "Pipeline Aborted at INIT.")
                            return False
                        else:
                            log("WARN", f"Stage {stage_name} reported failure/issue but continuing...")
                            
                except Exception as e:
                    err_msg = f"{str(e)}\n{traceback.format_exc()}"
                    context.log_error(stage_name, err_msg)
                    
                    # Critical Stages that abort the run
                    if stage_name in ["INIT", "PERSIST"]:
                        log("FATAL", f"Critical Failure in {stage_name}. Aborting.")
                        return False
                        
            duration = time.time() - start_time
            log("PIPELINE", f"✅ Run Complete in {duration:.2f}s. Errors: {len(context.errors)}")
            return True
            
        except Exception as e:
            log("FATAL", f"Unhanded Orchestrator Error: {e}")
            return False
        finally:
            # Ensure cleanup happens if possible? 
            # cleanup is usually a stage, if it wasn't reached, we might leak DB.
            # Ideally context.db_conn should be closed if orchestrator crashes.
            if context.db_conn:
                try:
                    context.db_conn.close()
                    log("DB", "Safety Close Connection")
                except:
                    pass
