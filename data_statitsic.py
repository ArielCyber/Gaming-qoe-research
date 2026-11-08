import pandas as pd

from nfstream import NFStreamer

from scapy.all import PcapNgReader, UDP, IP
from collections import defaultdict


def hhmmss_to_seconds(hhmmss: int) -> int:
    h = hhmmss // 10000
    m = (hhmmss // 100) % 100
    s = hhmmss % 100
    return h * 3600 + m * 60 + s


def diff_seconds(t1_hhmmss: int, t0_hhmmss: int) -> int:
    return hhmmss_to_seconds(t1_hhmmss) - hhmmss_to_seconds(t0_hhmmss)

def get_pcap_stats(pcap_path):
    total_bits = 0
    total_packets = 0
    connections = set() 
    conn_counter = defaultdict(int)
    min_packets = 100
    if game_name=="Call_of_Duty":
        streamer = NFStreamer(
            source=pcap_path,
            bpf_filter="udp and (portrange 7000-10000)",  
            active_timeout=1,
            idle_timeout=1
        )

    elif game_name=="Free-Fire":
        GAME_PORT_RANGE = "10010-10025"
        BPF_FILTER = f"udp and (portrange {GAME_PORT_RANGE})"
        streamer = NFStreamer(
            source=pcap_path,
            bpf_filter=BPF_FILTER,  
            active_timeout=1,
            idle_timeout=1
        )

    else:
        streamer = NFStreamer(
            source=pcap_path,
            bpf_filter="udp",  
            active_timeout=1,
            idle_timeout=1
        )

        
    for flow in streamer:
        # connections += 1
        if game_name == "PUBG":


            PUBG_PORTS = {
                    8011, 9030, 10491, 10612, 12235,
                    13004, 13748, 14073, 17000, 17500,
                    10039, 10096, 11096, 11455,
                    13894, 13972
                }
            sport = flow.src_port
            dport = flow.dst_port
            if not (
                (20000 <= sport <= 20002) or
                (20000 <= dport <= 20002) or
                (7086 <= sport <= 7995) or
                (7086 <= dport <= 7995) or
                (12070 <= sport <= 12460) or
                (12070 <= dport <= 12460) or (flow.src_port in PUBG_PORTS or flow.dst_port in PUBG_PORTS)
            ):
                continue
        total_bits += (flow.src2dst_bytes + flow.dst2src_bytes) * 8
        total_packets += (flow.src2dst_packets + flow.dst2src_packets)

        conn = tuple(sorted([
            (flow.src_ip, flow.src_port),
            (flow.dst_ip, flow.dst_port)
        ])) 
        conn_counter[conn] += 1
       
        # connections.add(conn)
    if game_name == "Guns_of_Boom":
        strong_connections = {
            conn: count for conn, count in conn_counter.items()
            if count >= 10
        }
    else:
        strong_connections = {
            conn: count for conn, count in conn_counter.items()
            if count >= min_packets
        }
    # הכוונה קונקשנים שיש להם יותר מ100 חבילות בקונקשין
    return total_bits, total_packets, len(conn_counter),len(strong_connections)


def get_statistic(i):

   
    row = mtadata_df.iloc[i]

    folder = row['folder']
    pcap_file = row['pcapng_file'] 
    pcap_path = f"{path}/{folder}/{pcap_file}"
    import ast
    import os

    if not os.path.exists(pcap_path):
        return None
    start = None
    end = None
    ping_min = float('inf')
    ping_max = 0
    pairs = row["time_value_pairs"]
    for t_str, ping in pairs.items():
        if ping is None:
            continue

        t = int(t_str)

        if start is None:
            start = t

        end = t

        ping_min = min(ping_min, ping)
        ping_max = max(ping_max, ping)

    if start is None or end is None:
        return None

    duration = diff_seconds(end, start)

    total_bits, total_packets, connections, strong_connections = get_pcap_stats(pcap_path)

    return {
        "game": game_name,
        "folder": folder,
        "duration": duration
        ,
        "max_duration": duration
        ,
        "min_duration": duration
        ,
        "Q1": duration
        ,
        "Q3": duration
        ,
        "median": duration
        ,
        "bits": total_bits,
        "packets": total_packets,
        "connections": connections,
        "connections_+100": strong_connections,
        "pps": total_packets / duration if duration > 0 else 0,
        "PCAPS": 1 if pcap_file.endswith((".pcap", ".pcapng")) else 0    }


def update_dataset():
    # אני רוצה שהיא תהיה השורה הראשונה

    df = pd.read_csv(path_to + f"/{game_name}_statistics.csv")

    # 🔹 חישוב ממוצעים רק לעמודות מספריות
    mean_row = df.mean(numeric_only=True)

    # 🔹 הפיכת זה לשורה (DataFrame)
    mean_row = mean_row.to_frame().T

    # 🔹 הוספת ערכים לעמודות לא מספריות
    mean_row["game"] = game_name
    mean_row["folder"] = "average"

    # 🔹 סידור סדר עמודות כמו המקורי
    mean_row = mean_row[df.columns]

    mean_row["PCAPS"]=0
    mean_row["PCAPS"] = df["PCAPS"].sum()
    mean_row["max_duration"]=0
    mean_row["max_duration"]=df["max_duration"].max()
    mean_row["min_duration"]=0
    mean_row["min_duration"] = df[df["min_duration"] > 90]["min_duration"].min()
    mean_row["Q1"] = df["max_duration"].quantile(0.25)
    mean_row["Q3"] = df["max_duration"].quantile(0.75)
    mean_row["median"] = df["max_duration"].median()

    # 🔹 הוספה לדאטה
    df = pd.concat([mean_row, df], ignore_index=True)

    # 🔹 שמירה
    output_path = f"{path_to}/{game_name}_statistics.csv"
    df.to_csv(output_path, index=False)
    print("Added average row ")

def run(mtadata_df):
    results = []
    import ast

    mtadata_df["time_value_pairs"] = mtadata_df["time_value_pairs"].apply(ast.literal_eval)
    for i in range(len(mtadata_df)):
        # if i == 3:
        #     break
        s = get_statistic(i)
        if s is not None:
            results.append(s)

    stats_df = pd.DataFrame(results)
    output_path = f"{path_to}/{game_name}_statistics.csv"
    stats_df.to_csv(output_path, index=False)

    print(f"Saved to: {output_path}")
    update_dataset()
if __name__ == "__main__":
    mtadata = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\asath_data\metadata.csv"
    path=r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\asath_data\recordings"
    path_to=r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\asath_data"
    game_name="Guns_of_Boom"
    mtadata_df = pd.read_csv(mtadata)

    run(mtadata_df)
    mtadata = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\Call_of_Duty_data\metadata_cod.csv"
    path=r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\Call_of_Duty_data\recordings"
    path_to=r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\Call_of_Duty_data"
    game_name="Call_of_Duty"
    mtadata_df = pd.read_csv(mtadata)
    run(mtadata_df)


    mtadata = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\menash_data\metadata.csv"
    path=r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\menash_data\recordings"
    path_to=r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\menash_data"
    game_name="PUBG"
    mtadata_df = pd.read_csv(mtadata)

    run(mtadata_df)

    mtadata = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\michael_data\metadata_results_auto.csv"
    path=r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\michael_data\recordings"
    path_to=r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\michael_data"
    game_name="Free-Fire"
    mtadata_df = pd.read_csv(mtadata)
    run(mtadata_df)




