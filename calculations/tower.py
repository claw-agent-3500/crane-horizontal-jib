"""
Tower (Mast) Structural Analysis - Correct Load Accumulation

Key concept:
- Fz = sum of all weights of parts above
- My = (My_jib - My_counterjib) with OPPOSITE signs + wind moments + eccentric moments
- Fx = sum of all Fx from parts above
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TowerSection:
    """Single tower/mast section."""
    name: str
    start_height: float
    end_height: float
    length: float
    weight_per_length: float
    area: float
    moment_of_inertia: float
    height: float
    width: float
    yield_strength: float = 345.0
    wind_area_per_m: float = 1.5


@dataclass
class CranePartLoad:
    """Load contribution from a single crane part."""
    name: str
    weight_kN: float
    cg_height: float  # m from ground
    wind_area_m2: float = 0.0
    moment_My: float = 0.0  # kN·m
    moment_Mz: float = 0.0
    moment_Mx: float = 0.0
    Fx_kN: float = 0.0


def compute_cumulative_loads(
    parts: List[CranePartLoad],
    at_height: float,
) -> dict:
    """Compute cumulative loads at a given height from all parts above."""
    above = [p for p in parts if p.cg_height > at_height]
    
    Fz = sum(p.weight_kN for p in above)
    My = sum(p.moment_My for p in above)
    Mz = sum(p.moment_Mz for p in above)
    Mx = sum(p.moment_Mx for p in above)
    Fx = sum(p.Fx_kN for p in above)
    
    return {'Fz': Fz, 'My': My, 'Mz': Mz, 'Mx': Mx, 'Fx': Fx}


def analyze_tower(
    parts: List[CranePartLoad],
    sections: List[TowerSection],
    wind_pressure: float = 0.0,
) -> dict:
    """Analyze tower with cumulative loads."""
    results = []
    
    for sec in sections:
        h_mid = (sec.start_height + sec.end_height) / 2
        
        # Get cumulative loads at this height
        loads = compute_cumulative_loads(parts, h_mid)
        
        # Add this section's weight
        sec_weight = sec.weight_per_length * sec.length
        loads['Fz'] += sec_weight
        
        # Stress
        sigma_a = loads['Fz'] / sec.area / 1000 if sec.area > 0 else 0
        
        M_total = np.sqrt(loads['My']**2 + loads['Mz']**2)
        y = sec.height / 2
        sigma_b = M_total * y / sec.moment_of_inertia / 1000 if sec.moment_of_inertia > 0 else 0
        
        sigma = abs(sigma_a) + abs(sigma_b)
        util = sigma / sec.yield_strength * 100
        
        results.append({
            'section': sec.name,
            'height': sec.start_height,
            'Fz': loads['Fz'],
            'My': loads['My'],
            'sigma': sigma,
            'util': util,
        })
    
    return {
        'sections': results,
        'max_util': max(r['util'] for r in results) if results else 0,
    }


# Standard tower
def create_tower_sections(n: int, start: float = 0.0) -> List[TowerSection]:
    return [
        TowerSection(
            name=f'S{i+1}', start_height=start + i*3, end_height=start + (i+1)*3,
            length=3, weight_per_length=1.5, area=0.08, moment_of_inertia=0.02,
            height=1.8, width=1.8, yield_strength=345.0
        ) for i in range(n)
    ]


def compute_mast_sfd_bmd(
    parts: List[CranePartLoad],
    sections: List[TowerSection],
    wind_pressure: float = 0.0,
) -> dict:
    """
    Compute SFD and BMD along mast (cantilever from foundation).
    
    The mast is fixed at ground (foundation) and loads act from above.
    """
    n_points = len(sections)
    
    # Heights at each section top
    heights = [s.end_height for s in sections]
    
    # Initialize arrays
    shear = np.zeros(n_points)
    moment = np.zeros(n_points)
    
    # Calculate from top to bottom (like cantilever load)
    # At each height, shear = sum of horizontal forces above
    # Moment = sum of (horizontal force × distance from point)
    
    for i, h in enumerate(heights):
        # Get cumulative loads at this height
        loads = compute_cumulative_loads(parts, h)
        
        # Shear = Fx (horizontal force)
        shear[i] = loads['Fx']
        
        # Moment = My (tipping moment from above)
        moment[i] = loads['My']
    
    return {
        'heights': heights,
        'shear_kN': shear,
        'moment_kNm': moment,
    }


def plot_mast_sfd_bmd(mast_results: dict) -> str:
    """Generate SFD and BMD for mast."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    fig.patch.set_facecolor('#1e1e2e')
    
    h = mast_results['heights']
    V = mast_results['shear_kN']
    M = mast_results['moment_kNm']
    
    # SFD
    ax1.set_facecolor('#1e1e2e')
    ax1.plot(V, h, 'b-', linewidth=2)
    ax1.fill_betweenx(h, V, alpha=0.3, color='blue')
    ax1.set_xlabel('Shear V (kN)', color='#aaa')
    ax1.set_ylabel('Height (m)', color='#aaa')
    ax1.set_title('Shear Force Diagram - Mast', color='#fff')
    ax1.grid(True, alpha=0.2, color='#555')
    
    # BMD
    ax2.set_facecolor('#1e1e2e')
    ax2.plot(M, h, 'r-', linewidth=2)
    ax2.fill_betweenx(h, M, alpha=0.3, color='red')
    ax2.set_xlabel('Moment M (kN·m)', color='#aaa')
    ax2.set_ylabel('Height (m)', color='#aaa')
    ax2.set_title('Bending Moment Diagram - Mast', color='#fff')
    ax2.grid(True, alpha=0.2, color='#555')
    
    for ax in (ax1, ax2):
        ax.tick_params(colors='#888')
        for spine in ax.spines.values():
            spine.set_color('#555')
    
    buf = plt.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#1e1e2e')
    buf.seek(0)
    import base64
    return base64.b64encode(buf.read()).decode()


