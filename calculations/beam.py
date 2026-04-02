"""Beam analysis: shear force V(x) and bending moment M(x)."""

import numpy as np
from models import CraneModel


def get_section_at(sections, x: float):
    """Get the section at position x."""
    for sec in sections:
        if sec.start <= x <= sec.end:
            return sec
    return None


def compute_beam(model: CraneModel, x: np.ndarray,
                 trolley_pos: float = None, trolley_mag: float = None) -> dict:
    """
    Compute V(x) and M(x) using right-portion approach.

    All loads act in -Y (downward). Positive V = net downward force to the right.
    Positive M = hogging moment (tension on top fiber for cantilever).
    """
    V = np.zeros_like(x)
    M = np.zeros_like(x)

    for i, xi in enumerate(x):
        # Section self-weights (UDL)
        for sec in model.sections:
            if sec.start >= xi:
                length_in, d_start, d_end = sec.length, sec.start - xi, sec.end - xi
            elif sec.end > xi:
                length_in, d_start, d_end = sec.end - xi, 0.0, sec.end - xi
            else:
                continue
            w = sec.weight_per_length
            V[i] += w * length_in
            M[i] += w * (d_end**2 - d_start**2) / 2.0

        # Additional UDLs
        for udl in model.udls:
            if udl.start >= xi:
                length_in, d_start, d_end = udl.end - udl.start, udl.start - xi, udl.end - xi
            elif udl.end > xi:
                length_in, d_start, d_end = udl.end - xi, 0.0, udl.end - xi
            else:
                continue
            w = udl.magnitude
            V[i] += w * length_in
            M[i] += w * (d_end**2 - d_start**2) / 2.0

        # Point loads
        for pl in model.point_loads:
            if pl.position > xi:
                V[i] += pl.magnitude
                M[i] += pl.magnitude * (pl.position - xi)

        # Trolley load (optional override for sweep)
        if trolley_pos is not None and trolley_pos > xi:
            mag = trolley_mag if trolley_mag is not None else 0
            V[i] += mag
            M[i] += mag * (trolley_pos - xi)

    return {'V': V, 'M': M}
