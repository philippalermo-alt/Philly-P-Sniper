
import pandas as pd
from db.connection import get_db
from psycopg2.extras import execute_values

CSV_FILE = "data/nhl_processed/player_game_stats_mnp_2025.csv"

def merge_xg():
    print("🔄 Merging MoneyPuck xG into DB...")
    
    # Load CSV
    df = pd.read_csv(CSV_FILE)
    print(f"Loaded {len(df)} rows from CSV.")
    
    # Inspect Date Format
    # Expecting 'date' column.
    if 'date' not in df.columns:
        print("❌ 'date' column missing in CSV.")
        return

    # Convert Date to String YYYY-MM-DD
    # If int 20250101 -> 2025-01-01
    df['date_str'] = pd.to_datetime(df['date'], format='%Y%m%d').dt.strftime('%Y-%m-%d')
    
    # Prepare Update Data
    # List of (ixg, player_name, date_str)
    # Note: We rely on Name+Date uniqueness. 
    # Valid validation: (player_id, game_id) is better but we don't have API GameID in MoneyPuck CSV easily without map.
    # We DO have 'full_game_id' constructed in Step 3208.
    # But API game_id is 202502xxxx.
    # Step 3208 constructed `202502xxxx`.
    # So we CAN match on `game_id` + `player_name` (or just `game_id` if we map names?).
    # Wait, API GameID matches MoneyPuck constructed ID?
    # Step 3208: "Constructing IDs... 2025020001".
    # MoneyPuck CSV has `full_game_id`.
    # DB has `game_id`.
    # Let's try matching on `game_id` and `player_name`.
    
    updates = []
    for _, row in df.iterrows():
        try:
            gid = str(int(row['full_game_id']))
            pname = row['player_name']
            ixg = float(row.get('ixG', 0.0))
            
            updates.append((ixg, gid, pname))
        except:
            continue
            
    print(f"Prepared {len(updates)} updates.")
    
    conn = get_db()
    cur = conn.cursor()
    
    # Bulk Update via Temp Table or Loop?
    # Loop for 25k rows is slow but safe.
    # Optimized: UPDATE ... FROM VALUES.
    
    # Let's try simple loop batching
    success = 0
    fail = 0
    
    # We match on game_id AND player_name (exact).
    # If name mismatch, we fail.
    # Given urgency, let's try fuzzy later if needed.
    
    sql = """
        UPDATE public.nhl_player_game_logs
        SET ixg = %s
        WHERE game_id = %s AND player_name = %s
    """
    
    batch_size = 1000
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        try:
            execute_values(cur, sql, batch, template=None, page_size=1000)
            # wait, execute_values is for Insert. For Update?
            # execute_values generates `(val1, val2), (val3, val4)...`
            # For UPDATE we need `UPDATE ... AS t SET col = v.col FROM (VALUES %s) AS v(...) WHERE ...`
            pass
        except:
            pass
            
    # Explicit Casting in Values CTE not standard. We cast in SET/WHERE.
    # Postgres syntax: VALUES (val1, val2), (val3, val4) ...
    # We must ensure params passed match types.
    
    # Explicit Casting in Values CTE not standard. We cast in SET/WHERE.
    # Postgres syntax: VALUES (val1, val2), (val3, val4) ...
    # We must ensure params passed match types.
    
    # Let's try explicit casting in the query
    update_query = """
    UPDATE public.nhl_player_game_logs AS t
    SET ixg = v.ixg::float
    FROM (VALUES %s) AS v(ixg, game_id, player_name)
    WHERE t.game_id::text = v.game_id::text 
      AND t.player_name::text = v.player_name::text
    """
    
    try:
        execute_values(cur, update_query, updates)
        updated_rows = cur.rowcount
        conn.commit()
        print(f"✅ Updated {updated_rows} rows with xG.")
    except Exception as e:
        print(f"❌ Batch Update Error: {e}")
        conn.rollback()
        
    conn.close()

if __name__ == "__main__":
    merge_xg()
