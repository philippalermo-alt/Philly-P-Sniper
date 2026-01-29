from models.soccer import SoccerModelV2
import pandas as pd

def check_coverage():
    model = SoccerModelV2()
    print(f"📊 Model loaded with {len(model.team_stats)} teams in memory.")
    
    # List from The-Odds-API (Step 2165)
    ucl_teams = [
        "AS Monaco", "Juventus", "Ajax", "Olympiakos Piraeus", "Arsenal", "FC Kairat",
        "Union Saint-Gilloise", "Atalanta BC", "Athletic Bilbao", "Sporting Lisbon",
        "Atlético Madrid", "Bodø/Glimt", "Barcelona", "FC Copenhagen", "Bayer Leverkusen",
        "Villarreal", "PSV Eindhoven", "Bayern Munich", "Benfica", "Real Madrid",
        "Borussia Dortmund", "Inter Milan", "Napoli", "Chelsea", "Club Brugge",
        "Marseille", "Eintracht Frankfurt", "Tottenham Hotspur", "Manchester City",
        "Galatasaray", "Liverpool", "Qarabağ FK", "Paris Saint Germain",
        "Newcastle United", "Pafos FC", "Slavia Praha"
    ]
    
    hits = 0
    misses = []
    
    print("\n🔎 Matching Check (With Normalization):")
    from utils.team_names import normalize_team_name
    
    # Simulate Normalized Stats Dict
    # Convert Loaded stats to normalized keys
    norm_stats = {}
    for k, v in model.team_stats.items():
        norm_stats[normalize_team_name(k)] = v
        
    for t in ucl_teams:
        n_t = normalize_team_name(t)
        
        # Check Normalized Match
        if n_t in norm_stats:
            s = norm_stats[n_t]
            is_default = (abs(s['home_att'] - 1.35) < 0.01) and (abs(s['home_def'] - 1.35) < 0.01)
            
            status = "⚠️ DEFAULT" if is_default else "✅ DATA"
            # print(f"   MATCH: '{t}' -> '{n_t}' -> {status}")
            if not is_default: hits += 1
        else:
            print(f"   ❌ MISS:  '{t}' -> '{n_t}'")
            misses.append(t)
            
    print(f"\n📈 Coverage: {hits}/{len(ucl_teams)} Teams have historical data.")
    if misses:
        print("\n⚠️ Missing Teams (Need Aliases?):")
        print(", ".join(misses))

if __name__ == "__main__":
    check_coverage()
