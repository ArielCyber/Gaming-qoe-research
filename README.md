# Gaming QoE Research: Per-Second QoE Estimation from Encrypted Traffic

Code for estimating the Quality of Experience (QoE) of mobile first-person shooter (FPS) games, second by second, from passive network traffic only. No payload is inspected: the models see packet counts, sizes and timings of the encrypted game flows.

Games: **Call of Duty: Mobile**, **Free Fire**, **PUBG Mobile** and **Guns of Boom**.

This repository accompanies the journal paper *"Every second counts! High granularity Quality of Experience Prediction for First-Person Shooter Online Gaming"* (under review), which extends our CCNC 2026 conference paper.

## Data

The raw data is on Zenodo: **[10.5281/zenodo.24051689](https://doi.org/10.5281/zenodo.24051689)**.

| Game | Matches |
|---|---|
| Call of Duty: Mobile | 615 |
| Free Fire | 407 |
| PUBG Mobile | 184 |
| Guns of Boom | 300 |

For every match: the network capture of the Android phone (`.pcapng` / `.pcap`), cropped screenshots of the in-game ping indicator (about every 1.4 s) and the screenshot log. Latency of 0 to 500 ms was added with Clumsy on the access point. Start with `gaming_qoe_sample.zip` (3 matches per game). The scripts that built the release are in `scripts/data_release/`.

## How it works

1. **Capture.** The phone plays through a Windows access point that records the traffic (Wireshark) and adds latency (Clumsy). ADB takes a screenshot of the in-game ping indicator about every 1.4 s.
2. **Per-second labels.** The ping value is read from each screenshot by OCR (an ensemble of OCR pipelines, majority vote), giving one ping value, and so one QoE label, per second of gameplay. Frames from death, match start and match end, and unreadable frames, are dropped.
3. **Features.** Each capture is reduced to the game flow (per-game UDP filter) and cut into 1-second samples. Over a sliding window (10 s by default) the extractor computes 62 features: six statistics (min, max, mean, median, std, last value) for seven directional metrics (upload and download PPS, packet size and inter-arrival time, plus the client-to-server PPS ratio), and five statistics for four combined metrics (total PPS, IAT, bytes and average packet size).
4. **QoE classes.** Ping is mapped to QoE classes:

   | Scheme | Classes (ping in ms) |
   |---|---|
   | 3 classes | Excellent below 120, Fair 120 to 160, Bad 160 and above |
   | 5 classes | Excellent below 80, Good 80 to 120, Fair 120 to 160, Poor 160 to 200, Bad 200 and above |

5. **Models.** Random Forest, XGBoost, CatBoost, LightGBM, KNN, FaissKNN (approximate KNN), Decision Tree and Logistic Regression, evaluated with stratified 5-fold cross-validation, `random_state=42`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`training/run_models.py` needs scikit-learn below 1.8 (tested: 1.7.2, pandas 2.2.3).

## Usage

Extract features from the captures (per-game settings in `features/games.py`):

```bash
python features/extract.py --game cod --window 10
# -> datasets/cod/features_cod_10s.csv     (games: cod, freefire, pubg, gob)
```

The extractor needs the captures and a labels file per game (`datasets/<game>/labels_<game>.csv`: match folder, capture file name and the OCR ping per second). `DATA.md` describes the data files and their layout.

Train and evaluate:

```bash
python training/run_models.py --game cod --classes 3 5
python training/run_models.py --game all_games --features 30
```

Options: `--window` (window size in seconds), `--classes` (2, 3, 5), `--features` (62, 47, 30), `--smote`, `--file` (explicit dataset CSV).

Paper figures: `python figures/make_all.py` (see `figures/README.md`).

Real-time prediction on a live interface:

```bash
python realtime.py --window-size 10 --model ./model.pkl --interface eth0 --ring ./capture_ring
```

## Repository layout

| Path | Content |
|---|---|
| `results/` | paper results: metrics and confusion matrices per game, three and five classes |
| `features/` | feature extractor for all games (`extract.py`, `games.py`) |
| `training/` | model training and evaluation (`run_models.py`) |
| `figures/` | paper figures |
| `scripts/data_release/` | build and upload of the Zenodo raw-data release |
| `Free-Fire/`, `data_collection_adb/` | data collection and OCR labeling tools |
| `gaming-qoe-conference/` | reproduction package of the CCNC 2026 conference paper (own `requirements.txt`) |
| `realtime.py` | live capture and prediction |
| `rank.py` | ping to QoE class mapping |
| `analyze.py`, `new___analyze.py` | earlier extractors, kept for reference |

## Citation

Please cite the dataset and the paper (citation added on acceptance):

```bibtex
@misc{gamingQoEDataset,
  author    = {Zion, Yehonatan and Dvir, Amit and Hajaj, Chen and Dubin, Ran and Opatowsky, Dvir},
  title     = {Mobile Gaming {QoE} Dataset: Encrypted Network Traffic Captures and In-Game Ping Screenshots},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.24051689}
}
```

## License

Code: MIT (see `LICENSE`). Data: CC BY 4.0 (see the Zenodo record).
