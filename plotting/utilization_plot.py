"""Utilization ratio plot along jib length."""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64


def plot_utilization(result) -> str:
    """
    Plot utilization ratio (sigma / yield_strength) along jib length.
    Shows limit lines at 0.7 (OK), 0.9 (warning), 1.0 (failure).
    """
    x = result.x
    model = result.model
    n = len(x)
    
    # Compute utilization at each point
    utilization = np.zeros(n)
    for j in range(n):
        xj = x[j]
        sec = None
        for s in model.sections:
            if s.start <= xj <= s.end:
                sec = s
                break
        if sec and sec.yield_strength > 0:
            utilization[j] = result.sigma[j] / sec.yield_strength
    
    fig, ax = plt.subplots(figsize=(12, 3.5))
    fig.patch.set_facecolor('#1e1e2e')
    ax.set_facecolor('#1e1e2e')
    
    # Plot line
    ax.fill_between(x, utilization * 100, alpha=0.3, color='#89b4fa', zorder=2)
    ax.plot(x, utilization * 100, color='#89b4fa', linewidth=1.5, zorder=3)
    
    # Limit lines
    ax.axhline(y=100, color='#f38ba8', linestyle='-', linewidth=1.5, alpha=0.8)
    ax.axhline(y=90, color='#f9e2af', linestyle='--', linewidth=1, alpha=0.6)
    ax.axhline(y=70, color='#a6e3a1', linestyle=':', linewidth=1, alpha=0.6)
    
    ax.set_xlabel('X — Position along jib (m)', color='#cdd6f4', fontsize=10)
    ax.set_ylabel('Utilization σ/f_y (%)', color='#cdd6f4', fontsize=10)
    ax.set_title('Utilization Ratio along Jib Length', color='#cdd6f4', fontsize=12, fontweight='bold')
    
    ax.set_ylim(0, max(utilization.max() * 110, 110))
    ax.axhline(y=0, color='#555', linewidth=0.5, zorder=1)
    ax.tick_params(colors='#aaa', labelsize=8)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('bottom', 'left'):
        ax.spines[s].set_color('#555')
    ax.grid(True, alpha=0.15, color='#888')
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#1e1e2e', edgecolor='none')
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return encoded
