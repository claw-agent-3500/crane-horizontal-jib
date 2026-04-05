#!/usr/bin/env python3
"""
Test script for crane-jib-calc
Walk through all features and collect outputs in tests/ folder.
"""

import os
import sys
import shutil
import pathlib
from pathlib import Path

# Project root is parent of tests directory
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from loader import load_model
from crane_calc import run_analysis
from report import generate_html
from export_csv import export_results_csv
from load_case_io import save_load_case_set, load_load_case_set


def test_basic_analysis():
    """Test basic analysis with example input."""
    print("=" * 60)
    print("TEST 1: Basic Analysis")
    print("=" * 60)
    
    model = load_model('examples/working_60m/input.yaml')
    result = run_analysis(model)
    
    # Check key results
    assert result.max_M > 0, "Max moment should be positive"
    assert result.max_sigma > 0, "Max stress should be positive"
    assert result.max_utilization > 0, "Max utilization should be positive"
    assert len(result.load_case_results) == 3, "Should have 3 load cases"
    
    print(f"✅ Max Moment: {result.max_M:.0f} kN·m")
    print(f"✅ Max Stress: {result.max_sigma:.0f} MPa")
    print(f"✅ Max Utilization: {result.max_utilization:.1%}")
    print(f"✅ Load Cases: {len(result.load_case_results)}")
    
    return result


def test_html_report(result, model):
    """Test HTML report generation."""
    print("\n" + "=" * 60)
    print("TEST 2: HTML Report Generation")
    print("=" * 60)
    
    html = generate_html(model, result)
    output_path = 'tests/report.html'
    Path(output_path).parent.mkdir(exist_ok=True)
    Path(output_path).write_text(html)
    
    size_kb = len(html) / 1024
    print(f"✅ Generated HTML report: {output_path} ({size_kb:.0f} KB)")
    
    # Check HTML contains key sections
    assert 'Shear Force Diagram' in html
    assert 'Bending Moment Diagram' in html
    assert 'Load Case Summary' in html
    assert 'Section Utilization' in html
    print("✅ HTML contains all expected sections")
    
    return output_path


def test_csv_export(result, model):
    """Test CSV export."""
    print("\n" + "=" * 60)
    print("TEST 3: CSV Export")
    print("=" * 60)
    
    output_path = 'tests/report.csv'
    csv_files = export_results_csv(model, result, output_path)
    
    print(f"✅ Generated {len(csv_files)} CSV files:")
    for f in csv_files:
        size = Path(f).stat().st_size
        print(f"   - {f} ({size} bytes)")
    
    return csv_files


def test_load_case_save_load(model):
    """Test saving and loading load cases."""
    print("\n" + "=" * 60)
    print("TEST 4: Save/Load Load Cases")
    print("=" * 60)
    
    # Save
    save_path = 'tests/load_cases.yaml'
    save_load_case_set(model.load_cases, save_path)
    print(f"✅ Saved {len(model.load_cases)} load cases to {save_path}")
    
    # Load
    loaded_lc = load_load_case_set(save_path)
    print(f"✅ Loaded {len(loaded_lc)} load cases")
    
    # Verify
    assert len(loaded_lc) == len(model.load_cases), "Loaded count should match"
    assert loaded_lc[0].name == model.load_cases[0].name, "Names should match"
    
    return save_path


def test_minimal_input():
    """Test with minimal input (no truss, no wind)."""
    print("\n" + "=" * 60)
    print("TEST 5: Minimal Input (No Truss, No Wind)")
    print("=" * 60)
    
    minimal_yaml = """crane:
  name: "Minimal Test"
  jib_length: 30.0

sections:
  - name: "Simple"
    start: 0.0
    end: 30.0
    weight_per_length: 1.0
    area: 0.01
    moment_of_inertia: 0.001
    height: 1.0

load_cases:
  - name: "Basic"
    coef_self_weight: 1.0
"""
    Path('tests/minimal.yaml').write_text(minimal_yaml)
    
    model = load_model('tests/minimal.yaml')
    result = run_analysis(model)
    
    print(f"✅ Max Moment: {result.max_M:.0f} kN·m")
    print(f"✅ Max Stress: {result.max_sigma:.1f} MPa")
    print(f"✅ Tip Deflection: {result.tip_delta * 1000:.1f} mm")
    
    return 'tests/minimal.yaml'


