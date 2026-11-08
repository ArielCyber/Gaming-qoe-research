# prefix_remover_V1_gm.py
import os
from pathlib import Path

# --- הגדרות ---
# Michael's Rule: Quotes and double backslashes for Windows path
SOURCE_PATH = "C:\\project_ping\\adb\\sessions_screencap_pc_roi\\FF_Mich_Ping+300_(150+150)_lbld"

def remove_v_prefix():
    root = Path(SOURCE_PATH)
    
    if not root.exists():
        print(f"[ERROR] Path not found: {SOURCE_PATH}")
        return

    print(f"[INFO] Scanning folders in: {SOURCE_PATH}")
    
    renamed_count = 0
    skipped_count = 0

    # מעבר על כל הפריטים בתיקיית האב
    # Michael's Rule: for loop ends with colon
    for folder in root.iterdir():
        # בדיקה אם מדובר בתיקייה ואם היא מתחילה ב-V_
        if folder.is_dir() and folder.name.startswith("V_"):
            # יצירת השם החדש (הסרת ה-2 תווים הראשונים: 'V_')
            new_name = folder.name[2:]
            new_path = folder.with_name(new_name)
            
            try:
                os.rename(folder, new_path)
                print(f"[RENAME] {folder.name} -> {new_name}")
                renamed_count += 1
            except Exception as e:
                print(f"[ERROR] Could not rename {folder.name}: {e}")
        else:
            skipped_count += 1

    print("\n" + "=" * 40)
    print(f"[SUCCESS] Process finished.")
    print(f"Folders renamed: {renamed_count}")
    print(f"Items skipped (no V_ prefix): {skipped_count}")
    print("=" * 40)

if __name__ == "__main__":
    remove_v_prefix()
'''
# דוגמת הרצה:
# 1. וודא שסגרת את כל התיקיות שפתוחות בסייר הקבצים (כדי למנוע שגיאת 'Permission Denied').
# 2. הרץ בטרמינל: 
cd C:\project_ping\ping_extractor\First_Action
python prefix_remover_V1_gm.py
'''