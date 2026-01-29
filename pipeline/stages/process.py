from config.settings import Config
from utils.models.nhl_totals_v2 import NHLTotalsV2
from datetime import datetime
from pipeline.orchestrator import PipelineContext
from processing.markets import process_match, process_nhl_props, create_opportunity, calculate_kelly_stake
from utils.logging import log
from core.kelly import calculate_kelly_stake
from models.soccer import SoccerModelV2
from models.nba import NBAModel
from models.nhl import NHLModelV2
from processing.sharp_scoring import calculate_sharp_score
from utils.team_names import normalize_team_name
import difflib

# Instantiate Global Models
_soccer_model = SoccerModelV2()
_nba_model = NBAModel()
_nhl_model = NHLModelV2()
_nhl_totals = NHLTotalsV2()

def get_nhl_sharp_data_helper(game, sharp_data):
    """
    Helper to look up sharp data for an NHL match.
    Logic duplicated from processing/markets.py to ensure consistency
    without circular imports or complexity.
    """
    if not sharp_data:
        return None
        
    home = game.get('home_team')
    away = game.get('away_team')
    n_home = normalize_team_name(home)
    n_away = normalize_team_name(away)
    matched_key = None
    
    # 1. Containment Search
    for sk in sharp_data.keys():
        try:
            s_away, s_home = sk.split(' @ ')
        except:
            continue
        match_h = (s_home in n_home) or (n_home in s_home)
        match_a = (s_away in n_away) or (n_away in s_away)
        if match_h and match_a:
            matched_key = sk
            break
            
    # 2. Fallback
    if not matched_key:
        search_key = f"{n_away} @ {n_home}"
        m_match = difflib.get_close_matches(search_key, sharp_data.keys(), n=1, cutoff=0.85)
        if m_match:
            matched_key = m_match[0]
            
    return matched_key

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
            
            is_soccer = sport in ['EPL', 'LaLiga', 'Bundesliga', 'SerieA', 'Ligue1', 'ChampionsLeague', 'EuropaLeague']

            seen_matches = set()
            
            for game in games:
                try:
                    # predictions containers
                    s_preds = None
                    nba_preds = None
                    nhl_preds = None
                    
                    # ---------------------------
                    # SOCCER V2
                    # ---------------------------
                    if is_soccer and _soccer_model:
                        try:
                            p = _soccer_model.predict_match(
                                game.get('home_team'), 
                                game.get('away_team'), 
                                league_name=sport
                            )
                            if p:
                                key = f"{game.get('away_team')} @ {game.get('home_team')}"
                                s_preds = {key: p}
                        except Exception:
                            pass
                            
                    # ---------------------------
                    # NBA V2 (Pilot)
                    # ---------------------------
                    if sport == 'NBA' and _nba_model:
                        try:
                            cur_odds = {
                                'home_odds': game.get('home_odds', 2.0),
                                'away_odds': game.get('away_odds', 2.0)
                            }
                            p = _nba_model.predict_match(
                                game.get('id'),
                                game.get('home_team'),
                                game.get('away_team'),
                                game.get('commence_time'), 
                                cur_odds
                            )
                            if p:
                                key = f"{game.get('away_team')} @ {game.get('home_team')}"
                                nba_preds = {key: p}
                        except Exception:
                            pass

                    # ---------------------------
                    # NHL V2 (AUTHORITATIVE)
                    # ---------------------------
                    if sport == 'NHL':
                        # STRICT PROOF: Gate Mechanism to prevent Double-Run (Cron vs Systemd)
                        import os
                        if os.environ.get("SKIP_NHL") == "1":
                            if 'NHL_SKIPPED_LOG' not in context.metadata:
                                log("PROCESS", "SKIP_NHL=1 -> NHL pipelines disabled in hourly run")
                                context.metadata['NHL_SKIPPED_LOG'] = True
                            continue

                        # 1. Moneyline V2
                        if _nhl_model:
                            if 'nhl_ml_audit_log' not in context.metadata:
                                context.metadata['nhl_ml_audit_log'] = []
                                
                            try:
                                starters = game.get('starters', {})
                                h_start = starters.get('home_starter')
                                a_start = starters.get('away_starter')
                                
                                # Extract H2H Odds
                                bm = game.get('bookmakers', [])
                                h_price, a_price = None, None
                                
                                # Heuristic: Use first bookmaker with h2h
                                for b in bm:
                                    for m in b.get('markets', []):
                                        if m['key'] == 'h2h':
                                            outcomes = m.get('outcomes', [])
                                            h_out = next((x for x in outcomes if x['name'] == game.get('home_team')), None)
                                            a_out = next((x for x in outcomes if x['name'] == game.get('away_team')), None)
                                            if h_out and a_out:
                                                h_price = h_out['price']
                                                a_price = a_out['price']
                                                break
                                    if h_price: break
                                
                                commence = game.get('commence_time')
                                date_str = commence[:10] if commence else None

                                p = _nhl_model.predict_match(
                                    game.get('home_team'),
                                    game.get('away_team'),
                                    home_starter=h_start, 
                                    away_starter=a_start,
                                    home_dec_odds=h_price,
                                    away_dec_odds=a_price,
                                    date_str=date_str
                                )
                                
                                if p:
                                    # Audit Log
                                    p['game_id'] = game.get('id')
                                    context.metadata['nhl_ml_audit_log'].append(p)
                                    
                                    key = f"{game.get('away_team')} @ {game.get('home_team')}"
                                    nhl_preds = {key: p}
                            except Exception as ex:
                                pass
                        
                        # 2. Totals V2 (Phase 6 - Configured)
                        if _nhl_totals:
                            if Config.NHL_TOTALS_V2_ENABLED:
                                # PROOF HOOK (Run once per batch or per game? Per Game is fine for logs, but we want one global line preferably.
                                # But here we are inside a loop.
                                # Let's log it on the first NHL game processed.
                                if 'NHL_V2_PROOF' not in context.metadata:
                                    log("PROOF", f"NHL_TOTALS_V2_ACTIVE model=ElasticNet sigma={_nhl_totals.SIGMA} bias={_nhl_totals.BIAS} features=nhl_totals_features_v1")
                                    context.metadata['NHL_V2_PROOF'] = True
                                    
                                try:
                                    # Extract Totals Odds (Best/First available)
                                    # Assuming 'bookmakers' structure in 'game'
                                    bm = game.get('bookmakers', [])
                                    line, o_price, u_price = None, None, None
                                    
                                    # Heuristic: Use first bookmaker with totals
                                    for b in bm:
                                        for m in b.get('markets', []):
                                            if m['key'] == 'totals':
                                                outcomes = m.get('outcomes', [])
                                                if len(outcomes) == 2:
                                                    o = next((x for x in outcomes if x['name'] == 'Over'), None)
                                                    u = next((x for x in outcomes if x['name'] == 'Under'), None)
                                                    if o and u and o.get('point') == u.get('point'):
                                                        line = o['point']
                                                        o_price = o['price']
                                                        u_price = u['price']
                                                        break
                                        if line: break
                                    
                                    if line:
                                        commence = game.get('commence_time')
                                        # Convert commence to date string for Lookup
                                        # "2023-10-12T23:00:00Z" -> "2023-10-12"
                                        # Assuming ISO format
                                        date_str = commence[:10] if commence else None
                                        
                                        # Initialize Audit Log
                                        if 'nhl_audit_log' not in context.metadata:
                                            context.metadata['nhl_audit_log'] = []

                                        t_res = _nhl_totals.predict(
                                            game.get('home_team'),
                                            game.get('away_team'),
                                            line, o_price, u_price,
                                            date_str
                                        )
                                        
                                        # Log Trace
                                        if t_res:
                                            # Inject Identifiers for joining
                                            t_res['game_id'] = game.get('id')
                                            t_res['commence_time'] = commence
                                            context.metadata['nhl_audit_log'].append(t_res)
                                        
                                        if t_res and t_res.get('recommendation'):
                                            logger_msg = f"NHL Totals V2 REC: {t_res['recommendation']} {line} @ {t_res['bet_side'] == 'OVER' and o_price or u_price} (EV: {t_res['ev']:.2%})"
                                            log("NHL_TOTALS", logger_msg)
                                            
                                            # Capture Opportunity (Standardized Dataclass)
                                            # ID Format Parity with Ops: {game_id}_totals_{side}
                                            side_lower = t_res['bet_side'].lower()
                                            uid = f"{game.get('id')}_totals_{side_lower}"
                                            
                                            # Calculate Stake (using V2 Edge)
                                            stake_val = calculate_kelly_stake(t_res['ev'], o_price if t_res['bet_side'] == 'OVER' else u_price)
                                            
                                            # Lookup Sharp Data
                                            sharp_score_val = 0
                                            m_pct = None
                                            t_pct = None
                                            
                                            try:
                                                matched_key = get_nhl_sharp_data_helper(game, context.sharp_data)
                                                if matched_key:
                                                    # Get split for the specific side (Over/Under)
                                                    side_key = t_res['bet_side'].capitalize() # "Over"/"Under"
                                                    split = context.sharp_data.get(matched_key, {}).get("total", {}).get(side_key)
                                                    if split:
                                                        m_pct = split.get("money")
                                                        t_pct = split.get("tickets")
                                                        if m_pct is not None and t_pct is not None:
                                                            sharp_score_val = calculate_sharp_score(m_pct, t_pct)
                                            except Exception as e:
                                                log("WARN", f"NHL Sharp Lookup Failed: {e}")

                                            opp = create_opportunity(
                                                event_id=uid,
                                                timestamp=datetime.now(),
                                                kickoff=datetime.fromisoformat(commence.replace('Z', '+00:00')),
                                                sport='icehockey_nhl',
                                                teams=f"{game.get('away_team')} @ {game.get('home_team')}",
                                                selection=f"{t_res['recommendation']} {line}", # Updated to include line
                                                odds=o_price if t_res['bet_side'] == 'OVER' else u_price,
                                                true_prob=t_res['prob_over'] if t_res['bet_side'] == 'OVER' else t_res['prob_under'],
                                                edge=t_res['ev'],
                                                stake=stake_val,
                                                trigger_type='model_nhl_v2',
                                                sharp_score=sharp_score_val,
                                                ticket_pct=t_pct,
                                                money_pct=m_pct,
                                                metadata=t_res
                                            )
                                            # Explicit Overwrite for Consistency
                                            opp.unique_id = uid 
                                            
                                            all_opps.append(opp)
                                            
                                except Exception as ex:
                                    log("NHL_TOTALS", f"Error: {ex}")

                            else:
                                if 'NHL_DISABLED_PROOF' not in context.metadata:
                                    log("PROOF", "NHL Totals disabled (V2 flag off)")
                                    context.metadata['NHL_DISABLED_PROOF'] = True

                    # 1. Core Market Processing
                    # NOW INCLUDES NHL PREDS
                    combined_preds = s_preds or nba_preds or nhl_preds
                    
                    if sport == 'NHL' and not combined_preds:
                        # STRICT MODE: If V2 failed, do NOT run process_match with legacy fallback.
                        # process_match will return [] if no ratings/stats, but let's be explicit.
                        # We continue loop to skip legacy processing.
                        continue

                    all_opps.extend(process_match(
                        match=game,
                        ratings=context.ratings,
                        calibration=1.0,
                        target_sport=sport,
                        seen_matches=seen_matches,
                        sharp_data=context.sharp_data,
                        existing_bets_map=context.existing_bets,
                        is_soccer=is_soccer,
                        predictions=combined_preds,
                        seen_bet_signatures=context.seen_bet_signatures
                    ))
                    
                    # 2. NHL Props Processing
                    # Only if we have a match processed? Or separate?
                    if sport == 'NHL':
                         # Keep Props Logic? Prop logic uses Poisson on player stats.
                         # This is separate from V2 ML model.
                         # User said "NHL V2 is the only NHL model allowed".
                         # Does this apply to Props?
                         # Usually Props are distinct. I will leave Props active for now 
                         # as they don't conflict with ML.
                        player_stats = {} 
                        all_opps.extend(process_nhl_props(
                            match=game,
                            props_data=None, 
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
