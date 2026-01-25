"""Sharp money signal scoring."""

def calculate_sharp_score(money_pct: float, ticket_pct: float) -> int:
    """
    Calculate sharp score based on money vs ticket divergence.
    
    High score (70+) = Sharp money signal
    Low score (<25) = Public money
    
    Args:
        money_pct: Percentage of money on this side (0-100)
        ticket_pct: Percentage of tickets on this side (0-100)
    
    Returns:
        Sharp score (0-100)
    """
    try:
        m_val = float(money_pct)
        t_val = float(ticket_pct)
    except (ValueError, TypeError):
        return 0
    
    gap = m_val - t_val
    
    # Component scores
    # Adjusted: Reward ANY positive gap (Money > Tickets).
    # Tuned to reach ~40s for moderate gap/minority (User Feedback 1/25)
    gap_score = max(0, min(1, (gap - 0) / 15)) 
    
    minority_score = max(0, min(1, (55 - t_val) / 25))
    money_majority_score = max(0, min(1, (m_val - 50) / 20))
    
    # Weighted combination
    weighted = 0.60 * gap_score + 0.30 * minority_score + 0.10 * money_majority_score
    return int(round(100 * weighted))

def get_sharp_signal_tier(score: int) -> str:
    """Convert score to tier label."""
    if score >= 70:
        return "SHARP"
    elif score >= 45:
        return "LEAN"
    elif score >= 25:
        return "NEUTRAL"
    else:
        return "PUBLIC"
