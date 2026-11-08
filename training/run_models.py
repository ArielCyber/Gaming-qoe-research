import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # ← בלי GUI בכלל
from ANN import FaissKNN
from sklearn.svm import SVC
import matplotlib.pyplot as plt
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier
from imblearn.over_sampling import SMOTE
from sklearn.pipeline import make_pipeline
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from rank import rank_qoe2, rank_str_to_int_mapping2
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.preprocessing import StandardScaler, LabelEncoder
from rank import rank_qoe, rank_str_to_int_mapping
from rank import rank_qoe_3_classes, rank_str_to_int_mapping_3_classes
from sklearn.model_selection import train_test_split, StratifiedKFold, KFold
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix, recall_score





RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
RESET = "\033[0m"

new_ficherse=1
if new_ficherse==0:
        
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
if new_ficherse==1:
        
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
    FEATURE_COLUMNS += [

        "src2dst_iat",
        "src2dst_iat_mean",
        "src2dst_iat_median",
        "src2dst_iat_std",
        "src2dst_iat_min",
        "src2dst_iat_max",

        "dst2src_iat",
        "dst2src_iat_mean",
        "dst2src_iat_median",
        "dst2src_iat_std",
        "dst2src_iat_min",
        "dst2src_iat_max",

    ]
    FEATURE_COLUMNS += [

        "pps_mean",
        "pps_median",
        "pps_std",
        "pps_min",
        "pps_max",
    ]

    FEATURE_COLUMNS += [

        "iat_mean",
        "iat_median",
        "iat_std",
        "iat_min",
        "iat_max",

    ]
    FEATURE_COLUMNS += [

        "bytes_mean",
        "bytes_median",
        "bytes_std",
        "bytes_min",
        "bytes_max",

    ]
    FEATURE_COLUMNS += [

        "avg_pkt_size_mean",
        "avg_pkt_size_median",
        "avg_pkt_size_std",
        "avg_pkt_size_min",
        "avg_pkt_size_max",

    ]
FINAL_COLUMNS = FEATURE_COLUMNS + ['ping']










def get_model_path(base_path, class_type, use_smote, model_name):
    smote_str = "smote" if use_smote else "no_smote"

    path = os.path.join(
        base_path,
        f"class_{class_type}",
        smote_str,
        model_name
    )

    os.makedirs(path, exist_ok=True)
    return path



def make_models(n_classes: int,knn_k: int = 5,knn_weights: str = 'uniform',knn_metric: str = 'minkowski'):

    models = [
        ('RF', RandomForestClassifier(
            random_state=42,
            n_estimators=300,
            max_depth=None,
            n_jobs=-1,
            class_weight='balanced'
        )),
        ('DT', DecisionTreeClassifier(
            random_state=42,
            class_weight='balanced'
        ))
        ,
        ('LR', make_pipeline(
            StandardScaler(),
            LogisticRegression(
                random_state=42,
                max_iter=2000,
                multi_class='auto',
                class_weight='balanced'
            )
        ))
        # ,
        # ('SVM', make_pipeline(
        #     StandardScaler(),
        #     SVC(
        #         random_state=42,
        #         class_weight='balanced'
        #     )
        # ))
    ]

    if n_classes == 2:
        xgb = XGBClassifier(
            objective='binary:logistic',
            eval_metric='logloss',
            random_state=42,
            n_estimators=300,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            tree_method='hist',
            n_jobs=-1
        )

        lgbm = LGBMClassifier(
            objective='binary',
            random_state=42,
            n_estimators=300,
            learning_rate=0.05,
            num_leaves=31,
            subsample=0.8,
            colsample_bytree=0.8,
            class_weight='balanced',
            n_jobs=-1,
            force_col_wise=True,
            verbose=-1
        )

        cat = CatBoostClassifier(
            loss_function='Logloss',
            random_seed=42,
            iterations=300,
            learning_rate=0.05,
            depth=6,
            verbose=False
        )
    else:
        xgb = XGBClassifier(
            objective='multi:softprob',
            num_class=n_classes,
            eval_metric='mlogloss',
            random_state=42,
            n_estimators=300,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            tree_method='hist',
            n_jobs=-1
        )

        lgbm = LGBMClassifier(
            objective='multiclass',
            num_class=n_classes,
            random_state=42,
            n_estimators=300,
            learning_rate=0.05,
            num_leaves=31,
            subsample=0.8,
            colsample_bytree=0.8,
            class_weight='balanced',
            n_jobs=-1,
            force_col_wise=True,
            verbose=-1
        )

        cat = CatBoostClassifier(
            loss_function='MultiClass',
            random_seed=42,
            iterations=300,
            learning_rate=0.05,
            depth=6,
            verbose=False
        )

    models.append(('XGBoost', xgb))
    # models.append(('LGBM', lgbm))
    models.append(('CatBoost', cat))

    knn = make_pipeline(
        StandardScaler(),
        KNeighborsClassifier(
            n_neighbors=knn_k,
            weights=knn_weights,
            metric=knn_metric,
            n_jobs=-1
        )
    )
    models.append(('KNN', knn))


    FaissKNN1 = FaissKNN(k=5, nlist=50, nprobe=5)
    models.append(('FaissKNN_fast', FaissKNN1))


    return models



