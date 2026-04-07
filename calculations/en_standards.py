"""
EN 14439:2025 and EN 13001 Crane Standards Implementation
"""

import numpy as np

# EN 14439 Load Cases (Table 2)
EN14439_CASES = {
    'H1': {'name': 'Normal Working', 'gamma_F': 1.0, 'gamma_W': 0.0},
    'H2': {'name': 'Working with Wind', 'gamma_F': 1.0, 'gamma_W': 1.0, 'psi0': 0.6},
    'H3': {'name': 'Crane Standing', 'gamma_F': 1.0, 'gamma_W': 1.0},
    'H4': {'name': 'Proof Load', 'gamma_F': 1.25, 'gamma_W': 0.0},
    'H5': {'name': 'Safety Test', 'gamma_F': 1.5, 'gamma_W': 0.0},
    'H6': {'name': 'Storm', 'gamma_F': 1.0, 'gamma_W': 1.0},
}

# Partial factors (EN 13001)
GAMMA_M = {'yield': 1.25, 'ultimate': 1.10, 'buckling': 1.10, 'fatigue': 1.35}

# Fatigue categories
FATIGUE_CAT = {'A': 18.0, 'B': 17.0, 'C': 16.0, 'D': 15.0, 'E': 14.0, 'F': 13.0}


def compute_en14439(base_loads, case):
    """Compute loads for EN 14439 case."""
    c = EN14439_CASES.get(case, EN14439_CASES['H1'])
    return {
        'G': base_loads.get('self_weight', 0) * c['gamma_F'],
        'Q': base_loads.get('payload', 0) * c['gamma_F'],
        'W': base_loads.get('wind', 0) * c['gamma_W'],
    }


def ulm_check(M_kNm, Z_m3, fy_MPa):
    """ULS check per EN 13001."""
    sigma = (M_kNm * 1000) / (Z_m3 * 1e6)
    sigma_d = GAMMA_M['yield'] * sigma
    fy_d = fy_MPa / GAMMA_M['yield']
    return {'sigma_MPa': sigma, 'design_MPa': sigma_d, 'allowable_MPa': fy_d, 'pass': sigma_d <= fy_d}


def fatigue_en(Delta_sigma_MPa, n_cycles, cat='D'):
    """Fatigue per EN 13001."""
    log_a = FATIGUE_CAT.get(cat, 15.0)
    m = 5.0
    if Delta_sigma_MPa > 0:
        log_N = (np.log10(Delta_sigma_MPa) * m - log_a) / m
        N_allow = 10**log_N if log_N > 0 else float('inf')
    else:
        N_allow = float('inf')
    damage = n_cycles / N_allow if N_allow > 0 else 0
    return {'damage': damage, 'safe_years': 1/damage if damage > 0 else float('inf'), 'pass': damage < 1.0}


def buckling_en(N_kN, L_m, A_m2, I_m4, fy_MPa=345):
    """Column buckling per EN 1993-1-1."""
    E = 210000  # MPa
    N_cr = (np.pi**2 * E * I_m4 * 1e12) / (L_m * 1000)**2 / 1000
    lam = L_m / np.sqrt(I_m4 / A_m2)
    alpha = 0.49
    phi = 0.5 * (1 + alpha * (lam/100)**0.5 + (lam/100)**2)
    chi = 1.0 / (phi + np.sqrt(phi**2 - (lam/100)**2))
    N_bd = chi * A_m2 * 1e6 * (fy_MPa/1.25) / 1000
    return {'N_cr_kN': N_cr, 'chi': chi, 'N_bd_kN': N_bd, 'util': N_kN/N_bd, 'pass': N_kN/N_bd < 1.0}

# =============================================================================
# FEM 1.001 - European Federation of Materials Handling Standards
# =============================================================================
# FEM 1.001: Rules for the design of cranes
# FEM 1.002: Principles for crane structures
# FEM 1.004: Classification and utilization
# FEM L 02 100: Fatigue strength calculation method

# FEM Classification of mechanisms (Table 1)
FEM_MECHANISM_GROUPS = {
    'T1': {'description': 'Light duty', ' utilization_factor': 0.25},
    'T2': {'description': 'Medium duty', ' utilization_factor': 0.50},
    'T3': {'description': 'Heavy duty', ' utilization_factor': 0.63},
    'T4': {'description': 'Very heavy duty', ' utilization_factor': 0.75},
    'T5': {'description': 'Continuous', ' utilization_factor': 1.00},
    'T6': {'description': 'Severe continuous', ' utilization_factor': 1.25},
    'T7': {'description': 'Intermittent periodic', ' utilization_factor': 1.60},
    'T8': {'description': 'Continuous periodic', ' utilization_factor': 2.00},
}

