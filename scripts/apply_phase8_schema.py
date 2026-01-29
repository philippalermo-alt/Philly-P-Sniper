
from db.connection import init_db

if __name__ == "__main__":
    print("🚀 Applying Phase 8 Schema Changes...")
    init_db()
    print("✅ Schema Applied.")
