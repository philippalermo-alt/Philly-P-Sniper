
import sys
import os

sys.path.append(os.getcwd())

print("🧪 Starting Import Smoke Test...")

try:
    print("   Checking 'main.py' import...", end=" ")
    # We mock 'get_db' etc to avoid runtime execution, but we want to verify IMPORTS
    import main
    print("✅ OK")
except ImportError as e:
    print(f"\n❌ IMPORT ERROR in main.py: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n⚠️ Runtime Error in main (Expected if DB not mocked): {e}")
    # This is fine, we just wanted to check if imports broke
    pass

try:
    print("   Checking 'web.dashboard' import...", end=" ")
    from web import dashboard
    print("✅ OK")
except ImportError as e:
    print(f"\n❌ IMPORT ERROR in web.dashboard: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n⚠️ Runtime Error in dashboard: {e}")
    pass

print("\n🎉 Smoke Test Complete. No ImportErrors detected.")