def compute_mast_deflection(
    parts: List[CranePartLoad],
    sections: List[TowerSection],
    E: float = 200000.0,  # MPa (Young's modulus)
    wind_pressure: float = 0.0,  # Pa
) -> dict:
    """
    Compute deflection along mast with distributed and point loads.
    
    Loads:
    - Distributed: wind pressure on mast sections
    - Point: loads from upper structure at cathead level
    """
    n = len(sections)
    heights = np.array([s.end_height for s in sections])
    delta = np.zeros(n)
    
    # Average section properties
    I_avg = np.mean([s.moment_of_inertia for s in sections])
    
    # Convert I from m⁴ to mm⁴ for MPa units
    I_mm4 = I_avg * 1e12
    
    for i in range(n):
        h = heights[i]
        
        # 1. Point load moment from upper structure (at cathead level ~45m)
        # This causes tip deflection at the top, but we calculate at each height
        # For a cantilever, deflection at point x due to moment at end:
        # δ = M * x² / (2EI) for point moment at end
        
        point_load_M = sum(p.moment_My for p in parts if p.cg_height > h)
        
        # Deflection from point moment at cathead
        if h > 0 and I_mm4 > 0:
            x = h  # distance from base
            delta_point = (point_load_M * 1000 * x**2) / (2 * E * I_mm4)  # mm
        else:
            delta_point = 0
        
        # 2. Distributed wind load
        # q = wind pressure × area per meter
        q_total = 0
        for sec in sections:
            q_total += sec.wind_area_per_m * sec.length
        q_avg = q_total / sum(s.length for s in sections)  # m²/m
        
        wind_load = wind_pressure * q_avg / 1000 if wind_pressure > 0 else 0  # kN/m
        
        # Deflection from distributed load (cantilever):
        # δ = q * x⁴ / (8EI)
        if h > 0 and I_mm4 > 0:
            delta_wind = (wind_load * 1000 * h**4) / (8 * E * I_mm4)  # mm
        else:
            delta_wind = 0
        
        delta[i] = delta_point + delta_wind
    
    # Serviceability check
    max_deflection = np.max(np.abs(delta))
    L = sections[-1].end_height if sections else 45
    limit = L / 250  # typical limit
    
    return {
        'heights': heights.tolist(),
        'deflection_mm': delta.tolist(),
        'max_deflection_mm': max_deflection,
        'serviceability_limit': f'L/250 = {limit:.0f}mm',
        'passes': max_deflection < limit,
    }


