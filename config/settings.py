import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """
    Configuration and constants for Philly P Sniper betting system.

    API Keys are loaded from environment variables without fallback defaults.
    """

    # Feature Flags
    ENABLE_SOCCER_V2 = True
    ENABLE_NBA_V2 = True
    # Phase 6 Deployment (Recs Only) - Allow Env Override, Default to TRUE for standardization
    NHL_TOTALS_V2_ENABLED = os.getenv('NHL_TOTALS_V2_ENABLED', 'True').lower() == 'true'

    # API Keys (environment variables only)
    ODDS_API_KEY = os.getenv('ODDS_API_KEY')
    KENPOM_API_KEY = os.getenv('KENPOM_API_KEY')
    FOOTBALL_API_KEY = os.getenv('FOOTBALL_API_KEY')
    ACTION_COOKIE = os.getenv('ACTION_COOKIE')
    # ACTION_COOKIE = os.getenv('ACTION_COOKIE') # Duplicate removed
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # Docker Override: If DB_HOST is set (e.g. valid hostname 'db'), use it.
    _db_host = os.getenv('DB_HOST')
    if _db_host:
         _db_user = os.getenv('DB_USER', 'postgres')
         _db_pass = os.getenv('DB_PASSWORD', 'postgres')
         _db_name = os.getenv('DB_NAME', 'philly_p_sniper')
         DATABASE_URL = f"postgresql://{_db_user}:{_db_pass}@{_db_host}:5432/{_db_name}"
    
    if not DATABASE_URL:
        # Fallback to localhost if neither are set
        DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/philly_p_sniper"
    DASHBOARD_PASSWORD = os.getenv('DASHBOARD_PASSWORD', 'phillyedge')
    
    # Telegram Alerts
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

    # Email Alerts (Recap)
    EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
    EMAIL_USER = os.getenv('EMAIL_USER')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    EMAIL_RECIPIENT = os.getenv('EMAIL_RECIPIENT')

    # Business Analytics (Default OpEx)
    SERVER_COST_MONTHLY = float(os.getenv('SERVER_COST_MONTHLY', 50.0))
    API_COST_MONTHLY = float(os.getenv('API_COST_MONTHLY', 0.0))

    # Twitter Automation
    TWITTER_CONSUMER_KEY = os.getenv('TWITTER_CONSUMER_KEY')
    TWITTER_CONSUMER_SECRET = os.getenv('TWITTER_CONSUMER_SECRET')
    TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
    TWITTER_ACCESS_TOKEN_SECRET = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

    # Bankroll Management
    BANKROLL = 1000.00
    KELLY_FRAC = 0.125
    MAX_STAKE_PCT = 0.06

    # Edge Thresholds
    MIN_EDGE = 0.00
    MAX_EDGE = 0.50
    MAX_PROBABILITY = 0.72
    SHARP_SIGNAL_THRESHOLD = 2

    # Market Weighting
    MARKET_WEIGHT_US = 0.15
    MARKET_WEIGHT_SOCCER = 0.65 # RELAXED (Was 0.80)

    # Debug Mode
    DEBUG_MODE = True

    # Sportsbooks
    PREFERRED_BOOKS = ['hardrockbet', 'draftkings', 'fanduel', 'betmgm', 'caesars', 'bovada']

    # Markets
    MAIN_MARKETS = 'h2h,spreads,totals'
    EXOTIC_MARKETS = 'h2h_h1,spreads_h1,totals_h1'
    PROP_MARKETS = 'player_shots_on_goal'

    # Sport-Specific Standard Deviations
    NBA_MARGIN_STD = 11.0
    NCAAB_MARGIN_STD = 11.0
    NFL_MARGIN_STD = 13.0
    NHL_MARGIN_STD = 1.8

    # Supported Leagues
    LEAGUES = [
        'basketball_nba', 'basketball_ncaab', 'americanfootball_nfl', 'icehockey_nhl',
        'soccer_epl', 'soccer_spain_la_liga', 'soccer_germany_bundesliga',
        'soccer_france_ligue_one', 'soccer_italy_serie_a', 'soccer_germany_bundesliga2',
        'soccer_efl_champ', 'soccer_uefa_champs_league', 'soccer_uefa_europa_league'
    ]

    # Soccer League IDs for Football API
    SOCCER_LEAGUE_IDS = {
        'soccer_epl': 39,
        'soccer_spain_la_liga': 140,
        'soccer_germany_bundesliga': 78,
        'soccer_france_ligue_one': 61,
        'soccer_italy_serie_a': 135,
        'soccer_germany_bundesliga2': 79,
        'soccer_efl_champ': 40,
        # 'soccer_efl_champ': 40, # Duplicate key in original
        'soccer_uefa_champs_league': 2,
        'soccer_uefa_europa_league': 3
    }
