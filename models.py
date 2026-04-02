"""Data models for crane jib analysis."""

from dataclasses import dataclass
from typing import Optional

import numpy as np


# ── Constants ─────────────────────────────────────────────────────────────

MAX_POINT_LOADS = 5
MAX_UDLS = 5
DEFAULT_E = 200e6  # kN/m² (200 GPa steel)


# ── Truss geometry ────────────────────────────────────────────────────────

@dataclass
class DiagonalConfig:
    """Configuration for one diagonal type in a truss web."""
    angle: float    # degrees from horizontal (X axis)
    present: bool = True


@dataclass
class TrussConfig:
    """Cross-section truss geometry for a section."""
    upper_chords: int = 2      # 1 or 2
    lower_chords: int = 2      # 1 or 2
    compression_diagonal: Optional[DiagonalConfig] = None
    tension_diagonal: Optional[DiagonalConfig] = None
    neutral_diagonal: Optional[DiagonalConfig] = None


# ── Structural elements ──────────────────────────────────────────────────

@dataclass
class Section:
    name: str
    start: float              # X start (m)
    end: float                # X end (m)
    weight_per_length: float  # kN/m (self-weight, acts in -Y)
    area: float               # m² (effective A)
    moment_of_inertia: float  # m⁴ (I about Z axis)
    height: float             # m (Y dimension, depth)
    truss: Optional[TrussConfig] = None

    @property
    def length(self) -> float:
        return self.end - self.start


@dataclass
class PointLoad:
    name: str
    position: float  # X position (m from root)
    magnitude: float  # kN (downward, -Y)


@dataclass
class UDL:
    name: str
    start: float      # X start (m)
    end: float        # X end (m)
    magnitude: float  # kN/m (downward, -Y)


@dataclass
class TrolleySweep:
    magnitude: float          # kN (trolley + payload)
    min_position: float = 3.0
    max_position: float = 0.0  # 0 = auto (jib_length - 2m)
    step: float = 1.0


@dataclass
class CraneModel:
    name: str
    jib_length: float
    sections: list[Section]
    point_loads: list[PointLoad]
    udls: list[UDL]
    youngs_modulus: float = DEFAULT_E
    num_points: int = 500
    trolley_sweep: Optional[TrolleySweep] = None


# ── Analysis results ─────────────────────────────────────────────────────

@dataclass
class AnalysisResult:
    """Container for all analysis outputs. Add new fields as modules grow."""
    # Grid
    x: np.ndarray

    # Beam results (from calculations.beam)
    V: np.ndarray          # Shear force (kN)
    M: np.ndarray          # Bending moment (kN·m)

    # Deflection (from calculations.deflection)
    theta: np.ndarray      # Slope (rad)
    delta: np.ndarray      # Deflection (m, positive = downward)

    # Stresses (from calculations.stress)
    sigma: np.ndarray      # Bending stress (MPa)
    tau: np.ndarray         # Shear stress (MPa)

    # Truss member forces (from calculations.truss)
    F_upper_chord: np.ndarray    # kN (compression = positive)
    F_lower_chord: np.ndarray    # kN (tension = negative)
    F_comp_diag: np.ndarray      # kN (compression diagonal)
    F_tens_diag: np.ndarray      # kN (tension diagonal)
    F_neut_diag: np.ndarray      # kN (neutral diagonal)

    # Summary scalars
    reaction_V: float
    reaction_M: float
    max_V: float
    max_V_pos: float
    max_M: float
    max_M_pos: float
    max_sigma: float
    max_sigma_pos: float
    max_delta: float
    max_delta_pos: float
    tip_delta: float
    max_F_upper: float
    max_F_lower: float
    max_F_comp_diag: float
    max_F_tens_diag: float

    # Reference data
    sections: list[Section]
    model: 'CraneModel'


@dataclass
class SweepResult:
    positions: np.ndarray
    root_moments: np.ndarray
    root_shears: np.ndarray
    tip_deflections: np.ndarray
    worst_position: float
    worst_moment: float
    worst_shear: float
    worst_deflection: float
