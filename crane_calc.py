#!/usr/bin/env python3
"""
Flat Top Tower Crane Jib Calculator
=====================================
Models a flat-top tower crane jib as a cantilever beam with varying
cross-sections. Computes shear force diagrams (SFD) and bending moment
diagrams (BMD) along the X axis.

Coordinate system:
  X = longitudinal (along jib, root at x=0)
  Y = vertical (positive up, gravity in -Y)
  Z = width (perpendicular to bending plane)

Constraints:
  - Max 5 point loads
  - Max 5 UDLs (in addition to section self-weights)
  - 1 load case only (MVP)

Usage:
    python3 crane_calc.py input.yaml [--output report.html] [--no-browser]
"""

import argparse
import io
import base64
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import yaml


MAX_POINT_LOADS = 5
MAX_UDLS = 5


# ── Data classes ──────────────────────────────────────────────────────────

@dataclass
class Section:
    name: str
    start: float          # X start (m)
    end: float            # X end (m)
    weight_per_length: float  # kN/m (self-weight, acts in -Y)
    area: float           # m² (effective A)
    moment_of_inertia: float  # m⁴ (I about Z axis)
    height: float         # m (Y dimension, depth)

    @property
    def length(self) -> float:
        return self.end - self.start


@dataclass
class PointLoad:
    name: str
    position: float  # X position (m from root)
    magnitude: float  # kN (downward, -Y)


@dataclass
class UDL:
    name: str
    start: float      # X start (m)
    end: float        # X end (m)
    magnitude: float  # kN/m (downward, -Y)


@dataclass
class CraneModel:
    name: str
    jib_length: float
    sections: list[Section]
    point_loads: list[PointLoad]
    udls: list[UDL]
    num_points: int = 500


@dataclass
class AnalysisResult:
    x: np.ndarray
    V: np.ndarray          # Shear force (kN)
    M: np.ndarray          # Bending moment (kN·m)
    sigma: np.ndarray      # Bending stress (MPa)
    tau: np.ndarray         # Shear stress (MPa)
    reaction_V: float      # Root shear (kN)
    reaction_M: float      # Root moment (kN·m)
    max_V: float
    max_V_pos: float
    max_M: float
    max_M_pos: float
    max_sigma: float
    max_sigma_pos: float
    sections: list[Section]
    model: CraneModel


# ── Validation ────────────────────────────────────────────────────────────

def validate_model(model: CraneModel) -> list[str]:
    """Validate model constraints and return list of warnings/errors."""
    errors = []

    if len(model.point_loads) > MAX_POINT_LOADS:
        errors.append(f"Too many point loads: {len(model.point_loads)} (max {MAX_POINT_LOADS})")

    if len(model.udls) > MAX_UDLS:
        errors.append(f"Too many UDLs: {len(model.udls)} (max {MAX_UDLS})")

    # Check sections cover [0, jib_length]
    sorted_secs = sorted(model.sections, key=lambda s: s.start)
    if sorted_secs[0].start != 0:
        errors.append(f"First section starts at {sorted_secs[0].start}, must be 0")
    if sorted_secs[-1].end != model.jib_length:
        errors.append(f"Last section ends at {sorted_secs[-1].end}, must be {model.jib_length}")

    for i in range(len(sorted_secs) - 1):
        gap = sorted_secs[i + 1].start - sorted_secs[i].end
        if abs(gap) > 1e-6:
            errors.append(f"Gap between sections at X={sorted_secs[i].end:.1f} to {sorted_secs[i+1].start:.1f}")

    # Check load positions are within jib
    for pl in model.point_loads:
        if pl.position < 0 or pl.position > model.jib_length:
            errors.append(f"Point load '{pl.name}' at X={pl.position} is outside jib [0, {model.jib_length}]")

    for udl in model.udls:
        if udl.start < 0 or udl.end > model.jib_length:
            errors.append(f"UDL '{udl.name}' [{udl.start}, {udl.end}] is outside jib [0, {model.jib_length}]")
        if udl.start >= udl.end:
            errors.append(f"UDL '{udl.name}' has start >= end")

    return errors


# ── Core calculation ──────────────────────────────────────────────────────

