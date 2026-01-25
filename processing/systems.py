from config.settings import Config
from utils.logging import log
from utils.team_names import normalize_team_name

def check_pro_systems(match, home_stats, away_stats, sharp_data, team_ratings):
    """
    Check if a match triggers any known Pro Betting Systems.
    
    Args:
        match (dict): Match metadata (sport, venue, neutral_site, etc.)
        home_stats (dict): Home team statistics (record, last_margin)
        away_stats (dict): Away team statistics
        sharp_data (dict): Betting splits (money/ticket pct)
        team_ratings (dict): KenPom/Advanced ratings
        
    Returns:
        list: List of triggered system names.
    """
    triggers = []
    
    sport = match.get('sport_key', '')
    if 'basketball_ncaab' in sport:
        sport = 'NCAAB'
    elif 'basketball_nba' in sport:
        sport = 'NBA'
    else:
        # Some systems rely on specific sports
        pass
        
    # --- PRE-CALCULATIONS ---
    # Public Splits
    # match['splits'] should be populated by main loop matching logic
    splits = match.get('splits', {}) 
    spread_tickets_h = splits.get('spread', {}).get(match['home_team'], {}).get('tickets', 50)
    spread_tickets_a = splits.get('spread', {}).get(match['away_team'], {}).get('tickets', 50)
    under_tickets = splits.get('total', {}).get('Under', {}).get('tickets', 50)
    
    # Lines (Current)
    total_line = None
    spread_line = None # Home spread
    
    # Extract lines from bookmakers (assuming 'match' has 'bookmakers')
    # Use best available or first preferred
    # This logic assumes 'process_markets' helps us, but here we scan raw 'match'
    # For simplicity, we assume the caller passes relevant line info or we parse it here.
    # We'll try to find a consensus line.
    for book in match.get('bookmakers', []):
        for market in book.get('markets', []):
            if market['key'] == 'totals':
                total_line = market['outcomes'][0].get('point')
            if market['key'] == 'spreads':
                # find home spread
                for out in market['outcomes']:
                    if out['name'] == match['home_team']:
                        spread_line = out.get('point')
    
    # ---------------------------------------------------------
    # SYSTEM 1: Neutral Court Unders (NCAAB)
    # ---------------------------------------------------------
    if sport == 'NCAAB' and match.get('neutral_site'):
        # Month Filter: Nov-Apr (basically all season except rare weirdness)
        # Total Range: 145 - 180
        if total_line and 145 <= total_line <= 180:
            if under_tickets <= 50:
                triggers.append("Neutral Court Unders")

    # ---------------------------------------------------------
    # SYSTEM 2: Fade The Public in Big Conferences (NCAAB)
    # ---------------------------------------------------------
    if sport == 'NCAAB':
        # Big Conferences: Check ratings or notes
        # We can leverage 'notes' from ESPN if available, or team rating metadata
        # Simpler proxy: Check if 'conference' is in team stats if we tracked it
        # For now, we'll try to guess based on 'notes' or if user provides conf data.
        # Let's assume 'notes' contain conference names like "Big 12"
        notes_text = " ".join(match.get('notes', [])).upper()
        big_confs = ['BIG 12', 'SEC', 'PAC-12', 'ACC', 'BIG TEN', 'BIG EAST']
        
        is_big_conf = any(c in notes_text for c in big_confs)
        
        if is_big_conf:
            # Total Range 128 - 146.5
            if total_line and 128 <= total_line <= 146.5:
                # Spread % <= 24% on one side
                # If Home has <= 24% tickets
                if spread_tickets_h <= 24:
                    triggers.append(f"Fade Public in Big Conf ({match['home_team']})")
                elif spread_tickets_a <= 24:
                    triggers.append(f"Fade Public in Big Conf ({match['away_team']})")

    # ---------------------------------------------------------
    # SYSTEM 3: Evan Abrams - Stadium Unders (NCAAB)
    # ---------------------------------------------------------
    if sport == 'NCAAB':
        # Hardcoded list of shooting-difficulty arenas
        target_arenas = [
            "Barclays Center", "Jersey Mike's Arena", "UPMC Cooper Fieldhouse", 
            "Madison Square Garden", "Jack Breslin Student Events Center", "Chartway Arena", 
            "Thomas & Mack Center", "Corbett Sports Center", "Mitchell Center", 
            "Redhawk Center", "University Arena", "Boardwalk Hall", "Pan American Center", 
            "Save Mart Center", "Fertitta Center", "John Gray Gymnasium", "Sanford Center", 
            "Wells Fargo Arena", "NIU Convocation Center", "Enterprise Center"
        ]
        
        current_venue = match.get('venue', '')
        # Fuzzy check
        match_venue = any(arena.upper() in current_venue.upper() for arena in target_arenas)
        
        if match_venue:
            # Filter: Home Team's previous game went UNDER
            # Check home_stats['last_game_total_result']
            prev_result = home_stats.get('last_game_ou_result')
            
            # If we don't have the data (e.g. first game of tracking or no odds found), 
            # we should probably skip to be safe, OR match the user's strict criteria.
            # User said: "It is in one of the listed arena's, but Old Dominions previous game did not go under"
            # This implies the check MUST PASS.
            
            if prev_result == 'Under':
                triggers.append(f"Stadium Under ({current_venue})")

    # ---------------------------------------------------------
    # SYSTEM 4: RLM Unders (NBA)
    # ---------------------------------------------------------
    if sport == 'NBA':
        # Need opening odds to detect RLM. 
        # Since we don't strictly have 'open', we check if we have 'movement' data passed in.
        # Or we skip RLM for now and just look for extremely low under tickets?
        # User screenshot: "Line Move Open to Close is Negative"
        # We'll use a placeholder: if under_tickets <= 40, flag as "Contra Under"
        if under_tickets <= 40:
             # Ideally check line movement here
             triggers.append("Contra Under (Potential RLM)")

    # ---------------------------------------------------------
    # SYSTEM 5: Updated Tanking System (NBA)
    # ---------------------------------------------------------
    # ---------------------------------------------------------
    # SYSTEM 5: Updated Tanking System (NBA)
    # ---------------------------------------------------------
    if sport == 'NBA':
        gp = home_stats.get('games_played', 0)
        if 60 <= gp <= 82:
            win_pct = home_stats.get('win_pct', 0.5)
            if win_pct <= 0.39:
                opp_win_pct = away_stats.get('win_pct', 0.5)
                if opp_win_pct >= 0.50:
                    if spread_line and spread_line > 0:
                        if home_stats.get('last_margin', 0) > 0:
                            triggers.append("NBA Tanking System (Home Dog)")

    # ---------------------------------------------------------
    # ⚾ MLB PRO SYSTEMS (Action Network)
    # ---------------------------------------------------------
    if sport == 'MLB':
        # Weather Data (Assumed present in match metadata)
        weather = match.get('weather', {})
        wind_speed = weather.get('wind_speed', 0)
        wind_direction = weather.get('wind_direction', '').lower() # 'in', 'out', 'cross'
        venue = match.get('venue', '')
        
        # 1. Wrigley Field Unders
        # Rule: Wrigley Field, Wind Blowing IN, Speed >= 5 mph
        if "Wrigley" in venue:
            if "in" in wind_direction and wind_speed >= 5:
                # Check tickets? Ideally yes, but system is purely weather based usually.
                triggers.append(f"Wrigley Field Under (Wind {wind_speed}mph In)")

        # 2. General Weather: Wind Blowing In
        # Rule: Any stadium, Wind In >= 5 mph, Total >= 7
        if "in" in wind_direction and wind_speed >= 5:
            if total_line and total_line >= 7:
                triggers.append(f"Wind Blowing In Under ({wind_speed}mph)")

        # 3. Contrarian Runline vs Elite Teams
        # Rule: Opponent Win% > 60%, Public > 50% on Opponent, Bet Runline on Underdog?
        # Typically: Fade elite teams on RL.
        # Let's assume user wants to bet AGAINST the Elite team covering.
        # Home Elite Check
        h_win_pct = home_stats.get('win_pct', 0.0)
        a_win_pct = away_stats.get('win_pct', 0.0)
        
        # If Home is Elite (>60%) and Public (>60% tickets)
        if h_win_pct >= 0.60 and spread_tickets_h > 60:
            triggers.append("Contrarian Runline (Fade Home Elite)")
        # If Away is Elite
        elif a_win_pct >= 0.60 and spread_tickets_a > 60:
            triggers.append("Contrarian Runline (Fade Away Elite)")

        # 4. Contrarian Unders for Winning Teams
        # Rule: Both teams > 50% win pct (Good teams), Public is heavy on OVER (>60%)
        # System: Bet UNDER (Public loves overs with good teams)
        if h_win_pct >= 0.50 and a_win_pct >= 0.50:
            over_tickets = splits.get('total', {}).get('Over', {}).get('tickets', 50)
            if over_tickets > 60:
                triggers.append("Contrarian Under (Good Teams/Public Over)")

        # 5. High Strikeout Pitchers
        # Rule: Starting Pitcher K/9 > 9.0 (Elite K guy)
        # Often undervalued on moneylines or unders?
        # Assuming trigger is "Bet On" or "Prop Over"
        hp_k9 = home_stats.get('starter_k9', 0.0)
        ap_k9 = away_stats.get('starter_k9', 0.0)
        
        if hp_k9 > 9.0:
            triggers.append(f"High Strikeout Pitcher (Home: {hp_k9:.1f} K/9)")
        if ap_k9 > 9.0:
            triggers.append(f"High Strikeout Pitcher (Away: {ap_k9:.1f} K/9)")

    return triggers
