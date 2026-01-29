import json
import os
from utils.team_names import normalize_team_name

CACHE_FILE = 'data/cache/action_network_data.json'

def inspect():
    if not os.path.exists(CACHE_FILE):
        print("No cache file found.")
        return

    with open(CACHE_FILE, 'r') as f:
        data = json.load(f)

    print(f"Loaded {len(data)} records.")
    
    target = "charlotte hornets @ memphis grizzlies"
    
    if target in data:
        print(f"FOUND: {target}")
        print(json.dumps(data[target], indent=2))
    else:
        print(f"NOT FOUND: {target}")
        # Print close matches
        for k in data.keys():
            if "memphis" in k:
                print(f"Partial match: {k}")

if __name__ == "__main__":
    inspect()
