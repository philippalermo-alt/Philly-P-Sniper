from pipeline.orchestrator import PipelineContext
from config.settings import Config
from utils.logging import log
import requests
from datetime import datetime, timedelta, timezone
from data.clients.action_network import get_action_network_data
from data.sources.nhl_goalies_lwl import fetch_lwl_goalies
from utils.team_names import normalize_team_name
import os

def execute(context: PipelineContext) -> bool:
    """
    Stage 2: Data Fetching
    """
    # 0. Fetch NHL Goalies (Phase 1.5)
    nhl_starters = {}
    if 'NHL' in context.target_sports:
        # Deconfliction Gate
        if os.getenv("SKIP_NHL", "0") == "1":
            log("FETCH", "⚠️ SKIP_NHL=1 set. Skipping NHL Goalie Fetch & Odds (will be skipped in loop).")
            # We also need to remove NHL from target_sports locally to avoid fetching odds?
            # Or just set a flag. 
            # If we leave it in target_sports, the loop below will fetch odds but have no starters.
            # Best to remove it from target_sports for this run context if we truly want to skip.
            if 'NHL' in context.target_sports:
                context.target_sports.remove('NHL')
        else:
            try:
                log("FETCH", "Retrieving NHL Starting Goalies (LeftWingLock)...")
                nhl_starters = fetch_lwl_goalies()
                if nhl_starters:
                    log("FETCH", f"✅ Loaded Starters for {len(nhl_starters)} Teams")
                else:
                    context.log_error("FETCH_GOALIES", "No Goalies Found (Offseason or Scraper Fail?)")
            except Exception as e:
                context.log_error("FETCH_GOALIES", str(e))

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
            # Fetch all PENDING bets to prevent duplicates/swaps in memory
            # CHANGED: Added 'teams' to query for Stable Deduplication
            context.db_cursor.execute("SELECT event_id, selection, edge, sport, teams FROM intelligence_log WHERE outcome='PENDING'")
            rows = context.db_cursor.fetchall()
            
            # Organize by Match ID (Prefix of event_id)
            # Schema: {match_id}_{selection_slug}
            
            count = 0
            for r in rows:
                eid, sel, edge, sp, teams_str = r
                
                # 1. Match ID Map (Optimization)
                parts = eid.split('_')
                if len(parts) > 1:
                    MID = parts[0] # OddsAPI ID
                    if MID not in context.existing_bets:
                        context.existing_bets[MID] = []
                    context.existing_bets[MID].append(r)
                    count += 1
                    
                # 2. Stable Signature (Robustness)
                # Handle MatchID changes or generic duplicates
                # Signature: "{teams_str} [{sel}]" -> "Duke @ UNC [Duke ML]"
                # Standardize spacing just in case
                if teams_str:
                    clean_teams = teams_str.strip()
                    clean_sel = sel.strip()
                    sig = f"{clean_teams} [{clean_sel}]"
                    context.seen_bet_signatures.add(sig)
            
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
            
            # 36-Hour Window (Strict)
            now_utc = datetime.now(timezone.utc)
            limit_time = now_utc + timedelta(hours=36)
            iso_limit = limit_time.replace(microsecond=0).isoformat().replace('+00:00', 'Z')
            iso_start = now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            url = f"https://api.the-odds-api.com/v4/sports/{league_key}/odds/?apiKey={Config.ODDS_API_KEY}&regions=us,us2&markets=h2h,spreads,totals&oddsFormat=decimal&commenceTimeFrom={iso_start}&commenceTimeTo={iso_limit}"
            res = requests.get(url, timeout=15)
            
            if res.status_code == 200:
                data = res.json()
                context.odds_data[sport] = data
                success_count += 1
                log("FETCH", f"✅ {sport}: {len(data)} Games Found")
                
                # INJECT GOALIES (NHL)
                if sport == 'NHL' and nhl_starters:
                    matched_g = 0
                    for game in data:
                        h = normalize_team_name(game.get('home_team'))
                        a = normalize_team_name(game.get('away_team'))
                        
                        h_info = nhl_starters.get(h)
                        a_info = nhl_starters.get(a)
                        
                        game['starters'] = {
                            'home_starter': h_info['starter'] if h_info else None,
                            'away_starter': a_info['starter'] if a_info else None,
                            'home_status': h_info['status'] if h_info else 'Unknown',
                            'away_status': a_info['status'] if a_info else 'Unknown'
                        }
                        
                        if h_info and a_info:
                             matched_g += 1
                             # log("FETCH", f"   🥅 Matched: {a_info['starter']} vs {h_info['starter']}")
                            
                    log("FETCH", f"   ✅ Associated Goalies for {matched_g}/{len(data)} games.")
                        
                # 3. Deep Detail Fetch (Soccer Totals via Alternates)
                if sport in ['ChampionsLeague', 'EuropaLeague']:
                    log("FETCH", f"   🔍 Fetching Deep Details (alternate_totals) for {len(data)} games...")
                    details_count = 0
                    for g in data:
                        try:
                            evt_id = g['id']
                            # Request alternate_totals
                            d_url = f"https://api.the-odds-api.com/v4/sports/{league_key}/events/{evt_id}/odds?apiKey={Config.ODDS_API_KEY}&regions=us&markets=alternate_totals&oddsFormat=decimal"
                            d_res = requests.get(d_url, timeout=5)
                            if d_res.status_code == 200:
                                d_data = d_res.json()
                                details_count += 1
                                # Merge Logic
                                for dbk in d_data.get('bookmakers', []):
                                    existing_bk = next((b for b in g['bookmakers'] if b['key'] == dbk['key']), None)
                                    if existing_bk:
                                        # Deduplicate markets by key? usually unique keys per bookie response
                                        # But let's just extend. markets.py deduplicates if needed.
                                        existing_bk['markets'].extend(dbk['markets'])
                                    else:
                                        g['bookmakers'].append(dbk)
                        except Exception as ex:
                             # Warning only, don't crash
                             pass
                    log("FETCH", f"   ✅ Merged Alternates for {details_count} games.")

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
        'NFL': 'americanfootball_nfl',
        'EPL': 'soccer_epl',
        'LaLiga': 'soccer_spain_la_liga',
        'Bundesliga': 'soccer_germany_bundesliga',
        'SerieA': 'soccer_italy_serie_a',
        'Ligue1': 'soccer_france_ligue_one',
        'ChampionsLeague': 'soccer_uefa_champs_league',
        'EuropaLeague': 'soccer_uefa_europa_league'
    }
    return idx.get(sport)
