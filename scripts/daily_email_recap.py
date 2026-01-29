import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import pytz
import pandas as pd
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.connection import get_db
from config.settings import Config
from utils.logging import log

def get_yesterday_range():
    """Get start and end UTC timestamps for Yesterday (ET)."""
    eastern = pytz.timezone('US/Eastern')
    now = datetime.now(eastern)
    yesterday = now - timedelta(days=1)
    
    start_et = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end_et = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    start_utc = start_et.astimezone(pytz.utc)
    end_utc = end_et.astimezone(pytz.utc)
    
    return start_utc, end_utc, yesterday.strftime('%Y-%m-%d')

def categorize_odds(odds):
    if odds < 1.50: return "Heavy Favorites (<1.50)"
    if 1.50 <= odds <= 2.20: return "Coin Flip (1.50-2.20)"
    if 2.20 < odds <= 3.00: return "Small Dogs (2.20-3.00)"
    return "Longshots (>3.00)"

def categorize_market(selection, market_col=None):
    # If explicit market column exists (from recent schema updates), use it.
    # Otherwise infer from selection.
    sel = str(selection).lower()
    if 'over' in sel or 'under' in sel: return "Total"
    if ' ml' in sel or 'moneyline' in sel: return "Moneyline"
    if '+' in sel or '-' in sel: return "Spread" # Crude but likely sufficient for now
    return "Prop/Other"

