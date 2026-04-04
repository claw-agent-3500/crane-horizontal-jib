"""Seismic load analysis per ASCE 7-22 / Eurocode 8."""

import numpy as np
from dataclasses import dataclass
from typing import Optional
from models import CraneModel, LoadCase


@dataclass
class SeismicParams:
    """Seismic design parameters."""
    Ss: float = 0.0   # Short period spectral acceleration (g)
    S1: float = 0.0   # 1-second spectral acceleration (g)
    site_class: str = 'D'  # Site class (A-F)
    importance_factor: float = 1.0
    response_modification: float = 1.0  # R factor
    design_category: str = 'A'


def compute_seismic_response(model: CraneModel, x: np.ndarray, 
                              seismic: SeismicParams) -> dict:
    """
    Compute seismic load distribution along jib.
    
    Returns:
    - F_seismic: array of seismic forces (kN)
    - base_shear: total seismic base shear (kN)
    - moment: seismic moment at root (kN·m)
    """
    W_total = sum(pl.magnitude for pl in model.point_loads)
    W_total += sum(udl.magnitude * (udl.end - udl.start) for udl in model.udls)
    W_total += model.jib_length * 0.5  # self-weight estimate (kN/m)
    
    # Calculate spectral acceleration
    # SDS = (2/3) * Fa * Ss
    # SD1 = (2/3) * Fv * S1
    
    Fa = 1.0 if seismic.site_class in ('A', 'B', 'C') else 1.4
    Fv = 1.0 if seismic.site_class in ('A', 'B', 'C') else 1.8
    
    SDS = (2/3) * Fa * seismic.Ss if seismic.Ss > 0 else 0.0
    SD1 = (2/3) * Fv * seismic.S1 if seismic.S1 > 0 else 0.0
    
    # Seismic base coefficient (ASCE 7-22 simplified)
    Cs = SDS / seismic.response_modification if seismic.response_modification > 0 else 0.0
    Cs_max = SD1 / (seismic.response_modification * 1.0) if seismic.response_modification > 0 else float('inf')
    Cs = min(Cs, Cs_max) if SD1 > 0 else Cs
    
    # Base shear
    V = Cs * W_total if Cs > 0 else 0.0
    
    # Distribute along jib (simplified: triangular)
    F_seismic = np.zeros(len(x))
    for i, xi in enumerate(x):
        # Triangular distribution (more at tip for crane)
        ratio = xi / model.jib_length if model.jib_length > 0 else 0
        F_seismic[i] = V * ratio * 2 / model.jib_length  # kN/m
    
    # Base moment
    moment = V * model.jib_length / 3  # kN·m (triangular distribution)
    
    return {
        'F_seismic': F_seismic,
        'base_shear': V,
        'base_moment': moment,
        'SDS': SDS,
        'SD1': SD1,
        'Cs': Cs,
    }


def add_seismic_load_case(model: CraneModel, seismic: Optional[SeismicParams] = None) -> CraneModel:
    """Add seismic load case to model if seismic params provided."""
    if seismic is None or (seismic.Ss == 0 and seismic.S1 == 0):
        return model
    
    # Create seismic load case
    seismic_lc = LoadCase(
        name='Seismic',
        description=f"Seismic (SDC {seismic.design_category})",
        coefficients={'self_weight': 1.0, 'trolley': 1.0, 'payload': 1.0},
        wind_pressure=0.0,
    )
    
    model.load_cases.append(seismic_lc)
    return model