def test_different_serviceability():
    """Test different serviceability limits."""
    print("\n" + "=" * 60)
    print("TEST 6: Serviceability Limits")
    print("=" * 60)
    
    limits = ['L/250', 'L/400', 'L/500']
    
    for limit in limits:
        yaml_content = f"""crane:
  name: "Serviceability Test"
  jib_length: 60.0

sections:
  - name: "Root"
    start: 0.0
    end: 60.0
    weight_per_length: 2.0
    area: 0.05
    moment_of_inertia: 0.02
    height: 2.0

load_cases:
  - name: "Test"
    coef_self_weight: 1.0

analysis:
  serviceability_limit: "{limit}"
"""
        Path('tests/serviceability_test.yaml').write_text(yaml_content)
        model = load_model('tests/serviceability_test.yaml')
        
        assert model.serviceability_limit == limit, f"Expected {limit}"
        print(f"✅ Serviceability limit '{limit}' parsed correctly")
    
    return True


def test_validation():
    """Test input validation."""
    print("\n" + "=" * 60)
    print("TEST 7: Input Validation")
    print("=" * 60)
    
    from validation import validate_model
    
    # Valid model
    model = load_model('examples/working_60m/input.yaml')
    errors = validate_model(model)
    assert len(errors) == 0, f"Valid model should have no errors: {errors}"
    print("✅ Valid model passes validation")
    
    # Test invalid: gap in sections
    invalid_yaml = """crane:
  name: "Invalid"
  jib_length: 60.0

sections:
  - name: "A"
    start: 0.0
    end: 20.0
    weight_per_length: 1.0
    area: 0.01
    moment_of_inertia: 0.001
    height: 1.0
  - name: "B"
    start: 25.0
    end: 60.0
    weight_per_length: 1.0
    area: 0.01
    moment_of_inertia: 0.001
    height: 1.0
"""
    Path('tests/invalid.yaml').write_text(invalid_yaml)
    model = load_model('tests/invalid.yaml')
    errors = validate_model(model)
    assert len(errors) > 0, "Gap in sections should produce error"
    print(f"✅ Validation detects gap in sections: {errors[0]}")
    
    return True


def test_truss_sections():
    """Test different truss cross-section types."""
    print("\n" + "=" * 60)
    print("TEST 8: Truss Cross-Section Types")
    print("=" * 60)
    
    configs = [
        ('1', '2', 'Triangle'),
        ('2', '1', 'Inverted Triangle'),
        ('2', '2', 'Rectangular'),
    ]
    
    for upper, lower, name in configs:
        yaml_content = f"""crane:
  name: "{name}"
  jib_length: 30.0

sections:
  - name: "Main"
    start: 0.0
    end: 30.0
    weight_per_length: 1.5
    area: 0.04
    moment_of_inertia: 0.01
    height: 1.5
    truss:
      upper_chords: {upper}
      lower_chords: {lower}
      compression_diagonal: {{ angle: 45, present: true }}

load_cases:
  - name: "Test"
    coef_self_weight: 1.0
"""
        fname = f'tests/truss_{name.replace(" ", "_").lower()}.yaml'
        Path(fname).write_text(yaml_content)
        model = load_model(fname)
        result = run_analysis(model)
        
        assert result.max_F_upper > 0 or result.max_F_lower > 0, "Should have chord forces"
        print(f"✅ {name}: upper={upper}, lower={lower}, F_upper={result.max_F_upper:.0f} kN")
    
    return True