# FEM fatigue classes (Table A.1)
FEM_FATIGUE_CLASSES = {
    'A': {'beta': 5, 'sigma_a': 140, 'description': 'Excellent (welded, polished)'},
    'B': {'beta': 5, 'sigma_a': 112, 'description': 'Good (welded, machined)'},
    'C': {'beta': 5, 'sigma_a': 90, 'description': 'Standard (welded, as-welded)'},
    'D': {'beta': 5, 'sigma_a': 71, 'description': 'Low (welded, not treated)'},
    'E': {'beta': 5, 'sigma_a': 56, 'description': 'Very low (welded, with notch)'},
}


def compute_fem_fatigue(sigma_max_MPa: float, sigma_min_MPa: float, 
                       n_cycles: int, fem_class: str = 'C') -> dict:
    """
    Fatigue calculation per FEM L 02 100.
    
    Uses S-N curve with slope m = 5 (beta)
    
    N = (sigma_a / sigma_r)^m
    
    where:
      sigma_a = allowable stress range
      sigma_r = actual stress range
      m = 5 (slope)
    """
    fc = FEM_FATIGUE_CLASSES.get(fem_class, FEM_FATIGUE_CLASSES['C'])
    m = fc['beta']  # slope
    sigma_a = fc['sigma_a']  # MPa
    
    # Stress range
    sigma_r = abs(sigma_max_MPa - sigma_min_MPa)
    
    # Allowable cycles
    if sigma_r > 0:
        N_allow = (sigma_a / sigma_r) ** m
    else:
        N_allow = float('inf')
    
    # Damage
    damage = n_cycles / N_allow if N_allow > 0 else 0
    
    # Safe life
    safe_life_years = 1.0 / damage if damage > 0 and n_cycles > 0 else float('inf')
    
    return {
        'sigma_range_MPa': sigma_r,
        'n_cycles': n_cycles,
        'N_allowable': N_allow,
        'damage': damage,
        'safe_life_years': safe_life_years,
        'fem_class': fem_class,
        'sigma_a_MPa': sigma_a,
        'passes': damage < 1.0,
    }


def compute_fem_group(jib_length: float, swl_kN: float, tm_per_hour: float) -> str:
    """
    Determine FEM mechanism group based on:
    - Jib length
    - Safe Working Load (SWL)
    - Operating time per hour
    """
    # Calculate utilization factor
    # Based on class of crane and operating time
    if tm_per_hour < 1:
        return 'T1'
    elif tm_per_hour < 2:
        return 'T2'
    elif tm_per_hour < 4:
        return 'T3'
    elif tm_per_hour < 8:
        return 'T4'
    elif tm_per_hour < 12:
        return 'T5'
    elif tm_per_hour < 16:
        return 'T6'
    elif tm_per_hour < 20:
        return 'T7'
    else:
        return 'T8'


def compute_fem_service_factor(swl_kN: float, actual_load_kN: float) -> dict:
    """
    FEM service factor calculation.
    
    k = S_actual / S_max
    
    Should be >= 1.0 for normal operation
    """
    k = actual_load_kN / swl_kN if swl_kN > 0 else 0
    
    return {
        'swl_kN': swl_kN,
        'actual_load_kN': actual_load_kN,
        'service_factor': k,
        'ok': k <= 1.0,
    }


def compute_fem_wind_operating_limit(
    wind_speed_m_s: float,
    jib_area_m2: float,
    jib_weight_kN: float,
) -> dict:
    """
    Calculate if crane can operate in given wind per FEM.
    
    Wind pressure: q = 0.5 * rho * v^2
    """
    rho = 1.225  # kg/m³ air density
    
    # Wind pressure
    q = 0.5 * rho * wind_speed_m_s ** 2  # Pa
    
    # Wind force
    F_wind = q * jib_area_m2 / 1000  # kN
    
    # Check against limit (typically 0.3 * SWL for operation)
    swl = 120  # assume 120kN SWL
    limit = 0.3 * swl
    
    return {
        'wind_speed_m_s': wind_speed_m_s,
        'wind_pressure_Pa': q,
        'wind_force_kN': F_wind,
        'operating_limit_kN': limit,
        'can_operate': F_wind <= limit,
    }
