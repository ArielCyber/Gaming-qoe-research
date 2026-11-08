"""
Regenerate the MTAP journal paper figures with one shared style (ticket #13).

Usage:
    python figures/fetch_data.py          # once: inputs into datasets/paper_figures
    python figures/make_all.py [--only fig09 fig11] [--data-dir DIR] [--out-dir paper]

--data-dir (default datasets/paper_figures) holds the files that
figures/fetch_data.py collects from Google Drive. See figures/README.md for
which figure needs which file. Figures that only use numbers reported in the
paper (fig10, fig11, fig13) need no data.

Output: <out-dir>/<name>.pdf (included by LaTeX) and <name>.png (600 dpi).
MTAP requires all figure files at the paper root, so --out-dir defaults to paper/.
"""

import argparse
import ast
import os
import sys

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import style  # noqa: E402
from rank import (  # noqa: E402
    rank_qoe,
    rank_qoe_3_classes,
    rank_str_to_int_mapping,
    rank_str_to_int_mapping_3_classes,
)

# Per-game files, in style.GAMES order.
DATA_FILES = {
    # the frozen paper datasets: 10-second windows, one row per labelled second
    "datasets": {
        "Call of Duty": "features_cod_10s_paper.csv",
        "Free Fire": "features_freefire_10s_paper.csv",
        "PUBG": "features_pubg_10s_paper.csv",
        "Guns of Boom": "features_gob_10s_paper.csv",
    },
    # per-match statistics
    "statistics": {
        "Call of Duty": "matches_cod.csv",
        "Free Fire": "matches_freefire.csv",
        "PUBG": "matches_pubg.csv",
        "Guns of Boom": "matches_gob.csv",
    },
    "pubg_metadata": "labels_pubg.csv",
}

SECONDS_PER_DAY = 86400

# two-line tick labels for narrow (half-width) panels
SHORT_TICK = {"Call of Duty": "Call of\nDuty", "Free Fire": "Free\nFire",
              "Guns of Boom": "Guns of\nBoom"}


# --------------------------------------------------------- Figs. 2-7 (CoD)
COD_WINDOWS = "conference_cod_experiments_10s.csv"   # CoD experiments, one row per second
EXAMPLE_EXP = 7                            # the match shown in Figs. 2-4 (95 ms)
EXAMPLE_ROWS = slice(50, 320)              # gameplay time 80-349 s, as submitted
# The 22 experiments labelled in the submitted Fig. 7 (it used an unseeded sample).
FIG7_EXPERIMENTS = [102, 13, 24, 35, 107, 26, 60, 79, 49, 87, 7,
                    33, 84, 34, 19, 32, 72, 91, 66, 93, 78, 77]
WIDE = (style.TEXT_WIDTH * 0.8, 2.4)


def _cod_windows(data_dir):
    return pd.read_csv(os.path.join(data_dir, COD_WINDOWS))


def _cod_per_experiment(data_dir):
    """Median of each feature per experiment; each experiment has one ping value."""
    df = _cod_windows(data_dir)
    return df.groupby(["exp_id", "ping"]).agg(
        c2s_pps=("src2dst_pps", "median"), s2c_pps=("dst2src_pps", "median"),
        c2s_size=("src2dst_avg_pkt_size", "median"),
        s2c_size=("dst2src_avg_pkt_size", "median"),
    ).reset_index()


def _direction_plot(ax, x, c2s, s2c, size=6):
    ax.scatter(x, c2s, s=size, marker="o", color=style.DIRECTION_COLORS["c2s"],
               label=style.LABELS["c2s"], linewidths=0)
    ax.scatter(x, s2c, s=size, marker="s", color=style.DIRECTION_COLORS["s2c"],
               label=style.LABELS["s2c"], linewidths=0)
    ax.grid(True)
    ax.set_axisbelow(True)
    ax.legend(loc="upper right", markerscale=1.5, handletextpad=0.2)


def _example_match(data_dir, rows=None):
    df = _cod_windows(data_dir)
    match = df[df["exp_id"] == EXAMPLE_EXP]
    return match.iloc[rows] if rows is not None else match


def fig02_bandwidth(data_dir, out_dir):
    m = _example_match(data_dir)
    fig, ax = plt.subplots(figsize=WIDE)
    _direction_plot(ax, m["pktIdx"], m["src2dst_bytes"], m["dst2src_bytes"])
    ax.legend(loc="center right", markerscale=1.5, handletextpad=0.2)  # top right holds peaks
    ax.set_xlabel(style.LABELS["time"])
    ax.set_ylabel("Bytes per second")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(style.thousands))
    style.save(fig, out_dir, "Bandwidth_vs_Gameplay_Time")


