#!/usr/bin/env python3
"""
Flat Top Tower Crane Jib Calculator
=====================================
Modular analysis tool with load cases and trolley envelope.

Usage:
    python3 crane_calc.py input.yaml [--output report.html] [--no-browser]
"""

import argparse
import sys
from pathlib import Path

import numpy as np

from models import CraneModel, AnalysisResult, LoadCase, MAX_POINT_LOADS, MAX_UDLS
from validation import validate_model
from loader import load_model
from calculations import compute_beam, compute_deflection, compute_stress, compute_truss_forces
from report import generate_html


def _run_single(model: CraneModel, x: np.ndarray, load_case: LoadCase,
                trolley_pos: float = None) -> dict:
    """Run pipeline for one load case + one trolley position."""
    beam = compute_beam(model, x, load_case, trolley_pos)
    V, M = beam['V'], beam['M']
    defl = compute_deflection(model, x, M)
    stress = compute_stress(model, x, M, V)
    truss = compute_truss_forces(model, x, M, V)
    return {
        'V': V, 'M': M,
        'theta': defl['theta'], 'delta': defl['delta'],
        'sigma': stress['sigma'], 'tau': stress['tau'],
        **truss,
    }


def _update_envelope(env: dict, res: dict):
    """Take element-wise max into envelope dict."""
    env['V'] = np.maximum(env['V'], np.abs(res['V']))
    env['M'] = np.maximum(env['M'], res['M'])
    env['delta'] = np.maximum(env['delta'], res['delta'])
    env['sigma'] = np.maximum(env['sigma'], res['sigma'])
    env['tau'] = np.maximum(env['tau'], np.abs(res['tau']))
    env['F_upper_chord'] = np.maximum(env['F_upper_chord'], np.abs(res['F_upper_chord']))
    env['F_lower_chord'] = np.maximum(env['F_lower_chord'], np.abs(res['F_lower_chord']))
    env['F_comp_diag'] = np.maximum(env['F_comp_diag'], np.abs(res['F_comp_diag']))
    env['F_tens_diag'] = np.maximum(env['F_tens_diag'], np.abs(res['F_tens_diag']))
    env['F_neut_diag'] = np.maximum(env['F_neut_diag'], np.abs(res['F_neut_diag']))


def run_analysis(model: CraneModel) -> AnalysisResult:
    """
    Run analysis across all load cases.

    For each load case with trolley coef > 0:
      sweep trolley positions, take envelope.
    For each load case without trolley:
      single computation.

    Final result = envelope across all load cases.
    """
    x = np.linspace(0, model.jib_length, model.num_points)
    n = len(x)
    load_cases = model.load_cases or [LoadCase(name='Default', coefficients={})]

    # Initialize envelope
    env = {k: np.zeros(n) for k in [
        'V', 'M', 'delta', 'sigma', 'tau',
        'F_upper_chord', 'F_lower_chord', 'F_comp_diag', 'F_tens_diag', 'F_neut_diag',
    ]}

    # Store theta from the case that produces max root moment
    best_theta = np.zeros(n)
    best_root_moment = 0
    worst_trolley_pos = 0.0
    V_base = np.zeros(n)
    M_base = np.zeros(n)

    # Also track result that gave max root moment for section forces
    best_res = None

    for lc in load_cases:
        has_trolley = model.trolley and lc.coef('trolley') > 0

        if has_trolley:
            t = model.trolley
            trolley_positions = np.arange(t.min_position, t.max_position + t.step / 2, t.step)

            for tp in trolley_positions:
                res = _run_single(model, x, lc, trolley_pos=tp)
                _update_envelope(env, res)
                root_m = res['M'][0]
                if root_m > best_root_moment:
                    best_root_moment = root_m
                    best_theta = res['theta']
                    worst_trolley_pos = tp
                    best_res = res
        else:
            res = _run_single(model, x, lc)
            _update_envelope(env, res)
            root_m = res['M'][0]
            if root_m > best_root_moment:
                best_root_moment = root_m
                best_theta = res['theta']
                best_res = res

            if np.all(V_base == 0):
                V_base = res['V'].copy()
                M_base = res['M'].copy()

    # Compute forces at each section start (pivot point for design)
    section_start_forces = []
    if best_res is not None:
        for sec in model.sections:
            # Find index closest to section start
            idx = int(sec.start / (model.jib_length / (n - 1)))
            idx = min(idx, n - 1)

            # For this section, upper chord is tension if M is negative (sagging), compression if positive (hogging)
            # Wait - our convention: positive M = hogging (tension on bottom, compression on top)
            # For cantilever root at X=0, positive M = compression on top = upper chord in compression
            # So at section start: upper_chord = M/h (comp if +), lower_chord = -M/h (tens if +)
            M_at_start = best_res['M'][idx]
            h = sec.height

            if sec.truss and h > 0:
                uc = sec.truss.upper_chords
                lc = sec.truss.lower_chords
                upper = M_at_start / (h * uc) if uc > 0 else 0  # compression (positive)
                lower = -M_at_start / (h * lc) if lc > 0 else 0  # tension (negative)

                # Diagonals at this section
                comp_diag = abs(best_res['F_comp_diag'][idx])
                tens_diag = best_res['F_tens_diag'][idx]  # already negative
                neut_diag = abs(best_res['F_neut_diag'][idx])
            else:
                upper = lower = comp_diag = tens_diag = neut_diag = 0.0

            section_start_forces.append({
                'section': sec.name,
                'x': sec.start,
                'upper_chord': upper,
                'lower_chord': lower,
                'comp_diag': comp_diag,
                'tens_diag': tens_diag,
                'neut_diag': neut_diag,
            })

    max_V_idx = np.argmax(env['V'])
    max_M_idx = np.argmax(env['M'])
    max_sigma_idx = np.argmax(env['sigma'])
    max_delta_idx = np.argmax(env['delta'])

    # Compute utilization ratios (sigma / yield_strength) for each section
    section_util = []
    if best_res is not None:
        for sec in model.sections:
            idx = int(sec.start / (model.jib_length / (n - 1)))
            idx = min(idx, n - 1)
            sigma_at_start = env['sigma'][idx]
            util = sigma_at_start / sec.yield_strength if sec.yield_strength > 0 else 0
            section_util.append({
                'section': sec.name,
                'x': sec.start,
                'sigma': sigma_at_start,
                'yield_strength': sec.yield_strength,
                'utilization': util,
            })

    max_util = max([u['utilization'] for u in section_util], default=0)
    max_util_pos = 0
    for u in section_util:
        if u['utilization'] == max_util:
            max_util_pos = u['x']
            break

    return AnalysisResult(
        x=x,
        V_base=V_base, M_base=M_base,
        V=env['V'], M=env['M'],
        theta=best_theta, delta=env['delta'],
        sigma=env['sigma'], tau=env['tau'],
        F_upper_chord=env['F_upper_chord'],
        F_lower_chord=-env['F_lower_chord'],
        F_comp_diag=env['F_comp_diag'],
        F_tens_diag=-env['F_tens_diag'],
        F_neut_diag=env['F_neut_diag'],
        reaction_V=env['V'][0], reaction_M=env['M'][0],
        max_V=np.max(env['V']), max_V_pos=x[max_V_idx],
        max_M=np.max(env['M']), max_M_pos=x[max_M_idx],
        max_sigma=np.max(env['sigma']), max_sigma_pos=x[max_sigma_idx],
        max_delta=np.max(env['delta']), max_delta_pos=x[max_delta_idx],
        tip_delta=env['delta'][-1],
        max_F_upper=np.max(env['F_upper_chord']),
        max_F_lower=np.max(env['F_lower_chord']),
        max_F_comp_diag=np.max(env['F_comp_diag']),
        max_F_tens_diag=np.max(env['F_tens_diag']),
        worst_trolley_pos=worst_trolley_pos,
        section_forces_at_start=section_start_forces,
        max_utilization=max_util,
        max_utilization_pos=max_util_pos,
        section_utilization=section_util,
        sections=model.sections,
        model=model,
    )


