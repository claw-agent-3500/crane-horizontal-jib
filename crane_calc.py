#!/usr/bin/env python3
"""
Flat Top Tower Crane Jib Calculator
=====================================
Models a flat-top tower crane jib as a cantilever beam with varying
cross-sections. Computes shear force, bending moment, deflection,
and stress diagrams along the X axis.

Coordinate system:
  X = longitudinal (along jib, root at x=0)
  Y = vertical (positive up, gravity in -Y)
  Z = width (perpendicular to bending plane)

Constraints:
  - Max 5 point loads
  - Max 5 UDLs (in addition to section self-weights)
  - 1 load case only (MVP), with optional trolley sweep

Usage:
    python3 crane_calc.py input.yaml [--output report.html] [--no-browser]
"""

import argparse
import io
import base64
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import yaml


MAX_POINT_LOADS = 5
MAX_UDLS = 5
DEFAULT_E = 200e6  # kN/m² (200 GPa steel)


# ── Data classes ──────────────────────────────────────────────────────────

@dataclass
class Section:
    name: str
    start: float              # X start (m)
    end: float                # X end (m)
    weight_per_length: float  # kN/m (self-weight, acts in -Y)
    area: float               # m² (effective A)
    moment_of_inertia: float  # m⁴ (I about Z axis)
    height: float             # m (Y dimension, depth)

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
class TrolleySweep:
    magnitude: float          # kN (trolley + payload)
    min_position: float = 3.0
    max_position: float = 0.0  # 0 = auto (jib_length - 2m)
    step: float = 1.0


@dataclass
class CraneModel:
    name: str
    jib_length: float
    sections: list[Section]
    point_loads: list[PointLoad]
    udls: list[UDL]
    youngs_modulus: float = DEFAULT_E  # kN/m²
    num_points: int = 500
    trolley_sweep: Optional[TrolleySweep] = None


@dataclass
class AnalysisResult:
    x: np.ndarray
    V: np.ndarray          # Shear force (kN)
    M: np.ndarray          # Bending moment (kN·m)
    theta: np.ndarray      # Slope (rad)
    delta: np.ndarray      # Deflection (m, positive = downward)
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
    max_delta: float
    max_delta_pos: float
    tip_delta: float
    sections: list[Section]
    model: CraneModel


@dataclass
class SweepResult:
    positions: np.ndarray
    root_moments: np.ndarray
    root_shears: np.ndarray
    tip_deflections: np.ndarray
    worst_position: float
    worst_moment: float
    worst_shear: float
    worst_deflection: float


# ── Validation ────────────────────────────────────────────────────────────

def validate_model(model: CraneModel) -> list[str]:
    errors = []

    if len(model.point_loads) > MAX_POINT_LOADS:
        errors.append(f"Too many point loads: {len(model.point_loads)} (max {MAX_POINT_LOADS})")
    if len(model.udls) > MAX_UDLS:
        errors.append(f"Too many UDLs: {len(model.udls)} (max {MAX_UDLS})")

    sorted_secs = sorted(model.sections, key=lambda s: s.start)
    if sorted_secs[0].start != 0:
        errors.append(f"First section starts at {sorted_secs[0].start}, must be 0")
    if sorted_secs[-1].end != model.jib_length:
        errors.append(f"Last section ends at {sorted_secs[-1].end}, must be {model.jib_length}")

    for i in range(len(sorted_secs) - 1):
        gap = sorted_secs[i + 1].start - sorted_secs[i].end
        if abs(gap) > 1e-6:
            errors.append(f"Gap between sections at X={sorted_secs[i].end:.1f} to {sorted_secs[i+1].start:.1f}")

    for pl in model.point_loads:
        if pl.position < 0 or pl.position > model.jib_length:
            errors.append(f"Point load '{pl.name}' at X={pl.position} outside jib [0, {model.jib_length}]")

    for udl in model.udls:
        if udl.start < 0 or udl.end > model.jib_length:
            errors.append(f"UDL '{udl.name}' [{udl.start}, {udl.end}] outside jib [0, {model.jib_length}]")
        if udl.start >= udl.end:
            errors.append(f"UDL '{udl.name}' has start >= end")

    if model.youngs_modulus <= 0:
        errors.append(f"Young's modulus must be positive, got {model.youngs_modulus}")

    return errors


