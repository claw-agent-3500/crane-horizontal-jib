"""
Cathead (Turntable) Structural Analysis

The cathead is the horizontal truss structure at crane apex:
- Connects jib and counterjib at pivot point
- Supports trolley on jib side
- Transfers all loads to slewing bearing

Structure: Similar to jib (truss with sections, self-weight, wind area)
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional
from models import (
    CraneModel, Section, PointLoad, UDL, Trolley, LoadCase,
    TrussConfig, DiagonalConfig
)


@dataclass
class CatheadConfig:
    """Configuration for cathead structural analysis."""
    length: float = 0.0  # Total cathead length (m)
    height: float = 0.0  # Height above tower (m)
    width: float = 0.0  # Width of truss (m)
    
    # Structural properties
    sections: List[Section] = field(default_factory=list)
    truss_config: Optional[TrussConfig] = None
    
    # Self-weight (kN)
    self_weight: float = 0.0
    
    # Wind area (m²)
    wind_area: float = 0.0
    
    # CG coordinates (from pivot point)
    cg_x: float = 0.0  # m from pivot (jib side positive)
    cg_y: float = 0.0  # m above pivot
    cg_z: float = 0.0  # m from centerline


def create_cathead_model(
    length: float,
    height: float = 0.0,
    width: float = 1.5,
    self_weight: float = 50.0,
    wind_area: float = 8.0,
    cg_offset: float = 1.0,  # CG offset from center
    youngs_modulus: float = 200000.0,  # MPa
    yield_strength: float = 345.0,  # MPa
) -> CraneModel:
    """
    Create CraneModel for cathead structural analysis.
    """
    # Calculate average weight per length
    weight_per_m = self_weight / length if length > 0 else 0
    
    # Default sections
    sections = [
        Section(
            name='Root',
            start=0.0,
            end=length * 0.2,
            weight_per_length=weight_per_m * 0.6,
            area=0.02,
            moment_of_inertia=0.005,
            height=width,
            yield_strength=yield_strength,
        ),
        Section(
            name='Mid',
            start=length * 0.2,
            end=length * 0.8,
            weight_per_length=weight_per_m,
            area=0.025,
            moment_of_inertia=0.006,
            height=width,
            yield_strength=yield_strength,
        ),
        Section(
            name='Tip',
            start=length * 0.8,
            end=length,
            weight_per_length=weight_per_m * 0.6,
            area=0.02,
            moment_of_inertia=0.005,
            height=width,
            yield_strength=yield_strength,
        ),
    ]
    
    # Self-weight as UDL
    udls = [
        UDL(
            name='self_weight',
            start=0.0,
            end=length,
            magnitude=weight_per_m,
        ),
    ]
    
    # No point loads (trolley is on jib, not cathead)
    point_loads = []
    
    # Create model
    model = CraneModel(
        name='Cathead',
        jib_length=length,
        jib_height_position=height,
        sections=sections,
        point_loads=point_loads,
        udls=udls,
        youngs_modulus=youngs_modulus,
        load_cases=[
            LoadCase(
                name='Cathead Load',
                coefficients={'self_weight': 1.0},
            ),
        ],
    )
    
    # Store CG info
    model.cg_x = cg_offset
    model.cg_y = height
    model.cg_z = 0.0
    model.wind_area = wind_area
    
    return model


def compute_cathead_wind_load(
    cathead_model: CraneModel,
    wind_pressure: float,  # Pa
) -> float:
    """
    Compute wind force on cathead.
    
    F_wind = pressure × area × Cd
    """
    # Drag coefficient for truss ~1.2
    Cd = 1.2
    
    area = getattr(cathead_model, 'wind_area', 8.0)  # m²
    
    return wind_pressure * area * Cd / 1000  # kN


def analyze_cathead(config: CatheadConfig, load_case: LoadCase = None):
    """
    Analyze cathead structure.
    """
    from crane_calc import run_analysis
    
    # Create model
    model = create_cathead_model(
        length=config.length,
        height=config.height,
        width=config.truss_config.height if config.truss_config else 1.5,
        self_weight=config.self_weight,
        wind_area=config.wind_area,
        cg_offset=config.cg_x,
    )
    
    # Run analysis
    result = run_analysis(model)
    
    return model, result


# Standard cathead sizes per crane class
CATHEAD_CONFIGS = {
    'TC7030-12': {
        'length': 6.0,
        'self_weight': 45.0,  # kN
        'wind_area': 7.0,  # m²
        'cg_offset': 0.5,  # m from center
    },
    'TC7030-15': {
        'length': 7.0,
        'self_weight': 55.0,
        'wind_area': 8.5,
        'cg_offset': 0.6,
    },
    'TC7030-18': {
        'length': 8.0,
        'self_weight': 65.0,
        'wind_area': 10.0,
        'cg_offset': 0.7,
    },
}


def get_cathead_for_crane(crane_name: str, custom: dict = None) -> CraneModel:
    """
    Get appropriate cathead model for crane type.
    """
    config = CATHEAD_CONFIGS.get(crane_name, CATHEAD_CONFIGS['TC7030-12'])
    
    if custom:
        config.update(custom)
    
    return create_cathead_model(
        length=config['length'],
        self_weight=config['self_weight'],
        wind_area=config['wind_area'],
        cg_offset=config['cg_offset'],
    )


def compute_load_path(
    jib_result,
    counterjib_result,
    cathead_result,
    tower_height: float = 30.0,
    bearing_diameter: float = 2.0,
) -> dict:
    """
    Compute complete load path with proper cathead analysis.
    """
    # Vertical loads
    Fz_jib = np.max(np.abs(jib_result.V)) if hasattr(jib_result, 'V') else 0
    Fz_counter = np.max(np.abs(counterjib_result.V)) if hasattr(counterjib_result, 'V') else 0
    Fz_cathead = np.max(np.abs(cathead_result.V)) if hasattr(cathead_result, 'V') else 0
    
    Fz_total = Fz_jib + Fz_counter + Fz_cathead
    
    # Moments from jib and counterjib at pivot
    M_jib = np.max(np.abs(jib_result.M))
    M_counter = np.max(np.abs(counterjib_result.M))
    M_cathead = np.max(np.abs(cathead_result.M))
    
    # Net tipping moment at bearing
    My = abs(M_jib - M_counter) + M_cathead
    
    # Slewing moment (approximate)
    Mz = 0.05 * max(M_jib, M_counter)
    
    # Max stress check
    max_stress = max(
        np.max(jib_result.sigma),
        np.max(counterjib_result.sigma),
        np.max(cathead_result.sigma),
    )
    
    # Max utilization
    max_util = max_stress / 345.0 * 100
    
    return {
        'vertical_load_kN': Fz_total,
        'tipping_moment_kNm': My,
        'slewing_moment_kNm': Mz,
        'max_stress_MPa': max_stress,
        'max_utilization_percent': max_util,
        'bearing_load_kN': Fz_total,
        'bearing_moment_kNm': My,
    }


def print_load_path_summary(load_path: dict):
    """Print formatted load path summary."""
    print("=" * 60)
    print("COMPLETE LOAD PATH")
    print("=" * 60)
    print(f"\n📍 CATHEAD → SLEWING BEARING")
    print(f"   Vertical: {load_path['vertical_load_kN']:.0f} kN")
    print(f"   Tipping Moment: {load_path['tipping_moment_kNm']:.0f} kN·m")
    print(f"   Slewing Moment: {load_path['slewing_moment_kNm']:.0f} kN·m")
    
    print(f"\n🔄 SLEWING BEARING → FOUNDATION")
    print(f"   Vertical: {load_path['bearing_load_kN']:.0f} kN")
    print(f"   Moment: {load_path['bearing_moment_kNm']:.0f} kN·m")
    
    print(f"\n📊 STRESS CHECK")
    print(f"   Max Stress: {load_path['max_stress_MPa']:.0f} MPa")
    print(f"   Max Utilization: {load_path['max_utilization_percent']:.1f}%")
    print("=" * 60)
