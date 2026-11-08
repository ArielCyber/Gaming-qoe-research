# analyze.py
# Windows-ready, NO editcap, NO temp split files.
# Builds 1-second feature vectors directly from the whole PCAP using NFStream (active_timeout=1),
# then applies rolling window features (window_size=10 by default),
# then joins ping labels from metadata (keeps NaN when ping is missing / None).

import sys
import argparse
import os
import ast
from time import time

import pandas as pd
from nfstream import NFStreamer

from PingLatency import PingLatency

FEATURE_COLUMNS = [
    'src2dst_avg_pkt_size', 'src2dst_avg_pkt_size_mean', 'src2dst_avg_pkt_size_median',
    'src2dst_avg_pkt_size_std', 'src2dst_avg_pkt_size_min', 'src2dst_avg_pkt_size_max',

    'src2dst_pps', 'src2dst_pps_mean', 'src2dst_pps_median',
    'src2dst_pps_std', 'src2dst_pps_min', 'src2dst_pps_max',

    'dst2src_avg_pkt_size', 'dst2src_avg_pkt_size_mean', 'dst2src_avg_pkt_size_median',
    'dst2src_avg_pkt_size_std', 'dst2src_avg_pkt_size_min', 'dst2src_avg_pkt_size_max',

    'dst2src_pps', 'dst2src_pps_mean', 'dst2src_pps_median',
    'dst2src_pps_std', 'dst2src_pps_min', 'dst2src_pps_max',

    'pkt_dir_ratio', 'pkt_dir_ratio_mean', 'pkt_dir_ratio_median',
    'pkt_dir_ratio_std', 'pkt_dir_ratio_min', 'pkt_dir_ratio_max'
]
FEATURE_COLUMNS += [

    "src2dst_iat",
    "src2dst_iat_mean",
    "src2dst_iat_median",
    "src2dst_iat_std",
    "src2dst_iat_min",
    "src2dst_iat_max",

    "dst2src_iat",
    "dst2src_iat_mean",
    "dst2src_iat_median",
    "dst2src_iat_std",
    "dst2src_iat_min",
    "dst2src_iat_max",

]
FEATURE_COLUMNS += [

    "pps_mean",
    "pps_median",
    "pps_std",
    "pps_min",
    "pps_max",



]

def weighted_average_decay(arr, r=0.5):
    """נשים לב שמשקל שווה 1 מדובר בממוצע רגיל וכחול שהוא קטן יותר המשקל יותר חזק על החדשים"""
    if not arr:
        return 0
    if not (0 < r <= 1):
        raise ValueError("r must be between 0 and 1")

    w = 1.0
    s = 0.0
    w_sum = 0.0
    # arr=arr[::-1]  
    for x in arr:
        if x is not None:
            s += w * x
        w_sum += w
        w *= r

    return s / w_sum

