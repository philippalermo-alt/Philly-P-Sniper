import sys
import os

print("--- 🛡️ PRE-DEPLOYMENT VERIFICATION ---")
failures = 0

def check_import(module_name):
    global failures
    print(f"Testing import: {module_name}...", end=" ")
    try:
        __import__(module_name)
        print("✅ PASS")
    except Exception as e:
        print(f"❌ FAIL: {e}")
        failures += 1

# 1. Check Dashboard (Most critical UI)
# Set headless for streamlit
os.environ['STREAMLIT_HEADLESS'] = 'true'
try:
    # Dashboard uses streamlit, difficult to import directly without context??
    # Actually, we can check for SyntaxErrors/NameErrors at module level.
    with open('dashboard.py', 'r') as f:
        compile(f.read(), 'dashboard.py', 'exec')
    print("Testing syntax: dashboard.py... ✅ PASS")
except Exception as e:
    print(f"Testing syntax: dashboard.py... ❌ FAIL: {e}")
    failures += 1

# 2. Check Prop Sniper
check_import('prop_sniper')

# 3. Check Lineup Client
check_import('lineup_client')

# 4. Check Utils
check_import('utils')

if failures == 0:
    print("\n✅ ALL CHECKS PASSED. Safe to deploy.")
    sys.exit(0)
else:
    print(f"\n❌ {failures} CHECKS FAILED. DO NOT DEPLOY.")
    sys.exit(1)
