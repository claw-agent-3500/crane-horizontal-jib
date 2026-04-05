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

# Standard counterweight configurations per jib size
# (jib_length: counterweight_kN, position_m, ballast_kN)
COUNTERJIB_CONFIGS = {
    # TC7030 series
    45.0: {'counterweight': 180.0, 'position': 10.0, 'ballast': 80.0},
    50.0: {'counterweight': 200.0, 'position': 11.0, 'ballast': 100.0},
    55.0: {'counterweight': 220.0, 'position': 12.0, 'ballast': 120.0},
    60.0: {'counterweight': 250.0, 'position': 13.0, 'ballast': 140.0},
    65.0: {'counterweight': 280.0, 'position': 14.0, 'ballast': 160.0},
    70.0: {'counterweight': 320.0, 'position': 14.0, 'ballast': 180.0},
    # TC7030-15 (stronger)
    'TC7030-15-65': {'counterweight': 350.0, 'position': 14.0, 'ballast': 200.0},
    'TC7030-15-70': {'counterweight': 380.0, 'position': 14.0, 'ballast': 220.0},
    # TC7030-18 (largest)
    'TC7030-18-70': {'counterweight': 420.0, 'position': 14.0, 'ballast': 250.0},
}


def get_counterjib_for_jib(jib_config: str or float, counterjib_length: float = 15.0) -> dict:
    """
    Get appropriate counterjib config for given jib.
    
    Args:
        jib_config: Either jib length (float) or jib name (str like 'TC7030-15-65')
        counterjib_length: Counterjib length (default 15m)
    
    Returns:
        dict with counterweight, position, ballast
    """
    if isinstance(jib_config, str):
        # Named config
        return COUNTERJIB_CONFIGS.get(jib_config, COUNTERJIB_CONFIGS[60.0])
    else:
        # Length-based
        closest = min(COUNTERJIB_CONFIGS.keys(), key=lambda k: abs(k - jib_config) if isinstance(k, float) else 999)
        return COUNTERJIB_CONFIGS.get(closest, COUNTERJIB_CONFIGS[60.0])


def create_counterjib_for_jib(
    jib_length: float,
    jib_name: str = None,
    counterjib_length: float = 15.0,
    custom_counterweight: float = None,
) -> CraneModel:
    """
    Create counterjib model matched to specific jib configuration.
    
    Args:
        jib_length: Length of main jib
        jib_name: Optional name (e.g., 'TC7030-15-65') for precise config lookup
        counterjib_length: Counterjib structural length
        custom_counterweight: Override default if provided
    
    Returns:
        CraneModel for counterjib
    """
    # Get config
    if jib_name:
        config = get_counterjib_for_jib(jib_name, counterjib_length)
    else:
        config = get_counterjib_for_jib(jib_length, counterjib_length)
    
    # Override if custom specified
    if custom_counterweight is not None:
        config['counterweight'] = custom_counterweight
    
    return create_counterjib_model(
        length=counterjib_length,
        counterweight=config['counterweight'],
        counterweight_position=config['position'],
        ballasting=config['ballast'],
    )


class CounterJibSelector:
    """Select appropriate counterjib based on jib selection."""
    
    def __init__(self, counterjib_length: float = 15.0):
        self.counterjib_length = counterjib_length
        self.configs = {}
    
    def add_jib_config(self, jib_name: str, counterweight: float, position: float, ballast: float = 0.0):
        """Add custom counterjib config for a specific jib."""
        self.configs[jib_name] = {
            'counterweight': counterweight,
            'position': position,
            'ballast': ballast,
        }
    
    def get_counterjib(self, jib_name: str) -> CraneModel:
        """Get counterjib model for given jib name."""
        config = self.configs.get(jib_name, COUNTERJIB_CONFIGS.get(jib_name, COUNTERJIB_CONFIGS[60.0]))
        
        return create_counterjib_model(
            length=self.counterjib_length,
            counterweight=config['counterweight'],
            counterweight_position=config['position'],
            ballasting=config.get('ballast', 0.0),
        )
    
    def list_available(self) -> list:
        """List all available jib configurations."""
        return list(self.configs.keys()) + list(COUNTERJIB_CONFIGS.keys())


def analyze_complete_crane(
    jib_input: str = "examples/working_60m/input.yaml",
    counterjib_length: float = 15.0,
    counterjib_name: str = None,
) -> dict:
    """
    Analyze complete crane (jib + counterjib) together.
    
    Returns combined results for both jib and counterjib.
    """
    from loader import load_model
    from crane_calc import run_analysis
    import numpy as np
    
    # Analyze jib
    jib_model = load_model(jib_input)
    jib_result = run_analysis(jib_model)
    
    # Get counterjib matching jib
    if counterjib_name is None:
        counterjib_name = jib_model.name
    
    counterjib_model = create_counterjib_for_jib(
        jib_length=jib_model.jib_length,
        jib_name=counterjib_name,
        counterjib_length=counterjib_length,
    )
    
    # Add load case
    from models import LoadCase
    counterjib_model.load_cases.append(LoadCase(
        name='Counterweight',
        coefficients={'self_weight': 1.0, 'counterweight': 1.0, 'ballast': 1.0},
    ))
    
    counterjib_result = run_analysis(counterjib_model)
    
    return {
        'jib': {
            'model': jib_model,
            'result': jib_result,
            'max_moment': float(np.max(np.abs(jib_result.M))),
            'max_stress': float(np.max(jib_result.sigma)),
            'max_utilization': float(np.max(jib_result.sigma) / 345.0 * 100),
            'tip_deflection': float(jib_result.delta[-1]),
        },
        'counterjib': {
            'model': counterjib_model,
            'result': counterjib_result,
            'max_moment': float(np.max(np.abs(counterjib_result.M))),
            'max_stress': float(np.max(counterjib_result.sigma)),
            'max_utilization': float(np.max(counterjib_result.sigma) / 345.0 * 100),
            'tip_deflection': float(counterjib_result.delta[-1]),
        },
    }


def print_complete_analysis(results: dict):
    """Print formatted analysis results."""
    print("=" * 60)
    print("COMPLETE CRANE ANALYSIS")
    print("=" * 60)
    
    print("\n📐 JIB (Main Arm)")
    print(f"   Length: {results['jib']['model'].jib_length}m")
    print(f"   Max Moment: {results['jib']['max_moment']:.0f} kN·m")
    print(f"   Max Stress: {results['jib']['max_stress']:.0f} MPa")
    print(f"   Utilization: {results['jib']['max_utilization']:.1f}%")
    print(f"   Tip Deflection: {results['jib']['tip_deflection']:.0f} mm")
    
    print("\n⚖️ COUNTERJIB (Counterweight Arm)")
    print(f"   Length: {results['counterjib']['model'].jib_length}m")
    print(f"   Max Moment: {results['counterjib']['max_moment']:.0f} kN·m")
    print(f"   Max Stress: {results['counterjib']['max_stress']:.0f} MPa")
    print(f"   Utilization: {results['counterjib']['max_utilization']:.1f}%")
    print(f"   Tip Deflection: {results['counterjib']['tip_deflection']:.0f} mm")
    
    print("\n" + "=" * 60)
