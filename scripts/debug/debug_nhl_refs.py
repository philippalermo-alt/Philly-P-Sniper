
import os
import pandas as pd
from nhl_modeling import NHLRefModel

def test_refs():
    # 1. Initialize Model (this triggers the load logic)
    print("--- Initializing Model ---")
    model = NHLRefModel()
    
    print(f"\nStats Map Size: {len(model.ref_bias_map)}")
    
    # 2. Inspect Keys from CSV
    print("\n--- First 10 Keys in Map ---")
    keys = list(model.ref_bias_map.keys())
    for k in keys[:10]:
        print(f"'{k}' -> {model.ref_bias_map[k]}")
        
    # 3. Test Cases from User Log
    test_crews = [
        ['Jon Mclsaac', 'Scott Cherrey', 'Kendrick Nicholson', 'David Brisebois'], # Typo: Mclsaac
        ['Carter Sandlak', 'Chris Rooney', 'Dylan Blujus', 'Kiel Murchison'],
        ['Furman South', 'Michael Markovic', 'Joe Mahon', 'Trent Knorr']
    ]
    
    print("\n--- Testing Match Logic ---")
    for crew in test_crews:
        print(f"\nTesting Crew: {crew}")
        impact = model.get_game_impact('Home', 'Away', crew)
        print(f"Result Impact: {impact:+.4f}")

if __name__ == "__main__":
    test_refs()
