import os

class Config:
    """
    Configuration and constants for Philly P Sniper betting system.

    API Keys are loaded from environment variables without fallback defaults.
    """

    # API Keys (environment variables only)
    ODDS_API_KEY = os.getenv('ODDS_API_KEY')
    KENPOM_API_KEY = os.getenv('KENPOM_API_KEY')
    FOOTBALL_API_KEY = os.getenv('FOOTBALL_API_KEY')
    ACTION_COOKIE = os.getenv('ACTION_COOKIE')
    DATABASE_URL = os.getenv('DATABASE_URL')

    # Bankroll Management
    BANKROLL = 451.16
    KELLY_FRAC = 0.125
    MAX_STAKE_PCT = 0.06

    # Edge Thresholds
    MIN_EDGE = 0.00
    MAX_EDGE = 0.50
    MAX_PROBABILITY = 0.72

    # Market Weighting
    MARKET_WEIGHT_US = 0.15
    MARKET_WEIGHT_SOCCER = 0.80

    # Debug Mode
    DEBUG_MODE = True

    # Sportsbooks
    PREFERRED_BOOKS = ['hardrockbet', 'draftkings', 'fanduel', 'betmgm', 'caesars', 'bovada']

    # Markets
    MAIN_MARKETS = 'h2h,spreads,totals'
    EXOTIC_MARKETS = 'h2h_h1,spreads_h1,totals_h1'

    # Sport-Specific Standard Deviations
    NBA_MARGIN_STD = 11.0
    NCAAB_MARGIN_STD = 9.5
    NFL_MARGIN_STD = 13.0
    NHL_MARGIN_STD = 1.8

    # Supported Leagues
    LEAGUES = [
        'basketball_nba', 'basketball_ncaab', 'americanfootball_nfl', 'icehockey_nhl',
        'soccer_epl', 'soccer_spain_la_liga', 'soccer_germany_bundesliga',
        'soccer_france_ligue_one', 'soccer_italy_serie_a', 'soccer_germany_bundesliga2',
        'soccer_efl_champ'
    ]

    # Soccer League IDs for Football API
    SOCCER_LEAGUE_IDS = {
        'soccer_epl': 39,
        'soccer_spain_la_liga': 140,
        'soccer_germany_bundesliga': 78,
        'soccer_france_ligue_one': 61,
        'soccer_italy_serie_a': 135,
        'soccer_germany_bundesliga2': 79,
        'soccer_efl_champ': 40
    }
