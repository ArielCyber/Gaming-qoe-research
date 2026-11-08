"""
שם הקובץ: Error_Image_Collector_V1_gm.py
רקע: קובץ זה משמש לריכוז תמונות שבהן חלו טעויות זיהוי (Wrong) או חוסר זיהוי (None) לתיקיית למידה אחת.
המטרה היא לאפשר אימון חוזר של המודל על המקרים הבעייתיים מבלי לפגוע במבנה התיקיות המקורי של המחקר.

קלטים (Inputs):
  - SOURCE_PATH: תיקיית המקור המכילה את 100 ההקלטות (FF_Mich_Ping+200...).
  - TARGET_BASE_PATH: תיקיית היעד ללמידה (eror_detected_image\\from_P+200).

פלטים (Outputs):
  - העתקה (Copy) של קבצי _N_ לתיקיית None_from_P+200 (בתוך תת-תיקיות N_from_run...).
  - העתקה (Copy) של קבצי _W_ לתיקיית Wrong_from_P+200 (בתוך תת-תיקיות W_from_run...).

דוגמת הרצה:
cd C:\project_ping\ping_extractor\First_Action
python Error_Image_Collector_V1_gm.py
"""

import os
import shutil
from pathlib import Path

# --- הגדרות נתיבים (Michael's Rule: Double backslashes) ---
SOURCE_PATH = "C:\\project_ping\\adb\\sessions_screencap_pc_roi\\FF_Mich_Ping+300_(150+150)"
TARGET_BASE_PATH = "C:\\project_ping\\ping_extractor\\eror_detected_image\\from_P+300"

def rev(text):
    """הופך טקסט כדי שיוצג תקין בטרמינל ללא כפל הפיכות"""
    return text #[::-1]

def collect_error_images():
    src_root = Path(SOURCE_PATH)
    target_root = Path(TARGET_BASE_PATH)

    # בניית תיקיות אב של היעד אם אינן קיימות
    none_root = target_root / "None_from_P+200"
    wrong_root = target_root / "Wrong_from_P+200"
    
    for p in [none_root, wrong_root]:
        p.mkdir(parents=True, exist_ok=True)

    if not src_root.exists():
        print(f"[ERROR] Source not found: {SOURCE_PATH}")
        return

    print(f"[START] {rev('...הדימל תיקייל תונומת קתעהל לחימ')}")
    
    copied_count_n = 0
    copied_count_w = 0

    # 1. מעבר על כל תיקיות הריצה (run_...)
    # Michael's Rule: loop ends with colon
    for subdir in src_root.iterdir():
        if subdir.is_dir():
            run_name = subdir.name
            
            # 2. מעבר על כל התמונות בתיקייה
            for img_file in subdir.glob("*"):
                if img_file.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                    filename = img_file.name
                    
                    target_sub_folder = None
                    prefix = ""
                    
                    # בדיקה אם מדובר ב-None (N) או Wrong (W)
                    if "_N_" in filename:
                        target_sub_folder = none_root / f"N_from_{run_name}"
                        copied_count_n += 1
                    elif "_W_" in filename:
                        target_sub_folder = wrong_root / f"W_from_{run_name}"
                        copied_count_w += 1
                    
                    # 3. ביצוע ההעתקה
                    if target_sub_folder:
                        target_sub_folder.mkdir(parents=True, exist_ok=True)
                        dest_path = target_sub_folder / filename
                        
                        # העתקה בלבד (לא העברה!)
                        shutil.copy2(str(img_file), str(dest_path))

    # 4. סיכום ביצוע
    print("\n" + "=" * 40)
    print(f" {rev('--- !המישמה המלשוה ---')} ")
    print(f" {copied_count_n} : {rev('None_from_P+200-ל וקתעהש תונומת')}")
    print(f" {copied_count_w} : {rev('Wrong_from_P+200-ל וקתעהש תונומת')}")
    print(f" {copied_count_n + copied_count_w} : {rev('כ\"הס')}")
    print("=" * 40)

if __name__ == "__main__":
    collect_error_images()