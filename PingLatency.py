import numpy as np
import nfstream
from nfstream import NFStreamer, NFPlugin
from time import time
from consts import *

class PingLatency(NFPlugin):
    
    def on_init(self, pkt, flow): # flow creation with the first packet
        flow.udps.last_pkt_dir = C2S
        flow.udps.last_pkt_time_before_reply = { C2S: pkt.time, S2C: 0 }
        flow.udps.avg_ping = 0
        flow.udps.ping_count = 0
        flow.udps.ping_sum = 0
        
    def on_update(self, pkt, flow): # flow update with each packet belonging to the flow        
        pkt_dir = S2C
        if pkt.src_port == flow.src_port and pkt.src_ip == flow.src_ip:
            pkt_dir = C2S
        
        if flow.udps.last_pkt_dir == C2S and pkt_dir == S2C:
            currnet_ping = pkt.time - flow.udps.last_pkt_time_before_reply[flow.udps.last_pkt_dir]
            flow.udps.ping_count += 1 
            flow.udps.ping_sum += currnet_ping
            flow.udps.avg_ping = flow.udps.ping_sum / flow.udps.ping_count
            # print(f'flow.udps.avg_ping: {flow.udps.avg_ping}, currnet_ping: {currnet_ping}')
            flow.udps.last_pkt_time_before_reply[S2C] = pkt.time
        elif flow.udps.last_pkt_dir == S2C and pkt_dir == C2S:
            flow.udps.last_pkt_time_before_reply[C2S] = pkt.time
        else:
            a = 1
                    
        flow.udps.last_pkt_dir = pkt_dir

