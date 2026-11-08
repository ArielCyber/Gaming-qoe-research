'''
שם הקובץ: template_deduplicator_V1_gm.py
---------------------------------
הסבר על הפונקציה:
הסקריפט סורק את מאגר הטמפלייטים ומזהה קבצים כפולים או זהים לחלוטין בתוך אותה תיקיית ספרה.

מה הקוד עושה:
1. עובר על תיקיות הספרות (0-9) בתוך digits_font/0_9.
2. משווה כל זוג תמונות בתוך כל תיקייה באמצעות חישוב ההפרש המוחלט (Absolute Difference) ביניהן.
3. אם שתי תמונות זהות ב-100% (או כמעט לחלוטין), הקוד משאיר אחת ומעביר את השנייה לתיקיית ההסגר (dirty_templates).
4. פעולה זו שומרת על מאגר טמפלייטים רזה, מה שגורם ל-V12 לעבוד הרבה יותר מהר.

איך משתמשים:
1. וודא שתיקיית digits_font קיימת.
2. הרץ בטרמינל: python3 template_deduplicator_V1_gm.py

דוגמת הרצה:
michael@michael-VirtualBox:~/Documents/ping_extractor$ python3 template_deduplicator_V1_gm.py
'''

import cv2
import numpy as np
import os
import shutil
from pathlib import Path

# הגדרות נתיבים - בהתאם למבנה הפרויקט שלך באובונטו
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "digits_font" / "0_9"
DIRTY_DIR = BASE_DIR / "digits_font" / "dirty_templates"

# סף דמיון (0 אומר זהות מוחלטת)
SIMILARITY_THRESHOLD = 0 

def deduplicate():
    if not TEMPLATES_DIR.exists():
        print(f"Error: {TEMPLATES_DIR} not found.")
        return

    moved_count = 0
    print(f"Starting deduplication in: {TEMPLATES_DIR}")

    for i in range(10):
        digit_folder = TEMPLATES_DIR / str(i)
        if not digit_folder.exists():
            continue
        
        # טעינת כל התמונות בתיקייה
        files = sorted(list(digit_folder.glob("*.png")))
        if len(files) < 2:
            continue

        # רשימת קבצים שכבר סומנו ככפולים כדי לא לעבד אותם שוב
        duplicates = set()

        for idx, file_a in enumerate(files):
            if file_a in duplicates:
                continue

            img_a = cv2.imread(str(file_a), cv2.IMREAD_GRAYSCALE)
            if img_a is None: continue

            for file_b in files[idx + 1:]:
                if file_b in duplicates:
                    continue

                img_b = cv2.imread(str(file_b), cv2.IMREAD_GRAYSCALE)
                if img_b is None: continue

                # השוואת מימדים
                if img_a.shape != img_b.shape:
                    continue

                # חישוב הפרש בין התמונות
                diff = cv2.absdiff(img_a, img_b)
                non_zero_count = cv2.countNonZero(diff)

                # אם התמונות זהות
                if non_zero_count <= SIMILARITY_THRESHOLD:
                    duplicates.add(file_b)

        # העברת הכפולים להסגר
        for dup_path in duplicates:
            quarantine_path = DIRTY_DIR / str(i)
            quarantine_path.mkdir(parents=True, exist_ok=True)
            
            try:
                shutil.move(str(dup_path), str(quarantine_path / dup_path.name))
                moved_count += 1
            except Exception as e:
                print(f"Error moving {dup_path.name}: {e}")

    print(f"\nDeduplication finished. Moved {moved_count} duplicate templates to quarantine.")

if __name__ == "__main__":
    deduplicate()
