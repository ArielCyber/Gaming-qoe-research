'''
שם הקובץ: template_cleaner_V2_gm.py
---------------------------------
הסבר על הפונקציה:
הסקריפט מבצע סינון איכות לטמפלייטים הקיימים בתיקיית digits_font/0_9.

מה הקוד עושה:
1. במקום למחוק קבצים, הוא מעביר אותם לתיקיית "הסגר" בשם digits_font/dirty_templates.
2. הקוד שומר על מבנה התיקיות (0-9) גם בתוך תיקיית ההסגר כדי שתוכל לבחון אותם בקלות.
3. הסינון מתבצע לפי כמות פיקסלים לבנים (מינימום 40) וגובה מינימלי (מינימום 12).

איך משתמשים:
1. הרץ בטרמינל: python3 template_cleaner_V2_gm.py
2. אם הקוד זיהה טמפלייטים גרועים, הוא ייצור את התיקייה digits_font/dirty_templates ויעביר אותם לשם.
3. תוכל להיכנס לתיקייה, לראות מה הועבר, ואם תרצה להחזיר משהו - פשוט גרור אותו חזרה לתיקיית המקור.

מה צריך לעשות:
מומלץ להריץ את הסקריפט לאחר כל סבב של ייצור טמפלייטים חדשים כדי למנוע מ"רעש" לפגוע בדיוק של V12_gm.
'''

import cv2
import os
import shutil
from pathlib import Path

# הגדרות נתיבים
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "digits_font" / "0_9"
DIRTY_DIR = BASE_DIR / "digits_font" / "dirty_templates"

# פרמטרים לסינון
MIN_PIXELS = 40 
MIN_HEIGHT = 12

def clean_and_move():
    if not TEMPLATES_DIR.exists():
        print(f"Error: {TEMPLATES_DIR} not found.")
        return

    moved_count = 0
    print(f"Scanning templates in: {TEMPLATES_DIR}")

    for i in range(10):
        digit_folder = TEMPLATES_DIR / str(i)
        if not digit_folder.exists():
            continue
        
        # יצירת תיקיית הסגר תואמת עבור כל ספרה
        quarantine_path = DIRTY_DIR / str(i)
        
        for img_p in digit_folder.glob("*.png"):
            img = cv2.imread(str(img_p), cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            
            h, w = img.shape
            white_pixels = cv2.countNonZero(img)
            
            # תנאים להעברה להסגר
            if white_pixels < MIN_PIXELS or h < MIN_HEIGHT:
                # יצירת תיקיית ההסגר רק אם נמצא קובץ בעייתי
                quarantine_path.mkdir(parents=True, exist_ok=True)
                
                # העברת הקובץ
                destination = quarantine_path / img_p.name
                shutil.move(str(img_p), str(destination))
                moved_count += 1
                
    if moved_count > 0:
        print(f"Done! Moved {moved_count} suspicious templates to: {DIRTY_DIR}")
    else:
        print("Everything looks good. No templates were moved.")

if __name__ == "__main__":
    clean_and_move()
