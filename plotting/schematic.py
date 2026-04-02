"""Jib schematic (X-Y side view)."""

from . import new_fig, fig_to_base64, DARK_BG


def plot_schematic(model) -> str:
    fig, ax = new_fig(figsize=(12, 2.5))
    colors = ['#f38ba8', '#a6e3a1', '#89b4fa', '#f9e2af', '#cba6f7',
              '#94e2d5', '#fab387', '#74c7ec']

    for i, sec in enumerate(model.sections):
        h = sec.height
        color = colors[i % len(colors)]
        rect = __import__('matplotlib').patches.Rectangle(
            (sec.start, -h/2), sec.length, h,
            facecolor=color, alpha=0.25, edgecolor=color, linewidth=1.5, zorder=2)
        ax.add_patch(rect)
        mid = (sec.start + sec.end) / 2
        ax.text(mid, h/2 + 0.15, sec.name, ha='center', va='bottom',
                fontsize=7, color=color, fontweight='bold')
        weight_label = f'{sec.weight_per_length} kN/m'
        if sec.truss:
            uc = sec.truss.upper_chords
            lc = sec.truss.lower_chords
            weight_label += f'  [{uc}U+{lc}L]'
        ax.text(mid, -h/2 - 0.15, weight_label, ha='center', va='top', fontsize=6, color='#aaa')

    for pl in model.point_loads:
        ax.annotate('', xy=(pl.position, -2.8), xytext=(pl.position, -2.2),
                    arrowprops=dict(arrowstyle='->', color='#f38ba8', lw=1.5))
        ax.text(pl.position, -3.0, f'{pl.name}\n{pl.magnitude} kN',
                ha='center', va='top', fontsize=6, color='#f38ba8')

    for udl in model.udls:
        mid = (udl.start + udl.end) / 2
        ax.annotate('', xy=(mid, -2.8), xytext=(mid, -2.2),
                    arrowprops=dict(arrowstyle='->', color='#f9e2af', lw=1.5))
        ax.text(mid, -3.0, f'{udl.name}\n{udl.magnitude} kN/m',
                ha='center', va='top', fontsize=6, color='#f9e2af')

    ax.annotate('FIXED\n(ROOT)\nX = 0', xy=(0, 0), xytext=(-3, 0),
                fontsize=7, color='#cdd6f4', ha='center', va='center',
                arrowprops=dict(arrowstyle='->', color='#cdd6f4', lw=1.2))
    ax.annotate('X →', xy=(model.jib_length * 0.95, 1.8), fontsize=7, color='#6c7086', ha='center')
    ax.annotate('Y ↑', xy=(-1.5, 1.5), fontsize=7, color='#6c7086', ha='center')

    ax.set_xlim(-4, model.jib_length + 2)
    ax.set_ylim(-3.8, 2.5)
    ax.set_xlabel('X — Longitudinal (m)', color='#cdd6f4', fontsize=10)
    ax.set_title(f'Jib Side View (X-Y) — {model.name}', color='#cdd6f4', fontsize=12, fontweight='bold')
    ax.axhline(y=0, color='#555', linewidth=0.5, zorder=1)
    ax.tick_params(colors='#aaa', labelsize=8)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('bottom', 'left'):
        ax.spines[s].set_color('#555')
    ax.grid(True, alpha=0.1, color='#888')
    return fig_to_base64(fig)
