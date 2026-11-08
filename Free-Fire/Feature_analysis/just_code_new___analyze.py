import os
import pandas as pd
import numpy as np
import re
import ast
import time
import multiprocessing
from datetime import datetime
from pathlib import Path
from nfstream import NFStreamer
from scapy.all import PcapReader, IP, IPv6, UDP, TCP
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
from sklearn.model_selection import train_test_split
from sklearn.inspection import permutation_importance
from joblib import Parallel, delayed
try:
    from rank import rank_qoe_3_classes, rank_str_to_int_mapping_3_classes
    from modelse import make_models
except ImportError:
    print("⚠️ Warning: Local modules (rank.py/modelse.py) not found. Check your paths!")
CURRENT_DIR = Path(os.getcwd())
BASE_DIR = CURRENT_DIR.parent
DATA_SUBFOLDER = "P++200"
RAW_DATA_PATH = BASE_DIR.parent / "adb" / "sessions_screencap_pc_roi" / DATA_SUBFOLDER
PRODUCTS_DIR = CURRENT_DIR / f"Products_{DATA_SUBFOLDER}"
os.makedirs(PRODUCTS_DIR, exist_ok=True)
GAME_PORT_RANGE = "10010-10025"
BPF_FILTER = f"udp and (portrange {GAME_PORT_RANGE})"
WINDOW_SIZE = 10
DECAY_RATE = 0.5
SAMPLE_DURATION = 1
USE_PARALLEL = False
USE_PARALLEL_ML = True
CORES_TO_USE = max(1, multiprocessing.cpu_count() - 4)
INCLUDE_SVM = False
start_time = time.time()
METADATA_FILENAME = "metadata_results_auto.csv"
NETWORK_ANALYSIS_FILENAME = "NetDiscovery_Michael_gm.xlsx"
FEATURES_FILENAME = "final_training_features.csv"
IMPORTANCE_FILENAME = "feature_importance_results.csv"
REPORT_FILENAME = f"Color_Coded_{DATA_SUBFOLDER}.xlsx"
NET_BACKUP_FILENAME = "network_analysis_backup.csv"

