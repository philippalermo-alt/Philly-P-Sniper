#!/bin/bash
# scripts/verify_totals_v2.sh
# Automated Regression Guard for NHL Totals V2 Cutover

set -e

echo "=== NHL Totals V2: Automated Verification ==="

# 1. RUN WITH V2 DISABLED
echo "Testing DISABLED State..."
export NHL_TOTALS_V2_ENABLED=False
LOG_DISABLED=$(python3 scripts/proof_nhl_totals_v2.py 2>&1)
echo "$LOG_DISABLED" >> analysis/nhl_phase2_totals/totals_v2_proof_run.log

# Checks
if echo "$LOG_DISABLED" | grep -q "NHL Totals disabled (V2 flag off)"; then
    echo "✅ [PASS] 'NHL Totals disabled' message found."
else
    echo "❌ [FAIL] Missing 'NHL Totals disabled' message."
    echo "Log: $LOG_DISABLED"
    exit 1
fi

if echo "$LOG_DISABLED" | grep -q "NHL_TOTALS_V2_ACTIVE"; then
    echo "❌ [FAIL] V2 Active log found despite flag=False."
    print "Log: $LOG_DISABLED"
    exit 1
else
    echo "✅ [PASS] No V2 Activity detected."
fi

if echo "$LOG_DISABLED" | grep -q "NHL_TOTALS_LEGACY_ACTIVE"; then
    echo "❌ [FAIL] Legacy Activity detected."
    exit 1
fi

# 2. RUN WITH V2 ENABLED
echo -e "\nTesting ENABLED State..."
export NHL_TOTALS_V2_ENABLED=True
LOG_ENABLED=$(python3 scripts/proof_nhl_totals_v2.py 2>&1)
echo "$LOG_ENABLED" >> analysis/nhl_phase2_totals/totals_v2_proof_run.log

# Checks
if echo "$LOG_ENABLED" | grep -q "NHL_TOTALS_V2_ACTIVE"; then
    echo "✅ [PASS] V2 Active log found."
else
    echo "❌ [FAIL] Missing 'NHL_TOTALS_V2_ACTIVE' log."
    echo "Log: $LOG_ENABLED"
    exit 1
fi

if echo "$LOG_ENABLED" | grep -q "NHL Totals disabled"; then
    echo "❌ [FAIL] 'Disabled' message found despite flag=True."
    exit 1
fi

if echo "$LOG_ENABLED" | grep -q "NHL_TOTALS_LEGACY_ACTIVE"; then
    echo "❌ [FAIL] Legacy Activity detected."
    exit 1
fi

echo -e "\n=== ✅ ALL CHECKS PASSED ==="
echo "Legacy Decommissioned. V2 Gated Correctly."
exit 0
