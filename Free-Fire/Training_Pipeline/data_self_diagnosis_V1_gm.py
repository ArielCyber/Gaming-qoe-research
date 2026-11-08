# data_self_diagnosis_V1_gm.py

'''
מה הוא עושה: סורק את תיקיות האימון (0 עד 9) ובודק האם יש תמונות "חריגות" (Outliers) מבחינת גודל, יחס גובה-רוחב או צפיפות פיקסלים, שעלולות להיות תיוג שגוי.

למה כתבנו אותו: בשלב שבו המודל הציג דיוק נמוך, חשדנו ש"זבל" נכנס לדאטה-סט (למשל, ספרה "7" שמתויגת בטעות כ-"1"). הקוד נכתב כדי לנקות את הנתונים לפני אימון חוזר.
'''

import os
import cv2
import numpy as np
import tensorflow as tf
import re
import shutil

# הגדרות נתיבים
MODEL_PATH = 'thin_ping_model_final.keras'
DATA_PATH = 'final_training_data'
BAD_SAMPLES_DIR = 'bad_samples_review'

# טעינת המודל (ה"מוח" שאימנת)
print(f"[INFO] Loading model: {MODEL_PATH}")
model = tf.keras.models.load_model(MODEL_PATH)

def process_for_ai(img, size=(40, 64)):
    """נרמול התמונה בדיוק כפי שהמודל מכיר מהאימון"""
    kernel = np.ones((3, 3), np.uint8)
    img_f = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)
    img_f = cv2.dilate(img_f, kernel, iterations=1)
    
    h, w = img_f.shape
    # מניעת חלוקה באפס וחישוב קנה מידה
    scale = min(size[1] / max(1, h), size[0] / max(1, w)) * 0.8
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    resized = cv2.resize(img_f, (nw, nh))
    
    canvas = np.zeros((size[1], size[0]), dtype=np.uint8)
    y_off = (size[1] - nh) // 2
    x_off = (size[0] - nw) // 2
    canvas[y_off:y_off+nh, x_off:x_off+nw] = resized
    
    return (canvas.astype('float32') / 255.0).reshape(1, 64, 40, 1)

def run_diagnosis():
    # יצירת תיקיית ביקורת לתמונות בעייתיות
    if not os.path.exists(BAD_SAMPLES_DIR):
        os.makedirs(BAD_SAMPLES_DIR)
        
    total_checked = 0
    mismatches = 0

    print(f"[INFO] Scanning images in {DATA_PATH}...")

    # מעבר על תיקיות 0-9
    for digit in range(10):
        folder_path = os.path.join(DATA_PATH, str(digit))
        if not os.path.exists(folder_path):
            continue
            
        files = [f for f in os.listdir(folder_path) if f.lower().endswith('.png')]
        print(f"[PROCESS] Checking digit {digit} ({len(files)} files)...")

        for filename in files:
            file_path = os.path.join(folder_path, filename)
            img = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            
            # ביצוע חיזוי (Prediction)
            prep = process_for_ai(img)
            prediction_idx = np.argmax(model.predict(prep, verbose=0))
            
            is_correct = (prediction_idx == digit)
            total_checked += 1
            
            # חילוץ מונים קיימים משם הקובץ בעזרת Regex
            match = re.search(r'good_(\d+)_bad_(\d+)', filename)
            if match:
                good_count = int(match.group(1))
                bad_count = int(match.group(2))
                base_name = filename[:match.start()].rstrip('_')
            else:
                good_count = 0
                bad_count = 0
                base_name = os.path.splitext(filename)[0]
                
            # עדכון המונים לפי התוצאה
            if is_correct:
                good_count += 1
            else:
                bad_count += 1
                mismatches += 1
                # העתקת התמונה לתיקיית הביקורת לזיהוי ה"רעל"
                review_name = f"folder_{digit}_pred_{prediction_idx}_{filename}"
                shutil.copy2(file_path, os.path.join(BAD_SAMPLES_DIR, review_name))

            # בניית שם הקובץ החדש
            new_filename = f"{base_name}_good_{good_count}_bad_{bad_count}.png"
            new_file_path = os.path.join(folder_path, new_filename)
            
            # שינוי שם הקובץ בפועל
            if file_path != new_file_path:
                try:
                    os.rename(file_path, new_file_path)
                except OSError:
                    pass

    print("-" * 40)
    print(f"[SUCCESS] Diagnosis finished.")
    print(f"Total checked: {total_checked}")
    print(f"Mismatches found: {mismatches}")
    print(f"Problematic samples copied to: {BAD_SAMPLES_DIR}")

if __name__ == "__main__":
    run_diagnosis()