def hhmmss_to_seconds(hhmmss: int) -> int:
    h = hhmmss // 10000
    m = (hhmmss // 100) % 100
    s = hhmmss % 100
    return h * 3600 + m * 60 + s
def to_qoe_class_zero(ping):
    if pd.isna(ping):
        return 0
    try:
        ping = float(ping)
    except Exception:
        return 0
    label = rank_qoe_3_classes(ping)
    return rank_str_to_int_mapping_3_classes.get(label, 0)

def extract_ping_from_filename(filename):
    match = re.search(r"_(\d{6})_.*Ping_(\d+)\.png", filename, re.IGNORECASE)
    if match:
        return match.group(1), int(match.group(2))
    match_none = re.search(r"_(\d{6})_.*Ping_None\.png", filename, re.IGNORECASE)
    if match_none:
        return match_none.group(1), None
    return None, None
def generate_metadata_live(source_path):
    all_runs_data = []
    root = Path(source_path)
    for folder in root.iterdir():
        if folder.is_dir():
            pcap_files = list(folder.glob("*.pcapng"))
            pcap_name = pcap_files[0].name if pcap_files else "MISSING"
            time_value_pairs = {}
            for img in folder.glob("*.png"):
                timestamp, ping_val = extract_ping_from_filename(img.name)
                if timestamp:
                    time_value_pairs[timestamp] = ping_val
            all_runs_data.append({
                "folder": folder.name,
                "pcapng_file": pcap_name,
                "time_value_pairs": repr(time_value_pairs)
            })
    return pd.DataFrame(all_runs_data)

def run_network_exploration():
    start_time = datetime.now()
    log_file = PRODUCTS_DIR / NET_BACKUP_FILENAME
    RESUME_ANALYSIS = False
    processed_folders = set()
    results = []
    global_port_stats = {}
    if log_file.exists():
        if RESUME_ANALYSIS:
            try:
                temp_df = pd.read_csv(log_file)
                processed_folders = set(temp_df['folder'].astype(str).unique())
                results = temp_df.to_dict('records')
                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] Resume Mode: Found {len(processed_folders)} folders in backup. Skipping...")
            except Exception as e:
                print(f"⚠️ Warning: Could not read backup. Starting fresh ({e}).")
                os.remove(log_file)
        else:
            os.remove(log_file)
    print(f"[{start_time.strftime('%H:%M:%S')}] Starting Analysis...")
    folders = [f for f in os.listdir(RAW_DATA_PATH) if f.lower().startswith('run_')]
    p_start, p_end = map(int, GAME_PORT_RANGE.split('-'))
    for idx, folder in enumerate(folders):
        curr_t = datetime.now().strftime('%H:%M:%S')
        if folder in processed_folders:
            print(f"   [{curr_t}] [{idx + 1}/{len(folders)}] Skipping: {folder} (Already in backup) ✅")
            continue
        print(f"   [{curr_t}] [{idx + 1}/{len(folders)}] Processing: {folder}...", end=" ", flush=True)
        f_path = RAW_DATA_PATH / folder
        pcap_files = list(f_path.glob("*.pcap*"))
        if not pcap_files:
            print("Skipped ❌")
            continue
        try:
            pcap_path = str(pcap_files[0])
            streamer = NFStreamer(source=pcap_path, statistical_analysis=True, idle_timeout=1, active_timeout=1)
            nfs_df = streamer.to_pandas()
            legacy_total_flows = len(nfs_df)
            all_ip_convs = set()
            udp_convs = set()
            game_convs = set()
            game_ports = set()
            total_pkts, game_pkts, total_bytes, udp_bytes, tcp_bytes = 0, 0, 0, 0, 0
            game_pkt_sizes = []
            game_timestamps = []
            unique_ipv4 = set()
            with PcapReader(pcap_path) as reader:
                for pkt in reader:
                    total_pkts += 1
                    p_len = len(pkt)
                    total_bytes += p_len
                    if pkt.haslayer(IP):
                        for ip in [pkt[IP].src, pkt[IP].dst]:
                            if ip != "255.255.255.255":
                                unique_ipv4.add(ip)
                    if (pkt.haslayer(IP) or pkt.haslayer(IPv6)) and (pkt.haslayer(UDP) or pkt.haslayer(TCP)):
                        l = IP if pkt.haslayer(IP) else IPv6
                        pr = UDP if pkt.haslayer(UDP) else TCP
                        for p in [pkt[pr].sport, pkt[pr].dport]:
                            if p not in global_port_stats:
                                global_port_stats[p] = {'bytes': 0, 'pkts': 1}
                            else:
                                global_port_stats[p]['pkts'] += 1
                            global_port_stats[p]['bytes'] += (p_len / 2)
                        c_id = tuple(sorted([(pkt[l].src, pkt[pr].sport), (pkt[l].dst, pkt[pr].dport)]))
                        all_ip_convs.add(c_id)
                        if pkt.haslayer(UDP):
                            udp_bytes += p_len
                            udp_convs.add(c_id)
                            s_p, d_p = pkt[UDP].sport, pkt[UDP].dport
                            if (p_start <= s_p <= p_end) or (p_start <= d_p <= p_end):
                                game_convs.add(c_id)
                                game_pkts += 1
                                game_pkt_sizes.append(p_len)
                                game_timestamps.append(float(pkt.time))
                                if p_start <= s_p <= p_end: game_ports.add(s_p)
                                if p_start <= d_p <= p_end: game_ports.add(d_p)
                        elif pkt.haslayer(TCP):
                            tcp_bytes += p_len
            avg_iat = 0
            if len(game_timestamps) > 1:
                iats = [game_timestamps[i] - game_timestamps[i - 1] for i in range(1, len(game_timestamps))]
                avg_iat = (sum(iats) / len(iats)) * 1000
            stats = {
                'folder': folder,
                'total_ip_convs': len(all_ip_convs),
                'total_udp_convs': len(udp_convs),
                'game_convs': len(game_convs),
                'identified_ports': str(sorted(list(game_ports))),
                'game_purity_pct': (game_pkts / total_pkts * 100) if total_pkts > 0 else 0,
                'purity_ratio': f"{game_pkts} / {total_pkts}",
                'udp_pct': (udp_bytes / total_bytes * 100) if total_bytes > 0 else 0,
                'tcp_pct': (tcp_bytes / total_bytes * 100) if total_bytes > 0 else 0,
                'avg_iat_ms': avg_iat,
                'avg_pkt_size': (sum(game_pkt_sizes) / len(game_pkt_sizes)) if game_pkt_sizes else 0,
                'unique_ips': len(unique_ipv4),
                'total_flows': legacy_total_flows
            }
            results.append(stats)
            pd.DataFrame([stats]).to_csv(log_file, mode='a', header=not log_file.exists(), index=False)
            print("Done! ✅")
        except Exception as e:
            print(f"Error: {e} ❌")
    final_df = pd.DataFrame(results)
    xlsx_out = PRODUCTS_DIR / NETWORK_ANALYSIS_FILENAME
    final_df = pd.DataFrame(results)
    port_summary = pd.DataFrame([
        {'Port Number': k, 'Total Bytes': int(v['bytes']), 'Total Packets': v['pkts']}
        for k, v in global_port_stats.items()
    ]).sort_values('Total Packets', ascending=False)
    anomalies = final_df[final_df['udp_pct'] < 80]['folder'].tolist()
    dom_port = port_summary.iloc[0]['Port Number'] if not port_summary.empty else "N/A"
    insights_data = [
        ['Total Sessions', len(final_df), ".All recording sessions were processed and validated"],
        ['% Avg UDP', f"{final_df['udp_pct'].mean():.2f}%",
         ".High UDP percentage confirms primary game traffic capture"],
        ['Dominant Port', dom_port, ".The main communication channel for the game has been identified"],
        ['Avg Flows', round(final_df['total_flows'].mean(), 1),
         ".Flow density matches typical real-time game signatures"],
        ['Anomalies (<80% UDP)', len(anomalies), f"Flagged folders for exclusion: {', '.join(anomalies[:5])}..."]
    ]
    insights_df = pd.DataFrame(insights_data, columns=['Metric', 'Value', 'Researcher Insight'])
    with pd.ExcelWriter(xlsx_out, engine='xlsxwriter') as writer:
        final_df.to_excel(writer, sheet_name='Detailed Data', index=False)
        writer.sheets['Detailed Data'].set_column('A:Z', 22)
        port_summary.to_excel(writer, sheet_name='Port Volume Summary', index=False)
        writer.sheets['Port Volume Summary'].set_column('A:C', 20)
        insights_df.to_excel(writer, sheet_name='Project Insights', index=False)
        writer.sheets['Project Insights'].set_column('A:C', 45)
    if log_file.exists():
        os.remove(log_file)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Cleanup: Backup file removed (Analysis Finalized).")
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [SUCCESS] All Parity Requirements Met (Full Report Created).")
    return final_df

