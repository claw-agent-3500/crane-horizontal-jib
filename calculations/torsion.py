"""Torsion analysis for jib cross-section."""

import numpy as np
from models import CraneModel


def compute_torsion(model: CraneModel, x: np.ndarray, V: np.ndarray, 
                    point_loads: list, udls: list) -> dict:
    """
    Compute torsional effects from eccentric loads.
    
    For a crane jib, torsion arises from:
    - Trolley position (offset from centroid)
    - Eccentric load points
    
    Returns:
    - T: torsion moment array (kN·m)
    - tau: shear stress from torsion (MPa)
    - max_torsion: maximum torsion moment
    """
    results = {
        'T': np.zeros(len(x)),
        'tau': np.zeros(len(x)),
        'max_torsion': 0.0,
    }
    
    # Get trolley position from model
    trolley_x = (model.trolley.min_position + model.trolley.max_position) / 2 if model.trolley else model.jib_length / 2
    
    # For each x, compute torsion from point loads and UDLs
    for i, xi in enumerate(x):
        T_i = 0.0
        
        # Point loads - if eccentric, add torsion
        for pl in model.point_loads:
            if pl.position <= xi:
                # Eccentric moment arm (assume 0.5m offset from centroid)
                arm = 0.5  # m (offset from centerline)
                T_i += pl.magnitude * arm
        
        # UDLs
        for udl in model.udls:
            if udl.start <= xi <= udl.end:
                # Distributed load creates torsion
                arm = 0.5  # m
                length = min(xi, udl.end) - max(0, udl.start)
                T_i += udl.magnitude * arm * length
        
        results['T'][i] = T_i
    
    # Compute shear stress from torsion
    # tau = T / W_t where W_t is torsion section modulus
    W_t = 0.001  # m³ (approximate, would need actual J)
    for i in range(len(x)):
        if results['T'][i] != 0:
            results['tau'][i] = abs(results['T'][i]) / W_t / 1000  # MPa
    
    results['max_torsion'] = np.max(np.abs(results['T']))
    
    return results


def add_torsion_to_result(result, load_case):
    """Add torsion analysis to existing result."""
    x = result.x
    from calculations.beam import compute_beam
    beam = compute_beam(result.model, x, load_case)
    V = beam['V']
    
    torsion = compute_torsion(result.model, x, V, 
                                result.model.point_loads,
                                result.model.udls)
    
    result.torsion = torsion
    return result