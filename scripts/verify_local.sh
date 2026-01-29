#!/bin/bash
set -e

echo "🔍 [VERIFY LOCAL] Starting Verification..."
echo "📦 Building/Refreshing Container..."
docker-compose build api

echo "🏃 Running main.py inside Container..."
if docker-compose run --rm api python3 main.py; then
    echo "✅ [VERIFY LOCAL] PASS"
    exit 0
else
    echo "❌ [VERIFY LOCAL] FAIL"
    exit 1
fi
