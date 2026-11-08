import os
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
            'pkt_dir_ratio_std', 'pkt_dir_ratio_min', 'pkt_dir_ratio_max']
FINAL_COLUMNS = FEATURE_COLUMNS + ['ping']
# FEATURE_COLUMNS += [

#     "src2dst_iat",
#     "src2dst_iat_mean",
#     "src2dst_iat_median",
#     "src2dst_iat_std",
#     "src2dst_iat_min",
#     "src2dst_iat_max",

#     "dst2src_iat",
#     "dst2src_iat_mean",
#     "dst2src_iat_median",
#     "dst2src_iat_std",
#     "dst2src_iat_min",
#     "dst2src_iat_max",

# ]






files = [
    "output/subset_window_1754898203.csv",
    "output/window_3_1756030271.csv",
    "output/window_5_1756032959.csv","output/window_10_1754904064.csv","output/window_15_1756035248.csv"
]



# # F_C = [
# #             'src2dst_avg_pkt_size', 'src2dst_avg_pkt_size_mean', 'src2dst_avg_pkt_size_median',
# #             'src2dst_avg_pkt_size_std', 'src2dst_avg_pkt_size_min', 'src2dst_avg_pkt_size_max',
# #                         'dst2src_avg_pkt_size', 'dst2src_avg_pkt_size_mean', 'dst2src_avg_pkt_size_median',
# #             'dst2src_avg_pkt_size_std', 'dst2src_avg_pkt_size_min', 'dst2src_avg_pkt_size_max',
# #                                 'pkt_dir_ratio_std',]
# F_C= [          'src2dst_avg_pkt_size', 'src2dst_avg_pkt_size_mean', 'src2dst_avg_pkt_size_median',
#             'src2dst_avg_pkt_size_std', 'src2dst_avg_pkt_size_min', 'src2dst_avg_pkt_size_max',
#             'src2dst_pps', 'src2dst_pps_mean', 'src2dst_pps_median',
#             'src2dst_pps_std', 'src2dst_pps_min', 'src2dst_pps_max',
#             'dst2src_avg_pkt_size', 'dst2src_avg_pkt_size_mean', 'dst2src_avg_pkt_size_median',
#             'dst2src_avg_pkt_size_std', 'dst2src_avg_pkt_size_min', 'dst2src_avg_pkt_size_max',
#             'dst2src_pps', 'dst2src_pps_mean', 'dst2src_pps_median',
#             'dst2src_pps_std', 'dst2src_pps_min', 'dst2src_pps_max',
#             'pkt_dir_ratio', 'pkt_dir_ratio_mean', 'pkt_dir_ratio_median',
#             'pkt_dir_ratio_std', 'pkt_dir_ratio_min', 'pkt_dir_ratio_max']
# F_C += [


#     "src2dst_iat",
#     "src2dst_iat_mean",
#     "src2dst_iat_median",
#     "src2dst_iat_std",
#     "src2dst_iat_min",
#     "src2dst_iat_max",


#     "dst2src_iat",
#     "dst2src_iat_mean",
#     "dst2src_iat_median",
#     "dst2src_iat_std",
#     "dst2src_iat_min",
#     "dst2src_iat_max",


# ]
# F_C += [

#     "pps_mean",
#     "pps_median",
#     "pps_std",
#     "pps_min",
#     "pps_max",

# ]
# FEATURE_COLUMNS = F_C
# FINAL_COLUMNS = F_C + ['ping']
# F_C = F_C + ['ping']

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

