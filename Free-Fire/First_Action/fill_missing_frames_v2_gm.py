'''
# fill_missing_frames_v2_gm.py
#
# --- דוגמת הרצה (CMD) ---
# 1. מעבר לתיקייה: 
cd /d C:\project_ping\ping_extractor\First_Action
# 2. הפעלת הסביבה: 
..\venv_win\Scripts\activate
# 3. הרצת הקוד: 
python fill_missing_frames_v2_gm.py "C:\project_ping\adb\sessions_screencap_pc_roi"
הרצת הקוד בלי פרמטרים:
python fill_missing_frames_v2_gm.py
# ------------------------
'''
import os
import cv2
import numpy as np
import re
import sys
from pathlib import Path
from datetime import datetime, timedelta

# --- הגדרות Michael's Rule ---
# קבלת נתיב הסריקה מה-CMD או שימוש בנתיב ברירת מחדל
SOURCE_PATH = sys.argv[1] if len(sys.argv) > 1 else r"C:\project_ping\adb\sessions_screencap_pc_roi\FF_Mich_Ping+0_lbld"
IMAGE_EXTS = {".png", ".jpg", ".jpeg"}

def parse_filename(filename):
    """ חילוץ אינדקס, תאריך, זמן ובדיקה אם קיים פורמט פינג בשם הקובץ """
    # שימוש בביטוי רגולרי לאיתור המבנה: Index_Date_Time_...
    pattern = r"^(\d{6})_(\d{8})_(\d{6})(.*)\.(?:png|jpg|jpeg)$"
    match = re.search(pattern, filename, re.IGNORECASE)
    if match:
        return {
            "index": int(match.group(1)),
            "date_str": match.group(2),
            "time_str": match.group(3),
            "has_ping": "Ping" in match.group(4),
            "suffix": Path(filename).suffix
        }
    return None

def create_white_image(path, height, width):
    """ ייצור תמונה לבנה נקייה במידות המבוקשות ושמירתה """
    # יצירת מערך שכולו 255 (לבן) בפורמט BGR
    white_img = np.full((height, width, 3), 255, dtype=np.uint8)
    cv2.imwrite(str(path), white_img)

def process_folder(folder_path):
    """ סורק תיקייה ומזהה פערים. מחזיר רשימה של שמות הקבצים שנוספו """
    # סינון ומיון הקבצים הקיימים לפי המספר הסידורי
    files = sorted([f for f in folder_path.iterdir() if f.suffix.lower() in IMAGE_EXTS])
    
    if len(files) < 2:
        return []

    added_files = []

    # מעבר על צמדי קבצים סמוכים לאיתור "חור" באינדקסים
    for i in range(len(files) - 1):
        curr_f, next_f = files[i], files[i+1]
        curr_p, next_p = parse_filename(curr_f.name), parse_filename(next_f.name)
        
        if not curr_p or not next_p:
            continue

        # חישוב גודל הפער
        gap = next_p["index"] - curr_p["index"]
        
        if gap > 1:
            # דגימת מידות מהתמונה האחרונה שקדמה לפער
            img_sample = cv2.imread(str(curr_f))
            if img_sample is None: continue
            height, width = img_sample.shape[:2]

            # המרת חותמות הזמן לאובייקטים לחישוב מתמטי
            curr_dt = datetime.strptime(f"{curr_p['date_str']}{curr_p['time_str']}", "%Y%m%d%H%M%S")
            next_dt = datetime.strptime(f"{next_p['date_str']}{next_p['time_str']}", "%Y%m%d%H%M%S")

            # מילוי הפער בפריימים לבנים
            for j in range(1, gap):
                missing_index = curr_p["index"] + j
                # קידום הזמן ב-1 שנייה, תוך חסימה (Clamping) שלא יעבור את זמן התמונה הבאה
                new_dt = min(curr_dt + timedelta(seconds=j), next_dt)
                
                new_date_str = new_dt.strftime("%Y%m%d")
                new_time_str = new_dt.strftime("%H%M%S")
                index_str = str(missing_index).zfill(6)
                
                # החלטה על פורמט השם לפי הקובץ העוקב
                if next_p["has_ping"]:
                    new_name = f"{index_str}_{new_date_str}_{new_time_str}_Ping_None{curr_p['suffix']}"
                else:
                    new_name = f"{index_str}_{new_date_str}_{new_time_str}{curr_p['suffix']}"
                
                new_path = folder_path / new_name
                # יצירה פיזית של הקובץ אם הוא לא קיים
                if not new_path.exists():
                    create_white_image(new_path, height, width)
                    added_files.append(new_name)

    return added_files

