"""
שם הקובץ: Cut_pcap_V5_gm.py

רקע:
קוד זה מבצע חיתוך אוטומטי (Trimming) של קבצי PCAPNG בכל תיקיית משחק.
החיתוך מתבצע לפי זמן התמונה האחרונה בתיקייה בתוספת 2 שניות.

מה התחדש בגרסה V5:
1. מעקב נפח (MB): הקוד מחשב את גודל הקובץ לפני ואחרי החיתוך ומציג את החיסכון לכל תיקייה.
2. סיכום גלובלי סופי: הצגת סך כל הפקטות שנמחקו וסך כל הזיכרון (MB) שנחסך בכל הריצה.
3. סינון ודילוגים: הצגת תיקיות ששונו בלבד (מספר פקטות > 0), וטיפול בתיקיות נעולות (Wireshark פתוח).
4. Michael's Rule: פלט באנגלית בלבד, הערות בעברית, לוכסנים כפולים ודוגמאות הרצה במירכאות משולשות.

קלטים (Inputs):
- SOURCE_PATH: נתיב האב של הריצות.
- קבצי תמונה ו-PCAPNG בתוך התיקיות.

פלטים (Outputs):
- קבצי PCAPNG חתוכים.
- דוח מפורט הכולל נתוני נפח וסיכום חיסכון כללי.

דוגמת הרצה:
Navigate to your project directory and run:
cd C:\project_ping\ping_extractor\First_Action
python Cut_pcap_V5_gm.py
"""

# ייבוא ספריות לניהול מערכת ההפעלה, הרצת תהליכים חיצוניים וביטויים רגולריים
import os
import subprocess
import re
# ייבוא ספריות לניהול זמנים (עבור חיתוך לפי שעה) וניהול נתיבי קבצים
from datetime import datetime, timedelta
from pathlib import Path

# --- הגדרות נתיבים (Michael's Rule: Double backslashes) ---
# הגדרת נתיב המקור המכיל את תיקיות המחקר המעובדות
SOURCE_PATH = "C:\\project_ping\\adb\\sessions_screencap_pc_roi\\FF_Mich_Ping+300_(150+150)_lbld"
# נתיבים לכלי העזר של Wireshark המשמשים לניתוח וחיתוך קבצי תעבורת רשת
EDITCAP_PATH = "C:\\Program Files\\Wireshark\\editcap.exe"
CAPINFOS_PATH = "C:\\Program Files\\Wireshark\\capinfos.exe"


# פונקציה המשתמשת בכלי capinfos כדי לספור כמה פקטות יש בקובץ נתון
def get_packet_count(file_path):
    """מחלץ כמות פקטות בעזרת capinfos"""
    try:
        # הרצת פקודת capinfos עם דגל -c לקבלת ספירת פקטות
        result = subprocess.run([CAPINFOS_PATH, "-c", str(file_path)], capture_output=True, text=True)
        # אם הפקודה הצליחה (קוד חזרה 0)
        if result.returncode == 0:
            # חיפוש התבנית "Number of packets" בפלט הטקסטואלי שהתקבל
            match = re.search(r"Number of packets:\s+(\d+)", result.stdout)
            # החזרת המספר כערך שלם במידה ונמצא
            return int(match.group(1)) if match else 0
    except Exception:
        # החזרת 0 במידה וקרתה תקלה במהלך הבדיקה
        return 0
    return 0


# פונקציה פשוטה לחישוב גודל הקובץ ביחידות של מגה-בייט (MB)
def get_file_size_mb(file_path):
    """מחזיר את גודל הקובץ ב-MB"""
    try:
        # קבלת גודל הקובץ בבייטים וחלוקה פעמיים ב-1024
        return os.path.getsize(file_path) / (1024 * 1024)
    except Exception:
        return 0.0


