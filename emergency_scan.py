
import os
import sys
import types
import pandas as pd

# --- MOCK DATABASE MODULE ---
# We must do this BEFORE importing hard_rock_model or probability_models
# to prevent them from trying to connect to a real DB.

db_mock = types.ModuleType("database")

def mock_get_db():
    return None

def mock_init_db():
    print("   [MOCK] DB Init skipped.")

def mock_safe_execute(cur, sql, params=None):
    return None

def mock_get_calibration(sport):
    return 1.0

def mock_get_dynamic_bankroll():
    return 1000.0

db_mock.get_db = mock_get_db
db_mock.init_db = mock_init_db
db_mock.safe_execute = mock_safe_execute
db_mock.get_calibration = mock_get_calibration
db_mock.get_dynamic_bankroll = mock_get_dynamic_bankroll
db_mock._to_python_scalar = lambda x: x

sys.modules["database"] = db_mock

# --- IMPORT APP LOGIC ---
try:
    from config import Config
    # Force settings
    os.environ['SPORT_FILTER'] = 'icehockey_nhl' # Use specific key or 'NHL' logic handle it
    Config.LEAGUES = ['icehockey_nhl'] # Force only NHL to save time/api calls
    
    from hard_rock_model import run_sniper
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

# --- CAPTURE OUTPUT ---
from io import StringIO
import sys

class CaptureStdOut(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self
    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio    # free up some memory
        sys.stdout = self._stdout

if __name__ == "__main__":
    print("🚀 Starting Emergency NHL Scan (Local/Mock DB)...")
    
    # Run the sniper
    run_sniper()
