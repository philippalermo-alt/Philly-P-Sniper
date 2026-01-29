
import os
import requests
import pandas as pd
import difflib
import re
from datetime import datetime, timedelta
from db.connection import get_db
from config import Config
from utils import log

# Set up logging context
CONTEXT = "SoccerPropSettlement"

def get_fixtures_for_date(league_id, date_str):
    """
    Fetch finished fixtures for a specific league and date.
    Returns list of dicts: {fixture_id, home, away, score}
    """
    url = f"https://v3.football.api-sports.io/fixtures"
    params = {
        'league': league_id,
        'season': 2025, # Corrected for 2025-2026 Season
        'date': date_str,
        'status': 'FT' # Finished
    }
    headers = {'x-apisports-key': Config.FOOTBALL_API_KEY}
    
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        fixtures = []
        for f in data.get('response', []):
            fixtures.append({
                'id': f['fixture']['id'],
                'home': f['teams']['home']['name'],
                'away': f['teams']['away']['name'],
                'home_goals': f['goals']['home'],
                'away_goals': f['goals']['away']
            })
        return fixtures
    except Exception as e:
        log(CONTEXT, f"[ERROR] Error fetching fixtures: {e}")
        return []

def get_fixture_player_stats(fixture_id):
    """
    Fetch player statistics for a specific fixture.
    Returns a dict keyed by Normalized Player Name logic.
    """
    url = f"https://v3.football.api-sports.io/fixtures/players"
    params = {'fixture': fixture_id}
    headers = {'x-apisports-key': Config.FOOTBALL_API_KEY}
    
    player_stats = {}
    
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        # API returns data per team
        for team_data in data.get('response', []):
            for player in team_data.get('players', []):
                p_name = player['player']['name']
                stats = player['statistics'][0] # Usually only 1 item per game
                
                # Check metrics we care about
                goals = stats['goals']['total'] or 0
                shots = stats['shots']['total'] or 0
                sot = stats['shots']['on'] or 0
                assists = stats['goals']['assists'] or 0
                
                # Normalize name for easier matching
                norm_name = p_name.lower().strip()
                
                player_stats[norm_name] = {
                    'name_display': p_name,
                    'goals': goals,
                    'shots': shots,
                    'shots_on_target': sot,
                    'assists': assists
                }
                
        return player_stats
        
    except Exception as e:
        log(CONTEXT, f"[ERROR] Error fetching stats for fixture {fixture_id}: {e}")
        return {}

def normalize_name(name):
    """Simple normalization for fuzzy matching."""
    return name.lower().strip()

def match_player(target_name, player_stats_db):
    """
    Find best match for target_name in player_stats_db keys.
    Returns (stats_dict, score)
    """
    target_norm = normalize_name(target_name)
    
    # Direct match check
    if target_norm in player_stats_db:
        return player_stats_db[target_norm], 100
        
    # Fuzzy match
    keys = list(player_stats_db.keys())
    matches = difflib.get_close_matches(target_norm, keys, n=1, cutoff=0.7)
    
    if matches:
        return player_stats_db[matches[0]], 90 # Arbitrary high confidence for fuzzy
        
    return None, 0

def grade_prop_bet(selection, stats):
    """
    Grade a prop bet based on selection string and stats.
    Selection fmt: "Player Name Over X.5 Shots"
    """
    # Regex to parse selection
    # Supported Patterns:
    # 1. "{Player} Over {Line} Shots"
    # 2. "{Player} Over {Line} Shots on Target"
    # 3. "{Player} Over {Line} Goals"
    # 4. "{Player} Anytime Goalscorer"
    
    sel = selection.lower()
    
    actual = 0
    line = 0.0
    metric = "unknown"
    
    # 1. Anytime Goalscorer
    if "anytime goalscorer" in sel:
        metric = "goals"
        line = 0.5
        actual = stats['goals']
        
    # 2. Shots on Target
    elif "shots on target" in sel:
        metric = "sot"
        match = re.search(r'over\s+(\d+\.?\d*)', sel)
        if match:
            line = float(match.group(1))
        actual = stats['shots_on_target']

    # 3. Shots (Total)
    elif "shots" in sel: # Warning: "shots on target" also contains "shots", so check SOT first
        metric = "shots"
        # Regex to find line
        match = re.search(r'over\s+(\d+\.?\d*)', sel)
        if match:
            line = float(match.group(1))
        actual = stats['shots']
        
    # 4. Goals (Over)
    elif "goals" in sel and "over" in sel:
        metric = "goals"
        match = re.search(r'over\s+(\d+\.?\d*)', sel)
        if match:
            line = float(match.group(1))
        actual = stats['goals']
        
    else:
        log(CONTEXT, f"[WARNING] Unknown prop format: {selection}")
        return "PENDING", f"Unknown Format: {metric}"

    # Determine Outcome
    if actual > line:
        return "WON", f"{metric.title()}: {actual} > {line}"
    else:
        return "LOST", f"{metric.title()}: {actual} <= {line}"

