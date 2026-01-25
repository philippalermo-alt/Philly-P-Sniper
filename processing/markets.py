import difflib
from datetime import datetime, timezone
from scipy import stats
from config.settings import Config
from utils.logging import log
from utils.team_names import match_team
from utils.math import _num
from core.probability import logit_scale
import numpy as np
from db.connection import get_dynamic_bankroll
# ... 
from data.sources.ncaab_kenpom import KenPomClient
from core.kelly import calculate_kelly_stake
from core.edge import calculate_edge
from processing.sharp_scoring import calculate_sharp_score
from utils.markets import get_market_type
from utils.team_names import normalize_team_name
from models.sport_models import NCAAB_Model

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class Opportunity:
    """Represents a betting opportunity."""
    event_id: str
    timestamp: datetime
    kickoff: datetime
    sport: str
    teams: str
    selection: str
    odds: float
    true_prob: float
    edge: float
    stake: float
    trigger_type: str
    sharp_score: int = 0
    ticket_pct: Optional[int] = None
    money_pct: Optional[int] = None
    raw_stake: Optional[float] = 0.0 # helper
    unique_id: str = "" # helper
    Dec_Odds: float = 0.0 # helper
    True_Prob: float = 0.0 # helper
    Edge_Val: float = 0.0 # helper
    Kickoff_Str: str = "" # helper
    Sport: str = "" # helper
    Event: str = "" # helper
    Selection: str = "" # helper
    op_type: str = "INSERT" # helper
    Bucket: str = "" # helper
    home_rest: int = 0
    away_rest: int = 0
    ref_1: str = None
    ref_2: str = None
    ref_3: str = None
    home_adj_em: float = 0
    away_adj_em: float = 0
    home_adj_o: float = 0
    away_adj_o: float = 0
    home_adj_d: float = 0
    away_adj_d: float = 0
    home_tempo: float = 0
    away_tempo: float = 0
    
    def to_db_params(self) -> tuple:
        """Convert to database insert parameters."""
        return (
            self.event_id, self.timestamp, self.kickoff, self.sport,
            self.teams, self.selection, self.odds, self.true_prob,
            self.edge, self.stake, self.trigger_type, self.odds,
            self.ticket_pct, self.money_pct, self.sharp_score
        )
    
    # Compatibility with dictionary access for legacy code
    def get(self, key, default=None):
        return getattr(self, key, default)
    
    def __getitem__(self, key):
         # Legacy Compatibility Mapping
         if key == 'Kickoff': return self.kickoff
         if key == 'Sport': return self.sport
         if key == 'Event': return self.teams
         if key == 'Selection': return self.selection
         if key == 'Dec_Odds': return self.odds
         if key == 'True_Prob': return self.true_prob
         if key == 'Edge_Val': return self.edge
         if key == 'Stake': return f"${self.stake:.2f}"
         if key == 'raw_stake': return self.stake
         if key == 'unique_id': return self.event_id # Use event_id as unique_id
         return getattr(self, key)
         
    def __setitem__(self, key, value):
         setattr(self, key, value)

def create_opportunity(event_id, timestamp, kickoff, sport, teams, selection, odds, true_prob, edge, stake, trigger_type='model', sharp_score=0, bucket="", match=None, **kwargs):
    """Helper to create Opportunity with legacy fields populated."""
    return Opportunity(
        event_id=event_id,
        timestamp=timestamp,
        kickoff=kickoff,
        sport=sport,
        teams=teams,
        selection=selection,
        odds=odds,
        true_prob=true_prob,
        edge=edge,
        stake=stake,
        trigger_type=trigger_type,
        sharp_score=sharp_score,
        ticket_pct=kwargs.get('ticket_pct'),
        money_pct=kwargs.get('money_pct'),
        home_rest=kwargs.get('home_rest', 0),
        away_rest=kwargs.get('away_rest', 0),
        ref_1=kwargs.get('ref_1'),
        ref_2=kwargs.get('ref_2'),
        ref_3=kwargs.get('ref_3'),
        home_adj_em=kwargs.get('home_adj_em', 0),
        away_adj_em=kwargs.get('away_adj_em', 0),
        home_adj_o=kwargs.get('home_adj_o', 0),
        away_adj_o=kwargs.get('away_adj_o', 0),
        home_adj_d=kwargs.get('home_adj_d', 0),
        away_adj_d=kwargs.get('away_adj_d', 0),
        home_tempo=kwargs.get('home_tempo', 0),
        away_tempo=kwargs.get('away_tempo', 0),
        # Legacy
        unique_id=event_id,
        Dec_Odds=odds,
        True_Prob=true_prob,
        Edge_Val=edge,
        Kickoff_Str=match['commence_time'] if match else "",
        Sport=sport,
        Event=teams,
        Selection=selection,
        Bucket=bucket,
        op_type=kwargs.get('op_type', 'INSERT')
    )

# KenPom Cache
_kp_client = KenPomClient()
_kp_cache = None
_kp_last_update = 0

# V2 Model Instance
_ncaab_model_v2 = NCAAB_Model()