def fig03_pps(data_dir, out_dir):
    m = _example_match(data_dir, EXAMPLE_ROWS)
    fig, ax = plt.subplots(figsize=WIDE)
    _direction_plot(ax, m["pktIdx"], m["src2dst_pps"], m["dst2src_pps"])
    ax.set_xlabel(style.LABELS["time"])
    ax.set_ylabel(style.LABELS["pps"])
    style.save(fig, out_dir, "PPS_Raw_vs_Gameplay_Time")


def fig04_pps_median(data_dir, out_dir):
    m = _example_match(data_dir, EXAMPLE_ROWS)
    fig, ax = plt.subplots(figsize=WIDE)
    _direction_plot(ax, m["pktIdx"], m["src2dst_pps_median"], m["dst2src_pps_median"])
    ax.set_xlabel(style.LABELS["time"])
    ax.set_ylabel("Packets per second (10-s median)")
    style.save(fig, out_dir, "PPS_vs_Gameplay_Time_median")


def fig05_pps_vs_ping(data_dir, out_dir):
    a = _cod_per_experiment(data_dir)
    fig, ax = plt.subplots(figsize=WIDE)
    _direction_plot(ax, a["ping"], a["c2s_pps"], a["s2c_pps"], size=10)
    ax.legend(loc="upper left", markerscale=1.2, handletextpad=0.2)
    ax.set_xlabel(style.LABELS["ping"])
    ax.set_ylabel("Median packets per second")
    style.save(fig, out_dir, "PPS_vs_Ping_Rate")


def fig06_size_vs_ping(data_dir, out_dir):
    a = _cod_per_experiment(data_dir)
    fig, ax = plt.subplots(figsize=WIDE)
    _direction_plot(ax, a["ping"], a["c2s_size"], a["s2c_size"], size=10)
    ax.legend(loc="center right", markerscale=1.2, handletextpad=0.2)
    ax.set_xlabel(style.LABELS["ping"])
    ax.set_ylabel("Median " + style.LABELS["pkt_size"][0].lower() + style.LABELS["pkt_size"][1:])
    style.save(fig, out_dir, "Ping_vs_Average_Packet_Size")


def _place_labels(ax, xs, ys, texts, fontsize):
    """Put each label at the first offset whose box overlaps no marker or earlier label."""
    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    pts = ax.transData.transform(np.column_stack([xs, ys]))
    marker_r = 3.0 * fig.dpi / 72
    taken = []
    offsets = [(4, 3), (4, -9), (-4, 3), (-4, -9), (0, 6), (0, -12), (8, -3), (-8, -3)]
    for (px, py), x, y, txt in zip(pts, xs, ys, texts):
        chosen = None
        for dx, dy in offsets:
            ha = "left" if dx > 0 else "right" if dx < 0 else "center"
            t = ax.annotate(txt, (x, y), xytext=(dx, dy), textcoords="offset points",
                            ha=ha, va="bottom", fontsize=fontsize)
            bb = t.get_window_extent(renderer).expanded(1.05, 1.1)
            hits_marker = any(bb.x0 - marker_r < qx < bb.x1 + marker_r and
                              bb.y0 - marker_r < qy < bb.y1 + marker_r for qx, qy in pts)
            if not hits_marker and not any(bb.overlaps(o) for o in taken):
                chosen = (t, bb)
                break
            t.remove()
        if chosen is None:   # nothing free: keep the first offset
            t = ax.annotate(txt, (x, y), xytext=offsets[0], textcoords="offset points",
                            ha="left", va="bottom", fontsize=fontsize)
            chosen = (t, t.get_window_extent(renderer))
        taken.append(chosen[1])


def fig07_c2s_vs_s2c(data_dir, out_dir):
    a = _cod_per_experiment(data_dir).set_index("exp_id").loc[FIG7_EXPERIMENTS].reset_index()
    fig, ax = plt.subplots(figsize=WIDE)
    ax.scatter(a["c2s_pps"], a["s2c_pps"], s=12, color=style.NEUTRAL, linewidths=0)
    ax.grid(True)
    ax.set_axisbelow(True)
    ax.set_xlabel("Client-to-server packets per second (median)")
    ax.set_ylabel("Server-to-client packets\nper second (median)")
    ax.margins(x=0.08, y=0.12)
    _place_labels(ax, a["c2s_pps"].values, a["s2c_pps"].values,
                  [f"{p:.0f}" for p in a["ping"]], style.SMALL_LEGEND_SIZE)
    style.save(fig, out_dir, "Client_to_Server_vs_Server_to_Client_PPS")