# ── Core calculation ──────────────────────────────────────────────────────

def _compute_loads(model: CraneModel, trolley_pos: Optional[float] = None,
                   trolley_mag: Optional[float] = None) -> tuple[np.ndarray, np.ndarray]:
    """Compute V(x) and M(x) arrays. Returns (x, V, M)."""
    L = model.jib_length
    x = np.linspace(0, L, model.num_points)
    V = np.zeros_like(x)
    M = np.zeros_like(x)

    for i, xi in enumerate(x):
        # Section self-weights
        for sec in model.sections:
            if sec.start >= xi:
                length_in, d_start, d_end = sec.length, sec.start - xi, sec.end - xi
            elif sec.end > xi:
                length_in, d_start, d_end = sec.end - xi, 0.0, sec.end - xi
            else:
                continue
            w = sec.weight_per_length
            V[i] += w * length_in
            M[i] += w * (d_end**2 - d_start**2) / 2.0

        # Additional UDLs
        for udl in model.udls:
            if udl.start >= xi:
                length_in, d_start, d_end = udl.end - udl.start, udl.start - xi, udl.end - xi
            elif udl.end > xi:
                length_in, d_start, d_end = udl.end - xi, 0.0, udl.end - xi
            else:
                continue
            w = udl.magnitude
            V[i] += w * length_in
            M[i] += w * (d_end**2 - d_start**2) / 2.0

        # Point loads
        for pl in model.point_loads:
            if pl.position > xi:
                V[i] += pl.magnitude
                M[i] += pl.magnitude * (pl.position - xi)

        # Trolley load
        tp = trolley_pos if trolley_pos is not None else None
        if tp is not None and tp > xi:
            mag = trolley_mag if trolley_mag is not None else 0
            V[i] += mag
            M[i] += mag * (tp - xi)

    return x, V, M