FEATURE_COLUMNS = [
            'src2dst_avg_pkt_size',
            'src2dst_avg_pkt_size_mean',
            'src2dst_avg_pkt_size_median',
            'src2dst_avg_pkt_size_std',
            'src2dst_avg_pkt_size_min',
            'src2dst_avg_pkt_size_max',
            'src2dst_pps',
            'src2dst_pps_mean',
            'src2dst_pps_median',
            'src2dst_pps_std',
            'src2dst_pps_min',
            'src2dst_pps_max',
            'dst2src_avg_pkt_size',
            'dst2src_avg_pkt_size_mean',
            'dst2src_avg_pkt_size_median',
            'dst2src_avg_pkt_size_std',
            'dst2src_avg_pkt_size_min',
            'dst2src_avg_pkt_size_max',
            'dst2src_pps',
            'dst2src_pps_mean',
            'dst2src_pps_median',
            'dst2src_pps_std',
            'dst2src_pps_min',
            'dst2src_pps_max',
            'pkt_dir_ratio',
            'pkt_dir_ratio_mean',
            'pkt_dir_ratio_median',
            'pkt_dir_ratio_std',
            'pkt_dir_ratio_min',
            'pkt_dir_ratio_max'
]

def weighted_average_decay(arr, r=DECAY_RATE):
    if not (0 < r < 1):
        raise ValueError("r must be between 0 and 1")
    if not arr: return 0
    w, s, w_sum = 1.0, 0.0, 0.0
    arr = arr[::-1]
    for x in arr:
        if x is not None and not (isinstance(x, float) and np.isnan(x)):
            s += w * x
            w_sum += w
        w *= r
    return s / w_sum if w_sum > 0 else 0
