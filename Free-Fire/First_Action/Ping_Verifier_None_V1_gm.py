"""
שם הקובץ: Ping_Verifier_None_V1_gm.py
מטרת העל: בקרה ותיקון ידני של קבצים שבהם ה-Extractor נכשל בזיהוי (None/Fail).

מה כולל הקובץ (מבוסס על V1.2):
1. סריקה מקדימה: סופר את כל התמונות ומציג אחוז "נכשלים" לפני תחילת העבודה.
2. ניהול דילוגים: תמיכה מלאה ב-SKIP (S) ודילוג על כל התיקייה (SP).
3. שינוי שם חכם: מחליף את מילת הכשלון (None/Fail) בסימון "N" (למשל: frame_10_ping_N75.png).
4. עדכון רציף: מעדכן גם את קובץ ה-ping_results.csv המקומי בכל תיקייה.
5. Michael's Rule: תיעוד בעברית, לוכסנים כפולים, לוגיקה מסתיימת בנקודתיים ודוגמת הרצה.

קלטים (Inputs):
  - תיקיית הריצות: C:\\project_ping\\adb\\sessions_screencap_pc_roi\\...
פלטים (Outputs):
  - שינוי שמות קבצי תמונה (הוספת N).
  - עדכון ערכי הפינג ב-CSV המקומי.
"""

# ייבוא ספריות לניהול קבצים במערכת ההפעלה
import os
# ייבוא ספריית OpenCV לעיבוד והצגת תמונות
import cv2
# ייבוא ספריית pandas לניהול ועדכון קבצי CSV (טבלאות נתונים)
import pandas as pd
# ייבוא ספריית re לשימוש בביטויים רגולריים (חיפוש והחלפת טקסט)
import re
# ייבוא Path לניהול נתיבים בצורה מודרנית ונוחה
from pathlib import Path

# --- הגדרות (Michael's Rule: Double backslashes) ---
# הגדרת נתיב המקור המכיל את התיקיות שבהן נחפש תמונות עם זיהוי שנכשל
SOURCE_PATH = "C:\\project_ping\\adb\\sessions_screencap_pc_roi\\FF_Mich_Ping+300_(150+150)"
# רשימת מילים המעידות על כך שהסקריפט האוטומטי לא הצליח לזהות את הפינג
FAIL_KEYWORDS = ["none", "fail", "not_found", "not_detected"]
# רשימת סיומות הקבצים שאותם נסרוק כתמונות
IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg"]


# פונקציה להצגת תפריט העזרה למשתמש בזמן הריצה
def show_help():
    # הדפסת קו מפריד מעוצב
    print("\n" + "?" * 30)
    # כותרת התפריט
    print("תפריט עזרה (HELP):")
    # הסבר: הזנת מספר תעדכן את השם עם האות N (לציון תיקון ידני של None)
    print("מספר -> עדכון פינג עם סימון N (למשל '60')")
    # הסבר: לחיצה על אנטר עוברת לתמונה הבאה ללא שינוי
    print("ENTER -> דלג על התמונה הנוכחית")
    # הסבר: האות S מבצעת דילוג (Skip)
    print("S -> דלג על התמונה הנוכחית")
    # הסבר: הפקודה SP מדלגת על כל שאר הקבצים בתיקייה הנוכחית
    print("SP -> דלג על כל התמונות בתיקייה הזו")
    # הסבר: האות E עוצרת את התהליך ושומרת את מה שבוצע עד כה
    print("E -> עצור הכל ושמור דוח")
    # סגירת מסגרת התפריט
    print("?" * 30 + "\n")


