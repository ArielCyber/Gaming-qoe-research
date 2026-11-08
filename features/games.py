"""
Per-game settings for features/extract.py.

Two kinds of settings:
- Traffic selection (always per game, as documented in the paper's methodology):
  the BPF filter that keeps the game's traffic, how flows in one second become
  one row, how the start time is read from the run folder name.
- Legacy behaviour: the differences between the four original extractors
  (new___analyze_COD.py, Mich_updt_new___analyze.py (FF), new___analyze_GOB.py,
  new___analyze_PUBG.py; removed, see commit 4243513). `--mode legacy`
  reproduces each game's original dataset. `--mode standard` uses STANDARD
  for every game instead.
"""

import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))

# Behaviour shared by all games in --mode standard.
STANDARD = {
    "pps": "rate",          # packets / (last - first packet time in the second) * 1000
    "mean_nan": "ignore",   # decay-weighted mean skips seconds without traffic (paper: null-tolerant windowing)
    "trim_tail": False,     # keep labelled seconds after the last captured packet
    "pps_filter": None,     # keep every labelled second (legacy dropped PPS >= 1000)
}


# ----------------------------------------------------------------- PUBG filter
PUBG_PORTS = [
    "udp port 8011", "udp port 9030", "udp port 10491", "udp port 10612",
    "udp port 12235", "udp port 13004", "udp port 13748", "udp port 14073",
    "udp port 17000", "udp port 17500", "udp port 10039", "udp port 10096",
    "udp port 11096", "udp port 11455", "udp port 13894", "udp port 13972",
    "udp portrange 20000-20002", "udp portrange 7086-7995",
    "udp portrange 12070-12460", "udp portrange 41182-41192",
]


def _star_prefix_to_cidr(star):
    """'43.157.*.*' -> '43.157.0.0/16'"""
    parts = str(star).strip().split(".")
    if len(parts) != 4:
        return None
    fixed, out = 0, []
    for p in parts:
        if p == "*":
            out.append("0")
        elif p.isdigit():
            out.append(p)
            fixed += 1
        else:
            return None
    return f"{'.'.join(out)}/{fixed * 8}"


def pubg_bpf(game_dir):
    """Game ports, or the known Tencent server IP prefixes (out/tencent.csv)."""
    ports = " or ".join(PUBG_PORTS)
    prefix_csv = os.path.join(game_dir, "out", "tencent.csv")
    nets = []
    if os.path.isfile(prefix_csv):
        for s in pd.read_csv(prefix_csv)["subip"].dropna().astype(str):
            cidr = _star_prefix_to_cidr(s)
            if cidr:
                nets.append(f"net {cidr}")
    ip_bpf = " or ".join(nets)
    return f"udp and (({ports}) or ({ip_bpf}))" if ip_bpf else f"udp and ({ports})"


PUBG_BALANCING_RUNS = [   # recorded 2026-05-03 to balance the classes
    "2026-05-03__14-27-32", "2026-05-03__16-37-14", "2026-05-03__17-04-25", "2026-05-03__17-14-27",
    "2026-05-03__19-16-05", "2026-05-03__19-47-23", "2026-05-03__20-02-58",
]


def pubg_matches(game_dir):
    """The paper's 184 PUBG matches: the 177 in matches_pubg.csv plus the 7 balancing runs.

    labels_pubg.csv also lists 15 runs of 2026-03-02 that are not in the paper.
    """
    stats = pd.read_csv(os.path.join(game_dir, "matches_pubg.csv"))
    return set(stats.loc[stats["folder"] != "average", "folder"]) | set(PUBG_BALANCING_RUNS)


# ----------------------------------------------------------------- games
GAMES = {
    "cod": {
        "bpf": "udp and (portrange 7000-10000)",
        "per_second": "heaviest",       # the flow with the most client-to-server bytes
        "start_time": "run_suffix",     # run_YYYYMMDD_HHMMSS
        "labels": "labels_cod.csv",
        "legacy": {"pps": "rate", "mean_nan": "propagate", "trim_tail": False, "pps_filter": 1000},
    },
    "freefire": {
        "bpf": "udp and (portrange 10010-10025)",
        "per_second": "heaviest",
        "start_time": "run_suffix",
        "labels": "labels_freefire.csv",
        "legacy": {"pps": "rate", "mean_nan": "propagate", "trim_tail": False, "pps_filter": 1000},
    },
    "gob": {
        "bpf": "udp",                   # no fixed port, see the paper's methodology
        "per_second": "heaviest",
        "start_time": "run_suffix",
        "labels": "labels_gob.csv",
        "legacy": {"pps": "count", "mean_nan": "propagate", "trim_tail": False, "pps_filter": 1000},
    },
    "pubg": {
        "bpf": pubg_bpf,                # built from the game folder (needs out/tencent.csv)
        "per_second": "sum",            # traffic is split over several server flows
        "start_time": "dunder_hh-mm-ss",  # 2026-01-01__19-25-33
        "labels": "labels_pubg.csv",
        "matches": pubg_matches,        # metadata rows to keep (the paper's matches)
        # The balancing runs were recorded at the Fair impairment level; seconds without an
        # OCR value get ping 145 (Fair in both schemes), as in the paper's PUBG dataset.
        "fill_ping": {"runs": PUBG_BALANCING_RUNS, "ping": 145},
        "legacy": {"pps": "rate", "mean_nan": "ignore", "trim_tail": True, "pps_filter": 1000},
    },
}
