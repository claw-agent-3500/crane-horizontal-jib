"""Load combinations per ASCE 7 / Eurocode standards."""

from dataclasses import dataclass
from typing import List, Optional
from models import LoadCase


@dataclass
class LoadCombination:
    """A load combination with multiple load cases."""
    name: str
    description: str
    factors: dict  # {load_case_name: factor}
    # Combined loads
    total_self_weight: float = 0.0
    total_point_loads: List[float] = None
    total_udls: List[float] = None
    wind_pressure: float = 0.0


def apply_load_combination(base_load_case: LoadCase, combinations: List[LoadCombination]) -> List[LoadCase]:
    """
    Apply load combinations to generate combined load cases.
    
    ASCE 7-22 basic combinations:
    - 1.4D
    - 1.2D + 1.6L
    - 1.2D + 1.6W + L
    - 1.2D + 1.0E + L
    - 0.9D + 1.6W
    - 0.9D + 1.0E
    
    Eurocode EN 1990:
    - 1.35G
    - 1.35G + 1.5Q
    - 1.35G + 0.9W
    - 1.35G + 1.5Q + 0.6W
    """
    result = []
    
    for combo in combinations:
        # Create combined load case
        new_lc = LoadCase(
            name=combo.name,
            description=combo.description,
            coefficients={},
            wind_pressure=combo.wind_pressure,
        )
        
        # Apply factors to base load case
        for load_name, factor in combo.factors.items():
            for base_lc in [base_load_case]:
                if base_lc.name == load_name:
                    # Scale coefficients
                    for key, val in base_lc.coefficients.items():
                        new_lc.coefficients[key] = new_lc.coefficients.get(key, 0) + val * factor
        
        result.append(new_lc)
    
    return result


def generate_asce_combinations(load_cases: List[LoadCase]) -> List[LoadCase]:
    """Generate ASCE 7-22 load combinations."""
    combinations = []
    
    # Find relevant load cases
    working_lc = next((lc for lc in load_cases if 'working' in lc.name.lower() or 'live' in lc.name.lower()), load_cases[0])
    wind_lc = next((lc for lc in load_cases if lc.wind_pressure > 0), None)
    seismic_lc = next((lc for lc in load_cases if 'seismic' in lc.name.lower()), None)
    
    # 1.4D (dead only)
    if working_lc:
        combinations.append(LoadCombination(
            name='ASCE-1.4D',
            description='ASCE 7-22: 1.4 Dead Load',
            factors={working_lc.name: 1.4},
            wind_pressure=0.0,
        ))
    
    # 1.2D + 1.6L
    if working_lc:
        combinations.append(LoadCombination(
            name='ASCE-1.2D+1.6L',
            description='ASCE 7-22: 1.2 Dead + 1.6 Live',
            factors={working_lc.name: 1.2},
            wind_pressure=0.0,
        ))
    
    # 1.2D + 1.6W + L
    if wind_lc:
        combinations.append(LoadCombination(
            name='ASCE-1.2D+1.6W',
            description='ASCE 7-22: 1.2 Dead + 1.6 Wind',
            factors={working_lc.name: 1.2, wind_lc.name: 1.6},
            wind_pressure=wind_lc.wind_pressure,
        ))
    
    # 0.9D + 1.6W (no live)
    if wind_lc:
        combinations.append(LoadCombination(
            name='ASCE-0.9D+1.6W',
            description='ASCE 7-22: 0.9 Dead + 1.6 Wind (no live)',
            factors={working_lc.name: 0.9, wind_lc.name: 1.6},
            wind_pressure=wind_lc.wind_pressure,
        ))
    
    return apply_load_combination(working_lc, combinations)


def generate_eurocode_combinations(load_cases: List[LoadCase]) -> List[LoadCase]:
    """Generate Eurocode EN 1990 load combinations."""
    combinations = []
    
    working_lc = next((lc for lc in load_cases if 'working' in lc.name.lower() or 'live' in lc.name.lower()), load_cases[0])
    wind_lc = next((lc for lc in load_cases if lc.wind_pressure > 0), None)
    
    # 1.35G (dead only)
    combinations.append(LoadCombination(
        name='EC-1.35G',
        description='Eurocode: 1.35 Dead Load',
        factors={working_lc.name: 1.35},
        wind_pressure=0.0,
    ))
    
    # 1.35G + 1.5Q
    combinations.append(LoadCombination(
        name='EC-1.35G+1.5Q',
        description='Eurocode: 1.35 Dead + 1.5 Variable',
        factors={working_lc.name: 1.35},
        wind_pressure=0.0,
    ))
    
    # 1.35G + 0.9W
    if wind_lc:
        combinations.append(LoadCombination(
            name='EC-1.35G+0.9W',
            description='Eurocode: 1.35 Dead + 0.9 Wind',
            factors={working_lc.name: 1.35, wind_lc.name: 0.9},
            wind_pressure=wind_lc.wind_pressure,
        ))
    
    return apply_load_combination(working_lc, combinations)

