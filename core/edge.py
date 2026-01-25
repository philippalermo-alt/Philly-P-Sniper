"""Edge calculation utilities."""

def calculate_edge(true_prob: float, decimal_odds: float) -> float:
    """
    Calculate edge as probability difference.
    
    Edge = True Probability - Implied Probability
    
    Args:
        true_prob: Model's estimated win probability (0-1)
        decimal_odds: Decimal odds offered
    
    Returns:
        Edge as decimal (e.g., 0.05 for 5%)
    """
    if decimal_odds <= 0:
        return 0.0
    
    implied_prob = 1.0 / decimal_odds
    return true_prob - implied_prob

def calculate_ev(true_prob: float, decimal_odds: float) -> float:
    """
    Calculate expected value per unit staked.
    
    EV = (prob * payout) - 1
    
    Args:
        true_prob: Model's estimated win probability
        decimal_odds: Decimal odds offered
    
    Returns:
        Expected value (e.g., 0.10 for 10% EV)
    """
    return (true_prob * decimal_odds) - 1
