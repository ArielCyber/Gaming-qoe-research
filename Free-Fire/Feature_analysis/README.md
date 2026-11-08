# 🎮 Game QoE Analysis Suite - Technical Documentation (2026)

This research platform provides an end-to-end framework for analyzing and predicting **Quality of Experience (QoE)** in cloud gaming environments. By integrating network traffic analysis (Packet-level inspection) with supervised Machine Learning (ML), the system identifies statistical correlations between raw network metrics and visual latency indicators (Ping) captured during active gameplay.

---

## ⚠️ Execution Prerequisites (Critical)

**The Backend Engine (`updt_new___analyze.py`) must be executed in its entirety prior to launching the Visualization Notebook.**

The system is designed as a decoupled architecture:

1. **Backend:** Performs heavy data ingestion, feature engineering, and model training.
2. **Notebook:** Functions as an interactive visualization and research layer.

Since the Notebook relies on pre-calculated results stored in CSV and Excel formats, it will fail to initialize the "Data Bridge" (Block 04) if the Backend products are missing.

---

## 🏗️ Backend Architecture: `updt_new___analyze.py`

The Backend serves as the primary processing engine, transforming raw Big Data (PCAPng captures and high-resolution screenshots) into a refined, high-dimensional dataset.

### A. Temporal Synchronization & Pre-processing

1. **`hhmmss_to_seconds(hhmmss)`**:
* **Function:** Normalizes 6-digit timestamp formats into absolute seconds from the start of the day.
* **Purpose:** Acts as the temporal anchor for synchronizing visual ping samples with asynchronous network traffic.


2. **`to_qoe_class_zero(ping)`**:
* **Function:** Classifies continuous ping values into discrete ordinal categories (1: Good, 2: Fair, 3: Poor).
* **Purpose:** Establishes the **Ground Truth** labels for supervised learning models.


3. **`extract_ping_from_filename(filename)`**:
* **Function:** Employs Regular Expressions (Regex) to parse metadata (timestamps and ping values) from image filenames.


4. **`generate_metadata_live(source_path)`**:
* **Function:** Recursively scans session directories to map PCAPng files to their corresponding visual labels.
* **Output:** Generates the **`metadata_results_auto.csv`** file.



### B. Network Discovery & Protocol Analysis

5. **`run_network_exploration()`**:
* **Function:** Conducts deep packet inspection (DPI) by merging **NFStreamer** (flow-level stats) and **Scapy** (packet-level precision). It calculates Game Purity, Inter-Arrival Time (IAT), and Payload signatures.
* **Outputs:** * **`network_analysis_backup.csv`**: A live log providing data persistence and "Resume" capabilities during long-running analysis.
* **`NetDiscovery_Michael_gm.xlsx`**: A formatted report summarizing protocol dominance and network stability per session.





### C. Feature Engineering Pipeline

6. **`weighted_average_decay(arr, r)`**:
* **Function:** Implements a time-decay heuristic where the most recent network samples receive higher statistical weight.


7. **`build_second_vectors(pcap_path)`**:
* **Function:** Leverages a custom NFStreamer plugin to extract PPS (Packets Per Second) and mean packet sizes at a 1-second resolution.


8. **`_process_run_task(row_tuple)`**:
* **Function:** The core worker for parallel processing. Handles time-sync, linear interpolation for missing indices, and 10-second **Rolling Window** statistical calculations.


9. **`generate_training_data_main(meta_df)`**:
* **Function:** Manages asynchronous task distribution across available CPU cores (Multiprocessing).
* **Output:** Generates **`final_training_features.csv`**, which is archived upon completion as **`window_10_[timestamp].csv`**.



### D. Machine Learning & Inference

10. **`top_features_per_model(...)`**:
* **Function:** Trains seven diverse ML models and performs **Permutation Importance** to quantify feature contribution.
* **Output:** Generates **`feature_importance_results.csv`**.


11. **`calculate_scores_and_contributions` / `get_stats_with_logic**`:
* **Function:** Implements **Consensus Logic** to identify dominant features based on agreement across multiple algorithmic architectures.


12. **`generate_full_color_coded_report()`**:
* **Function:** Exports analyzed importance scores into a color-coded Excel report with legend-based coding.
* **Output:** **`Color_Coded_P++200.xlsx`**.



---

## 📊 Notebook Exploration: `Micha_thin_heb...ipynb`

The Notebook provides a scientific interface for data validation and heuristic discovery.

* **Block 1 (Config)**: Initializes global paths, network filters, and parallelization parameters.
* **Block 4 (Smart Data Bridge)**: Scans the `/Products/` directory to automatically load the most recent Backend dataset into the active workspace.
* **Block 6 (QoE Timeline)**: Visualizes the ping fluctuations of specific game sessions, highlighting data gaps (QoE=0).
* **Block 8-10 (Network Profiling)**: Generates pie charts for UDP dominance and scatter plots for flow density to validate traffic integrity.
* **Block 12-13 (Correlation Matrix)**: Calculates **Spearman Correlation** heatmaps to identify feature redundancy and multicollinearity (threshold > 0.85).
* **Block 15-17 (Connectivity Patterns)**: Comparative analysis of how network feature relationships shift dynamically across different QoE classes.
* **Block 18-19 (Statistical Signatures)**: Produces Histograms and **Kernel Density Estimate (KDE)** plots. These visualize the "separability" of network metrics, identifying which features serve as reliable signatures for poor QoE.
* **Block 21 (Final Persistence)**: Re-exports the importance dataframe for archival purposes.

---

## 📂 Summary of Output Artifacts (Products)

| Filename | Source Generator | Description |
| --- | --- | --- |
| `metadata_results_auto.csv` | Backend (`main`) | Session-to-Ping mapping database. |
| `NetDiscovery_Michael_gm.xlsx` | Backend (`run_network_exploration`) | DPI analysis and Jitter metrics. |
| `final_training_features.csv` | Backend (`main`) | Raw feature vectors for ML training. |
| `window_10_[timestamp].csv` | Backend (`main` - Archiving) | Timestamped archive for Notebook bridge. |
| `feature_importance_results.csv` | Backend (`main`) / Notebook (21) | Raw importance rankings per model. |
| `Color_Coded_P++200.xlsx` | Backend (`gen_full_report`) | Final multi-model consensus report. |

---
