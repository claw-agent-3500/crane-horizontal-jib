"""Deflection: slope θ(x) and deflection δ(x) via double integration of M/(EI)."""

import numpy as np
from models import CraneModel
from .beam import get_section_at


def compute_deflection(model: CraneModel, x: np.ndarray, M: np.ndarray) -> dict:
    """
    Compute slope θ(x) and deflection δ(x) by double integration of M/(EI).

    Boundary conditions: θ(0) = 0, δ(0) = 0 (cantilever fixed at root).
    Deflection is positive downward (-Y direction).
    """
    n = len(x)
    dx = x[1] - x[0]

    # EI at each point
    EI = np.zeros(n)
    for j, xj in enumerate(x):
        sec = get_section_at(model.sections, xj)
        EI[j] = model.youngs_modulus * sec.moment_of_inertia if sec else 0

    # Curvature: κ = M / EI
    curvature = np.where(EI > 0, M / EI, 0)

    # First integration: θ(x) = ∫₀ˣ κ(ξ) dξ
    theta = np.zeros(n)
    for j in range(1, n):
        theta[j] = theta[j - 1] + (curvature[j - 1] + curvature[j]) * dx / 2.0

    # Second integration: δ(x) = ∫₀ˣ θ(ξ) dξ
    delta = np.zeros(n)
    for j in range(1, n):
        delta[j] = delta[j - 1] + (theta[j - 1] + theta[j]) * dx / 2.0

    return {'theta': theta, 'delta': delta}