def compute_mast_deflection_v2(
    parts: List[CranePartLoad],
    sections: List[TowerSection],
    E: float = 200000.0,  # MPa
) -> dict:
    """
    Compute mast deflection - corrected formula.
    
    δ = M * x² / (2EI) for point moment at end of cantilever
    """
    results = []
    
    # Use average I
    I_avg = sum(s.moment_of_inertia for s in sections) / len(sections)
    I_mm4 = I_avg * 1e12
    
    for sec in sections:
        h = sec.end_height
        
        # Sum of moments from parts above this height
        M_total = sum(p.moment_My for p in parts if p.cg_height > h)
        
        if h > 0 and I_mm4 > 0:
            delta_mm = (M_total * 1000 * (h*1000)**2) / (2 * E * I_mm4)
        else:
            delta_mm = 0
        
        results.append({
            'height': h,
            'moment_kNm': M_total,
            'deflection_mm': delta_mm,
        })
    
    max_delta = max(r['deflection_mm'] for r in results)
    L = sections[-1].end_height if sections else 45
    limit = L / 250 * 1000  # mm
    
    return {
        'results': results,
        'max_deflection_mm': max_delta,
        'limit_mm': limit,
        'passes': max_delta < limit,
    }


def compute_mast_fatigue(
    tower_result: dict,
    cycles_per_year: int = 20000,
    detail_category: str = 'D',  # Welded steel detail category
) -> dict:
    """
    Compute fatigue damage for mast structure.
    
    For tower crane mast:
    - Main chords (vertical): stress range from axial + bending
    - Diagonal chords: stress range from shear + torsion
    - Connections: stress concentration at welds
    
    Args:
        tower_result: Result from analyze_tower()
        cycles_per_year: Estimated load cycles per year
        detail_category: 'D' typical for welded steel (log_a=17, m=5)
    
    Returns:
        Fatigue damage results
    """
    # S-N curve parameters (detail category)
    log_a_map = {'A': 18.0, 'B': 17.0, 'C': 16.0, 'D': 15.0, 'E': 14.0, 'F': 13.0}
    log_a = log_a_map.get(detail_category, 15.0)
    m = 5.0  # Slope
    
    results = []
    
    for sec in tower_result['sections']:
        # Stress range = max stress - min stress (assuming min = 0 for simplicity)
        sigma_max = sec['sigma']
        delta_sigma = sigma_max  # Assuming tension-compression cycle
        
        # Allowable cycles at this stress range
        if delta_sigma > 0:
            log_N = (np.log10(delta_sigma) * m - log_a) / m
            N_allow = 10 ** log_N if log_N > 0 else float('inf')
        else:
            N_allow = float('inf')
        
        # Damage ratio
        if N_allow == float('inf') or N_allow <= 0:
            damage = 0.0
        else:
            damage = cycles_per_year / N_allow
        
        # Safe life
        safe_life = 1.0 / damage if damage > 0 else float('inf')
        
        results.append({
            'section': sec['section'],
            'height': sec['height'],
            'stress_range_MPa': delta_sigma,
            'cycles_per_year': cycles_per_year,
            'N_allowable': N_allow,
            'damage': damage,
            'safe_life_years': safe_life,
        })
    
    max_damage = max(r['damage'] for r in results) if results else 0
    min_life = min(r['safe_life_years'] for r in results) if results else float('inf')
    
    return {
        'sections': results,
        'max_damage': max_damage,
        'min_safe_life_years': min_life,
        'failed': max_damage > 1.0,
    }


def compute_diagonal_fatigue(
    tower_sections: list,
    diagonal_force_range: float,  # kN range for diagonals
) -> dict:
    """
    Compute fatigue for diagonal members.
    
    Diagonals see alternating compression/tension from wind/loading cycles.
    """
    # Simplified: assume diagonal stress proportional to force
    A_diagonal = 0.005  # m² average diagonal area
    sigma_range = (diagonal_force_range * 1000) / (A_diagonal * 1e6)  # MPa
    
    # Same S-N curve approach
    log_a = 15.0  # Detail category D
    m = 5.0
    
    cycles_per_year = 20000
    
    if sigma_range > 0:
        log_N = (np.log10(sigma_range) * m - log_a) / m
        N_allow = 10 ** log_N if log_N > 0 else float('inf')
    else:
        N_allow = float('inf')
    
    damage = cycles_per_year / N_allow if N_allow > 0 else 0
    safe_life = 1.0 / damage if damage > 0 else float('inf')
    
    return {
        'diagonal_stress_range_MPa': sigma_range,
        'damage': damage,
        'safe_life_years': safe_life,
    }