def five_fold_eval(df, clf, n_splits=5, feature_columns=None, use_smote=True):
    print(f"{YELLOW}Evaluating {clf.__class__.__name__} with {n_splits}-fold CV...{RESET}")
    X = df[feature_columns].to_numpy(dtype='float32')
    y = df['y'].to_numpy(dtype='int64')

    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    classes = le.classes_
    n_classes = len(classes)

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    accs, f1s, recalls_macro = [], [], []
    train_times, test_times = [], []

    cm_sum = np.zeros((n_classes, n_classes), dtype=np.int64)
 
    for tr, te in skf.split(X, y_enc):
        print(f"  Fold {len(accs)+1}/{n_splits}...")

        X_train, X_test = X[tr], X[te]
        y_train, y_test = y_enc[tr], y_enc[te]






        if use_smote:
            # דוגמה פשוטה: מאזן את כל המחלקות המיעוט עד גודל מחלקת הרוב
            smote = SMOTE(random_state=42, k_neighbors=3)
            smote = SMOTE(
                sampling_strategy='not majority',
                random_state=42,
                k_neighbors=3
            )
     
            X_train, y_train = smote.fit_resample(X_train, y_train)

        t0 = time.perf_counter()
        clf.fit(X_train, y_train)
        t1 = time.perf_counter()

        y_pred = clf.predict(X_test)
        t2 = time.perf_counter()

        train_times.append(t1 - t0)
        test_times.append(t2 - t1)

        accs.append(accuracy_score(y_test, y_pred))
        f1s.append(f1_score(y_test, y_pred, average='macro'))
        recalls_macro.append(recall_score(y_test, y_pred, average='macro', zero_division=0))

        cm = confusion_matrix(y_test, y_pred, labels=np.arange(n_classes))
        cm_sum += cm

    tp = cm_sum.diagonal().astype(float)
    fn = cm_sum.sum(axis=1) - tp
    per_class_recall = np.divide(
        tp,
        tp + fn,
        out=np.zeros_like(tp, dtype=float),
        where=(tp + fn) != 0
    )

    return train_times, test_times, accs, f1s, recalls_macro, per_class_recall, classes, cm_sum

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

def save_confusion_matrix(class_type, use_smote, cm,
                          classes,
                          model_name,
                          save_dir,
                          normalize=False):
    """
    Saves confusion matrix as PNG (and optionally normalized).

    Parameters
    ----------
    cm : np.ndarray
        Confusion matrix (absolute counts).
    classes : list or array
        Class labels.
    model_name : str
        Name of the model (for title + filename).
    save_dir : str
        Directory to save file.
    normalize : bool
        If True → normalize rows to percentages.
    """
    title = f"class{class_type}_smote{use_smote}"  
    os.makedirs(save_dir, exist_ok=True)

    cm_to_plot = cm.astype(float)

    if normalize:
        row_sums = cm_to_plot.sum(axis=1, keepdims=True)
        cm_to_plot = np.divide(
            cm_to_plot,
            row_sums,
            out=np.zeros_like(cm_to_plot),
            where=row_sums != 0
        )

    plt.figure(figsize=(6,5))
    plt.imshow(cm_to_plot, interpolation='nearest')
    plt.title(f"Confusion Matrix - {model_name} - {title}")
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.xticks(range(len(classes)), classes)
    plt.yticks(range(len(classes)), classes)
    plt.colorbar()

    # כתיבת הערכים בתוך התאים
    for i in range(cm_to_plot.shape[0]):
        for j in range(cm_to_plot.shape[1]):
            if normalize:
                value = f"{cm_to_plot[i, j]:.2f}"
            else:
                value = str(int(cm_to_plot[i, j]))

            plt.text(j, i, value, ha='center', va='center')

    plt.tight_layout()

    suffix = "_normalized" if normalize else ""
    file_path = os.path.join(save_dir, f"cm_{model_name}_{title}_{suffix}.png")
    plt.savefig(file_path, dpi=200)
    plt.close()

    print(f"Saved confusion matrix image: {file_path}")