def main():
    root = Path(SOURCE_PATH)
    if not root.exists():
        print(f"[ERROR] Path not found: {SOURCE_PATH}")
        return

    print(f"\n[START] Searching for gaps in: {SOURCE_PATH}")
    
    # מילון לאגירת הדיווחים: {שם_תיקייה: [רשימת_קבצים_חדשים]}
    report_data = {}
    total_added = 0
    
    # סריקה רקורסיבית לאיתור כל תיקייה המכילה תמונות
    processed_dirs = set()
    for img_file in root.rglob("*"):
        if img_file.suffix.lower() in IMAGE_EXTS:
            parent = img_file.parent
            if parent not in processed_dirs:
                new_files = process_folder(parent)
                if new_files:
                    report_data[str(parent)] = new_files
                    total_added += len(new_files)
                processed_dirs.add(parent)

    # --- הפקת הדיווח המשולש בסיום הריצה ---
    print("\n" + "="*60)
    print("FINAL EXECUTION REPORT - FRAME FILLER V2")
    print("="*60)

    # דיווח 1: סה"כ תמונות שנוספו
    print(f"1. TOTAL IMAGES ADDED IN ALL FOLDERS: {total_added}")

    if total_added == 0:
        print("\nNo gaps were detected. All sequences are complete.")
    else:
        # דיווח 2: ריכוז הוספות לפי תיקייה
        print("\n2. SUMMARY BY FOLDER:")
        for folder, files in report_data.items():
            print(f"   - {os.path.basename(folder)}: {len(files)} images added")

        # דיווח 3: פירוט מלא של שמות הקבצים החדשים
        print("\n3. DETAILED FILE LIST:")
        for folder, files in report_data.items():
            print(f"\nFolder: {os.path.basename(folder)} ({len(files)} images)")
            for f_name in files:
                print(f"   [+] {f_name}")

    print("\n" + "="*60)
    print("ALL SELECTED TASKS COMPLETED.")
    print("="*60)
    print("="*60)
    print(f"1. TOTAL IMAGES ADDED IN ALL FOLDERS: {total_added}")
    print("="*60)
if __name__ == "__main__":
    main()

   
'''
רקע לקוד והסבר פעולה
למה הקוד הזה נוצר? הקוד נוצר בעקבות דרישה של המנחה לשמור על רציפות מלאה של פריים-אחרי-פריים בנתונים המחקריים. 
במהלך העבודה המוקדמת, תמונות שלא פוענחו כראוי נמחקו, מה שיצר "חורים" ברצף האינדקסים. 
הקוד הזה משחזר את הרצף הויזואלי מבלי להמציא נתונים (על ידי שימוש ברקע לבן).

מה הקוד עושה בפועל?


סריקה חכמה: הוא מחפש תיקיות המכילות תמונות בכל עומק של התיקייה שסיפקת.

זיהוי פערים: הוא משווה את המספר הסידורי (ה-Index) של כל תמונה לזו שאחריה. אם חסר מספר, הוא יודע בדיוק כמה תמונות חסרות שם.

התאמת פורמט: הקוד "מסתכל קדימה" – אם התמונה הבאה כבר עברה עיבוד פינג (מכילה Ping בשם), הוא יוצר שם קובץ עם Ping_None. 
אם היא תמונה גולמית, הוא יוצר שם פשוט ללא תגיות פינג.

סינכרון זמן (Time Clamping): הקוד מקדם את השעון בשנייה אחת לכל תמונה חסרה כדי לשמור על היגיון כרונולוגי, 
אך הוא עוצר ב"קיר" של זמן התמונה הבאה כדי למנוע מצב שזמן תמונה חסרה יהיה מאוחר יותר מזמן התמונה המקורית שאחריה.

דיוק ויזואלי: התמונות הלבנות נוצרות בדיוק באותן רזולוציות (Width/Height) של התמונה שקדמה להן בתיקייה.

דיווח: בסיום, המשתמש מקבל פירוט מלא של כל הקבצים שנוצרו לצורך בקרה.

'''