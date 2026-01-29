#!/bin/bash

echo "🧪 Starting Pre-Deployment Verification..."

# 0. Fast Fail: Local Syntax Check
echo "🔍 Checking Local Syntax..."
python3 -m py_compile web/dashboard.py
if [ $? -ne 0 ]; then
    echo "❌ Local Syntax Check Failed."
    exit 1
fi

# 1. Build Local Image
echo "🔨 Building Local Image (philly-test)..."
docker build -t philly-test . 
if [ $? -ne 0 ]; then
    echo "❌ Build Failed."
    exit 1
fi

# 2. Syntax & Import Check
echo "🔍 Verifying Python Imports..."
docker run --rm --env-file .env philly-test python3 -c "
try:
    from db.connection import get_db
    from processing.grading import grade_bet, settle_pending_bets
    from manual_settle import main
    from settle_props import settle_props
    import data.clients.espn
    import web.dashboard
    print('✅ Imports OK')
except Exception as e:
    print(f'❌ Import Failed: {e}')
    exit(1)
"
if [ $? -ne 0 ]; then
    echo "❌ Verification Failed."
    exit 1
fi

# 3. Unit Tests (If we had them, we'd run pytest here)
# echo "🧪 Running Unit Tests..."
# docker run --rm philly-test pytest tests/

echo "✅ ALL CHECKS PASSED. Ready to Deploy."
