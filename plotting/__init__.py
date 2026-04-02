"""Shared plotting utilities and styles."""

import io
import base64

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


DARK_BG = '#1e1e2e'
BAND_COLORS = ['#2a2a3e', '#252540']


def fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor=DARK_BG, edgecolor='none')
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return encoded


def style_ax(ax, ylabel: str, ycolor: str):
    ax.set_facecolor(DARK_BG)
    ax.set_xlabel('X — Position along jib (m)', color='#cdd6f4', fontsize=10)
    ax.set_ylabel(ylabel, color=ycolor, fontsize=10)
    ax.axhline(y=0, color='#555', linewidth=0.5, zorder=1)
    ax.tick_params(colors='#aaa', labelsize=8)
    for spine in ('top', 'right'):
        ax.spines[spine].set_visible(False)
    for spine in ('bottom', 'left'):
        ax.spines[spine].set_color('#555')
    ax.grid(True, alpha=0.15, color='#888')


def section_bands(ax, sections, ymin: float, ymax: float):
    for i, sec in enumerate(sections):
        ax.axvspan(sec.start, sec.end, alpha=0.3, color=BAND_COLORS[i % 2], zorder=0)
        mid = (sec.start + sec.end) / 2
        ax.text(mid, ymax * 0.92, sec.name, ha='center', va='top',
                fontsize=6, color='#888', alpha=0.8, clip_on=True)


def new_fig(figsize=(12, 3.5)):
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(DARK_BG)
    return fig, ax
