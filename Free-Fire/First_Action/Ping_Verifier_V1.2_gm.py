'''
מטרת העל: בקרה ותיקון ידני של ערכי פינג חריגים בתמונות ROI.
מה התחדש בגרסה V1.2:
1. תיקון לוגי ל-SKIP FOLDER: שימוש במשתנה עזר לדילוג אמיתי על כל התמונות בתיקייה שנבחרה.
2. סטטיסטיקה מורחבת: הצגת סך התמונות בתיקייה הראשית וחישוב אחוז החריגים.
3. שיפור ממשק: הצגת שם הקובץ הנוכחי לפני ביצוע פעולה ושימוש ב-Walrus operator ליעילות.
4. Michael's Rule: תיעוד מלא בעברית, לוגיקה מסתיימת בנקודתיים, ודוגמת הרצה בסוף.
 הרצה:
cd C:\project_ping\ping_extractor\First_Action
python Ping_Verifier_V1.2_gm.py

'''

# ייבוא ספריות לניהול קבצים, עיבוד תמונה (OpenCV), ביטויים רגולריים וניהול נתיבים
import os
import cv2
import re
import sys
from pathlib import Path

# --- הגדרות (Michael's Rule: Double backslashes) ---
# הגדרת נתיב המקור המכיל את התיקיות עם התמונות שצריך לאמת
SOURCE_PATH = "C:\\project_ping\\adb\\sessions_screencap_pc_roi\\FF_Mich_Ping+300_(150+150)"
# הגדרת סף תחתון - תמונות עם פינג מתחת לערך זה ייחשבו כחריגות שדורשות בדיקה
X_THRESHOLD = 200  # check pictures with ping under X
# הגדרת סף עליון - תמונות עם פינג מעל ערך זה ייחשבו כחריגות (למעט רשימת החרגות)
Y_THRESHOLD = 730 # check pictures with ping above Y
# רשימת ערכים שהם חריגים אבל תקינים (999 מייצג מצב "אין אינטרנט" מוכר)
EXCLUDED_L = [999]


# פונקציה לחילוץ ערך הפינג מתוך שם הקובץ בעזרת רגקס
def get_ping_from_name(filename):
    # Michael's Rule: logic ends with colon
    # חיפוש התבנית "ping_" ואחריה רצף של ספרות בשם הקובץ
    match = re.search(r"ping_(\d+)", filename, re.IGNORECASE)
    # אם נמצאה התאמה, החזרת המספר כערך שלם (int), אחרת החזרת None
    return int(match.group(1)) if match else None


# פונקציה להדפסת תפריט העזרה למשתמש במידת הצורך
def show_help():
    # הדפסת מסגרת אסתטית לתפריט
    print("\n" + "?" * 30)
    print("HELP MENU:")
    # הסבר על הזנת מספר לתיקון
    print("Number -> Fix ping and rename (e.g. '50')")
    # הסבר על דילוג ללא שינוי
    print("ENTER -> No change (Skip current)")
    # הסבר על דילוג מפורש
    print("S / SKIP -> Skip current image")
    # הסבר על דילוג על כל התיקייה הנוכחית
    print("SP / SKIP FOLDER -> Skip all images in this folder")
    # הסבר על סיום התוכנית ושמירת הדוח
    print("E / END -> Stop program and save report")
    # הצגת תפריט העזרה שוב
    print("H / HELP -> Show this menu")
    print("?" * 30 + "\n")


