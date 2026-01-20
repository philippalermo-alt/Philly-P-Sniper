import difflib
from datetime import datetime, timezone
from scipy import stats
from config import Config
from utils import log, _num
from database import safe_execute
from smart_staking import calculate_smart_stake, get_performance_multipliers

# One-time debug counters for calculate_match_stats TypeErrors
_calc_stats_typeerror_count = 0
_calc_stats_typeerror_max = 5

def calculate_match_stats(home, away, ratings, target_sport):
    """
    Calculate expected margin, total, and standard deviation for a match.

    Args:
        home: Home team name
        away: Away team name
        ratings: Dictionary of team ratings
        target_sport: Target sport for calculations

    Returns:
        tuple: (margin, total, std_dev, sport) or (None, None, None, None) on error
    """
    global _calc_stats_typeerror_count, _calc_stats_typeerror_max

    home_r = ratings.get(home)
    if not home_r:
        m = difflib.get_close_matches(home, ratings.keys(), n=1, cutoff=0.75)
        if m:
            home_r = ratings[m[0]]

    away_r = ratings.get(away)
    if not away_r:
        m = difflib.get_close_matches(away, ratings.keys(), n=1, cutoff=0.75)
        if m:
            away_r = ratings[m[0]]

    if not home_r:
        home_r = {
            'offensive_eff': 110.0, 'defensive_eff': 110.0, 'tempo': 70.0,
            'sport': target_sport, 'league_avg_goals': 3.0, 'attack': 1.0, 'defense': 1.0
        }
    if not away_r:
        away_r = {
            'offensive_eff': 110.0, 'defensive_eff': 110.0, 'tempo': 70.0,
            'sport': target_sport, 'league_avg_goals': 3.0, 'attack': 1.0, 'defense': 1.0
        }

    if home_r.get('sport') != target_sport:
        return None, None, None, None
    sport = target_sport

    try:
        if sport == 'NFL':
            h_off_ypp = _num(home_r.get('off_ypp'), 5.0)
            h_def_ypp = _num(home_r.get('def_ypp'), 5.0)
            a_off_ypp = _num(away_r.get('off_ypp'), 5.0)
            a_def_ypp = _num(away_r.get('def_ypp'), 5.0)
            home_net = h_off_ypp - h_def_ypp
            away_net = a_off_ypp - a_def_ypp
            margin = ((home_net - away_net) * 4.5) + 2.0

            h_off_ppg = _num(home_r.get('off_ppg'), 20.0)
            h_def_ppg = _num(home_r.get('def_ppg'), 20.0)
            a_off_ppg = _num(away_r.get('off_ppg'), 20.0)
            a_def_ppg = _num(away_r.get('def_ppg'), 20.0)
            home_proj = (h_off_ppg + a_def_ppg) / 2
            away_proj = (a_off_ppg + h_def_ppg) / 2
            total = home_proj + away_proj
            return margin, total, Config.NFL_MARGIN_STD, sport

        if sport == 'NHL':
            avg_goals = _num(home_r.get('league_avg_goals'), 3.0)
            home_att = _num(home_r.get('attack'), 1.0)
            home_def = _num(home_r.get('defense'), 1.0)
            away_att = _num(away_r.get('attack'), 1.0)
            away_def = _num(away_r.get('defense'), 1.0)
            home_exp = home_att * away_def * avg_goals
            away_exp = away_att * home_def * avg_goals
            home_exp += 0.2
            return (home_exp - away_exp), (home_exp + away_exp), Config.NHL_MARGIN_STD, sport

        avg_tempo = (_num(home_r.get('tempo'), 70.0) + _num(away_r.get('tempo'), 70.0)) / 2
        poss = avg_tempo / 100
        baseline = 118.0 if sport == 'NBA' else 105.0
        home_exp_pts = (_num(home_r.get('offensive_eff'), baseline) - (_num(away_r.get('defensive_eff'), baseline) - baseline)) * poss
        away_exp_pts = (_num(away_r.get('offensive_eff'), baseline) - (_num(home_r.get('defensive_eff'), baseline) - baseline)) * poss

        home_court = 3.5 if sport == 'NCAAB' else 2.5
        margin = (home_exp_pts - away_exp_pts) + home_court
        total = home_exp_pts + away_exp_pts
        std = Config.NCAAB_MARGIN_STD if sport == 'NCAAB' else Config.NBA_MARGIN_STD
        return margin, total, std, sport

    except TypeError as e:
        _calc_stats_typeerror_count += 1
        if _calc_stats_typeerror_count <= _calc_stats_typeerror_max:
            log("ERROR", f"calculate_match_stats TypeError #{_calc_stats_typeerror_count} for {home} vs {away} ({sport}): {e}")
            try:
                log("ERROR", f"home_r keys: {list(home_r.keys())}, away_r keys: {list(away_r.keys())}")
                sample_info = {
                    'home_off': home_r.get('offensive_eff'),
                    'home_def': home_r.get('defensive_eff'),
                    'home_tempo': home_r.get('tempo'),
                    'away_off': away_r.get('offensive_eff'),
                    'away_def': away_r.get('defensive_eff'),
                    'away_tempo': away_r.get('tempo'),
                }
                log("ERROR", f"sample values: {sample_info}")
            except Exception:
                pass
        else:
            log("ERROR", f"calculate_match_stats TypeError for {home} vs {away} ({sport}); further details suppressed.")
        return None, None, None, None
    except Exception as e:
        log("ERROR", f"calculate_match_stats unexpected error for {home} vs {away} ({sport}): {e}")
        return None, None, None, None

