
import os
import sys

# Simulate Docker Environment
# Case 1: .env is mounted (DATABASE_URL present) AND Docker env var (DB_HOST) is present
os.environ['DATABASE_URL'] = "postgresql://user:pass@localhost:5432/db"
os.environ['DB_HOST'] = "db_container"
os.environ['DB_USER'] = "postgres"
os.environ['DB_PASSWORD'] = "postgres"
os.environ['DB_NAME'] = "philly_p_sniper"

# Trigger Config Load
try:
    from config.settings import Config
    import importlib
    import config.settings
    importlib.reload(config.settings)
    from config.settings import Config
    
    print(f"TEST 1 (Docker Priority): DATABASE_URL = {Config.DATABASE_URL}")
    
    if "db_container" in Config.DATABASE_URL:
        print("✅ PASS: Docker DB_HOST took precedence.")
    else:
        print("❌ FAIL: Still using localhost.")
        sys.exit(1)

except Exception as e:
    print(f"❌ FAIL: Exception during config load: {e}")
    sys.exit(1)
