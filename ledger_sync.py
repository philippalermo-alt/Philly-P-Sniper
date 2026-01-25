import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, timedelta
from database import get_db
from dotenv import load_dotenv

load_dotenv()

# Constants
SHEET_NAME = "Philly Edge - Official Ledger" # User can rename this
CREDENTIALS_FILE = "credentials.json"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

def get_google_client():
    if not os.path.exists(CREDENTIALS_FILE):
        print("❌ credentials.json not found. Skipping Google Sync.")
        return None
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"❌ Google Auth Error: {e}")
        return None

def sync_ledger(days_back=1):
    """
    Fetches confirmed picks (or validated passing picks) and appends to Sheet.
    Default: Last 24 hours.
    """
    client = get_google_client()
    if not client: return

    try:
        # Open Sheet
        try:
            sheet = client.open(SHEET_NAME).sheet1
        except gspread.SpreadsheetNotFound:
            print(f"❌ Sheet '{SHEET_NAME}' not found. Please create it or share it with the service account.")
            return

        # Fetch Data (The Sweet Spot: 3-15% Edge)
        conn = get_db()
        if not conn: return
        
        # We want PENDING bets that match our criteria
        # Or should we log bets the user *actually* took? 
        # User asked for "Export" of the picks, implied auto-publishing the model's best.
        # Let's stick to the "Validated Picks" logic: 3-15% Edge, >60 Sharp Score? 
        # Or just the Edge filter we used in the CSV.
        
        query = """
            SELECT kickoff, sport, teams, selection, odds, edge
            FROM intelligence_log
            WHERE edge >= 0.03 
              AND edge <= 0.15
              AND kickoff >= NOW() - INTERVAL '24 HOURS'
              AND outcome = 'PENDING'
            ORDER BY kickoff ASC
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        if df.empty:
            print("ℹ️ No new picks to sync.")
            return

        # Format Data
        # Date | Sport | Event | Selection | Odds | Edge
        # Kickoff is in UTC/Eastern - need to ensure string format
        
        # Determine existing rows to avoid duplicates?
        # A simple way is to read the sheet and check "Event + Selection" combo.
        # For now, let's just append and assume the scheduler runs once per block.
        
        existing_data = sheet.get_all_records()
        existing_keys = set()
        if existing_data:
            for row in existing_data:
                # Create a composite key: Event + Selection
                k = f"{row.get('Event')}_{row.get('Selection')}"
                existing_keys.add(k)
                
        new_rows = []
        for _, row in df.iterrows():
            k = f"{row['teams']}_{row['selection']}"
            if k in existing_keys:
                continue
            
            # Formatting
            kickoff_str = row['kickoff'].strftime('%Y-%m-%d %H:%M')
            edge_pct = f"{float(row['edge'])*100:.1f}%"
            odds_fmt = f"{float(row['odds']):.2f}"
            
            new_rows.append([
                kickoff_str,
                row['sport'].split('_')[-1].upper(),
                row['teams'],
                row['selection'],
                odds_fmt,
                edge_pct
            ])
            
        if new_rows:
            sheet.append_rows(new_rows)
            print(f"✅ Synced {len(new_rows)} picks to Google Sheet.")
        else:
            print("ℹ️ All picks already up to date.")

    except Exception as e:
        print(f"❌ Ledger Sync Error: {e}")

if __name__ == "__main__":
    sync_ledger()
