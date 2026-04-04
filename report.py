"""HTML report generator."""
from plotting.utilization_plot import plot_utilization
from plotting.wind_plot import plot_wind_diagram

from plotting.schematic import plot_schematic
from plotting.sfd import plot_sfd
from plotting.bmd import plot_bmd
from plotting.deflection_plot import plot_deflection
from plotting.stress_plot import plot_stress
from plotting.chord_plot import plot_chord_forces
from plotting.diagonal_plot import plot_diagonal_forces

from calculations.beam import get_section_at


def generate_html(model, result, sweep_result=None) -> str:
    schematic_b64 = plot_schematic(model)
    sfd_b64 = plot_sfd(result)
    bmd_b64 = plot_bmd(result)
    deflection_b64 = plot_deflection(result)
    utilization_b64 = plot_utilization(result)
    # Wind diagram - use max wind_pressure from load cases
    max_wind_pressure = max([lc.wind_pressure for lc in model.load_cases], default=0)
    wind_b64 = plot_wind_diagram(model, max_wind_pressure, result.x)
    stress_b64 = plot_stress(result)
    chord_b64 = plot_chord_forces(result)
    diag_b64 = plot_diagonal_forces(result)

    sec_at_max = get_section_at(model.sections, result.max_sigma_pos)
    sec_name = sec_at_max.name if sec_at_max else 'N/A'

    L = model.jib_length
    limit = _parse_serviceability_limit(model.serviceability_limit, L)
    tip_mm = result.tip_delta * 1000
    defl_status = '✅' if tip_mm < limit else '⚠️'

    trolley_info = ''
    if model.trolley:
        t = model.trolley
        trolley_info = f' · Trolley: {t.magnitude:.0f} kN [{t.min_position:.0f}–{t.max_position:.0f} m]'
    envelope_label = ' (envelope)' if model.trolley else ''

    # Section table
    section_rows = ''
    for sec in model.sections:
        truss_info = ''
        if sec.truss:
            tr = sec.truss
            diags = []
            if tr.compression_diagonal and tr.compression_diagonal.present:
                diags.append(f'C:{tr.compression_diagonal.angle}°')
            if tr.tension_diagonal and tr.tension_diagonal.present:
                diags.append(f'T:{tr.tension_diagonal.angle}°')
            if tr.neutral_diagonal and tr.neutral_diagonal.present:
                diags.append(f'N:{tr.neutral_diagonal.angle}°')
            truss_info = f'{tr.upper_chords}U+{tr.lower_chords}L ' + ' '.join(diags) if diags else f'{tr.upper_chords}U+{tr.lower_chords}L'
        section_rows += f'''
        <tr>
            <td>{sec.name}</td>
            <td>{sec.start:.1f} – {sec.end:.1f}</td>
            <td>{sec.length:.1f}</td>
            <td>{sec.weight_per_length:.2f}</td>
            <td>{sec.area:.4f}</td>
            <td>{sec.moment_of_inertia:.4f}</td>
            <td>{sec.height:.2f}</td>
            <td>{truss_info or '—'}</td>
        </tr>'''

    # Loads table
    load_rows = ''
    for sec in model.sections:
        load_rows += f'<tr><td><span class="tag">UDL</span> {sec.name} (self-weight)</td><td>{sec.start:.1f} – {sec.end:.1f} m</td><td>{sec.weight_per_length:.2f} kN/m</td><td>−Y</td></tr>'
    for udl in model.udls:
        load_rows += f'<tr><td><span class="tag">UDL</span> {udl.name}</td><td>{udl.start:.1f} – {udl.end:.1f} m</td><td>{udl.magnitude:.2f} kN/m</td><td>−Y</td></tr>'
    for pl in model.point_loads:
        load_rows += f'<tr><td><span class="tag">Point</span> {pl.name}</td><td>X = {pl.position:.1f} m</td><td>{pl.magnitude:.1f} kN</td><td>−Y</td></tr>'

    # Truss member force summary
    truss_summary = ''
    has_truss = any(s.truss for s in model.sections)
    if has_truss:
        truss_summary = f'''
    <div class="card">
        <h2>🔧 Truss Member Forces — Summary (Envelope)</h2>
        <div class="stats">
            <div class="stat">
                <div class="stat-label">Max Upper Chord (comp)</div>
                <div class="stat-value" style="color:#f38ba8">{result.max_F_upper:.1f} kN</div>
            </div>
            <div class="stat">
                <div class="stat-label">Max Lower Chord (tens)</div>
                <div class="stat-value" style="color:#89b4fa">{result.max_F_lower:.1f} kN</div>
            </div>
            <div class="stat">
                <div class="stat-label">Max Compression Diagonal</div>
                <div class="stat-value" style="color:#f38ba8">{result.max_F_comp_diag:.1f} kN</div>
            </div>
            <div class="stat">
                <div class="stat-label">Max Tension Diagonal</div>
                <div class="stat-value" style="color:#a6e3a1">{result.max_F_tens_diag:.1f} kN</div>
            </div>
            <div class="stat">
                <div class="stat-label">Max Utilization</div>
                <div class="stat-value" style="color:#{'#f38ba8' if result.max_utilization > 0.9 else '#f9e2af' if result.max_utilization > 0.7 else '#a6e3a1'}">{result.max_utilization:.1%}</div>
                <div class="stat-label">@ X = {result.max_utilization_pos:.1f} m</div>
            </div>
        </div>
    </div>'''

    # Utilization table
    util_table = ''
    if result.section_utilization:
        for u in result.section_utilization:
            status = '✅' if u['utilization'] < 0.7 else ('⚠️' if u['utilization'] < 0.9 else '❌')
            util_table += f'''
        <tr>
            <td>{u['section']}</td>
            <td>{u['x']:.1f}</td>
            <td>{u['sigma']:.1f}</td>
            <td>{u['yield_strength']:.0f}</td>
            <td class="{'util-ok' if u['utilization'] < 0.7 else 'util-warn' if u['utilization'] < 0.9 else 'util-fail'}">{u['utilization']:.1%} {status}</td>
        </tr>'''

    util_html = ''
    if util_table:
        util_html = f'''
    <div class="card">
        <h2>🔧 Section Utilization — σ / f_y</h2>
        <table>
            <thead>
                <tr>
                    <th>Section</th>
                    <th>X (m)</th>
                    <th>σ (MPa)</th>
                    <th>f_y (MPa)</th>
                    <th>Utilization</th>
                </tr>
            </thead>
            <tbody>{util_table}
            </tbody>
        </table>
    </div>'''

    # Load case summary table
    lc_table = ''
    if result.load_case_results:
        for lc in result.load_case_results:
            status = '✅' if lc['max_utilization'] < 0.7 else ('⚠️' if lc['max_utilization'] < 0.9 else '❌')
            lc_table += f'''
        <tr>
            <td>{lc['name']}</td>
            <td>{lc['max_V']:.1f}</td>
            <td>{lc['max_M']:.1f}</td>
            <td>{lc['max_sigma']:.1f}</td>
            <td class="{'util-ok' if lc['max_utilization'] < 0.7 else 'util-warn' if lc['max_utilization'] < 0.9 else 'util-fail'}">{lc['max_utilization']:.1%}</td>
            <td>{lc['tip_delta']*1000:.1f}</td>
            <td>{lc['wind_pressure']:.0f}</td>
        </tr>'''

    lc_summary_html = ''
    if lc_table:
        lc_summary_html = f'''
    <div class="card">
        <h2>📋 Load Case Summary</h2>
        <table>
            <thead>
                <tr>
                    <th>Load Case</th>
                    <th>Max V (kN)</th>
                    <th>Max M (kN·m)</th>
                    <th>Max σ (MPa)</th>
                    <th>Max Utilization</th>
                    <th>Tip δ (mm)</th>
                    <th>Wind (Pa)</th>
                </tr>
            </thead>
            <tbody>{lc_table}
            </tbody>
        </table>
    </div>'''

    # Per-section forces at section start (pivot point for design)
    section_forces_table = ''
    if result.section_forces_at_start:
        for sf in result.section_forces_at_start:
            upper_sign = 'comp' if sf['upper_chord'] >= 0 else 'tens'
            lower_sign = 'tens' if sf['lower_chord'] <= 0 else 'comp'
            section_forces_table += f'''
        <tr>
            <td>{sf['section']}</td>
            <td>{sf['x']:.1f}</td>
            <td class="force-comp">{sf['upper_chord']:.1f}</td>
            <td class="force-tens">{sf['lower_chord']:.1f}</td>
            <td>{sf['comp_diag']:.1f}</td>
            <td>{sf['tens_diag']:.1f}</td>
            <td>{sf['neut_diag']:.1f}</td>
        </tr>'''

    section_forces_html = ''
    if section_forces_table:
        section_forces_html = f'''
    <div class="card">
        <h2>🔧 Forces at Section Start (Worst Case Position)</h2>
        <p style="color:#6c7086;font-size:0.8rem;margin-bottom:1rem">
            Forces at each section's start X (pivot point for design). Upper chord in tension when M &lt; 0 (sagging), compression when M &gt; 0 (hogging).
        </p>
        <table>
            <thead>
                <tr>
                    <th>Section</th>
                    <th>X (m)</th>
                    <th>Upper Chord (kN)<br/>(+ comp, − tens)</th>
                    <th>Lower Chord (kN)<br/>(+ comp, − tens)</th>
                    <th>Comp Diag (kN)</th>
                    <th>Tens Diag (kN)</th>
                    <th>Neut Diag (kN)</th>
                </tr>
            </thead>
            <tbody>{section_forces_table}
            </tbody>
        </table>
    </div>'''

    # Trolley sweep
    sweep_html = ''
    if sweep_result:
        sweep_b64 = plot_sweep(sweep_result)
        sweep_html = f'''
    <div class="card">
        <h2>🔄 Trolley Position Sweep</h2>
        <div class="stats">
            <div class="stat"><div class="stat-label">Worst Position</div><div class="stat-value">{sweep_result.worst_position:.1f} m</div></div>
            <div class="stat"><div class="stat-label">Max Root Moment</div><div class="stat-value moment">{sweep_result.worst_moment:.1f} kN·m</div></div>
            <div class="stat"><div class="stat-label">Max Root Shear</div><div class="stat-value shear">{sweep_result.worst_shear:.1f} kN</div></div>
            <div class="stat"><div class="stat-label">Max Tip Deflection</div><div class="stat-value" style="color:#cba6f7">{sweep_result.worst_deflection * 1000:.1f} mm</div></div>
        </div>
        <img src="data:image/png;base64,{sweep_b64}" alt="Trolley Sweep" />
    </div>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tower Crane Jib Analysis — {model.name}</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #11111b; color: #cdd6f4; padding: 2rem; line-height: 1.6; }}
    .container {{ max-width: 1100px; margin: 0 auto; }}
    h1 {{ font-size: 1.8rem; margin-bottom: 0.5rem; background: linear-gradient(135deg, #f38ba8, #a6e3a1); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    .subtitle {{ color: #6c7086; margin-bottom: 2rem; font-size: 0.9rem; }}
    .coord-info {{ background: #181825; border: 1px solid #313244; border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 1.5rem; font-size: 0.8rem; color: #a6adc8; }}
    .coord-info span {{ color: #89b4fa; font-weight: 600; }}
    .card {{ background: #1e1e2e; border: 1px solid #313244; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; }}
    .card h2 {{ font-size: 1.1rem; margin-bottom: 1rem; }}
    img {{ width: 100%; border-radius: 8px; margin-top: 1rem; }}
    .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 1rem; }}
    .stat {{ background: #181825; border: 1px solid #313244; border-radius: 8px; padding: 1rem; text-align: center; }}
    .force-comp {{ color: #f38ba8; }}
    .force-tens {{ color: #89b4fa; }}
    .util-ok {{ color: #a6e3a1; }}
    .util-warn {{ color: #f9e2af; }}
    .util-fail {{ color: #f38ba8; }}
    .stat-label {{ font-size: 0.75rem; color: #6c7086; margin-bottom: 0.3rem; }}
    .stat-value {{ font-size: 1.3rem; font-weight: 700; }}
    .stat-value.shear {{ color: #f38ba8; }}
    .stat-value.moment {{ color: #a6e3a1; }}
    .stat-value.stress {{ color: #89b4fa; }}
    .stat-value.deflection {{ color: #cba6f7; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-top: 0.5rem; }}
    th {{ text-align: left; padding: 0.6rem 0.8rem; border-bottom: 2px solid #313244; color: #6c7086; font-weight: 600; font-size: 0.75rem; text-transform: uppercase; }}
    td {{ padding: 0.5rem 0.8rem; border-bottom: 1px solid #262637; }}
    tr:hover {{ background: #181825; }}
    .footer {{ text-align: center; color: #45475a; font-size: 0.75rem; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #313244; }}
    .tag {{ display: inline-block; background: #313244; color: #a6adc8; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.65rem; margin-right: 0.3rem; }}
</style>
</head>
<body>
<div class="container">
    <h1>🏗️ Tower Crane Jib Analysis</h1>
    <p class="subtitle">{model.name} — {len(model.sections)} sections, L = {model.jib_length:.0f} m, E = {model.youngs_modulus / 1e6:.0f} GPa{trolley_info}</p>
    <div class="coord-info">Coordinate system: <span>X</span> = longitudinal · <span>Y</span> = vertical (up) · <span>Z</span> = width{envelope_label}</div>

    <div class="card">
        <h2>📊 Summary</h2>
        <div class="stats">
            <div class="stat"><div class="stat-label">Root Shear V(0)</div><div class="stat-value shear">{result.reaction_V:.1f} kN</div></div>
            <div class="stat"><div class="stat-label">Root Moment M(0)</div><div class="stat-value moment">{result.reaction_M:.1f} kN·m</div></div>
            <div class="stat"><div class="stat-label">Max |V|</div><div class="stat-value shear">{result.max_V:.1f} kN</div><div class="stat-label">@ X={result.max_V_pos:.1f} m</div></div>
            <div class="stat"><div class="stat-label">Max M</div><div class="stat-value moment">{result.max_M:.1f} kN·m</div><div class="stat-label">@ X={result.max_M_pos:.1f} m</div></div>
            <div class="stat"><div class="stat-label">Max σ</div><div class="stat-value stress">{result.max_sigma:.1f} MPa</div><div class="stat-label">@ X={result.max_sigma_pos:.1f} m</div></div>
            <div class="stat"><div class="stat-label">Tip Deflection δ</div><div class="stat-value deflection">{tip_mm:.1f} mm</div><div class="stat-label">{defl_status} {model.serviceability_limit}={limit:.0f} mm</div></div>
        </div>
    </div>

    <div class="card">
        <h2>🔧 Jib Configuration (X-Y Side View)</h2>
        <img src="data:image/png;base64,{schematic_b64}" alt="Schematic" />
        <table><thead><tr><th>Section</th><th>X Range (m)</th><th>Length</th><th>w (kN/m)</th><th>A (m²)</th><th>I_z (m⁴)</th><th>h (m)</th><th>Truss</th></tr></thead>
        <tbody>{section_rows}</tbody></table>
    </div>

    <div class="card">
        <h2>⬇️ Applied Loads (−Y direction)</h2>
        <table><thead><tr><th>Load</th><th>X Position</th><th>Magnitude</th><th>Dir</th></tr></thead>
        <tbody>{load_rows}</tbody></table>
    </div>

    <div class="card"><h2>📈 Shear Force Diagram — V(x)</h2><img src="data:image/png;base64,{sfd_b64}" alt="SFD" /></div>
    <div class="card"><h2>📈 Bending Moment Diagram — M(x)</h2><img src="data:image/png;base64,{bmd_b64}" alt="BMD" /></div>
    <div class="card"><h2>📈 Deflection Curve — δ(x)</h2><img src="data:image/png;base64,{deflection_b64}" alt="Deflection" /></div>
    <div class="card"><h2>📈 Wind Loads Diagram</h2><img src="data:image/png;base64,{wind_b64}" alt="Wind" /></div>

    <div class="card"><h2>📈 Utilization Ratio Plot</h2><img src="data:image/png;base64,{utilization_b64}" alt="Utilization" /></div>

    <div class="card"><h2>📈 Stress Distribution</h2><img src="data:image/png;base64,{stress_b64}" alt="Stress" /></div>

    {truss_summary}
    {section_forces_html}
    {util_html}
    {lc_summary_html}
    <div class="card"><h2>📈 Chord Forces</h2><img src="data:image/png;base64,{chord_b64}" alt="Chord Forces" /></div>
    <div class="card"><h2>📈 Diagonal Forces</h2><img src="data:image/png;base64,{diag_b64}" alt="Diagonal Forces" /></div>

    {sweep_html}

    <div class="footer">
        <span class="tag">crane-jib-calc v0.4.0</span>
        <span class="tag">modular</span>
        <span class="tag">cantilever</span>
        <span class="tag">truss members</span>
    </div>
</div>
</body>
</html>'''


def _parse_serviceability_limit(limit_str: str, jib_length: float) -> float:
    """Parse serviceability limit string to mm."""
    limit_str = str(limit_str).strip().upper()
    if limit_str.startswith('L/'):
        ratio = int(limit_str.split('/')[1])
        return jib_length * 1000 / ratio
    elif limit_str.isdigit():
        return jib_length * 1000 / int(limit_str)
    else:
        return jib_length * 1000 / 250
