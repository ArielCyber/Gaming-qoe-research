import os
import argparse
from time import time
import pandas as pd
import nfstream
import pyshark
import pickle
from nfstream import NFStreamer, NFPlugin
from PingLatency import PingLatency
from analyze import get_pcap_features

def main():
    parser = argparse.ArgumentParser(description='Real-time QoE prediction')
    parser.add_argument('--window-size', type=str, default=10, help='window size in seconds')
    parser.add_argument('--model', type=str, default='/Users/<user>/PhD/github/qoe-research/model4.pkl', help='path to the trained model')
    parser.add_argument('--interface', type=str, default='ap1', help='name of the network interface to capture traffic from')
    parser.add_argument('--ring', type=str, default='/Users/<user>/PhD/qoe/ring', help='path to the directory to save captured traffic')
    parser.add_argument('--filter', type=str, default='udp and (portrange 7000-10000) and not udp port 53 and not port 7500 and not port 8700', help='BPF filter to apply to captured traffic')

    args = parser.parse_args()

    clf = None
    with open(args.model, 'rb') as f:
        clf = pickle.load(f)

    i = 0
    window_size = args.window_size
    while True:
        try:
            i += 1
            print(f'start round #{i}')
            filepath = os.path.join(args.ring, f'{i}.pcapng')
            capture = pyshark.LiveCapture(interface=args.interface, output_file=filepath, bpf_filter=args.filter)
            capture.sniff(timeout=window_size)
            capture.close()
            fv = get_pcap_features(filepath, window_size)
            if not isinstance(fv, pd.DataFrame):
                continue
            # fv.fillna(0, inplace=True)
            fv = fv[['src2dst_avg_pkt_size', 'src2dst_avg_pkt_size_mean', 'src2dst_avg_pkt_size_median', 'src2dst_avg_pkt_size_std', 'src2dst_avg_pkt_size_min', 'src2dst_avg_pkt_size_max', 'src2dst_pps', 'src2dst_pps_mean', 'src2dst_pps_median', 'src2dst_pps_std', 'src2dst_pps_min', 'src2dst_pps_max', 'dst2src_avg_pkt_size', 'dst2src_avg_pkt_size_mean', 'dst2src_avg_pkt_size_median', 'dst2src_avg_pkt_size_std', 'dst2src_avg_pkt_size_min', 'dst2src_avg_pkt_size_max', 'dst2src_pps', 'dst2src_pps_mean', 'dst2src_pps_median', 'dst2src_pps_std', 'dst2src_pps_min', 'dst2src_pps_max', 'pkt_dir_ratio', 'pkt_dir_ratio_mean', 'pkt_dir_ratio_median', 'pkt_dir_ratio_std', 'pkt_dir_ratio_min', 'pkt_dir_ratio_max']].tail(1)
            res = clf.predict(fv)[0]
            # print(fv)
            print(f'predicted QoE: {res}')
        except Exception as e:
            print(f'skip round due technial issue')
    # else:
    #     print(f'no traffic') 
if __name__ == '__main__':
    main()