# ------------------------------------------------------------------ Fig. 8
PUBG_BALANCING_RUNS = [
    "2026-05-03__14-27-32", "2026-05-03__16-37-14", "2026-05-03__17-04-25",
    "2026-05-03__17-14-27", "2026-05-03__19-16-05", "2026-05-03__19-47-23",
    "2026-05-03__20-02-58",
]


def _hhmmss_to_seconds(t):
    t = int(t)
    return t // 10000 * 3600 + (t // 100) % 100 * 60 + t % 100


def _metadata_durations(data_dir, folders):
    """Match duration = last - first labelled timestamp (data_statitsic.py)."""
    meta = pd.read_csv(os.path.join(data_dir, DATA_FILES["pubg_metadata"]))
    meta = meta[meta["folder"].isin(folders)]
    if len(meta) != len(folders):
        raise ValueError(f"expected {len(folders)} PUBG runs in metadata, found {len(meta)}")
    out = []
    for pairs in meta["time_value_pairs"]:
        times = [k for k, v in ast.literal_eval(pairs).items() if v is not None]
        d = _hhmmss_to_seconds(times[-1]) - _hhmmss_to_seconds(times[0])
        out.append(d if d > 0 else d + SECONDS_PER_DAY)
    return pd.Series(out, dtype=float)


def fig08_duration(data_dir, out_dir):
    durations = []
    for game in style.GAMES:
        df = pd.read_csv(os.path.join(data_dir, DATA_FILES["statistics"][game]))
        d = df.loc[df["folder"] != "average", "duration"].astype(float)
        # Matches that cross midnight were computed as end - start on the
        # clock time and came out ~ -86400 s; add the day back.
        d = d.where(d > 0, d + SECONDS_PER_DAY)
        if game == "PUBG":
            # PUBG_statistics.csv predates the 7 balancing runs of 2026-05-03
            # (177 + 7 = the 184 matches in the paper); take their durations
            # from the label metadata, as data_statitsic.py does.
            d = pd.concat([d, _metadata_durations(data_dir, PUBG_BALANCING_RUNS)])
        durations.append(d.values)

    fig, ax = plt.subplots(figsize=(style.TEXT_WIDTH * 0.8, 2.4))
    ax.boxplot(durations, widths=0.5, patch_artist=True,
               boxprops=dict(facecolor=style.NEUTRAL, alpha=0.35, edgecolor=style.EDGE_COLOR),
               medianprops=dict(color=style.EDGE_COLOR, linewidth=1.2),
               whiskerprops=dict(color=style.EDGE_COLOR),
               capprops=dict(color=style.EDGE_COLOR),
               flierprops=dict(marker="o", markersize=2.5, markerfacecolor="none",
                               markeredgecolor=style.EDGE_COLOR, markeredgewidth=0.5))
    ax.set_xticks(range(1, len(style.GAMES) + 1), style.GAMES)
    ax.set_ylabel(style.LABELS["duration"])
    ax.grid(axis="y")
    ax.set_axisbelow(True)
    style.save(fig, out_dir, "duration_distribution_per_game")


# ------------------------------------------------------------------ Fig. 9
def _class_counts(data_dir, rank_fn, mapping, n_classes):
    counts = {}
    for game in style.GAMES:
        path = os.path.join(data_dir, DATA_FILES["datasets"][game])
        ping = pd.read_csv(path, usecols=["ping"], low_memory=False)["ping"].dropna()
        labels = ping.map(lambda p: mapping[rank_fn(p)])
        counts[game] = [int((labels == c).sum()) for c in range(1, n_classes + 1)]
    return pd.DataFrame(counts, index=range(1, n_classes + 1))


def _stacked_bars(counts, class_names, colors, out_dir, name):
    fig, ax = plt.subplots(figsize=(style.HALF_WIDTH, 2.6))
    x = np.arange(counts.shape[1])
    bottom = np.zeros(counts.shape[1])
    label_min = 0.05 * counts.sum().max()
    for cls, cname, color in zip(counts.index, class_names, colors):
        vals = counts.loc[cls].values
        ax.bar(x, vals, 0.6, bottom=bottom, color=color, label=cname,
               edgecolor=style.EDGE_COLOR, linewidth=0.3)
        for xi, v, b in zip(x, vals, bottom):
            if v >= label_min:
                ax.text(xi, b + v / 2, f"{v:,}", ha="center", va="center",
                        fontsize=style.SMALL_ANNOT_SIZE)
        bottom += vals
    ax.set_xticks(x, [SHORT_TICK.get(g, g) for g in counts.columns])
    ax.set_ylabel(style.LABELS["samples"])
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(style.thousands))
    # one legend row in both panels so the (a)/(b) axes line up
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=len(class_names),
              fontsize=style.SMALL_LEGEND_SIZE, handlelength=0.8,
              handletextpad=0.3, columnspacing=0.6, borderaxespad=0.2)
    style.save(fig, out_dir, name)


