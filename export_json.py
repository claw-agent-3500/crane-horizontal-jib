"""JSON export for API/integration."""

import json
import numpy as np
from datetime import datetime


def export_analysis_json(model, result, file_path: str = None) -> str:
    """
    Export complete analysis results to JSON.
    
    Suitable for API integration, database storage, or further processing.
    """
    from crane_calc import run_analysis
    
    # Build JSON structure
    output = {
        "metadata": {
            "generator": "crane-jib-calc",
            "version": "0.14.0",
            "timestamp": datetime.now().isoformat(),
            "model_name": model.name,
            "jib_length": model.jib_length,
            "youngs_modulus": model.youngs_modulus,
        },
        "model": {
            "sections": [
                {
                    "name": s.name,
                    "start_m": s.start,
                    "end_m": s.end,
                    "length_m": s.end - s.start,
                    "weight_per_length_kN_m": s.weight_per_length,
                    "area_m2": s.area,
                    "moment_of_inertia_m4": s.moment_of_inertia,
                    "height_m": s.height,
                    "yield_strength_MPa": s.yield_strength,
                }
                for s in model.sections
            ],
            "point_loads": [
                {
                    "name": pl.name,
                    "position_m": pl.position,
                    "magnitude_kN": pl.magnitude,
                }
                for pl in model.point_loads
            ],
            "udls": [
                {
                    "name": udl.name,
                    "start_m": udl.start,
                    "end_m": udl.end,
                    "magnitude_kN_m": udl.magnitude,
                }
                for udl in model.udls
            ],
            "load_cases": [
                {
                    "name": lc.name,
                    "coefficients": lc.coefficients,
                    "wind_pressure_Pa": lc.wind_pressure,
                }
                for lc in model.load_cases
            ],
        },
        "results": {
            "x_coordinates": result.x.tolist() if hasattr(result, 'x') else [],
            "shear_force_kN": result.V.tolist() if hasattr(result, 'V') else [],
            "bending_moment_kNm": result.M.tolist() if hasattr(result, 'M') else [],
            "deflection_m": result.delta.tolist() if hasattr(result, 'delta') else [],
            "stress_MPa": result.sigma.tolist() if hasattr(result, 'sigma') else [],
        },
        "summary": {
            "max_shear_kN": float(np.max(np.abs(result.V))) if hasattr(result, 'V') else 0,
            "max_moment_kNm": float(np.max(np.abs(result.M))) if hasattr(result, 'M') else 0,
            "max_stress_MPa": float(np.max(result.sigma)) if hasattr(result, 'sigma') else 0,
            "max_deflection_m": float(np.max(np.abs(result.delta))) if hasattr(result, 'delta') else 0,
            "tip_deflection_m": float(result.delta[-1]) if hasattr(result, 'delta') else 0,
            "max_utilization_percent": float(np.max(result.sigma) / 345.0 * 100) if hasattr(result, 'sigma') else 0,
        },
    }
    
    json_str = json.dumps(output, indent=2)
    
    if file_path:
        with open(file_path, 'w') as f:
            f.write(json_str)
    
    return json_str


def export_batch_json(analyzer, file_path: str = None) -> str:
    """
    Export batch analysis results to JSON.
    """
    output = {
        "metadata": {
            "generator": "crane-jib-calc",
            "version": "0.14.0",
            "timestamp": datetime.now().isoformat(),
            "total_configurations": len(analyzer.results),
        },
        "results": [
            {
                "configuration": r.config_name,
                "max_moment_kNm": r.max_moment,
                "max_shear_kN": r.max_shear,
                "max_stress_MPa": r.max_stress,
                "utilization_percent": r.max_utilization,
                "tip_deflection_m": r.tip_deflection,
                "worst_load_case": r.worst_load_case,
                "passed": r.passed,
            }
            for r in analyzer.results
        ],
        "worst_case": {
            "configuration": analyzer.worst_case.config_name,
            "max_moment_kNm": analyzer.worst_case.max_moment,
            "utilization_percent": analyzer.worst_case.max_utilization,
        } if analyzer.worst_case else None,
    }
    
    json_str = json.dumps(output, indent=2)
    
    if file_path:
        with open(file_path, 'w') as f:
            f.write(json_str)
    
    return json_str


def add_reactions_to_json(model, result, json_data: dict):
    """Add reaction forces to JSON export."""
    from models import compute_reactions
    
    reactions = compute_reactions(model, result.V, result.M)
    
    json_data['reactions'] = [
        {
            'position_m': r.x,
            'shear_kN': r.shear,
            'moment_kNm': r.moment,
        }
        for r in reactions
    ]
    
    return json_data
