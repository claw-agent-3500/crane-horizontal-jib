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
