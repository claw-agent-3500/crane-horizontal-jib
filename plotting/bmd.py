"""Bending Moment Diagram plot."""

from . import new_fig, fig_to_base64, style_ax, section_bands


def plot_bmd(result) -> str:
    fig, ax = new_fig()
    section_bands(ax, result.sections, 0, result.max_M * 1.15)
    ax.fill_between(result.x, result.M, alpha=0.4, color='#a6e3a1', zorder=2)
    ax.plot(result.x, result.M, color='#a6e3a1', linewidth=1.5, zorder=3)
    style_ax(ax, 'M(x) Bending Moment (kN·m)', '#a6e3a1')
    ax.set_title('Bending Moment Diagram (BMD)', color='#cdd6f4', fontsize=12, fontweight='bold')
    ax.annotate(f'Max M = {result.max_M:.1f} kN·m\nat X = {result.max_M_pos:.1f} m',
                xy=(result.max_M_pos, result.max_M), xytext=(20, -30),
                textcoords='offset points', color='#a6e3a1', fontsize=8,
                arrowprops=dict(arrowstyle='->', color='#a6e3a1', lw=0.8))
    return fig_to_base64(fig)
