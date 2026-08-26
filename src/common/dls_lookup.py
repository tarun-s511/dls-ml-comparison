import numpy as np
import math

# DLS Standard Edition Parameters (from fitted model)
# Z(u, w) = Z0(w) * (1 - exp(-b(w) * u))
# where u is overs remaining, w is wickets lost
DLS_PARAMS = {
    0: {"Z0": 134.1023, "b": 0.0274},
    1: {"Z0": 118.5254, "b": 0.0310},
    2: {"Z0": 101.9144, "b": 0.0360},
    3: {"Z0": 84.4529, "b": 0.0435},
    4: {"Z0": 66.9956, "b": 0.0549},
    5: {"Z0": 50.2810, "b": 0.0731},
    6: {"Z0": 35.1161, "b": 0.1046},
    7: {"Z0": 21.9899, "b": 0.1672},
    8: {"Z0": 11.9074, "b": 0.3099},
    9: {"Z0": 4.7001, "b": 0.7632},
    10: {"Z0": 0.0, "b": 1.0}  # All out: 0 resources remaining
}

# Base resource score for 50 overs with 0 wickets lost
Z_50_0 = DLS_PARAMS[0]["Z0"] * (1.0 - np.exp(-DLS_PARAMS[0]["b"] * 50))

def get_resource_pct(overs_remaining, wickets_lost):
    """
    Computes the resource percentage remaining for a given state.
    Allows fractional overs (e.g. 19.3 overs remaining).
    """
    # Clip wickets lost to [0, 10]
    wickets_lost = int(clip(wickets_lost, 0, 10))
    if wickets_lost >= 10:
        return 0.0
    
    # Clip overs remaining to [0, 50]
    overs_remaining = max(0.0, float(overs_remaining))
    
    params = DLS_PARAMS[wickets_lost]
    Z0 = params["Z0"]
    b = params["b"]
    
    Z = Z0 * (1.0 - np.exp(-b * overs_remaining))
    resource_pct = (Z / Z_50_0) * 100.0
    
    return clip(resource_pct, 0.0, 100.0)

def clip(val, min_val, max_val):
    return min(max(val, min_val), max_val)

def calculate_par_score(s1, r1, r2, g50=245.0):
    """
    Calculates the revised target/par score for Team 2 based on:
    - s1: Team 1 final score (or current score at interruption)
    - r1: Team 1 resources used (%)
    - r2: Team 2 resources available (%)
    - g50: Standard G50 value (default 245)
    """
    if r1 <= 0.0:
        return 0
    
    if r2 <= r1:
        # Team 2 has fewer resources
        par = s1 * (r2 / r1)
    else:
        # Team 2 has more resources
        par = s1 + g50 * ((r2 - r1) / 100.0)
    
    # Par score is the score to TIE, target is par + 1
    # DLS target is floor(par) + 1
    return int(math.floor(par) + 1)
