"""Beam analysis: shear force V(x) and bending moment M(x)."""

import numpy as np
from models import CraneModel, LoadCase


def get_section_at(sections, x: float):
    """Get the section at position x."""
    for sec in sections:
        if sec.start <= x <= sec.end:
            return sec
    return None


def _get_load_name(name: str) -> str:
    """Convert load name to coefficient key: lowercase, spaces→underscores."""
    return name.lower().replace(' ', '_').replace('-', '_').replace('+', '_')


def compute_beam(model: CraneModel, x: np.ndarray,
                 load_case: LoadCase = None,
                 trolley_pos: float = None) -> dict:
    """
    Compute V(x) and M(x) with load case coefficients.

    Each load is multiplied by load_case.coef(load_name).
    If load_case is None, all coefficients = 1.0.
    """
    if load_case is None:
        load_case = LoadCase(name='Default', coefficients={})

    V = np.zeros_like(x)
    M = np.zeros_like(x)

    for i, xi in enumerate(x):
        # Section self-weights (UDL) — coef_self_weight
        sw_coef = load_case.coef('self_weight')
        for sec in model.sections:
            if sec.start >= xi:
                length_in, d_start, d_end = sec.length, sec.start - xi, sec.end - xi
            elif sec.end > xi:
                length_in, d_start, d_end = sec.end - xi, 0.0, sec.end - xi
            else:
                continue
            w = sec.weight_per_length * sw_coef
            V[i] += w * length_in
            M[i] += w * (d_end**2 - d_start**2) / 2.0

        # Additional UDLs — each with own coef
        for udl in model.udls:
            coef_key = _get_load_name(udl.name)
            udl_coef = load_case.coef(coef_key)
            if udl_coef == 0:
                continue
            if udl.start >= xi:
                length_in, d_start, d_end = udl.end - udl.start, udl.start - xi, udl.end - xi
            elif udl.end > xi:
                length_in, d_start, d_end = udl.end - xi, 0.0, udl.end - xi
            else:
                continue
            w = udl.magnitude * udl_coef
            V[i] += w * length_in
            M[i] += w * (d_end**2 - d_start**2) / 2.0

        # Point loads — each with own coef
        for pl in model.point_loads:
            coef_key = _get_load_name(pl.name)
            pl_coef = load_case.coef(coef_key)
            if pl_coef == 0:
                continue
            if pl.position > xi:
                P = pl.magnitude * pl_coef
                V[i] += P
                M[i] += P * (pl.position - xi)

        # Trolley load — coef_trolley, optional position override
        if model.trolley:
            trolley_coef = load_case.coef('trolley')
            if trolley_coef > 0:
                tp = trolley_pos if trolley_pos is not None else model.trolley.max_position
                mag = model.trolley.magnitude * trolley_coef
                if tp > xi:
                    V[i] += mag
                    M[i] += mag * (tp - xi)

    return {'V': V, 'M': M}
