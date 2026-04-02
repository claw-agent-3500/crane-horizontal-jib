#!/usr/bin/env python3
"""
Flat Top Tower Crane Jib Calculator
=====================================
Models a flat-top tower crane jib as a cantilever beam with varying
cross-sections. Computes shear force diagrams (SFD) and bending moment
diagrams (BMD), with optional trolley position sweep for worst-case analysis.

Usage:
    python crane_calc.py input.yaml [--output report.html] [--no-browser]
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
import matplotlib.ticker as ticker
import numpy as np
import yaml


# ── Data classes ──────────────────────────────────────────────────────────

@dataclass
class Section:
    name: str
    start: float
    end: float
    weight_per_length: float  # kN/m
    area: float               # m²
    moment_of_inertia: float  # m⁴
    height: float             # m

    @property
    def length(self) -> float:
        return self.end - self.start


@dataclass
class PointLoad:
    name: str
    position: float  # m from root
    magnitude: float  # kN downward


@dataclass
class TrolleyLoad:
    name: str
    position: float
    trolley_weight: float
    payload_weight: float

    @property
    def total(self) -> float:
        return self.trolley_weight + self.payload_weight


@dataclass
class CraneModel:
    name: str
    jib_length: float
    sections: list[Section]
    point_loads: list[PointLoad]
    trolley_loads: list[TrolleyLoad]
    num_points: int = 500
    trolley_sweep: Optional[dict] = None


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
    max_M: float
    max_sigma: float
    max_sigma_pos: float
    sections: list[Section]
    model: CraneModel


@dataclass
class SweepResult:
    positions: np.ndarray
    root_moments: np.ndarray
    root_shears: np.ndarray
    max_stresses: np.ndarray
    worst_position: float
    worst_moment: float
    worst_shear: float
    worst_stress: float


# ── Core calculation ──────────────────────────────────────────────────────

def compute_sfd_bmd(model: CraneModel, trolley_pos: Optional[float] = None,
                    trolley_mag: Optional[float] = None) -> AnalysisResult:
    """
    Compute SFD and BMD for a cantilever jib (root at x=0, free tip at x=L).

    Sign convention (right-portion approach):
    - V(x) = sum of all downward loads to the right of x
    - M(x) = sum of all load moments about x (hogging = positive)

    Args:
        trolley_pos: Override trolley position (m from root).
        trolley_mag: Override trolley magnitude (kN). If None, uses model's trolley_loads.
    """
    L = model.jib_length
    x = np.linspace(0, L, model.num_points)

    V = np.zeros_like(x)
    M = np.zeros_like(x)

    for i, xi in enumerate(x):
        # ── Distributed loads (self-weight) to the right of xi ──
        for sec in model.sections:
            if sec.start >= xi:
                # Entire section is to the right
                length_in = sec.length
            elif sec.end > xi:
                # Partial section to the right
                length_in = sec.end - xi
            else:
                continue

            w = sec.weight_per_length
            dist_to_start = max(sec.start, xi) - xi
            dist_to_end = sec.end - xi

            V[i] += w * length_in
            M[i] += w * (dist_to_end**2 - dist_to_start**2) / 2.0

        # ── Point loads to the right of xi ──
        for pl in model.point_loads:
            if pl.position > xi:
                V[i] += pl.magnitude
                M[i] += pl.magnitude * (pl.position - xi)

        # ── Trolley load to the right of xi ──
        tp = trolley_pos if trolley_pos is not None else (
            model.trolley_loads[0].position if model.trolley_loads else None
        )
        if tp is not None and tp > xi:
            if trolley_mag is not None:
                mag = trolley_mag
            elif model.trolley_loads:
                mag = sum(t.total for t in model.trolley_loads)
            else:
                mag = 0
            V[i] += mag
            M[i] += mag * (tp - xi)

    # ── Section properties at each x point ──
    sigma = np.zeros_like(x)
    tau = np.zeros_like(x)
    for i, xi in enumerate(x):
        sec = _get_section_at(model.sections, xi)
        if sec:
            c = sec.height / 2.0  # distance to extreme fiber
            I = sec.moment_of_inertia
            A = sec.area
            sigma[i] = M[i] * c / I if I > 0 else 0  # kN·m * m / m⁴ = kN/m²
            sigma[i] /= 1000.0  # convert to MPa (kN/m² → MPa: /1000)
            # Shear stress (average): τ = V / A (simplified)
            tau[i] = V[i] / A if A > 0 else 0
            tau[i] /= 1000.0  # MPa

    return AnalysisResult(
        x=x, V=V, M=M, sigma=sigma, tau=tau,
        reaction_V=V[0], reaction_M=M[0],
        max_V=np.max(np.abs(V)),
        max_M=np.max(M),
        max_sigma=np.max(sigma),
        max_sigma_pos=x[np.argmax(sigma)],
        sections=model.sections,
        model=model,
    )


def _get_section_at(sections: list[Section], x: float) -> Optional[Section]:
    for sec in sections:
        if sec.start <= x <= sec.end:
            return sec
    return None


def sweep_trolley(model: CraneModel) -> SweepResult:
    """Sweep trolley position to find worst-case loads."""
    sweep = model.trolley_sweep or {}
    pos_min = sweep.get('min_position', 3.0)
    pos_max = sweep.get('max_position', model.jib_length - 2.0)
    step = sweep.get('step', 1.0)

    positions = np.arange(pos_min, pos_max + step / 2, step)
    root_moments = np.zeros_like(positions)
    root_shears = np.zeros_like(positions)
    max_stresses = np.zeros_like(positions)

    # Use first trolley load as the sweep load
    trolley_mag = model.trolley_loads[0].total if model.trolley_loads else 0
    # Temporarily remove trolley loads from model for base calculation
    base_model = CraneModel(
        name=model.name, jib_length=model.jib_length,
        sections=model.sections, point_loads=model.point_loads,
        trolley_loads=[], num_points=model.num_points,
    )

    for i, pos in enumerate(positions):
        result = compute_sfd_bmd(base_model, trolley_pos=pos, trolley_mag=trolley_mag)
        root_moments[i] = result.reaction_M
        root_shears[i] = result.reaction_V
        max_stresses[i] = result.max_sigma

    worst_idx = np.argmax(root_moments)
    return SweepResult(
        positions=positions,
        root_moments=root_moments,
        root_shears=root_shears,
        max_stresses=max_stresses,
        worst_position=positions[worst_idx],
        worst_moment=root_moments[worst_idx],
        worst_shear=root_shears[worst_idx],
        worst_stress=max_stresses[worst_idx],
    )


# ── Plotting ──────────────────────────────────────────────────────────────

def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='#1e1e2e', edgecolor='none')
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return encoded


def _section_background(ax, sections: list[Section], ymin: float, ymax: float):
    """Draw alternating section backgrounds."""
    colors = ['#2a2a3e', '#252540']
    for i, sec in enumerate(sections):
        ax.axvspan(sec.start, sec.end, alpha=0.3, color=colors[i % 2], zorder=0)
        # Section label at top
        mid = (sec.start + sec.end) / 2
        ax.text(mid, ymax * 0.92, sec.name, ha='center', va='top',
                fontsize=6, color='#888', alpha=0.8, clip_on=True)


def plot_sfd(result: AnalysisResult) -> str:
    fig, ax = plt.subplots(figsize=(12, 3.5))
    fig.patch.set_facecolor('#1e1e2e')
    ax.set_facecolor('#1e1e2e')

    _section_background(ax, result.sections, np.min(result.V) * 1.1 or 0, np.max(result.V) * 1.1)

    ax.fill_between(result.x, result.V, alpha=0.4, color='#f38ba8', zorder=2)
    ax.plot(result.x, result.V, color='#f38ba8', linewidth=1.5, zorder=3)

    ax.set_xlabel('Position along jib (m)', color='#cdd6f4', fontsize=10)
    ax.set_ylabel('Shear Force (kN)', color='#f38ba8', fontsize=10)
    ax.set_title('Shear Force Diagram (SFD)', color='#cdd6f4', fontsize=12, fontweight='bold')
    ax.axhline(y=0, color='#555', linewidth=0.5, zorder=1)
    ax.tick_params(colors='#aaa', labelsize=8)
    ax.spines['bottom'].set_color('#555')
    ax.spines['left'].set_color('#555')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, alpha=0.15, color='#888')

    # Max annotation
    max_idx = np.argmax(np.abs(result.V))
    ax.annotate(f'Max |V| = {result.max_V:.1f} kN\nat x = {result.x[max_idx]:.1f} m',
                xy=(result.x[max_idx], result.V[max_idx]),
                xytext=(20, 20), textcoords='offset points',
                color='#f38ba8', fontsize=8,
                arrowprops=dict(arrowstyle='->', color='#f38ba8', lw=0.8))

    return _fig_to_base64(fig)


def plot_bmd(result: AnalysisResult) -> str:
    fig, ax = plt.subplots(figsize=(12, 3.5))
    fig.patch.set_facecolor('#1e1e2e')
    ax.set_facecolor('#1e1e2e')

    _section_background(ax, result.sections, 0, np.max(result.M) * 1.1)

    ax.fill_between(result.x, result.M, alpha=0.4, color='#a6e3a1', zorder=2)
    ax.plot(result.x, result.M, color='#a6e3a1', linewidth=1.5, zorder=3)

    ax.set_xlabel('Position along jib (m)', color='#cdd6f4', fontsize=10)
    ax.set_ylabel('Bending Moment (kN·m)', color='#a6e3a1', fontsize=10)
    ax.set_title('Bending Moment Diagram (BMD)', color='#cdd6f4', fontsize=12, fontweight='bold')
    ax.axhline(y=0, color='#555', linewidth=0.5, zorder=1)
    ax.tick_params(colors='#aaa', labelsize=8)
    ax.spines['bottom'].set_color('#555')
    ax.spines['left'].set_color('#555')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, alpha=0.15, color='#888')

    max_idx = np.argmax(result.M)
    ax.annotate(f'Max M = {result.max_M:.1f} kN·m\nat x = {result.x[max_idx]:.1f} m',
                xy=(result.x[max_idx], result.M[max_idx]),
                xytext=(20, -30), textcoords='offset points',
                color='#a6e3a1', fontsize=8,
                arrowprops=dict(arrowstyle='->', color='#a6e3a1', lw=0.8))

    return _fig_to_base64(fig)


def plot_stress(result: AnalysisResult) -> str:
    fig, ax = plt.subplots(figsize=(12, 3.5))
    fig.patch.set_facecolor('#1e1e2e')
    ax.set_facecolor('#1e1e2e')

    _section_background(ax, result.sections, 0, np.max(result.sigma) * 1.1)

    ax.fill_between(result.x, result.sigma, alpha=0.3, color='#89b4fa', label='Bending σ', zorder=2)
    ax.plot(result.x, result.sigma, color='#89b4fa', linewidth=1.5, label='Bending σ', zorder=3)

    ax.fill_between(result.x, np.abs(result.tau), alpha=0.2, color='#f9e2af', label='Shear τ (avg)', zorder=2)
    ax.plot(result.x, np.abs(result.tau), color='#f9e2af', linewidth=1.0,
            linestyle='--', label='Shear τ (avg)', zorder=3)

    ax.set_xlabel('Position along jib (m)', color='#cdd6f4', fontsize=10)
    ax.set_ylabel('Stress (MPa)', color='#cdd6f4', fontsize=10)
    ax.set_title('Stress Distribution', color='#cdd6f4', fontsize=12, fontweight='bold')
    ax.axhline(y=0, color='#555', linewidth=0.5, zorder=1)
    ax.tick_params(colors='#aaa', labelsize=8)
    ax.spines['bottom'].set_color('#555')
    ax.spines['left'].set_color('#555')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(fontsize=8, facecolor='#1e1e2e', edgecolor='#555',
              labelcolor='#cdd6f4', loc='upper right')
    ax.grid(True, alpha=0.15, color='#888')

    return _fig_to_base64(fig)


def plot_sweep(sweep: SweepResult) -> str:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
    fig.patch.set_facecolor('#1e1e2e')

    for ax in (ax1, ax2):
        ax.set_facecolor('#1e1e2e')
        ax.tick_params(colors='#aaa', labelsize=8)
        ax.spines['bottom'].set_color('#555')
        ax.spines['left'].set_color('#555')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(True, alpha=0.15, color='#888')

    # Root moment
    ax1.plot(sweep.positions, sweep.root_moments, color='#a6e3a1', linewidth=1.5)
    ax1.axvline(sweep.worst_position, color='#f38ba8', linestyle='--', alpha=0.6, linewidth=0.8)
    ax1.scatter([sweep.worst_position], [sweep.worst_moment], color='#f38ba8', s=40, zorder=5)
    ax1.set_ylabel('Root Moment (kN·m)', color='#a6e3a1', fontsize=10)
    ax1.set_title('Trolley Position Sweep — Worst Case Analysis', color='#cdd6f4',
                  fontsize=12, fontweight='bold')
    ax1.annotate(f'Worst: {sweep.worst_moment:.1f} kN·m\nat {sweep.worst_position:.1f} m',
                 xy=(sweep.worst_position, sweep.worst_moment),
                 xytext=(20, 0), textcoords='offset points',
                 color='#f38ba8', fontsize=8)

    # Root shear
    ax2.plot(sweep.positions, sweep.root_shears, color='#f38ba8', linewidth=1.5)
    ax2.axvline(sweep.worst_position, color='#f38ba8', linestyle='--', alpha=0.6, linewidth=0.8)
    ax2.set_ylabel('Root Shear (kN)', color='#f38ba8', fontsize=10)
    ax2.set_xlabel('Trolley Position (m from root)', color='#cdd6f4', fontsize=10)

    fig.tight_layout()
    return _fig_to_base64(fig)


def plot_section_overview(model: CraneModel) -> str:
    """Draw a schematic of the jib with sections labeled."""
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
        # Label
        mid = (sec.start + sec.end) / 2
        ax.text(mid, h/2 + 0.15, sec.name, ha='center', va='bottom',
                fontsize=7, color=color, fontweight='bold')
        ax.text(mid, -h/2 - 0.15, f'{sec.weight_per_length} kN/m',
                ha='center', va='top', fontsize=7, color='#aaa')

    # Point loads
    for pl in model.point_loads:
        ax.annotate('', xy=(pl.position, -2.5), xytext=(pl.position, -1.5),
                    arrowprops=dict(arrowstyle='->', color='#f38ba8', lw=1.5))
        ax.text(pl.position, -2.7, f'{pl.name}\n{pl.magnitude} kN',
                ha='center', va='top', fontsize=6, color='#f38ba8')

    # Trolley loads
    for tl in model.trolley_loads:
        ax.annotate('', xy=(tl.position, 2.5), xytext=(tl.position, 1.5),
                    arrowprops=dict(arrowstyle='->', color='#f9e2af', lw=1.5))
        ax.text(tl.position, 2.7, f'{tl.name}\n{tl.total:.0f} kN',
                ha='center', va='bottom', fontsize=6, color='#f9e2af')

    # Root marker
    ax.annotate('FIXED\n(ROOT)', xy=(0, 0), xytext=(-2.5, 0),
                fontsize=8, color='#cdd6f4', ha='center', va='center',
                arrowprops=dict(arrowstyle='->', color='#cdd6f4', lw=1.2))

    ax.set_xlim(-3, model.jib_length + 1)
    ax.set_ylim(-3.5, 3.5)
    ax.set_xlabel('Position along jib (m)', color='#cdd6f4', fontsize=10)
    ax.set_title(f'Jib Configuration — {model.name}', color='#cdd6f4',
                 fontsize=12, fontweight='bold')
    ax.axhline(y=0, color='#555', linewidth=0.5, zorder=1)
    ax.tick_params(colors='#aaa', labelsize=8)
    ax.spines['bottom'].set_color('#555')
    ax.spines['left'].set_color('#555')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_aspect('auto')
    ax.grid(True, alpha=0.1, color='#888')

    return _fig_to_base64(fig)


# ── HTML Report ───────────────────────────────────────────────────────────

def generate_html(model: CraneModel, result: AnalysisResult,
                  sweep_result: Optional[SweepResult] = None) -> str:
    schematic_b64 = plot_section_overview(model)
    sfd_b64 = plot_sfd(result)
    bmd_b64 = plot_bmd(result)
    stress_b64 = plot_stress(result)

    sweep_html = ''
    if sweep_result:
        sweep_b64 = plot_sweep(sweep_result)
        sweep_html = f'''
        <div class="card">
            <h2>🔄 Trolley Position Sweep</h2>
            <div class="stats">
                <div class="stat">
                    <div class="stat-label">Worst Trolley Position</div>
                    <div class="stat-value">{sweep_result.worst_position:.1f} m</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Max Root Moment</div>
                    <div class="stat-value">{sweep_result.worst_moment:.1f} kN·m</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Max Root Shear</div>
                    <div class="stat-value">{sweep_result.worst_shear:.1f} kN</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Max Bending Stress</div>
                    <div class="stat-value">{sweep_result.worst_stress:.1f} MPa</div>
                </div>
            </div>
            <img src="data:image/png;base64,{sweep_b64}" alt="Trolley Sweep" />
        </div>'''

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

    # Point loads table
    pl_rows = ''
    for pl in model.point_loads:
        pl_rows += f'''
        <tr>
            <td>{pl.name}</td>
            <td>{pl.position:.1f} m</td>
            <td>{pl.magnitude:.1f} kN</td>
        </tr>'''
    for tl in model.trolley_loads:
        pl_rows += f'''
        <tr>
            <td>{tl.name} (trolley + payload)</td>
            <td>{tl.position:.1f} m</td>
            <td>{tl.total:.1f} kN</td>
        </tr>'''

    # Max stress section
    sec_at_max = _get_section_at(model.sections, result.max_sigma_pos)
    sec_name = sec_at_max.name if sec_at_max else 'N/A'

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
    .card {{
        background: #1e1e2e;
        border: 1px solid #313244;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }}
    .card h2 {{
        font-size: 1.1rem;
        margin-bottom: 1rem;
        color: #cdd6f4;
    }}
    img {{
        width: 100%;
        border-radius: 8px;
        margin-top: 1rem;
    }}
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
    td {{
        padding: 0.5rem 0.8rem;
        border-bottom: 1px solid #262637;
    }}
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
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-size: 0.7rem;
        margin-right: 0.3rem;
    }}
</style>
</head>
<body>
<div class="container">
    <h1>🏗️ Tower Crane Jib Analysis</h1>
    <p class="subtitle">{model.name} — Cantilever model with {len(model.sections)} cross-sections, jib length {model.jib_length:.0f} m</p>

    <div class="card">
        <h2>📊 Summary</h2>
        <div class="stats">
            <div class="stat">
                <div class="stat-label">Root Shear (Reaction)</div>
                <div class="stat-value shear">{result.reaction_V:.1f} kN</div>
            </div>
            <div class="stat">
                <div class="stat-label">Root Moment (Reaction)</div>
                <div class="stat-value moment">{result.reaction_M:.1f} kN·m</div>
            </div>
            <div class="stat">
                <div class="stat-label">Max |Shear|</div>
                <div class="stat-value shear">{result.max_V:.1f} kN</div>
            </div>
            <div class="stat">
                <div class="stat-label">Max Bending Moment</div>
                <div class="stat-value moment">{result.max_M:.1f} kN·m</div>
            </div>
            <div class="stat">
                <div class="stat-label">Max Bending Stress</div>
                <div class="stat-value stress">{result.max_sigma:.1f} MPa</div>
            </div>
            <div class="stat">
                <div class="stat-label">Critical Section</div>
                <div class="stat-value" style="font-size:0.9rem">{sec_name}</div>
            </div>
        </div>
    </div>

    <div class="card">
        <h2>🔧 Jib Configuration</h2>
        <img src="data:image/png;base64,{schematic_b64}" alt="Jib Schematic" />
        <table>
            <thead>
                <tr>
                    <th>Section</th>
                    <th>Range (m)</th>
                    <th>Length (m)</th>
                    <th>Weight (kN/m)</th>
                    <th>Area (m²)</th>
                    <th>I (m⁴)</th>
                    <th>Height (m)</th>
                </tr>
            </thead>
            <tbody>{section_rows}</tbody>
        </table>
    </div>

    <div class="card">
        <h2>⬇️ Applied Loads</h2>
        <table>
            <thead>
                <tr>
                    <th>Load</th>
                    <th>Position</th>
                    <th>Magnitude</th>
                </tr>
            </thead>
            <tbody>{pl_rows}</tbody>
        </table>
    </div>

    <div class="card">
        <h2>📈 Shear Force Diagram (SFD)</h2>
        <img src="data:image/png;base64,{sfd_b64}" alt="SFD" />
    </div>

    <div class="card">
        <h2>📈 Bending Moment Diagram (BMD)</h2>
        <img src="data:image/png;base64,{bmd_b64}" alt="BMD" />
    </div>

    <div class="card">
        <h2>📈 Stress Distribution</h2>
        <img src="data:image/png;base64,{stress_b64}" alt="Stress" />
    </div>

    {sweep_html}

    <div class="footer">
        <span class="tag">crane-jib-calc v0.1.0</span>
        <span class="tag">cantilever model</span>
        <span class="tag">Euler-Bernoulli</span>
        <br><br>
        Generated by crane-jib-calc — flat top tower crane jib analysis tool
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
    trolley_loads = [TrolleyLoad(**tl) for tl in data.get('trolley_loads', [])]

    analysis = data.get('analysis', {})
    num_points = analysis.get('num_points', 500)

    sweep = data.get('trolley_sweep')

    return CraneModel(
        name=crane['name'],
        jib_length=crane['jib_length'],
        sections=sections,
        point_loads=point_loads,
        trolley_loads=trolley_loads,
        num_points=num_points,
        trolley_sweep=sweep if sweep and sweep.get('enabled') else None,
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

    # ── Main analysis ──
    print("🔧 Computing SFD & BMD...")
    result = compute_sfd_bmd(model)

    print(f"   Root reaction: V = {result.reaction_V:.1f} kN, M = {result.reaction_M:.1f} kN·m")
    print(f"   Max shear:     {result.max_V:.1f} kN")
    print(f"   Max moment:    {result.max_M:.1f} kN·m")
    print(f"   Max stress:    {result.max_sigma:.1f} MPa at x = {result.max_sigma_pos:.1f} m")

    # ── Trolley sweep ──
    sweep_result = None
    if model.trolley_sweep:
        print("🔄 Sweeping trolley positions for worst case...")
        sweep_result = sweep_trolley(model)
        print(f"   Worst trolley position: {sweep_result.worst_position:.1f} m")
        print(f"   Worst root moment:      {sweep_result.worst_moment:.1f} kN·m")

    # ── Generate report ──
    print(f"📄 Generating HTML report: {args.output}")
    html = generate_html(model, result, sweep_result)
    Path(args.output).write_text(html)
    print(f"   ✅ Report saved to {args.output}")

    if not args.no_browser:
        import webbrowser
        webbrowser.open(f'file://{Path(args.output).absolute()}')

    print("Done! 🏗️")


if __name__ == '__main__':
    main()
