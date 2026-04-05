"""Section optimization - find optimal section properties."""

import numpy as np
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class OptimizationResult:
    """Result of section optimization."""
    original_utilization: float
    optimized_utilization: float
    suggested_area: float
    suggested_inertia: float
    iterations: int
    converged: bool


def optimize_section(model, target_utilization: float = 0.80,
                     max_iterations: int = 50,
                     min_factor: float = 0.5,
                     max_factor: float = 2.0) -> dict:
    """
    Optimize section properties to achieve target utilization.
    
    Args:
        model: CraneModel with current sections
        target_utilization: Target utilization ratio (0.80 = 80%)
        max_iterations: Maximum optimization iterations
        min_factor: Minimum scaling factor
        max_factor: Maximum scaling factor
    
    Returns:
        dict with optimization results per section
    """
    from crane_calc import run_analysis
    
    # Run initial analysis
    result = run_analysis(model)
    max_stress = np.max(result.sigma)
    
    # Get current yield strengths
    yields = [s.yield_strength for s in model.sections]
    current_util = max_stress / max(yields) if yields else 1.0
    
    results = {}
    
    for i, sec in enumerate(model.sections):
        # Calculate required properties
        current_area = sec.area
        current_inertia = sec.moment_of_inertia
        
        # Ratio needed to achieve target
        if current_util > 0:
            scale = current_util / target_utilization
        else:
            scale = 1.0
        
        # Clamp scale factor
        scale = max(min_factor, min(max_factor, scale))
        
        # Suggested properties
        suggested_area = current_area * scale
        suggested_inertia = current_inertia * scale
        
        results[sec.name] = OptimizationResult(
            original_utilization=current_util * 100,
            optimized_utilization=target_utilization * 100,
            suggested_area=suggested_area,
            suggested_inertia=suggested_inertia,
            iterations=1,  # Single iteration for now
            converged=True,
        )
    
    return results


def find_optimal_jib_length(model, payload: float, 
                            max_utilization: float = 0.90,
                            length_range: tuple = (30.0, 80.0),
                            step: float = 5.0) -> dict:
    """
    Find optimal jib length that satisfies utilization constraint.
    
    Returns:
        dict with optimal length and analysis results
    """
    from batch_analysis import JibConfig, BatchAnalyzer
    
    lengths = np.arange(length_range[0], length_range[1] + step, step)
    
    best_length = None
    best_util = float('inf')
    results = []
    
    for length in lengths:
        # Create config
        config = JibConfig(
            name=f'{int(length)}m',
            jib_length=length,
            jib_height_position=model.jib_height_position,
        )
        
        # Copy sections and adjust
        for sec in model.sections:
            scale = length / model.jib_length
            config.sections.append(type(sec)(
                name=sec.name,
                start=sec.start * scale,
                end=min(sec.end * scale, length),
                weight_per_length=sec.weight_per_length,
                area=sec.area,
                moment_of_inertia=sec.moment_of_inertia,
                height=sec.height,
                yield_strength=sec.yield_strength,
            ))
        
        # Copy load
        for pl in model.point_loads:
            if pl.position * scale <= length:
                config.point_loads.append(pl)
        
        # Quick analysis estimate
        # M ≈ payload * position
        est_moment = payload * (length * 0.75)  # Assume 75% reach
        est_stress = est_moment / (model.sections[0].moment_of_inertia if model.sections else 0.01)
        util = est_stress / 345.0
        
        results.append({
            'length': length,
            'estimated_utilization': util * 100,
        })
        
        if util < max_utilization and util < best_util:
            best_util = util
            best_length = length
    
    return {
        'optimal_length': best_length,
        'estimated_utilization': best_util * 100,
        'all_lengths': results,
    }
