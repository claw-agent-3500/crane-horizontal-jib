"""Unit conversion utilities for crane-jib-calc."""


def convert_to_imperial(value: float, unit: str) -> float:
    """Convert SI values to Imperial.
    
    Args:
        value: SI value
        unit: one of 'kN', 'm', 'MPa', 'mm'
    Returns:
        Imperial value
    """
    conversions = {
        'kN': lambda v: v * 224.809,    # to lbf
        'm': lambda v: v * 3.28084,     # to ft
        'MPa': lambda v: v * 145.038,   # to psi
        'mm': lambda v: v * 0.0393701,  # to inch
    }
    if unit in conversions:
        return conversions[unit](value)
    return value


def convert_to_si(value: float, unit: str) -> float:
    """Convert Imperial values to SI.
    
    Args:
        value: Imperial value
        unit: one of 'lbf', 'ft', 'psi', 'in'
    Returns:
        SI value
    """
    conversions = {
        'lbf': lambda v: v / 224.809,   # to kN
        'ft': lambda v: v / 3.28084,    # to m
        'psi': lambda v: v / 145.038,    # to MPa
        'in': lambda v: v / 0.0393701,  # to mm
    }
    if unit in conversions:
        return conversions[unit](value)
    return value


def format_with_units(value: float, unit: str, system: str = 'SI') -> str:
    """Format value with unit label.
    
    Args:
        value: numeric value
        unit: base unit (kN, m, MPa, mm)
        system: 'SI' or 'Imperial'
    Returns:
        Formatted string with unit
    """
    if system == 'Imperial':
        if unit == 'kN':
            return f"{value * 224.809:.1f} lbf"
        elif unit == 'm':
            return f"{value * 3.28084:.2f} ft"
        elif unit == 'MPa':
            return f"{value * 145.038:.1f} psi"
        elif unit == 'mm':
            return f"{value * 0.0393701:.2f} in"
    
    # SI
    if unit == 'kN':
        return f"{value:.1f} kN"
    elif unit == 'm':
        return f"{value:.2f} m"
    elif unit == 'MPa':
        return f"{value:.1f} MPa"
    elif unit == 'mm':
        return f"{value:.1f} mm"
    
    return f"{value}"
