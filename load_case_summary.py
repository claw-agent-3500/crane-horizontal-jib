"""Per-load-case summary computation."""

import numpy as np
from models import CraneModel


def compute_load_case_summary(model: CraneModel, x: np.ndarray, load_cases, run_single_fn) -> list:
    """Compute summary for each load case."""
    results = []
    n = len(x)
    
    for lc in load_cases:
        has_trolley = model.trolley and lc.coef('trolley') > 0
        
        if has_trolley:
            t = model.trolley
            trolley_positions = np.arange(t.min_position, t.max_position + t.step / 2, t.step)
            
            max_V, max_M, max_sigma, max_util, max_delta = 0, 0, 0, 0, 0
            for tp in trolley_positions:
                res = run_single_fn(model, x, lc, trolley_pos=tp)
                max_V = max(max_V, np.max(np.abs(res['V'])))
                max_M = max(max_M, np.max(res['M']))
                max_sigma = max(max_sigma, np.max(res['sigma']))
                
                # Utilization at section starts
                util_at_positions = []
                for sec in model.sections:
                    idx = int(sec.start / (model.jib_length / (n - 1)))
                    idx = min(idx, n - 1)
                    s = res['sigma'][idx]
                    util = s / sec.yield_strength if sec.yield_strength > 0 else 0
                    util_at_positions.append(util)
                max_util = max(max_util, max(util_at_positions, default=0))
                max_delta = max(max_delta, np.max(res['delta']))
        else:
            res = run_single_fn(model, x, lc)
            max_V = np.max(np.abs(res['V']))
            max_M = np.max(res['M'])
            max_sigma = np.max(res['sigma'])
            
            util_at_positions = []
            for sec in model.sections:
                idx = int(sec.start / (model.jib_length / (n - 1)))
                idx = min(idx, n - 1)
                s = res['sigma'][idx]
                util = s / sec.yield_strength if sec.yield_strength > 0 else 0
                util_at_positions.append(util)
            max_util = max(util_at_positions, default=0)
            max_delta = np.max(res['delta'])
        
        results.append({
            'name': lc.name,
            'max_V': max_V,
            'max_M': max_M,
            'max_sigma': max_sigma,
            'max_utilization': max_util,
            'tip_delta': max_delta,
            'wind_pressure': lc.wind_pressure,
        })
    
    return results
