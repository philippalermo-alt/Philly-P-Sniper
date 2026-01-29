# Canonical Team Mapping for NHL Phase 2
# Aligns Odds API, MoneyPuck, and NHL Reference to standard 3-letter codes.

TEAM_MAPPING = {
    # CRITICAL: Handle Variations
    "Montréal Canadiens": "MTL",
    "Montreal Canadiens": "MTL",
    "St Louis Blues": "STL",
    "St. Louis Blues": "STL",
    "Tampa Bay Lightning": "TBL",
    "T.B": "TBL",
    "Los Angeles Kings": "LAK",
    "L.A": "LAK",
    "New Jersey Devils": "NJD",
    "N.J": "NJD",
    "San Jose Sharks": "SJS",
    "S.J": "SJS",
    "Utah Hockey Club": "UTA",
    "Utah Mammoth": "UTA",
    
    # Standard Full Names (Odds API / Ref)
    "Anaheim Ducks": "ANA",
    "Arizona Coyotes": "ARI",
    "Boston Bruins": "BOS",
    "Buffalo Sabres": "BUF",
    "Calgary Flames": "CGY",
    "Carolina Hurricanes": "CAR",
    "Chicago Blackhawks": "CHI",
    "Colorado Avalanche": "COL",
    "Columbus Blue Jackets": "CBJ",
    "Dallas Stars": "DAL",
    "Detroit Red Wings": "DET",
    "Edmonton Oilers": "EDM",
    "Florida Panthers": "FLA",
    "Minnesota Wild": "MIN",
    "Nashville Predators": "NSH",
    "New York Islanders": "NYI",
    "New York Rangers": "NYR",
    "Ottawa Senators": "OTT",
    "Philadelphia Flyers": "PHI",
    "Pittsburgh Penguins": "PIT",
    "Seattle Kraken": "SEA",
    "Toronto Maple Leafs": "TOR",
    "Vancouver Canucks": "VAN",
    "Vegas Golden Knights": "VGK",
    "Washington Capitals": "WSH",
    "Winnipeg Jets": "WPG",
    
    # Pass-through for already correct codes (ensure Upper)
    "ANA": "ANA", "ARI": "ARI", "BOS": "BOS", "BUF": "BUF", "CAR": "CAR",
    "CBJ": "CBJ", "CGY": "CGY", "CHI": "CHI", "COL": "COL", "DAL": "DAL",
    "DET": "DET", "EDM": "EDM", "FLA": "FLA", "LAK": "LAK", "MIN": "MIN",
    "MTL": "MTL", "NJD": "NJD", "NSH": "NSH", "NYI": "NYI", "NYR": "NYR",
    "OTT": "OTT", "PHI": "PHI", "PIT": "PIT", "SEA": "SEA", "SJS": "SJS",
    "STL": "STL", "TBL": "TBL", "TOR": "TOR", "UTA": "UTA", "VAN": "VAN",
    "VGK": "VGK", "WPG": "WPG", "WSH": "WSH"
}

def normalize_team(name):
    """
    Normalize a team name/abbr to the canonical 3-letter code.
    """
    if not isinstance(name, str):
        return None
    
    clean_name = name.strip()
    
    # Direct Lookup
    if clean_name in TEAM_MAPPING:
        return TEAM_MAPPING[clean_name]
        
    # Case insensitive check
    for k, v in TEAM_MAPPING.items():
        if k.lower() == clean_name.lower():
            return v
            
    # Return original if 3 letters? Or flag error?
    # For fail-safe, return Upper if length 3
    if len(clean_name) == 3:
        return clean_name.upper()
        
    return f"UNKNOWN({clean_name})"
