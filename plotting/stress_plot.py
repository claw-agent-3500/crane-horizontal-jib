"""Stress distribution plot."""

import numpy as np
from . import new_fig, fig_to_base64, style_ax, section_bands


def plot_stress(result) -> str:
    fig, ax = new_fig()
    section_bands(ax, result.sections, 0, result.max_sigma * 1.15)
    ax.fill_between(result.x, result.sigma, alpha=0.3, color='#89b4fa', label='Bending σ', zorder=2)
    ax.plot(result.x, result.sigma, color='#89b4fa', linewidth=1.5, label='Bending σ', zorder=3)
    ax.fill_between(result.x, np.abs(result.tau), alpha=0.2, color='#f9e2af', label='Shear τ (avg)', zorder=2)
    ax.plot(result.x, np.abs(result.tau), color='#f9e2af', linewidth=1.0,
            linestyle='--', label='Shear τ (avg)', zorder=3)
    style_ax(ax, 'Stress (MPa)', '#cdd6f4')
    ax.set_title('Stress Distribution along X', color='#cdd6f4', fontsize=12, fontweight='bold')
    ax.legend(fontsize=8, facecolor='#1e1e2e', edgecolor='#555', labelcolor='#cdd6f4', loc='upper right')
    return fig_to_base64(fig)
