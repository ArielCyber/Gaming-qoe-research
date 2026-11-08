# Project Guide: Encrypted Traffic Characterization and QoE Prediction

This guide centralizes the directory structure and setup instructions for the research environment. The system is designed to process raw gameplay recordings, extract network features, and train machine learning models for accurate latency (Ping) prediction.

## 📂 Directory Structure

* **`First_Action`**: Initial operations on raw recordings, including data synchronization and automated on-screen ping detection (OCR).
* **`Feature_analysis`**: Research notebooks dedicated to extracting multi-layered statistical descriptors from network flows and visual logs.
* **`Training_Pipeline`**: Training, evaluation, and optimization processes for the machine learning ensemble.

---

## ⚙️ Environment Setup and Dependency Management

The project features an automated mechanism to establish an isolated and consistent working environment.

### 1. `requirements.txt` (Library Manifest)

Defines all software packages required to execute the code:

* **Data Processing**: `pandas`, `numpy`.
* **Visualization**: `matplotlib`, `seaborn`.
* **Network Analysis**: `nfstream` (Flow analysis), `openpyxl`, `xlsxwriter` (Excel reporting).
* **Machine Learning**: `scikit-learn`, `xgboost`, `catboost`, `lightgbm`.

### 2. `setup_env.bat` (Environment Automation)

A Windows batch script for **"One-Click Setup"**:

1. **Detection**: Checks for an existing virtual environment (`venv_win`).
2. **Creation**: If missing, it creates a new isolated environment to prevent library conflicts.
3. **Installation**: Activates the environment, upgrades `pip`, and installs all dependencies from `requirements.txt`.
4. **Activation**: If already present, it simply activates the environment for the user.

---

## 🚀 Execution Instructions

### Option A: Using VS Code (Recommended for Developers)

1. Run `setup_env.bat` to build/verify the environment.
2. Open the project folder in **VS Code**.
3. Open any `.ipynb` file.
4. Click **"Select Kernel"** (top-right corner) and choose the Python interpreter located within the `venv_win` folder.

### Option B: Using Jupyter Notebook (Standard Browser Interface)

1. Run `setup_env.bat`.
2. In the active terminal window, type `jupyter notebook` and press Enter.
3. The interface will open automatically in your default web browser.

---
