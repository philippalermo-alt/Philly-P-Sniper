import os
import pandas as pd
from datetime import datetime, timedelta
import pytz
from database import get_db
from dotenv import load_dotenv

load_dotenv()

class BusinessAnalytics:
    def __init__(self):
        # Configuration
        self.server_cost = float(os.getenv('SERVER_COST_MONTHLY', 40.0))
        self.api_cost = float(os.getenv('API_COST_MONTHLY', 0.0))
        self.starting_capital = self._get_starting_capital()
        
    def _get_starting_capital(self):
        """Fetch custom bankroll setting or default."""
        conn = get_db()
        if not conn: return 451.16
        try:
            cur = conn.cursor()
            cur.execute("SELECT value FROM app_settings WHERE key='starting_bankroll'")
            row = cur.fetchone()
            cur.close()
            return float(row[0]) if row else 451.16
        except:
            return 451.16

    def get_financial_summary(self):
        """
        Generates the 'CEO Report' - High level P&L and Business Health.
        """
        conn = get_db()
        if not conn: return {}
        
        try:
            # 1. Fetch Betting Performance
            # Settled Bets (User Only)
            query_settled = """
                SELECT outcome, user_stake, user_odds, event_id 
                FROM intelligence_log 
                WHERE user_bet = TRUE 
                AND outcome IN ('WON', 'LOST', 'PUSH')
            """
            df_s = pd.read_sql(query_settled, conn)
            
            # Pending Bets (User Only)
            query_pending = """
                SELECT user_stake, user_odds, edge 
                FROM intelligence_log 
                WHERE user_bet = TRUE 
                AND outcome = 'PENDING'
            """
            df_p = pd.read_sql(query_pending, conn)
            
            # 2. Calculate Gross Betting Profit
            gross_profit = 0.0
            wins = 0
            losses = 0
            pushes = 0
            
            for _, row in df_s.iterrows():
                stake = float(row['user_stake']) if row['user_stake'] else 0
                odds = float(row['user_odds']) if row['user_odds'] else 1.0
                
                if row['outcome'] == 'WON':
                    profit = stake * (odds - 1)
                    gross_profit += profit
                    wins += 1
                elif row['outcome'] == 'LOST':
                    gross_profit -= stake
                    losses += 1
                else: # PUSH
                    pushes += 1
                    
            total_settled = wins + losses + pushes
            win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0.0
            
            # 3. Calculate OpEx (Operational Expenses)
            # Assumption: Business started Jan 1, 2026 (or simply count months active in DB?)
            # Let's count distinct months in the log to estimate duration
            cur = conn.cursor()
            cur.execute("SELECT MIN(timestamp), MAX(timestamp) FROM intelligence_log")
            min_ts, max_ts = cur.fetchone()
            
            months_active = 1
            if min_ts and max_ts:
                # Simple diff
                diff = max_ts - min_ts
                months_active = max(1, diff.days // 30 + 1)
                
            total_opex = (self.server_cost + self.api_cost) * months_active
            
            # 4. Enterprise Value
            net_profit = gross_profit - total_opex
            roi = (net_profit / self.starting_capital) * 100 if self.starting_capital > 0 else 0
            
            # 5. Theoretical Value (Pending)
            # EV = Stake * (Edge %)
            pending_ev = 0.0
            pending_exposure = 0.0
            for _, row in df_p.iterrows():
                stake = float(row['user_stake']) if row['user_stake'] else 0
                edge = float(row['edge']) if row['edge'] else 0
                exposure = stake
                
                pending_ev += (stake * edge)
                pending_exposure += exposure
                
            return {
                "gross_profit": gross_profit,
                "total_opex": total_opex,
                "net_profit": net_profit,
                "roi_pct": roi,
                "win_rate": win_rate,
                "wins": wins,
                "losses": losses,
                "pushes": pushes,
                "pending_exposure": pending_exposure,
                "pending_ev": pending_ev,
                "months_active": months_active,
                "current_capital": self.starting_capital + gross_profit # Cash on hand
            }
            
        except Exception as e:
            print(f"Analytics Error: {e}")
            return {}
        finally:
            conn.close()

    def get_clv_performance(self):
        """
        Analyzes performance against Closing Line Value.
        """
        conn = get_db()
        if not conn: return pd.DataFrame()
        
        # We need bets that are SETTLED or have STARTED (so closing line is set)
        query = """
            SELECT sport, user_odds, closing_odds, outcome 
            FROM intelligence_log 
            WHERE user_bet = TRUE 
            AND closing_odds IS NOT NULL 
            AND closing_odds > 1.0
        """
        df = pd.read_sql(query, conn)
        conn.close()
        
        if df.empty:
            return pd.DataFrame()
            
        # Calculate Beat %
        # (My Odds / Closing Odds) - 1
        df['clv_diff'] = (df['user_odds'] / df['closing_odds']) - 1
        df['beat_clv'] = df['clv_diff'] > 0
        
        return df

if __name__ == "__main__":
    # Test Run
    ba = BusinessAnalytics()
    print("📊 Generating CEO Report...")
    report = ba.get_financial_summary()
    print("\n--- ENTERPRISE HEALTH ---")
    print(f"💰 Net Profit: ${report.get('net_profit', 0):.2f}")
    print(f"📉 Total OpEx: ${report.get('total_opex', 0):.2f} ({report.get('months_active')} months)")
    print(f"📈 ROI: {report.get('roi_pct', 0):.1f}%")
    print(f"💸 Pending EV: ${report.get('pending_ev', 0):.2f}")
    print("-------------------------")