import warnings
warnings.filterwarnings(
    "ignore",
    message="X does not have valid feature names, but LGBMClassifier was fitted with feature names",
)
def evaluate_models_on_df(use_smote,df,class_type=3):
    results_base_path = dataset_path   # main() already points dataset_path at a results folder

    base_run_path = os.path.join(
    results_base_path,
    f"class_{class_type}",
    "smote" if use_smote else "no_smote"
    )

    os.makedirs(base_run_path, exist_ok=True)
    df = df.dropna(subset=FEATURE_COLUMNS + ['ping']).copy()

    if class_type == 3:
        df['y'] = df['ping'].apply(lambda p: rank_str_to_int_mapping_3_classes[rank_qoe_3_classes(p)])
    if class_type == 5:
        df['y'] = df['ping'].apply(lambda p: rank_str_to_int_mapping[rank_qoe(p)])
    if class_type == 2:
        df['y'] = df['ping'].apply(lambda p: rank_str_to_int_mapping2[rank_qoe2(p)])
    print(df.y.value_counts())  
    df=df.sample(frac=1, random_state=42).reset_index(drop=True)  
    print(df.y.value_counts())  

    models = make_models(n_classes=class_type, knn_k=3, knn_weights='uniform', knn_metric='minkowski')
    final_results = {}
    results = []

    for name, clf in models:
        print(name)

        train_times, test_times, accs, f1s, recalls_macro, per_class_recall, classes, cm_sum = five_fold_eval(df, clf, n_splits=5, feature_columns=FEATURE_COLUMNS, use_smote=use_smote)
        accs = np.array(accs)
        f1s = np.array(f1s)
        recalls_macro = np.array(recalls_macro)
        train_times = np.array(train_times)
        test_times = np.array(test_times)
        final_results[name] = {
            'accs': accs,
            'f1s': f1s,
            'recalls_macro': recalls_macro,
            'train_times': train_times,
            'test_times': test_times,
            'per_class_recall': per_class_recall,
            'classes': classes
        }
        results.append({

            **{
                f"Recall class {cls}": f"{rec:.3f}"
                for cls, rec in zip(classes, per_class_recall)
            },
                        "Test Time": f"{np.mean(test_times):.3f} ± {np.std(test_times):.3f}",
            "Train Time": f"{np.mean(train_times):.3f} ± {np.std(train_times):.3f}",
            "Macro Recall": f"{np.mean(recalls_macro):.3f} ± {np.std(recalls_macro):.3f}",
            "Macro F1": f"{np.mean(f1s):.3f} ± {np.std(f1s):.3f}",
            "Accuracy": f"{np.mean(accs):.3f} ± {np.std(accs):.3f}",
            "Model": name

        })
        model_path = get_model_path(results_base_path, class_type, use_smote, name)

        save_confusion_matrix(class_type, use_smote, cm_sum, classes, name, model_path, normalize=False)
        save_confusion_matrix(class_type, use_smote, cm_sum, classes, name, model_path, normalize=True)

    df_results = pd.DataFrame(results)

    title = f"class{class_type}_smote{use_smote}"  

    file_path = os.path.join(
    base_run_path,
    f"results_{title}.csv"
)

    df_results.to_csv(file_path, index=False)
    print(df_results)    

    for i in final_results:
        name = i
        res = final_results[i]
        accs = res['accs']
        f1s = res['f1s']
        recalls_macro = res['recalls_macro']
        train_times = res['train_times']
        test_times = res['test_times']
        per_class_recall = res['per_class_recall']
        classes = res['classes']
        print(f"{BLUE}{name:>10}{RESET} → "
            f"{RED}Accuracy {RESET}{accs.mean():.3f} ± {accs.std():.3f} | "
            f"{RED}Macro-F1{RESET} {f1s.mean():.3f} ± {f1s.std():.3f} | "
            f"{RED}Macro-Recall {RESET}{recalls_macro.mean():.3f} ± {recalls_macro.std():.3f} | "
            f"{RED}train {RESET}{train_times.mean():.3f}s ± {train_times.std():.3f}{YELLOW} | {RESET}"
            f"{RED}test {RESET}{test_times.mean():.3f}s ± {test_times.std():.3f}")

        per_class_str = " | ".join(
            f"{GREEN}recall(class={cls})={RESET}{rec:.3f}"
            for cls, rec in zip(classes, per_class_recall)
        )

