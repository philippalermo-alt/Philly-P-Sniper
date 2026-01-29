
import pandas as pd
import sys

def test_filters():
    print("🧪 Testing Dashboard Filters...")
    
    # Mock Data
    data = [
        {'event_id': 'NHL_Player1_SOG', 'kickoff': pd.Timestamp.now() + pd.Timedelta(hours=1)},
        {'event_id': 'PROP_Player2_Points', 'kickoff': pd.Timestamp.now() + pd.Timedelta(hours=1)},
        {'event_id': '12345678', 'kickoff': pd.Timestamp.now() + pd.Timedelta(hours=1)}, # Game
        {'event_id': 'NHL_OldProp', 'kickoff': pd.Timestamp.now() + pd.Timedelta(hours=1)}
    ]
    df_pending = pd.DataFrame(data)
    
    # Logic from Dashboard (Player Prop Edges)
    # Expected: NHL_ and PROP_ matching.
    prop_df = df_pending[
        df_pending['event_id'].astype(str).str.startswith(('PROP_', 'NHL_'))
    ].copy()
    
    # Assert
    print(f"  Total Rows: {len(df_pending)}")
    print(f"  Props Found: {len(prop_df)}")
    
    expected_count = 3 # NHL_, PROP_, NHL_OldProp
    if len(prop_df) == expected_count:
        print("✅ Filter Logic Correct: Caught NHL_ and PROP_")
    else:
        print(f"❌ Filter Logic FAILED. Expected {expected_count}, got {len(prop_df)}")
        print(prop_df)
        sys.exit(1)
        
    # Logic from Dashboard (Edge Plays / Top 15) - EXCLUSION
    # Expected: Only 12345678 remaining
    game_df = df_pending[
        ~df_pending['event_id'].astype(str).str.startswith(('PROP_', 'NHL_'))
    ].copy()
    
    print(f"  Games Found: {len(game_df)}")
    if len(game_df) == 1 and game_df.iloc[0]['event_id'] == '12345678':
        print("✅ Exclusion Logic Correct: Only Game ID remains.")
    else:
        print(f"❌ Exclusion Logic FAILED.")
        print(game_df)
        sys.exit(1)

if __name__ == "__main__":
    test_filters()
