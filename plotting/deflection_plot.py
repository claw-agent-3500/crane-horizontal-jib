"""Deflection curve plot."""

import numpy as np
from . import new_fig, fig_to_base64, style_ax, section_bands


def plot_deflection(result) -> str:
    fig, ax = new_fig()
    delta_mm = result.delta * 1000
    max_mm = delta_mm.max() if delta_mm.max() > 0 else 1
    section_bands(ax, result.sections, 0, max_mm * 1.15)
    ax.fill_between(result.x, delta_mm, alpha=0.4, color='#cba6f7', zorder=2)
    ax.plot(result.x, delta_mm, color='#cba6f7', linewidth=1.5, zorder=3)
    style_ax(ax, 'δ(x) Deflection (mm)', '#cba6f7')
    ax.set_title('Deflection Curve (downward = positive)', color='#cdd6f4', fontsize=12, fontweight='bold')
    ax.annotate(f'Tip δ = {result.tip_delta * 1000:.1f} mm\nat X = {result.x[-1]:.1f} m',
                xy=(result.x[-1], delta_mm[-1]), xytext=(-80, -30),
                textcoords='offset points', color='#cba6f7', fontsize=8,
                arrowprops=dict(arrowstyle='->', color='#cba6f7', lw=0.8))
    L = result.model.jib_length
    limit_mm = L * 1000 / 250
    ax.axhline(y=limit_mm, color='#f38ba8', linestyle='--', linewidth=0.8, alpha=0.6, zorder=1)
    ax.text(result.x[-1] * 0.98, limit_mm * 1.05, f'L/250 = {limit_mm:.0f} mm',
            ha='right', va='bottom', fontsize=7, color='#f38ba8', alpha=0.7)
    return fig_to_base64(fig)
