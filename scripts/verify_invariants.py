
import sys
import os
from core.probability import logit_scale, normalize_probabilities
from config.settings import Config

def verify_normalization():
    print("🧪 Testing Invariant: Sum of Probabilities = 1.0")
    
    probs = {'Home': 0.45, 'Draw': 0.30, 'Away': 0.25}
    print(f"\n[Case 1] Input Probs: {probs} (Sum: {sum(probs.values())})")
    
    # Apply Calibration
    calibrated = {}
    for k, p in probs.items():
        cp = logit_scale(p, 1.2)
        calibrated[k] = cp # Raw calibrated
        
    print(f"Pre-Normalization Sum: {sum(calibrated.values()):.4f}")
    
    # NEW LOGIC: Normalize
    normalized = normalize_probabilities(calibrated)
    total = sum(normalized.values())
    
    print(f"Post-Normalization: {normalized}")
    print(f"Sum: {total:.4f}")
    
    if abs(total - 1.0) > 0.0001:
        print("❌ FAIL: H2H Probabilities do not sum to 1.0")
        return False
    else:
        print("✅ PASS: H2H Normalization holds.")
        return True

def verify_totals_symmetry():
    print("\n🧪 Testing Invariant: Over + Under = 1.0")
    p_over = 0.60
    p_under = 0.40
    
    prob_map = {
        'Over': logit_scale(p_over, 1.2),
        'Under': logit_scale(p_under, 1.2)
    }
    
    print(f"Pre-Normalization Sum: {sum(prob_map.values()):.4f}")
    
    normalized = normalize_probabilities(prob_map)
    total = sum(normalized.values())
    
    print(f"Post-Normalization: {normalized}")
    print(f"Sum: {total:.4f}")
    
    if abs(total - 1.0) > 0.0001:
        print("❌ FAIL: Totals do not sum to 1.0")
        return False
    return True

if __name__ == "__main__":
    passed = True
    if not verify_normalization(): passed = False
    if not verify_totals_symmetry(): passed = False
    
    if not passed:
        sys.exit(1)
    print("\n✨ All Invariants Passed")