def main():
    parser = argparse.ArgumentParser(
        description='Tower Crane Jib Calculator — load cases + trolley envelope'
    )
    parser.add_argument('input', help='Path to YAML input file')
    parser.add_argument('-o', '--output', default='report.html',
                        help='Output HTML report path (default: report.html)')
    parser.add_argument('--csv', action='store_true',
                        help='Also export results to CSV files')
    parser.add_argument('--no-browser', action='store_true',
                        help='Skip opening the report in browser')

    args = parser.parse_args()

    print(f"📐 Loading crane model from: {args.input}")
    model = load_model(args.input)
    print(f"   {model.name} — {model.jib_length:.0f}m jib, {len(model.sections)} sections")
    print(f"   E = {model.youngs_modulus / 1e6:.0f} GPa")
    print(f"   Point loads: {len(model.point_loads)}/{MAX_POINT_LOADS}")
    print(f"   UDLs: {len(model.udls)}/{MAX_UDLS}")
    has_truss = any(s.truss for s in model.sections)
    print(f"   Truss config: {'Yes' if has_truss else 'No'}")
    if model.trolley:
        t = model.trolley
        print(f"   Trolley: {t.magnitude:.0f} kN, travel [{t.min_position:.0f}–{t.max_position:.0f} m]")
    print(f"   Load cases: {len(model.load_cases)}")
    for lc in model.load_cases:
        active = {k: v for k, v in lc.coefficients.items() if v != 1.0}
        info = ', '.join(f'{k}={v}' for k, v in active.items()) if active else 'all=1.0'
        print(f"     • {lc.name} [{info}]")

    # Validate
    errors = validate_model(model)
    if errors:
        print("❌ Validation errors:")
        for e in errors:
            print(f"   • {e}")


def _parse_serviceability_limit(limit_str: str, jib_length: float) -> float:
    """Parse serviceability limit string to mm.
    
    Args:
        limit_str: 'L/250', 'L/400', or 'custom' or a ratio like '250'
    Returns:
        Allowable tip deflection in mm
    """
    limit_str = str(limit_str).strip().upper()
    
    if limit_str.startswith('L/'):
        # Parse 'L/250' or 'L/400'
        ratio = int(limit_str.split('/')[1])
        return jib_length * 1000 / ratio
    elif limit_str.isdigit():
        # Direct ratio value
        return jib_length * 1000 / int(limit_str)
    else:
        # Default to L/250
        return jib_length * 1000 / 250