# הפונקציה המרכזית שמנהלת את סריקת התיקיות וחיתוך הקבצים
def trim_pcaps_v5():
    # יצירת אובייקט נתיב לתיקיית המקור
    root_path = Path(SOURCE_PATH)
    # בדיקה האם התיקייה קיימת במחשב
    if not root_path.exists():
        # הדפסת הודעת שגיאה ויציאה במידה והנתיב לא נמצא
        print(f"[ERROR] Source path not found: {SOURCE_PATH}")
        return

    # רשימות למעקב אחר התקדמות ושגיאות לצורך הדוח הסופי
    modified_folders = []  # מידע על תיקיות שבהן הקובץ קוצר בהצלחה
    locked_folders = []  # תיקיות שבהן הקובץ פתוח בתוכנה אחרת (כמו Wireshark)
    error_folders = []  # תיקיות שבהן קרתה שגיאה טכנית

    # משתני צובר לחישוב סך המשאבים שנחסכו בכל הריצה
    total_packets_removed_all = 0
    total_mb_saved_all = 0

    # הדפסת הודעת תחילת עבודה
    print("[START] Starting PCAP trimming and resource analysis V5...")

    # 1. מעבר על תיקיות הריצה שבתוך תיקיית השורש
    # Michael's Rule: loop ends with colon
    for subdir in root_path.iterdir():
        # בדיקה שהפריט הנוכחי הוא אכן תיקייה
        if subdir.is_dir():
            # יצירת רשימה של כל התמונות וקבצי ה-PCAP בתוך התיקייה
            images = list(subdir.glob("*.png"))
            pcap_files = list(subdir.glob("*.pcapng"))

            # אם אין תמונות או קבצי רשת, אין מה לעבד בתיקייה זו
            if not images or not pcap_files:
                continue

            # 2. זיהוי זמן חיתוך (תמונה אחרונה + 2 שניות לביטחון)
            # מציאת התמונה האחרונה לפי סדר השמות (הזמן הגבוה ביותר)
            last_image = max(images, key=lambda x: x.name)
            # חילוץ התאריך והשעה משם התמונה (לפי פורמט YYYYMMDD_HHMMSS)
            match = re.search(r"(\d{8})_(\d{6})", last_image.name)
            if not match: continue

            try:
                # המרת הטקסט משם התמונה לאובייקט זמן של פייתון
                dt_obj = datetime.strptime(f"{match.group(1)}{match.group(2)}", "%Y%m%d%H%M%S")
                # הוספת 2 שניות ועיצוב מחדש לפורמט ש-editcap מבין
                stop_time = (dt_obj + timedelta(seconds=2)).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                continue

            # הגדרת הקובץ המקורי והקובץ הזמני שייווצר במהלך החיתוך
            pcap_file = pcap_files[0]
            temp_pcap = subdir / "__tmp_trimmed.pcapng"

            # 3. איסוף נתוני נפח וכמות פקטות לפני ביצוע השינוי
            original_packet_count = get_packet_count(pcap_file)
            original_size_mb = get_file_size_mb(pcap_file)

            # 4. ביצוע החיתוך בפועל בעזרת editcap
            # Michael's Rule: logic ends with colon
            try:
                # בניית הפקודה: editcap עם דגל -B (Before) שחותר את כל מה שאחרי הזמן שהגדרנו
                cmd = [EDITCAP_PATH, "-B", stop_time, str(pcap_file), str(temp_pcap)]
                # הרצת הפקודה ותפיסת הפלט
                result = subprocess.run(cmd, capture_output=True, text=True)

                # בדיקה אם החיתוך הצליח ונוצר קובץ זמני חדש
                if result.returncode == 0 and temp_pcap.exists():
                    # בדיקת הנתונים של הקובץ החדש והמקוצץ
                    new_packet_count = get_packet_count(temp_pcap)
                    new_size_mb = get_file_size_mb(temp_pcap)

                    # חישוב החיסכון בבייטים ובפקטות
                    packets_removed = original_packet_count - new_packet_count
                    mb_saved = original_size_mb - new_size_mb

                    # 5. בדיקת נעילה והחלפת קבצים (רק אם בוצע שינוי משמעותי)
                    try:
                        # ניסיון לשנות את שם הקובץ לעצמו כדי לבדוק אם הוא פתוח/נעול ע"י תוכנה אחרת
                        if os.path.exists(pcap_file):
                            os.rename(str(pcap_file), str(pcap_file))

                        # אם אכן הוסרו פקטות (כלומר היה מה לחתוך)
                        if packets_removed > 0:
                            # מחיקת הקובץ המקורי הגדול
                            os.remove(str(pcap_file))
                            # שינוי השם של הקובץ המקוצץ לשם המקורי
                            os.rename(str(temp_pcap), str(pcap_file))

                            # הוספת התיקייה לרשימת הדיווח על שינויים
                            modified_folders.append({
                                "name": subdir.name,
                                "packets": packets_removed,
                                "size": mb_saved
                            })
                            # עדכון הצוברים הכלליים של הריצה
                            total_packets_removed_all += packets_removed
                            total_mb_saved_all += mb_saved

                            # הדפסת הודעת הצלחה בפירוט החיסכון
                            print(f"  [DONE] {subdir.name}: -{packets_removed} packets (-{mb_saved:.2f} MB)")
                        else:
                            # אם לא בוצע שינוי, מוחקים את הקובץ הזמני וממשיכים
                            if temp_pcap.exists(): os.remove(str(temp_pcap))
                            print(f"  [SKIP] {subdir.name} already trimmed.")

                    # טיפול במקרה שהקובץ נעול (למשל אם Wireshark פתוחה עליו)
                    except PermissionError:
                        locked_folders.append(subdir.name)
                        print(f"  [LOCKED] {subdir.name} is currently open. Skipping.")
                        # מחיקת הקובץ הזמני כדי לא להשאיר זבל בתיקייה
                        if temp_pcap.exists(): os.remove(str(temp_pcap))

                else:
                    # טיפול בשגיאה טכנית של editcap
                    error_folders.append(subdir.name)
                    if temp_pcap.exists(): os.remove(str(temp_pcap))

            except Exception as e:
                # טיפול בשגיאות מערכת בלתי צפויות
                print(f"  [SYSTEM ERROR] {subdir.name}: {e}")
                error_folders.append(subdir.name)

    # 6. הפקת דוח סיכום סופי ומפורט למשתמש
    print("\n" + "=" * 65)
    print("FINAL TRIMMING SUMMARY REPORT (V5)")
    print("=" * 65)

    # בדיקה אם היו שינויים כלשהם בריצה
    if not modified_folders:
        print("No PCAP files required modification.")
    else:
        # הדפסת רשימת התיקיות ששונו עם פירוט החיסכון לכל אחת
        print(f"Modified folders with changes ({len(modified_folders)}):")
        # Michael's Rule: Sequential numbering starting from 1
        for idx, item in enumerate(modified_folders, 1):
            print(f" [{idx}] {item['name']}:")
            print(f"     -> Packets removed: {item['packets']}")
            print(f"     -> Storage saved:   {item['size']:.2f} MB")

    # דיווח על תיקיות שדולגו בגלל נעילת קבצים
    if locked_folders:
        print(f"\nLocked/Skipped folders ({len(locked_folders)}):")
        for idx, folder in enumerate(locked_folders, 1):
            print(f" [!] {folder}")

    # 7. הצגת סיכום החיסכון הכולל של הריצה (לפי בקשת המשתמש)
    print("-" * 65)
    print("TOTAL RESOURCE SAVINGS:")
    # הדפסת כמות הפקטות הכללית שנמחקה
    print(f" TOTAL PACKETS REMOVED: {total_packets_removed_all}")
    # הדפסת נפח האחסון הכולל שנחסך בדיסק
    print(f" TOTAL STORAGE SAVED:   {total_mb_saved_all:.2f} MB")
    print("=" * 65)


# נקודת הכניסה לסקריפט - הרצה של פונקציית החיתוך
if __name__ == "__main__":
    trim_pcaps_v5()

"""
דוגמת הרצה:
1. Close Wireshark to allow the script to modify files.
2. Verify SOURCE_PATH is correct.
3. Run in CMD:
cd C:\project_ping\ping_extractor\First_Action
python Cut_pcap_V5_gm.py
"""