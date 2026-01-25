"""Kelly Criterion stake calculation."""

from config.settings import Config
from db.connection import get_dynamic_bankroll

def calculate_kelly_stake(
    edge: float,
    decimal_odds: float,
    sport: str = None,
    multipliers: dict = None
) -> float:
    """
    Calculate optimal stake using Kelly Criterion.
    
    Args:
        edge: Probability difference (model - implied)
        decimal_odds: Decimal odds (e.g., 2.00)
        sport: Sport key for smart staking multipliers
        multipliers: Pre-calculated multipliers by sport/bucket
    
    Returns:
        Recommended stake in dollars
    """
    if edge <= 0:
        return 0.0
    
    # Kelly formula
    b = decimal_odds - 1
    p = edge + (1.0 / decimal_odds)  # True probability
    q = 1.0 - p
    
    f_star = (b * p - q) / b
    
    # Apply fractional Kelly and bankroll
    bankroll = get_dynamic_bankroll()
    base_stake = f_star * Config.KELLY_FRAC * bankroll
    
    # Apply sport multipliers if provided
    if multipliers and sport:
        base_stake *= _get_multiplier(multipliers, sport, edge)
    
    # Cap at max stake
    max_stake = bankroll * Config.MAX_STAKE_PCT
    return round(min(base_stake, max_stake), 2)

def _get_multiplier(multipliers: dict, sport: str, edge: float) -> float:
    """Get staking multiplier for sport and edge bucket."""
    sport_mults = multipliers.get(sport, {})
    if not isinstance(sport_mults, dict):
        return float(sport_mults) if sport_mults else 1.0
    
    edge_pct = edge * 100
    if edge_pct < 3:
        bucket = '0-3%'
    elif edge_pct < 6:
        bucket = '3-6%'
    elif edge_pct < 10:
        bucket = '6-10%'
    else:
        bucket = '10%+'
    
    return sport_mults.get(bucket, 1.0)
