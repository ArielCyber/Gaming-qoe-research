# template_builder_V6_gm.py
import os
import cv2
import re
import numpy as np

# הגדרות - משתמשים בכל 2640 התמונות כדי לבנות דאטה-סט חזק
INPUT_DIR = 'all_new_pic'
OUTPUT_DIR = 'training_data_clean'

def init_folders():
    """יוצר את תיקיית הפלט ותתי-תיקיות לספרות 0-9"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    for i in range(10):
        os.makedirs(os.path.join(OUTPUT_DIR, str(i)), exist_ok=True)

def process_and_clean(img, size=(40, 64)):
    """ממלא את הספרה (למניעת חלל פנימי) וממרכז אותה במלבן קבוע"""
    # סגירת חורים ועיבוי הספרה (Morphological operations)
    kernel = np.ones((3, 3), np.uint8)
    img_closed = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)
    img_dilated = cv2.dilate(img_closed, kernel, iterations=1)
    
    # שינוי גודל תוך שמירה על יחס (Aspect Ratio)
    h, w = img_dilated.shape
    scale = min(size[1] / h, size[0] / w) * 0.8
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    resized = cv2.resize(img_dilated, (nw, nh))
    
    # יצירת קנבס שחור ומיקום הספרה במרכז
    canvas = np.zeros((size[1], size[0]), dtype=np.uint8)
    y_off = (size[1] - nh) // 2
    x_off = (size[0] - nw) // 2
    canvas[y_off:y_off+nh, x_off:x_off+nw] = resized
    return canvas

def build():
    """הפונקציה המרכזית לבניית הטמפלייטים"""
    init_folders()
    if not os.path.exists(INPUT_DIR):
        print(f"[ERROR] Directory {INPUT_DIR} not found!")
        return

    files = [f for f in os.listdir(INPUT_DIR) if "_Ping_" in f]
    print(f"[INFO] Analyzing {len(files)} images to find clean digits...")

    saved_count = 0
    for filename in files:
        # חילוץ המספר משם הקובץ בעזרת Regex
        match = re.search(r'_Ping_(\d+)', filename)
        if not match:
            continue
        
        expected_ping = match.group(1)
        img_path = os.path.join(INPUT_DIR, filename)
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        
        if img is None:
            continue

        # ROI מתוקן: מתחיל מ-0 (ראש המסך) כדי לא לקטום ספרות
        roi = img[0:130, 0:350]
        _, thresh = cv2.threshold(roi, 195, 255, cv2.THRESH_BINARY)
        
        # מציאת קונטורים של ספרות
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # סינון לפי גובה ורוחב של ספרה הגיונית ב-Free Fire
        valid_contours = []
        for ctr in contours:
            x, y, w, h = cv2.boundingRect(ctr)
            if 15 < h < 80 and 4 < w < 60:
                valid_contours.append(ctr)
        
        # מיון משמאל לימין
        valid_contours = sorted(valid_contours, key=lambda c: cv2.boundingRect(c)[0])
        
        # שמירה רק אם מספר הצורות שמצאנו זהה למספר הפינג בשם הקובץ
        if len(valid_contours) == len(expected_ping):
            for i, ctr in enumerate(valid_contours):
                x, y, w, h = cv2.boundingRect(ctr)
                digit_raw = thresh[y:y+h, x:x+w]
                digit_final = process_and_clean(digit_raw)
                
                label = expected_ping[i]
                save_name = f"v6_{saved_count}_{label}.png"
                cv2.imwrite(os.path.join(OUTPUT_DIR, label, save_name), digit_final)
                saved_count += 1
                
    print(f"[SUCCESS] Built {saved_count} clean templates in '{OUTPUT_DIR}'")

if __name__ == "__main__":
    build()