# הפונקציה המרכזית שמנהלת את תהליך אימות הפינגים
def verify_pings():
    # יצירת אובייקט נתיב לתיקיית השורש
    root = Path(SOURCE_PATH)
    # בדיקה האם התיקייה בכלל קיימת במחשב
    if not root.exists():
        # הדפסת הודעת שגיאה במקרה שהנתיב לא נמצא
        print(f"[ERROR] Path not found: {SOURCE_PATH}")
        return

    # ספירת תיקיות ותמונות מקדימה
    # יצירת רשימה של כל תיקיות המשנה בתוך תיקיית השורש
    folders = [f for f in root.iterdir() if f.is_dir()]
    # רשימה שתאחסן את כל התמונות החריגות שנמצאו
    outlier_list = []
    # מונה לסך כל התמונות שנסרקו
    total_images_count = 0

    # הדפסת הודעת תחילת סריקה
    print(f"[START] Scanning folders for outliers...")

    # מעבר על כל תיקייה ברשימה
    for folder in folders:
        # מעבר על כל קבצי ה-PNG בתוך התיקייה הנוכחית
        for img in folder.glob("*.png"):
            # עדכון מונה התמונות הכללי
            total_images_count += 1
            # חילוץ הפינג משם התמונה הנוכחית
            p = get_ping_from_name(img.name)
            # בדיקה האם הפינג חורג מהטווח שהגדרנו ואינו ברשימת ההחרגות
            if p is not None and ((p < X_THRESHOLD or p > Y_THRESHOLD) and p not in EXCLUDED_L):
                # הוספת התיקייה ונתיב התמונה לרשימת החריגים
                outlier_list.append((folder.name, img))

    # חישוב סך כל החריגים שנמצאו
    total_outliers = len(outlier_list)
    # חישוב אחוז החריגים מתוך כלל התמונות
    percent_to_check = (total_outliers / total_images_count * 100) if total_images_count > 0 else 0

    # הצגת נתונים סטטיסטיים בתחילת הריצה למשתמש
    print(f"\n[INFO] Found {len(folders)} folders.")
    print(f"[INFO] Total images in main directory: {total_images_count}")
    print(f"[INFO] Detected {total_outliers} outlier images ({percent_to_check:.2f}% of total).")

    # מילון לשמירת הדוח על השינויים שבוצעו בפועל
    changes_report = {}
    # משתנה למעקב אחרי דילוג על תיקיות שלמות
    last_skipped_folder = ""

    # מעבר בלולאה על כל התמונות החריגות שהתגלו
    for i, (folder_name, img_path) in enumerate(outlier_list):
        # Michael's Rule: logic ends with colon
        # בדיקה האם המשתמש ביקש לדלג על כל התיקייה הזו
        if folder_name == last_skipped_folder:
            # מעבר לתמונה הבאה בלולאה
            continue

        # הדפסת סטטוס התקדמות ושם התיקייה והקובץ
        print(f"\n[IMAGE {i + 1}/{total_outliers}] Folder: {folder_name}")
        print(f"File: {img_path.name}")

        # שמירת ערך הפינג הנוכחי כפי שהוא מופיע בשם הקובץ
        current_ping = get_ping_from_name(img_path.name)
        # קריאת התמונה מהדיסק לצורך הצגה
        img = cv2.imread(str(img_path))
        # בדיקה האם התמונה נטענה בהצלחה
        if img is None:
            # דילוג לתמונה הבאה במקרה של תקלה בקריאת הקובץ
            continue

        # הגדלת התמונה לצורך נוחות קריאה (חיתוך אזור הפינג המקורי קטן מדי)
        display_img = cv2.resize(img, (500, 200))
        # פתיחת חלון והצגת התמונה המוגדלת למשתמש
        cv2.imshow(f"Verifier - Image {i + 1}", display_img)
        # פקודה שמאפשרת לחלון להיפתח ולהתעדכן (ממתינה מילי-שנייה אחת)
        cv2.waitKey(1)

        # בקשת קלט מהמשתמש לגבי הפעולה שברצונו לבצע
        user_input = input(f"Ping is {current_ping}. Action (H for help): ").strip().upper()

        # אם המשתמש בחר לסיים את הריצה
        if user_input in ["E", "END"]:
            # הודעה על סיום התוכנית ושמירת התקדמות
            print("[STOP] User terminated run. Saving progress...")
            # סגירת כל חלונות התמונות של OpenCV
            cv2.destroyAllWindows()
            # יציאה מהלולאה הראשית
            break

        # אם המשתמש ביקש עזרה
        if user_input in ["H", "HELP"]:
            # קריאה לפונקציית העזרה
            show_help()
            # בקשת קלט מחודשת לאחר הצגת העזרה
            user_input = input(f"Ping is {current_ping}. Action: ").strip().upper()

        # אם המשתמש ביקש לדלג על כל התיקייה הנוכחית
        if user_input in ["SP", "SKIP FOLDER"]:
            # הדפסת הודעת דילוג
            print(f"[SKIP] Skipping rest of folder: {folder_name}")
            # שמירת שם התיקייה כדי לדלג עליה בשאר הריצות
            last_skipped_folder = folder_name
            # סגירת החלון הנוכחי
            cv2.destroyAllWindows()
            # מעבר לתמונה הבאה
            continue

        # אם המשתמש לחץ אנטר או בחר לדלג על התמונה הבודדת
        if user_input in ["S", "SKIP"] or user_input == "":
            # סגירת החלון
            cv2.destroyAllWindows()
            # מעבר לתמונה הבאה
            continue

        # שימוש ב-Walrus operator לבדיקה ושינוי בשורה אחת: האם הקלט הוא מספר השונה מהפינג הנוכחי
        if user_input.isdigit() and (new_ping := int(user_input)) != current_ping:
            # בניית שם הקובץ החדש תוך החלפת הפינג הישן בחדש בתוספת הסימון W (Verified)
            new_name = img_path.name.replace(f"Ping_{current_ping}", f"W_Ping_{new_ping}")
            # יצירת הנתיב המלא החדש
            new_path = img_path.with_name(new_name)

            # ביצוע שינוי השם בפועל במערכת הקבצים
            os.rename(img_path, new_path)
            # עדכון דוח השינויים
            if folder_name not in changes_report:
                # יצירת רשימה חדשה לתיקייה זו במילון אם היא לא קיימת
                changes_report[folder_name] = []
            # הוספת השינוי הספציפי לרשימת השינויים של התיקייה
            changes_report[folder_name].append(f"{img_path.name} -> {new_name}")
            # הדפסת אישור על התיקון שבוצע
            print(f"[FIXED] Renamed to: {new_name}")

        # סגירת חלון התמונה בסוף כל סבב
        cv2.destroyAllWindows()

    # הדפסת דוח סופי ומעוצב של כל השינויים שבוצעו בסבב הנוכחי
    print("\n" + "=" * 60)
    print("FINAL CHANGES REPORT")
    print("=" * 60)
    # אם לא בוצעו שינויים בכלל
    if not changes_report:
        print("No changes were made.")
    # מעבר על התיקיות בדוח והדפסת כל תיקון
    else:
        for f_name, changes in changes_report.items():
            print(f"\nFolder: {f_name}")
            for c in changes:
                print(f"  [X] {c}")
    # הדפסת קו סיום לדוח
    print("=" * 60)


# נקודת הכניסה של הסקריפט - הרצה של פונקציית האימות
if __name__ == "__main__":
    # קריאה לפונקציה הראשית
    verify_pings()

r'''
# --- דוגמת הרצה (Michael's Rule) ---
 1. פתח CMD (ניתן כמנהל לשיפור מהירות פתיחת החלונות)
 2. כניסה לסביבה:
cd "C:\project_ping\ping_extractor"
3. הפעלת venv :
venv_win\Scripts\activate
 4. הרצה:
cd C:\project_ping\ping_extractor\First_Action
python Ping_Verifier_V1.2_gm.py
'''