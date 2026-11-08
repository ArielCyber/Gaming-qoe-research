"""
Compare the old (legacy) and new (standard) feature extraction on the same captures.

Usage:
    python features/compare_modes.py --game cod [--runs 20] [--window 10]

For each match, NFStream runs once and both modes build their windows from the
same flow table. Rows are matched by (match, second). Prints, per feature, how
many seconds have the same value in both modes, and writes the per-feature
table to datasets/<game>/compare_modes_<game>_<W>s.csv.
"""

import argparse
import ast
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract  # noqa: E402
from games import GAMES, STANDARD  # noqa: E402


def compare(game, window, runs):
    cfg = GAMES[game]
    game_dir = os.path.join(extract.DATASETS_DIR, game)
    bpf = cfg["bpf"](game_dir) if callable(cfg["bpf"]) else cfg["bpf"]
    meta = pd.read_csv(os.path.join(game_dir, cfg["labels"]))
    if "matches" in cfg:
        meta = meta[meta["folder"].isin(cfg["matches"](game_dir))]
    meta = meta.head(runs)
    captures = extract.index_captures(game_dir)

    pairs = []
    for _, row in meta.iterrows():
        pcap = captures.get((row["folder"], row["pcapng_file"]))
        if pcap is None:
            continue
        flows = extract.flows(pcap, bpf)
        if flows.empty:
            continue
        labels = ast.literal_eval(row["time_value_pairs"])
        start = extract.start_hhmmss(row["folder"], cfg["start_time"])
        out = {}
        for mode, rules in [("legacy", cfg["legacy"]), ("standard", STANDARD)]:
            sec = extract.second_features(extract.one_row_per_second(flows.copy(), cfg["per_second"]),
                                          rules["pps"], aligned=(mode == "standard"))
            out[mode] = extract.run_windows(sec, window, start, labels, rules)
        m = out["legacy"].merge(out["standard"], on="pktIdx", how="outer", suffixes=("_old", "_new"),
                                indicator=True)
        m.insert(0, "folder", row["folder"])
        pairs.append(m)
    return pd.concat(pairs, ignore_index=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--game", required=True, choices=sorted(GAMES))
    parser.add_argument("--window", type=int, default=10)
    parser.add_argument("--runs", type=int, default=20, help="number of matches to compare")
    args = parser.parse_args()

    m = compare(args.game, args.window, args.runs)
    both = m[m["_merge"] == "both"]
    print(f"{args.game}: {m['folder'].nunique()} matches, {len(m)} labelled seconds "
          f"(in both modes {len(both)}, only old {(m['_merge'] == 'left_only').sum()}, "
          f"only new {(m['_merge'] == 'right_only').sum()})")
    rows = []
    for col in extract.FEATURE_COLUMNS:
        a, b = both[f"{col}_old"].to_numpy(float), both[f"{col}_new"].to_numpy(float)
        valid = ~(np.isnan(a) & np.isnan(b))
        same = np.isclose(a, b, rtol=1e-6, equal_nan=True)[valid].mean()
        diff = np.abs(a - b)[~np.isnan(a) & ~np.isnan(b)]
        rows.append(dict(feature=col, same_value=round(same, 4),
                         old_nan=round(np.isnan(a).mean(), 4), new_nan=round(np.isnan(b).mean(), 4),
                         median_abs_diff=round(float(np.median(diff)), 4) if len(diff) else np.nan))
    table = pd.DataFrame(rows)
    print(table.to_string(index=False))
    out = os.path.join(extract.DATASETS_DIR, args.game, f"compare_modes_{args.game}_{args.window}s.csv")
    table.to_csv(out, index=False)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
