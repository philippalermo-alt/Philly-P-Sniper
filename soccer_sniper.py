import sys
import argparse
import time
from datetime import datetime, timezone

from soccer_client import SoccerClient
from notifier import send_alert
from probability_models import Config
import pandas as pd

# Setup Clients
soccer_client = SoccerClient()
# telegram = TelegramClient() # Removed

def run_sniper(home, away, start_date_str):
    print(f"🎯 SNIPER ACTIVATED: {home} vs {away}")
    
    # 1. Match Fixture
    fixture_id = soccer_client.get_fixture_id(home, start_date_str)
    if not fixture_id:
        print(f"❌ Could not find fixture ID for {home} on {start_date_str}")
        return
        
    print(f"✅ Found Fixture ID: {fixture_id}")
    
    # 2. Fetch Lineups
    # Retry logic (3 attempts, 30s delay)
    lineups = None
    for i in range(3):
        h_lineup, a_lineup = soccer_client.get_lineups(fixture_id)
        if h_lineup and a_lineup:
            lineups = (h_lineup, a_lineup)
            break
        print(f"⏳ Lineups not ready... waiting 30s (Attempt {i+1}/3)")
        time.sleep(30)
        
    if not lineups:
        print("❌ Lineups still missing. Aborting.")
        return
        
    h_xi_dict, a_xi_dict = lineups
    # Flatten checks
    h_xi = list(h_xi_dict.values())[0] if isinstance(h_xi_dict, dict) else []
    a_xi = list(a_xi_dict.values())[0] if isinstance(a_xi_dict, dict) else []
    
    print(f"📋 Lineups Received!")
    
    # 3. Calculate Impact
    h_imp, h_found = soccer_client.calculate_impact(home, h_xi)
    a_imp, a_found = soccer_client.calculate_impact(away, a_xi)
    
    net_impact = h_imp - a_imp
    print(f"   🏠 Home Impact: {h_imp:.2f} {h_found}")
    print(f"   ✈️ Away Impact: {a_imp:.2f} {a_found}")
    print(f"   ⚖️ Net Impact: {net_impact:+.2f}")
    
    # 4. Trigger Alert if Significant
    # We define "Significant" as > 0.15 xG swing (e.g. 1 major player mismatch or missing star)
    
    if abs(net_impact) >= 0.15:
        msg = f"🎯 *PHILLY EDGE ALERT*\n\n"
        msg += f"⚽ *{home} vs {away}*\n"
        msg += f"⚖️ Net Impact: *{net_impact:+.2f}*\n"
        
        if h_found: msg += f"\n🏠 Home Stars: {', '.join(h_found)}"
        else: msg += f"\n🏠 Home Stars: ❌ NONE DETECTED"
        
        if a_found: msg += f"\n✈️ Away Stars: {', '.join(a_found)}"
        else: msg += f"\n✈️ Away Stars: ❌ NONE DETECTED"
        
        # Add V2 Model Prediction
        try:
            from soccer_model_v2 import SoccerModelV2
            model = SoccerModelV2()
            pred = model.predict_match(home, away)
            if pred:
                msg += f"\n\n🤖 **Model V2 Prediction**:"
                msg += f"\nScore: {pred['exp_score']}"
                msg += f"\nWin%: {pred['prob_home']:.0%} / {pred['prob_draw']:.0%} / {pred['prob_away']:.0%}"
                msg += f"\nFair Odds: {pred['fair_odds_home']:.2f}"
        except:
            pass

        msg += f"\n\n👉 Model Win Prob Adjusted accordingly."
        
        print(f"🚀 Sending Telegram Alert: {msg}")
        send_alert(msg)
    else:
        print("📉 Impact below threshold (0.15). No alert.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", required=True)
    parser.add_argument("--away", required=True)
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    
    args = parser.parse_args()
    
    run_sniper(args.home, args.away, args.date)
