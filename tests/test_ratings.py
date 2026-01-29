import unittest
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.clients.ratings import get_current_seasons

class TestRatings(unittest.TestCase):
    
    def test_dynamic_season_logic(self):
        """Verify season logic returns strings and reasonable years."""
        nfl, kenpom = get_current_seasons()
        
        # Check types
        self.assertIsInstance(nfl, str)
        self.assertIsInstance(kenpom, str)
        
        # Check logic reasonableness (should be near current year)
        current_year = datetime.now().year
        
        self.assertTrue(int(nfl) >= current_year - 1)
        self.assertTrue(int(nfl) <= current_year + 1)
        
        self.assertTrue(int(kenpom) >= current_year)
        self.assertTrue(int(kenpom) <= current_year + 1)
        
        print(f"Calculated Seasons -> NFL: {nfl}, KenPom: {kenpom}")

if __name__ == '__main__':
    unittest.main()