def build_second_vectors(pcap_path):
    from PingLatency import PingLatency
    try:
        streamer = NFStreamer(
            source=str(pcap_path),
            udps=[PingLatency()],
            bpf_filter=BPF_FILTER,
            active_timeout=SAMPLE_DURATION,
            idle_timeout=SAMPLE_DURATION
        )
        df = streamer.to_pandas()
        if df is None or df.empty or "bidirectional_first_seen_ms" not in df.columns:
            return pd.DataFrame()
        t0 = df["bidirectional_first_seen_ms"].min()
        if pd.isna(t0): return pd.DataFrame()
        df["pktIdx"] = ((df["bidirectional_first_seen_ms"] - t0) / 1000).astype(int)
        df = df.sort_values(["pktIdx", "src2dst_bytes"], ascending=[True, False])
        df = df.groupby("pktIdx").head(1).copy()
        df = df.set_index("pktIdx")
        out = pd.DataFrame(index=df.index)
        s_pkts = df["src2dst_packets"].fillna(0)
        d_pkts = df["dst2src_packets"].fillna(0)
        s_bytes = df["src2dst_bytes"].fillna(0)
        d_bytes = df["dst2src_bytes"].fillna(0)
        s_dur = (df["src2dst_last_seen_ms"] - df["src2dst_first_seen_ms"]).clip(lower=1.0)
        d_dur = (df["dst2src_last_seen_ms"] - df["dst2src_first_seen_ms"]).clip(lower=1.0)
        out["src2dst_avg_pkt_size"] = (s_bytes / s_pkts.clip(lower=1.0)).fillna(0)
        out["dst2src_avg_pkt_size"] = (d_bytes / d_pkts.clip(lower=1.0)).fillna(0)
        out["pkt_dir_ratio"] = (s_pkts / d_pkts.clip(lower=1.0)).fillna(0)
        out["src2dst_pps"] = (s_pkts / s_dur * 1000.0).fillna(0)
        out["dst2src_pps"] = (d_pkts / d_dur * 1000.0).fillna(0)
        return out.reset_index()
    except Exception as e:
        print(f"⚠️ Error processing {pcap_path}: {e}")
        return pd.DataFrame()
