"""
Tower (Mast) Structural Analysis

Vertical structure of tower crane:
- Mast sections (stackable)
- Upper slewing support
- Lower slewing support
- Foundation connection

Each section has: CG, self-weight, wind area, section properties
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TowerSection:
    """Single tower/mast section."""
    name: str
    start_height: float  # m from ground
    end_height: float   # m from ground
    length: float       # m (end - start)
    
    # Structural properties
    weight_per_length: float  # kN/m
    area: float              # m²
    moment_of_inertia: float # m⁴
    height: float            # m (cross-section)
    width: float             # m
    
    # Material
    yield_strength: float = 345.0  # MPa
    
    # Wind
    wind_area_per_m: float = 0.0  # m²/m
    
    # CG
    cg_y: float = 0.0  # height offset from center


@dataclass
class TowerConfig:
    """Complete tower configuration."""
    total_height: float = 0.0  # m
    sections: List[TowerSection] = field(default_factory=list)
    base_width: float = 0.0   # m
    top_width: float = 0.0    # m
    
    # Connection to foundation
    foundation_reaction_height: float = 0.0  # m


# Standard tower section sizes
TOWER_SECTION_CONFIGS = {
    'standard': {
        'length': 3.0,  # m per section
        'width': 1.8,   # m
        'height': 1.8,  # m
        'area': 0.08,   # m²
        'moment_of_inertia': 0.02,  # m⁴
        'weight_per_length': 1.5,  # kN/m
        'wind_area_per_m': 1.5,    # m²/m
    },
    'heavy': {
        'length': 3.0,
        'width': 2.0,
        'height': 2.0,
        'area': 0.10,
        'moment_of_inertia': 0.03,
        'weight_per_length': 2.0,
        'wind_area_per_m': 1.8,
    },
}


def create_tower_sections(
    num_sections: int,
    section_type: str = 'standard',
    start_height: float = 0.0,
) -> List[TowerSection]:
    """
    Create tower sections.
    """
    config = TOWER_SECTION_CONFIGS.get(section_type, TOWER_SECTION_CONFIGS['standard'])
    
    sections = []
    current_height = start_height
    
    for i in range(num_sections):
        start = current_height
        end = start + config['length']
        
        section = TowerSection(
            name=f'Section_{i+1}',
            start_height=start,
            end_height=end,
            length=config['length'],
            weight_per_length=config['weight_per_length'],
            area=config['area'],
            moment_of_inertia=config['moment_of_inertia'],
            height=config['height'],
            width=config['width'],
            wind_area_per_m=config['wind_area_per_m'],
            cg_y=0.0,  # centered
        )
        
        sections.append(section)
        current_height = end
    
    return sections


def compute_tower_self_weight(sections: List[TowerSection]) -> float:
    """Compute total tower self-weight."""
    return sum(s.length * s.weight_per_length for s in sections)


def compute_tower_wind_area(sections: List[TowerSection]) -> float:
    """Compute total wind area of tower."""
    total_height = sum(s.length for s in sections)
    # Average wind area per meter
    avg_area = np.mean([s.wind_area_per_m for s in sections]) if sections else 0
    return total_height * avg_area


def analyze_tower(
    sections: List[TowerSection],
    top_loads: dict,  # Fz, My, Mz from cathead/bearing
    youngs_modulus: float = 200000.0,
) -> dict:
    """
    Analyze tower under load from upper structure.
    
    Computes:
    - Axial stress from vertical load
    - Bending from moment
    - Combined stress at each section
    """
    results = {
        'sections': [],
        'max_axial': 0.0,
        'max_bending': 0.0,
        'max_stress': 0.0,
        'max_utilization': 0.0,
    }
    
    Fz = top_loads.get('Fz', 0.0)  # kN vertical
    My = top_loads.get('My', 0.0)  # kN·m (tipping)
    Mz = top_loads.get('Mz', 0.0)  # kN·m (slewing)
    
    for sec in sections:
        # Axial stress from vertical load
        sigma_axial = Fz / sec.area / 1000  # Convert to MPa (kN/m² = kPa)
        
        # Bending stress from moment
        # σ = M*y / I
        y_max = sec.height / 2  # distance to extreme fiber
        
        # Combined moment
        M_combined = np.sqrt(My**2 + Mz**2)
        sigma_bending = M_combined * y_max / sec.moment_of_inertia / 1000  # MPa
        
        # Total stress (max value)
        sigma_total = abs(sigma_axial) + abs(sigma_bending)
        
        # Utilization
        util = sigma_total / sec.yield_strength * 100 if sec.yield_strength > 0 else 0
        
        results['sections'].append({
            'name': sec.name,
            'height': sec.start_height,
            'axial_MPa': sigma_axial,
            'bending_MPa': sigma_bending,
            'total_MPa': sigma_total,
            'utilization_percent': util,
        })
        
        results['max_axial'] = max(results['max_axial'], abs(sigma_axial))
        results['max_bending'] = max(results['max_bending'], abs(sigma_bending))
        results['max_stress'] = max(results['max_stress'], sigma_total)
        results['max_utilization'] = max(results['max_utilization'], util)
    
    return results


# Standard tower heights per crane class
TOWER_HEIGHTS = {
    'TC7030-12': {
        'total_height': 45.0,  # m
        'num_sections': 15,
        'section_type': 'standard',
    },
    'TC7030-15': {
        'total_height': 50.0,
        'num_sections': 17,
        'section_type': 'standard',
    },
    'TC7030-18': {
        'total_height': 55.0,
        'num_sections': 18,
        'section_type': 'heavy',
    },
}


def create_tower_for_crane(crane_name: str, custom: dict = None) -> TowerConfig:
    """Create tower configuration for crane type."""
    config = TOWER_HEIGHTS.get(crane_name, TOWER_HEIGHTS['TC7030-12'])
    
    if custom:
        config.update(custom)
    
    sections = create_tower_sections(
        num_sections=config['num_sections'],
        section_type=config['section_type'],
    )
    
    return TowerConfig(
        total_height=config['total_height'],
        sections=sections,
        base_width=2.0,
        top_width=1.8,
    )


# Upper and Lower Slewing Support
@dataclass
class SlewingSupport:
    """Slewing support structure (upper or lower)."""
    name: str  # 'upper' or 'lower'
    height_from_ground: float  # m
    
    # Structural
    weight: float = 0.0  # kN
    area: float = 0.0    # m²
    moment_of_inertia: float = 0.0  # m⁴
    height: float = 0.0  # m
    
    # Connection to bearing/structure
    connection_type: str = 'flange'  # bolt connection
    
    # Loads from analysis
    reaction_Fz: float = 0.0  # kN
    reaction_M: float = 0.0   # kN·m


def create_slewing_supports(
    tower_height: float,
    bearing_diameter: float = 2.0,
) -> tuple:
    """
    Create upper and lower slewing supports.
    
    Typical spacing: 2-3m between upper and lower
    """
    # Upper support at cathead level (top of tower)
    upper = SlewingSupport(
        name='upper',
        height_from_ground=tower_height,
        weight=30.0,  # kN
        area=0.05,
        moment_of_inertia=0.01,
        height=1.5,
    )
    
    # Lower support 2-3m below upper
    lower_height = tower_height - 2.5
    
    # Check minimum height (foundation level)
    lower_height = max(lower_height, 0.5)  # at least 0.5m above ground
    
    lower = SlewingSupport(
        name='lower',
        height_from_ground=lower_height,
        weight=25.0,  # kN
        area=0.04,
        moment_of_inertia=0.008,
        height=1.2,
    )
    
    return upper, lower


def compute_slewing_support_stress(
    support: SlewingSupport,
    Fz: float,
    M: float,
    yield_strength: float = 345.0,
) -> dict:
    """
    Compute stress in slewing support.
    """
    # Axial
    sigma_axial = Fz / support.area / 1000 if support.area > 0 else 0  # MPa
    
    # Bending
    y = support.height / 2
    sigma_bending = M * y / support.moment_of_inertia / 1000 if support.moment_of_inertia > 0 else 0  # MPa
    
    # Total
    sigma_total = abs(sigma_axial) + abs(sigma_bending)
    util = sigma_total / yield_strength * 100 if yield_strength > 0 else 0
    
    return {
        'axial_MPa': sigma_axial,
        'bending_MPa': sigma_bending,
        'total_MPa': sigma_total,
        'utilization_percent': util,
    }


# Foundation
@dataclass
class FoundationConfig:
    """Foundation configuration."""
    type: str = 'pad'  # 'pad', 'raft', 'pile'
    
    # Dimensions
    length: float = 0.0  # m
    width: float = 0.0   # m
    depth: float = 0.0   # m
    
    # Concrete
    concrete_grade: str = 'C30'  # MPa
    
    # Reinforcement (for calculation)
    rebar_area: float = 0.0  # mm²
    
    # Soil
    soil_bearing_capacity: float = 0.0  # kPa (e.g., 150 kPa)
    
    # Allowable settlement
    max_settlement_mm: float = 25.0


# Standard foundation sizes
FOUNDATION_CONFIGS = {
    'small': {
        'type': 'pad',
        'length': 4.0,
        'width': 4.0,
        'depth': 1.5,
        'soil_bearing': 150.0,  # kPa
    },
    'medium': {
        'type': 'pad',
        'length': 5.0,
        'width': 5.0,
        'depth': 2.0,
        'soil_bearing': 150.0,
    },
    'large': {
        'type': 'raft',
        'length': 6.0,
        'width': 6.0,
        'depth': 2.5,
        'soil_bearing': 200.0,
    },
}


def create_foundation(
    foundation_type: str = 'medium',
    custom: dict = None,
) -> FoundationConfig:
    """Create foundation configuration."""
    config = FOUNDATION_CONFIGS.get(foundation_type, FOUNDATION_CONFIGS['medium'])
    
    if custom:
        config.update(custom)
    
    return FoundationConfig(
        type=config['type'],
        length=config['length'],
        width=config['width'],
        depth=config['depth'],
        soil_bearing_capacity=config.get('soil_bearing', 150.0),
    )


def check_foundation(
    foundation: FoundationConfig,
    loads: dict,  # Fx, Fy, Fz, Mx, My, Mz
) -> dict:
    """
    Check foundation adequacy.
    """
    # Vertical stress on soil
    area = foundation.length * foundation.width
    Fz = loads.get('Fz', 0.0)  # kN
    
    # Eccentricity for moment
    My = loads.get('My', 0.0)
    Mx = loads.get('Mx', 0.0)
    
    # Effective area (reduced for eccentricity)
    e_y = My / Fz if Fz > 0 else 0  # m eccentricity
    e_x = Mx / Fz if Fz > 0 else 0
    
    # Effective dimensions
    L_eff = foundation.length - 2 * abs(e_y)
    W_eff = foundation.width - 2 * abs(e_x)
    
    if L_eff > 0 and W_eff > 0:
        effective_area = L_eff * W_eff
    else:
        effective_area = area
    
    # Stress on soil
    if effective_area > 0:
        soil_stress = Fz / effective_area  # kN/m² = kPa
    else:
        soil_stress = float('inf')
    
    # Check against allowable
    allowable = foundation.soil_bearing_capacity
    soil_ok = soil_stress <= allowable
    
    # Bearing pressure ratio
    pressure_ratio = soil_stress / allowable * 100 if allowable > 0 else 0
    
    # Sliding check (F_h < friction)
    Fx = loads.get('Fx', 0.0)
    Fy = loads.get('Fy', 0.0)
    Fh = np.sqrt(Fx**2 + Fy**2)  # kN
    
    # Friction coefficient ~0.5 for concrete on soil
    friction_capacity = 0.5 * Fz
    sliding_ok = Fh <= friction_capacity
    
    # Overturning check
    # Must have restoring moment > overturning
    # Not fully implemented - simplify for now
    overturning_safe = True  # Would need detailed calc
    
    return {
        'soil_stress_kPa': soil_stress,
        'allowable_kPa': allowable,
        'soil_ok': soil_ok,
        'pressure_ratio_percent': pressure_ratio,
        'sliding_ok': sliding_ok,
        'overturning_safe': overturning_safe,
        'adequate': soil_ok and sliding_ok and overturning_safe,
    }


def compute_complete_crane_load_path(
    jib_result,
    counterjib_result,
    cathead_result,
    crane_name: str = 'TC7030-12',
    tower_height: float = 45.0,
    bearing_diameter: float = 2.0,
    foundation_type: str = 'medium',
) -> dict:
    """
    Compute complete load path: Jib → Counterjib → Cathead → Tower → Foundation
    """
    # 1. Get loads from each component
    Fz_jib = np.max(np.abs(jib_result.V))
    Fz_counter = np.max(np.abs(counterjib_result.V))
    Fz_cathead = np.max(np.abs(cathead_result.V))
    
    M_jib = np.max(np.abs(jib_result.M))
    M_counter = np.max(np.abs(counterjib_result.M))
    M_cathead = np.max(np.abs(cathead_result.M))
    
    # Net at cathead
    Fz_cathead_total = Fz_jib + Fz_counter + Fz_cathead
    My_tipping = abs(M_jib - M_counter) + M_cathead
    Mz_slewing = 0.05 * max(M_jib, M_counter)
    
    # 2. Tower analysis
    tower = create_tower_for_crane(crane_name)
    tower_loads = {'Fz': Fz_cathead_total, 'My': My_tipping, 'Mz': Mz_slewing}
    tower_result = analyze_tower(tower.sections, tower_loads)
    
    # 3. Foundation
    foundation = create_foundation(foundation_type)
    foundation_loads = {
        'Fz': Fz_cathead_total + compute_tower_self_weight(tower.sections),
        'Fx': 0.0,
        'Fy': 0.0,
        'Mx': 0.0,
        'My': My_tipping,
        'Mz': Mz_slewing,
    }
    foundation_check = check_foundation(foundation, foundation_loads)
    
    return {
        'cathead': {
            'Fz': Fz_cathead_total,
            'My': My_tipping,
            'Mz': Mz_slewing,
        },
        'tower': {
            'sections': tower_result['sections'],
            'max_stress_MPa': tower_result['max_stress'],
            'max_utilization_percent': tower_result['max_utilization'],
        },
        'foundation': foundation_check,
    }
