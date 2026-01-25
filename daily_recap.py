
import psycopg2
from datetime import datetime, timedelta
from config import Config
from utils import log
import requests

def send_telegram(message):
    if not Config.TELEGRAM_BOT_TOKEN or not Config.TELEGRAM_CHAT_ID:
        log("NOTIFIER", "❌ Telegram creds missing")
        return False
    
    url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': Config.TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        requests.post(url, json=payload, timeout=10)
        return True
    except Exception as e:
        log("NOTIFIER", f"❌ Failed to send Telegram: {e}")
        return False

def generate_daily_recap():
    """
    Generate W-L-P, P/L, ROI report for Yesterday's games.
    Runs at 7AM, so "Yesterday" = (Now - 1 Day).
    """
    log("RECAP", "Generating Daily Recap...")
    
    # 1. Define "Yesterday" window (00:00 to 23:59 local time? Or simply distinct date)
    # Assuming server time is used for storage.
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    conn = psycopg2.connect(Config.DATABASE_URL)
    cur = conn.cursor()
    
    # Query bets where kickoff::date = yesterday
    # And outcome is settled (WON/LOST/PUSH)
    # We filter by user_bet=True (Actual user action) OR all? 
    # User said "yesterdays results" implying model performance? 
    # But usually P/L assumes money.
    # Let's count "Active" bets (stake > 0 or user_bet = True)
    # Querying ALL settled bets for coverage.
    
    query = """
        SELECT sport, outcome, user_stake, user_odds 
        FROM intelligence_log 
        WHERE date(kickoff) = %s 
        AND outcome IN ('WON', 'LOST', 'PUSH', 'HALF_WIN', 'HALF_LOSS')
    """
    
    cur.execute(query, (yesterday,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    if not rows:
        log("RECAP", "No settled bets found for yesterday.")
        # Optional: Send "No Action Yesterday" msg?
        send_telegram(f"📉 **Daily Recap ({yesterday})**\nNo settled bets found.")
        return

    # 2. Aggregate by Sport
    stats = {}
    total_pnl = 0.0
    total_stake = 0.0
    
    for sport, outcome, stake, odds in rows:
        if not stake: stake = 100.0 # Default unit if missing? Or 0?
        if not odds: odds = 1.91
        
        # Clean sport name
        sport_name = sport.replace('basketball_', '').replace('americanfootball_', '').replace('icehockey_', '').replace('soccer_', '').upper()
        
        if sport_name not in stats:
            stats[sport_name] = {'W': 0, 'L': 0, 'P': 0, 'PnL': 0.0, 'Stake': 0.0}
            
        rec = stats[sport_name]
        rec['Stake'] += stake
        total_stake += stake
        
        pnl = 0.0
        if outcome == 'WON':
            rec['W'] += 1
            pnl = stake * (odds - 1)
        elif outcome == 'LOST':
            rec['L'] += 1
            pnl = -stake
        elif outcome == 'PUSH':
            rec['P'] += 1
            pnl = 0.0
        # Handle halves if present (rare)
        
        rec['PnL'] += pnl
        total_pnl += pnl

    # 3. Format Report
    # 📝 **Daily Recap (Mon Jan 21)**
    #
    # 🏀 **NBA**
    # 2-1-0 | +$150.00 | +12.5%
    #
    # ⚾️ **MLB**
    # 0-2-0 | -$200.00 | -100%
    #
    # 💰 **TOTAL**: +$50.00 (ROI: +2.1%)
    
    # 3. Format Report (HTML & Text)
    # 📝 **Daily Recap (Mon Jan 21)**
    
    msg_lines = [f"📝 **Daily Recap ({yesterday.strftime('%a %b %d')})**"]
    
    # HTML Builder
    html_parts = [
        f"<h2>📝 Daily Recap ({yesterday.strftime('%a %b %d')})</h2>",
        "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse; width: 100%; font-family: Arial, sans-serif;'>",
        "<tr style='background-color: #f2f2f2;'><th>Sport</th><th>Record</th><th>P/L</th><th>ROI</th></tr>"
    ]
    
    sorted_sports = sorted(stats.keys())
    
    for s in sorted_sports:
        d = stats[s]
        roi = (d['PnL'] / d['Stake']) * 100 if d['Stake'] > 0 else 0.0
        
        # Icon
        icon = "🏅"
        if "NBA" in s or "NCAAB" in s: icon = "🏀"
        elif "NFL" in s: icon = "🏈"
        elif "NHL" in s: icon = "🏒"
        elif "MLB" in s: icon = "⚾️"
        elif "SOCCER" in s or "EPL" in s: icon = "⚽️"
        
        # Text Line
        line1 = f"{icon} **{s}**"
        line2 = f"{d['W']}-{d['L']}-{d['P']} | ${d['PnL']:+.2f} | {roi:+.1f}%"
        
        msg_lines.append("")
        msg_lines.append(line1)
        msg_lines.append(line2)
        
        # HTML Row
        color = "green" if d['PnL'] >= 0 else "red"
        html_parts.append(
            f"<tr><td>{icon} {s}</td><td>{d['W']}-{d['L']}-{d['P']}</td><td style='color:{color}; font-weight:bold;'>${d['PnL']:+.2f}</td><td>{roi:+.1f}%</td></tr>"
        )
        
    msg_lines.append("")
    tot_roi = (total_pnl / total_stake) * 100 if total_stake > 0 else 0.0
    msg_lines.append(f"💰 **TOTAL**: ${total_pnl:+.2f} (ROI: {tot_roi:+.1f}%)")
    
    # HTML Footer
    tot_color = "green" if total_pnl >= 0 else "red"
    html_parts.append("</table>")
    html_parts.append(f"<h3>💰 TOTAL: <span style='color:{tot_color};'>${total_pnl:+.2f}</span> (ROI: {tot_roi:+.1f}%)</h3>")
    
    full_msg = "\n".join(msg_lines)
    full_html = "\n".join(html_parts)
    
    print(full_msg) # Log to stdout
    
    # Send Telegram (Legacy)
    send_telegram(full_msg)
    
    # Send Email (New)
    from email_notifier import EmailNotifier
    emailer = EmailNotifier()
    emailer.send_email(
        subject=f"Philly P Sniper Recap: {yesterday.strftime('%a %b %d')}",
        body=full_html,
        is_html=True
    )

if __name__ == "__main__":
    generate_daily_recap()