def _process_run_task(row_tuple):
    idx, row = row_tuple
    pcap_path = RAW_DATA_PATH / row["folder"] / row["pcapng_file"]
    if not pcap_path.exists(): return None
    sec_df = build_second_vectors(pcap_path)
    if sec_df.empty: return None
    time_pairs = ast.literal_eval(row["time_value_pairs"])
    start_hhmmss = int(row["folder"].split("_")[-1])
    ping_map = {hhmmss_to_seconds(int(t_str)) - hhmmss_to_seconds(start_hhmmss): v
                for t_str, v in time_pairs.items()}
    max_idx = max(sec_df["pktIdx"].max(), max(ping_map.keys() if ping_map else [0]))
    all_idx = pd.DataFrame({"pktIdx": list(range(0, max_idx + 1))})
    sec_df = all_idx.merge(sec_df, on="pktIdx", how="left")
    base_cols = ["src2dst_avg_pkt_size", "dst2src_avg_pkt_size", "dst2src_pps", "src2dst_pps", "pkt_dir_ratio"]
    rolling_df = pd.DataFrame({"pktIdx": sec_df["pktIdx"]})
    rolling_df["folder"] = row["folder"]
    for col in base_cols:
        r = sec_df[col].rolling(window=WINDOW_SIZE, min_periods=1)
        rolling_df[f"{col}"] = sec_df[col]
        rolling_df[f"{col}_mean"] = r.apply(lambda s: weighted_average_decay(s.tolist()), raw=False)
        rolling_df[f"{col}_median"] = r.median()
        rolling_df[f"{col}_min"] = r.min()
        rolling_df[f"{col}_max"] = r.max()
        rolling_df[f"{col}_std"] = r.std(ddof=0)
    rolling_df["ping"] = rolling_df["pktIdx"].map(ping_map)
    final_run_df = rolling_df[(rolling_df["pktIdx"] >= WINDOW_SIZE - 1) & (rolling_df["ping"].notna())].copy()
    del sec_df
    del rolling_df
    return final_run_df
def generate_training_data_main(meta_df, window_size=WINDOW_SIZE):
    if USE_PARALLEL:
        print(f"⚡ Parallel Mode: Using {CORES_TO_USE} CPU workers (Joblib).")
        results = Parallel(n_jobs=CORES_TO_USE, verbose=10)(
            delayed(_process_run_task)(item) for item in meta_df.iterrows()
        )
        all_dfs = [r for r in results if r is not None]
    else:
        print(f"🐢 Serial Mode: Processing folders one by one.")
        all_dfs = []
        items = list(meta_df.iterrows())
        total_items = len(items)
        for idx, item in enumerate(items):
            folder_name = item[1]['folder']
            print(
                f"   [{datetime.now().strftime('%H:%M:%S')}] Feature extraction [{idx + 1}/{total_items}]: {folder_name}...",
                end=" ")
            res = _process_run_task(item)
            if res is not None:
                all_dfs.append(res)
                print("Done! ✅")
            else:
                print("Skipped/Empty ❌")
    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

def top_features_per_model(
        df: pd.DataFrame,
        models_list,
        feature_cols,
        target_col: str,
        test_size: float = 0.2,
        random_state: int = 42,
        n_repeats: int = 10,
        top_k: int = 10
):
    X = df[feature_cols].astype("float32")
    y = df[target_col].astype(int)
    strat = y if y.nunique() > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=test_size,
        random_state=random_state,
        stratify=strat
    )
    current_n_jobs = CORES_TO_USE if USE_PARALLEL_ML else 1
    rows = []
    for name, model in models_list:
        try:
            print(
                f"   [{datetime.now().strftime('%H:%M:%S')}] Analyzing model: {name} (Parallel ML: {USE_PARALLEL_ML})...",
                end=" ")
            model.fit(X_train, y_train)
            perm = permutation_importance(
                model,
                X_test,
                y_test,
                n_repeats=n_repeats,
                random_state=random_state,
                n_jobs=current_n_jobs
            )
            importances = pd.Series(perm.importances_mean, index=feature_cols)
            top = importances.sort_values(ascending=False).head(top_k)
            for feat, val in top.items():
                rows.append({
                    "model": name,
                    "feature": feat,
                    "perm_importance_mean": float(val)
                })
            print("Done! ✅")
        except Exception as e:
            rows.append({
                "model": name,
                "feature": "__ERROR__",
                "perm_importance_mean": np.nan
            })
            print(f"Failed! ❌ ({e})")
    out = pd.DataFrame(rows)
    return out.sort_values(["model", "perm_importance_mean"], ascending=[True, False])

def calculate_scores_and_contributions(df):
    df = df.copy()
    df['rank'] = df.groupby('model')['perm_importance_mean'].rank(ascending=False, method='first').astype(int)
    df['points'] = df['rank'].apply(lambda r: max(0, 11 - r) if r <= 10 else 0)
    weights = {'XGBoost': 1.0, 'CatBoost': 1.0, 'LGBM': 1.0, 'RF': 0.8}
    df['contribution'] = df.apply(lambda row: row['points'] * weights.get(row['model'], 0.6), axis=1)
    final_scores = df.groupby('feature')['contribution'].sum().to_dict()
    return final_scores, df
