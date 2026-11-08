"""
Extract the paper's 62 traffic features from game captures, for any game.

Usage:
    python features/extract.py --game cod [--window 10] [--mode standard|legacy] [--runs N]

Reads datasets/<game>/labels_<game>.csv (one row per match: folder,
pcapng_file, time_value_pairs with the per-second OCR ping) and the captures
under datasets/<game>/, and writes datasets/<game>/features_<game>_<W>s.csv
(standard) or features_<game>_<W>s_legacy.csv (legacy): one row per labelled
second, the 62 features and the ping.

--mode legacy reproduces the four original per-game extractors
(new___analyze_COD.py, Mich_updt_new___analyze.py, new___analyze_GOB.py,
new___analyze_PUBG.py) exactly, including their known problems; the
originals and the test that proves it (features/test_equivalence.py) are in
commit 4243513. --mode standard applies one rule set to every game
(features/games.py STANDARD) and gives each second its own flow values.
See DATA.md.
"""

import argparse
import ast
import os
import re
import sys

import numpy as np
import pandas as pd
from nfstream import NFStreamer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PingLatency import PingLatency  # noqa: E402
from games import GAMES, STANDARD    # noqa: E402

DATASETS_DIR = os.path.join(ROOT, "datasets")
DECAY_R = 0.5   # weight of each older second in the decay-weighted mean

# The 62 features, in the order of the paper's datasets.
DIRECTIONAL = ["src2dst_avg_pkt_size", "src2dst_pps", "dst2src_avg_pkt_size", "dst2src_pps",
               "pkt_dir_ratio", "src2dst_iat", "dst2src_iat"]
COMBINED = ["pps", "iat", "bytes", "avg_pkt_size"]
STATS = ["mean", "median", "std", "min", "max"]
FEATURE_COLUMNS = ([f"{m}{s}" for m in DIRECTIONAL for s in [""] + [f"_{x}" for x in STATS]]
                   + [f"{m}_{s}" for m in COMBINED for s in STATS])
BASE_COLUMNS = DIRECTIONAL + COMBINED


# ----------------------------------------------------------------- helpers
def hhmmss_to_seconds(hhmmss):
    return hhmmss // 10000 * 3600 + (hhmmss // 100) % 100 * 60 + hhmmss % 100


def start_hhmmss(folder, style):
    if style == "run_suffix":                       # run_YYYYMMDD_HHMMSS
        return int(str(folder).split("_")[-1])
    m = re.search(r"__(\d{2})-(\d{2})-(\d{2})$", str(folder))   # 2026-01-01__19-25-33
    if not m:
        raise ValueError(f"cannot read start time from {folder}")
    hh, mm, ss = map(int, m.groups())
    return hh * 10000 + mm * 100 + ss


def decay_mean_propagate(values):
    """Legacy CoD/FF/GoB: a missing second (NaN) makes the whole mean NaN."""
    w, s, w_sum = 1.0, 0.0, 0.0
    for x in values:
        if x is not None:
            s += w * x
        w_sum += w
        w *= DECAY_R
    return s / w_sum if values else 0


def decay_mean_ignore(values):
    """Missing seconds are skipped (legacy PUBG, and the standard)."""
    w, s, w_sum = 1.0, 0.0, 0.0
    for x in values:
        if x is not None and not (isinstance(x, float) and np.isnan(x)):
            s += w * float(x)
            w_sum += w
        w *= DECAY_R
    return s / w_sum if w_sum > 0 else 0.0


def index_captures(game_dir):
    """(run folder, file name) -> capture path, anywhere under the game folder."""
    index = {}
    for root, _, files in os.walk(game_dir):
        for f in files:
            if f.endswith((".pcap", ".pcapng")):
                index.setdefault((os.path.basename(root), f), os.path.join(root, f))
    return index


# ----------------------------------------------------------------- seconds
def flows(pcap, bpf):
    # n_meters=1: one meter thread, so the output is identical on every run
    # (the original scripts used NFStream's default parallel meters, which are not)
    df = NFStreamer(source=pcap, udps=[PingLatency()], bpf_filter=bpf,
                    active_timeout=1, idle_timeout=1, n_meters=1).to_pandas()
    if df is None or df.empty:
        return pd.DataFrame()
    t0 = df["bidirectional_first_seen_ms"].min()
    df["pktIdx"] = ((df["bidirectional_first_seen_ms"] - t0) / 1000).astype(int)
    return df


