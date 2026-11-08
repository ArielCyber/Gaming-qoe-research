"""
Minimal test of paper reproduction pipeline
Tests core functionality without running the full experiment.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from model_utils import make_models
from rank import rank_qoe_3_classes, rank_str_to_int_mapping_3_classes

def test_minimal_pipeline():
    """Test the core pipeline with a small subset of data."""
    
    print("Testing minimal paper reproduction pipeline...")
    
    # Configuration
    RANDOM_STATE = 42
    np.random.seed(RANDOM_STATE)
    DATA_FILE = "output/window_10_1754904064.csv"
    
    # Feature columns
    FEATURE_COLUMNS = [
        'src2dst_avg_pkt_size', 'src2dst_avg_pkt_size_mean', 'src2dst_avg_pkt_size_median', 
        'src2dst_avg_pkt_size_std', 'src2dst_avg_pkt_size_min', 'src2dst_avg_pkt_size_max',
        'src2dst_pps', 'src2dst_pps_mean', 'src2dst_pps_median', 
        'src2dst_pps_std', 'src2dst_pps_min', 'src2dst_pps_max',
        'dst2src_avg_pkt_size', 'dst2src_avg_pkt_size_mean', 'dst2src_avg_pkt_size_median', 
        'dst2src_avg_pkt_size_std', 'dst2src_avg_pkt_size_min', 'dst2src_avg_pkt_size_max',
        'dst2src_pps', 'dst2src_pps_mean', 'dst2src_pps_median', 
        'dst2src_pps_std', 'dst2src_pps_min', 'dst2src_pps_max',
        'pkt_dir_ratio', 'pkt_dir_ratio_mean', 'pkt_dir_ratio_median', 
        'pkt_dir_ratio_std', 'pkt_dir_ratio_min', 'pkt_dir_ratio_max'
    ]
    
    # 1. Load data
    print("1. Loading dataset...")
    dataset = pd.read_csv(DATA_FILE)
    print(f"   Loaded: {dataset.shape[0]} samples")
    
    # 2. Create QoE labels
    print("2. Creating 3-class ping-based QoE labels...")
    dataset['y_qoe_by_ping'] = dataset['ping'].apply(
        lambda ping: rank_str_to_int_mapping_3_classes[rank_qoe_3_classes(ping)]
    )
    
    qoe_dist = dataset['y_qoe_by_ping'].value_counts().sort_index()
    print(f"   QoE distribution: {qoe_dist.to_dict()}")
    
    # 3. Prepare features and target
    print("3. Preparing features and target...")
    X = dataset[FEATURE_COLUMNS].dropna()
    y = dataset.loc[X.index, 'y_qoe_by_ping']
    print(f"   Features: {X.shape[1]} columns, {X.shape[0]} samples")
    
    # 4. Train/test split (small sample for speed)
    print("4. Creating train/test split...")
    X_sample = X.sample(n=min(1000, len(X)), random_state=RANDOM_STATE)
    y_sample = y.loc[X_sample.index]
    
    X_train, X_test, y_train, y_test = train_test_split(
        X_sample, y_sample, test_size=0.2, random_state=RANDOM_STATE, stratify=y_sample
    )
    print(f"   Train: {X_train.shape[0]}, Test: {X_test.shape[0]}")
    
    # 5. Test one model (Random Forest)
    print("5. Testing Random Forest model...")
    models = make_models(3)
    rf_model = dict(models)['RF']
    
    rf_model.fit(X_train, y_train)
    y_pred = rf_model.predict(X_test)
    
    from sklearn.metrics import accuracy_score, f1_score
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average='macro')
    
    print(f"   Accuracy: {accuracy:.3f}")
    print(f"   Macro F1: {f1:.3f}")
    
    # 6. Test artifacts creation
    print("6. Testing artifacts directory creation...")
    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)
    (artifacts_dir / "figures").mkdir(exist_ok=True)
    (artifacts_dir / "tables").mkdir(exist_ok=True)
    print(f"   Created: {artifacts_dir}")
    
    print("\n✓ Minimal pipeline test completed successfully!")
    print("  Ready to run full paper_repro.ipynb notebook")
    
    return True

if __name__ == "__main__":
    test_minimal_pipeline()
