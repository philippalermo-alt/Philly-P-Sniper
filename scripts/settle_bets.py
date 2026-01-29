
import pandas as pd
from db.connection import get_db
from datetime import datetime

class BetSettler:
    def __init__(self):
        self.conn = get_db()
        self.settled_count = 0
        
    def run(self):
        print(f"⚖️ Starting Settlement Run: {datetime.now()}")
        
        # 1. Fetch Pending Bets
        # Filtering for 'Hockey' sport only based on Slug prefix 'NHL_'
        obs = self.fetch_pending()
        if not obs:
            print("  No pending bets found.")
            return
            
        print(f"  Found {len(obs)} pending bets.")
        
        # 2. Iterate and Settle
        for row in obs:
            self.process_bet(row)
            
        print(f"✅ Run Complete. Settled {self.settled_count} bets.")
        
    def fetch_pending(self):
        q = """
        SELECT event_id, selection, odds, outcome 
        FROM intelligence_log 
        WHERE outcome = 'PENDING' AND sport = 'Hockey'
        """
        try:
            return pd.read_sql(q, self.conn).to_dict('records')
        except Exception as e:
            print(f"Error fetching bets: {e}")
            return []
            
    def process_bet(self, row):
        # Slug Format: NHL_{Player}_{Market}_{Line}_{Date}
        # e.g. NHL_ConnorMcDavid_POINTS_1p5_20260128
        slug = row['event_id']
        try:
            parts = slug.split('_')
            # Variable length player name?
            # Strategy: We assume Date is last, Line is second last, Market is third last.
            # Pop from end.
            
            date_str = parts[-1] # YYYYMMDD
            line_str = parts[-2] # 1p5
            market = parts[-3]   # POINTS
            
            # Player Name is the rest. Join back.
            # Handle potential underscore in name? Or unidecode removed them?
            # My slug generation logic in rec engine uses self._norm() logic?
            # No, looking at rec engine: f"NHL_{rec['player_name']}_{clean_market}_{line_str}_{date_str}"
            # Player Name contains spaces in Rec Engine dataframe?
            # Rec Engine: slug = f"NHL_{rec['player_name']}_{clean_market}_{line_str}_{date_str}"
            # So name has spaces! "Connor McDavid".
            # Split by '_' will work IF name has NO underscores.
            # Wait, standard names have spaces.
            # But split('_') splits spaces? No.
            # "NHL_Connor McDavid_POINTS_1p5_20260128"
            # parts = ['NHL', 'Connor McDavid', 'POINTS', '1p5', '20260128']
            
            # Reconstruct Name
            player_name = "_".join(parts[1:-3]) # In case name has underscores?
            # If name was "Connor McDavid", it's parts[1].
            
            # Actually Rec Engine does NOT normalize name in Slug, it passes raw player_name.
            # "Connor McDavid"
            
            # Date Fmt
            g_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}" # YYYY-MM-DD
            
            # Fetch Result
            actual = self.get_player_stat(player_name, g_date, market)
            
            if actual is None:
                # Game not played yet or Log not ingested
                return 
                
            # Determine Outcome
            line = float(line_str.replace('p', '.'))
            
            # Logic: Side is implied Over?
            # Rec Engine only does Overs.
            
            outcome = 'PENDING'
            profit = 0.0
            
            if actual > line:
                outcome = 'WIN'
                profit = (row['odds'] - 1.0) # Decimal Odds - 1
            elif actual < line:
                outcome = 'LOSS'
                profit = -1.0
            else:
                # Push
                outcome = 'PUSH'
                profit = 0.0
                
            # Update DB
            self.update_db(slug, outcome, profit, actual)
            self.settled_count += 1
            print(f"  Settled {slug}: Result {actual} vs Line {line} -> {outcome}")
            
        except Exception as e:
            print(f"  Error processing {slug}: {e}")

    def get_player_stat(self, player_name, date_str, market):
        # Query DB for Actuals
        # Need to handle name matching? 
        # Attempt Exact Match first.
        
        # Map Market to DB Col
        col_map = {
            'POINTS': 'goals + assists',
            'ASSISTS': 'assists',
            'GOALS': 'goals',
            'SOG': 'shots'
        }
        
        db_col = col_map.get(market)
        if not db_col: return None
        
        sql = f"""
        SELECT {db_col} as val
        FROM nhl_player_game_logs
        WHERE game_date = %s AND player_name = %s
        """
        
        # Handle "fuzzy" name match if needed?
        # For now strict.
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, (date_str, player_name))
                res = cur.fetchone()
                if res:
                    return float(res[0])
        except Exception as e:
            pass
            
        return None

    def update_db(self, event_id, outcome, profit, actual_val):
        sql = """
        UPDATE intelligence_log
        SET outcome = %s, profit = %s
        WHERE event_id = %s
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, (outcome, profit, event_id))
            self.conn.commit()
        except:
            pass

if __name__ == "__main__":
    settler = BetSettler()
    settler.run()
