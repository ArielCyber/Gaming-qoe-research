---

# 📂 First_Action - Initial Data Preparation for QoE Research

Welcome to the foundational stage of the project. This directory serves as the **gateway** to our research, where initial processing of raw network captures (PCAP) and visual telemetry from the game **"Free Fire"** is conducted.

## 🎯 Objectives of First_Action:

The primary purpose of this directory is to centralize the pre-processing workflow required immediately after data collection. Here, we transform "noisy" raw data into a refined, structured dataset ready for deep statistical and behavioral analysis.

## 📜 Workflow and Protocol

This README provides a general overview. For precise execution order and technical instructions on transitioning between tools, please refer to the detailed protocol file:
📄 `Protocol_Ping_Recognition_in_Image_Folders.txt`

---

## 🛠️ Directory Structure and Component Details

### 1. Operational Scripts (Direct Interaction)

| File Name | Functional Description |
| --- | --- |
| `Cut_pcap_V5_gm.py` | Truncates the trailing ends of PCAP recordings in cases where capture continued post-match. |
| `Ping_Verifier_None_V1_gm.py` | Facilitates manual annotation of images where recognition failed (`None`). Launches a GUI for user input. |
| `Ping_Verifier_V1.2_gm.py` | Enables manual validation for ping values detected outside defined logical thresholds (X to Y). |
| `prefix_remover_V1_gm.py` | A cleanup utility to remove "V_" status prefixes from directory names after successful processing. |
| `rename_manager_V2_gm.py` | Automated orchestrator for ping-based file renaming (utilizes components in `file_to_use`). |
| `quality_check_V3_gm.py` | Generates integrity reports: counts `None` values, untagged images, and identifies specific filenames requiring attention. |
| `fill_missing_frames_v2_gm.py` | Ensures temporal continuity by inserting white placeholder frames where data gaps are detected. |
| `Error_Image_Collector_V1_gm.py` | Aggregates unrecognized images into a dedicated dataset for future model retraining and fine-tuning. |
| `Find_Missing_Pcaps_gm.py` | Audits the dataset to identify session directories missing corresponding PCAP files. |

### 2. Internal Engine: `file_to_use/`

This subdirectory contains the backend modules utilized by the operational scripts. **Manual modification or execution of these files is generally not required**, as they function as the underlying processing engine:

* **`ping_extractor_V33_SuperHybrid_gm.py`**: Our advanced extraction algorithm, utilizing a hybrid approach to optimize ping recognition from video frames.
* **`ping_renamer_V1_gm.py`**: Logic handler for real-time file renaming based on extracted numerical telemetry.
* **`ping_model_final.keras`**: The trained Deep Learning model (CNN) responsible for optical character recognition of in-game ping digits.
* **`digits_font/`**: A repository of visual assets used for template matching and font characteristic comparison.

---
