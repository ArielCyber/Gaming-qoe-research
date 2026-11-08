import os
import pyshark
from scapy.all import PcapNgReader
import pandas as pd

def get_pcap_duration(pcap_path):
    with PcapNgReader(pcap_path) as packets:
        first_packet_time = next(packets).time
        for packet in packets:
            pass
        last_packet_time = packet.time
    duration = last_packet_time - first_packet_time
    return duration

pcap_dir = '/Users/<user>/PhD/github/qoe-research/exp/17-May-2024/pcaps'  # replace with your directory
total_duration = 0

exp_list = []
for exp_id in os.listdir(pcap_dir):
    pcap_exp_dir = os.path.join(pcap_dir, exp_id)
    if not os.path.isdir(pcap_exp_dir):
        continue
    for filename in os.listdir(pcap_exp_dir):
        if filename.endswith('.pcapng'):
            print(f'Processing {filename}...')
            pcap_path = os.path.join(pcap_exp_dir, filename)
            duration = get_pcap_duration(pcap_path)
            total_duration += duration
            print(f'{filename}: {duration} seconds')
            exp_list.append({ 'exp_id': exp_id, 'filename': filename, 'duration': duration})
df = pd.DataFrame.from_dict(exp_list)
df.sort_values(by='exp_id', ascending=True, inplace=True)
df.to_csv('pcap_durations.csv', index=False)
print(f'Total duration of all pcap files: {total_duration} seconds')