def compute_sfd_bmd(model: CraneModel) -> AnalysisResult:
    """
    Compute SFD and BMD for a cantilever jib (root at X=0, free tip at X=L).

    Coordinate system: X along jib, Y positive up.
    All loads act in -Y (downward).

    Sign convention (right-portion approach):
      V(x) = sum of all downward (-Y) loads to the right of x
             → V is positive for downward loads on the right portion
      M(x) = hogging moment about the cut at x
             → M is positive (tension on top fiber for cantilever)
    """
    L = model.jib_length
    x = np.linspace(0, L, model.num_points)

    V = np.zeros_like(x)
    M = np.zeros_like(x)

    for i, xi in enumerate(x):
        # ── Section self-weights (UDL) to the right of xi ──
        for sec in model.sections:
            if sec.start >= xi:
                length_in = sec.length
                d_start = sec.start - xi
                d_end = sec.end - xi
            elif sec.end > xi:
                length_in = sec.end - xi
                d_start = 0.0
                d_end = sec.end - xi
            else:
                continue

            w = sec.weight_per_length
            V[i] += w * length_in
            M[i] += w * (d_end**2 - d_start**2) / 2.0

        # ── Additional UDLs to the right of xi ──
        for udl in model.udls:
            if udl.start >= xi:
                length_in = udl.end - udl.start
                d_start = udl.start - xi
                d_end = udl.end - xi
            elif udl.end > xi:
                length_in = udl.end - xi
                d_start = 0.0
                d_end = udl.end - xi
            else:
                continue

            w = udl.magnitude
            V[i] += w * length_in
            M[i] += w * (d_end**2 - d_start**2) / 2.0

        # ── Point loads to the right of xi ──
        for pl in model.point_loads:
            if pl.position > xi:
                V[i] += pl.magnitude
                M[i] += pl.magnitude * (pl.position - xi)

    # ── Section properties at each x point ──
    sigma = np.zeros_like(x)
    tau = np.zeros_like(x)
    for j, xj in enumerate(x):
        sec = _get_section_at(model.sections, xj)
        if sec:
            c = sec.height / 2.0  # distance to extreme fiber (Y direction)
            I = sec.moment_of_inertia
            A = sec.area
            # σ = M*c/I (kN·m * m / m⁴ = kN/m²)
            # Convert to MPa: kN/m² / 1000
            sigma[j] = (M[j] * c / I / 1000.0) if I > 0 else 0
            # τ = V/A (average shear stress)
            tau[j] = (V[j] / A / 1000.0) if A > 0 else 0

    max_V_idx = np.argmax(np.abs(V))
    max_M_idx = np.argmax(M)
    max_sigma_idx = np.argmax(sigma)

    return AnalysisResult(
        x=x, V=V, M=M, sigma=sigma, tau=tau,
        reaction_V=V[0], reaction_M=M[0],
        max_V=np.max(np.abs(V)), max_V_pos=x[max_V_idx],
        max_M=np.max(M), max_M_pos=x[max_M_idx],
        max_sigma=np.max(sigma), max_sigma_pos=x[max_sigma_idx],
        sections=model.sections,
        model=model,
    )


def _get_section_at(sections: list[Section], x: float) -> Optional[Section]:
    for sec in sections:
        if sec.start <= x <= sec.end:
            return sec
    return None


# ── Plotting ──────────────────────────────────────────────────────────────

def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='#1e1e2e', edgecolor='none')
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return encoded


def _style_ax(ax, ylabel: str, ycolor: str):
    ax.set_facecolor('#1e1e2e')
    ax.set_xlabel('X — Position along jib (m)', color='#cdd6f4', fontsize=10)
    ax.set_ylabel(ylabel, color=ycolor, fontsize=10)
    ax.axhline(y=0, color='#555', linewidth=0.5, zorder=1)
    ax.tick_params(colors='#aaa', labelsize=8)
    for spine in ('top', 'right'):
        ax.spines[spine].set_visible(False)
    for spine in ('bottom', 'left'):
        ax.spines[spine].set_color('#555')
    ax.grid(True, alpha=0.15, color='#888')


def _section_bands(ax, sections: list[Section], ymin: float, ymax: float):
    colors = ['#2a2a3e', '#252540']
    for i, sec in enumerate(sections):
        ax.axvspan(sec.start, sec.end, alpha=0.3, color=colors[i % 2], zorder=0)
        mid = (sec.start + sec.end) / 2
        ax.text(mid, ymax * 0.92, sec.name, ha='center', va='top',
                fontsize=6, color='#888', alpha=0.8, clip_on=True)