def get_kenpom_stats(team_name):
    """Exclude strict filtering, fuzzy match against KenPom DF."""
    global _kp_cache, _kp_last_update
    
    if _kp_cache is None or (time.time() - _kp_last_update > 86400): # 24h cache
        try:
             df = _kp_client.get_efficiency_stats()
             if not df.empty:
                 _kp_cache = df
                 _kp_last_update = time.time()
        except:
             pass
    
    if _kp_cache is None: return None
    
    # 1. Exact/Containment
    # DB: "Houston Cougars", KP: "Houston"
    matches = _kp_cache[_kp_cache['Team'].apply(lambda x: x in team_name or team_name in x)]
    if not matches.empty:
         return matches.iloc[0].to_dict()
         
    # 2. Fuzzy Fallback
    import difflib
    all_kp_teams = _kp_cache['Team'].tolist()
    closest_match = difflib.get_close_matches(team_name, all_kp_teams, n=1, cutoff=0.6)
    
    if closest_match:
        # Return matched row
        match_name = closest_match[0]
        row = _kp_cache[_kp_cache['Team'] == match_name]
        if not row.empty:
            # print(f"   🎓 [MATCH] Fuzzy: {team_name} -> {match_name}") 
            return row.iloc[0].to_dict()

    return None

# One-time debug counters for calculate_match_stats TypeErrors
_calc_stats_typeerror_count = 0
_calc_stats_typeerror_max = 5

