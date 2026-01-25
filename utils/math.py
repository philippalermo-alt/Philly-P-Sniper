import numpy as np

def _to_python_scalar(v):
    """
    Convert numpy scalar types to native Python types so psycopg2 won't end up
    with representations like 'np.float64(...)' when queries fail or are logged.
    """
    try:
        if isinstance(v, (np.generic,)):
            return v.item()
    except Exception:
        pass
    return v

def _num(v, default=0.0):
    """
    Safely convert v to a float if possible, otherwise return default.
    Use this to avoid None values ending up in arithmetic/division.
    """
    if v is None:
        return float(default)
    try:
        return float(v)
    except Exception:
        try:
            if isinstance(v, (np.generic,)):
                return float(v.item())
        except Exception:
            pass
    return float(default)