def plot_sfd(result: AnalysisResult) -> str:
    fig, ax = plt.subplots(figsize=(12, 3.5))
    fig.patch.set_facecolor('#1e1e2e')

    _section_bands(ax, result.sections, 0, result.max_V * 1.15)
    ax.fill_between(result.x, result.V, alpha=0.4, color='#f38ba8', zorder=2)
    ax.plot(result.x, result.V, color='#f38ba8', linewidth=1.5, zorder=3)
    _style_ax(ax, 'V(x) Shear Force (kN)', '#f38ba8')
    ax.set_title('Shear Force Diagram (SFD)', color='#cdd6f4', fontsize=12, fontweight='bold')

    ax.annotate(f'Max |V| = {result.max_V:.1f} kN\nat X = {result.max_V_pos:.1f} m',
                xy=(result.max_V_pos, result.V[np.argmin(np.abs(result.x - result.max_V_pos))]),
                xytext=(20, 20), textcoords='offset points',
                color='#f38ba8', fontsize=8,
                arrowprops=dict(arrowstyle='->', color='#f38ba8', lw=0.8))
    return _fig_to_base64(fig)


def plot_bmd(result: AnalysisResult) -> str:
    fig, ax = plt.subplots(figsize=(12, 3.5))
    fig.patch.set_facecolor('#1e1e2e')

    _section_bands(ax, result.sections, 0, result.max_M * 1.15)
    ax.fill_between(result.x, result.M, alpha=0.4, color='#a6e3a1', zorder=2)
    ax.plot(result.x, result.M, color='#a6e3a1', linewidth=1.5, zorder=3)
    _style_ax(ax, 'M(x) Bending Moment (kN·m)', '#a6e3a1')
    ax.set_title('Bending Moment Diagram (BMD)', color='#cdd6f4', fontsize=12, fontweight='bold')

    ax.annotate(f'Max M = {result.max_M:.1f} kN·m\nat X = {result.max_M_pos:.1f} m',
                xy=(result.max_M_pos, result.max_M),
                xytext=(20, -30), textcoords='offset points',
                color='#a6e3a1', fontsize=8,
                arrowprops=dict(arrowstyle='->', color='#a6e3a1', lw=0.8))
    return _fig_to_base64(fig)


def plot_stress(result: AnalysisResult) -> str:
    fig, ax = plt.subplots(figsize=(12, 3.5))
    fig.patch.set_facecolor('#1e1e2e')

    _section_bands(ax, result.sections, 0, result.max_sigma * 1.15)
    ax.fill_between(result.x, result.sigma, alpha=0.3, color='#89b4fa', label='Bending σ', zorder=2)
    ax.plot(result.x, result.sigma, color='#89b4fa', linewidth=1.5, label='Bending σ', zorder=3)
    ax.fill_between(result.x, np.abs(result.tau), alpha=0.2, color='#f9e2af', label='Shear τ (avg)', zorder=2)
    ax.plot(result.x, np.abs(result.tau), color='#f9e2af', linewidth=1.0,
            linestyle='--', label='Shear τ (avg)', zorder=3)
    _style_ax(ax, 'Stress (MPa)', '#cdd6f4')
    ax.set_title('Stress Distribution along X', color='#cdd6f4', fontsize=12, fontweight='bold')
    ax.legend(fontsize=8, facecolor='#1e1e2e', edgecolor='#555',
              labelcolor='#cdd6f4', loc='upper right')
    return _fig_to_base64(fig)


