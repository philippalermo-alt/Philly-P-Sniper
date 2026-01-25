import sys
import traceback
from hard_rock_model import run_sniper

if __name__ == "__main__":
    print("🚀 Starting Manual Debug Run...")
    try:
        run_sniper()
        print("✅ Run Complete.")
    except Exception:
        print("❌ CRITICAL ERROR:")
        traceback.print_exc()
