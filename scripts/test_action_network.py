import sys
import os
import json
sys.path.append(os.getcwd())

from data.clients.action_network import get_action_network_data
from utils.team_names import normalize_team_name

# Force loading specific leagues for debugging if needed, 
# but get_action_network_data runs all configured endpoints.

print("🔍 Fetching Action Network Data...")
data = get_action_network_data()

print(f"\n✅ Total Records: {len(data)}")

# Sample keys to identify sports
print("\n--- SAMPLE KEYS ---")
keys = list(data.keys())
for k in keys[:20]:
    print(k)

# Check specifically for a few known team names
targets = [
    "Philadelphia Flyers", "Boston Bruins", # NHL
    "Lakers", "Warriors", # NBA
    "Kansas", "Duke" # NCAAB
]

print("\n--- TARGET CHECK ---")
for t in targets:
    norm = normalize_team_name(t)
    found = False
    for k in keys:
        if norm in k:
            print(f"✅ Found match for {t} ({norm}): {k}")
            found = True
            break
    if not found:
        print(f"❌ No match for {t} ({norm})")