def plot_schematic(model: CraneModel) -> str:
    """Draw a side view (X-Y plane) schematic of the jib."""
    fig, ax = plt.subplots(figsize=(12, 2.5))
    fig.patch.set_facecolor('#1e1e2e')
    ax.set_facecolor('#1e1e2e')

    colors = ['#f38ba8', '#a6e3a1', '#89b4fa', '#f9e2af', '#cba6f7',
              '#94e2d5', '#fab387', '#74c7ec']

    for i, sec in enumerate(model.sections):
        h = sec.height
        color = colors[i % len(colors)]
        rect = plt.Rectangle((sec.start, -h/2), sec.length, h,
                              facecolor=color, alpha=0.25, edgecolor=color,
                              linewidth=1.5, zorder=2)
        ax.add_patch(rect)
        mid = (sec.start + sec.end) / 2
        ax.text(mid, h/2 + 0.15, sec.name, ha='center', va='bottom',
                fontsize=7, color=color, fontweight='bold')
        ax.text(mid, -h/2 - 0.15, f'{sec.weight_per_length} kN/m',
                ha='center', va='top', fontsize=7, color='#aaa')

    # Point loads (arrows pointing down = -Y)
    for pl in model.point_loads:
        arrow_y_top = -2.2
        arrow_y_bot = -2.8
        ax.annotate('', xy=(pl.position, arrow_y_bot), xytext=(pl.position, arrow_y_top),
                    arrowprops=dict(arrowstyle='->', color='#f38ba8', lw=1.5))
        ax.text(pl.position, -3.0, f'{pl.name}\n{pl.magnitude} kN',
                ha='center', va='top', fontsize=6, color='#f38ba8')

    # UDLs
    for udl in model.udls:
        mid = (udl.start + udl.end) / 2
        ax.annotate('', xy=(mid, -2.8), xytext=(mid, -2.2),
                    arrowprops=dict(arrowstyle='->', color='#f9e2af', lw=1.5))
        ax.text(mid, -3.0, f'{udl.name}\n{udl.magnitude} kN/m [{udl.start:.0f}-{udl.end:.0f}]',
                ha='center', va='top', fontsize=6, color='#f9e2af')

    # Root marker
    ax.annotate('FIXED\n(ROOT)\nX = 0', xy=(0, 0), xytext=(-3, 0),
                fontsize=7, color='#cdd6f4', ha='center', va='center',
                arrowprops=dict(arrowstyle='->', color='#cdd6f4', lw=1.2))

    # Coordinate axes
    ax.annotate('X →', xy=(model.jib_length * 0.95, 1.8), fontsize=7, color='#6c7086', ha='center')
    ax.annotate('Y ↑', xy=(-1.5, 1.5), fontsize=7, color='#6c7086', ha='center')

    ax.set_xlim(-4, model.jib_length + 2)
    ax.set_ylim(-3.8, 2.5)
    ax.set_xlabel('X — Longitudinal (m)', color='#cdd6f4', fontsize=10)
    ax.set_title(f'Jib Side View (X-Y) — {model.name}', color='#cdd6f4',
                 fontsize=12, fontweight='bold')
    ax.axhline(y=0, color='#555', linewidth=0.5, zorder=1)
    ax.tick_params(colors='#aaa', labelsize=8)
    for spine in ('top', 'right'):
        ax.spines[spine].set_visible(False)
    for spine in ('bottom', 'left'):
        ax.spines[spine].set_color('#555')
    ax.set_aspect('auto')
    ax.grid(True, alpha=0.1, color='#888')

    return _fig_to_base64(fig)


# ── HTML Report ───────────────────────────────────────────────────────────

