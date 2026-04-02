"""Diagonal forces plot."""

import numpy as np
from . import new_fig, fig_to_base64, style_ax, section_bands


def plot_diagonal_forces(result) -> str:
    fig, ax = new_fig()
    has_data = result.max_F_comp_diag > 0 or result.max_F_tens_diag > 0
    if not has_data:
        ax.text(0.5, 0.5, 'No truss config — diagonal forces not computed',
                ha='center', va='center', transform=ax.transAxes, color='#6c7086', fontsize=11)
        style_ax(ax, 'Force (kN)', '#cdd6f4')
        ax.set_title('Diagonal Forces', color='#cdd6f4', fontsize=12, fontweight='bold')
        return fig_to_base64(fig)

    all_abs = np.concatenate([np.abs(result.F_comp_diag), np.abs(result.F_tens_diag), np.abs(result.F_neut_diag)])
    max_force = all_abs.max() * 1.15 or 1
    section_bands(ax, result.sections, 0, max_force)

    if result.max_F_comp_diag > 0:
        ax.plot(result.x, np.abs(result.F_comp_diag), color='#f38ba8', linewidth=1.5, label='Compression diag', zorder=3)
    if result.max_F_tens_diag > 0:
        ax.plot(result.x, np.abs(result.F_tens_diag), color='#a6e3a1', linewidth=1.5, label='Tension diag', zorder=3)
    if np.any(result.F_neut_diag != 0):
        ax.plot(result.x, np.abs(result.F_neut_diag), color='#f9e2af', linewidth=1.0, linestyle='--', label='Neutral diag', zorder=3)

    style_ax(ax, '|F_diagonal| (kN)', '#cdd6f4')
    ax.set_title('Diagonal Forces — F = V/sin(θ)', color='#cdd6f4', fontsize=12, fontweight='bold')
    ax.legend(fontsize=8, facecolor='#1e1e2e', edgecolor='#555', labelcolor='#cdd6f4', loc='upper right')
    return fig_to_base64(fig)
