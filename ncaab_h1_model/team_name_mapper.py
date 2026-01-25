"""
Team Name Normalization for NCAAB
Maps different team name variations between ESPN APIs and sportsbooks.
"""

# Common team name mappings
TEAM_NAME_ALIASES = {
    # Appalachian State variations
    "Appalachian St Mountaineers": "App State Mountaineers",
    "Appalachian State Mountaineers": "App State Mountaineers",

    # UMass variations
    "Massachusetts Minutemen": "Massachusetts Minutemen",
    "UMass Minutemen": "Massachusetts Minutemen",

    # Louisiana variations
    "Louisiana Ragin Cajuns": "Louisiana Ragin' Cajuns",
    "Louisiana-Lafayette Ragin' Cajuns": "Louisiana Ragin' Cajuns",
    "UL Lafayette Ragin' Cajuns": "Louisiana Ragin' Cajuns",

    # UL Monroe
    "Louisiana-Monroe Warhawks": "UL Monroe Warhawks",

    # UNC variations
    "North Carolina Tar Heels": "North Carolina Tar Heels",
    "UNC Tar Heels": "North Carolina Tar Heels",

    # Miami variations
    "Miami (FL) Hurricanes": "Miami Hurricanes",
    "Miami FL Hurricanes": "Miami Hurricanes",

    # USC
    "Southern California Trojans": "USC Trojans",
    "USC (CA) Trojans": "USC Trojans",

    # UTEP
    "Texas-El Paso Miners": "UTEP Miners",
    "UT El Paso Miners": "UTEP Miners",

    # UT variations
    "Texas Longhorns": "Texas Longhorns",
    "UT Longhorns": "Texas Longhorns",

    # Add more as needed...
}

def normalize_team_name(team_name: str) -> str:
    """
    Normalize team name to match dataset.

    Args:
        team_name: Raw team name from odds API or user input

    Returns:
        Normalized team name that matches historical_games.json
    """
    # First check exact alias match
    if team_name in TEAM_NAME_ALIASES:
        return TEAM_NAME_ALIASES[team_name]

    # Try fuzzy matching for close variations
    import difflib
    aliases = list(TEAM_NAME_ALIASES.keys())
    matches = difflib.get_close_matches(team_name, aliases, n=1, cutoff=0.85)

    if matches:
        return TEAM_NAME_ALIASES[matches[0]]

    # No mapping found, return original
    return team_name

def build_reverse_mapping(team_names_in_dataset):
    """
    Build reverse mapping from dataset names to common variations.
    Useful for debugging which teams might be missing mappings.

    Args:
        team_names_in_dataset: Set of team names from historical_games.json

    Returns:
        Dict mapping dataset names to list of known aliases
    """
    reverse_map = {}

    for alias, canonical in TEAM_NAME_ALIASES.items():
        if canonical not in reverse_map:
            reverse_map[canonical] = []
        reverse_map[canonical].append(alias)

    # Add dataset names that have no aliases
    for team in team_names_in_dataset:
        if team not in reverse_map:
            reverse_map[team] = [team]

    return reverse_map
