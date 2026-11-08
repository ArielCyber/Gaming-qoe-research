# Mobile Gaming QoE Dataset: Encrypted Network Traffic Captures and In-Game Ping Screenshots

Raw data behind the paper *"Every second counts! High granularity Quality of Experience Prediction for First-Person Shooter Online Gaming"* (under review; citation added on acceptance).

Four Android first-person shooter games:
**Call of Duty: Mobile (CoD)**, **Free Fire (FF)**, **PlayerUnknown's Battlegrounds Mobile (PUBG)** and **Guns of Boom (GoB)**.

Each match (a *run*) comes with:

1. the **network capture** of the phone's traffic (`.pcapng`, or `.pcap` for PUBG).
2. the **ping screenshots**: crops of the in-game ping indicator, taken about every 1.4 s during the match.
3. **`log.csv`**: the screenshot log (frame index, timestamp, file name, status).

This release holds raw data only. It does **not** include the OCR ping values, the per-second QoE labels or the extracted traffic features. The screenshots are the ground truth; anyone can re-run their own OCR on them.

## Files

| File | Content | Runs | Size |
|---|---|---|---|
| `gaming_qoe_sample.zip` | 3 runs per game (low, mid and high ping) to look at the data before downloading everything | 12 | 68 MB |
| `gaming_qoe_cod.zip` | Call of Duty: Mobile | 615 | 9.9 GB |
| `gaming_qoe_freefire.zip` | Free Fire | 407 | 3.9 GB |
| `gaming_qoe_pubg.zip` | PUBG Mobile | 184 | 1.8 GB |
| `gaming_qoe_gob.zip` | Guns of Boom | 300 | 0.75 GB |
| `manifest_<game>.csv` | one row per run (also inside each zip) | | |
| `SHA256SUMS` | checksums of the zip files | | |
| `README.md` | this file | | |

Check the downloads with `sha256sum -c SHA256SUMS` (Linux) or `shasum -a 256 -c SHA256SUMS` (macOS).

## Layout

```
gaming_qoe_<game>/
  manifest_<game>.csv
  <run>/
    <capture>.pcapng | .pcap      network capture of the match
    000001_YYYYMMDD_HHMMSS.png    ping screenshot: frame index, capture time
    000002_YYYYMMDD_HHMMSS.png
    ...
    log.csv                       screenshot log
```

The run folder name is the start time of the run (`run_YYYYMMDD_HHMMSS`, or `YYYY-MM-DD__HH-MM-SS` for PUBG).
The capture file names come from the original recordings: `<n>.pcapng` (CoD), `pCAP_run_<time>.pcapng` (FF), `pcap<n>.pcapng` (GoB), `phone-<phone IP>-<time>.pcap` (PUBG).

### `log.csv`

| Column | Meaning |
|---|---|
| `i` | frame index, matches the 6-digit prefix of the screenshot name |
| `ts` | capture time of the screenshot, `YYYYMMDD_HHMMSS`, local time of the access point (Israel) |
| `filename` | screenshot file name |
| `status` | `ok` when the screenshot was taken, `fail:<reason>` when it was not |
| `elapsed_sec` | seconds since the start of the run (GoB and PUBG only) |
| `error` | ADB error message of a failed screenshot (two PUBG runs only) |

`log.csv` lists every frame that was taken. Frames from player death, match start and match end, and unreadable frames, were removed from the run folder after the match, so some `log.csv` rows have no PNG (column `n_logged_frames` vs `n_screenshots` in the manifest). A few PUBG frames have a second copy named `..._HHMMSS(1).png`.

### `manifest_<game>.csv`

| Column | Meaning |
|---|---|
| `game`, `run` | game code and run folder |
| `capture_file` | capture file name |
| `capture_bytes`, `capture_sha256` | size and SHA-256 of the capture |
| `n_screenshots` | ping screenshots in the run folder |
| `n_logged_frames` | `ok` rows in `log.csv` |
| `has_log` | 1 if the run has `log.csv` |

## How the data was collected

- **Devices:** four Android phones, connected over Wi-Fi to Windows 11 PCs acting as the access point.
- **Capture:** Wireshark on the access point, one capture per match. Captures hold all of the phone's traffic during the match, not only the game traffic. The game flows are UDP; the paper describes the per-game filters.
- **Impairment:** Clumsy on the access point added 0, 100, 150, 200, 300, 400 or 500 ms of latency, depending on the game. The impairment level of each run is not part of this release.
- **Screenshots:** taken with ADB during the match and cropped to the ping indicator. Mean interval 1.4 s.
- **Game modes:** CoD matches were all played in FRONTLINE mode (5v5).
- **No anonymization:** captures and screenshots are the originals from lab devices. They contain local IP addresses (192.168.x.x) and the public IP addresses of the game servers.

## License

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Please cite this record (DOI on the Zenodo page) and the paper.

## Contact

Yehonatan Zion, Ariel University, yehonata.zion@msmail.ariel.ac.il
