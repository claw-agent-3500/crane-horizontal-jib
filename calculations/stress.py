"""Stress: bending stress σ and shear stress τ."""

import numpy as np
from models import CraneModel
from .beam import get_section_at


def compute_stress(model: CraneModel, x: np.ndarray,
                   M: np.ndarray, V: np.ndarray) -> dict:
    """
    Compute bending stress σ = M·c/I and average shear stress τ = V/A.

    Returns stresses in MPa (kN/m² / 1000).
    """
    n = len(x)
    sigma = np.zeros(n)
    tau = np.zeros(n)

    for j, xj in enumerate(x):
        sec = get_section_at(model.sections, xj)
        if sec:
            c = sec.height / 2.0
            I = sec.moment_of_inertia
            A = sec.area
            sigma[j] = (M[j] * c / I / 1000.0) if I > 0 else 0
            tau[j] = (V[j] / A / 1000.0) if A > 0 else 0

    return {'sigma': sigma, 'tau': tau}
