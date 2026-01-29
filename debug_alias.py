from utils.team_names import normalize_team_name

def test_alias():
    raw = "Atalanta BC"
    norm = normalize_team_name(raw)
    print(f"Raw: '{raw}'")
    print(f"Norm: '{norm}'")
    
    expected = "atalanta"
    if norm == expected:
        print("✅ SUCCESS")
    else:
        print(f"❌ FAILURE: Expected '{expected}', got '{norm}'")

if __name__ == "__main__":
    test_alias()