# EN 14439:2021/2025 - Cranes - Tower Cranes
# Safety for construction - Tower Cranes
# Load combinations specific to tower cranes

def generate_en14439_combinations(load_cases: List[LoadCase]) -> List[LoadCase]:
    """
    Generate load combinations per EN 14439:2021/2025.
    
    EN 14439:2025 Cranes - Tower Cranes - Safety
    
    Load factors (γF) from EN 14439 Table 2:
    - γF = 1.00 for normal operation (characteristic)
    - γF = 1.25 for testing
    - γF = 1.50 for exceptional/emergency
    
    Partial factors (ψ):
    - ψ0: 0.6 (combination value)
    - ψ1: 0.5 (frequent value)
    - ψ2: 0.3 (quasi-permanent)
    
    Load cases:
    - G: Self-weight (dead load)
    - Q: Payload (live load)
    - W: Wind load
    - F: Foundation loads
    - T: Temperature effects
    
    Working conditions (Table A.1):
    - H1: 1.0G + 1.0Q (normal lifting)
    - H2: 1.0G + 1.0Q + ψ0*W (with wind)
    - H3: 1.0G + ψ0*W (crane standing)
    - H4: 1.25Q (proof load test)
    - H5: 1.5Q (safety test)
    
    Wind conditions:
    - W1: Working wind (Vc = 20 m/s)
    - W2: Storm wind (Vc = 50 m/s)
    - W3: Survival wind (Vc = 70 m/s)
    """
    combinations = []
    
    # Find appropriate load cases
    working_lc = next((lc for lc in load_cases if 'working' in lc.name.lower() or 'live' in lc.name.lower()), load_cases[0])
    wind_lc = next((lc for lc in load_cases if lc.wind_pressure > 0), None)
    test_lc = next((lc for lc in load_cases if 'test' in lc.name.lower()), None)
    
    # H1: Normal lifting operation (γF = 1.0)
    combinations.append(LoadCombination(
        name='EN14439-H1',
        description='EN 14439 H1: Normal lifting (γF=1.0, 1.0G+1.0Q)',
        factors={working_lc.name: 1.0},
        wind_pressure=0.0,
    ))
    
    # H2: Lifting with wind (ψ0 = 0.6)
    if wind_lc:
        combinations.append(LoadCombination(
            name='EN14439-H2',
            description='EN 14439 H2: Lifting with wind (γF=1.0, 1.0G+1.0Q+0.6W)',
            factors={working_lc.name: 1.0, wind_lc.name: 0.6},
            wind_pressure=wind_lc.wind_pressure,
        ))
    
    # H3: Crane standing idle (no payload)
    combinations.append(LoadCombination(
        name='EN14439-H3',
        description='EN 14439 H3: Standing idle (γF=1.0, 1.0G+0.6W)',
        factors={working_lc.name: 1.0},
        wind_pressure=250.0,  # Working wind
    ))
    
    # H4: Proof load test (γF = 1.25)
    combinations.append(LoadCombination(
        name='EN14439-H4',
        description='EN 14439 H4: Proof load test (γF=1.25, 1.25Q)',
        factors={working_lc.name: 1.25},
        wind_pressure=0.0,
    ))
    
    # H5: Safety test / emergency (γF = 1.5)
    if test_lc:
        combinations.append(LoadCombination(
            name='EN14439-H5',
            description='EN 14439 H5: Safety test (γF=1.5)',
            factors={test_lc.name: 1.5},
            wind_pressure=0.0,
        ))
    
    # H6: Storm condition (γF = 1.0, higher wind)
    if wind_lc:
        combinations.append(LoadCombination(
            name='EN14439-H6',
            description='EN 14439 H6: Storm wind (survival, γF=1.0)',
            factors={working_lc.name: 1.0},
            wind_pressure=1100.0,  # Storm wind
        ))
    
    # H7: Frequent load case (ψ1 = 0.5)
    if wind_lc:
        combinations.append(LoadCombination(
            name='EN14439-H7',
            description='EN 14439 H7: Frequent (ψ1=0.5, 1.0G+1.0Q+0.5W)',
            factors={working_lc.name: 1.0, wind_lc.name: 0.5},
            wind_pressure=wind_lc.wind_pressure,
        ))
    
    # H8: Quasi-permanent (ψ2 = 0.3)
    if wind_lc:
        combinations.append(LoadCombination(
            name='EN14439-H8',
            description='EN 14439 H8: Quasi-permanent (ψ2=0.3, 1.0G+1.0Q+0.3W)',
            factors={working_lc.name: 1.0, wind_lc.name: 0.3},
            wind_pressure=wind_lc.wind_pressure,
        ))
    
    return apply_load_combination(working_lc, combinations)


def generate_all_load_combinations(load_cases: List[LoadCase]) -> dict:
    """
    Generate all load combinations from all standards.
    
    Returns:
        dict with keys: 'asce', 'eurocode', 'en14439'
    """
    return {
        'asce': generate_asce_combinations(load_cases),
        'eurocode': generate_eurocode_combinations(load_cases),
        'en14439': generate_en14439_combinations(load_cases),
    }
