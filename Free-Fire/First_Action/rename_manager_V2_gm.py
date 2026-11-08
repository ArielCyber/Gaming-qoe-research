# rename_manager_V2_gm.py
r'''
תיאור: מנהל אוטומציה המריץ את ה-Extractor וה-Renamer על מספר תיקיות, תוך מעקב אחר זמני ביצוע וסטטיסטיקות.
סיבה ורקע: הקוד נכתב כדי לייעל את תהליך המחקר ולחסוך עבודה ידנית על עשרות תיקיות 'Session' שנוצרו. 
          הצורך עלה מהרצון לעבד כמויות גדולות של נתונים (מעל 10,000 תמונות) באופן אחיד, 
          תוך מעקב מדויק אחר קצב הביצועים של מודל ה-V33 (בעל ה-97.5% דיוק) בכל סשן בנפרד.
שימוש:

python rename_manager_V2_gm.py
תלויות: os, subprocess, sys, pathlib, datetime
גרסה: V2
'''

# ייבוא ספרייה לביצוע פעולות בסיסיות במערכת ההפעלה (כמו מחיקת קבצים ושינוי שמות)
import os
# ייבוא ספרייה להרצת תוכנות וסקריפטים חיצוניים מתוך הקוד
import subprocess
# ייבוא ספרייה לגישה למערכת (למשל כדי לדעת איזה פייתון מריץ אותנו)
import sys
# ייבוא כלי לניהול נתיבים בצורה חכמה ומודרנית
from pathlib import Path
# ייבוא כלי למדידת זמנים ותאריכים (עבור סטטיסטיקות הרצה)
from datetime import datetime

# --- הגדרות ---
# Michael's Rule: Use raw strings (r"") for Windows paths
# הגדרת נתיב המקור המכיל את כל התיקיות שצריך לעבד
SOURCE_PATH = r"C:\Users\<user>\Desktop\adb3\P+600_to_handle"

# הגדרת הסקריפטים בתוך תיקיית העזר
# נתיב לסקריפט המפענח (האקסטרקטור) שנמצא בתוך תיקיית עזר
EXTRACTOR_SCRIPT = r"file_to_use\ping_extractor_V33_SuperHybrid_gm.py"
# נתיב לסקריפט שמשנה שמות קבצים (הריניימר)
RENAMER_SCRIPT = r"file_to_use\ping_renamer_V1_gm.py"


