"""Trolley position sweep plot."""

import matplotlib.pyplot as plt
from . import fig_to_base64, DARK_BG


def plot_sweep(sweep) -> str:
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    fig.patch.set_facecolor(DARK_BG)

    for ax in (ax1, ax2, ax3):
        ax.set_facecolor(DARK_BG)
        ax.tick_params(colors='#aaa', labelsize=8)
        for s in ('top', 'right'):
            ax.spines[s].set_visible(False)
        for s in ('bottom', 'left'):
            ax.spines[s].set_color('#555')
        ax.grid(True, alpha=0.15, color='#888')
        ax.axvline(sweep.worst_position, color='#f38ba8', linestyle='--', alpha=0.5, linewidth=0.8)

    ax1.plot(sweep.positions, sweep.root_moments, color='#a6e3a1', linewidth=1.5)
    ax1.scatter([sweep.worst_position], [sweep.worst_moment], color='#f38ba8', s=40, zorder=5)
    ax1.set_ylabel('Root Moment (kN·m)', color='#a6e3a1', fontsize=10)
    ax1.set_title('Trolley Position Sweep — Worst Case', color='#cdd6f4', fontsize=12, fontweight='bold')
    ax1.annotate(f'Worst: {sweep.worst_moment:.1f} kN·m @ {sweep.worst_position:.1f} m',
                 xy=(sweep.worst_position, sweep.worst_moment), xytext=(20, 0),
                 textcoords='offset points', color='#f38ba8', fontsize=8)

    ax2.plot(sweep.positions, sweep.root_shears, color='#f38ba8', linewidth=1.5)
    ax2.set_ylabel('Root Shear (kN)', color='#f38ba8', fontsize=10)

    ax3.plot(sweep.positions, sweep.tip_deflections * 1000, color='#cba6f7', linewidth=1.5)
    ax3.set_ylabel('Tip Deflection (mm)', color='#cba6f7', fontsize=10)
    ax3.set_xlabel('Trolley Position (m from root)', color='#cdd6f4', fontsize=10)

    fig.tight_layout()
    return fig_to_base64(fig)
