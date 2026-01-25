from pipeline.orchestrator import PipelineContext
from notifications.notifier import send_alert, format_opportunity
from utils.logging import log

def execute(context: PipelineContext) -> bool:
    """
    Stage 6: Notification
    - Send Alerts for High Value Opportunities
    """
    try:
        opps = context.opportunities
        if not opps:
            return True
            
        log("NOTIFY", f"Processing Alerts for {len(opps)} opportunities...")
        
        # Filter for high value
        for opp in opps:
            # Re-implement alert logic here or rely on legacy?
            # Legacy logic often sent alerts inside process_markets or separate notifier loop.
            # Here we can centralize it.
            # Check Trigger Type?
            pass 
            
        # For now, just log summary
        if len(opps) > 0:
            print(f"🚀 [NOTIFY] Pipeline found {len(opps)} bets.")
            
        return True
        
    except Exception as e:
        context.log_error("NOTIFY", str(e))
        return True # Non-fatal
