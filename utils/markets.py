"""Market classification utilities."""

def get_market_type(selection: str) -> str:
    """Determine market type from selection string."""
    prefix = ""
    if "1H " in selection or "1st Half" in selection:
        prefix = "1H_"
    
    if "Over" in selection or "Under" in selection:
        return prefix + "TOTAL"
    if " ML" in selection:
        return prefix + "ML"
    if "+" in selection or "-" in selection:
        return prefix + "SPREAD"
    return "OTHER"
