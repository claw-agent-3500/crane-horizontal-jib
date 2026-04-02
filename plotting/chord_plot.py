"""Chord forces plot."""

import numpy as np
from . import new_fig, fig_to_base64, style_ax, section_bands


def plot_chord_forces(result) -> str:
    fig, ax = new_fig()
    has_data = result.max_F_upper > 0 or result.max_F_lower > 0
    if not has_data:
        ax.text(0.5, 0.5, 'No truss config — chord forces not computed',
                ha='center', va='center', transform=ax.transAxes, color='#6c7086', fontsize=11)
        style_ax(ax, 'Force (kN)', '#cdd6f4')
        ax.set_title('Chord Forces', color='#cdd6f4', fontsize=12, fontweight='bold')
        return fig_to_base64(fig)

    max_force = max(result.max_F_upper, result.max_F_lower) * 1.15 or 1
    section_bands(ax, result.sections, -max_force, max_force)
    ax.fill_between(result.x, result.F_upper_chord, alpha=0.3, color='#f38ba8', label='Upper (comp)', zorder=2)
    ax.plot(result.x, result.F_upper_chord, color='#f38ba8', linewidth=1.5, label='Upper (comp)', zorder=3)
    ax.fill_between(result.x, result.F_lower_chord, alpha=0.3, color='#89b4fa', label='Lower (tens)', zorder=2)
    ax.plot(result.x, result.F_lower_chord, color='#89b4fa', linewidth=1.5, label='Lower (tens)', zorder=3)
    style_ax(ax, 'F_chord per chord (kN)', '#cdd6f4')
    ax.set_title('Chord Forces — F = M/h', color='#cdd6f4', fontsize=12, fontweight='bold')
    ax.legend(fontsize=8, facecolor='#1e1e2e', edgecolor='#555', labelcolor='#cdd6f4', loc='upper right')
    return fig_to_base64(fig)