def fetch_data(start_utc, end_utc):
    conn = get_db()
    if not conn:
        log("ERROR", "Could not connect to DB")
        return pd.DataFrame() 
    
    try:
        # Contract Section 2.C & 4.A: Filter by settled_at
        query = """
            SELECT 
                sport, 
                selection, 
                odds, 
                edge, 
                outcome, 
                stake,
                net_units,
                settled_at,
                accepted
            FROM intelligence_log
            WHERE outcome IN ('WON', 'LOST', 'PUSH')
            AND settled_at >= %s AND settled_at < %s
            AND accepted = TRUE
            AND edge > 0
        """
        df = pd.read_sql(query, conn, params=(start_utc, end_utc))
        return df
    except Exception as e:
        log("ERROR", f"Query failed: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def validate_contract_states(df):
    """
    Contract Section 5: Forbidden States (Auto-Fail).
    Returns (bool, str): (Passed, Reason)
    """
    if df.empty: return True, "Empty"

    # 1. Average Edge < 0 (Data Integrity Fail)
    if 'edge' in df.columns and df['edge'].mean() < 0:
        return False, f"Average Edge is Negative ({df['edge'].mean()})"
        
    # 2. Accepted = False (Leakage)
    if 'accepted' in df.columns and not df['accepted'].all():
        return False, "Found unaccepted bets in recap set."

    # 3. Null Attributes
    if df['outcome'].isnull().any(): return False, "Null Outcome found."
    if df['settled_at'].isnull().any(): return False, "Null Settled Timestamp found."
    if df['net_units'].isnull().any(): return False, "Null Net Units found."

    # 4. Net Units Sum Check (floating point tolerance)
    calc_sum = df['net_units'].sum()
    if abs(calc_sum) > 100000: # sanity check
        return False, f"Implausible Net Units Sum: {calc_sum}"

    return True, "OK"

def send_email(subject, html_body):
    sender = Config.EMAIL_USER
    password = Config.EMAIL_PASSWORD
    recipient = Config.EMAIL_RECIPIENT
    host = Config.EMAIL_HOST
    port = Config.EMAIL_PORT
    
    if not all([sender, password, recipient, host]):
        log("ERROR", "Email configuration missing.")
        return False

    msg = MIMEMultipart("alternative")
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient

    part = MIMEText(html_body, 'html')
    msg.attach(part)

    try:
        server = smtplib.SMTP(host, port)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        log("INFO", f"Email sent successfully to {recipient}")
        return True
    except Exception as e:
        log("ERROR", f"Failed to send email: {e}")
        return False

def generate_report():
    start_utc, end_utc, yesterday_str = get_yesterday_range()
    
    # User Request: Show Eastern Time in Logs
    est = pytz.timezone('US/Eastern')
    start_et = start_utc.astimezone(est)
    end_et = end_utc.astimezone(est)
    
    log("INFO", f"Generating Recap for {yesterday_str} (Settlement Window: {start_et} to {end_et} ET)")
    
    df = fetch_data(start_utc, end_utc)
    
    # Contract Section 6: Recap Self-Audit
    if not df.empty:
        total_bets = len(df)
        sum_net = df['net_units'].sum()
        avg_edge = df['edge'].mean() if 'edge' in df else 0
        min_settle = df['settled_at'].min()
        max_settle = df['settled_at'].max()
        
        log("AUDIT", f"Total Bets: {total_bets}")
        log("AUDIT", f"Net Units Sum: {sum_net:.2f}")
        log("AUDIT", f"Avg Edge: {avg_edge:.4f}")
        log("AUDIT", f"Settlement Window: {min_settle} - {max_settle}")
        
    # Contract Section 5: Forbidden State Check
    passed, reason = validate_contract_states(df)
    if not passed:
        error_msg = f"⛔ RECAP BLOCKED BY CONTRACT: {reason}"
        log("ERROR", error_msg)
        send_email(f"⚠️ Recap Failure: {yesterday_str}", f"<h3>Contract Violation</h3><p>{reason}</p>")
        return

    if df.empty:
        log("INFO", "No settled bets found in window.")
        send_email(
            f"Daily Performance Recap - {yesterday_str}",
            "<h3>No settled activity for yesterday.</h3>"
        )
        return

    # --- Feature Engineering ---
    # Profit Calculation: TRUST THE DB (Contract Section 4.B)
    # We DO NOT recompute pnl from odds here. We use 'net_units'.
    df['stake'] = df['stake'].fillna(1.0)
    df['result'] = df['outcome'].apply(lambda x: 1 if x == 'WON' else 0)
    df['market_type'] = df.apply(lambda x: categorize_market(x['selection']), axis=1)
    df['odds_bucket'] = df['odds'].apply(categorize_odds)

    # --- High Level Summary ---
    total_bets = len(df)
    total_won = len(df[df['outcome'] == 'WON'])
    win_rate = (total_won / total_bets) * 100
    total_staked = df['stake'].sum()
    net_units = df['net_units'].sum() # Using DB value
    roi = (net_units / total_staked * 100) if total_staked > 0 else 0.0

    # --- Breakdowns ---
    
    # By Sport
    sport_grp = df.groupby('sport').agg({
        'selection': 'count',
        'net_units': 'sum',
        'stake': 'sum'
    }).rename(columns={'selection': 'Bets', 'net_units': 'Net Units', 'stake': 'Staked'})
    sport_grp['ROI'] = (sport_grp['Net Units'] / sport_grp['Staked'] * 100).round(2)
    sport_grp['Net Units'] = sport_grp['Net Units'].round(2)
    
    # By Market
    market_grp = df.groupby('market_type').agg({
        'selection': 'count',
        'net_units': 'sum',
        'stake': 'sum'
    }).rename(columns={'selection': 'Bets', 'net_units': 'Net Units', 'stake': 'Staked'})
    
    market_grp['ROI'] = (market_grp['Net Units'] / market_grp['Staked'] * 100).round(2)
    market_grp['Net Units'] = market_grp['Net Units'].round(2)
    
    # By Odds Bucket
    odds_grp = df.groupby('odds_bucket').agg({
        'selection': 'count',
        'net_units': 'sum',
        'stake': 'sum',
        'result': 'mean' # Win rate
    }).rename(columns={'selection': 'Bets', 'net_units': 'Net Units', 'stake': 'Staked', 'result': 'Win Rate'})
    
    odds_grp['ROI'] = (odds_grp['Net Units'] / odds_grp['Staked'] * 100).round(2)
    odds_grp['Win Rate'] = (odds_grp['Win Rate'] * 100).round(1)
    odds_grp['Net Units'] = odds_grp['Net Units'].round(2)
    
    # --- Diagnostics ---
    avg_edge = df['edge'].mean() * 100 # Assuming edge is 0.05 for 5%
    if avg_edge < 1: avg_edge *= 100 # Handle if it was already decimal 0.0005? Usually 0.05
    # Check if edge is stored as percentage or decimal in DB.
    # Usually stored as decimal (0.05).
    # Safety clamp: if mean > 10, assumes it's percentage already.
    if df['edge'].mean() > 1.0: # Likely percentage
         avg_edge = df['edge'].mean()
    else:
         avg_edge = df['edge'].mean() * 100

    # --- Flags ---
    best_bet_row = df[df['outcome'] == 'WON'].sort_values('edge', ascending=False).head(1)
    worst_loss_row = df[df['outcome'] == 'LOST'].sort_values('stake', ascending=False).head(1)
    
    best_bet_str = "None"
    if not best_bet_row.empty:
        r = best_bet_row.iloc[0]
        best_bet_str = f"{r['sport']} - {r['selection']} (@ {r['odds']}) | Edge: {r['edge']:.1%}"
        
    worst_loss_str = "None"
    if not worst_loss_row.empty:
        r = worst_loss_row.iloc[0]
        worst_loss_str = f"{r['sport']} - {r['selection']} (@ {r['odds']}) | Loss: {r['stake']:.2f}u"

    # ROI Flag
    roi_flag_html = ""
    for idx, row in odds_grp.iterrows():
        if row['ROI'] < -5.0:
            roi_flag_html += f"<li>⚠️ <b>{idx}</b>: {row['ROI']}% ROI</li>"

    # --- HTML Styling ---
    # Simple CSS
    style = """
    <style>
        body { font-family: Arial, sans-serif; color: #333; }
        h1 { color: #2c3e50; }
        h2 { color: #34495e; border-bottom: 1px solid #eee; padding-bottom: 5px; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .win { color: green; }
        .loss { color: red; }
        .warning { color: orange; font-weight: bold; }
    </style>
    """
    
    color_class = "win" if net_units >= 0 else "loss"
    
    html = f"""
    <html>
    <head>{style}</head>
    <body>
        <h1>Daily Performance Recap</h1>
        <p><b>Date:</b> {yesterday_str}</p>
        
        <h2>High-Level Summary</h2>
        <p>
            <b>Total Bets:</b> {total_bets}<br>
            <b>Net Units:</b> <span class="{color_class}">{net_units:+.2f}u</span><br>
            <b>ROI:</b> <span class="{color_class}">{roi:+.2f}%</span><br>
            <b>Win Rate:</b> {win_rate:.1f}%
        </p>

        <h2>Breakdown by Sport</h2>
        {sport_grp.to_html(classes='table', columns=['Bets', 'Net Units', 'ROI'], border=0)}

        <h2>Breakdown by Market</h2>
        {market_grp.to_html(classes='table', columns=['Bets', 'Net Units', 'ROI'], border=0)}
        
        <h2>Breakdown by Odds Bucket</h2>
        {odds_grp.to_html(classes='table', columns=['Bets', 'Net Units', 'ROI', 'Win Rate'], border=0)}
        
        <h2>Diagnostics</h2>
        <p><b>Avg Accepted Edge:</b> {avg_edge:.2f}%</p>
        
        <h2>Notable Flags</h2>
        <ul>
            <li><b>Best Bet (High Edge Win):</b> {best_bet_str}</li>
            <li><b>Worst Loss (High Stake):</b> {worst_loss_str}</li>
            {roi_flag_html}
        </ul>
        
        <p><i>Generated by Philly-P-Sniper</i></p>
    </body>
    </html>
    """
    
    # Send
    send_email(f"Daily Performance Recap - {yesterday_str}", html)

if __name__ == "__main__":
    generate_report()
