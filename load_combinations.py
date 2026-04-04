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