def _compute_deflection(x: np.ndarray, M: np.ndarray, model: CraneModel) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute slope θ(x) and deflection δ(x) by double integration of M/(EI).

    Boundary conditions: θ(0) = 0, δ(0) = 0 (cantilever fixed at root).
    Deflection is positive downward (-Y direction).
    """
    n = len(x)
    dx = x[1] - x[0]

    # Get EI at each point
    EI = np.zeros(n)
    for j, xj in enumerate(x):
        sec = _get_section_at(model.sections, xj)
        EI[j] = model.youngs_modulus * sec.moment_of_inertia if sec else 0

    # Curvature: κ = M / EI
    curvature = np.where(EI > 0, M / EI, 0)

    # First integration: θ(x) = ∫₀ˣ κ(ξ) dξ
    theta = np.zeros(n)
    for j in range(1, n):
        theta[j] = theta[j - 1] + (curvature[j - 1] + curvature[j]) * dx / 2.0

    # Second integration: δ(x) = ∫₀ˣ θ(ξ) dξ
    delta = np.zeros(n)
    for j in range(1, n):
        delta[j] = delta[j - 1] + (theta[j - 1] + theta[j]) * dx / 2.0

    return theta, delta


def compute_sfd_bmd(model: CraneModel, trolley_pos: Optional[float] = None,
                    trolley_mag: Optional[float] = None) -> AnalysisResult:
    """
    Full analysis: SFD, BMD, deflection, stress.
    Optional trolley load override for sweep mode.
    """
    x, V, M = _compute_loads(model, trolley_pos, trolley_mag)
    theta, delta = _compute_deflection(x, M, model)

    # Stresses
    sigma = np.zeros_like(x)
    tau = np.zeros_like(x)
    for j, xj in enumerate(x):
        sec = _get_section_at(model.sections, xj)
        if sec:
            c = sec.height / 2.0
            I = sec.moment_of_inertia
            A = sec.area
            sigma[j] = (M[j] * c / I / 1000.0) if I > 0 else 0  # kN/m² → MPa
            tau[j] = (V[j] / A / 1000.0) if A > 0 else 0

    max_V_idx = np.argmax(np.abs(V))
    max_M_idx = np.argmax(M)
    max_sigma_idx = np.argmax(sigma)
    max_delta_idx = np.argmax(delta)

    return AnalysisResult(
        x=x, V=V, M=M, theta=theta, delta=delta, sigma=sigma, tau=tau,
        reaction_V=V[0], reaction_M=M[0],
        max_V=np.max(np.abs(V)), max_V_pos=x[max_V_idx],
        max_M=np.max(M), max_M_pos=x[max_M_idx],
        max_sigma=np.max(sigma), max_sigma_pos=x[max_sigma_idx],
        max_delta=np.max(delta), max_delta_pos=x[max_delta_idx],
        tip_delta=delta[-1],
        sections=model.sections,
        model=model,
    )


def sweep_trolley(model: CraneModel) -> SweepResult:
    """Sweep trolley position to find worst-case loads and deflection."""
    sweep = model.trolley_sweep
    pos_max = sweep.max_position if sweep.max_position > 0 else model.jib_length - 2.0
    positions = np.arange(sweep.min_position, pos_max + sweep.step / 2, sweep.step)

    root_moments = np.zeros_like(positions)
    root_shears = np.zeros_like(positions)
    tip_deflections = np.zeros_like(positions)

    for i, pos in enumerate(positions):
        result = compute_sfd_bmd(model, trolley_pos=pos, trolley_mag=sweep.magnitude)
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
                xytext=(20, 20), textcoords='offset points', color='#f38ba8', fontsize=8,
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
                xy=(result.max_M_pos, result.max_M), xytext=(20, -30),
                textcoords='offset points', color='#a6e3a1', fontsize=8,
                arrowprops=dict(arrowstyle='->', color='#a6e3a1', lw=0.8))
    return _fig_to_base64(fig)


def plot_deflection(result: AnalysisResult) -> str:
    fig, ax = plt.subplots(figsize=(12, 3.5))
    fig.patch.set_facecolor('#1e1e2e')
    delta_mm = result.delta * 1000  # convert to mm
    max_mm = delta_mm.max() if delta_mm.max() > 0 else 1
    _section_bands(ax, result.sections, 0, max_mm * 1.15)
    ax.fill_between(result.x, delta_mm, alpha=0.4, color='#cba6f7', zorder=2)
    ax.plot(result.x, delta_mm, color='#cba6f7', linewidth=1.5, zorder=3)
    _style_ax(ax, 'δ(x) Deflection (mm)', '#cba6f7')
    ax.set_title('Deflection Curve (downward = positive)', color='#cdd6f4', fontsize=12, fontweight='bold')
    ax.annotate(f'Tip δ = {result.tip_delta * 1000:.1f} mm\nat X = {result.x[-1]:.1f} m',
                xy=(result.x[-1], delta_mm[-1]), xytext=(-80, -30),
                textcoords='offset points', color='#cba6f7', fontsize=8,
                arrowprops=dict(arrowstyle='->', color='#cba6f7', lw=0.8))
    # Serviceability limit line
    L = result.model.jib_length
    limit_mm = L * 1000 / 250  # L/250 typical
    ax.axhline(y=limit_mm, color='#f38ba8', linestyle='--', linewidth=0.8, alpha=0.6, zorder=1)
    ax.text(result.x[-1] * 0.98, limit_mm * 1.05, f'L/250 = {limit_mm:.0f} mm',
            ha='right', va='bottom', fontsize=7, color='#f38ba8', alpha=0.7)
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
    ax.legend(fontsize=8, facecolor='#1e1e2e', edgecolor='#555', labelcolor='#cdd6f4', loc='upper right')
    return _fig_to_base64(fig)


def plot_schematic(model: CraneModel) -> str:
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

    for pl in model.point_loads:
        ax.annotate('', xy=(pl.position, -2.8), xytext=(pl.position, -2.2),
                    arrowprops=dict(arrowstyle='->', color='#f38ba8', lw=1.5))
        ax.text(pl.position, -3.0, f'{pl.name}\n{pl.magnitude} kN',
                ha='center', va='top', fontsize=6, color='#f38ba8')

    for udl in model.udls:
        mid = (udl.start + udl.end) / 2
        ax.annotate('', xy=(mid, -2.8), xytext=(mid, -2.2),
                    arrowprops=dict(arrowstyle='->', color='#f9e2af', lw=1.5))
        ax.text(mid, -3.0, f'{udl.name}\n{udl.magnitude} kN/m [{udl.start:.0f}-{udl.end:.0f}]',
                ha='center', va='top', fontsize=6, color='#f9e2af')

    ax.annotate('FIXED\n(ROOT)\nX = 0', xy=(0, 0), xytext=(-3, 0),
                fontsize=7, color='#cdd6f4', ha='center', va='center',
                arrowprops=dict(arrowstyle='->', color='#cdd6f4', lw=1.2))
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


def plot_sweep(sweep: SweepResult) -> str:
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    fig.patch.set_facecolor('#1e1e2e')

    for ax in (ax1, ax2, ax3):
        ax.set_facecolor('#1e1e2e')
        ax.tick_params(colors='#aaa', labelsize=8)
        for spine in ('top', 'right'):
            ax.spines[spine].set_visible(False)
        for spine in ('bottom', 'left'):
            ax.spines[spine].set_color('#555')
        ax.grid(True, alpha=0.15, color='#888')
        ax.axvline(sweep.worst_position, color='#f38ba8', linestyle='--', alpha=0.5, linewidth=0.8)

    # Root moment
    ax1.plot(sweep.positions, sweep.root_moments, color='#a6e3a1', linewidth=1.5)
    ax1.scatter([sweep.worst_position], [sweep.worst_moment], color='#f38ba8', s=40, zorder=5)
    ax1.set_ylabel('Root Moment (kN·m)', color='#a6e3a1', fontsize=10)
    ax1.set_title('Trolley Position Sweep — Worst Case Analysis', color='#cdd6f4',
                  fontsize=12, fontweight='bold')
    ax1.annotate(f'Worst: {sweep.worst_moment:.1f} kN·m @ {sweep.worst_position:.1f} m',
                 xy=(sweep.worst_position, sweep.worst_moment), xytext=(20, 0),
                 textcoords='offset points', color='#f38ba8', fontsize=8)

    # Root shear
    ax2.plot(sweep.positions, sweep.root_shears, color='#f38ba8', linewidth=1.5)
    ax2.set_ylabel('Root Shear (kN)', color='#f38ba8', fontsize=10)

    # Tip deflection
    ax3.plot(sweep.positions, sweep.tip_deflections * 1000, color='#cba6f7', linewidth=1.5)
    ax3.set_ylabel('Tip Deflection (mm)', color='#cba6f7', fontsize=10)
    ax3.set_xlabel('Trolley Position (m from root)', color='#cdd6f4', fontsize=10)

    fig.tight_layout()
    return _fig_to_base64(fig)


# ── HTML Report ───────────────────────────────────────────────────────────

def generate_html(model: CraneModel, result: AnalysisResult,
                  sweep_result: Optional[SweepResult] = None) -> str:
    schematic_b64 = plot_schematic(model)
    sfd_b64 = plot_sfd(result)
    bmd_b64 = plot_bmd(result)
    deflection_b64 = plot_deflection(result)
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
    for sec in model.sections:
        load_rows += f'''
        <tr>
            <td><span class="tag">UDL</span> {sec.name} (self-weight)</td>
            <td>{sec.start:.1f} – {sec.end:.1f} m</td>
            <td>{sec.weight_per_length:.2f} kN/m</td>
            <td>−Y (down)</td>
        </tr>'''
    for udl in model.udls:
        load_rows += f'''
        <tr>
            <td><span class="tag">UDL</span> {udl.name}</td>
            <td>{udl.start:.1f} – {udl.end:.1f} m</td>
            <td>{udl.magnitude:.2f} kN/m</td>
            <td>−Y (down)</td>
        </tr>'''
    for pl in model.point_loads:
        load_rows += f'''
        <tr>
            <td><span class="tag">Point</span> {pl.name}</td>
            <td>X = {pl.position:.1f} m</td>
            <td>{pl.magnitude:.1f} kN</td>
            <td>−Y (down)</td>
        </tr>'''

    # Deflection serviceability check
    L = model.jib_length
    limit_250 = L * 1000 / 250
    limit_400 = L * 1000 / 400
    tip_mm = result.tip_delta * 1000
    defl_status = '✅' if tip_mm < limit_250 else ('⚠️' if tip_mm < limit_400 else '❌')

    # Trolley sweep section
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
                <div class="stat-value moment">{sweep_result.worst_moment:.1f} kN·m</div>
            </div>
            <div class="stat">
                <div class="stat-label">Max Root Shear</div>
                <div class="stat-value shear">{sweep_result.worst_shear:.1f} kN</div>
            </div>
            <div class="stat">
                <div class="stat-label">Max Tip Deflection</div>
                <div class="stat-value" style="color:#cba6f7">{sweep_result.worst_deflection * 1000:.1f} mm</div>
            </div>
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
    .stat-value.deflection {{ color: #cba6f7; }}
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
    <p class="subtitle">{model.name} — Cantilever model, {len(model.sections)} sections, L = {model.jib_length:.0f} m, E = {model.youngs_modulus / 1e6:.0f} GPa</p>

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
                <div class="stat-label">Tip Deflection δ</div>
                <div class="stat-value deflection">{tip_mm:.1f} mm</div>
                <div class="stat-label">{defl_status} L/250 = {limit_250:.0f} mm</div>
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
        <h2>📈 Deflection Curve — δ(x)</h2>
        <img src="data:image/png;base64,{deflection_b64}" alt="Deflection" />
    </div>

    <div class="card">
        <h2>📈 Stress Distribution along X</h2>
        <img src="data:image/png;base64,{stress_b64}" alt="Stress" />
    </div>

    {sweep_html}

    <div class="footer">
        <span class="tag">crane-jib-calc v0.3.0</span>
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

    E = crane.get('youngs_modulus', DEFAULT_E)  # kN/m²

    # Trolley sweep
    ts_data = data.get('trolley_sweep')
    trolley_sweep = None
    if ts_data and ts_data.get('enabled'):
        trolley_sweep = TrolleySweep(
            magnitude=ts_data['magnitude'],
            min_position=ts_data.get('min_position', 3.0),
            max_position=ts_data.get('max_position', 0.0),
            step=ts_data.get('step', 1.0),
        )

    return CraneModel(
        name=crane['name'],
        jib_length=crane['jib_length'],
        sections=sections,
        point_loads=point_loads,
        udls=udls,
        youngs_modulus=E,
        num_points=num_points,
        trolley_sweep=trolley_sweep,
    )


# ── CLI ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Flat Top Tower Crane Jib Calculator — SFD, BMD, deflection & stress'
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
    if model.trolley_sweep:
        print(f"   Trolley sweep: {model.trolley_sweep.magnitude:.0f} kN, "
              f"[{model.trolley_sweep.min_position:.0f}–{model.trolley_sweep.max_position or model.jib_length - 2:.0f}m]")

    # Validate
    errors = validate_model(model)
    if errors:
        print("❌ Validation errors:")
        for e in errors:
            print(f"   • {e}")
        sys.exit(1)
    print("   ✅ Validation passed")

    # Main analysis
    print("🔧 Computing SFD, BMD, deflection & stress...")
    result = compute_sfd_bmd(model)

    tip_mm = result.tip_delta * 1000
    L = model.jib_length
    limit_250 = L * 1000 / 250
    print(f"   Root reaction: V(0) = {result.reaction_V:.1f} kN, M(0) = {result.reaction_M:.1f} kN·m")
    print(f"   Max |V|:  {result.max_V:.1f} kN  @ X = {result.max_V_pos:.1f} m")
    print(f"   Max M:    {result.max_M:.1f} kN·m  @ X = {result.max_M_pos:.1f} m")
    print(f"   Max σ:    {result.max_sigma:.1f} MPa  @ X = {result.max_sigma_pos:.1f} m")
    print(f"   Tip δ:    {tip_mm:.1f} mm  (L/250 = {limit_250:.0f} mm) {'✅' if tip_mm < limit_250 else '⚠️'}")

    # Trolley sweep
    sweep_result = None
    if model.trolley_sweep:
        print("🔄 Sweeping trolley positions for worst case...")
        sweep_result = sweep_trolley(model)
        print(f"   Worst position:  {sweep_result.worst_position:.1f} m")
        print(f"   Worst moment:    {sweep_result.worst_moment:.1f} kN·m")
        print(f"   Worst tip δ:     {sweep_result.worst_deflection * 1000:.1f} mm")

    # Generate report
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
