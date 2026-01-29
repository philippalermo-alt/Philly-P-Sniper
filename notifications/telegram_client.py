import requests
import json
from config.settings import Config
from utils.logging import log

def send_telegram_alert(message: str) -> bool:
    """
    Send a message to the configured Telegram Chat.
    Returns True if successful, False otherwise.
    Note: Does NOT throw exceptions (logs errors instead).
    """
    token = Config.TELEGRAM_BOT_TOKEN
    chat_id = Config.TELEGRAM_CHAT_ID
    
    if not token or not chat_id:
        log("WARN", "Telegram Token or Chat ID missing. Skipping alert.")
        return False
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML" # Optional, but good for formatting
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code == 200:
            return True
        else:
            log("ERROR", f"Telegram Send Failed: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        log("ERROR", f"Telegram Connection Error: {e}")
        return False

def format_telegram_message(bet: dict) -> str:
    """
    Format a bet dictionary OR Opportunity object into a user-friendly Telegram message.
    """
    # Helper to get value from dict or object
    def get_val(obj, key, alt_keys=None, default=None):
        # Try dict access
        if isinstance(obj, dict):
            val = obj.get(key)
            if val is not None: return val
            if alt_keys:
                for atk in alt_keys:
                    val = obj.get(atk)
                    if val is not None: return val
            return default
        # Try object attribute
        val = getattr(obj, key, None)
        if val is not None: return val
        if alt_keys:
            for atk in alt_keys:
                val = getattr(obj, atk, None)
                if val is not None: return val
        return default

    # Extract Data
    sport = str(get_val(bet, 'sport', default='Unknown')).upper()
    sport = sport.replace('BASKETBALL_', '').replace('ICEHOCKEY_', '').replace('AMERICANFOOTBALL_', '')
    
    # Teams
    home = get_val(bet, 'home_team', ['HomeTeam'], 'Unknown')
    away = get_val(bet, 'away_team', ['AwayTeam'], 'Unknown')
    
    # If "teams" string exists (e.g. "Away @ Home"), use it if individual teams missing
    teams_str = get_val(bet, 'teams')
    if teams_str and (home == 'Unknown' or away == 'Unknown'):
         event = teams_str
    else:
         event = f"{away} @ {home}"

    pick = get_val(bet, 'selection', ['Selection'], 'Pick')
    book = get_val(bet, 'book', ['Book'], 'Unknown')
    
    # Numerical
    odds = float(get_val(bet, 'odds', ['odds_decimal', 'Dec_Odds', 'price'], 0.0))
    edge = float(get_val(bet, 'edge', ['edge_val', 'Edge_Val'], 0.0)) * 100
    prob = float(get_val(bet, 'true_prob', ['model_prob', 'True_Prob'], 0.0)) * 100
    stake = float(get_val(bet, 'stake', ['kelly_stake', 'Stake'], 0.0)) 
    
    # Run ID
    run_id = get_val(bet, 'run_id', default='N/A')
    
    # Emoji
    sport_emoji = "🏀" if 'NBA' in sport or 'NCAAB' in sport else "🏒" if 'NHL' in sport else "🏈" if 'NFL' in sport else "⚽"
    
    msg = (
        f"{sport_emoji} <b>{sport}</b>\n"
        f"{event}\n"
        f"<b>Pick:</b> {pick}\n"
        f"<b>Odds:</b> {odds:.2f} ({book})\n"
        f"Model: {prob:.1f}% | Edge: +{edge:.1f}% | Stake: {stake:.2f}u\n"
        f"<i>Run: {run_id}</i>"
    )
    return msg
