"""
Cathead (Turntable/Slewing Assembly) Structural Analysis

Load transfer path:
  Jib + Counterjib → Cathead (apex) → Slewing bearing → Tower → Foundation

Forces transferred:
  - Fz: Vertical (gravity, payload)
  - Fx: Horizontal along jib axis
  - Fy: Horizontal perpendicular (wind)
  - Mz: Torque around vertical (slewing moment)
  - My: Moment around horizontal (tipping)
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class CatheadLoads:
    """Loads transferred through cathead to slewing bearing."""
    # Forces
    Fx: float = 0.0  # kN - along jib direction
    Fy: float = 0.0  # kN - perpendicular to jib
    Fz: float = 0.0  # kN - vertical
    
    # Moments
    Mx: float = 0.0  # kN·m - around jib axis
    My: float = 0.0  # kN·m - tipping moment
    Mz: float = 0.0  # kN·m - slewing torque
    
    # Location
    cathead_height: float = 0.0  # m - height above tower


@dataclass
class SlewingBearingLoads:
    """Loads on slewing bearing."""
    # Total reactions
    Fz_total: float = 0.0  # kN - total vertical
    Fx_total: float = 0.0  # kN - horizontal
    Fy_total: float = 0.0  # kN - perpendicular
    
    # Moment about bearing center
    Mx_total: float = 0.0  # kN·m
    My_total: float = 0.0  # kN·m
    Mz_total: float = 0.0  # kN·m
    
    # Bearing geometry
    bearing_diameter: float = 0.0  # m
    bolt_circle_diameter: float = 0.0  # m
    
    # Max bolt load (for check)
    max_bolt_load: float = 0.0  # kN


def compute_cathead_from_jib_counterjib(
    jib_result,
    counterjib_result,
    jib_length: float,
    counterjib_length: float,
    cathead_height: float = 0.0,
    jib_elev_angle: float = 0.0,  # degrees, jib elevation
) -> CatheadLoads:
    """
    Compute loads at cathead from jib and counterjib analysis.
    
    The cathead is at the pivot point where jib and counterjib meet.
    """
    # Get reaction forces at root (cathead connection)
    # For jib: moment at root = reaction moment
    M_jib = np.max(np.abs(jib_result.M)) if hasattr(jib_result, 'M') else 0
    
    # For counterjib: moment at root
    M_counter = np.max(np.abs(counterjib_result.M)) if hasattr(counterjib_result, 'M') else 0
    
    # Shear forces
    V_jib = np.max(np.abs(jib_result.V)) if hasattr(jib_result, 'V') else 0
    V_counter = np.max(np.abs(counterjib_result.V)) if hasattr(counterjib_result, 'V') else 0
    
    # Vertical forces (self-weight + payload)
    Fz_jib = V_jib  # Approx vertical reaction
    Fz_counter = V_counter
    
    # Total vertical = sum of both arms
    Fz_total = Fz_jib + Fz_counter
    
    # Tipping moment = sum of moments from both arms
    # Jib creates moment in one direction, counterjib in opposite
    # Net My depends on which is larger
    My = abs(M_jib - M_counter)  # kN·m
    
    # Slewing moment Mz - from eccentric loads during rotation
    # Approx as 5% of max moment for now
    Mz = 0.05 * max(M_jib, M_counter)  # kN·m
    
    # Horizontal forces from wind
    Fx = 0.0  # Along jib - from wind on jib
    Fy = 0.0  # Perpendicular - wind on sides
    
    # Axial moment (around jib axis) - from trolley position
    Mx = 0.0
    
    return CatheadLoads(
        Fx=Fx,
        Fy=Fy,
        Fz=Fz_total,
        Mx=Mx,
        My=My,
        Mz=Mz,
        cathead_height=cathead_height,
    )


def compute_slewing_bearing_reactions(
    cathead: CatheadLoads,
    tower_height: float,
    bearing_diameter: float = 2.0,  # m typical
) -> SlewingBearingLoads:
    """
    Compute reactions at slewing bearing from cathead loads.
    
    The slewing bearing connects upper (rotating) to lower (stationary) structure.
    """
    # Total vertical force
    Fz = cathead.Fz
    
    # Horizontal forces transferred to bearing
    Fx = cathead.Fx
    Fy = cathead.Fy
    
    # Moments about bearing center
    # My (tipping) creates vertical reaction differential
    # Mz (slewing) creates horizontal reaction differential
    
    Mx = cathead.Mx
    My = cathead.My
    Mz = cathead.Mz
    
    # Bolt circle diameter (typically 0.8 × bearing diameter)
    bolt_circle = 0.8 * bearing_diameter
    
    # Max bolt load calculation (simplified)
    # For tipping moment My: max bolt load = My / (bolt_circle × n_bolts)
    # Assuming 24 bolts on circle
    n_bolts = 24
    if bolt_circle > 0:
        max_bolt = My / (bolt_circle * n_bolts) if My > 0 else 0
        # Add safety factor
        max_bolt *= 1.5
    else:
        max_bolt = 0
    
    return SlewingBearingLoads(
        Fz_total=Fz,
        Fx_total=Fx,
        Fy_total=Fy,
        Mx_total=Mx,
        My_total=My,
        Mz_total=Mz,
        bearing_diameter=bearing_diameter,
        bolt_circle_diameter=bolt_circle,
        max_bolt_load=max_bolt,
    )


def compute_tower_base_reactions(
    bearing_reactions: SlewingBearingLoads,
    tower_height: float,
    tower_self_weight: float = 0.0,  # kN
) -> dict:
    """
    Compute reactions at tower base / foundation.
    
    Loads transfer through tower to foundation.
    """
    # Vertical at base = bearing vertical + tower self-weight
    Fz_base = bearing_reactions.Fz_total + tower_self_weight
    
    # Horizontal at base = bearing horizontals
    Fx_base = bearing_reactions.Fx_total
    Fy_base = bearing_reactions.Fy_total
    
    # Moments at base = bearing moments + horizontal × tower height
    Mx_base = bearing_reactions.Mx_total + bearing_reactions.Fy_total * tower_height
    My_base = bearing_reactions.My_total + bearing_reactions.Fx_total * tower_height
    Mz_base = bearing_reactions.Mz_total
    
    return {
        'Fx': Fx_base,  # kN
        'Fy': Fy_base,  # kN
        'Fz': Fz_base,  # kN
        'Mx': Mx_base,  # kN·m
        'My': My_base,  # kN·m
        'Mz': Mz_base,  # kN·m
    }


def analyze_full_load_path(
    jib_result,
    counterjib_result,
    jib_length: float,
    counterjib_length: float,
    tower_height: float = 30.0,
    bearing_diameter: float = 2.0,
    cathead_height: float = 0.0,
    tower_weight: float = 0.0,
) -> dict:
    """
    Complete load path analysis: Jib → Cathead → Bearing → Tower → Foundation
    """
    # Step 1: Cathead loads
    cathead = compute_cathead_from_jib_counterjib(
        jib_result, counterjib_result,
        jib_length, counterjib_length,
        cathead_height,
    )
    
    # Step 2: Slewing bearing reactions
    bearing = compute_slewing_bearing_reactions(cathead, tower_height, bearing_diameter)
    
    # Step 3: Tower base / foundation reactions
    foundation = compute_tower_base_reactions(bearing, tower_height, tower_weight)
    
    return {
        'cathead': cathead,
        'bearing': bearing,
        'foundation': foundation,
    }
