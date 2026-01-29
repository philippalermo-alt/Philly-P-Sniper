
import sys
from unittest.mock import MagicMock
import pandas as pd
import os

# Prevent loading .env related crash if missing?
os.environ["ADMIN_PASSWORD"] = "test"

# Mock Modules
sys.modules['psycopg2'] = MagicMock()
sys.modules['dotenv'] = MagicMock()

# Mock internal modules
sys.modules['processing'] = MagicMock()
sys.modules['processing.backtesting'] = MagicMock()
sys.modules['processing.parlay'] = MagicMock()
sys.modules['db'] = MagicMock()
sys.modules['db.connection'] = MagicMock()
sys.modules['db.queries'] = MagicMock()

# Setup Mocks
import db.connection as db_conn
import db.queries as db_queries
import streamlit as st

# Mock DB Connection
db_conn.get_db.return_value = MagicMock()
db_conn.get_last_update_time.return_value = "Never"

# Mock Data
now = pd.Timestamp.now(tz='US/Eastern')
data = {
    'kickoff': [now + pd.Timedelta(hours=1)],
    'sport': ['basketball_nba'],
    'teams': ['Team A vs Team B'],
    'selection': ['Team A'],
    'stake': [10.0],
    'odds': [1.9],
    'edge': [0.05],
    'user_bet': [False],
    'sharp_score': [80],
    'event_id': ['123'],
    'user_stake': [10.0],
    'user_odds': [1.9]
}
df = pd.DataFrame(data)

# Ensure fetch returns this DF
db_queries.fetch_pending_opportunities.return_value = df
db_queries.fetch_settled_bets.return_value = pd.DataFrame()

# Mock Streamlit
st.set_page_config = MagicMock()
st.tabs = MagicMock(return_value=[MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()])
st.session_state = {}

# Mock cache_data to execute function
def cache_noop(*args, **kwargs):
    def decorator(func):
        return func
    return decorator
st.cache_data = cache_noop
st.multiselect = MagicMock(return_value=[]) # Return empty list to skip filtering
st.error = MagicMock() # Explicitly mock error to track calls

print(f"🧪 Streamlit Type: {type(st)}")
print("🧪 Running Reproduction Script for 'NameError: displayed_ids'...")

try:
    import web.dashboard
    # Check if st.error was called with the NameError
    error_calls = [str(call) for call in st.error.call_args_list]
    name_error_found = any("displayed_ids" in str(c) for c in error_calls)
    
    if name_error_found:
        print(f"❌ REPRODUCED: Caught NameError via st.error: {error_calls}")
    else:
        print("✅ SUCCESS: Dashboard loaded without NameError.")
        if error_calls:
            print(f"   (Note: Other errors occured: {error_calls})")

except NameError as e:
    # This path is unlikely if exception is swallowed
    if "displayed_ids" in str(e):
        print(f"❌ REPRODUCED: Caught NameError: {e}")
    else:
        print(f"❌ ERROR: Caught unrelated NameError: {e}")
except Exception as e:
    print(f"⚠️ ERROR: Execution failed with: {e}")
