"""Beam analysis: shear force V(x), bending moment M(x), and wind load."""

import numpy as np
from models import CraneModel, LoadCase


def get_section_at(sections, x: float):
    """Get the section at position x."""
    for sec in sections:
        if sec.start <= x <= sec.end:
            return sec
    return None


def get_load_name(name: str) -> str:
    """Convert load name to coefficient key: lowercase, spaces→underscores."""
    return name.lower().replace(' ', '_').replace('-', '_').replace('+', '_')


def compute_beam(model: CraneModel, x: np.ndarray,
                 load_case: LoadCase = None,
                 trolley_pos: float = None) -> dict:
    """
    Compute V(x) and M(x) with load case coefficients and wind.

    Each load is multiplied by load_case.coef(load_name).
    Wind creates additional distributed load if wind_pressure > 0.
    """
    if load_case is None:
        load_case = LoadCase(name='Default', coefficients={}, wind_pressure=0.0)

    V = np.zeros_like(x)
    M = np.zeros_like(x)

    wind_pressure = load_case.wind_pressure  # Pa
    has_wind = wind_pressure > 0

    for i, xi in enumerate(x):
        # === Section self-weights (UDL) ===
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

            # Wind on section truss
            if has_wind and sec.wind_area > 0:
                # F_wind = pressure * area (N) → kN
                wind_force_per_m = wind_pressure * sec.wind_area / length_in if length_in > 0 else 0
                wind_force_per_m = wind_force_per_m / 1000.0 * sw_coef  # N/m → kN/m
                V[i] += wind_force_per_m * length_in
                M[i] += wind_force_per_m * (d_end**2 - d_start**2) / 2.0

        # === Additional UDLs ===
        for udl in model.udls:
            coef_key = get_load_name(udl.name)
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

            # Wind on UDL
            if has_wind and udl.wind_area > 0:
                wind_force_per_m = wind_pressure * udl.wind_area / 1000.0 * udl_coef
                V[i] += wind_force_per_m * length_in
                M[i] += wind_force_per_m * (d_end**2 - d_start**2) / 2.0

        # === Point loads ===
        for pl in model.point_loads:
            coef_key = get_load_name(pl.name)
            pl_coef = load_case.coef(coef_key)
            if pl_coef == 0:
                continue
            if pl.position > xi:
                P = pl.magnitude * pl_coef
                V[i] += P
                M[i] += P * (pl.position - xi)

                # Wind on point load
                if has_wind and pl.wind_area > 0:
                    wind_force = wind_pressure * pl.wind_area / 1000.0 * pl_coef  # N → kN
                    V[i] += wind_force
                    M[i] += wind_force * (pl.position - xi)

        # === Trolley load ===
        if model.trolley:
            trolley_coef = load_case.coef('trolley')
            if trolley_coef > 0:
                tp = trolley_pos if trolley_pos is not None else model.trolley.max_position
                mag = model.trolley.magnitude * trolley_coef
                if tp > xi:
                    V[i] += mag
                    M[i] += mag * (tp - xi)

                    # Wind on trolley
                    if has_wind and model.trolley.wind_area > 0:
                        wind_force = wind_pressure * model.trolley.wind_area / 1000.0 * trolley_coef
                        V[i] += wind_force
                        M[i] += wind_force * (tp - xi)

    return {'V': V, 'M': M}
