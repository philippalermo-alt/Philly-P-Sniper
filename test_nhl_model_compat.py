#!/usr/bin/env python3
"""
Test script to verify NHL Ref Model compatibility with current scikit-learn version.
This ensures the model doesn't have sklearn version compatibility issues.
"""

import sys

def test_nhl_model_compatibility():
    """Test that the NHL ref model loads and predicts without errors."""
    print("🧪 Testing NHL Ref Model Compatibility...")
    print("="*60)

    try:
        from nhl_modeling import NHLRefModel
        print("✅ NHLRefModel import successful")
    except ImportError as e:
        print(f"❌ Failed to import NHLRefModel: {e}")
        return False

    # Test model initialization
    try:
        model = NHLRefModel()
        print(f"✅ Model initialized")
        print(f"   - Loaded {len(model.ref_bias_map)} referee stats")
    except Exception as e:
        print(f"❌ Model initialization failed: {e}")
        return False

    # Test prediction (the critical part that was failing)
    try:
        test_crew = ['Kelly Sutherland', 'Travis Toomey', 'Andrew Smith', 'Pierre Lambert']
        impact = model.get_game_impact('Toronto Maple Leafs', 'Vegas Golden Knights', test_crew)
        print(f"✅ Prediction successful: impact = {impact:+.3f}")

        # Verify it's not returning default 0.0 due to error
        if impact == 0.0:
            print("⚠️  WARNING: Impact is exactly 0.0 - model may have failed silently")
            print("   Check that ref names are in the bias map")

    except AttributeError as e:
        if "'LogisticRegression' object has no attribute 'multi_class'" in str(e):
            print(f"❌ SKLEARN VERSION MISMATCH: {e}")
            print("   The model needs to be retrained with:")
            print("   python3 train_nhl_ref_model.py")
            return False
        else:
            print(f"❌ Prediction failed with AttributeError: {e}")
            return False
    except Exception as e:
        print(f"❌ Prediction failed: {e}")
        return False

    # Test with unknown refs (fallback behavior)
    try:
        unknown_crew = ['Unknown Ref 1', 'Unknown Ref 2']
        impact = model.get_game_impact('Team A', 'Team B', unknown_crew)
        print(f"✅ Fallback handling works: impact = {impact:+.3f}")
    except Exception as e:
        print(f"❌ Fallback handling failed: {e}")
        return False

    print("="*60)
    print("✅ ALL TESTS PASSED - Model is compatible!")
    return True

if __name__ == "__main__":
    success = test_nhl_model_compatibility()
    sys.exit(0 if success else 1)
