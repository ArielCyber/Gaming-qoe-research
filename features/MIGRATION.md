# From the four old extractors to `extract.py`

`features/extract.py` + `features/games.py` replace `new___analyze_COD.py`, `michael_data/Mich_updt_new___analyze.py` (Free Fire), `asath_data/new___analyze_GOB.py` and `menash_data/new___analyze_PUBG.py`. The four old files were about 90% the same code; the new code keeps that shared code once and turns the per-game differences into settings. A line diff therefore shows almost everything as changed. Compare function by function with the table below.

## See the old files

They were removed in commit `2375fac`; the last commit that has them is `4243513`:

```bash
git show 4243513:asath_data/new___analyze_GOB.py > /tmp/old_gob.py
git show 4243513:new___analyze_COD.py > /tmp/old_cod.py
code --diff /tmp/old_gob.py features/extract.py      # side by side in VS Code
```

On GitHub: `https://github.com/ArielCyber/Gaming-qoe-research/blob/4243513/asath_data/new___analyze_GOB.py`.

## Step by step (old GoB line numbers at `4243513`)

| Step | Old `new___analyze_GOB.py` | New `extract.py` | Changed? |
|---|---|---|---|
| Feature list (62 + ping) | `FEATURE_COLUMNS`, lines 18–107 | `FEATURE_COLUMNS` (built from `DIRECTIONAL`, `COMBINED`, `STATS`) | Same names, same order (checked against the paper datasets) |
| Decay-weighted mean | `weighted_average_decay`, line 109 | `decay_mean_propagate` (legacy) and `decay_mean_ignore` (standard) | Legacy identical. Standard skips seconds without traffic |
| Clock time to seconds | `hhmmss_to_seconds`, `diff_seconds`, lines 127–137 | `hhmmss_to_seconds` | Same |
| NFStream on the capture | `build_second_vectors_from_whole_pcap`, line 139: `NFStreamer(..., bpf_filter="udp", active_timeout=1, idle_timeout=1)` | `flows()` | Same call, plus `n_meters=1` (deterministic). The BPF filter comes from `games.py` (`GAMES["gob"]["bpf"] = "udp"`) |
| Second number of each flow | same function, `pktIdx` from `bidirectional_first_seen_ms` | `flows()` | Same |
| One flow per second | same function, line 160: sort by bytes, `groupby("pktIdx").head(1)` | `one_row_per_second(df, "heaviest")` | Same. PUBG's "sum of flows" is the other branch (`how="sum"`) |
| Client/server direction | same function, line 161: swap columns when `dst_port > 10000` | `flip_to_client_server()` | Same |
| Per-second metrics | same function, lines 175–222 (`out[...] = ...`) | `second_features(df, pps_rule, aligned)` | Legacy (`aligned=False`) identical, including the index misalignment. Standard (`aligned=True`) gives each second its own values. PPS: GoB legacy `pps_rule="count"` (old line 206), standard `"rate"` (old line 202, commented out in GoB) |
| Window of W seconds, labels | `get_run_windows`, line 226 (labels map, reindex to all seconds, rolling stats, ping of the window's last second) | `run_windows(sec_df, window, start, time_pairs, rules)` | Same steps. Standard adds `fill_ping` (PUBG balancing runs) |
| Loop over matches | `main()`, line 323: read metadata, `folder/pcapng_file`, `ast.literal_eval(time_value_pairs)`, start time `folder.split("_")[-1]` (line 382) | `extract()` with `index_captures()` and `start_hhmmss()` | Same. Captures are found anywhere under `datasets/<game>/`; PUBG's `__HH-MM-SS` folder names are a second start-time style |
| `pps < 1000` filter | `main()`, line 417 | `extract()`, `rules["pps_filter"]` | Legacy keeps it (1000), standard has none |
| Output | `main()`, line 426, Windows path | `main()`: `datasets/<game>/features_<game>_<W>s[_legacy].csv` | Same columns (62 + ping) |

## Where each game's differences went

Everything that differed between the four old files is now one entry in `games.py`:

| Difference | CoD | Free Fire | GoB | PUBG | `games.py` key |
|---|---|---|---|---|---|
| BPF filter | `portrange 7000-10000` | `portrange 10010-10025` | `udp` | ports + IP prefixes | `bpf` |
| One flow per second | heaviest | heaviest | heaviest | sum | `per_second` |
| Start time in folder name | `run_..._HHMMSS` | same | same | `...__HH-MM-SS` | `start_time` |
| PPS and IAT | rate | rate | **count** | rate | `legacy.pps` |
| Mean with a missing second | NaN | NaN | NaN | skip | `legacy.mean_nan` |
| Trailing seconds without traffic | kept | kept | kept | trimmed | `legacy.trim_tail` |
| `pps < 1000` filter | yes | yes | yes | yes | `legacy.pps_filter` |

`--mode legacy` uses each game's `legacy` entry; `--mode standard` uses `STANDARD` for every game.

## Proof that nothing else changed

`features/test_equivalence.py` (in commit `4243513`) ran each old script's own `get_run_windows` and the new legacy pipeline on the same NFStream output: identical values for all 62 features on 40 matches (10 per game). To rerun it, check out that commit: `git checkout 4243513 && python features/test_equivalence.py --runs 10`.