def fig09_label_distribution(data_dir, out_dir):
    c3 = _class_counts(data_dir, rank_qoe_3_classes, rank_str_to_int_mapping_3_classes, 3)
    print("3-class counts:\n", c3)
    _stacked_bars(c3, style.CLASSES_3, style.CLASS_COLORS_3, out_dir, "label_distribution_3class")
    c5 = _class_counts(data_dir, rank_qoe, rank_str_to_int_mapping, 5)
    print("5-class counts:\n", c5)
    _stacked_bars(c5, style.CLASSES_5, style.CLASS_COLORS_5, out_dir, "label_distribution_5class")


# ------------------------------------------------------- Figs. 11 and 13
def _matrix_heatmap(data, fmt, xlabel, ylabel, out_dir, name, cbar_label=None):
    fig, ax = plt.subplots(figsize=(style.TEXT_WIDTH * 0.6, 2.5))
    im = ax.imshow(data, cmap=style.HEATMAP_CMAP)
    n = data.shape[0]
    threshold = data.max() / 2
    for i in range(n):
        for j in range(n):
            ax.text(j, i, format(data[i, j], fmt), ha="center", va="center",
                    fontsize=style.ANNOT_SIZE,
                    color="white" if data[i, j] > threshold else "black")
    ax.set_xticks(range(n), style.CLASSES_3)
    ax.set_yticks(range(n), style.CLASSES_3)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.tick_params(length=0)
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.tick_params(labelsize=style.TICK_SIZE, width=0.6)
    cbar.outline.set_linewidth(0.6)
    if fmt == ",.0f":
        cbar.ax.yaxis.set_major_formatter(mticker.FuncFormatter(style.thousands))
    if cbar_label:
        cbar.set_label(cbar_label)
    style.save(fig, out_dir, name)


def fig10_cod_xgb_confusion(_data_dir, out_dir):
    # XGBoost on CoD, 3-class, no SMOTE: the run saved in
    # Call_of_Duty_data/results/new_ficherse/class_3/no_smote/XGBoost (2026-04-28),
    # whose results CSV is the CoD table. Recalls 0.930 / 0.841 / 0.932 as in the text.
    cm = np.array([
        [27253, 1679, 386],
        [1644, 12731, 761],
        [890, 938, 24887],
    ], dtype=float)
    _matrix_heatmap(cm, ",.0f", style.LABELS["pred"], style.LABELS["true"],
                    out_dir, "cm_XGB_class3_smoteFalse_",
                    cbar_label="Number of samples")


def fig11_transition_matrix(_data_dir, out_dir):
    # Values reported in Sec. 5 (QoE Transition Matrix Analysis):
    # Bad/Excellent self = 94.4 %, Fair self = 89.0 %, Excellent -> Bad = 2.3 %.
    tm = np.array([
        [94.4, 3.5, 2.2],
        [6.1, 89.0, 5.0],
        [2.3, 3.3, 94.4],
    ])
    _matrix_heatmap(tm, ".1f", "Class at second $t{+}1$", "Class at second $t$",
                    out_dir, "qoe_transition_matrix_cod_3_class",
                    cbar_label="Transition probability (%)")


def fig13_pooled_confusion(_data_dir, out_dir):
    # RF on the pooled four-game dataset; matches Table "pooled-results":
    # Recall(Bad)=0.926, Recall(Fair)=0.912, Recall(Excellent)=0.961.
    cm = np.array([
        [127729, 4196, 5958],
        [5989, 101940, 3844],
        [5479, 2241, 189857],
    ], dtype=float)
    _matrix_heatmap(cm, ",.0f", style.LABELS["pred"], style.LABELS["true"],
                    out_dir, "cross_game_3_class_rf_conf_mat",
                    cbar_label="Number of samples")


# ------------------------------------------------------------ Table (was Fig. 12)
SPEARMAN_GAMES = ["Free Fire", "Call of Duty"]


