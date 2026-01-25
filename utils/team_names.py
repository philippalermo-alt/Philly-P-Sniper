def normalize_team_name(name):
    """
    Normalize team name for matching (lowercase, remove descriptors).
    """
    if not name:
        return ""
    n = name.lower().strip()
    
    # Common Abbreviations
    n = n.replace("ok ", "oklahoma ")\
         .replace("nc ", "north carolina ")\
         .replace("lsu", "louisiana st")\
         .replace("ole miss", "mississippi")\
         .replace("uconn", "connecticut")\
         .replace("smu", "southern methodist")\
         .replace("ucf", "central florida")\
         .replace("vcu", "virginia commonwealth")

    return n.replace(" university", "").replace(" state", " st").replace(" saints", "").replace(" fighting", "")

def match_team(target, candidates):
    """
    Find best match for 'target' in 'candidates' list.
    Uses normalized simple containment.
    
    Args:
        target: The name we are looking for (e.g. "Ohio State")
        candidates: List of available names (e.g. from ESPN)
        
    Returns:
        The matching name from candidates, or None.
    """
    n_target = normalize_team_name(target)
    
    best_match = None
    # 1. Exact Normal Match
    for c in candidates:
        if normalize_team_name(c) == n_target:
            return c
            
    # 2. Containment
    for c in candidates:
        nc = normalize_team_name(c)
        if n_target in nc or nc in n_target:
            return c
            
    return None
