"""Fatigue analysis using S-N curve approach."""

import numpy as np
from dataclasses import dataclass
from typing import List
from models import CraneModel


@dataclass
class FatigueResult:
    """Fatigue analysis results."""
    damage: float  # cumulative damage ratio (0-1 = OK, >1 = failed)
    cycles: int    # estimated cycles
    stress_range: float  # stress range (MPa)
    safe_life: float    # safe fatigue life (years)
    failed: bool        # True if damage > 1.0


def estimate_cycles(model: CraneModel, load_case) -> int:
    """
    Estimate number of stress cycles per year.
    
    Typical tower crane jib:
    - 10,000-30,000 cycles/year for medium usage
    - 30,000-100,000 for high usage
    """
    # Base on load magnitude
    base_cycles = 20000
    
    # Adjust for load intensity
    if load_case.coefficients:
        max_coef = max(load_case.coefficients.values()) if load_case.coefficients else 1.0
        base_cycles *= (1 + max_coef * 0.5)
    
    return int(base_cycles)


def compute_fatigue_damage(model: CraneModel, result, load_case) -> FatigueResult:
    """
    Compute fatigue damage using S-N curve (log-log linear).
    
    Miner's rule: D = Σ(n_i / N_i)
    
    Where:
    - n_i = actual cycles at stress range S_i
    - N_i = allowable cycles from S-N curve at S_i
    - S-N curve: N = 10^((log_S - log_a) / m)
    
    For steel (log_a = 17, m = 5 for detail category D)
    """
    # Get stress range from analysis
    sigma_max = np.max(np.abs(result.sigma))
    sigma_min = 0.0  # assume tension-tension cycling
    delta_sigma = sigma_max - sigma_min
    
    # S-N curve parameters (detail category D, welded steel)
    log_a = 17.0  # intercept
    m = 5.0      # slope
    
    # Allowable cycles at this stress range
    if delta_sigma > 0:
        log_N = (np.log10(delta_sigma) * m - log_a) / m
        N_allow = 10 ** (-log_N) if log_N < 0 else 10 ** (log_N)
    else:
        N_allow = float('inf')
    
    # Actual cycles
    n_actual = estimate_cycles(model, load_case)
    
    # Damage ratio (Miner's rule)
    if N_allow == float('inf') or N_allow <= 0:
        damage = 0.0
    else:
        damage = n_actual / N_allow
    
    # Safe life (years before failure)
    safe_life = 1.0 / damage if damage > 0 else float('inf')
    
    return FatigueResult(
        damage=damage,
        cycles=n_actual,
        stress_range=delta_sigma,
        safe_life=safe_life,
        failed=damage > 1.0,
    )


def add_fatigue_to_result(result, load_case):
    """Add fatigue analysis to existing result."""
    fatigue = compute_fatigue_damage(result.model, result, load_case)
    result.fatigue = fatigue
    return result