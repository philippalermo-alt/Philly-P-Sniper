import numpy as np

def logit_scale(p, alpha):
    """
    Apply logit scaling to a probability p with factor alpha.
    Formula: p' = 1 / (1 + exp(-alpha * logit(p)))
    Where logit(p) = ln(p / (1 - p))
    
    Args:
        p (float): Original probability (0.0 to 1.0)
        alpha (float): Scaling factor (1.0 = no change, >1.0 = confidence boost)
        
    Returns:
        float: Scaled probability
    """
    if p <= 0.001: return 0.001
    if p >= 0.999: return 0.999
    if alpha == 1.0: return p
    
    # Logit transform
    logit_p = np.log(p / (1 - p))
    
    # Scale
    logit_new = alpha * logit_p
    
    # Inverse Logit
    p_new = 1 / (1 + np.exp(-logit_new))
    
    return float(p_new)
