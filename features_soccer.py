from __future__ import annotations

from typing import Dict, List, Any, Tuple
import math

NUMERIC_KEYS = ("min", "shots", "goals", "assists", "xG", "xA", "xGChain", "xGBuildup")

def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except (ValueError, TypeError):
        return default

def _safe_div(num: float, den: float, default: float = 0.0) -> float:
    return num / den if den and abs(den) > 1e-12 else default

def compute_team_features(player_rows: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Compute team-level aggregates + concentration/ratio metrics from player match rows.

    Expects each row to contain some subset of:
    min, shots, key_passes, xG, xA, xGChain, xGBuildup, etc.
    Missing values are treated as 0.
    """
    # Aggregate totals
    totals = {k: 0.0 for k in NUMERIC_KEYS}
    xg_list: List[float] = []
    chain_list: List[float] = []

    for r in player_rows:
        for k in NUMERIC_KEYS:
            totals[k] += _to_float(r.get(k), 0.0)
        xg_list.append(_to_float(r.get("xG"), 0.0))
        chain_list.append(_to_float(r.get("xGChain"), 0.0))

    team_xG = totals["xG"]
    team_xA = totals["xA"]
    team_xGChain = totals["xGChain"]
    team_xGBuildup = totals["xGBuildup"]

    # Concentration metrics (shares)
    xg_sorted = sorted(xg_list, reverse=True)
    top1_xG = xg_sorted[0] if xg_sorted else 0.0
    top2_xG = (xg_sorted[0] + xg_sorted[1]) if len(xg_sorted) >= 2 else (xg_sorted[0] if xg_sorted else 0.0)

    chain_sorted = sorted(chain_list, reverse=True)
    top1_chain = chain_sorted[0] if chain_sorted else 0.0

    top1_xG_share = _safe_div(top1_xG, team_xG, default=0.0)
    top2_xG_share = _safe_div(top2_xG, team_xG, default=0.0)
    top1_chain_share = _safe_div(top1_chain, team_xGChain, default=0.0)

    # Balance ratios
    buildup_ratio = _safe_div(team_xGBuildup, team_xGChain, default=0.0)
    creation_ratio = _safe_div(team_xA, team_xG, default=0.0)

    # Optional: normalize by minutes (not required for the minimal feature set)
    # We still compute total_minutes in case you want per-90 variants later.
    total_minutes = totals["min"]

    return {
        "team_minutes": total_minutes,
        "team_shots": totals["shots"],

        "team_xG": team_xG,
        "team_xA": team_xA,
        "team_xGChain": team_xGChain,
        "team_xGBuildup": team_xGBuildup,
        "top1_xG_share": top1_xG_share,
        "top2_xG_share": top2_xG_share,
        "top1_chain_share": top1_chain_share,
        "buildup_ratio": buildup_ratio,
        "creation_ratio": creation_ratio,
    }

def compute_match_features(
    home_rows: List[Dict[str, Any]],
    away_rows: List[Dict[str, Any]],
    prefix_home: str = "home_",
    prefix_away: str = "away_",
) -> Dict[str, float]:
    """
    Returns a single flat feature dict for modeling totals (e.g., Over 2.5).
    """
    H = compute_team_features(home_rows)
    A = compute_team_features(away_rows)

    feat: Dict[str, float] = {}

    # Prefix team features
    for k, v in H.items():
        feat[prefix_home + k] = float(v)
    for k, v in A.items():
        feat[prefix_away + k] = float(v)

    # Interactions
    feat["xG_sum"] = feat[prefix_home + "team_xG"] + feat[prefix_away + "team_xG"]
    feat["shots_sum"] = feat[prefix_home + "team_shots"] + feat[prefix_away + "team_shots"]

    feat["chain_sum"] = feat[prefix_home + "team_xGChain"] + feat[prefix_away + "team_xGChain"]
    feat["buildup_sum"] = feat[prefix_home + "team_xGBuildup"] + feat[prefix_away + "team_xGBuildup"]

    feat["balance_xG_abs"] = abs(feat[prefix_home + "team_xG"] - feat[prefix_away + "team_xG"])
    feat["fragility_sum_top1xG"] = feat[prefix_home + "top1_xG_share"] + feat[prefix_away + "top1_xG_share"]

    return feat

if __name__ == "__main__":
    print("✅ features_soccer.py loaded. Import compute_match_features to use.")
