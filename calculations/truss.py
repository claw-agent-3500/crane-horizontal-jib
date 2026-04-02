"""Truss member forces: chord forces and diagonal forces."""

import numpy as np
from models import CraneModel
from .beam import get_section_at


def compute_truss_forces(model: CraneModel, x: np.ndarray,
                         M: np.ndarray, V: np.ndarray) -> dict:
    """
    Compute truss member forces along the jib.

    Chord forces:   F = M / h  (split by chord count per side)
    Diagonal forces: F = V / sin(θ)  (sign by type)

    Upper chord: compression (+)
    Lower chord: tension (-)
    Compression diagonal: +|V|/sin(θ)
    Tension diagonal: -|V|/sin(θ)
    Neutral diagonal: |V|/sin(θ)
    """
    n = len(x)
    F_upper = np.zeros(n)
    F_lower = np.zeros(n)
    F_comp_diag = np.zeros(n)
    F_tens_diag = np.zeros(n)
    F_neut_diag = np.zeros(n)

    for j, xj in enumerate(x):
        sec = get_section_at(model.sections, xj)
        if not sec or not sec.truss:
            continue

        tr = sec.truss
        h = sec.height

        # Chord forces: split M/h by number of chords per side
        if tr.upper_chords > 0 and h > 0:
            F_upper[j] = M[j] / (h * tr.upper_chords)   # compression
        if tr.lower_chords > 0 and h > 0:
            F_lower[j] = -M[j] / (h * tr.lower_chords)  # tension

        # Diagonal forces: |V|/sin(θ)
        if tr.compression_diagonal and tr.compression_diagonal.present:
            sin_t = np.sin(np.radians(tr.compression_diagonal.angle))
            F_comp_diag[j] = abs(V[j]) / sin_t if sin_t > 0.01 else 0

        if tr.tension_diagonal and tr.tension_diagonal.present:
            sin_t = np.sin(np.radians(tr.tension_diagonal.angle))
            F_tens_diag[j] = -abs(V[j]) / sin_t if sin_t > 0.01 else 0

        if tr.neutral_diagonal and tr.neutral_diagonal.present:
            sin_t = np.sin(np.radians(tr.neutral_diagonal.angle))
            F_neut_diag[j] = abs(V[j]) / sin_t if sin_t > 0.01 else 0

    return {
        'F_upper_chord': F_upper,
        'F_lower_chord': F_lower,
        'F_comp_diag': F_comp_diag,
        'F_tens_diag': F_tens_diag,
        'F_neut_diag': F_neut_diag,
    }
