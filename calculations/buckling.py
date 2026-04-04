"""Global buckling analysis using Euler formula."""

import numpy as np
from models import CraneModel, AnalysisResult
from calculations.beam import compute_beam


def compute_global_buckling(model: CraneModel, x: np.ndarray, M: np.ndarray, V: np.ndarray) -> dict:
    """
    Compute global buckling safety factor using Euler formula.
    
    For a simply supported beam (jib pinned at root, free at tip):
    - Euler critical load: P_E = π²EI / (KL)²
    - Effective length factor K = 0.7 for semi-rigid connection
    
    Returns dict with:
    - P_critical: array of critical axial loads per section
    - safety_factor: array of buckling safety factors
    - min_safety: minimum safety factor across all sections
    - failed_sections: list of sections where safety < 1.0
    """
    E = model.youngs_modulus  # MPa
    K = 0.7  # effective length factor for semi-rigid
    
    # For upper chord (in compression)
    results = {
        'P_critical': np.zeros(len(x)),
        'safety_factor': np.zeros(len(x)),
        'min_safety': float('inf'),
        'failed_sections': [],
        'buckling_lengths': [],
    }
    
    # Find compression force in upper chord at each x
    from calculations.truss import compute_truss_forces
    truss = compute_truss_forces(model, x, M, V)
    P_upper = -truss['F_upper_chord']  # positive = compression
    
    # For each section, compute buckling capacity
    for i, xi in enumerate(x):
        sec = None
        for s in model.sections:
            if s.start <= xi <= s.end:
                sec = s
                break
        
        if sec is None:
            continue
        
        # Effective length: distance to next panel point (approx half panel if uniform)
        L_eff = 3.0  # assume 3m panel spacing
        
        # Euler critical load (N = kN * 1000 for MPa*mm² → N)
        I = sec.moment_of_inertia * 1e12  # mm⁴ to mm²*mm²
        P_cr = (np.pi**2 * E * I) / ((K * L_eff * 1000)**2)  # N
        P_cr_kN = P_cr / 1000  # convert to kN
        
        results['P_critical'][i] = P_cr_kN
        
        # Safety factor
        if P_upper[i] > 0:
            sf = P_cr_kN / P_upper[i] if P_upper[i] > 0 else float('inf')
            results['safety_factor'][i] = sf
            
            if sf < results['min_safety']:
                results['min_safety'] = sf
            
            if sf < 1.0:
                results['failed_sections'].append(xi)
    
    return results


def add_buckling_to_result(result: AnalysisResult) -> AnalysisResult:
    """Add buckling analysis to existing result."""
    from calculations.beam import compute_beam
    from calculations.truss import compute_truss_forces
    
    x = result.x
    beam = compute_beam(result.model, x, result.load_case)
    M = beam['M']
    V = beam['V']
    
    buckling = compute_global_buckling(result.model, x, M, V)
    
    # Add to result
    result.global_buckling = buckling
    return result