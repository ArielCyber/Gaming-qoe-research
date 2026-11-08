# ping_renamer_V1_gm.py
import os  # ייבוא ספרייה לביצוע פעולות במערכת ההפעלה כמו שינוי שמות קבצים
import re  # ייבוא ספריית ביטויים רגולריים לחיפוש תבניות טקסט מורכבות
import sys  # ייבוא ספרייה המאפשרת לקבל ארגומנטים (פרמטרים) משורת הפקודה
from pathlib import Path  # ייבוא כלי מודרני ויעיל לניהול נתיבי קבצים ותיקיות

# --- הגדרות בסיס ---
# הגדרת תיקיית המטרה לפי הארגומנט הראשון שנשלח בהרצת הסקריפט
TARGET_FOLDER = sys.argv[1]  # "collected_images"


# הגדרת פונקציה שמנתחת את קובץ התוצאות (CSV/TXT) ובודקת קידודים
def parse_output_file(file_path):
    """מנסה לקרוא את הקובץ במספר קידודים כדי להתגבר על פורמטים של Windows"""
    # יצירת מילון ריק שיחבר בין שם קובץ לערך הפינג שלו
    mapping = {}
    # בדיקה האם קובץ התוצאות בכלל קיים בנתיב שניתן
    if not os.path.exists(file_path):
        # הדפסת שגיאה במקרה שהקובץ חסר
        print(f"[ERROR] File not found: {file_path}")
        # החזרת מילון ריק
        return mapping

    # משתנה זמני לאחסון תוכן הקובץ לאחר קריאה
    content = None
    # רשימת קידודים אפשריים שנוצרים על ידי מערכות Windows (CMD או PowerShell)
    encodings_to_try = ['utf-8', 'utf-16-le', 'utf-16', 'cp1255', 'cp1252']

    # לולאה שעוברת על הקידודים ומנסה לפתוח את הקובץ מבלי להתרסק
    for enc in encodings_to_try:
        try:
            # ניסיון פתיחת הקובץ לקריאה עם הקידוד הנוכחי בלולאה
            with open(file_path, 'r', encoding=enc) as f:
                # קריאת כל תוכן הקובץ למחרוזת אחת
                content = f.read()
                # בדיקה האם הקובץ מכיל את הסימן שמסמל קשר בין שם לפינג
                # בודק אם הקובץ מכיל חץ, פסיק או נקודה (של סיומת קובץ) כדי לאשר פענוח
                if any(marker in content for marker in ["->", "<-", ",", ".png", ".jpg"]):
                    # הדפסת אישור על פענוח מוצלח של פורמט הטקסט
                    print(f"[INFO] Successfully read file using {enc} encoding.")
                    # יציאה מהלולאה ברגע שמצאנו קידוד תקין
                    break
        # טיפול בשגיאת פענוח במידה והקידוד אינו מתאים
        except (UnicodeDecodeError, UnicodeError):
            # המשך לקידוד הבא ברשימה
            continue

    # אם לאחר כל הניסיונות לא הצלחנו לקרוא את הקובץ
    if content is None:
        # הדפסת הודעת שגיאה על כשל בפענוח
        print("[ERROR] Could not decode the file with any known encoding.")
        # החזרת המילון הריק
        return mapping

    # הגדרת תבנית חיפוש (Regex) לחילוץ שם הקובץ (PNG/JPG) וערך הפינג שאחרי החץ
    #pattern = re.compile(r"([\w\.-]+\.(?:png|jpg|jpeg))[\s,]+(?:->|<-|,|)\s*(\w+)", re.IGNORECASE)#############
    #pattern = re.compile(r"([\w\\/ \.-]+\.(?:png|jpg|jpeg))[\s,]*[-><,]*\s*(\w+)", re.IGNORECASE)
    pattern = re.compile(r'^([^,]+)\s*,\s*([^,]*)\s*,\s*.*$', re.IGNORECASE)

    # מעבר שורה-שורה על תוכן הקובץ שפוענח
    for line in content.splitlines():
        # ניסיון למצוא את התבנית (שם קובץ + פינג) בשורה הנוכחית
        match = pattern.search(line)
        # אם נמצאה התאמה
        '''
        if match:
            # חילוץ שם הקובץ מהקבוצה הראשונה בתבנית וניקוי רווחים
            filename = match.group(1).strip()
            # חילוץ ערך הפינג מהקבוצה השנייה בתבנית וניקוי רווחים
            ping_val = match.group(2).strip()
            # הוספת הנתונים למילון ה-mapping
            mapping[filename] = ping_val
        '''
        if match:
            raw_filename = match.group(1).strip()
            ping_val = match.group(2).strip()

            # דילוג על שורת כותרת
            if raw_filename.lower() in ["filename", ""]:
                continue

            # לוקחים רק את שם הקובץ (למקרה שיש נתיב – לא סביר כאן אבל בטוח)
            filename = Path(raw_filename).name

            # אם העמודה של הפינג ריקה → נתייחס לזה כ-"FAIL" או נדלג
            if not ping_val:
                ping_val = "FAIL"

            mapping[filename] = ping_val
    # החזרת המילון המלא עם כל הקישורים בין קבצים לפינגים
    return mapping


