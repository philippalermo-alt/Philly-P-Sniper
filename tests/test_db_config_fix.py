import os
from config import Config

# Mock Docker Env Vars
os.environ['DB_HOST'] = 'db'
os.environ['DB_USER'] = 'testuser'
os.environ['DB_PASSWORD'] = 'testpass'
os.environ['DB_NAME'] = 'testdb'
if 'DATABASE_URL' in os.environ:
    del os.environ['DATABASE_URL']

# Reload Config (Simulating app start)
# Note: Config class attributes are evaluated at import time, so we need to re-import or logic check
# Actually, let's just inspect the logic we PLAN to insert.

db_url = os.getenv('DATABASE_URL')
if not db_url:
    host = os.getenv('DB_HOST', 'localhost')
    user = os.getenv('DB_USER', 'postgres')
    passw = os.getenv('DB_PASSWORD', 'postgres')
    name = os.getenv('DB_NAME', 'philly_p_sniper')
    db_url = f"postgresql://{user}:{passw}@{host}:5432/{name}"

print(f"Constructed URL: {db_url}")
expected = "postgresql://testuser:testpass@db:5432/testdb"
if db_url == expected:
    print("✅ SUCCESS: Logic correctly builds URL from Docker Env Vars")
else:
    print(f"❌ FAILURE: Expected {expected}, got {db_url}")
