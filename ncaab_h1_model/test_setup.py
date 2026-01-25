"""
Quick setup test for NCAAB H1 Model
Verifies all dependencies and files are in place.
"""

import sys
import os

def test_imports():
    """Test that all required packages are installed."""
    print("Testing imports...")
    required_packages = [
        ('requests', 'requests'),
        ('numpy', 'numpy'),
        ('pandas', 'pandas'),
        ('sklearn', 'scikit-learn'),
        ('scipy', 'scipy'),
        ('dotenv', 'python-dotenv')
    ]

    missing = []
    for package_name, pip_name in required_packages:
        try:
            __import__(package_name)
            print(f"  ✓ {pip_name}")
        except ImportError:
            print(f"  ✗ {pip_name} - NOT INSTALLED")
            missing.append(pip_name)

    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        return False

    print("✅ All packages installed\n")
    return True

def test_files():
    """Test that all required files exist."""
    print("Testing file structure...")
    required_files = [
        'ncaab_h1_scraper.py',
        'ncaab_h1_features.py',
        'ncaab_h1_train.py',
        'ncaab_h1_predict.py',
        'ncaab_h1_edge_finder.py',
        'requirements.txt',
        'README.md'
    ]

    required_dirs = ['data', 'models']

    missing_files = []
    for filename in required_files:
        if os.path.exists(filename):
            print(f"  ✓ {filename}")
        else:
            print(f"  ✗ {filename} - MISSING")
            missing_files.append(filename)

    for dirname in required_dirs:
        if os.path.exists(dirname):
            print(f"  ✓ {dirname}/")
        else:
            print(f"  ✗ {dirname}/ - MISSING")
            missing_files.append(dirname)

    if missing_files:
        print(f"\n❌ Missing files: {', '.join(missing_files)}")
        return False

    print("✅ All files present\n")
    return True

def test_env():
    """Test that .env file exists and has API key."""
    print("Testing environment...")

    if not os.path.exists('.env'):
        print("  ⚠️  .env file not found")
        print("  Create .env with: cp .env.example .env")
        print("  Then add your ODDS_API_KEY")
        return False

    print("  ✓ .env file exists")

    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv('ODDS_API_KEY')
    if not api_key or api_key == 'your_api_key_here':
        print("  ✗ ODDS_API_KEY not set or still using placeholder")
        print("  Edit .env and add your real API key")
        return False

    print("  ✓ ODDS_API_KEY is set")
    print("✅ Environment configured\n")
    return True

def test_data():
    """Test if data has been collected."""
    print("Testing data...")

    if not os.path.exists('data/team_h1_profiles.json'):
        print("  ⚠️  No team profiles found")
        print("  Run: python ncaab_h1_scraper.py")
        return False

    print("  ✓ Team profiles exist")

    if not os.path.exists('data/historical_games.json'):
        print("  ⚠️  No historical games found")
        print("  Run: python ncaab_h1_scraper.py")
        return False

    print("  ✓ Historical games exist")

    # Check data age
    import json
    from datetime import datetime

    with open('data/team_h1_profiles.json') as f:
        profiles = json.load(f)

    print(f"  ✓ Found {len(profiles)} team profiles")

    print("✅ Data collected\n")
    return True

def test_model():
    """Test if model has been trained."""
    print("Testing model...")

    if not os.path.exists('models/h1_total_model.pkl'):
        print("  ⚠️  No trained model found")
        print("  Run: python ncaab_h1_train.py")
        return False

    print("  ✓ Trained model exists")
    print("✅ Model ready\n")
    return True

def main():
    print("=" * 60)
    print("🏀 NCAAB H1 Model - Setup Test")
    print("=" * 60)
    print()

    results = {
        'Packages': test_imports(),
        'Files': test_files(),
        'Environment': test_env(),
        'Data': test_data(),
        'Model': test_model()
    }

    print("=" * 60)
    print("📊 Summary")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:<15} {status}")

    all_passed = all(results.values())

    print()
    if all_passed:
        print("🎉 All tests passed! Ready to find edges.")
        print("\nRun: python ncaab_h1_edge_finder.py")
    else:
        print("⚠️  Some tests failed. Follow instructions above to fix.")

        # Provide next steps
        if not results['Packages']:
            print("\n📦 Next: pip install -r requirements.txt")
        elif not results['Environment']:
            print("\n🔧 Next: Create .env file with your ODDS_API_KEY")
        elif not results['Data']:
            print("\n📊 Next: python ncaab_h1_scraper.py")
        elif not results['Model']:
            print("\n🤖 Next: python ncaab_h1_train.py")

    print()
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