# הגדרת הפונקציה הראשית שמנהלת את הזרמת העבודה
def run_manager():
    # הדפסת הודעת פתיחה לבקרה
    print("[DEBUG] Manager V2 started...")

    # יצירת אובייקט נתיב עבור תיקיית המקור
    base_path = Path(SOURCE_PATH)
    # בדיקה האם התיקייה שצוינה בהגדרות בכלל קיימת במחשב
    if not base_path.exists():
        # הדפסת שגיאה במקרה שהנתיב לא תקין ויציאה מהפונקציה
        print(f"[ERROR] Source path not found: {SOURCE_PATH}")
        return

    # 1. איתור תיקיות שלא מתחילות ב-V
    # קריאת רשימת כל הפריטים הנמצאים בתוך תיקיית המקור
    all_items = os.listdir(SOURCE_PATH)
    # יצירת רשימה של תיקיות בלבד (לא קבצים) ששמן אינו מתחיל באות V (כלומר, טרם עובדו)
    unmarked_folders = [item for item in all_items
                        if (base_path / item).is_dir() and not item.lower().startswith("v")]

    # אם לא נמצאו תיקיות חדשות לעיבוד
    if not unmarked_folders:
        # הדפסת הודעה שכל התיקיות כבר מסומנות ככאלו שהסתיימו
        print("[INFO] All folders are already marked with V.")
        return

    # הדפסת כמות התיקיות החדשות שזוהו במערכת
    print(f"[INFO] Found {len(unmarked_folders)} unmarked folders.")

    # ניסיון לקבל מהמשתמש את כמות התיקיות שהוא רוצה להריץ כעת
    try:
        # בקשת קלט מהמשתמש
        x_str = input("How many folders would you like to process? ")
        # חישוב הכמות: המינימום בין מה שהמשתמש ביקש לבין מה שקיים בפועל
        num_to_process = min(int(x_str), len(unmarked_folders))
    # טיפול במקרה שהמשתמש לא הזין מספר תקין
    except ValueError:
        # הדפסת שגיאה וסיום הריצה
        print("[ERROR] Invalid number entered.")
        return

    # בחירת רשימת התיקיות לעבודה לפי המספר שנבחר
    selected_folders = unmarked_folders[:num_to_process]
    # שמירת הנתיב למנוע הפייתון הנוכחי (כדי להשתמש בו להרצת הסקריפטים האחרים)
    python_exe = sys.executable

    # לולאה שעוברת על כל תיקייה שנבחרה ומבצעת עליה את התהליך המלא
    for folder_name in selected_folders:
        # בניית הנתיב המלא לתיקייה הנוכחית בלולאה
        folder_path = str(base_path / folder_name)
        # שמירת זמן ההתחלה של עיבוד התיקייה
        start_time = datetime.now()
        # ספירת כמות תמונות ה-PNG בתוך התיקייה לצורך חישוב ממוצעים
        image_count = len(list(Path(folder_path).glob("*.png")))

        # נתיב תיקיית האקסטרקטור - שם ייווצר קובץ ה-CSV
        extractor_dir = Path(EXTRACTOR_SCRIPT).resolve().parent
        

        # הדפסת כותרת מעוצבת לתחילת עבודה על תיקייה ספציפית
        print(f"\n" + "=" * 40)
        print(f"[START] Folder: {folder_name} ({image_count} images)")

        # שלב א: הרצת אקסטרקטור
        print(f"[1/3] Extracting pings...")
        # רישום קבצי CSV שקיימים לפני הריצה
        csvs_before = set(extractor_dir.glob("ping_results_v33_*.csv"))
        # הרצת האקסטרקטור - הפלט שלו מגיע לטרמינל כרגיל
        ext_res = subprocess.run(
            [python_exe, Path(EXTRACTOR_SCRIPT).name, folder_path],
            cwd=str(extractor_dir)
        )
        # זיהוי קובץ ה-CSV החדש שנוצר
        csvs_after = set(extractor_dir.glob("ping_results_v33_*.csv"))
        new_csvs = csvs_after - csvs_before

        success = False
        if ext_res.returncode == 0 and new_csvs:
            # זיהוי הנתיב המדויק של הקובץ החדש
            csv_output_path = list(new_csvs)[0]
            print(f"[INFO] Detected output file: {csv_output_path.name}")
            # שלב ב: הרצת ריניימר
            print(f"[2/3] Renaming files...")
            ren_res = subprocess.run(
                [python_exe, Path(RENAMER_SCRIPT).name, folder_path, str(csv_output_path)],
                cwd=str(Path(RENAMER_SCRIPT).parent)
            )
            if ren_res.returncode == 0:
                success = True
        else:
            print(f"[FAIL] Extractor failed or created no CSV file.")
        # שלב ג: סימון התיקייה ב-V
        # רק אם שני הסקריפטים הקודמים עבדו ללא שגיאות
        if success:
            # הדפסת סטטוס סיום
            print(f"[3/3] Marking folder as completed...")
            # הגדרת השם החדש לתיקייה עם תוספת ה-V בהתחלה
            new_name = f"V_{folder_name}"
            try:
                # ביצוע שינוי שם התיקייה בפועל על הדיסק
                os.rename(base_path / folder_name, base_path / new_name)
                # הדפסת אישור הצלחה סופי
                print(f"[SUCCESS] Process completed for {new_name}")
            # טיפול במקרה של תקלה טכנית בשינוי שם התיקייה
            except Exception as e:
                # הדפסת השגיאה שקרתה בשינוי השם
                print(f"[ERROR] Final rename failed: {e}")
        # במקרה של כשל באחד השלבים
        else:
            # הודעה שהתהליך נכשל עבור התיקייה הנוכחית בלולאה
            print(f"[FAIL] Process failed for {folder_name}. Check logs.")
 
        # חישוב הזמן הכולל שלקח לעבד את התיקייה הנוכחית
        duration = datetime.now() - start_time
        # חישוב זמן ממוצע לתמונה אחת
        avg_time = duration.total_seconds() / image_count if image_count > 0 else 0
        # הדפסת סיכום סטטיסטי להרצה הנוכחית
        print(f"[STATS] Time: {str(duration).split('.')[0]} | Avg: {avg_time:.2f}s/img")
        # הדפסת קו מפריד לסיום הבלוק של התיקייה
        print("=" * 40)

    # הדפסת הודעת סיום חגיגית לאחר שכל המשימות שנבחרו הסתיימו
    print("\n" + "#" * 50 + "\nALL SELECTED TASKS COMPLETED.\n" + "#" * 50)


# נקודת הכניסה לסקריפט - אם מריצים את הקובץ ישירות
if __name__ == "__main__":
    # הפעלת פונקציית המנהל
    run_manager()
    
# דוגמת הרצה:
# 1. וודא שאתה בתוך (venv_win) בטרמינל.
# venv_win\Scripts\activate
# 2. וודא ששמות 4 התיקיות מהניסוי הקודם שונו חזרה (בלי ה-V).
# 3. הרץ:
# cd C:\project_ping\ping_extractor\First_Action
# ..\venv_win\Scripts\activate
# python rename_manager_V2_gm.py    