def calculate_kelly_stake(edge, decimal_odds, sport=None, use_smart_staking=True, multipliers=None):
    """
    Calculate Kelly Criterion stake size with optional smart staking adjustments.

    Args:
        edge: Edge value (positive expected value)
        decimal_odds: Decimal odds
        sport: Sport category (for smart staking)
        use_smart_staking: Whether to apply performance-based adjustments
        multipliers: Pre-calculated multipliers (optional, will fetch if needed)

    Returns:
        float: Recommended stake amount
    """
    if edge <= 0:
        return 0.0

    b = decimal_odds - 1
    p = (edge + 1) / decimal_odds
    q = 1 - p

    f_star = (b * p - q) / b
    base_stake = f_star * Config.KELLY_FRAC * Config.BANKROLL
    max_stake = Config.BANKROLL * Config.MAX_STAKE_PCT

    base_stake = min(base_stake, max_stake)

    # Apply smart staking if enabled and sport is provided
    if use_smart_staking and sport:
        return calculate_smart_stake(base_stake, sport, edge, multipliers)

    return base_stake

    return base_stake


def process_nhl_props(match, props_data, player_stats, calibration, cur, all_opps, seen_matches):
    """
    Process NHL player props (specifically Shots on Goal).
    """
    now_utc = datetime.now(timezone.utc)
    mdt = datetime.fromisoformat(match['commence_time'].replace('Z', '+00:00'))
    if mdt < now_utc:
        return

    home, away = match['home_team'], match['away_team']
    
    # Iterate through Bookmakers
    bookie = next((b for b in match.get('bookmakers', []) if b['key'] in Config.PREFERRED_BOOKS), None)
    if not bookie:
        return

    prop_id = f"{match['id']}_props"
    if prop_id in seen_matches:
        return
    seen_matches.add(prop_id)

    # DEBUG: Log available bookies
    available_keys = [b['key'] for b in match.get('bookmakers', [])]
    print(f"   🔍 [DEBUG-PROP] {match.get('home_team')} vs {match.get('away_team')} | Bookies: {available_keys}")

    bookie = next((b for b in match.get('bookmakers', []) if b['key'] in Config.PREFERRED_BOOKS), None)
    if not bookie:
        print(f"   ⚠️ [DEBUG-PROP] No preferred bookie found. (Preferred: {Config.PREFERRED_BOOKS})")
        return
    
    # Trace selected bookie
    print(f"   ✅ [DEBUG-PROP] Using Bookie: {bookie['key']}")

    for market in bookie['markets']:
        # LOG MARKET
        print(f"   ℹ️ [DEBUG-PROP] Checking market: {market['key']}", flush=True)
        if market['key'] != 'player_shots_on_goal':
            continue

        outcomes = market.get('outcomes', [])
        print(f"   ℹ️ [DEBUG-PROP] Outcome Count: {len(outcomes)}", flush=True)

        for outcome in outcomes:
            # Robust Name Matching
            raw_name = outcome.get('name', '')
            raw_desc = outcome.get('description', '')
            price = outcome.get('price')
            point = outcome.get('point')
            
            # LOG OUTCOME - Debugging flow
            print(f"   ℹ️ [DEBUG-PROP] Processing: {raw_name} | {raw_desc} | Pt:{point}", flush=True)

            if raw_name in ['Over', 'Under'] and raw_desc:
                player_name_odds = raw_desc
                description = raw_name
            else:
                player_name_odds = raw_name
                description = raw_desc

            if not point or not price or not description:
                print(f"   ⚠️ [DEBUG-PROP] SKIPPED due to missing data. Point:{point} Price:{price} Desc:{description}", flush=True)
                continue
            
            # 1. Fuzzy Match
            best_match = difflib.get_close_matches(player_name_odds, player_stats.keys(), n=1, cutoff=0.85)
            if not best_match:
                print(f"   ❌ [DEBUG-PROP] No name match for: {player_name_odds}", flush=True)
                continue
            
            print(f"   ✅ [DEBUG-PROP] Matched: {player_name_odds} -> {best_match[0]}", flush=True)
                
            p_stats = player_stats[best_match[0]]
            
            # Simple Projection Model
            # Project SOG = Average Shots/Game
            avg_sog = p_stats.get('avg_shots', 0)
            if avg_sog == 0:
                continue
                
            # Poisson Probability
            # Probability of getting > point (if Over) or < point (if Under)
            # given mean = avg_sog
            
            # stats.poisson.cdf(k, mu) = prob of <= k events
            # Over X.5 -> Prob(>= X+1) = 1 - cdf(X, mu) -> actually 1 - cdf(floor(point), mu)
            # Under X.5 -> Prob(<= X) = cdf(floor(point), mu)
            
            mu = avg_sog
            line = point
            
            if description == 'Over':
                # P(X > line) = 1 - P(X <= line)
                # Since lines are usually x.5, floor(line) gives the integer threshold
                # e.g. Over 2.5 -> P(X >= 3) -> 1 - P(X <= 2)
                prob = 1 - stats.poisson.cdf(int(line), mu)
                sel = f"{player_name_odds} Over {line} SOG"
            else: # Under
                # P(X < line) -> P(X <= line)
                # e.g. Under 2.5 -> P(X <= 2)
                prob = stats.poisson.cdf(int(line), mu)
                sel = f"{player_name_odds} Under {line} SOG"
                
            # Edge Calculation
            # Conservative calibration for props
            true_prob = prob * calibration
            true_prob = min(true_prob, 0.85) # Cap max confidence
            
            implied_prob = 1 / price
            # Standard Kelly formulation
            edge = (true_prob * price) - 1
            
            # FLOODGATES DEBUG: Show everything found
            print(f"   🏒 [PROP] {sel} | Edge: {edge*100:.1f}%")
            
            if edge >= Config.MIN_EDGE: # Regular Filter (Positive Edge only)
                # Calculate stake 
                stake = calculate_kelly_stake(edge, price) * 0.5 # Half stake for props volatility
                
                opp = {
                    'Date': mdt.strftime('%Y-%m-%d'),
                    'Kickoff': match['commence_time'],
                    'Sport': 'NHL_PROP',
                    'Event': f"{away} @ {home}",
                    'Selection': sel,
                    'True_Prob': true_prob,
                    'Target': 1/true_prob if true_prob else 0,
                    'Dec_Odds': price,
                    'Edge_Val': edge,
                    'Edge': f"{edge*100:.1f}%",
                    'Stake': f"${stake:.2f}"
                }
                all_opps.append(opp)
                
                if cur:
                    try:
                        unique_id = f"{match['id']}_{sel.replace(' ', '_')}"
                        sql = """
                            INSERT INTO intelligence_log
                            (event_id, timestamp, kickoff, sport, teams, selection, odds, true_prob, edge, stake, trigger_type, closing_odds, ticket_pct, money_pct, sharp_score)
                            VALUES (%s,%s,%s,'NHL_PROP',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                            ON CONFLICT (event_id) DO UPDATE SET
                                odds=EXCLUDED.odds, true_prob=EXCLUDED.true_prob, edge=EXCLUDED.edge,
                                stake=EXCLUDED.stake, selection=EXCLUDED.selection, timestamp=EXCLUDED.timestamp;
                        """
                        params = (
                            unique_id, datetime.now(), opp['Kickoff'], 'NHL', opp['Event'],
                            opp['Selection'], float(price), float(true_prob), float(edge), float(stake), 'model_prop', float(price),
                            None, None, 0
                        )
                        safe_execute(cur, sql, params)
                    except Exception as e:
                        print(f"❌ [DB ERROR] Failed to save {opp['Selection']}: {e}")


