"""CSV export module."""

import csv
from pathlib import Path


def export_results_csv(model, result, output_path: str):
    """Export analysis results to CSV files.
    
    Creates:
    - sections.csv: section properties
    - loads.csv: applied loads
    - results.csv: summary results
    - forces_at_sections.csv: forces at section starts
    """
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Sections CSV
    with open(output_dir / 'sections.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Section', 'X_Start', 'X_End', 'Length', 'Weight_kN_m', 'Area', 'I_z', 'Height', 'Yield_MPa', 'Wind_Area'])
        for sec in model.sections:
            writer.writerow([sec.name, sec.start, sec.end, sec.length, sec.weight_per_length, 
                           sec.area, sec.moment_of_inertia, sec.height, sec.yield_strength, sec.wind_area])
    
    # Loads CSV
    with open(output_dir / 'loads.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Type', 'Name', 'Position', 'Start', 'End', 'Magnitude', 'Wind_Area'])
        for pl in model.point_loads:
            writer.writerow(['Point', pl.name, pl.position, '', '', pl.magnitude, pl.wind_area])
        for udl in model.udls:
            writer.writerow(['UDL', udl.name, '', udl.start, udl.end, udl.magnitude, udl.wind_area])
    
    # Results summary CSV
    with open(output_dir / 'results.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Metric', 'Value', 'Unit', 'At_X'])
        writer.writerow(['Root_Shear_V', result.reaction_V, 'kN', '0'])
        writer.writerow(['Root_Moment_M', result.reaction_M, 'kN·m', '0'])
        writer.writerow(['Max_Shear', result.max_V, 'kN', result.max_V_pos])
        writer.writerow(['Max_Moment', result.max_M, 'kN·m', result.max_M_pos])
        writer.writerow(['Max_Stress', result.max_sigma, 'MPa', result.max_sigma_pos])
        writer.writerow(['Max_Utilization', f'{result.max_utilization:.4f}', '', result.max_utilization_pos])
        writer.writerow(['Tip_Deflection', result.tip_delta * 1000, 'mm', model.jib_length])
        writer.writerow(['Max_Upper_Chord', result.max_F_upper, 'kN', ''])
        writer.writerow(['Max_Lower_Chord', result.max_F_lower, 'kN', ''])
        writer.writerow(['Max_Comp_Diagonal', result.max_F_comp_diag, 'kN', ''])
        writer.writerow(['Max_Tens_Diagonal', result.max_F_tens_diag, 'kN', ''])
    
    # Forces at sections CSV
    with open(output_dir / 'forces_at_sections.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Section', 'X', 'Upper_Chord_kN', 'Lower_Chord_kN', 'Comp_Diag_kN', 'Tens_Diag_kN', 'Neut_Diag_kN'])
        for sf in result.section_forces_at_start:
            writer.writerow([sf['section'], sf['x'], sf['upper_chord'], sf['lower_chord'], 
                           sf['comp_diag'], sf['tens_diag'], sf['neut_diag']])
    
    # Utilization CSV
    if result.section_utilization:
        with open(output_dir / 'utilization.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Section', 'X', 'Stress_MPa', 'Yield_MPa', 'Utilization'])
            for u in result.section_utilization:
                writer.writerow([u['section'], u['x'], u['sigma'], u['yield_strength'], u['utilization']])
    
    return [str(output_dir / f) for f in ['sections.csv', 'loads.csv', 'results.csv', 'forces_at_sections.csv', 'utilization.csv']]


def export_reactions(model, result, file_path: str):
    """Export reaction forces to CSV."""
    from models import compute_reactions
    
    reactions = compute_reactions(model, result.V, result.M)
    
    with open(file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Position (m)', 'Shear (kN)', 'Moment (kN·m)'])
        for r in reactions:
            writer.writerow([r.x, r.shear, r.moment])
    
    print(f"✅ Exported reactions to {file_path}")
