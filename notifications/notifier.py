
import requests
import json
from config import Config
from utils import log

def send_alert(message):
    """
    Send a message to the configured Telegram chat.
    Args:
        message (str): The plain text or MarkdownV2 message to send.
    """
    token = Config.TELEGRAM_BOT_TOKEN
    chat_id = Config.TELEGRAM_CHAT_ID
    
    if not token or not chat_id:
        log("WARN", "Telegram credentials missing. Alert skipped.")
        return False
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "MarkdownV2"
    }
    
    try:
        res = requests.post(url, json=payload, timeout=5)
        if res.status_code != 200:
            log("ERROR", f"Telegram Alert Failed: {res.text}")
            return False
        return True
    except Exception as e:
        log("ERROR", f"Telegram Connection Failed: {e}")
        return False

def escape_md(text):
    """Helper to escape MarkdownV2 special characters."""
    special_chars = r'_*[]()~`>#+-=|{}.!'
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text

def format_opportunity(opp):
    """
    Format a betting opportunity into a clean Telegram alert.
    EMOJI KEY:
    🔥 = 5%+ Edge
    🦅 = Valid Snipe
    """
    edge_val = opp.get('Edge_Val', 0)
    emoji = "🔥" if edge_val >= 0.05 else "🦅"
    
    sport = escape_md(opp.get('Sport', 'General'))
    event = escape_md(opp.get('Event', 'Match'))
    sel = escape_md(opp.get('Selection', 'Pick'))
    
    # Format Odds: +150 or -110
    dec_odds = opp.get('Dec_Odds', 0)
    us_odds = int((dec_odds - 1) * 100) if dec_odds >= 2.0 else int(-100 / (dec_odds - 1))
    odds_fmt = f"{us_odds:+}" if us_odds > 0 else f"{us_odds}"
    odds_fmt = escape_md(odds_fmt)
    
    edge_txt = escape_md(opp.get('Edge', '0%'))
    stake_txt = escape_md(opp.get('Stake', '$0'))
    
    msg = (
        f"{emoji} *PHILLY EDGE ALERT* {emoji}\n\n"
        f"🏆 *{sport}*\n"
        f"🏟 {event}\n"
        f"🎯 *{sel}* @ *{odds_fmt}*\n\n"
        f"💰 Edge: *{edge_txt}*\n"
        f"💵 Rec\\. Stake: {stake_txt}\n\n"
        f"Powered by PhillyEdge 🦅"
    )
    
    return msg