def calculate_match_stats(home, away, ratings, target_sport, is_neutral=False):
    """
    Calculate expected margin, total, and standard deviation for a match.

    Args:
        home: Home team name
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

    # STRICT VALIDATION: Return None if ratings are missing
    # Do NOT impute average stats (110.0) as this creates fake alpha on unknown teams.
    if not home_r or not away_r:
        if not home_r:
            pass # log("WARN", f"Missing ratings for Home: {home}")
        if not away_r:
            pass # log("WARN", f"Missing ratings for Away: {away}")
        return None, None, None, None

    if home_r.get('sport') != target_sport:
        return None, None, None, None
    sport = target_sport

    try:
        if sport == 'NFL':
            # STRICT: Fail if any stat is missing
            vals = [
                home_r.get('off_ypp'), home_r.get('def_ypp'),
                away_r.get('off_ypp'), away_r.get('def_ypp'),
                home_r.get('off_ppg'), home_r.get('def_ppg'),
                away_r.get('off_ppg'), away_r.get('def_ppg')
            ]
            if any(v is None for v in vals):
                return None, None, None, None

            h_off_ypp = float(vals[0])
            h_def_ypp = float(vals[1])
            a_off_ypp = float(vals[2])
            a_def_ypp = float(vals[3])
            
            home_net = h_off_ypp - h_def_ypp
            away_net = a_off_ypp - a_def_ypp
            margin = ((home_net - away_net) * 4.5) + 2.0

            h_off_ppg = float(vals[4])
            h_def_ppg = float(vals[5])
            a_off_ppg = float(vals[6])
            a_def_ppg = float(vals[7])
            
            home_proj = (h_off_ppg + a_def_ppg) / 2
            away_proj = (a_off_ppg + h_def_ppg) / 2
            total = home_proj + away_proj
            return margin, total, Config.NFL_MARGIN_STD, sport

        if sport == 'NHL':
            vals = [
                home_r.get('league_avg_goals'), home_r.get('attack'), home_r.get('defense'),
                away_r.get('attack'), away_r.get('defense')
            ]
            if any(v is None for v in vals): return None, None, None, None
            
            avg_goals = float(vals[0])
            home_att = float(vals[1])
            home_def = float(vals[2])
            away_att = float(vals[3])
            away_def = float(vals[4])
            
            home_exp = home_att * away_def * avg_goals
            away_exp = away_att * home_def * avg_goals
            home_exp += 0.2
            return (home_exp - away_exp), (home_exp + away_exp), Config.NHL_MARGIN_STD, sport

        # NBA / NCAAB Logic
        vals = [
            home_r.get('tempo'), away_r.get('tempo'),
            home_r.get('offensive_eff'), home_r.get('defensive_eff'),
            away_r.get('offensive_eff'), away_r.get('defensive_eff')
        ]
        if any(v is None for v in vals): return None, None, None, None
        
        avg_tempo = (float(vals[0]) + float(vals[1])) / 2
        poss = avg_tempo / 100
        baseline = 118.0 if sport == 'NBA' else 105.0
        
        home_exp_pts = (float(vals[2]) - (float(vals[5]) - baseline)) * poss
        away_exp_pts = (float(vals[4]) - (float(vals[3]) - baseline)) * poss

        if is_neutral:
            home_court = 0.0
        else:
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



    return base_stake


def process_nhl_props(match, props_data, player_stats, calibration, seen_matches, existing_bets_map=None) -> List[Opportunity]:
    opportunities = []
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
            # Conservation calibration (Props)
            true_prob = logit_scale(prob, calibration)
            true_prob = min(true_prob, 0.85) # Cap max confidence
            
            implied_prob = 1 / price
            # Standard Kelly formulation
            edge = (true_prob * price) - 1
            
            # FLOODGATES DEBUG: Show everything found
            print(f"   🏒 [PROP] {sel} | Edge: {edge*100:.1f}%")
            
            if edge >= Config.MIN_EDGE: # Regular Filter (Positive Edge only)
                # Calculate stake 
                stake = calculate_kelly_stake(edge, price) * 0.5 # Half stake for props volatility
                
                # Check Conflicts
                existing_match_bets = []
                if existing_bets_map:
                    # Props use same match-based ID prefix
                    existing_match_bets = existing_bets_map.get(match['id'], [])
                
                should_insert = True
                
                current_type = get_market_type(sel)
                for r in existing_match_bets:
                   eid, esel, eedge, esp = r
                   if player_name_odds in esel:
                       etype = get_market_type(esel)
                       if etype == current_type and esel != sel:
                           print(f"   🔄 [SWAP] Replacing {esel} -> {sel}")
                           opportunities.append(Opportunity(
                               event_id=eid, op_type='DELETE',
                               timestamp=now_utc, kickoff=now_utc, sport='', teams='', selection='', odds=0, true_prob=0, edge=0, stake=0, trigger_type=''
                           ))

                if should_insert:
                    opportunities.append(create_opportunity(
                        event_id=f"{match['id']}_{sel.replace(' ', '_')}",
                        timestamp=now_utc,
                        kickoff=mdt,
                        sport='NHL_PROP',
                        teams=f"{away} @ {home}",
                        selection=sel,
                        odds=price,
                        true_prob=true_prob,
                        edge=edge,
                        stake=stake,
                        trigger_type='model_prop',
                        sharp_score=0,
                        match=match,
                        op_type='INSERT'
                    ))

    return opportunities


from processing.systems import check_pro_systems

def process_match(match, ratings, calibration, target_sport, seen_matches, sharp_data, existing_bets_map=None, is_soccer=False, predictions=None, multipliers=None) -> List[Opportunity]:
    """
    Process betting markets for a match and identify valuable opportunities.

    Args:
        match: Match data from odds API
        ratings: Team ratings dictionary
        calibration: Calibration factor for probabilities
        target_sport: Target sport
        seen_matches: Set of already processed matches
        sharp_data: Public betting splits data
        is_soccer: Boolean indicating if this is a soccer match
        predictions: Soccer predictions (if applicable)
        multipliers: Pre-calculated smart staking multipliers (optional)
        
    Returns:
        List[Opportunity]: List of identified opportunities
    """
    opportunities = []
    
    now_utc = datetime.now(timezone.utc)
    mdt = datetime.fromisoformat(match['commence_time'].replace('Z', '+00:00'))
    if mdt < now_utc:
        return []

    bookie = next((b for b in match.get('bookmakers', []) if b['key'] in Config.PREFERRED_BOOKS), None)
    if not bookie:
        return []

    home, away = match['home_team'], match['away_team']
    match_id = f"{home} vs {away}"
    if match_id in seen_matches:
        return []
    seen_matches.add(match_id)

    
    # Robust Matching for Sharp Data
    matched_key = None
    if sharp_data:
        n_home = normalize_team_name(home)
        n_away = normalize_team_name(away)
        
        # 1. Containment Search
        # sharp_data keys are already normalized in api_clients.py: "norm_away @ norm_home"
        for sk in sharp_data.keys():
            try:
                s_away, s_home = sk.split(' @ ')
            except:
                continue
                
            # Check overlap
            match_h = (s_home in n_home) or (n_home in s_home)
            match_a = (s_away in n_away) or (n_away in s_away)
            
            if match_h and match_a:
                matched_key = sk
                break
                
        # 2. Fallback to difflib on normalized strings
        if not matched_key:
            search_key = f"{n_away} @ {n_home}"
            m_match = difflib.get_close_matches(search_key, sharp_data.keys(), n=1, cutoff=0.55)
            if m_match:
                matched_key = m_match[0]

    # --- PRO SYSTEMS & SPLITS INJECTION ---
    matched_splits = {}
    if matched_key and sharp_data:
        matched_splits = sharp_data[matched_key]
        match['splits'] = matched_splits 

    # Retrieve stats for Systems
    h_stats = match.get('home_stats', {})
    a_stats = match.get('away_stats', {})
    
    system_triggers = check_pro_systems(match, h_stats, a_stats, sharp_data, ratings)

    def get_sharp_split(market_key, side_key):
        if not matched_key:
            return None, None, 0
            
        # Normalize side key if it's a team name (not Over/Under/Draw)
        lookup_side = side_key
        if market_key in ['spread', 'moneyline'] and side_key not in ['Over', 'Under', 'Draw']:
            lookup_side = normalize_team_name(side_key)
            
        split = sharp_data.get(matched_key, {}).get(market_key, {}).get(lookup_side)
        if not split:
            return None, None, 0
        m_pct = split.get("money")
        t_pct = split.get("tickets")
        return m_pct, t_pct, calculate_sharp_score(m_pct, t_pct)

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

                        # Get Lineup Impact (Phase 7)
                        # defined as Net Home Advantage (e.g. +0.05 means Home is 5% better due to lineups)
                        # SCALING: Raw Impact is xG (e.g. 0.85). We must scale this to Probability.
                        # Heuristic: 1.0 xG diff ~= 20% Win Prob diff.
                        LINEUP_SCALE_FACTOR = 0.20
                        raw_impact = match.get('lineup_impact', 0.0)
                        l_impact = raw_impact * LINEUP_SCALE_FACTOR

                        if name == home:
                            mp = pred['home_win'] + l_impact
                            sel = f"{home} ML"
                        elif name == away:
                            mp = pred['away_win'] - l_impact
                            sel = f"{away} ML"
                        elif 'Draw' in name or 'Tie' in name:
                            mp = pred['draw']
                            sel = "Draw ML"
                        else:
                            continue

                        mp = logit_scale(mp, calibration)
                        mp = min(mp, Config.MAX_PROBABILITY)

                        # SAFETY FIX: Kelly Criterion now uses MODEL Probability (mp) directly
                        # We calculate 'true_edge' based on our model's conviction vs price.
                        # tp (Target Prob) is still calculated for reference but NOT used for edge.
                        
                        tp = (Config.MARKET_WEIGHT_SOCCER * (1 / price)) + ((1 - Config.MARKET_WEIGHT_SOCCER) * mp)
                        
                        # OLD (Dangerous): edge = (tp * price) - 1
                        # NEW (Safe): edge = mp - (1.0 / price) if price > 0 else 0
                        edge = mp - (1.0 / price) if price > 0 else 0

                        
                        # IMPROVEMENT: Step 3 - Stale Line Detector (Max Edge 12%)
                        if edge >= 0.0: # Check positive edge
                             
                            # IMPROVEMENT: Step 11 - Soccer "Draw Edge"
                            # If Draw and Odds > 3.10, we classify as 'DrawHigh' for staking
                            bucket_tag = "Standard"
                            if "Draw" in sel and price > 3.10:
                                bucket_tag = "DrawHigh"
                                # Allow slightly lower edge for these high-value draws?
                                # Let's keep min edge but ensure they are flagged.
                            
                            if (edge >= Config.MIN_EDGE or (bucket_tag == "DrawHigh" and edge >= 0.015)) and edge < 0.12:
                                stake = calculate_kelly_stake(edge, price)
                                
                                # Boost Stake for DrawHigh (Optional, or just let Kelly handle it)
                                # Kelly naturally handles high odds (lower stake).
                                
                                soccer_match_opps.append(Opportunity(
                                    event_id=f"{match['id']}_{sel}",
                                    timestamp=now_utc,
                                    kickoff=mdt,
                                    sport='SOCCER',
                                    teams=mk,
                                    selection=sel,
                                    odds=price,
                                    true_prob=tp,
                                    edge=edge,
                                    stake=stake,
                                    trigger_type='model',
                                    sharp_score=0,
                                    # Helpers for legacy compatibility
                                    unique_id=f"{match['id']}_{sel}",
                                    Dec_Odds=price,
                                    True_Prob=tp,
                                    Edge_Val=edge,
                                    Kickoff_Str=match['commence_time'],
                                    Sport='SOCCER',
                                    Event=mk,
                                    Selection=sel,
                                    Bucket=bucket_tag
                                ))

                elif m['key'] == 'totals':
                    # Parse goal stats for totals
                    # print(f"   🐛 [DEBUG] Processing Totals for {mk}. Pred: {pred}")
                    
                        # Logic 1: Direct Model Output (V6)
                    use_model_prob = False
                    implied_lambda = None
                    
                    if 'prob_over' in pred and pred['prob_over'] > 0:
                        use_model_prob = True
                        p_over_25 = pred['prob_over']
                        
                        # --- STEP 12: ALT TOTALS UNLOCK ---
                        # Numerical solver: Find lambda where P(X >= 3) = p_over_25
                        # P(X >= 3) = 1 - CDF(2, lambda)
                        # We iterate to find optimal lambda (Simple binary search or lookup)
                        # Range for Goals: 0.5 to 6.0
                        low, high = 0.5, 6.0
                        for _ in range(10): # 10 iterations is plenty for 2 decimal precision
                            mid = (low + high) / 2
                            # Calculate P(Over 2.5) given mid
                            p_test = 1 - stats.poisson.cdf(2, mid)
                            if p_test < p_over_25:
                                low = mid # Need higher lambda
                            else:
                                high = mid
                        implied_lambda = (low + high) / 2
                        # print(f"   🔓 [DEBUG-FIX] V6 Prob {p_over_25:.2f} -> Implied Goals: {implied_lambda:.2f}")

                    # Logic 2: Poisson Fallback (V5/Legacy)
                    if not use_model_prob:
                        if 'home_goals' in pred and 'away_goals' in pred:
                             implied_lambda = pred['home_goals'] + pred['away_goals']
                        else:
                             # Missing goals data
                             continue
                    
                    for o in m.get('outcomes', []):
                        name = o['name'] # Over / Under
                        price = o.get('price')
                        point = o.get('point') # e.g. 2.5
                        if not price or not point: continue
                        
                        prob = 0.0
                        is_direct = False
                        
                        # Use V6 direct prob for 2.5 line only to preserve exact model output
                        if use_model_prob and abs(point - 2.5) < 0.1:
                            if name == 'Over':
                                prob = pred['prob_over']
                            else:
                                prob = 1.0 - pred['prob_over']
                            is_direct = True
                        else:
                            # Use Implied Lambda for everything else (1.5, 3.5, etc)
                            # This fixes the "Zero Totals" bug for alt lines
                            if implied_lambda:
                                if name == 'Over':
                                    # P(X > point) = 1 - CDF(floor(point), lambda)
                                    prob = 1 - stats.poisson.cdf(int(point), implied_lambda)
                                else:
                                    prob = stats.poisson.cdf(int(point), implied_lambda)
                            else:
                                continue

                        # Calibration (Only apply to Poisson, V6 is already calibrated)
                        if not is_direct:
                            prob = logit_scale(prob, calibration)
                            
                        prob = min(prob, Config.MAX_PROBABILITY)
                        
                        # Market weight logic (kept for 'True_Prob' display reference only)
                        tp = (Config.MARKET_WEIGHT_SOCCER * (1 / price)) + ((1 - Config.MARKET_WEIGHT_SOCCER) * prob)
                        
                        # SAFETY FIX: Edge calculated on PURE model prob
                        edge = prob - (1.0 / price) if price > 0 else 0

                        
                        print(f"   🐛 [DEBUG] {name} {point}: {prob:.2%} -> Edge: {edge:.1%}")
                        
                        # IMPROVEMENT: Step 3 - Stale Line Detector (Max Edge 12%)
                        if Config.MIN_EDGE <= edge < 0.12:
                            stake = calculate_kelly_stake(edge, price)
                            soccer_match_opps.append(create_opportunity(f"{match['id']}_{sel}", now_utc, mdt, 'SOCCER', mk, sel, price, tp, edge, stake, bucket=bucket_tag, match=match))

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

                        mp = logit_scale(mp, calibration)
                        # Less confident in 1H heuristic, clamp tighter
                        mp = min(mp, 0.65) 

                        tp = (Config.MARKET_WEIGHT_SOCCER * (1 / price)) + ((1 - Config.MARKET_WEIGHT_SOCCER) * mp)
                        
                        # SAFETY FIX: Edge calculated on PURE model prob
                        edge = mp - (1.0 / price) if price > 0 else 0

                        
                        # IMPROVEMENT: Step 3 - Stale Line Detector (Max Edge 12%)
                        if Config.MIN_EDGE <= edge < 0.12:
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
                                
                            soccer_match_opps.append(create_opportunity(f"{match['id']}_{sel}", now_utc, mdt, 'SOCCER', mk, sel, price, tp, edge, stake, sharp_score=sharp_score_val, match=match))
                            
                elif m['key'] == 'totals_h1':
                    # 1H Totals Logic
                    if 'home_goals' not in pred: continue
                    
                    # Heuristic: 45% of scoring happens in 1H
                    proj_total_1h = (pred['home_goals'] + pred['away_goals']) * 0.45
                    
                    for o in m.get('outcomes', []):
                        name = o['name'] # Over / Under
                        price = o.get('price')
                        point = o.get('point')
                        if not price or point is None: continue
                        
                        if name == 'Over':
                            prob = 1 - stats.poisson.cdf(int(point), proj_total_1h)
                            sel = f"1H Over {point} Goals"
                        else: # Under
                            prob = stats.poisson.cdf(int(point), proj_total_1h)
                            sel = f"1H Under {point} Goals"
                            
                        prob = logit_scale(prob, calibration)
                        prob = min(prob, Config.MAX_PROBABILITY) # 1H is volatile
                        
                        tp = (Config.MARKET_WEIGHT_SOCCER * (1 / price)) + ((1 - Config.MARKET_WEIGHT_SOCCER) * prob)
                        
                        # SAFETY FIX: Edge calculated on PURE model prob
                        edge = prob - (1.0 / price) if price > 0 else 0

                        
                        # IMPROVEMENT: Step 3 - Stale Line Detector (Max Edge 12%)
                        if Config.MIN_EDGE <= edge < 0.12:
                            stake = calculate_kelly_stake(edge, price) * 0.5 # Half stake
                            soccer_match_opps.append(create_opportunity(f"{match['id']}_{sel}", now_utc, mdt, 'SOCCER', mk, sel, price, tp, edge, stake, match=match))

                elif m['key'] in ['spreads', 'spreads_h1']:
                    # Soccer Spreads (Asian Handicap) & 1H Spreads
                    if 'home_goals' not in pred: continue
                    
                    is_1h = 'h1' in m['key']
                    factor = 0.45 if is_1h else 1.0
                    lbl = "1H " if is_1h else ""
                    
                    hg = pred['home_goals'] * factor
                    ag = pred['away_goals'] * factor
                    
                    for o in m.get('outcomes', []):
                        name = o['name']
                        point = o.get('point') 
                        price = o.get('price')
                        if not price or point is None: continue
                        
                        # Logic: P(Score + Point > OpponentScore)
                        # We use Poisson summation for exact probability
                        prob = 0.0
                        
                        # Determine lambda for this side and opponent
                        if name == home:
                            l_for, l_opp = hg, ag
                        elif name == away:
                            l_for, l_opp = ag, hg
                        else:
                            continue
                            
                        # Sum probabilities (Truncate at 15 to capture tail)
                        for g_for in range(15):
                            for g_opp in range(15):
                                # Handicap Condition
                                # If spread is -0.5, we need g_for - 0.5 > g_opp => g_for > g_opp
                                # If spread is +0.5, we need g_for + 0.5 > g_opp => g_for >= g_opp
                                if g_for + point > g_opp:
                                    p = stats.poisson.pmf(g_for, l_for) * stats.poisson.pmf(g_opp, l_opp)
                                    prob += p
                        
                        # Apply Calibration
                        prob *= calibration
                        prob = min(prob, Config.MAX_PROBABILITY)
                        
                        tp = (Config.MARKET_WEIGHT_SOCCER * (1 / price)) + ((1 - Config.MARKET_WEIGHT_SOCCER) * prob)
                        edge = tp - (1.0 / price) if price > 0 else 0
                        
                        # IMPROVEMENT: Step 3 - Stale Line Detector (Max Edge 12%)
                        if Config.MIN_EDGE <= edge < 0.12:
                            stake = calculate_kelly_stake(edge, price)
                            if is_1h: stake *= 0.5
                            
                            sel = f"{lbl}{name} {point:+.1f}"
                            
                            soccer_match_opps.append(create_opportunity(f"{match['id']}_{sel}", now_utc, mdt, 'SOCCER', mk, sel, price, tp, edge, stake, match=match))

            if soccer_match_opps:
                best_opp = sorted(soccer_match_opps, key=lambda x: x['Edge_Val'], reverse=True)[0]
                
                # Check for existing bets & Conflicts
                existing_match_bets = []
                if existing_bets_map:
                     existing_match_bets = existing_bets_map.get(match['id'], [])

                should_insert = True
                
                # CONFLICT CHECK (Soccer)
                current_type_m = get_market_type(best_opp['Selection'])
                
                for r in existing_match_bets:
                    # row: (event_id, selection, edge, sport)
                    eid_m, esel_m, existing_edge, esp = r
                    
                    etype_m = get_market_type(esel_m)
                    if etype_m == current_type_m and etype_m != "OTHER":
                        if esel_m != best_opp['Selection']:
                            # BARRIER: Swap if new edge > old + 0.5%
                            if best_opp['Edge_Val'] > (existing_edge + 0.005):
                                print(f"   🔄 [SWAP] Replacing {esel_m} ({existing_edge:.1%}) -> {best_opp['Selection']} ({best_opp['Edge_Val']:.1%})")
                                all_opps.append({
                                    'op_type': 'DELETE',
                                    'event_id': eid_m
                                })
                            else:
                                print(f"   🛡️ [HOLD] Keeping {esel_m} ({existing_edge:.1%}) vs {best_opp['Selection']} ({best_opp['Edge_Val']:.1%})")
                                should_insert = False
                                break # Stop checking, we are blocked

                if should_insert:
                     # Enrich Best Opp
                     best_opp['op_type'] = 'INSERT'
                     best_opp['trigger_type'] = 'model' # Default trigger
                     best_opp['match_id'] = match['id']
                     best_opp['unique_id'] = f"{match['id']}_{best_opp['Selection'].replace(' ', '_')}"
                     best_opp['home_rest'] = match.get('home_rest')
                     best_opp['away_rest'] = match.get('away_rest')
                     # Soccer usually doesn't have ref stats in this dict, but we safely get them
                     best_opp['ref_1'] = match.get('ref_1')
                     
                     all_opps.append(best_opp)
        
        return

    # --- US SPORTS ---
    # Pass neutral site flag from match metadata
    is_neutral = match.get('neutral_site', False)
    
    exp_margin, exp_total, margin_std, sport = calculate_match_stats(
        home, away, ratings, target_sport, is_neutral=is_neutral
    )
    if exp_margin is None:
        return
        
    # KenPom Stats for DB (NCAAB Only)
    kp_home, kp_away = {}, {}
    if sport == 'NCAAB':
        h_stats = get_kenpom_stats(home)
        if h_stats: kp_home = h_stats
        
        a_stats = get_kenpom_stats(away)
        if a_stats: kp_away = a_stats

    # --- NHL V2 REF ADJUSTMENT ---
    if sport == 'NHL' and 'crew_pen' in match:
        try:
            # 1. Totals Adjustment
            # Coeff: 0.087 goals per extra penalty (Weak signal, R^2=0.02)
            # League Avg: 7.43 (2025 Data)
            # Safety: Clip to max +/- 0.35 goals
            LEAGUE_AVG_PEN = 7.43
            PP_CONVERSION = 0.087
            
            crew_p = match['crew_pen']
            pen_diff = crew_p - LEAGUE_AVG_PEN
            total_adj = pen_diff * PP_CONVERSION
            
            # CLIP logic
            total_adj = max(-0.35, min(0.35, total_adj))
            
            if abs(total_adj) > 0.05:
                exp_total += total_adj

            # 2. Side Adjustment (Margin)
            # DISABLE: Regression showed negative correlation (-0.05), implying "Game Management"
            # (Refs give penalties to losing teams). This is reactive, not predictive.
            # We do not want to bake this reverse causality into the prediction.
            pass
                
        except Exception as e:
            print(f"⚠️ NHL Ref Adj Failed: {e}")
        
    # --- NEWS IMPACT ---
    # Injected from hard_rock_model.py
    # If not present, default to 0.0
    news_impact = match.get('news_impact', 0.0)
    
    # If News Impact is negative (Home Team has bad news), we should shift the MARGIN against them.
    # Impact is currently defined as probability penalty in hard_rock_model logic, 
    # but applying it to the MARGIN is mathematically cleaner for Spreads & ML simultaneously.
    # A 2.5% win prob shift approx equals 1.0 - 1.5 points in NBA.
    # Let's apply it directly to `exp_margin`.
    
    if news_impact != 0:
        # news_impact of -0.025 (prob) roughly maps to -1.5 points.
        # Let's scale it: 50 points per 1.0 prob (rough heuristic) implies -1.25 pts.
        # Simplified: If impact is negative, reduce home margin.
        
        # NOTE: hard_rock_model currently sets it to 0.0, so this is future-proof logic.
        # V2 will populate 'news_impact' with float values.
        
        # Heuristic: 1% Prob = 0.5 points
        # If news_impact is -0.05 (-5%), margin shift should be -2.5 points.
        
        if sport in ['NBA', 'NFL', 'NCAAB']:
             margin_shift = news_impact * 50.0 
             exp_margin += margin_shift
             print(f"   📰 [{home} vs {away}] News Impact Applied (Spread): {news_impact:.3f} -> Margin Shift: {margin_shift:.2f} pts")
        elif sport == 'NHL':
             # For NHL, do NOT shift margin by 2.5 goals!
             # We will apply the impact directly to the Win Probability (mp) below.
             pass


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
                std_mult = 1.8 if sport == 'NBA' else 1.9 if sport == 'NCAAB' else 1.2
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

            # Apply NHL News Impact (Probability Shift)
            if mp and sport == 'NHL' and news_impact != 0 and 'h2h' in key:
                 # Logic: news_impact is a +/- Win Prob value from Home perspective.
                 # If Home has bad news (negative impact), Home MP decreases.
                 # If Home has bad news, Away MP increases.
                 
                 if name == home:
                     mp += news_impact
                     print(f"   🏒 NHL News Impact Applied: {news_impact:+.3f} to {home} ML")
                 elif name == away:
                     mp -= news_impact # Inverse impact
                     print(f"   🏒 NHL News Impact Inverse: {-news_impact:+.3f} to {away} ML")

            if mp:
                mp = logit_scale(mp, calibration)
                mp = min(mp, Config.MAX_PROBABILITY)
                # Math Correction (Final Review): Use pure Model Probability.
                # Do NOT blend with market odds.
                tp = mp
                
                # REFACTOR 2026-01-25: Use Diff (Prob - Implied)
                raw_edge = (tp - (1.0 / price)) if price > 0 else 0
                edge = raw_edge * (0.75 if sport == 'NHL' else 1.0)


                # Calculate Sharp Score FIRST
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

                # --- PRO SYSTEM BOOST ---
                triggered_systems_for_bet = []
                if system_triggers:
                    print(f"   🔎 [DEBUG] Match ID: {match.get('id')} | Systems Found: {system_triggers}")
                    unique_systems = set()
                    
                    # 1. Totals (Unders)
                    if "Under" in str(sel):
                        for s in system_triggers:
                            if "Under" in s:
                                unique_systems.add(s)
                                sharp_score_val += 15 # Big boost per system
                    
                    # 2. Side Systems (Fade Public, Tanking, Big Conf Dogs)
                    is_home_bet = (home in str(sel))
                    is_away_bet = (away in str(sel))
                    
                    for s in system_triggers:
                        if "Fade Public" in s:
                            if (is_home_bet and "Home" in s) or (is_away_bet and "Away" in s):
                                unique_systems.add(s)
                                sharp_score_val += 15
                        elif "Big Conf Dogs" in s:
                             if (is_home_bet and "Home" in s) or (is_away_bet and "Away" in s):
                                unique_systems.add(s)
                                sharp_score_val += 15
                        elif "Tanking" in s:
                             if (is_home_bet and "Home" in s) or (is_away_bet and "Away" in s):
                                unique_systems.add(s)
                                sharp_score_val += 15
                                
                    triggered_systems_for_bet = list(unique_systems)
                    if triggered_systems_for_bet:
                        print(f"   🔥 [PRO SYSTEM] {sel} | Sc: {sharp_score_val} | Systems: {triggered_systems_for_bet}")

                # --- NCAAB V2 MODEL OVERRIDE ---
                # NOTE: Disabled for 1H markets as V2 is trained on Full Game data
                if sport == 'NCAAB' and mp is not None and "h1" not in key and "1h" not in key:
                    # Debug to catch leaks
                    # print(f"   🔍 [V2 CANDIDATE] Key: {key} | Sel: {sel}")
                    try:
                        # Construct Features for V2
                        # features = ['implied_prob', 'true_prob', 'ticket_pct', 'minutes_to_kickoff', 
                        #             'kenpom_diff', 'adjo_diff', 'adjd_diff', 'tempo_diff']
                        
                        kp_diff = float(kp_home.get('AdjEM', 0)) - float(kp_away.get('AdjEM', 0))
                        adjo_diff = float(kp_home.get('AdjO', 0)) - float(kp_away.get('AdjO', 0))
                        adjd_diff = float(kp_home.get('AdjD', 0)) - float(kp_away.get('AdjD', 0))
                        tempo_diff = float(kp_home.get('AdjT', 0)) - float(kp_away.get('AdjT', 0))
                        
                        # Invert for Away team bets?
                        # The model was trained on "Home - Away" diffs relative to the Outcome (Win/Loss).
                        # Using 'target' = 1 if outcome='WON'.
                        # But wait, the model predicts probability of WINNING the bet?
                        # The training data ('target') is based on 'outcome' of the bet.
                        # So if the bet is "Away ML", the features should be from Away perspective?
                        # Actually, looking at base_model.py, it loads `true_prob` (heuristic) and `implied_prob`.
                        # The features `home_adj_em` etc are static per game.
                        # The model learns the relationship between (Legacy Prob + Game Stats) -> Win.
                        # However, for Away bets, the 'true_prob' (heuristic) accounts for being Away.
                        # The static stats (Home - Away) should remain Home - Away, because the model
                        # learns that if Home is much better (Positive Diff) and we bet Home (High True Prob), we win.
                        # If Home is much better (Positive Diff) and we bet Away (Low True Prob), we lose.
                        # So we pass the Raw Diffs as is.
                        
                        mins_to_kick = (mdt - now_utc).total_seconds() / 60
                        
                        input_data = {
                            'implied_prob': 1/price,
                            'true_prob': mp,
                            'ticket_pct': float(t_val) if t_val else 50.0,
                            'minutes_to_kickoff': mins_to_kick,
                            'kenpom_diff': kp_diff,
                            'adjo_diff': adjo_diff, 
                            'adjd_diff': adjd_diff, 
                            'tempo_diff': tempo_diff
                        }
                        
                        # If bet is on AWAY team, does the model know?
                        # The model doesn't explicitly know "Side".
                        # But 'true_prob' contains the side info (it's low for underdog, high for favorite).
                        # So the interaction between 'true_prob' and 'kenpom_diff' captures it.
                        
                        v2_prob = _ncaab_model_v2.predict(input_data)
                        
                        # Log significant deviations
                        if abs(v2_prob - mp) > 0.10:
                            print(f"   🏀 [V2 ADJUST] {sel}: {mp:.3f} -> {v2_prob:.3f}")
                            
                        # IMPROVEMENT: Step 1 - NCAAB Reality Cap (65%) & Recalculate Logic
                        mp = min(v2_prob, 0.65)
                        
                        # Recalculate Edge & TP with new MP (Pure Model)
                        tp = mp
                        edge = (tp - (1.0 / price)) if price > 0 else 0
                        
                    except Exception as e:
                        print(f"   ⚠️ V2 Inference Failed: {e}")

                # Criteria: Value Bet OR Sharp Signal OR Pro System
                
                # IMPROVEMENT: Step 2 - NCAAB Noise Floor (Min Edge 6.0%)
                min_edge_required = Config.MIN_EDGE
                if sport == 'NCAAB':
                    min_edge_required = 0.06
                elif sport == 'NHL':
                    # IMPROVEMENT: Step 5 - NHL Volume Boost (Min Edge 2.5%)
                    min_edge_required = 0.025
                    min_edge_required = 0.025
                
                # IMPROVEMENT: Step 6 - RLM Filter (NCAAB) - Skip if Sharp Score < 30
                if sport == 'NCAAB' and sharp_score_val < 30:
                    continue

                # Phase 2: Calibration Logging (Every evaluated bet)
                if mp and cur:
                    # Log every prediction for calibration
                    # Using safe_execute/inline requires import? No, call log_calibration from database
                    # But probability_models imports database.safe_execute. Need to import log_calibration too?
                    # Or just direct SQL here to avoid circular import if database imports probability_models (unlikely)
                    # Let's assume log_calibration is available or use SQL.
                    pass # Handled below
                
                # Check for existing bets using Pre-Fetched Map
                is_existing = False
                existing_match_bets = []
                
                if existing_bets_map:
                    # Look up by Match ID (which we need to extract from numeric IDs?)
                    # fetch.py stored them by odds-api ID (match['id'])?
                    # Let's try direct look up
                    existing_match_bets = existing_bets_map.get(match['id'], [])
                    
                    for row_e in existing_match_bets:
                        # row structure: (event_id, selection, edge, sport)
                        if row_e[1] == sel:
                            is_existing = True
                            break

                is_value = (min_edge_required <= edge < Config.MAX_EDGE)
                is_pro = bool(triggered_systems_for_bet)
                is_sharp = (sharp_score_val >= Config.SHARP_SIGNAL_THRESHOLD) or is_pro

                # Policy: Log if Value OR Sharp OR It's an existing bet we need to update status for
                if is_value or is_sharp or is_existing:
                    stake = calculate_kelly_stake(edge, price, sport=sport, multipliers=multipliers)
                    
                    if not (is_value or is_sharp):
                        stake = 0.0

                    trig_type = 'model' if is_value else 'sharp_signal'
                    if triggered_systems_for_bet:
                        trig_type = f"PRO: {', '.join(set(triggered_systems_for_bet))}"
                    if is_existing and not (is_value or is_sharp):
                        trig_type = "stale_update"

                    # ENRICHMENT: Add all fields required for DB Buffer
                    opp = create_opportunity(
                        event_id=f"{match['id']}_{sel.replace(' ', '_')}",
                        timestamp=now_utc,
                        kickoff=mdt,
                        sport=sport,
                        teams=f"{away} @ {home}",
                        selection=sel,
                        odds=price,
                        true_prob=tp,
                        edge=edge,
                        stake=stake,
                        trigger_type=trig_type,
                        sharp_score=sharp_score_val,
                        match=match,
                        ticket_pct=int(t_val) if t_val is not None else None,
                        money_pct=int(m_val) if m_val is not None else None,
                        home_rest=match.get('home_rest'),
                        away_rest=match.get('away_rest'),
                        ref_1=match.get('ref_1'),
                        ref_2=match.get('ref_2'),
                        ref_3=match.get('ref_3'),
                        home_adj_em=float(kp_home.get('AdjEM', 0)),
                        away_adj_em=float(kp_away.get('AdjEM', 0)),
                        home_adj_o=float(kp_home.get('AdjO', 0)),
                        away_adj_o=float(kp_away.get('AdjO', 0)),
                        home_adj_d=float(kp_home.get('AdjD', 0)),
                        away_adj_d=float(kp_away.get('AdjD', 0)),
                        home_tempo=float(kp_home.get('AdjT', 0)),
                        away_tempo=float(kp_away.get('AdjT', 0))
                    )
                    
                    # Store Operation Type
                    opp['op_type'] = 'INSERT' 
                    
                    # CONFLICT / SWAP Logic (In-Memory)
                    if existing_match_bets:
                        current_type_us = get_market_type(sel)
                        for eid_u, esel_u, existing_edge, esp in existing_match_bets:
                            etype_u = get_market_type(esel_u)
                            if etype_u == current_type_us and etype_u != "OTHER":
                                if esel_u != sel:
                                    # BARRIER: Swap if new bet is better
                                    if edge > (existing_edge + 0.005):
                                        print(f"   🔄 [SWAP] Replacing {esel_u} ({existing_edge:.1%}) -> {sel} ({edge:.1%})")
                                        # Trigger DELETE for old bet
                                        opportunities.append(Opportunity(
                                            event_id=eid_u, op_type='DELETE', 
                                            timestamp=now_utc, kickoff=now_utc, sport='', teams='', selection='', odds=0, true_prob=0, edge=0, stake=0, trigger_type=''
                                        ))
                                    else:
                                        print(f"   🛡️ [HOLD] Keeping {esel_u} ({existing_edge:.1%}) vs {sel} ({edge:.1%})")
                                        # Skip adding this new lower value bet
                                        # Unless it's an update (handled by is_existing check? No, different sel)
                                        # So we abort this addition
                                        pass

                    if is_value or is_sharp or is_existing:
                         opportunities.append(opp)
    
    return opportunities