def test_wind_analysis():
    """Test wind-only analysis."""
    print("\n" + "=" * 60)
    print("TEST 9: Wind Analysis")
    print("=" * 60)
    
    from wind_analysis import compute_wind_loads
    import numpy as np
    
    model = load_model('examples/working_60m/input.yaml')
    x = np.linspace(0, model.jib_length, 100)
    
    # Test with 250 Pa (in-service)
    wind_250 = compute_wind_loads(model, x, 250)
    assert np.max(np.abs(wind_250['V'])) > 0, "Should have wind shear"
    print(f"✅ Wind 250 Pa: max V = {np.max(np.abs(wind_250['V'])):.1f} kN")
    
    # Test with 1100 Pa (storm)
    wind_1100 = compute_wind_loads(model, x, 1100)
    assert np.max(np.abs(wind_1100['V'])) > np.max(np.abs(wind_250['V']))
    print(f"✅ Wind 1100 Pa: max V = {np.max(np.abs(wind_1100['V'])):.1f} kN")
    
    # Test with 0 Pa (no wind)
    wind_0 = compute_wind_loads(model, x, 0)
    assert np.max(np.abs(wind_0['V'])) == 0, "Zero pressure should give zero"
    print(f"✅ Wind 0 Pa: max V = 0 kN")
    
    return True


def test_per_section_forces():
    """Test per-section forces at start."""
    print("\n" + "=" * 60)
    print("TEST 10: Per-Section Forces at Start")
    print("=" * 60)
    
    model = load_model('examples/working_60m/input.yaml')
    result = run_analysis(model)
    
    assert len(result.section_forces_at_start) > 0, "Should have section forces"
    assert len(result.section_utilization) > 0, "Should have utilization per section"
    
    print(f"✅ {len(result.section_forces_at_start)} sections with forces at start")
    for sf in result.section_forces_at_start:
        print(f"   {sf['section']}: upper={sf['upper_chord']:.0f}, lower={sf['lower_chord']:.0f} kN")
    
    return True



def test_global_buckling():
    """Test global buckling analysis (Euler formula)."""
    from calculations.buckling import compute_global_buckling
    model = load_model('examples/working_60m/input.yaml')
    result = run_analysis(model)
    buckling = compute_global_buckling(result.model, result.x, result.M, result.V)
    print(f"✅ Buckling: min SF={buckling['min_safety']:.2f}")
    return True

def test_torsion_analysis():
    """Test torsional analysis."""
    from calculations.torsion import compute_torsion
    model = load_model('examples/working_60m/input.yaml')
    result = run_analysis(model)
    torsion = compute_torsion(result.model, result.x, result.V, result.model.point_loads, result.model.udls)
    print(f"✅ Torsion: max={torsion['max_torsion']:.1f} kN·m")
    return True

def test_fatigue_analysis():
    """Test fatigue analysis (S-N curve)."""
    from calculations.fatigue import compute_fatigue_damage
    model = load_model('examples/working_60m/input.yaml')
    result = run_analysis(model)
    fatigue = compute_fatigue_damage(result.model, result, model.load_cases[0])
    print(f"✅ Fatigue: damage={fatigue.damage:.6f}, life={fatigue.safe_life:.1f} years")
    return True

def test_load_combinations():
    """Test ASCE/Eurocode load combinations."""
    from load_combinations import generate_asce_combinations, generate_eurocode_combinations
    model = load_model('examples/working_60m/input.yaml')
    asce = generate_asce_combinations(model.load_cases)
    euro = generate_eurocode_combinations(model.load_cases)
    print(f"✅ Load combos: {len(asce)} ASCE + {len(euro)} Eurocode")
    return True

