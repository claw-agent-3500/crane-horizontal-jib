"""3D visualization of crane jib structure."""

import numpy as np
import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D


def plot_3d_schematic(model, result=None) -> str:
    """
    Generate 3D schematic of the crane jib with truss structure.
    
    Shows:
    - Jib outline with sections
    - Upper and lower chords
    - Diagonal members
    - Load points
    """
    fig = plt.figure(figsize=(14, 8))
    fig.patch.set_facecolor('#1e1e2e')
    ax = fig.add_subplot(111, projection='3d')
    ax.set_facecolor('#1e1e2e')
    
    # Jib length and height
    L = model.jib_length
    H = model.jib_height_position
    truss_height = 1.5  # assumed truss depth
    
    # Upper chord (top)
    x_upper = np.linspace(0, L, 50)
    y_upper = np.full_like(x_upper, H + truss_height/2)
    z_upper = np.zeros_like(x_upper)
    ax.plot(x_upper, y_upper, z_upper, 'b-', linewidth=2, label='Upper chord', alpha=0.8)
    
    # Lower chord (bottom)
    x_lower = np.linspace(0, L, 50)
    y_lower = np.full_like(x_lower, H - truss_height/2)
    z_lower = np.zeros_like(x_lower)
    ax.plot(x_lower, y_lower, z_lower, 'r-', linewidth=2, label='Lower chord', alpha=0.8)
    
    # Vertical ends
    ax.plot([0, 0], [H - truss_height/2, H + truss_height/2], [0, 0], 'k-', linewidth=3)
    ax.plot([L, L], [H - truss_height/2, H + truss_height/2], [0, 0], 'k-', linewidth=3)
    
    # Diagonal members (sample)
    n_diagonals = 10
    for i in range(n_diagonals):
        x1 = i * L / n_diagonals
        x2 = (i + 1) * L / n_diagonals
        
        # X-bracing pattern
        ax.plot([x1, x2], [H - truss_height/2, H + truss_height/2], [0, 0], 
                'g--', alpha=0.4, linewidth=0.8)
        ax.plot([x1, x2], [H + truss_height/2, H - truss_height/2], [0, 0], 
                'g--', alpha=0.4, linewidth=0.8)
    
    # Point loads
    for pl in model.point_loads:
        ax.scatter([pl.position], [H], [0], c='orange', s=100, marker='^', 
                   edgecolors='black', linewidth=1, zorder=5)
        ax.text(pl.position, H + 0.5, 0, f'{pl.magnitude:.0f} kN', 
                color='orange', fontsize=8)
    
    # UDLs
    for udl in model.udls:
        x_udl = np.linspace(udl.start, udl.end, 10)
        y_udl = np.full_like(x_udl, H)
        ax.plot(x_udl, y_udl, np.zeros_like(x_udl), 'orange', linewidth=2, alpha=0.5)
    
    # Trolley position
    if model.trolley:
        tx = model.trolley.max_position
        ax.scatter([tx], [H + truss_height/2 + 0.3], [0], c='cyan', s=150, 
                   marker='s', edgecolors='white', linewidth=2, zorder=6)
        ax.text(tx, H + truss_height + 0.5, 0, 'Trolley', color='cyan', fontsize=9)
    
    # Section markers
    for sec in model.sections:
        ax.axvline(x=sec.start, color='gray', linestyle=':', alpha=0.5)
        ax.text(sec.start, H - truss_height - 0.3, 0, sec.name, 
                color='gray', fontsize=7)
    
    # Labels and styling
    ax.set_xlabel('X - Along jib (m)', color='#aaa', fontsize=10)
    ax.set_ylabel('Y - Vertical (m)', color='#aaa', fontsize=10)
    ax.set_zlabel('Z - Width (m)', color='#aaa', fontsize=10)
    ax.set_title('Crane Jib - 3D Truss Schematic', color='#fff', fontsize=14, fontweight='bold')
    
    # Set axis limits
    ax.set_xlim(0, L * 1.05)
    ax.set_ylim(H - truss_height - 0.5, H + truss_height + 1)
    ax.set_zlim(-0.5, 0.5)
    
    # Legend
    ax.plot([], [], 'b-', linewidth=2, label='Upper chord (compression)')
    ax.plot([], [], 'r-', linewidth=2, label='Lower chord (tension)')
    ax.plot([], [], 'g--', linewidth=1, label='Diagonals')
    ax.legend(loc='upper right', facecolor='#1e1e2e', edgecolor='#555', 
              labelcolor='#aaa', fontsize=8)
    
    # Style
    ax.tick_params(colors='#888')
    for spine in ax.spines.values():
        spine.set_color('#555')
    
    # Save
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', 
                facecolor='#1e1e2e', edgecolor='none')
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return encoded