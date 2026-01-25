import unittest
import sys
import os

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import normalize_team_name, _num

class TestUtils(unittest.TestCase):
    
    def test_normalize_team_name(self):
        # Test basic lowercasing
        self.assertEqual(normalize_team_name("Ohio State"), "ohio st")
        self.assertEqual(normalize_team_name("LSU"), "louisiana st")
        
        # Test cleaning
        self.assertEqual(normalize_team_name("Purdue University"), "purdue")
        self.assertEqual(normalize_team_name("Notre Dame Fighting Irish"), "notre dame irish")
        
        # Test edge cases
        self.assertEqual(normalize_team_name(None), "")
        self.assertEqual(normalize_team_name("   Spaces   "), "spaces")

    def test_num_conversion(self):
        # Test float conversion
        self.assertEqual(_num("5.5"), 5.5)
        self.assertEqual(_num(10), 10.0)
        
        # Test safe defaults
        self.assertEqual(_num(None), 0.0)
        self.assertEqual(_num("invalid", 1.0), 1.0)
        self.assertEqual(_num(None, 5.0), 5.0)

if __name__ == '__main__':
    unittest.main()