# הגדרת הפונקציה הראשית לביצוע שינוי השמות
def run_renaming():
    # קבלת נתיב קובץ התוצאות מהארגומנט השני שנשלח ב-CMD
    output_file = sys.argv[2]  # output_file = input("Please enter the path to the output results file: ")

    # הפעלת הפונקציה שיוצרת את המפה בין שמות הקבצים לתוצאות הפינג
    file_map = parse_output_file(output_file)
    # בדיקה האם נמצאו נתונים כלשהם בקובץ
    if not file_map:
        # הודעה למשתמש לבדוק את תוכן הקובץ אם המילון ריק
        print("[INFO] No mappings found. Please check your output file content.")
        # סיום הריצה
        return

    # יצירת אובייקט נתיב לתיקיית התמונות
    image_folder = Path(TARGET_FOLDER)
    # בדיקה האם התיקייה שצוינה אכן קיימת במחשב
    if not image_folder.exists():
        # הדפסת שגיאה אם התיקייה לא נמצאה
        print(f"[ERROR] Folder '{TARGET_FOLDER}' does not exist.")
        # סיום הריצה
        return

    # הדפסת תחילת התהליך בתיקייה שנבחרה
    print(f"[INFO] Starting renaming process in: {TARGET_FOLDER}...")

    # מונה למעקב אחרי כמה קבצים שונה שמם
    count_renamed = 0
    # מונה למעקב אחרי כמה קבצים לא נמצא להם פינג
    count_not_found = 0

    # מעבר על כל הקבצים בתוך התיקייה
    for img_path in image_folder.glob("*"):
        # בדיקה האם סיומת הקובץ היא תמונה (PNG או JPG)
        if img_path.suffix.lower() not in [".png", ".jpg", ".jpeg"]:
            # דילוג על קבצים שאינם תמונות
            continue

        # שמירת השם המקורי של הקובץ
        old_name = img_path.name

        # בדיקה האם השם המקורי מופיע במילון התוצאות שייצרנו
        if old_name in file_map:
            # שליפת ערך הפינג המשויך לקובץ זה
            ping_val = file_map[old_name]
            # ניקוי תוספות קודמות של פינג או "Not Found" משם הקובץ בעזרת Regex
            clean_stem = re.sub(r"_Ping_[\w]+|_Not_Found", "", img_path.stem, flags=re.IGNORECASE)
            # בניית השם החדש: השם הנקי + תוספת הפינג + הסיומת המקורית
            new_name = f"{clean_stem}_Ping_{ping_val}{img_path.suffix}"
            # יצירת הנתיב המלא החדש עבור הקובץ
            new_path = img_path.with_name(new_name)

            # ניסיון לבצע את שינוי השם בפועל במערכת הקבצים
            try:
                # הפקודה שמשנה את שם הקובץ בדיסק
                os.rename(img_path, new_path)
                # עדכון המונה של הקבצים ששונו
                count_renamed += 1
            # טיפול במקרה של תקלה טכנית בשינוי השם
            except Exception as e:
                # הדפסת פירוט השגיאה עבור הקובץ הספציפי
                print(f"[ERROR] Could not rename {old_name}: {e}")
        # מקרה שבו שם הקובץ לא נמצא במילון התוצאות
        else:
            # אם הקובץ עדיין לא סומן כ"לא נמצא"
            if "_Not_Found" not in old_name:
                # בניית שם חדש עם תוספת שמציינת שהפינג לא אותר
                new_name = f"{img_path.stem}_Not_Found{img_path.suffix}"
                # שינוי השם במערכת
                os.rename(img_path, img_path.with_name(new_name))
                # עדכון המונה של הקבצים הלא מזוהים
                count_not_found += 1

    # הדפסת סיכום התהליך בעיצוב ברור
    print("\n" + "=" * 50)
    print(f"[SUCCESS] Renaming process finished.")
    print(f"Total renamed: {count_renamed}")
    print(f"Total marked as Not Found: {count_not_found}")
    print("=" * 50)


# נקודת הכניסה של הסקריפט - הרצה של הפונקציה הראשית
if __name__ == "__main__":
    # קריאה לפונקציית שינוי השמות
    run_renaming()


# --- דוגמת הרצה ---
# 1. וודא שאתה בתוך הסביבה הווירטואלית (venv_win).
# 2. הרץ את הפקודה: python ping_renamer_V1_gm.py
# 3. כאשר תתבקש, הקלד: out_V33_10K.txt
# 4. הקוד יסרוק את תיקיית 'collected_images' ויעדכן את השמות.


# עדכון דוגמת הרצה:

# כעת הוא מקבל את נתיב התיקייה כארגומנט ראשון, ואת קובץ הפלט כארגומנט שני.
# python ping_renamer_V1_gm.py ./collected_images out_V33_10K.txt
