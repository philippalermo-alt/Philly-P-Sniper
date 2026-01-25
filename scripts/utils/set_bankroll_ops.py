import os
import sys
from dotenv import load_dotenv
from database import get_db, get_dynamic_bankroll

load_dotenv()

TARGET_BANKROLL = 1000.00

def reset_bankroll():
    print(f"🔄 Calculating Bankroll Reset to ${TARGET_BANKROLL:.2f}...")
    
    conn = get_db()
    if not conn:
        print("❌ DB Connection Failed")
        return

    try:
        cur = conn.cursor()
        
        # 1. Get Realized PnL (User Bets Only)
        cur.execute("""
            SELECT sum(case 
                when outcome='WON' then (user_stake * (user_odds - 1)) 
                when outcome='LOST' then -user_stake 
                else 0 end) 
            FROM intelligence_log 
            WHERE outcome IN ('WON', 'LOST', 'PUSH') 
            AND user_bet = TRUE
        """)
        
        row_pnl = cur.fetchone()
        realized_pnl = float(row_pnl[0]) if row_pnl and row_pnl[0] else 0.0
        
        print(f"   📈 Realized User PnL: ${realized_pnl:.2f}")
        
        # 2. Calculate Required Starting Bankroll
        # Target = Start + PnL
        # Start = Target - PnL
        new_starting = TARGET_BANKROLL - realized_pnl
        
        print(f"   🔧 Setting 'starting_bankroll' to: ${new_starting:.2f}")
        print(f"      Verify: {new_starting:.2f} + {realized_pnl:.2f} = {new_starting + realized_pnl:.2f}")
        
        # 3. Update DB
        cur.execute(
            "INSERT INTO app_settings (key, value) VALUES ('starting_bankroll', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            (str(new_starting),)
        )
        conn.commit()
        print("✅ Bankroll Reset Complete.")
        
        # 4. Verify Dynamic Calculation
        # We need to re-import or simulate the get_dynamic_bankroll call
        # Since we just updated the DB, the function should return ~1000
        
        # Re-query
        cur.execute("SELECT value FROM app_settings WHERE key='starting_bankroll'")
        row = cur.fetchone()
        saved_start = float(row[0])
        print(f"   ✅ [VERIFY] Database 'starting_bankroll': ${saved_start:.2f}")
        
        final_balance = saved_start + realized_pnl
        print(f"   💰 [FINAL] Dynamic Bankroll: ${final_balance:.2f}")

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    reset_bankroll()
