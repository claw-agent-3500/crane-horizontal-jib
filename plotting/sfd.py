"""Shear Force Diagram plot."""

import numpy as np
from . import new_fig, fig_to_base64, style_ax, section_bands


def plot_sfd(result) -> str:
    fig, ax = new_fig()
    section_bands(ax, result.sections, 0, result.max_V * 1.15)
    ax.fill_between(result.x, result.V, alpha=0.4, color='#f38ba8', zorder=2)
    ax.plot(result.x, result.V, color='#f38ba8', linewidth=1.5, zorder=3)
    style_ax(ax, 'V(x) Shear Force (kN)', '#f38ba8')
    ax.set_title('Shear Force Diagram (SFD)', color='#cdd6f4', fontsize=12, fontweight='bold')
    idx = np.argmin(np.abs(result.x - result.max_V_pos))
    ax.annotate(f'Max |V| = {result.max_V:.1f} kN\nat X = {result.max_V_pos:.1f} m',
                xy=(result.max_V_pos, result.V[idx]),
                xytext=(20, 20), textcoords='offset points', color='#f38ba8', fontsize=8,
                arrowprops=dict(arrowstyle='->', color='#f38ba8', lw=0.8))
    return fig_to_base64(fig)
