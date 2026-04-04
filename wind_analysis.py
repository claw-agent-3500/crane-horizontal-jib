"""Wind-only load diagram for analysis."""

import numpy as np
from models import CraneModel, LoadCase


def compute_wind_loads(model: CraneModel, x: np.ndarray, wind_pressure: float) -> dict:
    """Compute V and M from wind only (wind_pressure > 0)."""
    if wind_pressure <= 0:
        return {'V': np.zeros_like(x), 'M': np.zeros_like(x)}
    
    V = np.zeros_like(x)
    M = np.zeros_like(x)
    
    for i, xi in enumerate(x):
        # Wind on sections
        for sec in model.sections:
            if sec.wind_area <= 0:
                continue
            if sec.start >= xi:
                length_in = sec.length
                d_start, d_end = sec.start - xi, sec.end - xi
            elif sec.end > xi:
                length_in = sec.end - xi
                d_start, d_end = 0.0, sec.end - xi
            else:
                continue
            
            wind_force_per_m = wind_pressure * sec.wind_area / 1000.0  # N/m → kN/m
            V[i] += wind_force_per_m * length_in
            M[i] += wind_force_per_m * (d_end**2 - d_start**2) / 2.0
        
        # Wind on point loads
        for pl in model.point_loads:
            if pl.wind_area <= 0 or pl.position <= xi:
                continue
            wind_force = wind_pressure * pl.wind_area / 1000.0  # kN
            V[i] += wind_force
            M[i] += wind_force * (pl.position - xi)
        
        # Wind on UDLs
        for udl in model.udls:
            if udl.wind_area <= 0:
                continue
            if udl.start >= xi:
                length_in = udl.end - udl.start
                d_start, d_end = udl.start - xi, udl.end - xi
            elif udl.end > xi:
                length_in = udl.end - xi
                d_start, d_end = 0.0, udl.end - xi
            else:
                continue
            
            wind_force_per_m = wind_pressure * udl.wind_area / 1000.0
            V[i] += wind_force_per_m * length_in
            M[i] += wind_force_per_m * (d_end**2 - d_start**2) / 2.0
        
        # Wind on trolley
        if model.trolley and model.trolley.wind_area > 0:
            tp = model.trolley.max_position
            if tp > xi:
                wind_force = wind_pressure * model.trolley.wind_area / 1000.0
                V[i] += wind_force
                M[i] += wind_force * (tp - xi)
    
    return {'V': V, 'M': M}
