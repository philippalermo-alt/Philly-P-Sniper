import difflib

def normalize_team_name(name):
    return name.replace("State", "St").strip()

def test_bad_match():
    # Simulation of current logic in ncaab_h1_features.py
    team_name = "UMKC Kangaroos"
    norm_name = normalize_team_name(team_name)
    
    # Mock Profiles Keys (Target set contains UCF but NOT UMKC, simulating missing profile)
    profile_keys = [
        "Duke Blue Devils",
        "UNC Tar Heels", 
        "Kansas Jayhawks",
        "UCF Knights", 
        "Utah Valley Wolverines"
    ]
    
    print(f"Input: '{team_name}' -> Norm: '{norm_name}'")
    
    # 1. Substring
    candidates = [k for k in profile_keys if k.lower().startswith(norm_name.lower())]
    if candidates:
        print(f"✅ Substring Match: {candidates[0]}")
        return

    # 2. Fuzzy (Current Logic: cutoff=0.4)
    matches = difflib.get_close_matches(norm_name, profile_keys, n=1, cutoff=0.4)
    if matches:
        print(f"⚠️  Current Fuzzy Match (0.4): '{norm_name}' -> '{matches[0]}'")
    else:
        print("✅ No Bad Match found with 0.4 (Unexpected?)")

    # 3. Proposed Logic (Token Overlap + 0.85)
    print("\nTesting Proposed Logic...")
    
    STOPWORDS = {"state", "st", "university", "tech", "college", "north", "south", "east", "west"}
    input_tokens = set([t.lower() for t in norm_name.split() if t.lower() not in STOPWORDS])
    
    best_match = None
    best_score = 0
    
    for key in profile_keys:
        # Token Check
        key_tokens = set([t.lower() for t in key.split() if t.lower() not in STOPWORDS])
        overlap = input_tokens.intersection(key_tokens)
        
        if not overlap:
            continue
            
        # Similarity
        ratio = difflib.SequenceMatcher(None, norm_name, key).ratio()
        if ratio > 0.85: # Metric 2
             if ratio > best_score:
                 best_score = ratio
                 best_match = key
                 
    if best_match:
        print(f"❌ Proposed Match: '{best_match}' (Score: {best_score:.2f})")
    else:
        print("✅ Proposed Logic Rejected Bad Match.")

if __name__ == "__main__":
    test_bad_match()
