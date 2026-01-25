from soccer_model_v2 import SoccerModelV2

def test_live():
    model = SoccerModelV2()
    
    # User Provided Odds
    # Over 2.5 @ 1.63
    # Implied Prob = 1/1.63 = 61.3%
    # Assuming ~5% Vig, Under Prob = ~43.7% => Odds ~2.29
    
    current_odds = {
        'over': 1.63,
        'under': 2.29, # Inferred
        'line': 2.5
    }
    
    print("\n🔍 Running V6 Custom Test for Auxerre vs PSG...")
    print(f"   Input: Over {current_odds['line']} @ {current_odds['over']}")
    
    res = model.predict_match("Auxerre", "Paris Saint Germain", "Ligue_1", current_odds=current_odds)
    
    if res:
        print("\n" + "="*40)
        print(f"⚽ Prediction: {res['home_team']} vs {res['away_team']}")
        print(f"   Market Line:    {current_odds['line']}")
        print(f"   Market Prob:    {res.get('market_prob', 0.52):.2%}")
        print(f"   Total exp xG:   {res['exp_total_xg']:.2f}")
        print("-" * 30)
        print(f"   Model Prob (Over {current_odds['line']}):  {res['prob_over']:.1%}")
        print(f"   Fair Odds:      {res['fair_odds']:.2f}")
        
        edge = (res['prob_over'] * current_odds['over']) - 1
        print(f"   Edge:           {edge:.1%}")
        
        if edge > 0:
            print("✅ RECOMMENDATION: BET OVER")
        else:
            print("❌ RECOMMENDATION: PASS / UNDER")
        print("="*40 + "\n")

if __name__ == "__main__":
    test_live()