def table_spearman_top10(data_dir, _out_dir, top=10):
    """Print LaTeX rows: features most correlated (Spearman) with the 3-class label."""
    ranked = {}
    for game in SPEARMAN_GAMES:
        df = pd.read_csv(os.path.join(data_dir, DATA_FILES["datasets"][game]),
                         low_memory=False).dropna(subset=["ping"])
        label = df["ping"].map(lambda p: rank_str_to_int_mapping_3_classes[rank_qoe_3_classes(p)])
        features = df.drop(columns=["ping"]).apply(pd.to_numeric, errors="coerce")
        # Spearman = Pearson correlation of the ranks
        rho = features.rank().corrwith(label.rank()).dropna()
        ranked[game] = rho.reindex(rho.abs().sort_values(ascending=False).index).head(top)

    def tt(name):
        return "\\texttt{" + name.replace("_", "\\_") + "}"

    for i in range(top):
        cells = [str(i + 1)]
        for game in SPEARMAN_GAMES:
            name, value = ranked[game].index[i], ranked[game].iloc[i]
            cells += [tt(name), f"${value:+.2f}$"]
        print(" & ".join(cells) + " \\\\ \\hline")


# --------------------------------------------- Window-size comparison (#47)
WINDOW_SIZES = [1, 3, 5, 10, 15]
# written by `python training/run_models.py --game cod --window W --tag legacy` (three classes, no SMOTE)
WINDOW_RESULTS = os.path.join("results", "features_cod_{}s_legacy_f62", "class_3", "no_smote",
                              "results_class3_smoteFalse.csv")


def _mean_sd(cell):
    mean, sd = str(cell).split("±")
    return float(mean), float(sd)


def fig_window_size(data_dir, out_dir):
    """Macro F1 against window size, from run_models.py's results per window.

    data_dir is --window-dir: datasets/cod, which holds results/features_cod_<W>s_legacy_f62.
    """
    rows = []
    for w in WINDOW_SIZES:
        res = pd.read_csv(os.path.join(data_dir, WINDOW_RESULTS.format(w)))
        for _, r in res[res["Model"].isin(["RF", "XGBoost"])].iterrows():
            f1, sd = _mean_sd(r["Macro F1"])
            rows.append(dict(window=w, model=r["Model"], f1=f1, sd=sd))
    res = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(style.TEXT_WIDTH * 0.6, 2.3))
    for model, color, marker in [("RF", style.NEUTRAL, "o"),
                                 ("XGBoost", style.DIRECTION_COLORS["c2s"], "s")]:
        m = res[res["model"] == model]
        ax.errorbar(m["window"], m["f1"], yerr=m["sd"], color=color, marker=marker,
                    markersize=3.5, capsize=2, linewidth=1, label=model)
    ax.set_xticks(WINDOW_SIZES)
    ax.set_xlabel("Window size (s)")
    ax.set_ylabel("Macro F1")
    ax.grid(True)
    ax.set_axisbelow(True)
    ax.legend(loc="lower right")
    style.save(fig, out_dir, "accuracy_vs_window_size")


FIGURES = {
    "fig02": fig02_bandwidth,
    "fig03": fig03_pps,
    "fig04": fig04_pps_median,
    "fig05": fig05_pps_vs_ping,
    "fig06": fig06_size_vs_ping,
    "fig07": fig07_c2s_vs_s2c,
    "fig08": fig08_duration,
    "fig09": fig09_label_distribution,
    "fig10": fig10_cod_xgb_confusion,
    "fig11": fig11_transition_matrix,
    "fig13": fig13_pooled_confusion,
    "tab_spearman": table_spearman_top10,
    "fig_window": fig_window_size,
}


# Run only with --only: it needs the run_models.py results for each window size.
ON_REQUEST = {"fig_window"}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", default=os.path.join(ROOT, "datasets", "paper_figures"),
                        help="folder filled by figures/fetch_data.py")
    parser.add_argument("--window-dir", default=os.path.join(ROOT, "datasets", "cod"),
                        help="CoD pipeline folder with window_size_W/results (fig_window)")
    parser.add_argument("--out-dir", default=os.path.join(ROOT, "paper"))
    parser.add_argument("--only", nargs="+", choices=sorted(FIGURES))
    args = parser.parse_args()

    style.apply()
    for key in args.only or [k for k in FIGURES if k not in ON_REQUEST]:
        print(f"--- {key}")
        data_dir = args.window_dir if key == "fig_window" else args.data_dir
        FIGURES[key](data_dir, args.out_dir)


if __name__ == "__main__":
    main()