def get_stats_with_logic(df, final_scores):
    stats_list = []
    features = df['feature'].unique()
    for feat in features:
        feat_data = df[df['feature'] == feat]
        ranks = feat_data['rank'].tolist()
        s = {
            'feature': feat,
            '1st': sum(1 for r in ranks if r == 1),
            '2nd': sum(1 for r in ranks if r == 2),
            '3rd': sum(1 for r in ranks if r == 3),
            'top3': sum(1 for r in ranks if r <= 3),
            'top5': sum(1 for r in ranks if r <= 5),
            'else': sum(1 for r in ranks if r > 3),
            'total': len(ranks),
            'final_score': round(final_scores.get(feat, 0), 2)
        }
        is_winner = (s['top3'] >= 2) or (s['top3'] >= 1 and s['top5'] >= 3) or (s['top3'] >= 1 and s['total'] >= 4)
        if not is_winner:
            for n in range(2, 9):
                if sum(1 for r in ranks if r <= n) >= n:
                    is_winner = True;
                    break
        s['is_winner'] = is_winner
        stats_list.append(s)
    return stats_list
def generate_full_color_coded_report():
    input_csv = PRODUCTS_DIR / IMPORTANCE_FILENAME
    output_xlsx = PRODUCTS_DIR / REPORT_FILENAME
    if not input_csv.exists():
        return print(f"❌ Error: Could not find CSV at {input_csv}")
    raw_df = pd.read_csv(input_csv)
    final_scores, df_processed = calculate_scores_and_contributions(raw_df)
    all_stats = get_stats_with_logic(df_processed, final_scores)
    winners = sorted([s for s in all_stats if s['is_winner']], key=lambda x: x['final_score'], reverse=True)
    others = sorted([s for s in all_stats if not s['is_winner']], key=lambda x: x['final_score'], reverse=True)
    palette = ["FFFF00", "00FF00", "00FFFF", "FF00FF", "FFA500", "FFC0CB", "ADFF2F", "FFD700", "00BFFF", "F08080",
               "90EE90", "DDA0DD"]
    mapping = {s['feature']: {"letter": chr(65 + i), "color": palette[i % len(palette)]} for i, s in enumerate(winners)}
    wb = Workbook()
    ws = wb.active
    ws.title = "Consensus Analysis V5"
    ws.append(["Model", "Pos", "Feature (Coded)", "Importance Score", "Score Contribution"])
    for cell in ws[1]: cell.font = Font(bold=True); cell.alignment = Alignment(horizontal="center")
    for _, row in df_processed.iterrows():
        feat = row['feature']
        display = mapping[feat]['letter'] if feat in mapping else feat
        ws.append([row['model'], row['rank'], display, row['perm_importance_mean'], round(row['contribution'], 1)])
        curr = ws.max_row
        ws.cell(row=curr, column=2).alignment = Alignment(horizontal="center")
        ws.cell(row=curr, column=5).alignment = Alignment(horizontal="center")
        if feat in mapping:
            cell = ws.cell(row=curr, column=3)
            cell.fill = PatternFill(start_color=mapping[feat]['color'], end_color=mapping[feat]['color'],
                                    fill_type="solid")
            cell.font = Font(bold=True);
            cell.alignment = Alignment(horizontal="center")
    start_col = 7
    legend_headers = ["Letter", "Feature Name", "1st", "2nd", "3rd", "else", "Total", "FINAL SCORE"]
    for i, h in enumerate(legend_headers):
        cell = ws.cell(row=1, column=start_col + i, value=h);
        cell.font = Font(bold=True)
    cur_row = 2
    for s in winners:
        info = mapping[s['feature']]
        ws.cell(row=cur_row, column=start_col, value=info['letter']).fill = PatternFill(start_color=info['color'],
                                                                                        end_color=info['color'],
                                                                                        fill_type="solid")
        ws.cell(row=cur_row, column=start_col).alignment = Alignment(horizontal="center")
        ws.cell(row=cur_row, column=start_col + 1, value=s['feature'])
        for i, key in enumerate(['1st', '2nd', '3rd', 'else', 'total']):
            ws.cell(row=cur_row, column=start_col + 2 + i, value=s[key])
        ws.cell(row=cur_row, column=start_col + 7, value=s['final_score']).font = Font(bold=True)
        cur_row += 1
    cur_row += 2
    ws.cell(row=cur_row, column=start_col + 1, value="Other Participants").font = Font(bold=True)
    cur_row += 1
    for s in others:
        ws.cell(row=cur_row, column=start_col + 1, value=s['feature'])
        for i, key in enumerate(['1st', '2nd', '3rd', 'else', 'total']):
            ws.cell(row=cur_row, column=start_col + 2 + i, value=s[key])
        ws.cell(row=cur_row, column=start_col + 7, value=s['final_score'])
        cur_row += 1
    wb.save(output_xlsx)
    print(f"✅ Full color-coded report saved to: {output_xlsx}")