def hhmmss_to_seconds(hhmmss: int) -> int:
    h = hhmmss // 10000
    m = (hhmmss // 100) % 100
    s = hhmmss % 100
    return h * 3600 + m * 60 + s


def diff_seconds(t1_hhmmss: int, t0_hhmmss: int) -> int:
    return hhmmss_to_seconds(t1_hhmmss) - hhmmss_to_seconds(t0_hhmmss)



def build_second_vectors_from_whole_pcap(pcap_path: str) -> pd.DataFrame:

    df = NFStreamer(
        source=pcap_path,
        udps=[PingLatency()],
        bpf_filter="udp and (portrange 7000-10000)",
        active_timeout=1,   # <- 1 second slicing
        idle_timeout=1
    ).to_pandas()

    if df is None or df.empty:
        return pd.DataFrame()

    # Define pktIdx = seconds since first seen
    t0 = df["bidirectional_first_seen_ms"].min()
    df["pktIdx"] = ((df["bidirectional_first_seen_ms"] - t0) / 1000).astype(int)

    # Pick the heaviest flow in each second (same logic as before)
    df.sort_values(["pktIdx", "src2dst_bytes"], ascending=[True, False], inplace=True)
    df = df.groupby("pktIdx").head(1).copy()
    flip_mask = df["dst_port"].fillna(0).astype(int) > 10000

    if flip_mask.any():
        swap_cols = [
            ("src2dst_bytes", "dst2src_bytes"),
            ("src2dst_packets", "dst2src_packets"),
            ("src2dst_first_seen_ms", "dst2src_first_seen_ms"),
            ("src2dst_last_seen_ms", "dst2src_last_seen_ms"),
            ("src_port", "dst_port"),
        ]
        for a, b in swap_cols:
            if a in df.columns and b in df.columns:
                tmp = df.loc[flip_mask, a].copy()
                df.loc[flip_mask, a] = df.loc[flip_mask, b].values
                df.loc[flip_mask, b] = tmp.values
    # Compute features safely
    s_pkts = df.get("src2dst_packets", 0).fillna(0).astype(float)
    d_pkts = df.get("dst2src_packets", 0).fillna(0).astype(float)
    s_bytes = df.get("src2dst_bytes", 0).fillna(0).astype(float)
    d_bytes = df.get("dst2src_bytes", 0).fillna(0).astype(float)

    s_dur = (df.get("src2dst_last_seen_ms", 0) - df.get("src2dst_first_seen_ms", 0)).astype(float).clip(lower=1.0)
    d_dur = (df.get("dst2src_last_seen_ms", 0) - df.get("dst2src_first_seen_ms", 0)).astype(float).clip(lower=1.0)

    out = pd.DataFrame(index=df["pktIdx"].astype(int))

    # keep bytes
    out["src2dst_bytes"] = s_bytes
    out["dst2src_bytes"] = d_bytes

    # port (keep as you expect in later code)
    out["dst_port"] = df.get("dst_port", 0).fillna(0).astype(int)

    # computed
    out["src2dst_avg_pkt_size"] = s_bytes / s_pkts.clip(lower=1.0)
    out["dst2src_avg_pkt_size"] = d_bytes / d_pkts.clip(lower=1.0)
    out["pkt_dir_ratio"] = s_pkts / d_pkts.clip(lower=1.0)

    out["src2dst_pps"] = (s_pkts / s_dur) * 1000.0
    out["dst2src_pps"] = (d_pkts / d_dur) * 1000.0
# Approximate IAT (ms between packets)
    out["src2dst_iat"] = s_dur / s_pkts.clip(lower=1)
    out["dst2src_iat"] = d_dur / d_pkts.clip(lower=1)

    out["pps"] = out["src2dst_pps"] + out["dst2src_pps"]

    # Ensure sorted by pktIdx
    out.sort_index(inplace=True)
    out.index.name = "pktIdx"
    out.reset_index(inplace=True)
    return out



def get_run_windows(pcap_path: str, window_size: int,
                    start_hhmmss: int, time_pairs: dict) -> pd.DataFrame:
    """
    Builds 1-second vectors, reindexes to keep missing seconds as NaN,
    adds rolling features across window_size seconds,
    and attaches ping labels at the end-of-window second.
    Ping stays NaN if None/missing in metadata.
    """
    # 1) Build label map: end-second-index -> ping_value (can be None, we keep NaN later)
    labeled_end_idx_to_ping = {}
    if time_pairs is not None and start_hhmmss is not None:
        for t_str, val in time_pairs.items():
            end_hhmmss = int(t_str)
            end_idx = diff_seconds(end_hhmmss, int(start_hhmmss))
            if end_idx >= 0:
                labeled_end_idx_to_ping[end_idx] = val  # keep None too -> becomes NaN later

    if not labeled_end_idx_to_ping:
        max_needed = None
    else:
        max_needed = max(labeled_end_idx_to_ping.keys())

    # 2) 1-second vectors (NO file splitting)
    sec_df = build_second_vectors_from_whole_pcap(pcap_path)
    if sec_df.empty:
        return pd.DataFrame()

    # 3) Decide how far we need to compute, and reindex to keep missing seconds as NaN
    if max_needed is None:
        max_needed = int(sec_df["pktIdx"].max())

    all_idx = pd.DataFrame({"pktIdx": list(range(0, max_needed + 1))})
    sec_df = all_idx.merge(sec_df, on="pktIdx", how="left")  # <- keeps NaNs

    # 4) Rolling features (FIXED: compute stats if at least ONE valid value in window)
    rolling_df = pd.DataFrame()
    rolling_df["pktIdx"] = sec_df["pktIdx"]
    rolling_df["dst_port"] = sec_df["dst_port"]
    rolling_df["src2dst_bytes"] = sec_df["src2dst_bytes"]
    rolling_df["dst2src_bytes"] = sec_df["dst2src_bytes"]

    # base_cols = ["src2dst_avg_pkt_size", "dst2src_avg_pkt_size", "dst2src_pps", "src2dst_pps", "pkt_dir_ratio"]
    base_cols = [
        "src2dst_avg_pkt_size",
        "dst2src_avg_pkt_size",
        "dst2src_pps",
        "src2dst_pps",
        "pps",
        "pkt_dir_ratio",
        "src2dst_iat",
        "dst2src_iat"
    ]
    for col in base_cols:
        rolling_df[col] = sec_df[col]

        # rolling object: require at least 1 non-NaN value to produce a stat
        r = sec_df[col].rolling(window=window_size, min_periods=1)

        # how many valid values exist in this window
        rolling_df[f"{col}_count_valid"] = r.count()#.....................................................................................................................................................

        # stats ignore NaN automatically; if all NaN -> result stays Na


        # rolling_df[f"{col}_mean"] = r.mean()   ממוצע משוקלל ניסיון חדש
        rolling_df[f"{col}_mean"] = r.apply(
        lambda s: weighted_average_decay(list(reversed(s.tolist())), r=0.5),
        raw=False)#.......................................................................................................................................................................................

        rolling_df[f"{col}_median"] = r.median()
        rolling_df[f"{col}_min"] = r.min()
        rolling_df[f"{col}_max"] = r.max()

        # std: ddof=0 => if only 1 value valid => std = 0.0 (instead of NaN)
        rolling_df[f"{col}_std"] = r.std(ddof=0)
        


#ניסיון רק הוספתי זה עדיין לא מעודכן בשום מקום בקוד
        # rolling_df[f"{col}_range"] = rolling_df[f"{col}_max"] - rolling_df[f"{col}_min"]
        # rolling_df[f"{col}_currentval"] =sec_df[col]# הערך האחרון כלומר הכי חדש




    # 5) Add ping column for EVERY second (end-of-window seconds will matter later)
    rolling_df["ping"] = rolling_df["pktIdx"].map(labeled_end_idx_to_ping)

    # 6) Keep only seconds that are valid window ends (>= window_size-1).
    # We do NOT drop NaN ping here (you asked to keep NaN).
    rolling_df = rolling_df[rolling_df["pktIdx"] >= (window_size - 1)].copy()
    rolling_df = rolling_df[rolling_df["ping"].notna()]#..........................................................

    return rolling_df


# -----------------------------
# Main script
# -----------------------------
def main():
    parser = argparse.ArgumentParser(description="Extract rolling-window features from pcaps (Windows-friendly).")
    parser.add_argument("--window-size", type=int, default=10)
    parser.add_argument("--sample-duration", type=int, default=1)

    # Defaults (you can change these once and run from VSCode with F5)
    parser.add_argument("--pcap-dir", default=r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\pictgers\test")
    parser.add_argument("--short-window-path", default=r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\band")
    parser.add_argument("--exp-csv-path", default=r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\metadata.csv")

    args = parser.parse_args()

    window_size = args.window_size
    pcap_dir = args.pcap_dir
    short_window_path = args.short_window_path
    exp_csv_path = args.exp_csv_path



    if not os.path.isdir(pcap_dir):
        print(f"pcap_dir not found: {pcap_dir}")
        sys.exit(1)

    if not os.path.isfile(exp_csv_path):
        print(f"metadata csv not found: {exp_csv_path}")
        sys.exit(1)

    meta_df = pd.read_csv(exp_csv_path)
    print(f"Loaded metadata for {len(meta_df)} runs from {exp_csv_path}")

    all_runs = []

    for _, row in meta_df.iterrows():
        folder = row["folder"]
        pcap_file = row["pcapng_file"]
        pcap_path = os.path.join(pcap_dir, folder, pcap_file)

        if not os.path.isfile(pcap_path):
            print(f"SKIP: missing pcap: {pcap_path}")
            continue

        # Parse time_value_pairs dict
        try:
            time_pairs = ast.literal_eval(row["time_value_pairs"])
            if not isinstance(time_pairs, dict):
                print(f"SKIP: time_value_pairs not dict for {folder}/{pcap_file}")
                continue
        except Exception as e:
            print(f"SKIP: cannot parse time_value_pairs for {folder}/{pcap_file}: {e}")
            continue

        # Start time from folder name run_YYYYMMDD_HHMMSS
        try:
            start_hhmmss = int(folder.split("_")[-1])
        except Exception:
            print(f"SKIP: cannot parse start_hhmmss from folder={folder}")
            continue

        print(f"Processing {folder}/{pcap_file} ...")

        run_df = get_run_windows(
            pcap_path=pcap_path,
            window_size=window_size,
            start_hhmmss=start_hhmmss,
            time_pairs=time_pairs
        )

        if run_df is None or run_df.empty:
            print(f"  -> produced 0 rows (empty)")
            continue

        # Add run identifiers
        run_df.insert(0, "folder", folder)
        run_df.insert(1, "pcapng_file", pcap_file)

        all_runs.append(run_df)
        print(f"  -> produced {len(run_df)} rows")

    if not all_runs:
        print("No windows produced at all (all runs empty).")
        return

    window_df = pd.concat(all_runs, ignore_index=True)

    # Safety: only filter if columns exist
    if "dst2src_pps" in window_df.columns and "src2dst_pps" in window_df.columns:
        before = len(window_df)
        window_df = window_df[(window_df["dst2src_pps"] < 1000) & (window_df["src2dst_pps"] < 1000)]
        print(f"pps filter: {before} -> {len(window_df)}")

    os.makedirs(short_window_path, exist_ok=True)
    output_path = os.path.join(short_window_path, f"window_{window_size}_{int(time())}.csv")
    FINAL_COLUMNS = FEATURE_COLUMNS + ['ping']

    window_df = window_df[FINAL_COLUMNS]
    window_df.to_csv(output_path, index=False)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    print("Starting analysis...")
    main()
    print("Analysis completed.")
