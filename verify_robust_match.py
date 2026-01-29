from utils.team_names import robust_match_team

def test_robust():
    print("Testing robust_match_team...")
    
    # 1. UMKC vs UCF (Should FAIL)
    # Norm: "umkc kangaroos" vs "central florida knights" (if normalized)
    # But candidaites might be raw.
    # UMKC vs UCF (Short acronyms).
    
    cains = ["UCF Knights", "Duke Blue Devils", "Kansas City Roos"]
    target = "UMKC Kangaroos"
    
    match = robust_match_team(target, cains)
    if match == "Kansas City Roos":
        print(f"✅ PASS: '{target}' matched '{match}' (Correct Alias)")
    elif match:
        print(f"❌ FAIL: '{target}' matched '{match}' (Should be Kansas City Roos)")
    else:
        print(f"❌ FAIL: '{target}' yielded None (Should match Alias)")
        
    # 2. Duke vs Duke Blue Devils (Should PASS with Robust Logic)
    cains = ["Duke Blue Devils", "UNC Tar Heels"]
    target = "Duke"
    match = robust_match_team(target, cains)
    if match == "Duke Blue Devils":
        print(f"✅ PASS: '{target}' matched '{match}'")
    else:
        print(f"❌ FAIL: '{target}' -> '{match}' (Expected Duke Blue Devils)")

    # 3. Iowa vs Iowa State (Should FAIL if high threshold? or Token Overlap?)
    # "Iowa" tokens: {iowa}
    # "Iowa State" tokens: {iowa} (state is stopword?)
    # If state IS stopword, tokens are same {iowa}.
    # Overlap YES. 
    # Similarity: "iowa" vs "iowa state". 4 / 10 chars ratio < 0.5.
    # Should FAIL threshold 0.85.
    cains = ["Iowa State Cyclones", "Ohio State Buckeyes"]
    target = "Iowa Hawkeyes"
    match = robust_match_team(target, cains)
    if match:
         print(f"❌ FAIL: '{target}' matched '{match}' (Should be None)")
    else:
         print(f"✅ PASS: '{target}' correctly yielded None (No Iowa State match)")

if __name__ == "__main__":
    test_robust()
