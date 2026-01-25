from pipeline.orchestrator import PipelineContext
from config.settings import Config
from utils.logging import log
import requests
from data.clients.action_network import get_action_network_data

def execute(context: PipelineContext) -> bool:
    """
    Stage 2: Data Fetching
    - Fetch Odds from OddsAPI
    - Fetch Sharp Data (Splits)
    """
    # 1. Fetch Sharp Data (Action Network)
    # We do this first as it maps to matches
    try:
        log("FETCH", "Retrieving Sharp Money Splits...")
        splits = get_action_network_data()
        if splits:
            context.sharp_data = splits
            log("FETCH", f"✅ Loaded {len(splits)} Sharp Records")
        else:
            log("WARN", "Sharp Data Unavailable (or empty)")
    except Exception as e:
        context.log_error("FETCH_SHARP", str(e)) # Non-fatal

    # 1.5 Fetch Active Bets (for Atomic Conflict Checking)
    try:
        log("FETCH", "Loading Active Pending Bets...")
        if context.db_cursor:
            # Fetch all PENDING bets to prevent duplicates/swaps in memory
            context.db_cursor.execute("SELECT event_id, selection, edge, sport FROM intelligence_log WHERE outcome='PENDING'")
            rows = context.db_cursor.fetchall()
            
            # Organize by Match ID (Prefix of event_id)
            # Schema: {match_id}_{selection_slug}
            # We assume match_id is the first part before the first underscore? 
            # CAUTION: OddsAPI IDs are usually alphanumeric. Selections might have underscores.
            # But we generated event_id as f"{match['id']}_{sel}".
            # So if we map: match['id'] -> bets, we need to extract match['id'].
            # Simpler: Just pass the whole list? No, optimized map.
            # Let's assume match['id'] is correct.
            
            count = 0
            for r in rows:
                eid, sel, edge, sp = r
                # Heuristic: Match ID is first segment?
                # OddsAPI IDs are typically like "42839482..." (no underscores).
                # But some legacy IDs might be "TeamA_vs_TeamB...".
                # Let's try to match existing logic.
                # If we can't easily parse, we stash by full event_id too?
                
                parts = eid.split('_')
                if len(parts) > 1:
                    MID = parts[0] # OddsAPI ID
                    if MID not in context.existing_bets:
                        context.existing_bets[MID] = []
                    context.existing_bets[MID].append(r)
                    count += 1
            
            log("FETCH", f"✅ Loaded {count} Active Bets across {len(context.existing_bets)} Matches")
            
    except Exception as e:
        context.log_error("FETCH_BETS", str(e))

    # 2. Fetch Odds per Sport
    success_count = 0
    for sport in context.target_sports:
        try:
            # Determine League Key from Config mapping or direct usage
            # Assuming sport is like 'NBA', 'NCAAB', 'NHL'
            league_key = _map_sport_to_key(sport)
            if not league_key: continue
            
            log("FETCH", f"Fetching Odds for {sport} ({league_key})...")
            
            url = f"https://api.the-odds-api.com/v4/sports/{league_key}/odds/?apiKey={Config.ODDS_API_KEY}&regions=us,us2&markets=h2h,spreads,totals&oddsFormat=decimal"
            res = requests.get(url, timeout=15)
            
            if res.status_code == 200:
                data = res.json()
                context.odds_data[sport] = data
                success_count += 1
                log("FETCH", f"✅ {sport}: {len(data)} Games Found")
            else:
                log("WARN", f"Failed to fetch {sport}: {res.status_code}")
                
        except Exception as e:
            context.log_error(f"FETCH_{sport}", str(e))
            
    if success_count == 0:
        context.log_error("FETCH", "No odds data fetched for any sport.")
        return False
        
    return True

def _map_sport_to_key(sport):
    idx = {
        'NBA': 'basketball_nba',
        'NCAAB': 'basketball_ncaab',
        'NHL': 'icehockey_nhl',
        'NFL': 'americanfootball_nfl'
    }
    return idx.get(sport)
