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