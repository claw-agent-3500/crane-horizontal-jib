"""Wind-only SFD and BMD plot."""

import io
import base64
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def _fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#1e1e2e', edgecolor='none')
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return encoded


def plot_wind_diagram(model, wind_pressure: float, x: np.ndarray) -> str:
    """Plot SFD and BMD from wind loads only."""
    if wind_pressure <= 0:
        fig, ax = plt.subplots(figsize=(12, 3.5))
        fig.patch.set_facecolor('#1e1e2e')
        ax.set_facecolor('#1e1e2e')
        ax.text(0.5, 0.5, 'No wind pressure defined',
                ha='center', va='center', transform=ax.transAxes, color='#6c7086', fontsize=11)
        ax.set_xlabel('X — Position (m)', color='#cdd6f4')
        ax.set_ylabel('V (kN)', color='#89b4fa')
        ax.set_title('Wind Loads Diagram', color='#cdd6f4', fontsize=12, fontweight='bold')
        return _fig_to_base64(fig)
    
    from wind_analysis import compute_wind_loads
    
    wind = compute_wind_loads(model, x, wind_pressure)
    V_wind = wind['V']
    M_wind = wind['M']
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
    fig.patch.set_facecolor('#1e1e2e')
    
    for ax in (ax1, ax2):
        ax.set_facecolor('#1e1e2e')
        ax.tick_params(colors='#aaa', labelsize=8)
        for s in ('top', 'right'):
            ax.spines[s].set_visible(False)
        for s in ('bottom', 'left'):
            ax.spines[s].set_color('#555')
        ax.grid(True, alpha=0.15, color='#888')
    
    ax1.fill_between(x, V_wind, alpha=0.4, color='#89b4fa', zorder=2)
    ax1.plot(x, V_wind, color='#89b4fa', linewidth=1.5, zorder=3)
    ax1.axhline(y=0, color='#555', linewidth=0.5, zorder=1)
    ax1.set_ylabel('V (kN)', color='#89b4fa', fontsize=10)
    ax1.set_title(f'Wind Loads Only (pressure = {wind_pressure} Pa)', color='#cdd6f4', fontsize=12, fontweight='bold')
    
    ax2.fill_between(x, M_wind, alpha=0.4, color='#89b4fa', zorder=2)
    ax2.plot(x, M_wind, color='#89b4fa', linewidth=1.5, zorder=3)
    ax2.axhline(y=0, color='#555', linewidth=0.5, zorder=1)
    ax2.set_ylabel('M (kN·m)', color='#89b4fa', fontsize=10)
    ax2.set_xlabel('X — Position (m)', color='#cdd6f4', fontsize=10)
    
    fig.tight_layout()
    return _fig_to_base64(fig)