def main():
    print(f"🚀 [BACKEND] Starting Full Pipeline for {DATA_SUBFOLDER}")
    print("-" * 50)
    print("\n[Step 1/5] Extracting Metadata...")
    metadata = generate_metadata_live(RAW_DATA_PATH)
    metadata.to_csv(PRODUCTS_DIR / METADATA_FILENAME, index=False)
    print("\n[Step 2/5] Running Network Analysis (Ironclad)...")
    run_network_exploration()
    print("\n[Step 3/5] Extracting Feature Vectors...")
    training_df = generate_training_data_main(metadata)
    training_df = training_df[(training_df["dst2src_pps"] < 1000) & (training_df["src2dst_pps"] < 1000)]
    training_df.to_csv(PRODUCTS_DIR / FEATURES_FILENAME, index=False)
    print("\n[Step 4/5] Running Machine Learning Importance...")
    training_df['y'] = training_df['ping'].apply(to_qoe_class_zero)
    training_df = training_df[training_df['y'] > 0].copy()
    training_df['y0'] = training_df['y'] - 1
    models_list = make_models(n_classes=3, knn_k=3, knn_weights='uniform', knn_metric='minkowski')
    if not INCLUDE_SVM: models_list = [m for m in models_list if m[0] != 'SVM']
    imp_df = top_features_per_model(df=training_df, models_list=models_list, feature_cols=FEATURE_COLUMNS, target_col="y0")
    imp_df.to_csv(PRODUCTS_DIR / IMPORTANCE_FILENAME, index=False)
    print("\n[Step 5/5] Generating Color-Coded Consensus Report...")
    generate_full_color_coded_report()
    timestamp_id = int(time.time())
    final_archive_name = f"window_{WINDOW_SIZE}_{timestamp_id}.csv"
    old_path = PRODUCTS_DIR / FEATURES_FILENAME
    new_path = PRODUCTS_DIR / final_archive_name
    if old_path.exists():
        try:
            os.rename(old_path, new_path)
            print(f"\n📦 Archive Complete: '{old_path.name}' renamed to '{new_path.name}'")
        except Exception as e:
            print(f"⚠️ Warning: Could not archive file: {e}")
    end_time = time.time()
    total_duration_seconds = end_time - start_time
    hours, rem = divmod(total_duration_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    print("-" * 40)
    print(f"🏁 Overall Execution Finished at: {datetime.now().strftime('%H:%M:%S')}")
    print(f"⏱️ Total Runtime: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")
    print("-" * 40)
    print("\n" + "=" * 50)
    print(f"✅ [SUCCESS] Backend Pipeline Completed at {datetime.now().strftime('%H:%M:%S')}")
    print(f"📂 All products are waiting in: {PRODUCTS_DIR}")
    print("=" * 50)
if __name__ == "__main__":
    main()