def compute_slewing_fatigue(
    jib_moment_kNm: float = 10981,
    section_modulus: float = 0.022,
    slewing_cycles_per_year: int = 10000,
    wind_cycles_per_year: int = 5000,
) -> dict:
    """Compute fatigue from slewing rotation."""
    # Convert moment to stress
    M_Nm = jib_moment_kNm * 1000
    sigma_max = (M_Nm / section_modulus) / 1e6
    sigma_min = -sigma_max
    
    delta_sigma = abs(sigma_max - sigma_min)
    
    log_a = 15.0
    m = 5.0
    
    total_cycles = slewing_cycles_per_year + wind_cycles_per_year
    
    if delta_sigma > 0:
        log_N = (np.log10(delta_sigma) * m - log_a) / m
        N_allow = 10 ** log_N if log_N > 0 else float('inf')
    else:
        N_allow = float('inf')
    
    damage = total_cycles / N_allow if N_allow > 0 else 0
    safe_life = 1.0 / damage if damage > 0 else float('inf')
    
    return {
        'stress_range_MPa': delta_sigma,
        'total_cycles': total_cycles,
        'N_allowable': N_allow,
        'damage': damage,
        'safe_life_years': safe_life,
    }



def compute_slewing_fatigue_by_condition(
    jib_moment_kNm: float,
    section_modulus: float = 0.022,
    condition: str = 'in_service',  # 'in_service', 'working', 'storm', 'survival'
) -> dict:
    """
    Compute slewing fatigue for different service conditions.
    
    Conditions:
    - in_service: Normal operation, 10000 slewing cycles/year
    - working: Heavy use, 20000 cycles/year  
    - storm: High wind, reduced cycles but higher moment
    - survival: Extreme, 0 cycles but max stress
    
    Returns fatigue results for each condition.
    """
    conditions = {
        'in_service': {
            'name': 'In Service (Normal)',
            'slewing_cycles': 10000,
            'wind_cycles': 5000,
            'moment_factor': 1.0,
        },
        'working': {
            'name': 'Heavy Working',
            'slewing_cycles': 20000,
            'wind_cycles': 10000,
            'moment_factor': 1.2,
        },
        'storm': {
            'name': 'Storm Condition',
            'slewing_cycles': 1000,
            'wind_cycles': 500,
            'moment_factor': 1.5,  # higher due to wind
        },
        'survival': {
            'name': 'Survival (No slewing)',
            'slewing_cycles': 0,
            'wind_cycles': 50,
            'moment_factor': 2.0,  # max wind
        },
    }
    
    cfg = conditions.get(condition, conditions['in_service'])
    
    # Adjust moment based on condition
    M_effective = jib_moment_kNm * cfg['moment_factor']
    
    # Compute stress
    M_Nm = M_effective * 1000
    sigma_max = (M_Nm / section_modulus) / 1e6
    sigma_min = -sigma_max
    delta_sigma = abs(sigma_max - sigma_min)
    
    # S-N curve
    log_a = 15.0
    m = 5.0
    
    total_cycles = cfg['slewing_cycles'] + cfg['wind_cycles']
    
    if delta_sigma > 0 and total_cycles > 0:
        log_N = (np.log10(delta_sigma) * m - log_a) / m
        N_allow = 10 ** log_N if log_N > 0 else float('inf')
    else:
        N_allow = float('inf')
    
    damage = total_cycles / N_allow if N_allow > 0 else 0
    safe_life = 1.0 / damage if damage > 0 else float('inf')
    
    return {
        'condition': cfg['name'],
        'slewing_cycles': cfg['slewing_cycles'],
        'wind_cycles': cfg['wind_cycles'],
        'moment_factor': cfg['moment_factor'],
        'stress_range_MPa': delta_sigma,
        'total_cycles': total_cycles,
        'N_allowable': N_allow,
        'damage': damage,
        'safe_life_years': safe_life,
    }


def compute_all_condition_fatigue(jib_moment_kNm: float) -> dict:
    """Compute fatigue for all service conditions."""
    results = {}
    for condition in ['in_service', 'working', 'storm', 'survival']:
        results[condition] = compute_slewing_fatigue_by_condition(
            jib_moment_kNm, condition=condition
        )
    return results