def five_fold_eval(df_tr, df_te, clf, n_splits=5, feature_columns=None, use_smote=True):
    print(f"{YELLOW}Evaluating {clf.__class__.__name__} with {n_splits}-fold CV...{RESET}")

    # 🔹 דאטה A (אימון)
    X_A = df_tr[feature_columns].to_numpy(dtype='float32')
    y_A = df_tr['y'].to_numpy(dtype='int64')

    # 🔹 דאטה B (בדיקה)
    X_B = df_te[feature_columns].to_numpy(dtype='float32')
    y_B = df_te['y'].to_numpy(dtype='int64')

    le = LabelEncoder()
    y_A_enc = le.fit_transform(y_A)
    y_B_enc = le.transform(y_B)

    classes = le.classes_
    n_classes = len(classes)

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    accs, f1s, recalls_macro = [], [], []
    train_times, test_times = [], []

    cm_sum = np.zeros((n_classes, n_classes), dtype=np.int64)

    for fold, (tr, _) in enumerate(skf.split(X_A, y_A_enc)):
        print(f"  Fold {fold+1}/{n_splits}...")

        X_train = X_A[tr]
        y_train = y_A_enc[tr]

        idx = np.random.choice(len(X_B), int(0.2 * len(X_B)), replace=False)
        X_test = X_B[idx]
        y_test = y_B_enc[idx]

        if use_smote:
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
def evaluate_models_on_df(df2,use_smote,df,class_type=3):
    results_base_path = os.path.join(dataset_path, "results")

    base_run_path = os.path.join(
    results_base_path,
    f"class_{class_type}",
    "smote" if use_smote else "no_smote"
    )

    os.makedirs(base_run_path, exist_ok=True)
    df = df.dropna(subset=FEATURE_COLUMNS + ['ping']).copy()
    df2 = df2.dropna(subset=FEATURE_COLUMNS + ['ping']).copy()

    if class_type == 3:
        df['y'] = df['ping'].apply(lambda p: rank_str_to_int_mapping_3_classes[rank_qoe_3_classes(p)])
        df2['y'] = df2['ping'].apply(lambda p: rank_str_to_int_mapping_3_classes[rank_qoe_3_classes(p)])

    if class_type == 5:
        df['y'] = df['ping'].apply(lambda p: rank_str_to_int_mapping[rank_qoe(p)])
        df2['y'] = df2['ping'].apply(lambda p: rank_str_to_int_mapping[rank_qoe(p)])
    if class_type == 2:
        df['y'] = df['ping'].apply(lambda p: rank_str_to_int_mapping2[rank_qoe2(p)])
        df2['y'] = df2['ping'].apply(lambda p: rank_str_to_int_mapping2[rank_qoe2(p)])
    print(df.y.value_counts())  
    df=df.sample(frac=1, random_state=42).reset_index(drop=True) 
    df2=df2.sample(frac=1, random_state=42).reset_index(drop=True) 

    print(df.y.value_counts())  
    print(df2.y.value_counts())  

    models = make_models(n_classes=class_type, knn_k=3, knn_weights='uniform', knn_metric='minkowski')
    final_results = {}
    results = []

    for name, clf in models:
        print(name)

        train_times, test_times, accs, f1s, recalls_macro, per_class_recall, classes, cm_sum = five_fold_eval(df,df2, clf, n_splits=5, feature_columns=FEATURE_COLUMNS, use_smote=use_smote)
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

        save_confusion_matrix(class_type,use_smote,cm_sum, classes, name, model_path, normalize=False)
        save_confusion_matrix(class_type,use_smote,cm_sum, classes, name, model_path, normalize=True)

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
        print(f"    {per_class_str}")
# df = pd.read_csv(
#     r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\michael_data\combined_dataset.csv"
# )
# dataset_path = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\michael_data"
# evaluate_models_on_df(use_smote=False, df=df, class_type=3)

def run(df,df2):
    # evaluate_models_on_df(use_smote=False, df=df, class_type=2)
    evaluate_models_on_df(df2,use_smote=False, df=df, class_type=3)
    # evaluate_models_on_df(use_smote=False, df=df, class_type=5)

    # evaluate_models_on_df(use_smote=True, df=df, class_type=2)
    evaluate_models_on_df(df2,use_smote=True, df=df, class_type=3)
    # evaluate_models_on_df(use_smote=True, df=df, class_type=5)

df_C_O_D = pd.read_csv(
    r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\Call_of_Duty_data\dataset_C_O_D.csv"
)
# dataset_path = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\Call_of_Duty_data"
# run(df)

df_Guns_Of_Boom = pd.read_csv(
    r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\asath_data\dataset_Guns_Of_Boom.csv"
)
# dataset_path = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\asath_data"
# run(df)


df_PUBG = pd.read_csv(
    r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\menash_data\dataset_PUBG.csv"
)
# dataset_path = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\menash_data"
# run(df)



df4 = pd.read_csv(
    r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\michael_data\combined_dataset.csv"
)
# dataset_path = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\michael_data"
# run(df)

# PUBG:
dataset_path = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\autcome_df1_on_df2\PUBG\PUBG_on_GOB"
run(df_PUBG,df_Guns_Of_Boom)

dataset_path = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\autcome_df1_on_df2\PUBG\PUBG_on_FF"
run(df_PUBG,df4)

dataset_path = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\autcome_df1_on_df2\PUBG\PUBG_on_COD"
run(df_PUBG,df_C_O_D)

# Guns_Of_Boom:
dataset_path = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\autcome_df1_on_df2\GOB\GOB_on_COD"
run(df_Guns_Of_Boom,df_C_O_D)

dataset_path = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\autcome_df1_on_df2\GOB\GOB_on_FF"
run(df_Guns_Of_Boom,df4)

dataset_path = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\autcome_df1_on_df2\GOB\GOB_on_PUBG"
run(df_Guns_Of_Boom,df_PUBG)

# Free_Fire:
dataset_path = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\autcome_df1_on_df2\FF\FF_on_COD"
run(df4,df_C_O_D)

dataset_path = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\autcome_df1_on_df2\FF\FF_on_GOB"
run(df4,df_Guns_Of_Boom)

dataset_path = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\autcome_df1_on_df2\FF\FF_on_PUBG"
run(df4,df_PUBG)

# Call_Of_Duty:
dataset_path = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\autcome_df1_on_df2\cod\cod_on_GOB"
run(df_C_O_D,df_Guns_Of_Boom)

dataset_path = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\autcome_df1_on_df2\cod\cod_on_FF"
run(df_C_O_D,df4)

dataset_path = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\autcome_df1_on_df2\cod\cod_on_PUBG"
run(df_C_O_D,df_PUBG)