def generate_html(model: CraneModel, result: AnalysisResult) -> str:
    schematic_b64 = plot_schematic(model)
    sfd_b64 = plot_sfd(result)
    bmd_b64 = plot_bmd(result)
    stress_b64 = plot_stress(result)

    sec_at_max = _get_section_at(model.sections, result.max_sigma_pos)
    sec_name = sec_at_max.name if sec_at_max else 'N/A'

    # Section table
    section_rows = ''
    for sec in model.sections:
        section_rows += f'''
        <tr>
            <td>{sec.name}</td>
            <td>{sec.start:.1f} – {sec.end:.1f}</td>
            <td>{sec.length:.1f}</td>
            <td>{sec.weight_per_length:.2f}</td>
            <td>{sec.area:.4f}</td>
            <td>{sec.moment_of_inertia:.4f}</td>
            <td>{sec.height:.2f}</td>
        </tr>'''

    # Loads table
    load_rows = ''
    # Section self-weights
    for sec in model.sections:
        load_rows += f'''
        <tr>
            <td><span class="tag">UDL</span> {sec.name} (self-weight)</td>
            <td>{sec.start:.1f} – {sec.end:.1f} m</td>
            <td>{sec.weight_per_length:.2f} kN/m</td>
            <td>−Y (down)</td>
        </tr>'''
    # Additional UDLs
    for udl in model.udls:
        load_rows += f'''
        <tr>
            <td><span class="tag">UDL</span> {udl.name}</td>
            <td>{udl.start:.1f} – {udl.end:.1f} m</td>
            <td>{udl.magnitude:.2f} kN/m</td>
            <td>−Y (down)</td>
        </tr>'''
    # Point loads
    for pl in model.point_loads:
        load_rows += f'''
        <tr>
            <td><span class="tag">Point</span> {pl.name}</td>
            <td>X = {pl.position:.1f} m</td>
            <td>{pl.magnitude:.1f} kN</td>
            <td>−Y (down)</td>
        </tr>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tower Crane Jib Analysis — {model.name}</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
        background: #11111b;
        color: #cdd6f4;
        padding: 2rem;
        line-height: 1.6;
    }}
    .container {{ max-width: 1100px; margin: 0 auto; }}
    h1 {{
        font-size: 1.8rem;
        margin-bottom: 0.5rem;
        background: linear-gradient(135deg, #f38ba8, #a6e3a1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    .subtitle {{ color: #6c7086; margin-bottom: 2rem; font-size: 0.9rem; }}
    .coord-info {{
        background: #181825;
        border: 1px solid #313244;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin-bottom: 1.5rem;
        font-size: 0.8rem;
        color: #a6adc8;
    }}
    .coord-info span {{ color: #89b4fa; font-weight: 600; }}
    .card {{
        background: #1e1e2e;
        border: 1px solid #313244;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }}
    .card h2 {{ font-size: 1.1rem; margin-bottom: 1rem; color: #cdd6f4; }}
    img {{ width: 100%; border-radius: 8px; margin-top: 1rem; }}
    .stats {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 1rem;
        margin-bottom: 1rem;
    }}
    .stat {{
        background: #181825;
        border: 1px solid #313244;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }}
    .stat-label {{ font-size: 0.75rem; color: #6c7086; margin-bottom: 0.3rem; }}
    .stat-value {{ font-size: 1.3rem; font-weight: 700; }}
    .stat-value.shear {{ color: #f38ba8; }}
    .stat-value.moment {{ color: #a6e3a1; }}
    .stat-value.stress {{ color: #89b4fa; }}
    table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.85rem;
        margin-top: 0.5rem;
    }}
    th {{
        text-align: left;
        padding: 0.6rem 0.8rem;
        border-bottom: 2px solid #313244;
        color: #6c7086;
        font-weight: 600;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    td {{ padding: 0.5rem 0.8rem; border-bottom: 1px solid #262637; }}
    tr:hover {{ background: #181825; }}
    .footer {{
        text-align: center;
        color: #45475a;
        font-size: 0.75rem;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid #313244;
    }}
    .tag {{
        display: inline-block;
        background: #313244;
        color: #a6adc8;
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
        font-size: 0.65rem;
        margin-right: 0.3rem;
    }}
</style>
</head>
<body>
<div class="container">
    <h1>🏗️ Tower Crane Jib Analysis</h1>
    <p class="subtitle">{model.name} — Cantilever model, {len(model.sections)} sections, L = {model.jib_length:.0f} m</p>

    <div class="coord-info">
        Coordinate system: <span>X</span> = longitudinal (root at 0) ·
        <span>Y</span> = vertical (positive up, gravity in −Y) ·
        <span>Z</span> = width (perpendicular to bending)
    </div>

    <div class="card">
        <h2>📊 Summary</h2>
        <div class="stats">
            <div class="stat">
                <div class="stat-label">Root Shear V(0)</div>
                <div class="stat-value shear">{result.reaction_V:.1f} kN</div>
            </div>
            <div class="stat">
                <div class="stat-label">Root Moment M(0)</div>
                <div class="stat-value moment">{result.reaction_M:.1f} kN·m</div>
            </div>
            <div class="stat">
                <div class="stat-label">Max |V|</div>
                <div class="stat-value shear">{result.max_V:.1f} kN</div>
                <div class="stat-label">@ X = {result.max_V_pos:.1f} m</div>
            </div>
            <div class="stat">
                <div class="stat-label">Max M</div>
                <div class="stat-value moment">{result.max_M:.1f} kN·m</div>
                <div class="stat-label">@ X = {result.max_M_pos:.1f} m</div>
            </div>
            <div class="stat">
                <div class="stat-label">Max Bending Stress σ</div>
                <div class="stat-value stress">{result.max_sigma:.1f} MPa</div>
                <div class="stat-label">@ X = {result.max_sigma_pos:.1f} m</div>
            </div>
            <div class="stat">
                <div class="stat-label">Critical Section</div>
                <div class="stat-value" style="font-size:0.9rem">{sec_name}</div>
            </div>
        </div>
    </div>

    <div class="card">
        <h2>🔧 Jib Configuration (Side View, X-Y Plane)</h2>
        <img src="data:image/png;base64,{schematic_b64}" alt="Jib Schematic" />
        <table>
            <thead>
                <tr>
                    <th>Section</th>
                    <th>X Range (m)</th>
                    <th>Length (m)</th>
                    <th>Weight (kN/m)</th>
                    <th>A (m²)</th>
                    <th>I<sub>z</sub> (m⁴)</th>
                    <th>Height Y (m)</th>
                </tr>
            </thead>
            <tbody>{section_rows}</tbody>
        </table>
    </div>

    <div class="card">
        <h2>⬇️ Applied Loads (−Y direction)</h2>
        <table>
            <thead>
                <tr>
                    <th>Load</th>
                    <th>X Position</th>
                    <th>Magnitude</th>
                    <th>Direction</th>
                </tr>
            </thead>
            <tbody>{load_rows}</tbody>
        </table>
    </div>

    <div class="card">
        <h2>📈 Shear Force Diagram — V(x)</h2>
        <img src="data:image/png;base64,{sfd_b64}" alt="SFD" />
    </div>

    <div class="card">
        <h2>📈 Bending Moment Diagram — M(x)</h2>
        <img src="data:image/png;base64,{bmd_b64}" alt="BMD" />
    </div>

    <div class="card">
        <h2>📈 Stress Distribution along X</h2>
        <img src="data:image/png;base64,{stress_b64}" alt="Stress" />
    </div>

    <div class="footer">
        <span class="tag">crane-jib-calc v0.2.0</span>
        <span class="tag">cantilever</span>
        <span class="tag">Euler-Bernoulli</span>
        <span class="tag">1 load case</span>
        <span class="tag">X-Y-Z coords</span>
        <br><br>
        crane-jib-calc — flat top tower crane jib analysis
    </div>
</div>
</body>
</html>'''


