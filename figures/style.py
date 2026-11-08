"""
Shared figure style for the MTAP journal paper (ticket #13).

Every paper figure is drawn at its final printed size so that the text in
the PDF has the font sizes set here (no LaTeX `scale=`). The page is the
single-column sn-jnl layout: \\textwidth = 372pt.

Rules every figure follows:
  - no in-chart titles (the caption carries that information)
  - every axis label has units where the quantity has units
  - the same wording for the same quantity (see LABELS)
  - the same colours for the same entity (see colour constants)
"""

import os

import matplotlib as mpl
import matplotlib.pyplot as plt

# ---------------------------------------------------------------- page sizes
PT_PER_INCH = 72.27
TEXT_WIDTH = 372 / PT_PER_INCH            # 5.15 in, full text width
HALF_WIDTH = 0.48 * TEXT_WIDTH            # one panel of a side-by-side pair

# ---------------------------------------------------------------- font sizes
FONT_SIZE = 9          # axis labels
TICK_SIZE = 8          # tick labels
LEGEND_SIZE = 8
SMALL_LEGEND_SIZE = 7  # legends of half-width panels
ANNOT_SIZE = 8         # numbers written inside the plot (cells, bars)
SMALL_ANNOT_SIZE = 6.5  # numbers inside narrow bar segments

# ---------------------------------------------------------------- wording
GAMES = ["Call of Duty", "Free Fire", "PUBG", "Guns of Boom"]

CLASSES_3 = ["Bad", "Fair", "Excellent"]
CLASSES_5 = ["Bad", "Poor", "Fair", "Good", "Excellent"]

LABELS = {
    "c2s": "Client-to-server",
    "s2c": "Server-to-client",
    "ping": "Ping (ms)",
    "pps": "Packets per second",
    "pkt_size": "Average packet size (bytes)",
    "time": "Gameplay time (s)",
    "duration": "Match duration (s)",
    "samples": "Number of samples",
    "true": "True class",
    "pred": "Predicted class",
}

# ---------------------------------------------------------------- colours
# QoE classes, worst -> best. ColorBrewer RdYlBu: colour-blind safe and
# prints in greyscale as a monotone ramp.
CLASS_COLORS_5 = ["#d7191c", "#fdae61", "#ffffbf", "#abd9e9", "#2c7bb6"]
CLASS_COLORS_3 = [CLASS_COLORS_5[0], CLASS_COLORS_5[2], CLASS_COLORS_5[4]]

# Traffic direction (Okabe-Ito vermillion / blue).
DIRECTION_COLORS = {"c2s": "#D55E00", "s2c": "#0072B2"}

NEUTRAL = "#4C72B0"    # single-series plots
HEATMAP_CMAP = "Blues"

EDGE_COLOR = "#333333"


def apply():
    """Set matplotlib rcParams for all paper figures."""
    mpl.rcParams.update({
        # Computer Modern, matching the paper's Latin Modern body text.
        # cmr10 ships with matplotlib as TrueType, so it embeds cleanly as
        # Type 42 (the Latin Modern .otf files embed as mismatched CFF).
        "font.family": "serif",
        "font.serif": ["cmr10"],
        "mathtext.fontset": "cm",
        "axes.formatter.use_mathtext": True,
        "axes.unicode_minus": False,
        "font.size": FONT_SIZE,
        "axes.labelsize": FONT_SIZE,
        "axes.titlesize": FONT_SIZE,
        "xtick.labelsize": TICK_SIZE,
        "ytick.labelsize": TICK_SIZE,
        "legend.fontsize": LEGEND_SIZE,
        "legend.frameon": False,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "lines.linewidth": 1.0,
        "lines.markersize": 3,
        "grid.linewidth": 0.4,
        "grid.linestyle": "--",
        "grid.alpha": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 150,
        # Fixed canvas: the saved file is exactly figsize, so LaTeX includes
        # it at natural size and never rescales the fonts. Constrained
        # layout keeps labels and legends inside that canvas.
        "figure.constrained_layout.use": True,
        "figure.constrained_layout.h_pad": 0.02,
        "figure.constrained_layout.w_pad": 0.02,
        "savefig.dpi": 600,
        "savefig.bbox": None,
        # embed TrueType so text stays selectable and editable in the PDF
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def thousands(x, _pos=None):
    return f"{x:,.0f}"


def save(fig, out_dir, name):
    """Write <name>.pdf (used by LaTeX) and a 600-dpi <name>.png fallback.

    Refuses to save a figure that has an in-chart title.
    """
    for ax in fig.axes:
        if ax.get_title():
            raise ValueError(f"{name}: axis title '{ax.get_title()}' — move it to the caption")
    if fig._suptitle is not None:
        raise ValueError(f"{name}: suptitle present — move it to the caption")
    os.makedirs(out_dir, exist_ok=True)
    for ext in ("pdf", "png"):
        path = os.path.join(out_dir, f"{name}.{ext}")
        fig.savefig(path)
        print(f"Saved: {path}")
    plt.close(fig)
