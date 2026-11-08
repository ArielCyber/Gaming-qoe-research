"""
Paper Reproduction Utilities
Helper functions for debugging and validating the paper reproduction notebook.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from rank import rank_qoe_3_classes, rank_str_to_int_mapping_3_classes


def validate_environment():
    """Check if all required packages are available."""
    packages = ['pandas', 'numpy', 'sklearn', 'matplotlib', 'xgboost']
    missing = []
    
    for pkg in packages:
        try:
            __import__(pkg)
            print(f"✓ {pkg}: Available")
        except ImportError:
            missing.append(pkg)
            print(f"✗ {pkg}: Missing")
    
    if missing:
        print(f"\nInstall missing packages: pip install {' '.join(missing)}")
        return False
    return True


def validate_datasets():
    """Check if all required datasets are available."""
    window_files = {
        3: 'output/window_3_1756030271.csv',
        5: 'output/window_5_1756032959.csv', 
        10: 'output/window_10_1754904064.csv',
        15: 'output/window_15_1756035248.csv'
    }
    
    print("Dataset validation:")
    all_available = True
    
    for size, filepath in window_files.items():
        path = Path(filepath)
        if path.exists():
            df = pd.read_csv(path, nrows=5)  # Quick check
            print(f"✓ {size}s: {path.stat().st_size // 1024:,} KB, {len(pd.read_csv(path)):,} rows")
        else:
            print(f"✗ {size}s: Missing - {filepath}")
            all_available = False
    
    return all_available


def check_data_structure(filepath="output/window_10_1754904064.csv"):
    """Validate data structure and feature availability."""
    if not Path(filepath).exists():
        print(f"Error: Dataset not found - {filepath}")
        return False
    
    df = pd.read_csv(filepath)
    print(f"Dataset shape: {df.shape}")
    
    # Check required columns
    required_cols = ['ping', 'self_rate_qoe_score', 'exp_id']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        print(f"Missing required columns: {missing_cols}")
        return False
    
    # Check feature columns
    feature_cols = [
        'src2dst_avg_pkt_size', 'dst2src_avg_pkt_size', 'src2dst_pps', 'dst2src_pps',
        'pkt_dir_ratio'
    ]
    available_features = [col for col in feature_cols if col in df.columns]
    print(f"Available features: {len(available_features)}/30 expected")
    
    # Check QoE distribution
    print("\nQoE distributions:")
    if 'ping' in df.columns:
        ping_qoe = df['ping'].apply(lambda x: rank_str_to_int_mapping_3_classes[rank_qoe_3_classes(x)])
        print(f"Ping-based QoE: {ping_qoe.value_counts().sort_index().to_dict()}")
    
    if 'self_rate_qoe_score' in df.columns:
        survey_qoe = df['self_rate_qoe_score'].apply(lambda x: 1 if x in [1, 2] else (2 if x == 3 else 3))
        print(f"Survey-based QoE (3-class): {survey_qoe.value_counts().sort_index().to_dict()}")
    
    return True


def quick_model_test():
    """Test model creation and basic functionality."""
    try:
        from model_utils import make_models
        
        models = make_models(3)
        print(f"Created {len(models)} models successfully:")
        
        for name, model in models:
            print(f"  {name}: {type(model).__name__}")
        
        return True
    except Exception as e:
        print(f"Model creation failed: {e}")
        return False


def run_all_validations():
    """Run all validation checks."""
    print("="*50)
    print("PAPER REPRODUCTION VALIDATION")
    print("="*50)
    
    checks = [
        ("Environment", validate_environment),
        ("Datasets", validate_datasets), 
        ("Data Structure", check_data_structure),
        ("Model Creation", quick_model_test)
    ]
    
    all_passed = True
    for name, check_func in checks:
        print(f"\n{name}:")
        try:
            result = check_func()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"✗ {name} check failed: {e}")
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("✓ ALL CHECKS PASSED - Ready for paper reproduction!")
    else:
        print("✗ Some checks failed - Please fix issues before running notebook")
    print("="*50)
    
    return all_passed


if __name__ == "__main__":
    run_all_validations()
