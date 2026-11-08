# Data Collection — ADB + PCAP

Simultaneous capture of:
- **Phone screenshots** via ADB at 1 Hz (PNG crop of the in-game ping display)
- **Network traffic** via Wireshark `dumpcap` on the Windows Mobile Hotspot interface

Both captures run in parallel and save to the same timestamped session folder.

---

## Prerequisites

| Tool | Purpose | Install |
|---|---|---|
| Python 3.8+ | Run collection scripts | [python.org](https://www.python.org) |
| Android Platform Tools | `adb.exe` | [developer.android.com/tools/releases/platform-tools](https://developer.android.com/tools/releases/platform-tools) — place `adb.exe` in `adb/` or add to system PATH |
| Wireshark | `dumpcap.exe` for PCAP capture | [wireshark.org](https://www.wireshark.org) — install to default `C:\Program Files\Wireshark` |
| Windows Mobile Hotspot | Phone internet via PC | Built into Windows — enable in Settings > Network > Mobile Hotspot |

---

## Setup

```cmd
pip install -r requirements.txt
```

Place `adb.exe` (and its DLLs) inside the `adb/` folder, or ensure `adb` is on your system PATH.

---

## One-Time Configuration

### 1. Find your hotspot dumpcap interface index

```cmd
"C:\Program Files\Wireshark\dumpcap.exe" -D
```

Look for the interface named something like `Local Area Connection* X` or `Wi-Fi Direct Virtual Adapter`. Run a short test:

```cmd
"C:\Program Files\Wireshark\dumpcap.exe" -i 5 -a duration:5 -w NUL
```

If it captures packets, index 5 is correct. Otherwise try other indices.

Update `record_pcap.ps1` line 21:
```powershell
$CaptureInterfaceIndex = 5   # <-- change this to your correct index
```

### 2. Tune the ping ROI for your game

`adb/screencap_phone_then_pull.py` crops a fixed pixel region containing the in-game ping value.
The defaults (`x1=250, y1=1040, x2=320, y2=1080`) are tuned for **PUBG Mobile** on a specific device resolution.

For other games or resolutions, take a test screenshot and adjust the crop coordinates:
```python
# line 248 in screencap_phone_then_pull.py
crop = crop_region_bgr(frame_bgr, x1=250, y1=1040, x2=320, y2=1080)
```

---

## Phone Setup

1. Enable **USB Debugging** on the phone: Settings > Developer Options > USB Debugging
2. Connect phone via USB cable
3. On first connection: approve the "Allow USB debugging?" prompt on the phone screen
4. Connect phone to the PC's Mobile Hotspot for internet

---

## Running a Session

```cmd
cd data_collection_adb
python record_all.py
```

This starts both captures in parallel. Press **Ctrl+C** to stop both simultaneously.

Output is saved to:
```
data_collection_adb/captures/<YYYY-MM-DD__HH-MM-SS>/
    000001_20260101_120000.png   (screenshot crops at 1 Hz)
    000002_20260101_120001.png
    ...
    phone-192.168.137.xxx-20260101-120000.pcap
    log.csv                      (i, timestamp, filename, status, elapsed_sec)
```

---

## Running Scripts Individually

**Screenshots only:**
```cmd
python adb/screencap_phone_then_pull.py
# or with explicit output dir:
python adb/screencap_phone_then_pull.py --out_dir C:\path\to\session
```

**PCAP only:**
```powershell
powershell -ExecutionPolicy Bypass -File record_pcap.ps1
# or with explicit output dir:
powershell -ExecutionPolicy Bypass -File record_pcap.ps1 -OutDir C:\path\to\session
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `adb not found in PATH` | Place `adb.exe` in `adb/` folder or add to system PATH |
| `[+] Waiting for device...` forever | Check USB cable, enable USB debugging, approve prompt on phone |
| `[+] Device unauthorized` | Tap "Allow" on the phone screen |
| `Hotspot not found` | Enable Mobile Hotspot in Windows Settings |
| `No real device found` | Open a website on the phone to generate traffic, then retry |
| `dumpcap not found` | Install Wireshark or update `$WiresharkDir` in `record_pcap.ps1` |
| PCAP is empty | Wrong interface index — run `dumpcap -D` and update `$CaptureInterfaceIndex` |

---

## Next Steps

After collection, process the session with the pipeline in `Free-Fire/First_Action/` (ping OCR labeling) and then run `new___analyze.py` for feature extraction.
