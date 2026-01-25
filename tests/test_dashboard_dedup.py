import pandas as pd
import unittest
from datetime import datetime, timedelta

class TestDashboardLogic(unittest.TestCase):
    def test_prop_deduplication(self):
        """
        Verify that prop dataframe is correctly deduplicated, retaining the most recent timestamp.
        """
        # 1. Setup Mock Data
        data = [
            # Duplicate Set 1 (Latest should remain)
            {'event_id': 'PROP_1', 'selection': 'Player A Goal', 'teams': 'Team A vs Team B', 'timestamp': datetime(2026, 1, 25, 10, 0, 0), 'kickoff': datetime(2026, 1, 26, 15, 0)},
            {'event_id': 'PROP_2', 'selection': 'Player A Goal', 'teams': 'Team A vs Team B', 'timestamp': datetime(2026, 1, 25, 10, 30, 0), 'kickoff': datetime(2026, 1, 26, 15, 0)}, # NEWEST
            {'event_id': 'PROP_3', 'selection': 'Player A Goal', 'teams': 'Team A vs Team B', 'timestamp': datetime(2026, 1, 25, 9, 30, 0), 'kickoff': datetime(2026, 1, 26, 15, 0)},

            # Unique Entry
            {'event_id': 'PROP_4', 'selection': 'Player B Assist', 'teams': 'Team C vs Team D', 'timestamp': datetime(2026, 1, 25, 10, 0, 0), 'kickoff': datetime(2026, 1, 26, 12, 0)},
        ]
        
        prop_df = pd.DataFrame(data)
        
        print(f"\n[TEST] Original Count: {len(prop_df)}")

        # 2. Apply Logic from Dashboard.py
        if not prop_df.empty:
            # Sort by timestamp desc first to keep the newest
            if 'timestamp' in prop_df.columns:
                prop_df = prop_df.sort_values('timestamp', ascending=False)
            
            # Drop duplicates based on Selection (Player+Type) and Teams (Matchup)
            prop_df = prop_df.drop_duplicates(subset=['selection', 'teams'], keep='first')
            
            # Re-sort by kickoff for display
            prop_df = prop_df.sort_values('kickoff', ascending=True)

        print(f"[TEST] Deduped Count: {len(prop_df)}")

        # 3. Assertions
        # Should have 2 rows left (Player A Goal, Player B Assist)
        self.assertEqual(len(prop_df), 2)
        
        # Verify Key Correctness
        player_a_row = prop_df[prop_df['selection'] == 'Player A Goal'].iloc[0]
        self.assertEqual(player_a_row['event_id'], 'PROP_2') # Should be the one from 10:30
        
        print("[TEST] ✅ Logic Validated: Duplicates removed, newest retained.")

if __name__ == '__main__':
    unittest.main()
