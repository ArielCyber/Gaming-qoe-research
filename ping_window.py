import pandas as pd
import numpy as np
import ast
from rank import rank_qoe, rank_str_to_int_mapping

from rank import rank_qoe_3_classes, rank_str_to_int_mapping_3_classes
WINDOW = 10
rows = []

metadata = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\metadata.csv"
meta_df = pd.read_csv(metadata)

for folder in meta_df["folder"].dropna().unique():
    game_df = meta_df[meta_df["folder"] == folder]

    seq = []

    # בונים רצף ערכים
    for _, r in game_df.iterrows():
        d = ast.literal_eval(r["time_value_pairs"])
        vals = list(d.values())
        vals = [np.nan if v is None else float(v) for v in vals]
        seq.extend(vals)

    # rolling window
    for i in range(len(seq) - WINDOW):
        w = seq[i:i+WINDOW+1]   # 11 ערכים

        X = w[:WINDOW]          # 10 אחורה
        y = w[WINDOW]           # הבא

        row = {str(j+1): X[j] for j in range(WINDOW)}  # "1".."10"
        row["y"] = y


        if pd.isna(y):
            continue
        rows.append(row)

# יוצרים DF
final_df = pd.DataFrame(rows)

# שומרים לקובץ
out_path = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\ping_windows_10.csv"
final_df.to_csv(out_path, index=False)

print("Saved to:", out_path)
print(final_df.head())


X = final_df[[str(i) for i in range(1, 11)]]
y3 = final_df["y"]
y5 = final_df["y"]


y3 = y3.apply(lambda p: rank_str_to_int_mapping_3_classes[rank_qoe_3_classes(p)])
y5 = y5.apply(lambda p: rank_str_to_int_mapping[rank_qoe(p)])

X = X.fillna(0)
y3 = y3.fillna(0)
y5 = y5.fillna(0)


from sklearn.model_selection import train_test_split

X_train3, X_test3, y_train3, y_test3 = train_test_split(
    X, y3, test_size=0.2, random_state=42
)

# split ל-5 classes
X_train5, X_test5, y_train5, y_test5 = train_test_split(
    X, y5, test_size=0.2, random_state=42
)

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

clf3 = RandomForestClassifier(n_estimators=100, random_state=42)
clf3.fit(X_train3, y_train3)

y_pred3 = clf3.predict(X_test3)

print("=== 3 Classes ===")
print("Accuracy:", accuracy_score(y_test3, y_pred3))
print(classification_report(y_test3, y_pred3))

clf5 = RandomForestClassifier(n_estimators=100, random_state=42)
clf5.fit(X_train5, y_train5)

y_pred5 = clf5.predict(X_test5)

print("=== 5 Classes ===")
print("Accuracy:", accuracy_score(y_test5, y_pred5))
print(classification_report(y_test5, y_pred5))