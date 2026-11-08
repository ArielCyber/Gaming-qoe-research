# quality_check_V3_gm.py

'''
cd C:\project_ping\ping_extractor\First_Action
..\venv_win\Scripts\activate
python quality_check_V3_gm.py
'''

import os
from pathlib import Path

# --- הגדרות ---
# Michael's Rule: Quotes around paths and double backslash for Windows
SOURCE_PATH = "C:\\project_ping\\adb\\sessions_screencap_pc_roi\\FF_Mich_Ping+400_(200+200)"

def analyze_failures():
    global_total_images = 0  # מונה לכל התמונות בכל התיקיות
    root_path = Path(SOURCE_PATH)
    if not root_path.exists():
        print(f"[ERROR] Path not found: {SOURCE_PATH}")
        return

    fail_keywords = ["none", "fail", "not_found", "not_detected"]
    image_extensions = [".png", ".jpg", ".jpeg"]
    folder_stats = []

    # 1. איסוף נתונים (קטגוריה א' וקטגוריה ב')
    for subdir in root_path.iterdir():
        if subdir.is_dir():
            # ספירה גלובלית לצורך הדו"ח הראשי
            current_folder_images = [f for f in subdir.glob("*") if f.suffix.lower() in image_extensions]
            global_total_images += len(current_folder_images)
            
            failed_ids = []     # קטגוריה א': ה-Extractor נכשל (None/Fail)
            unprocessed = []    # קטגוריה ב': ה-Renamer לא עבד (אין ping בשם)
            
            for file in current_folder_images:
                filename_lower = file.name.lower()
                
                # בדיקת קטגוריה א' (זיהוי שגוי)
                if any(kw in filename_lower for kw in fail_keywords):
                    failed_ids.append(file.name)
                # בדיקת קטגוריה ב' (לא עבר עיבוד)
                elif "ping" not in filename_lower:
                    unprocessed.append(file.name)
            
            # שומרים נתונים רק אם יש כשלון כלשהו
            if failed_ids or unprocessed:
                folder_stats.append({
                    "name": subdir.name,
                    "fail_count": len(failed_ids),
                    "unprocessed_count": len(unprocessed),
                    "total_count": len(current_folder_images),
                    "failed_list": failed_ids,
                    "unprocessed_list": unprocessed
                })

    if global_total_images == 0:
        print("!תונומת וצאמנ אל")
        return

    # 2. סיכום גלובלי בראש הפלט (טקסט הפוך ידנית)
    total_all_errors = sum(s['fail_count'] + s['unprocessed_count'] for s in folder_stats)
    error_pct = (total_all_errors / global_total_images) * 100 if global_total_images > 0 else 0

    print("\n" + "*" * 40)
    print(" --- תוייקתה לכל יללכ םוכיס --- ")
    print(f" {total_all_errors} :והוז אלש םיצבק כ\"הס")
    print(f" {global_total_images} :תומיקה תונומת כ\"הס ךותמ")
    print(f" {error_pct:.2f}% :יללכ וולשכ זוהא")
    print("*" * 40 + "\n")

    # 3. חלק א' - רשימות מרוכזות (סיכומים)
    
    # סיכום קטגוריה א'
    sorted_failed = sorted([f for f in folder_stats if f["fail_count"] > 0], key=lambda x: x["fail_count"], reverse=True)
    if sorted_failed:
        print("="*10 + " === (תומכ יפל נויממ) יוהיז תונולשכ םע תוייקית === " + "="*10)
        for stat in sorted_failed:
            print(f"{stat['name']} - {stat['fail_count']}/{stat['total_count']}")

    # סיכום קטגוריה ב'
    sorted_unprocessed = sorted([f for f in folder_stats if f["unprocessed_count"] > 0], key=lambda x: x["unprocessed_count"], reverse=True)
    if sorted_unprocessed:
        print("\n" + "="*10 + " === (םשב ping רסח) ודבוע אלש תוייקית === " + "="*10)
        for stat in sorted_unprocessed:
            print(f"{stat['name']} - {stat['unprocessed_count']}/{stat['total_count']}")

    # 4. חלק ב' - פירוט שמות קבצים
    
    # פירוט קטגוריה א' (None/Fail)
    if sorted_failed:
        print("\n" + "!" * 50)
        print(" :והוז אלש םיצבקה תומש טוריפ")
        print("!" * 50)
        for stat in sorted_failed:
            print(f"\n {stat['name']} :הייקית")
            print(f" םיצבק {stat['fail_count']} :תומכ")
            print("-" * 20)
            for fname in stat["failed_list"]:
                print(fname)
            print("\n" + "%" * 40)

    # פירוט קטגוריה ב' (Missing Ping)
    if sorted_unprocessed:
        print("\n" + "?" * 50)
        print(" :(בוש ץירהל) ודבוע אלש םיצבקה תומש טוריפ")
        print("?" * 50)
        for stat in sorted_unprocessed:
            print(f"\n {stat['name']} :הייקית")
            print(f" םיצבק {stat['unprocessed_count']} :תומכ")
            print("-" * 20)
            for fname in stat["unprocessed_list"]:
                print(fname)
            print("\n" + "#" * 40)

if __name__ == "__main__":
    analyze_failures()

r'''
# דוגמת הרצה:
# 1. וודא שהנתיב ב-SOURCE_PATH תקין.
# 2. וודא שאתה בתוך ה-venv.
cd C:\project_ping\ping_extractor
venv_win\Scripts\activate
# 3. הרץ בטרמינל:
cd C:\project_ping\ping_extractor\First_Action
python quality_check_V3_gm.py

'''