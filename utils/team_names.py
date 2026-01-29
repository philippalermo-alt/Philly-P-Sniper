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

    # NHL Specific Aliases
    aliases = {
        "utah mammoth": "utah",
        "utah hockey club": "utah",
        "montréal canadiens": "montreal canadiens",
        "st louis blues": "st. louis blues",
        "st. louis blues": "st. louis blues", 
        "fla": "florida panthers",
        "wsh": "washington capitals",
        "tb": "tampa bay lightning",
        "nj": "new jersey devils",
        "nyi": "new york islanders",
        "nyr": "new york rangers",
        "la": "los angeles kings",
        "sj": "san jose sharks",
        "vgk": "vegas golden knights",
        "iu indianapolis": "iupui",
        "iu indianapolis jaguars": "iupui jaguars",
        "kansas city": "umkc",
        "kansas city roos": "umkc kangaroos",
        
        # Soccer Aliases
        "inter milan": "inter",
        "internazionale": "inter",
        "as monaco": "monaco",
        "tottenham hotspur": "tottenham",
        "spurs": "tottenham",
        "athletic bilbao": "athletic club",
        "atlético madrid": "atletico madrid",
        "atletico de madrid": "atletico madrid",
        "sporting lisbon": "sporting cp", 
        "psv eindhoven": "psv",
        "ajax amsterdam": "ajax",
        "atalanta bc": "atalanta"
    }
    if n in aliases:
        return aliases[n]

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

def robust_match_team(target, candidates, threshold=0.85):
    """
    Robust matching strategy with Token Overlap Enforcement.
    Prevents "UMKC" -> "UCF" by requiring shared identity tokens.
    
    Args:
        target: Target team name (e.g. "UMKC Kangaroos")
        candidates: List of candidate names
        threshold: Minimum similarity score (default 0.85)
        
    Returns:
        Best match from candidates or None.
    """
    import difflib
    
    n_target = normalize_team_name(target)
    
    # 1. Exact Match (Fast Path)
    # Check normalized candidates
    # Wait, simple 'in' check is faster if candidates are raw
    # We'll stick to logic flow.
    
    STOPWORDS = {"state", "st", "university", "tech", "college", "north", "south", "east", "west", "the", "a", "of"}
    
    target_tokens = set([t for t in n_target.split() if t not in STOPWORDS])
    
    best_match = None
    best_score = 0.0
    
    # 2. Iterate candidates
    for cand in candidates:
        n_cand = normalize_team_name(cand)
        
        # A. Exact Match
        if n_cand == n_target:
            return cand
            
        # B. Startswith (High Confidence for NCAA)
        # "Duke" starts with "Duke"
        if n_cand.startswith(n_target) or n_target.startswith(n_cand):
            # If significant overlap? "Ken" starts with "Kentucky" (No). "Kentucky" starts with "Ken" (Yes).
            # Safety: Length ratio check.
            # Only if length difference isn't massive logic?
            # Actually, Startswith is dangerous if input is "San" -> "San Diego".
            # Skip broad startswith without token overlap.
            pass

        # C. Token Overlap Constraint
        cand_tokens = set([t for t in n_cand.split() if t not in STOPWORDS])
        
        # Strict Rule: Must share at least one meaningful token
        # Exception: If target or cand is very short/acronym?
        # Let's assume normalization handles acronyms (e.g. ucf -> central florida).
        
        if not target_tokens.isdisjoint(cand_tokens):
            # Shared Token Exists
            # Calculate Similarity
            ratio = difflib.SequenceMatcher(None, n_target, n_cand).ratio()
            
            # BOOST for Startswith (High Confidence)
            # e.g. "Duke" (4) vs "Duke Blue Devils". n_cand starts with n_target.
            # Safety: Length > 3 prevents broad "San" matches if not token overlapped.
            # But we ARE inside token overlap check, so it's safer.
            if len(n_target) > 3 and (n_cand.startswith(n_target) or n_target.startswith(n_cand)):
                 ratio = max(ratio, 0.90)

            if ratio >= threshold:
                if ratio > best_score:
                     best_score = ratio
                     best_match = cand
    
    return best_match