SWAP = [("src2dst_bytes", "dst2src_bytes"), ("src2dst_packets", "dst2src_packets"),
        ("src2dst_first_seen_ms", "dst2src_first_seen_ms"),
        ("src2dst_last_seen_ms", "dst2src_last_seen_ms"), ("src_port", "dst_port")]


def flip_to_client_server(df):
    """Servers that send from a port above 10000 are recorded the other way round."""
    mask = df["dst_port"].fillna(0).astype(int) > 10000
    if mask.any():
        for a, b in SWAP:
            if a in df.columns and b in df.columns:
                tmp = df.loc[mask, a].copy()
                df.loc[mask, a] = df.loc[mask, b].values
                df.loc[mask, b] = tmp.values
    return df


def one_row_per_second(df, how):
    if how == "heaviest":
        df = df.sort_values(["pktIdx", "src2dst_bytes"], ascending=[True, False])
        df = df.groupby("pktIdx").head(1).copy()
        return flip_to_client_server(df)
    # "sum": flip each flow first, then add up all flows of the second
    df = flip_to_client_server(df)
    return df.groupby("pktIdx", as_index=False).agg({
        "src2dst_bytes": "sum", "dst2src_bytes": "sum",
        "src2dst_packets": "sum", "dst2src_packets": "sum",
        "src2dst_first_seen_ms": "min", "src2dst_last_seen_ms": "max",
        "dst2src_first_seen_ms": "min", "dst2src_last_seen_ms": "max",
        "dst_port": lambda s: int(s.dropna().astype(int).mode().iloc[0]) if len(s.dropna()) else 0,
    })


def second_features(df, pps_rule, aligned):
    """Per-second base metrics.

    aligned=False reproduces the original code: values keep the flow-row index
    while the output is indexed by second, so pandas pairs second k with flow
    row k. aligned=True gives every second its own flow's values.
    """
    def col(name):
        s = df.get(name, 0).fillna(0).astype(float)
        return s.values if aligned else s

    s_pkts, d_pkts = col("src2dst_packets"), col("dst2src_packets")
    s_bytes, d_bytes = col("src2dst_bytes"), col("dst2src_bytes")
    s_dur = (df.get("src2dst_last_seen_ms", 0) - df.get("src2dst_first_seen_ms", 0)).astype(float).clip(lower=1.0)
    d_dur = (df.get("dst2src_last_seen_ms", 0) - df.get("dst2src_first_seen_ms", 0)).astype(float).clip(lower=1.0)
    if aligned:
        s_dur, d_dur = s_dur.values, d_dur.values
    clip1 = (lambda x: np.clip(x, 1.0, None)) if aligned else (lambda x: x.clip(lower=1.0))

    out = pd.DataFrame(index=df["pktIdx"].astype(int))
    out["src2dst_bytes"] = s_bytes
    out["dst2src_bytes"] = d_bytes
    out["dst_port"] = (df.get("dst_port", 0).fillna(0).astype(int).values if aligned
                       else df.get("dst_port", 0).fillna(0).astype(int))
    out["src2dst_avg_pkt_size"] = s_bytes / clip1(s_pkts)
    out["dst2src_avg_pkt_size"] = d_bytes / clip1(d_pkts)
    out["pkt_dir_ratio"] = s_pkts / clip1(d_pkts)
    if pps_rule == "count":            # legacy GoB: packets in the 1-second bin
        out["src2dst_pps"] = s_pkts
        out["dst2src_pps"] = d_pkts
    else:                              # rate within the second
        out["src2dst_pps"] = (s_pkts / s_dur) * 1000.0
        out["dst2src_pps"] = (d_pkts / d_dur) * 1000.0
    out["src2dst_iat"] = s_dur / clip1(s_pkts)
    out["dst2src_iat"] = d_dur / clip1(d_pkts)
    out["iat"] = out["dst2src_iat"] + out["src2dst_iat"]
    out["pps"] = out["src2dst_pps"] + out["dst2src_pps"]
    out["bytes"] = d_bytes + s_bytes
    out["avg_pkt_size"] = out["src2dst_avg_pkt_size"] + out["dst2src_avg_pkt_size"]
    out.sort_index(inplace=True)
    out.index.name = "pktIdx"
    return out.reset_index()


