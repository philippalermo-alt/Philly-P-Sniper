import pandas as pd
from database import get_db
from data_sources.nba_dvp import NBADvPClient
from data_sources.soccer_xg import SoccerXGClient
from data_sources.ncaab_kenpom import KenPomClient
from datetime import datetime
import time

def backfill_metrics():
    print("🚀 Starting Backfill of Historical Metrics...")
    conn = get_db()
    
    # 1. Fetch eligible bets (Settled, missing metrics)
    # We target rows where 'outcome' is settled but 'dvp_rank' or 'home_xg' is NULL or 0
    query = """
    SELECT event_id, sport, teams, kickoff, home_xg, dvp_rank, home_adj_em, home_adj_o
    FROM intelligence_log
    WHERE outcome IN ('WON', 'LOST', 'PUSH')
    """
    df = pd.read_sql(query, conn)
    
    if df.empty:
        print("✅ No bets to backfill.")
        return

    # Initialize Clients
    nba_client = NBADvPClient()
    soccer_client = SoccerXGClient()
    kp_client = KenPomClient()
    
    # Cache for KenPom (season stats are constant-ish)
    kp_stats = pd.DataFrame()
    if not kp_client.get_efficiency_stats().empty:
        kp_stats = kp_client.get_efficiency_stats()

    updates = 0
    
    for i, row in df.iterrows():
        eid = row['event_id']
        sport = row['sport']
        teams_str = row['teams'] # "Home vs Away"
        kickoff = row['kickoff']
        
        # Check if already done (simple check)
        if row['dvp_rank'] and row['dvp_rank'] > 0: continue
        if row['home_xg'] and row['home_xg'] > 0: continue
        if row['home_adj_o'] and row['home_adj_o'] > 0: continue

        print(f"🔄 Processing {eid} ({sport})...")
        
        try:
            # Parse Teams
            # Assuming "Home vs Away" format or "Away @ Home"?
            # Standard in this app: "Home vs Away" usually.
            if ' vs ' in teams_str:
                home, away = teams_str.split(' vs ')
            elif ' @ ' in teams_str:
                away, home = teams_str.split(' @ ')
            else:
                continue

            cur = conn.cursor()

            # --- NBA ---
            if 'nba' in sport.lower():
                # Fetch DvP as of kickoff date?
                # Date format for nba_api: MM/DD/YYYY
                date_str = pd.to_datetime(kickoff).strftime('%m/%d/%Y')
                
                # We need rank for the opponent? complexity high.
                # Simplified: Get current season rank proxy or last known.
                # Actually, fetching for every single row is expensive (API limit).
                # Optimization: Backfill with "Season Average" (Leakage accepted).
                # We'll rely on the existing client method which gets CURRENT stats.
                # Better than 0.
                pass 
                
            # --- SOCCER ---
            if 'soccer' in sport.lower():
                # We need League ID and Team IDs.
                # Hard without mapping.
                # Ideally we used Team Mapping table.
                # Skip for now if mapping missing.
                pass

            # --- NCAAB ---
            if 'ncaab' in sport.lower() and not kp_stats.empty:
                # Fuzzy match names in kp_stats
                h_row = kp_stats[kp_stats['Team'].str.contains(home, case=False)]
                a_row = kp_stats[kp_stats['Team'].str.contains(away, case=False)]
                
                if not h_row.empty and not a_row.empty:
                    h_em = h_row.iloc[0]['AdjEM']
                    a_em = a_row.iloc[0]['AdjEM']
                    h_o = h_row.iloc[0]['AdjO']
                    a_o = a_row.iloc[0]['AdjO']
                    h_d = h_row.iloc[0]['AdjD']
                    a_d = a_row.iloc[0]['AdjD']
                    h_t = h_row.iloc[0]['AdjT']
                    a_t = a_row.iloc[0]['AdjT']
                    
                    cur.execute("""
                        UPDATE intelligence_log 
                        SET home_adj_em = %s, away_adj_em = %s,
                            home_adj_o = %s, away_adj_o = %s,
                            home_adj_d = %s, away_adj_d = %s,
                            home_tempo = %s, away_tempo = %s
                        WHERE event_id = %s
                    """, (
                        float(h_em), float(a_em), 
                        float(h_o), float(a_o),
                        float(h_d), float(a_d),
                        float(h_t), float(a_t),
                        eid
                    ))
                    updates += 1

            conn.commit()
            cur.close()

        except Exception as e:
            print(f"❌ Error processing {eid}: {e}")
            conn.rollback()

    print(f"✨ Backfill Complete. Updated {updates} rows.")

if __name__ == "__main__":
    backfill_metrics()