# הפונקציה המרכזית שמנהלת את סריקת ה-None ותיקונם
def verify_none_identifications():
    # יצירת אובייקט נתיב לשורש הפרויקט
    root = Path(SOURCE_PATH)
    # בדיקה האם התיקייה קיימת במחשב
    if not root.exists():
        # הדפסת הודעת שגיאה במידה והנתיב שגוי
        print(f"[ERROR] Path not found: {SOURCE_PATH}")
        # יציאה מהפונקציה
        return

    # 1. סריקה מקדימה וסטטיסטיקה
    # יצירת רשימה של כל תיקיות המשנה
    folders = [f for f in root.iterdir() if f.is_dir()]
    # רשימה שתאחסן את כל התמונות הבעייתיות שמצאנו
    none_list = []
    # מונה לסך כל התמונות שקיימות במערכת בנתיב הזה
    total_images_in_system = 0

    # הדפסת הודעת תחילת סריקה
    print("[START] Scanning for non-identified pings...")

    # מעבר על כל תיקייה ברשימה
    for folder in folders:
        # מעבר על כל הקבצים בתוך התיקייה הנוכחית
        for img in folder.glob("*"):
            # בדיקה האם הסיומת של הקובץ נמצאת ברשימת סיומות התמונות
            if img.suffix.lower() in IMAGE_EXTENSIONS:
                # עדכון מונה התמונות הכללי
                total_images_in_system += 1
                # בדיקה האם שם הקובץ מכיל את אחת ממילות הכשל (כמו none או fail)
                if any(kw in img.name.lower() for kw in FAIL_KEYWORDS):
                    # הוספת שם התיקייה ונתיב התמונה לרשימת הטיפול
                    none_list.append((folder.name, img))

    # חישוב כמות התמונות שנכשלו בזיהוי
    total_nones = len(none_list)
    # חישוב אחוז הכשלון מתוך כלל התמונות במערכת
    fail_rate = (total_nones / total_images_count * 100) if (total_images_count := total_images_in_system) > 0 else 0

    # הצגת נתונים סטטיסטיים למשתמש לפני תחילת העבודה הידנית
    print(f"\n[INFO] Found {len(folders)} folders.")
    print(f"[INFO] Total images scanned: {total_images_count}")
    print(f"[INFO] Found {total_nones} non-identified images ({fail_rate:.2f}% of total).")

    # 2. לולאת אימות ותיקון
    # מילון לשמירת תיעוד השינויים שיבוצעו
    changes_report = {}
    # משתנה למעקב אחרי דילוג על תיקייה שלמה
    last_skipped_folder = ""

    # מעבר על רשימת התמונות שדורשות תיקון
    for i, (folder_name, img_path) in enumerate(none_list):
        # Michael's Rule: logic ends with colon
        # בדיקה האם ביקשנו לדלג על התיקייה הזו בסבב הקודם
        if folder_name == last_skipped_folder:
            # דילוג לתמונה הבאה
            continue

        # הדפסת סטטוס התקדמות ושם הקובץ הנוכחי
        print(f"\n[IMAGE {i + 1}/{total_nones}] Folder: {folder_name}")
        print(f"File: {img_path.name}")

        # קריאת התמונה מהדיסק בעזרת OpenCV
        img = cv2.imread(str(img_path))
        # אם התמונה לא נטענה (למשל קובץ פגום), דלג עליה
        if img is None: continue

        # הצגת התמונה (מוגדלת לקריאה נוחה)
        # שינוי גודל התמונה ל-500 על 200 פיקסלים להצגה ברורה
        display_img = cv2.resize(img, (500, 200))
        # פתיחת חלון תצוגה
        cv2.imshow(f"Verifier - {folder_name}", display_img)
        # הגדרת החלון שיופיע תמיד מעל חלונות אחרים (Topmost)
        cv2.setWindowProperty(f"Verifier - {folder_name}", cv2.WND_PROP_TOPMOST, 1)
        # המתנה רגעית (מילי-שנייה אחת) כדי לאפשר לחלון להתרנדר
        cv2.waitKey(1)

        # בקשת קלט מהמשתמש לגבי ערך הפינג האמיתי שנראה בתמונה
        user_input = input("Enter real ping (or H for help): ").strip().upper()

        # אם המשתמש בחר לסיים את התהליך (End)
        if user_input in ["E", "END"]:
            # סגירת כל חלונות התמונות
            cv2.destroyAllWindows()
            # יציאה מהלולאה
            break

        # אם המשתמש ביקש עזרה
        if user_input in ["H", "HELP"]:
            # קריאה לפונקציית העזרה
            show_help()
            # בקשת הקלט מחדש לאחר הצגת העזרה
            user_input = input("Enter real ping: ").strip().upper()

        # אם המשתמש ביקש לדלג על כל שאר התיקייה
        if user_input in ["SP", "SKIP FOLDER"]:
            # הדפסת הודעת דילוג
            print(f"[SKIP] Skipping folder: {folder_name}")
            # שמירת שם התיקייה ברשימת הדילוג
            last_skipped_folder = folder_name
            # סגירת החלון
            cv2.destroyAllWindows()
            # מעבר לתמונה הבאה
            continue

        # אם המשתמש בחר לדלג על התמונה הנוכחית (S או פשוט אנטר)
        if user_input in ["S", "SKIP", ""]:
            # סגירת החלון
            cv2.destroyAllWindows()
            # מעבר לתמונה הבאה
            continue

        # ביצוע התיקון אם הוזן מספר (הפינג הנכון)
        # --- זהו הקטע החדש והמתוקן (Michael's Rule) ---
        # בדיקה האם הקלט הוא מספרי
        if user_input.isdigit():
            # שמירת ערך הפינג החדש
            new_ping = user_input

            # 1. שינוי השם לפורמט המבוקש: החלפת "Ping_None" ב-"N_Ping_Value"
            # הביטוי הרגולרי מחפש את התבנית Ping_ ולאחריה אחת ממילות הכשלון ומחליף בפורמט התיקון הידני N
            new_name = re.sub(r"Ping_(None|fail|not_found|not_detected)", f"N_Ping_{new_ping}", img_path.name,
                              flags=re.IGNORECASE)

            # יצירת נתיב יעד עם השם החדש
            new_path = img_path.with_name(new_name)
            # ביצוע שינוי השם (Rename) בפועל על הדיסק
            os.rename(str(img_path), str(new_path))

            # 2. עדכון ה-CSV המקומי כדי לסנכרן את הנתונים למחקר
            # בדיקה האם קיים קובץ ping_results.csv באותה התיקייה של התמונה
            if (csv_path := img_path.parent / "ping_results.csv").exists():
                try:
                    # טעינת קובץ ה-CSV לתוך DataFrame
                    df_csv = pd.read_csv(csv_path)
                    # חילוץ מספר הפריים: בפורמט שלך (000331_...) המספר נמצא באינדקס 0 לפני הקו התחתון
                    frame_id = img_path.stem.split("_")[0]
                    # עדכון ערך הפינג בשורה המתאימה למספר הפריים שמצאנו
                    df_csv.loc[df_csv['frame'].astype(str) == str(frame_id), 'ping'] = new_ping
                    # שמירת קובץ ה-CSV המעודכן חזרה לדיסק
                    df_csv.to_csv(csv_path, index=False)
                    # הדפסת אישור על העדכון הכפול
                    print(f"[FIXED] File renamed to: {new_name} and CSV updated.")
                # טיפול בשגיאה במידה ועדכון ה-CSV נכשל
                except Exception as e:
                    # הדפסת אזהרה עם פירוט השגיאה
                    print(f"[WARN] CSV Update failed for {img_path.name}: {e}")

            # הוספת התיעוד לדוח השינויים עבור התיקייה הנוכחית
            if folder_name not in changes_report:
                # יצירת רשימה לתיקייה חדשה במידת הצורך
                changes_report[folder_name] = []
            # הוספת השורה של "לפני ואחרי"
            changes_report[folder_name].append(f"{img_path.name} -> {new_name}")
            # הדפסת הודעת אישור למסך
            print(f"[FIXED] Renamed to: {new_name}")

        # סגירת חלון התמונה לקראת התמונה הבאה
        cv2.destroyAllWindows()

    # 3. דוח סיכום סופי
    # הדפסת כותרת הדו"ח
    print("\n" + "=" * 60)
    print("FINAL CHANGES REPORT (NONE IDENTIFICATION)")
    print("=" * 60)
    # אם לא בוצעו תיקונים בכלל
    if not changes_report:
        # הודעה למשתמש
        print("No manual fixes were performed.")
    # מעבר על המילון והדפסת כל התיקונים לפי תיקיות
    else:
        for f_name, changes in changes_report.items():
            # הדפסת שם התיקייה
            print(f"\nFolder: {f_name}")
            for c in changes:
                # הדפסת כל קובץ ששונה עם הסימון N (Manual None Fix)
                print(f"  [N] {c}")
    # סגירת מסגרת הדו"ח
    print("=" * 60)


# נקודת הכניסה לתוכנית - הרצה של פונקציית האימות במידה ומריצים את הקובץ ישירות
if __name__ == "__main__":
    # קריאה לפונקציה
    verify_none_identifications()

# --- דוגמת הרצה (Michael's Rule) ---
"""
1. וודא שהנתיב ב-SOURCE_PATH תואם ל-100 המשחקים החדשים.
2. כנס ל-venv:
   cd "C:\\project_ping\\ping_extractor"
   venv_win\\Scripts\\activate
3. הרץ את הקובץ:
cd C:\project_ping\ping_extractor\First_Action
python Ping_Verifier_None_V1_gm.py
4. בצע תיקונים (הקוד יוסיף 'N' באופן אוטומטי).
"""