def process_markets(match, ratings, calibration, cur, all_opps, target_sport, seen_matches, sharp_data, is_soccer=False, predictions=None, multipliers=None):
    """
    Process betting markets for a match and identify valuable opportunities.

    Args:
        match: Match data from odds API
        ratings: Team ratings dictionary
        calibration: Calibration factor for probabilities
        cur: Database cursor
        all_opps: List to append opportunities to
        target_sport: Target sport
        seen_matches: Set of already processed matches
        sharp_data: Public betting splits data
        is_soccer: Boolean indicating if this is a soccer match
        predictions: Soccer predictions (if applicable)
        multipliers: Pre-calculated smart staking multipliers (optional)
    """
    now_utc = datetime.now(timezone.utc)
    mdt = datetime.fromisoformat(match['commence_time'].replace('Z', '+00:00'))
    if mdt < now_utc:
        return

    bookie = next((b for b in match.get('bookmakers', []) if b['key'] in Config.PREFERRED_BOOKS), None)
    if not bookie:
        return

    home, away = match['home_team'], match['away_team']
    match_id = f"{home} vs {away}"
    if match_id in seen_matches:
        return
    seen_matches.add(match_id)

    def _sharp_score_from_split(money_pct, ticket_pct):
        try:
            m_val = float(money_pct)
            t_val = float(ticket_pct)
        except Exception:
            return 0
        gap = m_val - t_val
        gap_score = max(0, min(1, (gap - 5) / 25))
        minority_score = max(0, min(1, (55 - t_val) / 25))
        money_majority_score = max(0, min(1, (m_val - 50) / 20))
        return int(round(100 * (0.55 * gap_score + 0.25 * minority_score + 0.20 * money_majority_score)))

    match_key = f"{away} @ {home}"
    matched_key = None
    m_match = difflib.get_close_matches(match_key, sharp_data.keys(), n=1, cutoff=0.6) if sharp_data else []
    if m_match:
        matched_key = m_match[0]

    def get_sharp_split(market_key, side_key):
        if not matched_key:
            return None, None, 0
        split = sharp_data.get(matched_key, {}).get(market_key, {}).get(side_key)
        if not split:
            return None, None, 0
        m_pct = split.get("money")
        t_pct = split.get("tickets")
        return m_pct, t_pct, _sharp_score_from_split(m_pct, t_pct)

    # --- SOCCER ---
    if is_soccer:
        mk = f"{away} @ {home}"
        pred = predictions.get(mk) if predictions else None

        if not pred and predictions:
            for pk, pd in predictions.items():
                try:
                    pa, ph = pk.split(" @ ")
                except Exception:
                    continue
                if (difflib.SequenceMatcher(None, home, ph).ratio() > 0.6 and
                    difflib.SequenceMatcher(None, away, pa).ratio() > 0.6):
                    pred = pd
                    break

        if not pred:
            pred = None

        if pred:
            soccer_match_opps = []
            for m in bookie['markets']:
                if m['key'] == 'h2h':
                    for o in m.get('outcomes', []):
                        name = o['name']
                        price = o.get('price')
                        if not price: continue

                        if name == home:
                            mp = pred['home_win']
                            sel = f"{home} ML"
                        elif name == away:
                            mp = pred['away_win']
                            sel = f"{away} ML"
                        elif 'Draw' in name or 'Tie' in name:
                            mp = pred['draw']
                            sel = "Draw ML"
                        else:
                            continue

                        mp *= calibration
                        mp = min(mp, Config.MAX_PROBABILITY)

                        tp = (Config.MARKET_WEIGHT_SOCCER * (1 / price)) + ((1 - Config.MARKET_WEIGHT_SOCCER) * mp)
                        edge = (tp * price) - 1
                        
                        if Config.MIN_EDGE <= edge < Config.MAX_EDGE:
                            stake = calculate_kelly_stake(edge, price)
                            soccer_match_opps.append({
                                'Date': mdt.strftime('%Y-%m-%d'),
                                'Kickoff': match['commence_time'],
                                'Sport': 'SOCCER',
                                'Event': mk,
                                'Selection': sel,
                                'True_Prob': tp,
                                'Target': 1 / tp if tp else 0,
                                'Dec_Odds': price,
                                'Edge_Val': edge,
                                'Edge': f"{edge*100:.1f}%",
                                'Stake': f"${stake:.2f}"
                            })

                elif m['key'] == 'totals':
                    # Parse goal stats for totals
                    if 'home_goals' not in pred: continue
                    
                    proj_total = pred['home_goals'] + pred['away_goals']
                    
                    for o in m.get('outcomes', []):
                        name = o['name'] # Over / Under
                        price = o.get('price')
                        point = o.get('point') # e.g. 2.5
                        if not price or not point: continue
                        
                        # Poisson sum: T ~ Pois(lambda1 + lambda2)
                        # P(Over X) = 1 - cdf(X, lambda_total)
                        # P(Under X) = cdf(X, lambda_total)
                        
                        if name == 'Over':
                            # P(total > point) = P(total >= point_int + 1) = 1 - P(total <= floor(point))
                            prob = 1 - stats.poisson.cdf(int(point), proj_total)
                            sel = f"Over {point} Goals"
                        else: # Under
                            prob = stats.poisson.cdf(int(point), proj_total)
                            sel = f"Under {point} Goals"
                            
                        prob *= calibration
                        prob = min(prob, Config.MAX_PROBABILITY)
                        
                        # Market weight logic
                        tp = (Config.MARKET_WEIGHT_SOCCER * (1 / price)) + ((1 - Config.MARKET_WEIGHT_SOCCER) * prob)
                        edge = (tp * price) - 1
                        
                        if Config.MIN_EDGE <= edge < Config.MAX_EDGE:
                            stake = calculate_kelly_stake(edge, price)
                            soccer_match_opps.append({
                                'Date': mdt.strftime('%Y-%m-%d'),
                                'Kickoff': match['commence_time'],
                                'Sport': 'SOCCER',
                                'Event': mk,
                                'Selection': sel,
                                'True_Prob': tp,
                                'Target': 1 / tp if tp else 0,
                                'Dec_Odds': price,
                                'Edge_Val': edge,
                                'Edge': f"{edge*100:.1f}%",
                                'Stake': f"${stake:.2f}"
                            })

                elif m['key'] == 'h2h_h1':
                     # 1st Half Logic
                     # Heuristic: 1H goals approx 45% of FT goals
                     if 'home_goals' not in pred: continue
                     
                     h_goals_1h = pred['home_goals'] * 0.45
                     a_goals_1h = pred['away_goals'] * 0.45
                     
                     # Calculate Win/Draw/Loss probs for 1H using Poisson difference (Skellam? or simple simulation?)
                     # Simpler: P(H) = sum(P(h_goals=i)*P(a_goals=j) where i > j)
                     # Since we need this for grading, let's implement the generic Poisson match calculator
                     
                     p_home, p_draw, p_away = 0, 0, 0
                     for i in range(10): # Max 10 goals
                         for j in range(10):
                             prob_score = stats.poisson.pmf(i, h_goals_1h) * stats.poisson.pmf(j, a_goals_1h)
                             if i > j: p_home += prob_score
                             elif i == j: p_draw += prob_score
                             else: p_away += prob_score
                             
                     for o in m.get('outcomes', []):
                        name = o['name']
                        price = o.get('price')
                        if not price: continue

                        if name == home:
                            mp = p_home
                            sel = f"1H {home} ML"
                        elif name == away:
                            mp = p_away
                            sel = f"1H {away} ML"
                        elif 'Draw' in name or 'Tie' in name:
                            mp = p_draw
                            sel = "1H Draw ML"
                        else:
                            continue

                        mp *= calibration
                        # Less confident in 1H heuristic, clamp tighter
                        mp = min(mp, 0.65) 

                        tp = (Config.MARKET_WEIGHT_SOCCER * (1 / price)) + ((1 - Config.MARKET_WEIGHT_SOCCER) * mp)
                        edge = (tp * price) - 1
                        
                        if Config.MIN_EDGE <= edge < Config.MAX_EDGE:
                            stake = calculate_kelly_stake(edge, price) * 0.5 # Half stake on 1H
                            
                            side_key = None
                            if sel.startswith(home):
                                side_key = home
                            elif sel.startswith(away):
                                side_key = away
                            elif sel.startswith("Draw") or "Draw" in sel:
                                side_key = "Draw"
                                
                            m_val, t_val, sharp_score_val = (None, None, 0)
                            if side_key:
                                m_val, t_val, sharp_score_val = get_sharp_split("moneyline", side_key)
                                
                            soccer_match_opps.append({
                                'Date': mdt.strftime('%Y-%m-%d'),
                                'Kickoff': match['commence_time'],
                                'Sport': 'SOCCER',
                                'Event': mk,
                                'Selection': sel,
                                'True_Prob': tp,
                                'Target': 1 / tp if tp else 0,
                                'Dec_Odds': price,
                                'Edge_Val': edge,
                                'Edge': f"{edge*100:.1f}%",
                                'Stake': f"${stake:.2f}",
                                'Sharp_Score': sharp_score_val
                            })

            if soccer_match_opps:
                best_opp = sorted(soccer_match_opps, key=lambda x: x['Edge_Val'], reverse=True)[0]
                all_opps.append(best_opp)
                if cur:
                    try:
                        unique_id = f"{match['id']}_{best_opp['Selection'].replace(' ', '_')}"
                        sql = """
                            INSERT INTO intelligence_log
                            (event_id, timestamp, kickoff, sport, teams, selection, odds, true_prob, edge, stake, trigger_type, closing_odds, ticket_pct, money_pct, sharp_score)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                            ON CONFLICT (event_id) DO UPDATE SET
                                odds=EXCLUDED.odds, true_prob=EXCLUDED.true_prob, edge=EXCLUDED.edge,
                                stake=EXCLUDED.stake, selection=EXCLUDED.selection, timestamp=EXCLUDED.timestamp,
                                closing_odds=EXCLUDED.closing_odds, ticket_pct=EXCLUDED.ticket_pct, money_pct=EXCLUDED.money_pct, sharp_score=EXCLUDED.sharp_score;
                        """

                        # Values already calculated above
                        sharp_score_val = best_opp.get('Sharp_Score', 0)
                        
                        params = (
                            unique_id, datetime.now(), best_opp['Kickoff'], 'SOCCER', best_opp['Event'],
                            best_opp['Selection'], float(best_opp['Dec_Odds']), float(best_opp['True_Prob']),
                            float(best_opp['Edge_Val']), float(best_opp['Stake'].replace('$','')), 'model', float(best_opp['Dec_Odds']),
                            int(t_val) if t_val is not None else None,
                            int(m_val) if m_val is not None else None,
                            int(sharp_score_val)
                        )
                        safe_execute(cur, sql, params)
                    except Exception as e:
                        print(f"❌ [DB ERROR] Failed to save {best_opp['Event']}: {e}")

        return

    # --- US SPORTS ---
    exp_margin, exp_total, margin_std, sport = calculate_match_stats(home, away, ratings, target_sport)
    if exp_margin is None:
        return

    for m in bookie['markets']:
        key = m['key']
        if any(x in key for x in ['alternate', 'team', 'q1', 'q2', 'q3', 'q4', '_h2']):
            continue

        for o in m.get('outcomes', []):
            name, price, point = o['name'], o.get('price'), o.get('point', 0)
            if price is None or price == 0:
                continue

            mp, sel = None, None

            if 'spreads' in key:
                eff_m, eff_s = exp_margin, margin_std
                lbl = "1H" if 'h1' in key else ""
                if lbl:
                    eff_m *= 0.48
                    eff_s *= 0.75
                sel = f"{name} {lbl} {point:+.1f}".strip()
                mp = 1 - stats.norm.cdf((-point - (eff_m if name == home else -eff_m)) / eff_s)
            elif 'h2h' in key:
                eff_m, eff_s = exp_margin, margin_std
                lbl = "1H" if 'h1' in key else ""
                if lbl:
                    eff_m *= 0.48
                    eff_s *= 0.75
                sel = f"{name} {lbl} ML".strip()
                mp = 1 - stats.norm.cdf((0 - (eff_m if name == home else -eff_m)) / eff_s)
            elif 'totals' in key:
                eff_t = exp_total
                std_mult = 1.8 if sport == 'NBA' else 1.6 if sport == 'NCAAB' else 1.2
                eff_s = margin_std * std_mult
                lbl = "1H" if 'h1' in key else ""
                if lbl:
                    eff_t = exp_total * 0.50
                    eff_s = margin_std * 0.75 * std_mult
                if name == 'Over':
                    sel = f"{lbl} Over {point}".strip()
                    mp = 1 - stats.norm.cdf((point - eff_t) / eff_s)
                else:
                    sel = f"{lbl} Under {point}".strip()
                    mp = stats.norm.cdf((point - eff_t) / eff_s)

            if mp:
                mp *= calibration
                mp = min(mp, Config.MAX_PROBABILITY)
                tp = (Config.MARKET_WEIGHT_US * (1/price)) + ((1 - Config.MARKET_WEIGHT_US) * mp)
                edge = ((tp * price) - 1) * (0.75 if sport == 'NHL' else 1.0)

                if Config.MIN_EDGE <= edge < Config.MAX_EDGE:
                    stake = calculate_kelly_stake(edge, price, sport=sport, multipliers=multipliers)
                    
                    # Calculate Sharp Score BEFORE creating object
                    sharp_market = None
                    sharp_side = None
                    if 'spreads' in key:
                        sharp_market = "spread"
                        sharp_side = name
                    elif 'h2h' in key:
                        sharp_market = "moneyline"
                        sharp_side = "Draw" if ('draw' in str(name).lower() or 'tie' in str(name).lower()) else name
                    elif 'totals' in key:
                        sharp_market = "total"
                        sharp_side = "Over" if str(name).lower() == "over" else "Under"

                    m_val, t_val, sharp_score_val = (None, None, 0)
                    if sharp_market and sharp_side:
                        m_val, t_val, sharp_score_val = get_sharp_split(sharp_market, sharp_side)

                    opp = {
                        'Date': mdt.strftime('%Y-%m-%d'), 'Kickoff': match['commence_time'], 'Sport': sport, 'Event': f"{away} @ {home}",
                        'Selection': sel, 'True_Prob': tp, 'Target': 1/tp if tp else 0, 'Dec_Odds': price,
                        'Edge_Val': edge, 'Edge': f"{edge*100:.1f}%", 'Stake': f"${stake:.2f}",
                        'Sharp_Score': sharp_score_val # Added for alerts
                    }
                    all_opps.append(opp)
                    if cur:
                        try:
                            unique_id = f"{match['id']}_{sel.replace(' ', '_')}"
                            sql = """
                                INSERT INTO intelligence_log
                                (event_id, timestamp, kickoff, sport, teams, selection, odds, true_prob, edge, stake, trigger_type, closing_odds, ticket_pct, money_pct, sharp_score)
                                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                                ON CONFLICT (event_id) DO UPDATE SET
                                    odds=EXCLUDED.odds, true_prob=EXCLUDED.true_prob, edge=EXCLUDED.edge,
                                    stake=EXCLUDED.stake, selection=EXCLUDED.selection, timestamp=EXCLUDED.timestamp,
                                    closing_odds=EXCLUDED.closing_odds, ticket_pct=EXCLUDED.ticket_pct, money_pct=EXCLUDED.money_pct, sharp_score=EXCLUDED.sharp_score;
                            """
                            params = (
                                unique_id, datetime.now(), opp['Kickoff'], sport, opp['Event'],
                                opp['Selection'], float(price), float(tp), float(edge), float(stake), 'model', float(price),
                                int(t_val) if t_val is not None else None,
                                int(m_val) if m_val is not None else None,
                                int(sharp_score_val)
                            )
                            safe_execute(cur, sql, params)
                        except Exception as e:
                            print(f"❌ [DB ERROR] Failed to save {opp['Event']}: {e}")