def run(df):
    evaluate_models_on_df(use_smote=False, df=df, class_type=2)
    evaluate_models_on_df(use_smote=False, df=df, class_type=3)
    evaluate_models_on_df(use_smote=False, df=df, class_type=5)

    evaluate_models_on_df(use_smote=True, df=df, class_type=2)
    evaluate_models_on_df(use_smote=True, df=df, class_type=3)
    evaluate_models_on_df(use_smote=True, df=df, class_type=5)

# ----------------------------------------------------------------------------
# Datasets and command line
# ----------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS_DIR = os.path.join(ROOT, "datasets")
GAMES = ["cod", "freefire", "pubg", "gob", "all_games"]

# Feature sets. "62" is the paper's feature vector. "30" is the conference set.
# "47" is the intermediate set of the pooled run reported in the submitted paper.
FEATURE_SETS = {
    "62": list(FEATURE_COLUMNS),
    "30": list(FEATURE_COLUMNS[:30]),
    "47": list(FEATURE_COLUMNS[:30])
          + [c for c in FEATURE_COLUMNS if c.startswith(("src2dst_iat", "dst2src_iat"))]
          + ["pps_mean", "pps_median", "pps_std", "pps_min", "pps_max"],
}


def dataset_file(game, window, tag):
    """datasets/<game>/features_<game>_<window>s[_<tag>].csv"""
    name = f"features_{game}_{window}s" + (f"_{tag}" if tag else "") + ".csv"
    return os.path.join(DATASETS_DIR, game, name)


def main():
    import argparse
    global dataset_path, FEATURE_COLUMNS, FINAL_COLUMNS
    parser = argparse.ArgumentParser(description="Train and evaluate the paper's models on one dataset.")
    parser.add_argument("--game", required=True, choices=GAMES)
    parser.add_argument("--window", type=int, default=10, help="window size in seconds")
    parser.add_argument("--tag", default="", help="dataset variant, e.g. 'paper' for the frozen paper datasets")
    parser.add_argument("--classes", type=int, nargs="+", default=[3], choices=[2, 3, 5])
    parser.add_argument("--smote", action="store_true", help="oversample the training folds with SMOTE")
    parser.add_argument("--features", default="62", choices=sorted(FEATURE_SETS))
    parser.add_argument("--file", help="explicit dataset CSV (overrides --game/--window/--tag naming)")
    args = parser.parse_args()

    FEATURE_COLUMNS = FEATURE_SETS[args.features]
    FINAL_COLUMNS = FEATURE_COLUMNS + ["ping"]
    path = args.file or dataset_file(args.game, args.window, args.tag)
    df = pd.read_csv(path, low_memory=False)
    # results go next to the data: datasets/<game>/results/<dataset name>/class_N/...
    dataset_path = os.path.join(DATASETS_DIR, args.game, "results",
                                os.path.splitext(os.path.basename(path))[0] + f"_f{args.features}")
    print(f"{path}: {len(df)} rows, {len(FEATURE_COLUMNS)} features -> {dataset_path}")
    for n_classes in args.classes:
        evaluate_models_on_df(use_smote=args.smote, df=df, class_type=n_classes)


if __name__ == "__main__":
    main()
