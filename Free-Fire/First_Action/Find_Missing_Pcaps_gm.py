r'''
תיאור: סריקה מהירה של תיקיות המשחק לאיתור תיקיות בהן חסר קובץ הקלטת רשת (pcapng).
סיבה ורקע: בעקבות שגיאות שהופיעו בזמן חילוץ הפיצ'רים, עלינו לבצע 'ניקוי נתונים' (Data Cleaning). 
          תיקייה ללא קובץ רשת אינה מאפשרת הצלבה עם הפינג הויזואלי, ולכן יש לאתרן 
          כדי להחליט אם להקליט אותן מחדש או להוציא אותן מהמחקר הסופי.
שימוש:
cd C:\project_ping\ping_extractor\First_Action
..\venv_win\Scripts\activate
python Find_Missing_Pcaps_gm.py
תלויות: pathlib
גרסה: V1.0
'''

import os
from pathlib import Path

# --- הגדרות נתיבים (Michael's Rule: Double backslashes) ---
SOURCE_PATH = "C:\\project_ping\\adb\\sessions_screencap_pc_roi\\P+0+100"

def find_missing_files():
    # Michael's Rule: logical blocks end with colon
    root = Path(SOURCE_PATH)
    if not root.exists():
        print(f"[ERROR] Path not found: {SOURCE_PATH}")
        return

    missing_folders = []
    total_folders = 0

    print(f"[START] Scanning for missing pcapng files in: {SOURCE_PATH}\n")

    for folder in root.iterdir():
        if not folder.is_dir():
            continue
        
        total_folders += 1
        # חיפוש קבצים עם סיומת pcapng בתוך התיקייה
        pcap_files = list(folder.glob("*.pcapng"))
        
        if not pcap_files:
            missing_folders.append(folder.name)
            print(f"[MISSING] {folder.name}")

    # הצגת סיכום למשתמש
    print("\n" + "=" * 50)
    print("FINAL REPORT:")
    print(f"Total folders scanned: {total_folders}")
    print(f"Folders missing pcapng: {len(missing_folders)}")
    print("=" * 50)

    if missing_folders:
        print("\nList of folders to check:")
        for name in missing_folders:
            print(f"- {name}")
    else:
        print("\n[SUCCESS] No missing pcapng files found!")

if __name__ == "__main__":
    find_missing_files()