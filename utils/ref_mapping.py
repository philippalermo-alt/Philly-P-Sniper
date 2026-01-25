"""Referee assignment mapping utilities."""

def build_ref_map(assignments: list, game_key: str, delimiter: str) -> dict:
    """
    Build team->assignment lookup from raw assignments.
    
    Args:
        assignments: List of {'Game': 'Team A @ Team B', 'Officials': [...]}
        game_key: Key name for game string in dict
        delimiter: Separator in game string (e.g., '@' or ' at ')
    
    Returns:
        Dict mapping team names to their assignment dicts
    """
    ref_map = {}
    if not assignments:
        return ref_map

    for assignment in assignments:
        game_title = assignment.get(game_key, '')
        if delimiter not in game_title:
            continue
        
        parts = game_title.split(delimiter)
        if len(parts) != 2:
            continue
        
        away_raw, home_raw = [p.strip() for p in parts]
        ref_map[away_raw] = assignment
        ref_map[home_raw] = assignment
    
    return ref_map
