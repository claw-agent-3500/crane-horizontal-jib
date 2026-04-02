#!/usr/bin/env python3
"""
Flat Top Tower Crane Jib Calculator
=====================================
Modular analysis tool for flat-top tower crane jibs.
Computes SFD, BMD, deflection, stress, and truss member forces.

Usage:
    python3 crane_calc.py input.yaml [--output report.html] [--no-browser]
"""

import argparse
import sys
from pathlib import Path

import numpy as np

from models import CraneModel, AnalysisResult, SweepResult, MAX_POINT_LOADS, MAX_UDLS
from validation import validate_model
from loader import load_model
from calculations import compute_beam, compute_deflection, compute_stress, compute_truss_forces
from report import generate_html


def run_analysis(model: CraneModel, trolley_pos: float = None,
                 trolley_mag: float = None) -> AnalysisResult:
    """Run all calculation modules and assemble result."""
    x = np.linspace(0, model.jib_length, model.num_points)

    # Pipeline: beam → deflection → stress → truss
    beam = compute_beam(model, x, trolley_pos, trolley_mag)
    V, M = beam['V'], beam['M']

    defl = compute_deflection(model, x, M)

    stress = compute_stress(model, x, M, V)

    truss = compute_truss_forces(model, x, M, V)

    # Summary scalars
    max_V_idx = np.argmax(np.abs(V))
    max_M_idx = np.argmax(M)
    max_sigma_idx = np.argmax(stress['sigma'].max() and np.argmax(stress['sigma']))
    max_delta_idx = np.argmax(defl['delta'])

    return AnalysisResult(
        x=x, V=V, M=M,
        theta=defl['theta'], delta=defl['delta'],
        sigma=stress['sigma'], tau=stress['tau'],
        reaction_V=V[0], reaction_M=M[0],
        max_V=np.max(np.abs(V)), max_V_pos=x[max_V_idx],
        max_M=np.max(M), max_M_pos=x[max_M_idx],
        max_sigma=np.max(stress['sigma']), max_sigma_pos=x[np.argmax(stress['sigma'])],
        max_delta=np.max(defl['delta']), max_delta_pos=x[max_delta_idx],
        tip_delta=defl['delta'][-1],
        F_upper_chord=truss['F_upper_chord'],
        F_lower_chord=truss['F_lower_chord'],
        F_comp_diag=truss['F_comp_diag'],
        F_tens_diag=truss['F_tens_diag'],
        F_neut_diag=truss['F_neut_diag'],
        max_F_upper=np.max(np.abs(truss['F_upper_chord'])),
        max_F_lower=np.max(np.abs(truss['F_lower_chord'])),
        max_F_comp_diag=np.max(np.abs(truss['F_comp_diag'])),
        max_F_tens_diag=np.max(np.abs(truss['F_tens_diag'])),
        sections=model.sections,
        model=model,
    )


def run_sweep(model: CraneModel) -> SweepResult:
    """Sweep trolley position for worst case."""
    sweep = model.trolley_sweep
    pos_max = sweep.max_position if sweep.max_position > 0 else model.jib_length - 2.0
    positions = np.arange(sweep.min_position, pos_max + sweep.step / 2, sweep.step)

    root_moments = np.zeros_like(positions)
    root_shears = np.zeros_like(positions)
    tip_deflections = np.zeros_like(positions)

    for i, pos in enumerate(positions):
        result = run_analysis(model, trolley_pos=pos, trolley_mag=sweep.magnitude)
        root_moments[i] = result.reaction_M
        root_shears[i] = result.reaction_V
        tip_deflections[i] = result.tip_delta

    worst_idx = np.argmax(root_moments)
    return SweepResult(
        positions=positions,
        root_moments=root_moments,
        root_shears=root_shears,
        tip_deflections=tip_deflections,
        worst_position=positions[worst_idx],
        worst_moment=root_moments[worst_idx],
        worst_shear=root_shears[worst_idx],
        worst_deflection=tip_deflections[worst_idx],
    )


def main():
    parser = argparse.ArgumentParser(
        description='Tower Crane Jib Calculator — SFD, BMD, deflection, stress & truss forces'
    )
    parser.add_argument('input', help='Path to YAML input file')
    parser.add_argument('-o', '--output', default='report.html',
                        help='Output HTML report path (default: report.html)')
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
    if model.trolley_sweep:
        ts = model.trolley_sweep
        pmax = ts.max_position if ts.max_position > 0 else model.jib_length - 2
        print(f"   Trolley sweep: {ts.magnitude:.0f} kN, [{ts.min_position:.0f}–{pmax:.0f}m]")

    # Validate
    errors = validate_model(model)
    if errors:
        print("❌ Validation errors:")
        for e in errors:
            print(f"   • {e}")
        sys.exit(1)
    print("   ✅ Validation passed")

    # Run analysis
    print("🔧 Running analysis pipeline...")
    result = run_analysis(model)

    tip_mm = result.tip_delta * 1000
    limit_250 = model.jib_length * 1000 / 250

    print(f"   V(0) = {result.reaction_V:.1f} kN, M(0) = {result.reaction_M:.1f} kN·m")
    print(f"   Max |V|:  {result.max_V:.1f} kN  @ X={result.max_V_pos:.1f} m")
    print(f"   Max M:    {result.max_M:.1f} kN·m  @ X={result.max_M_pos:.1f} m")
    print(f"   Max σ:    {result.max_sigma:.1f} MPa  @ X={result.max_sigma_pos:.1f} m")
    print(f"   Tip δ:    {tip_mm:.1f} mm  (L/250={limit_250:.0f} mm) {'✅' if tip_mm < limit_250 else '⚠️'}")

    if has_truss:
        print(f"   Max upper chord:   {result.max_F_upper:.1f} kN (compression)")
        print(f"   Max lower chord:   {result.max_F_lower:.1f} kN (tension)")
        print(f"   Max comp diagonal: {result.max_F_comp_diag:.1f} kN")
        print(f"   Max tens diagonal: {result.max_F_tens_diag:.1f} kN")

    # Trolley sweep
    sweep_result = None
    if model.trolley_sweep:
        print("🔄 Sweeping trolley positions...")
        sweep_result = run_sweep(model)
        print(f"   Worst: X={sweep_result.worst_position:.1f} m, M={sweep_result.worst_moment:.1f} kN·m, δ={sweep_result.worst_deflection*1000:.1f} mm")

    # Report
    print(f"📄 Generating report: {args.output}")
    html = generate_html(model, result, sweep_result)
    Path(args.output).write_text(html)
    print(f"   ✅ Saved")

    if not args.no_browser:
        import webbrowser
        webbrowser.open(f'file://{Path(args.output).absolute()}')

    print("Done! 🏗️")


if __name__ == '__main__':
    main()
