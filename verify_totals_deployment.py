import sys
import os

# Add root to path
sys.path.append(os.getcwd())

from config.settings import Config
from utils.models.nhl_totals_v2 import NHLTotalsV2

def verify():
    print("=== NHL Totals V2 Deployment Verification ===")
    
    # 1. Check Flag
    print(f"1. Feature Flag Check: NHL_TOTALS_V2_ENABLED = {Config.NHL_TOTALS_V2_ENABLED}")
    if not Config.NHL_TOTALS_V2_ENABLED:
        print("   ✅ Flag is SAFE (False) as expected for initial deployment.")
    else:
        print("   ⚠️ Flag is ENABLED. Ensure this is intentional.")
        
    # 2. Instantiate Model
    print("\n2. Model Instantiation...")
    try:
        model = NHLTotalsV2()
        if model.model and model.lookup:
            print(f"   ✅ Instantiated successfully.")
            print(f"   Lookup Size: {len(model.lookup)} teams")
        else:
            print("   ❌ Failed to load artifacts.")
            return
    except Exception as e:
        print(f"   ❌ Error instantiating: {e}")
        return

    # 3. Mock Prediction
    print("\n3. Mock Prediction (PHI vs NYR)...")
    try:
        # Mock Inputs
        home = "PHI"
        away = "NYR"
        line = 6.5
        o_price = 2.00 # +100
        u_price = 1.90 # -110 (Strong Under Juice)
        date = "2026-01-27"
        
        result = model.predict(home, away, line, o_price, u_price, date)
        
        if result:
            print("   ✅ Prediction Successful:")
            print(f"   Expected Total: {result['expected_total']}")
            print(f"   Prob Over: {result['prob_over']:.4f}, Prob Under: {result['prob_under']:.4f}")
            print(f"   EV Over: {result['ev_over']:.4f}, EV Under: {result['ev_under']:.4f}")
            print(f"   Recommendation: {result['recommendation']}")
            
            if result['recommendation']:
                ev = result['ev']
                if ev > 0.05:
                    print(f"   ✅ Strategy B Logic Verified (EV {ev:.2%} > 5%)")
                else:
                    print(f"   ❌ Strategy B Violation (EV {ev:.2%} < 5% but Rec exists)")
            else:
                print("   ℹ️ No Recommendation (Likely EV < 5%). This works.")
                
        else:
            print("   ❌ Predict returned None.")
            
    except Exception as e:
        print(f"   ❌ Prediction Error: {e}")

if __name__ == "__main__":
    verify()
