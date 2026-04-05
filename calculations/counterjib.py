"""Counterjib structural analysis.

The counterjib is similar to the jib but with static loads (counterweights).
It extends from the tower and carries counterweights/ballast.
"""

import numpy as np
from models import CraneModel, Section, PointLoad, UDL, CounterJibConfig


def create_counterjib_model(
    length: float,
    counterweight: float,
    counterweight_position: float,
    ballasting: float = 0.0,
    height: float = 0.0,
    sections: list = None,
    youngs_modulus: float = 200000.0,  # MPa
) -> CraneModel:
    """
    Create a CraneModel for counterjib analysis.
    
    Args:
        length: Counterjib length (m)
        counterweight: Counterweight magnitude (kN)
        counterweight_position: Position from root (m)
        ballasting: Additional ballast (kN)
        height: Height position (m)
        sections: List of Section objects
        youngs_modulus: Steel Young's modulus (MPa)
    
    Returns:
        CraneModel configured for counterjib analysis
    """
    # Default sections if not provided
    if not sections:
        sections = [
            Section(
                name='Root',
                start=0.0,
                end=length * 0.3,
                weight_per_length=2.0,
                area=0.04,
                moment_of_inertia=0.012,
                height=1.5,
                yield_strength=345.0,
            ),
            Section(
                name='Mid',
                start=length * 0.3,
                end=length * 0.7,
                weight_per_length=1.8,
                area=0.035,
                moment_of_inertia=0.010,
                height=1.4,
                yield_strength=345.0,
            ),
            Section(
                name='Tip',
                start=length * 0.7,
                end=length,
                weight_per_length=1.5,
                area=0.03,
                moment_of_inertia=0.008,
                height=1.3,
                yield_strength=345.0,
            ),
        ]
    
    # Create point loads for counterweights
    point_loads = []
    
    # Main counterweight
    if counterweight > 0:
        point_loads.append(PointLoad(
            name='counterweight',
            position=counterweight_position,
            magnitude=counterweight,
        ))
    
    # Additional ballasting
    if ballasting > 0:
        point_loads.append(PointLoad(
            name='ballast',
            position=length - 1.0,  # Typically at tip
            magnitude=ballasting,
        ))
    
    # Self-weight as UDL
    total_weight = sum(s.weight_per_length * (s.end - s.start) for s in sections)
    udls = [
        UDL(
            name='self_weight',
            start=0.0,
            end=length,
            magnitude=total_weight / length,  # kN/m average
        )
    ]
    
    # Create model
    model = CraneModel(
        name='Counterjib',
        jib_length=length,
        jib_height_position=height,
        sections=sections,
        point_loads=point_loads,
        udls=udls,
        youngs_modulus=youngs_modulus,
        load_cases=[
            # Single load case for counterjib (static)
        ],
    )
    
    return model


def analyze_counterjib(config: CounterJibConfig, youngs_modulus: float = 200000.0):
    """
    Analyze counterjib and return results.
    
    Similar to jib analysis but with static loads.
    Returns shear, moment, stress, deflection.
    """
    from crane_calc import run_analysis
    
    # Create model
    model = create_counterjib_model(
        length=config.length,
        counterweight=config.counterweight,
        counterweight_position=config.counterweight_position,
        ballasting=config.ballasting,
        height=config.height,
        sections=config.sections,
        youngs_modulus=youngs_modulus,
    )
    
    # Add default load case
    from models import LoadCase
    model.load_cases.append(LoadCase(
        name='Counterweight',
        coefficients={'self_weight': 1.0, 'counterweight': 1.0, 'ballast': 1.0},
    ))
    
    # Run analysis
    result = run_analysis(model)
    
    return model, result


def compute_counterjib_moment_at_root(
    counterweight: float,
    counterweight_position: float,
    ballasting: float,
    length: float,
    self_weight_per_m: float,
) -> float:
    """
    Quick calculation of moment at root (tower connection).
    
    M_root = Σ(Fi × xi) + q × L²/2
    
    Args:
        counterweight: kN
        counterweight_position: m from root
        ballasting: kN  
        length: m
        self_weight_per_m: kN/m
    
    Returns:
        Moment at root (kN·m)
    """
    # Counterweight moment
    m_counter = counterweight * counterweight_position
    
    # Ballast moment (assume at tip)
    m_ballast = ballasting * length
    
    # Self-weight moment (uniform load)
    m_self = self_weight_per_m * length * length / 2
    
    return m_counter + m_ballast + m_self


def compare_jib_counterjib(jib_result, counterjib_result):
    """
    Compare jib and counterjib analyses.
    
    Returns comparison metrics.
    """
    return {
        'jib_max_moment': float(np.max(np.abs(jib_result.M))),
        'counterjib_max_moment': float(np.max(np.abs(counterjib_result.M))),
        'jib_max_stress': float(np.max(jib_result.sigma)),
        'counterjib_max_stress': float(np.max(counterjib_result.sigma)),
        'jib_tip_deflection': float(jib_result.delta[-1]),
        'counterjib_tip_deflection': float(counterjib_result.delta[-1]),
    }