# ----------------------------------------------------------------- windows
def run_windows(sec_df, window, start, time_pairs, rules, fill_ping=None):
    """Rolling features over `window` seconds, labelled with the ping of the window's last second.

    fill_ping: label for every second between the first and last OCR timestamp
    that has no OCR value (runs recorded at one known impairment level).
    """
    labels = {}
    for t, ping in time_pairs.items():
        idx = hhmmss_to_seconds(int(t)) - hhmmss_to_seconds(int(start))
        if idx >= 0:
            labels[idx] = ping
    if fill_ping is not None and labels:
        for idx in range(min(labels), max(labels) + 1):
            if labels.get(idx) is None:
                labels[idx] = fill_ping
    pcap_max = int(sec_df["pktIdx"].max())
    last = max(labels) if labels else pcap_max
    if rules["trim_tail"]:
        last = min(last, pcap_max)
    sec_df = pd.DataFrame({"pktIdx": range(last + 1)}).merge(sec_df, on="pktIdx", how="left")

    decay = decay_mean_ignore if rules["mean_nan"] == "ignore" else decay_mean_propagate
    out = pd.DataFrame({"pktIdx": sec_df["pktIdx"]})
    for col in BASE_COLUMNS:
        r = sec_df[col].rolling(window=window, min_periods=1)
        out[col] = sec_df[col]
        out[f"{col}_mean"] = r.apply(lambda s: decay(list(reversed(s.tolist()))), raw=False)
        out[f"{col}_median"] = r.median()
        out[f"{col}_min"] = r.min()
        out[f"{col}_max"] = r.max()
        out[f"{col}_std"] = r.std(ddof=0)
    out["ping"] = out["pktIdx"].map(labels)
    out = out[out["pktIdx"] >= window - 1]
    return out[out["ping"].notna()]


# ----------------------------------------------------------------- main
def extract(game, window, mode, max_runs=None, log=print):
    cfg = GAMES[game]
    game_dir = os.path.join(DATASETS_DIR, game)
    rules = cfg["legacy"] if mode == "legacy" else STANDARD
    bpf = cfg["bpf"](game_dir) if callable(cfg["bpf"]) else cfg["bpf"]
    meta = pd.read_csv(os.path.join(game_dir, cfg["labels"]))
    if "matches" in cfg:
        meta = meta[meta["folder"].isin(cfg["matches"](game_dir))]
        log(f"{len(meta)} matches kept from {cfg['labels']}")
    if max_runs:
        meta = meta.head(max_runs)
    captures = index_captures(game_dir)

    runs = []
    for _, row in meta.iterrows():
        pcap = captures.get((row["folder"], row["pcapng_file"]))
        if pcap is None:
            log(f"SKIP missing capture {row['folder']}/{row['pcapng_file']}")
            continue
        time_pairs = ast.literal_eval(row["time_value_pairs"])
        df = flows(pcap, bpf)
        if df.empty:
            continue
        sec = second_features(one_row_per_second(df, cfg["per_second"]), rules["pps"],
                              aligned=(mode == "standard"))
        fill = cfg.get("fill_ping")
        fill_value = fill["ping"] if fill and mode == "standard" and row["folder"] in fill["runs"] else None
        w = run_windows(sec, window, start_hhmmss(row["folder"], cfg["start_time"]), time_pairs, rules,
                        fill_ping=fill_value)
        w.insert(0, "folder", row["folder"])
        runs.append(w)
        log(f"{row['folder']}: {len(w)} rows")
    data = pd.concat(runs, ignore_index=True)
    if rules.get("pps_filter"):
        before = len(data)
        limit = rules["pps_filter"]
        data = data[(data["dst2src_pps"] < limit) & (data["src2dst_pps"] < limit)]
        log(f"pps < {limit} filter: {before} -> {len(data)} rows")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--game", required=True, choices=sorted(GAMES))
    parser.add_argument("--window", type=int, default=10, help="window size in seconds")
    parser.add_argument("--mode", default="standard", choices=["standard", "legacy"])
    parser.add_argument("--runs", type=int, help="only the first N matches (for tests)")
    parser.add_argument("--out", help="output CSV (default: datasets/<game>/features_<game>_<W>s[_legacy].csv)")
    parser.add_argument("--keep-folder", action="store_true", help="keep the match folder column")
    args = parser.parse_args()

    data = extract(args.game, args.window, args.mode, args.runs)
    cols = (["folder"] if args.keep_folder else []) + FEATURE_COLUMNS + ["ping"]
    suffix = "" if args.mode == "standard" else "_legacy"
    out = args.out or os.path.join(DATASETS_DIR, args.game, f"features_{args.game}_{args.window}s{suffix}.csv")
    data[cols].to_csv(out, index=False)
    print(f"Saved {len(data)} rows to {out}")


if __name__ == "__main__":
    main()
