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