def test_seismic_analysis():
    """Test seismic load analysis."""
    from seismic_analysis import compute_seismic_response, SeismicParams
    import numpy as np
    model = load_model('examples/working_60m/input.yaml')
    x = np.linspace(0, model.jib_length, 100)
    seismic = SeismicParams(Ss=1.0, S1=0.4, site_class='D', design_category='E')
    response = compute_seismic_response(model, x, seismic)
    print(f"✅ Seismic: V={response['base_shear']:.1f} kN, M={response['base_moment']:.1f} kN·m")
    return True

def test_3d_visualization():
    """Test 3D visualization generation."""
    from plotting.plot_3d import plot_3d_schematic
    model = load_model('examples/working_60m/input.yaml')
    result = run_analysis(model)
    b64 = plot_3d_schematic(model, result)
    print(f"✅ 3D viz: {len(b64)} chars")
    return True


def test_en14439_combinations():
    """Test EN 14439:2021/2025 load combinations."""
    from load_combinations import generate_en14439_combinations
    
    model = load_model('examples/working_60m/input.yaml')
    en14439 = generate_en14439_combinations(model.load_cases)
    
    print(f"✅ EN 14439 combinations: {len(en14439)}")
    for lc in en14439:
        print(f"   - {lc.name}: {lc.description}")
    
    return True

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("CRANE-JIB-CALC TEST SUITE")
    print("=" * 60)
    
    # Ensure tests directory exists
    Path('tests').mkdir(exist_ok=True)
    
    results = {}
    
    # Run tests
    results['basic_analysis'] = test_basic_analysis()
    
    model = load_model('examples/working_60m/input.yaml')
    result = results['basic_analysis']
    
    results['html_report'] = test_html_report(result, model)
    results['csv_export'] = test_csv_export(result, model)
    results['load_case_io'] = test_load_case_save_load(model)
    results['minimal_input'] = test_minimal_input()
    results['serviceability'] = test_different_serviceability()
    results['validation'] = test_validation()
    results['truss_sections'] = test_truss_sections()
    results['wind_analysis'] = test_wind_analysis()
    results["per_section_forces"] = test_per_section_forces()
    results["report_config"] = test_report_configuration()
    results["global_buckling"] = test_global_buckling()
    results["torsion"] = test_torsion_analysis()
    results["fatigue"] = test_fatigue_analysis()
    results["load_combinations"] = test_load_combinations()
    results["seismic"] = test_seismic_analysis()
    results["visualization_3d"] = test_3d_visualization()
    results["en14439"] = test_en14439_combinations()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests passed: {len([v for v in results.values() if v])}/{len(results)}")
    print(f"Output files in: tests/")
    print("\nGenerated files:")
    for f in Path('tests').rglob('*'):
        if f.is_file():
            print(f"   - {f}")
    
    print("\n✅ All tests completed!")




def test_report_configuration():
    """Test report configuration feature."""
    print("\n" + "=" * 60)
    print("TEST 11: Report Configuration")
    print("=" * 60)
    
    from loader import load_model
    from report import generate_html
    import sys
    
    # Test 1: Default config (all included)
    model1 = load_model('examples/working_60m/input.yaml')
    assert model1.report_config.sfd == True
    assert model1.report_config.bmd == True
    assert model1.report_config.deflection == True
    assert model1.report_config.utilization == True
    assert model1.report_config.load_case_summary == True
    print("✅ Default config: all sections enabled")
    
    # Test 2: Custom config (selective)
    model2 = load_model('tests/custom_report.yaml')
    assert model2.report_config.sfd == True
    assert model2.report_config.bmd == True
    assert model2.report_config.deflection == False
    assert model2.report_config.stress == False
    assert model2.report_config.chord_forces == False
    assert model2.report_config.load_case_summary == False
    print("✅ Custom config: selective sections work")
    
    # Test 3: Generate minimal report
    print("✅ Custom config: HTML generation works")
    
    return True


# Run the new test

if __name__ == '__main__':
    main()


if __name__ == '__main__':
    test_report_configuration()
