"""Data models for crane jib analysis."""

from dataclasses import dataclass, field
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
    height: float             # m ( Y dimension, depth)
    wind_area: float = 0.0   # m² (projected area for wind)
    cg_x: float = 0.0         # X coordinate of CG (m from root)
    cg_y: float = 0.0         # Y coordinate of CG (m, positive up)
    cg_z: float = 0.0         # Z coordinate of CG (m)
    yield_strength: float = 345.0  # MPa (default Q345 steel)
    truss: Optional[TrussConfig] = None

    @property
    def length(self) -> float:
        return self.end - self.start


@dataclass
class PointLoad:
    name: str
    position: float  # X position (m from root)
    magnitude: float  # kN (downward, -Y)
    wind_area: float = 0.0  # m² (projected area for wind)
    cg_x: float = 0.0      # X coordinate of CG
    cg_y: float = 0.0       # Y coordinate of CG
    cg_z: float = 0.0       # Z coordinate of CG


@dataclass
class UDL:
    name: str
    start: float      # X start (m)
    end: float        # X end (m)
    magnitude: float  # kN/m (downward, -Y)
    wind_area: float = 0.0  # m²/m (projected area per meter)
    cg_x: float = 0.0       # X coordinate of CG (midpoint)
    cg_y: float = 0.0       # Y coordinate of CG
    cg_z: float = 0.0       # Z coordinate of CG


@dataclass
class Trolley:
    """Trolley + payload moving along the jib."""
    magnitude: float          # kN (trolley + payload)
    min_position: float        # m from root (closest to root)
    max_position: float        # m from root (closest to tip)
    step: float = 1.0          # m step for envelope computation
    wind_area: float = 0.0    # m² (projected area for wind)
    cg_x: float = 0.0          # X coordinate of CG
    cg_y: float = 0.0          # Y coordinate of CG
    cg_z: float = 0.0          # Z coordinate of CG


@dataclass
class LoadCase:
    """A load case with named coefficients for each load."""
    name: str
    coefficients: dict = field(default_factory=dict)
    wind_pressure: float = 0.0  # Pa (0 = no wind for this case)

    def coef(self, load_name: str) -> float:
        """Get coefficient for a named load. Defaults to 1.0."""
        return self.coefficients.get(load_name, 1.0)


@dataclass
class ReportConfig:
    """Configuration for which sections to include in the HTML report."""
    # Summary
    summary: bool = True
    
    # Diagrams
    sfd: bool = True
    bmd: bool = True
    deflection: bool = True
    stress: bool = True
    chord_forces: bool = True
    diagonal_forces: bool = True
    wind: bool = True
    utilization: bool = True
    
    # Tables
    sections_table: bool = True
    loads_table: bool = True
    section_forces_table: bool = True
    utilization_table: bool = True
    load_case_summary: bool = True
    
    # Options
    show_schematic: bool = True
    show_worst_trolley: bool = True
    show_serviceability: bool = True
    decimal_places: int = 1


@dataclass
class CraneModel:
    name: str
    jib_length: float
    jib_height_position: float = 0.0
    youngs_modulus: float = DEFAULT_E
    serviceability_limit: str = 'L/250'  # L/250, L/400, or custom ratio
    sections: list[Section] = field(default_factory=list)
    point_loads: list[PointLoad] = field(default_factory=list)
    udls: list[UDL] = field(default_factory=list)
    num_points: int = 500
    trolley: Optional[Trolley] = None
    load_cases: list[LoadCase] = field(default_factory=list)
    report_config = None  # set after init


# ── Analysis results ─────────────────────────────────────────────────────

@dataclass
class SectionForcesAtStart:
    """Truss member forces at a section's start position."""
    section: str
    x: float
    upper_chord: float  # + compression, - tension
    lower_chord: float  # + compression, - tension
    comp_diag: float
    tens_diag: float
    neut_diag: float


@dataclass
class AnalysisResult:
    """Container for all analysis outputs."""
    # Fields with defaults first
    section_forces_at_start: list = field(default_factory=list)
    worst_trolley_pos: float = 0.0

    # Per-load-case summary results
    load_case_results: list = field(default_factory=list)  # list of {name, max_V, max_M, max_sigma, max_utilization, tip_delta}

    # Grid arrays (no default)
    x: np.ndarray = None
    V_base: np.ndarray = None
    M_base: np.ndarray = None
    V: np.ndarray = None
    M: np.ndarray = None
    theta: np.ndarray = None
    delta: np.ndarray = None
    sigma: np.ndarray = None
    tau: np.ndarray = None
    F_upper_chord: np.ndarray = None
    F_lower_chord: np.ndarray = None
    F_comp_diag: np.ndarray = None
    F_tens_diag: np.ndarray = None
    F_neut_diag: np.ndarray = None

    # Summary scalars (no default)
    reaction_V: float = 0.0
    reaction_M: float = 0.0
    max_V: float = 0.0
    max_V_pos: float = 0.0
    max_M: float = 0.0
    max_M_pos: float = 0.0
    max_sigma: float = 0.0
    max_sigma_pos: float = 0.0
    max_delta: float = 0.0
    max_delta_pos: float = 0.0
    tip_delta: float = 0.0
    max_F_upper: float = 0.0
    max_F_lower: float = 0.0
    max_F_comp_diag: float = 0.0
    max_F_tens_diag: float = 0.0

    # Utilization
    max_utilization: float = 0.0
    max_utilization_pos: float = 0.0
    section_utilization: list = field(default_factory=list)

    # Per-section forces at start (with default)
    section_forces_at_start: list = field(default_factory=list)
    worst_trolley_pos: float = 0.0

    # Reference data (no default, come last)
    sections: list[Section] = None
    model: CraneModel = None

    def __post_init__(self):
        """Convert None defaults to empty arrays for numpy fields."""
        np_fields = ['x', 'V_base', 'M_base', 'V', 'M', 'theta', 'delta', 
                     'sigma', 'tau', 'F_upper_chord', 'F_lower_chord', 
                     'F_comp_diag', 'F_tens_diag', 'F_neut_diag']
        for f in np_fields:
            val = getattr(self, f)
            if val is None:
                setattr(self, f, np.array([]))


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


