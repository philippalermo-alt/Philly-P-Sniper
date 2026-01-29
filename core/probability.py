
import math

def normalize_probabilities(probs: dict) -> dict:
    """
    Normalize a dictionary of probabilities so they sum to 1.0.
    
    Args:
        probs (dict): Dictionary of {selection_name: probability}
        
    Returns:
        dict: Normalized probabilities.
    """
    total = sum(probs.values())
    if total <= 0:
        return probs # Avoid division by zero, return as-is (likely error upstream)
    
    return {k: v / total for k, v in probs.items()}

def logit_scale(prob: float, factor: float = 1.0) -> float:
    """
    Apply logistic scaling to a probability.
    
    Args:
        prob (float): Verification probability (0-1)
        factor (float): Scaling factor (1.0 = no change, >1.0 = sharpen, <1.0 = flatten)
        
    Returns:
        float: Scaled probability
    """
    if prob <= 0.001: return 0.001
    if prob >= 0.999: return 0.999
    
    logit = math.log(prob / (1 - prob))
    scaled_logit = logit * factor
    return 1 / (1 + math.exp(-scaled_logit))