def settle_soccer_props():
    log(CONTEXT, "[INFO] Starting Soccer Prop Settlement...")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Get Pending Props
    # Look for event_id starting with 'PROP_' or containing player prop keywords in selection?
    # Better to trust event_id prefix as per new convention.
    # Also fetch legacy ones if we can identify them.
    # For now, strictly 'PROP_' prefix or 'player_props_model' source.
    cursor.execute("""
        SELECT event_id, sport, teams, selection, kickoff, stake
        FROM intelligence_log 
        WHERE outcome = 'PENDING' 
        AND (event_id LIKE 'PROP_%' OR selection LIKE '%Over%' OR selection LIKE '%Goalscorer%')
        AND sport LIKE 'soccer_%'
        AND kickoff < NOW() - INTERVAL '3 hours' -- Wait for game to finish
    """)
    
    bets = cursor.fetchall()
    
    if not bets:
        log(CONTEXT, "[INFO] No pending soccer props to settle.")
        return

    # 2. Group by League & Date to minimize API Calls
    # Map: (league_id, date) -> fixtures_list
    fixtures_cache = {}
    stats_cache = {} # fixture_id -> stats_dict
    
    processed_count = 0
    
    for bet in bets:
        event_id, sport, event_str, selection, kickoff, stake = bet
        
        # Parse essentials
        lid = Config.SOCCER_LEAGUE_IDS.get(sport)
        if not lid:
            log(CONTEXT, f"[WARNING] Skipping bet {db_id}: Unknown league {sport}")
            continue
            
        date_str = kickoff.strftime('%Y-%m-%d')
        cache_key = (lid, date_str)
        
        # Fetch fixtures if not cached
        if cache_key not in fixtures_cache:
            fixtures_cache[cache_key] = get_fixtures_for_date(lid, date_str)
            
        fixtures = fixtures_cache[cache_key]
        
        # Find Fixture
        # Event string format: "Home vs Away" or "Home @ Away"
        # We need to fuzzy match these team names against fixture names
        target_teams = event_str.replace(' vs ', ' ').replace(' @ ', ' ').split(' ')
        # That logic is weak. Better: use the full string similarity against "Home vs Away"
        
        matched_fixture = None
        best_score = 0
        
        for f in fixtures:
            # Construct comparable strings
            api_str_1 = f"{f['home']} vs {f['away']}"
            api_str_2 = f"{f['away']} vs {f['home']}"
            
            score_1 = difflib.SequenceMatcher(None, event_str, api_str_1).ratio()
            score_2 = difflib.SequenceMatcher(None, event_str, api_str_2).ratio()
            
            max_score = max(score_1, score_2)
            if max_score > 0.6 and max_score > best_score:
                best_score = max_score
                matched_fixture = f
        
        if not matched_fixture:
            log(CONTEXT, f"[WARNING] Could not find match for bet {db_id}: {event_str} ({date_str})")
            continue
            
        # Found Match -> Fetch Stats
        fid = matched_fixture['id']
        
        if fid not in stats_cache:
            stats_cache[fid] = get_fixture_player_stats(fid)
            
        game_stats = stats_cache[fid]
        
        if not game_stats:
            log(CONTEXT, f"[WARNING] No stats available for fixture {fid}")
            continue
            
        # Extract Player Name from Selection
        # Heuristic: Player Name is everything before "Over" or "Anytime"
        # Example: "Mohamed Salah Over 0.5 Shots on Target" -> "Mohamed Salah"
        
        player_name_target = ""
        if "Over" in selection:
            player_name_target = selection.split(" Over ")[0].strip()
        elif "Anytime" in selection:
            player_name_target = selection.split(" Anytime")[0].strip()
        else:
            # Fallback
            player_name_target = selection.split(" ")[0] # Very risky
            
        p_stats, score = match_player(player_name_target, game_stats)
        
        if not p_stats:
             log(CONTEXT, f"[WARNING] Player not found in stats: {player_name_target} (Bet {db_id})")
             continue
             
        # Grade It
        outcome, logic = grade_prop_bet(selection, p_stats)
        
        if outcome in ['WON', 'LOST']:
            pnl = 0.0
            # Get odds if needed for PnL, but DB update usually just needs Outcome
            # We can calculate PnL in the Update
            
            # Update DB
            cursor.execute("""
                UPDATE intelligence_log
                SET outcome = %s, logic = %s 
                WHERE event_id = %s
            """, (outcome, logic, event_id))
            
            cursor.execute("UPDATE calibration_log SET outcome = %s WHERE event_id = %s", (outcome, event_id))
            
            conn.commit()
            log(CONTEXT, f"[INFO] Settled Bet {event_id}: {selection} -> {outcome} ({logic})")
            processed_count += 1
            
    conn.close()
    log(CONTEXT, f"[INFO] Completed Cycle. Settled {processed_count} props.")

if __name__ == "__main__":
    settle_soccer_props()