# ── YAML loader ───────────────────────────────────────────────────────────

def load_model(path: str) -> CraneModel:
    with open(path) as f:
        data = yaml.safe_load(f)

    crane = data['crane']
    sections = [Section(**s) for s in data['sections']]
    point_loads = [PointLoad(**pl) for pl in data.get('point_loads', [])]
    udls = [UDL(**u) for u in data.get('udls', [])]

    analysis = data.get('analysis', {})
    num_points = analysis.get('num_points', 500)

    return CraneModel(
        name=crane['name'],
        jib_length=crane['jib_length'],
        sections=sections,
        point_loads=point_loads,
        udls=udls,
        num_points=num_points,
    )


# ── CLI ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Flat Top Tower Crane Jib Calculator — SFD, BMD & stress analysis'
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
    print(f"   Point loads: {len(model.point_loads)}/{MAX_POINT_LOADS}")
    print(f"   UDLs: {len(model.udls)}/{MAX_UDLS}")

    # ── Validate ──
    errors = validate_model(model)
    if errors:
        print("❌ Validation errors:")
        for e in errors:
            print(f"   • {e}")
        sys.exit(1)
    print("   ✅ Validation passed")

    # ── Main analysis ──
    print("🔧 Computing SFD & BMD along X axis...")
    result = compute_sfd_bmd(model)

    print(f"   Root reaction: V(0) = {result.reaction_V:.1f} kN, M(0) = {result.reaction_M:.1f} kN·m")
    print(f"   Max |V|:  {result.max_V:.1f} kN  @ X = {result.max_V_pos:.1f} m")
    print(f"   Max M:    {result.max_M:.1f} kN·m  @ X = {result.max_M_pos:.1f} m")
    print(f"   Max σ:    {result.max_sigma:.1f} MPa  @ X = {result.max_sigma_pos:.1f} m")

    # ── Generate report ──
    print(f"📄 Generating HTML report: {args.output}")
    html = generate_html(model, result)
    Path(args.output).write_text(html)
    print(f"   ✅ Report saved to {args.output}")

    if not args.no_browser:
        import webbrowser
        webbrowser.open(f'file://{Path(args.output).absolute()}')

    print("Done! 🏗️")


if __name__ == '__main__':
    main()
