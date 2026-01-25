
import logging
from lineup_client import get_confirmed_lineup
from config import Config
from datetime import datetime
import pytz

logging.basicConfig(level=logging.INFO)

def debug_fiorentina():
    print(f"Current System Time (UTC): {datetime.now(pytz.utc)}")
    print(f"Current System Time (Local): {datetime.now()}")
    
    # User mentioned Fiorentina vs Cagliari
    # League: Serie A (soccer_italy_serie_a)
    
    print("\n1. Fetching Lineup for Fiorentina vs Cagliari...")
    res = get_confirmed_lineup("soccer_italy_serie_a", "Fiorentina", "Cagliari")
    
    print(f"\nResult: {res}")
    
    if res:
        print(f"Found {len(res)} starters.")
        # Check specific players mentioned by user
        print(f"Moise Kean in lineup? {'moise kean' in res}")
        print(f"Matteo Prati in lineup? {'matteo prati' in res}")
    else:
        print("Result is None (Lineup not found or match not found).")

if __name__ == "__main__":
    debug_fiorentina()
