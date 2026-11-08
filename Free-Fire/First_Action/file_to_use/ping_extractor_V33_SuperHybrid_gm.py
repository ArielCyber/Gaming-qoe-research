# ping_extractor_V33_SuperHybrid_gm.py
r'''
[דוגמת הרצה]:
cd C:\project_ping\ping_extractor\First_Action\file_to_use
..\..\venv_win\Scripts\activate
python ping_extractor_V33_SuperHybrid_gm.py

'''

# ייבוא ספריות בסיסיות למערכת ההפעלה, עיבוד תמונה וחישובים
import os  # ספרייה לניהול קבצים ותיקיות במערכת
import cv2  # ספריית OpenCV לביצוע עיבוד תמונה וראייה ממוחשבת
import numpy as np  # ספרייה לחישובים מתמטיים ועבודה עם מערכים
import tensorflow as tf  # ספריית הבינה המלאכותית להרצת מודל ה-AI
import csv  # ספרייה לקריאה וכתיבה של קבצי CSV (אקסל)
import sys  # ספרייה לניהול פרמטרים של המערכת ושורת הפקודה
from pathlib import Path  # ספרייה לניהול נתיבי קבצים בצורה חכמה
from collections import Counter  # כלי לספירת מופעים לצורך סטטיסטיקה
import json  # ספרייה לעבודה עם קבצי הגדרות בפורמט JSON
from datetime import datetime  # ספרייה לניהול והצגת תאריכים ושעות
import wmi  # ספרייה לקריאת נתוני חומרה כמו טמפרטורת מעבד
import sys

# --- הגדרות "מצב הישרדות" (Survivor Mode) ---
RESUME_MODE = False  # דגל: שים True כדי להמשיך ריצה שנעצרה, False להתחלה חדשה
WORKING_TEMP_FILE = "ping_work_in_progress.csv"  # שם קובץ העבודה הזמני

# --- הגדרות ליבה ואופטימיזציה ---
AI_THRESHOLDS = [170, 195, 220]  # ערכי הסף לזיהוי AI (העברנו לכאן לפי המלצת GPT)
DIGIT_SIZE = (40, 64)  # הגדרת הגודל הקבוע אליו ננרמל כל ספרה
BASE_DIR = Path(__file__).resolve().parent  # איתור תיקיית העבודה של הסקריפט
TEMPLATES_DIR = BASE_DIR / "digits_font" / "0_9"  # נתיב לתיקיית הטמפלייטים
MODEL_PATH = str(BASE_DIR / "ping_model_final.keras")  # נתיב למודל ה-AI
THERMAL_PROTECTION_ENABLED = True  #האם לאפשר עצירה אוטומטית בחום קיצוני (אם מסמנים אמת אז להריץ את הקוד ב-CMD כמנהל)
MAX_SAFE_TEMP = 92.0  # טמפרטורה מקסימלית לעצירה
SAVE_INTERVAL = 5000  # כל כמה תמונות לבצע שמירה לדיסק
INPUT_DIR_DEFAULT = r"C:\project_ping\adb\sessions_screencap_pc_roi\Per_Num"  # נתיב ברירת מחדל

# איתחול חיבור WMI פעם אחת בלבד (שיפור ביצועים לפי GPT)
WMI_INTERFACE = None  # יצירת משתנה גלובלי לחיבור
if THERMAL_PROTECTION_ENABLED:  # אם הגנת החום מופעלת
    try:
        WMI_INTERFACE = wmi.WMI(namespace="root\\wmi")  # נסה להתחבר לממשק החומרה
    except:
        print("[WARNING] No WMI access. Run as Administrator for temperature checks.")  # אזהרה אם אין גישה


def get_now():
    """פונקציה שמחזירה את השעה הנוכחית בפורמט קריא"""
    return datetime.now().strftime("%H:%M:%S")  # שעות:דקות:שניות


def get_cpu_temp():
    """מקבל נתוני חום מהמעבד תוך שימוש בחיבור הקיים"""
    if WMI_INTERFACE is None: return None, "no access"  # אם אין חיבור, החזר שאין גישה
    try:
        temp_info = WMI_INTERFACE.MSAcpi_ThermalZoneTemperature()[0]  # קבלת נתוני החיישן
        temp_c = (temp_info.CurrentTemperature / 10.0) - 273.15  # המרה למעלות צלזיוס
        return temp_c, f"{temp_c:.1f}°C"  # החזרת ערך ומחרוזת
    except:
        return None, "error"  # במקרה של תקלה בקריאה


# --- פונקציות העיבוד נשארות זהות (ה"מוח" של המערכת) ---

def get_next_output_name(base_name="ping_results_v33", extension=".csv"):
    """מוצא את המספר הסידורי הפנוי הבא בתיקייה בשביל קובץ הפלט הסופי"""
    i = 1;  # התחלה מ-1
    while os.path.exists(f"{base_name}_{i}{extension}"): i += 1  # חיפוש הקובץ הפנוי הבא
    return f"{base_name}_{i}{extension}"  # החזרת השם המלא


FINAL_OUTPUT_CSV = get_next_output_name()  # קביעת שם הקובץ הסופי לריצה הנוכחית


def load_config_source(source):
    """טוען הגדרות צבע HSV מקובץ או מילון"""
    if isinstance(source, str) and os.path.exists(source):  # אם זה נתיב לקובץ
        with open(source, 'r') as f:
            data = json.load(f)  # קריאת ה-JSON
        config = {}  # מילון חדש
        for key in ["WHITE", "YELLOW", "RED"]:  # מעבר על צבעים
            if key in data:  # אם קיים בנתונים
                c = data[key]  # קבלת הערכים
                config[key.lower()] = {"low": [c["h_min"], c["s_min"], c["v_min"]],
                                       "high": [c["h_max"], c["s_max"], c["v_max"]]}
        if "red" in config: config["red_1"] = config["red"]; config["red_2"] = config["red"]  # פיצול אדום
        return config  # החזרת הקונפיגורציה
    return source if isinstance(source, dict) else DEFAULT_COLOR_CONFIG  # החזרת ברירת מחדל


# הגדרות צבעי HSV כברירת מחדל
DEFAULT_COLOR_CONFIG = {
    "white": {"low": [0, 0, 160], "high": [180, 50, 255]},
    "yellow": {"low": [18, 90, 90], "high": [40, 255, 255]},
    "red_1": {"low": [0, 90, 90], "high": [15, 255, 255]},
    "red_2": {"low": [150, 90, 90], "high": [180, 255, 255]}
}

# טעינת מודל ה-AI
print(f"[{get_now()}] [INFO] Loading AI model: {MODEL_PATH}")  # הודעת פתיחה
model = tf.keras.models.load_model(MODEL_PATH)  # טעינת הקובץ לזיכרון


class PingResult:
    """מחלקה לשמירת תוצאת עיבוד של תמונה בודדת"""

    def __init__(self, path, ping=None, src="FAIL"):
        self.path = Path(path);
        self.ping = ping;
        self.src = src  # שמירת נתיב, ערך ומקור


def load_templates():
    """טוען את תמונות הספרות להשוואה"""
    templates = {i: [] for i in range(10)}  # מילון ריק
    if not os.path.exists(TEMPLATES_DIR): return templates  # בדיקת קיום תיקייה
    for i in range(10):  # עבור כל ספרה
        folder = TEMPLATES_DIR / str(i)  # נתיב התיקייה
        if os.path.exists(folder):  # אם קיימת
            for p in Path(folder).glob("*.png"):  # עבור כל תמונה
                t = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)  # קריאה בשחור-לבן
                if t is not None: templates[i].append(cv2.resize(t, DIGIT_SIZE))  # שמירה
    return templates  # החזרת הכל


def get_v16_masks(img, config=None):
    """יוצר מסכות צבע HSV לתמונה"""
    cfg = load_config_source(config);
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)  # המרה ל-HSV
    return {
        "white": cv2.inRange(hsv, np.array(cfg["white"]["low"]), np.array(cfg["white"]["high"])),
        "yellow": cv2.inRange(hsv, np.array(cfg["yellow"]["low"]), np.array(cfg["yellow"]["high"])),
        "red": cv2.bitwise_or(
            cv2.inRange(hsv, np.array(cfg.get("red_1", cfg.get("red"))["low"]),
                        np.array(cfg.get("red_1", cfg.get("red"))["high"])),
            cv2.inRange(hsv, np.array(cfg.get("red_2", cfg.get("red"))["low"]),
                        np.array(cfg.get("red_2", cfg.get("red"))["high"]))
        )
    }


def validate_color(val, color):
    """בודק התאמת פינג לצבע"""
    if val is None: return False
    if color == "white" and 1 <= val <= 149: return True
    if color == "yellow" and 150 <= val <= 998: return True
    if color == "red" and val == 999: return True
    return False


def match_tpl(crop, templates):
    """השוואת תבנית (Template Matching)"""
    best_val, best_score = None, -1  # אתחול
    for d, t_list in templates.items():  # עבור כל ספרה
        for t in t_list:  # עבור כל טמפלייט
            res = cv2.matchTemplate(crop, t, cv2.TM_CCOEFF_NORMED)  # חישוב התאמה
            _, score, _, _ = cv2.minMaxLoc(res)  # קבלת ציון
            if score > best_score: best_score, best_val = score, d  # שמירת הכי טוב
    return best_val, best_score  # החזרה


def process_for_ai(img, size=(40, 64)):
    """הכנת גזיר תמונה למודל ה-AI"""
    kernel = np.ones((3, 3), np.uint8);
    img_f = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)  # ניקוי
    img_f = cv2.dilate(img_f, kernel, iterations=1);
    h, w = img_f.shape  # הדגשה
    scale = min(size[1] / max(1, h), size[0] / max(1, w)) * 0.8  # יחס גודל
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale));
    resized = cv2.resize(img_f, (nw, nh))  # שינוי גודל
    canvas = np.zeros((size[1], size[0]), dtype=np.uint8);
    y_off = (size[1] - nh) // 2;
    x_off = (size[0] - nw) // 2  # קנבס
    canvas[y_off: y_off + nh, x_off: x_off + nw] = resized  # מיקום במרכז
    return (canvas.astype('float32') / 255.0).reshape(1, 64, 40, 1)  # נרמול


def ai_extract_single(img_bgr, threshold_val):
    """חילוץ פינג באמצעות רשת נוירונים"""
    roi = img_bgr[0: 130, 0: 350];
    red_channel = roi[:, :, 2]  # חיתוך האזור הרלוונטי
    _, thresh = cv2.threshold(red_channel, threshold_val, 255, cv2.THRESH_BINARY)  # הפרדה בינארית
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # מציאת קווים
    valid_c = sorted([c for c in contours if 18 < cv2.boundingRect(c)[3] < 70],
                     key=lambda c: cv2.boundingRect(c)[0])  # סינון ומיון
    digits, confs = "", []  # תוצאות
    for c in valid_c:  # עבור כל רכיב
        x, y, w, h = cv2.boundingRect(c)  # מימדים
        if w >= 75:  # דבוקות (3)
            w3 = w // 3
            for i in range(3):
                p = process_for_ai(thresh[y: y + h, x + i * w3: x + (i + 1) * w3]);
                pred = model.predict(p, verbose=0)
                digits += str(np.argmax(pred));
                confs.append(np.max(pred))
        elif w > 42:  # דבוקות (2)
            mid = w // 2
            for part in [thresh[y: y + h, x: x + mid], thresh[y: y + h, x + mid: x + w]]:
                p = process_for_ai(part);
                pred = model.predict(p, verbose=0)
                digits += str(np.argmax(pred));
                confs.append(np.max(pred))
        else:  # ספרה אחת
            p = process_for_ai(thresh[y: y + h, x: x + w]);
            pred = model.predict(p, verbose=0)
            digits += str(np.argmax(pred));
            confs.append(np.max(pred))
    if not confs or len(digits) > 3: return None  # בדיקת תקינות
    return digits if (sum(confs) / len(confs)) > 0.9 else None  # החזרה לפי ביטחון


def process_image_v33(img_path, templates, config=None):
    """המנוע ההיברידי: טמפלייטים ואז AI"""
    img = cv2.imread(str(img_path))  # קריאת תמונה
    if img is None: return PingResult(img_path, None, "ERROR")  # בדיקת קובץ
    masks = get_v16_masks(img, config=config)  # יצירת מסכות
    for color in ["white", "yellow", "red"]:  # מעבר על צבעים
        mask = masks[color];
        num_labels, _, stats, _ = cv2.connectedComponentsWithStats(mask)  # רכיבים
        components = sorted([stats[i] for i in range(1, num_labels) if stats[i, cv2.CC_STAT_AREA] > 10],
                            key=lambda x: x[cv2.CC_STAT_LEFT])  # סינון
        digits, scores = [], []  # תוצאות
        for c in components:  # עיבוד ספרות
            crop = cv2.resize(mask[c[1]: c[1] + c[3], c[0]: c[0] + c[2]], DIGIT_SIZE)
            d, score = match_tpl(crop, templates)
            if d is not None: digits.append(str(d)); scores.append(score)
        if digits and len(digits) <= 3 and min(scores) > 0.85:  # אם אמין
            val = int("".join(digits))
            if validate_color(val, color): return PingResult(img_path, val, f"TPL_{color.upper()}")  # הצלחה
    img_blur = cv2.GaussianBlur(img, (3, 3), 0);
    ai_attempts = []  # ניסיונות AI
    for t_val in AI_THRESHOLDS:  # שימוש בקבוע שהגדרנו למעלה (שיפור GPT)
        res = ai_extract_single(img_blur, t_val)
        if res: ai_attempts.append(res)
    if ai_attempts: return PingResult(img_path, int(Counter(ai_attempts).most_common(1)[0][0]),
                                      "AI_V30_RED")  # הצלחה AI
    return PingResult(img_path, None, "FAIL")  # כישלון סופי


# --- פונקציות ניהול קבצים ו-Resume ---

def append_batch_to_temp_csv(batch_results, file_path):
    """הוספת תוצאות לקובץ הזמני"""
    file_exists = os.path.exists(file_path)  # בדיקת קיום
    with open(file_path, 'a', newline='', encoding='utf-8') as f:  # מצב הוספה
        writer = csv.writer(f)  # יצירת כותב
        if not file_exists: writer.writerow(['Filename', 'Ping', 'Detection_Method'])  # כותרת אם צריך
        for r in batch_results: writer.writerow([r.path.name, r.ping, r.src])  # כתיבת שורות


def finalize_output(all_results, temp_file, final_file):
    """יצירת דוח סופי ומחיקת הזמני"""
    stats = Counter(r.src for r in all_results);
    total = len(all_results)  # סטטיסטיקה
    with open(final_file, 'w', newline='', encoding='utf-8') as f:  # כתיבת הקובץ הסופי
        writer = csv.writer(f);
        writer.writerow(['Filename', 'Ping', 'Detection_Method'])  # כותרת
        for r in all_results: writer.writerow([r.path.name, r.ping, r.src])  # נתונים
        writer.writerow([]);
        writer.writerow(['--- DETECTION SUMMARY ---']);
        writer.writerow(['Method', 'Count', 'Percentage'])
        for method, count in stats.items(): writer.writerow([method, count, f"{(count / total) * 100:.1f}%"])  # סיכום
    if os.path.exists(temp_file): os.remove(temp_file)  # מחיקת הקובץ הזמני בסיום בטוח


def main():
    """הלוגיקה המרכזית של הריצה"""
    print(f"\n[{get_now()}] === SCRIPT EXECUTION STARTED ===")  # פתיחה
    folder = sys.argv[1] if len(sys.argv) > 1 else INPUT_DIR_DEFAULT  # תיקיית קלט
    config_input = sys.argv[2] if len(sys.argv) > 2 else None  # הגדרות צבע
    templates = load_templates();
    images = sorted(list(Path(folder).rglob("*.png")))  # טעינת משאבים
    if not images: print(f"[{get_now()}] !!! [ERROR] No PNG images found."); return  # בדיקת תמונות

    results, processed_map = [], {}  # אתחול

    if RESUME_MODE:  # מצב המשכיות
        if not os.path.exists(WORKING_TEMP_FILE):
            error_msg = f"\n{'!'*60}\n"
            error_msg += f"[{get_now()}] !!! [ERROR] Resume mode ON but {WORKING_TEMP_FILE} not found!\n"
            error_msg += f"!!! [ACTION REQUIRED] Please change RESUME_MODE = False in:\n"
            error_msg += f"!!! ping_extractor_V33_SuperHybrid_gm.py\n"
            error_msg += f"{'!'*60}\n"
            sys.stderr.write(error_msg) # שולח לטרמינל הראשי
            sys.exit(1)
        
        print(f"[{get_now()}] [INFO] Resume Mode active. Loading data...")  # הודעה
        with open(WORKING_TEMP_FILE, 'r', encoding='utf-8') as f:  # קריאת שחזור
            reader = csv.reader(f)
            for row in reader:  # מעבר על שורות
                if not row or row[0] == 'Filename': continue  # דילוג על כותרות
                try:  # הוספת try-except למניעת קריסה משורה פגומה (שיפור GPT הקריטי)
                    p_val = int(row[1]) if row[1] != 'None' and row[1] != '' else None
                    results.append(PingResult(Path(folder) / row[0], p_val, row[2]))
                    processed_map[row[0]] = True  # סימון כמעובד
                except (ValueError, IndexError):
                    continue  # אם השורה פגומה, פשוט דלג עליה
        print(f"[{get_now()}] [INFO] Recovered {len(processed_map)} images.")  # סיום שחזור

    total_imgs, current_batch = len(images), []  # אתחול לולאה
    for i, p in enumerate(images):  # מעבר על תמונות
        if p.name in processed_map: continue  # דילוג על מה שכבר עשינו

        res = process_image_v33(p, templates, config=config_input)  # עיבוד תמונה
        results.append(res);
        current_batch.append(res)  # שמירת תוצאה

        if len(results) % SAVE_INTERVAL == 0:  # שמירה כל 5000 תמונות
            temp_val, temp_str = get_cpu_temp()  # בדיקת חום
            perc = (len(results) / total_imgs) * 100  # חישוב אחוז ההתקדמות (השורה החדשה!)
            print(f"[{get_now()}] Progress: {len(results)}/{total_imgs} | {perc:.1f}% | CPU: {temp_str}")  # הוספנו את האחוזים להדפסה

            append_batch_to_temp_csv(current_batch, WORKING_TEMP_FILE);
            current_batch = []  # כתיבה לדיסק
            if THERMAL_PROTECTION_ENABLED and temp_val and temp_val > MAX_SAFE_TEMP:  # הגנה מחום
                print(f"\n!!! EMERGENCY SHUTDOWN: CPU {temp_str} !!!");
                sys.exit(1)

    if current_batch: append_batch_to_temp_csv(current_batch, WORKING_TEMP_FILE)  # כתיבת שארית
    ''' 
    #השלמות מהשכנים #
    print(f"[{get_now()}] [INFO] Starting Neighbor Fill...")  # תיקון חורים
    for i in range(2, len(results) - 2):  # מעבר על תוצאות
        if results[i].ping is None:  # אם חסר ערך
            n = [results[i - 2].ping, results[i - 1].ping, results[i + 1].ping, results[i + 2].ping]
            if all(x is not None for x in n): results[i].ping = int(sum(n) / 4); results[i].src = "NB_FILL"
    '''
    finalize_output(results, WORKING_TEMP_FILE, FINAL_OUTPUT_CSV)  # יצירת דוח ומחיקת זמני
    print("\n" + "=" * 50);
    print(f"[{get_now()}] DONE. Final results: {FINAL_OUTPUT_CSV}");
    print("=" * 50)


if __name__ == "__main__": main()  # הרצה

r'''
==============================================================================
--- דוגמאות הרצה מעודכנות לגרסת ה"שורד" (Survivor Mode CLI Usage) ---
==============================================================================

1. הרצה רגילה (התחלה חדשה):
   מוודאים ש-RESUME_MODE = False בראש הקוד.
python ping_extractor_V33_SuperHybrid_gm.py

2. הרצת המשכיות (Resume) אחרי קריסה:
   א. משנים בראש הקוד ל-RESUME_MODE = True.
   ב. מוודאים שהקובץ 'ping_work_in_progress.csv' נמצא בתיקייה.
   ג. מריצים רגיל - הסקריפט ימשיך בדיוק מהתמונה האחרונה שנשמרה.
python ping_extractor_V33_SuperHybrid_gm.py

3. שינוי תיקיית מקור בלבד (דרך ה-CMD):
python ping_extractor_V33_SuperHybrid_gm.py "C:\MyGames\Screenshots"

4. הזרקת קונפיגורציית JSON (למשל עבור טווחי צבע של P1 או P4):
python ping_extractor_V33_SuperHybrid_gm.py "." "color_range_config_P1.json"

5. הגדרת HSV ידנית בשורת הפקודה (למתקדמים):
   שימו לב לשימוש ב-Backslash (\) לפני הגרשיים בתוך המילון בחלונות (Windows).
python ping_extractor_V33_SuperHybrid_gm.py "." "{\"white\":{\"low\":[0,0,225],\"high\":[100,14,252]}}"

6. דוגמה להרצה עם כל ערכי ה-HSV (לבן, צהוב, אדום 1 ו-2):
python ping_extractor_V33_SuperHybrid_gm.py "." "{\"white\":{\"low\":[0,0,225],\"high\":[100,14,252]},\"yellow\":{\"low\":[25,235,223],\"high\":[26,254,253]},\"red_1\":{\"low\":[2,234,216],\"high\":[4,254,254]},\"red_2\":{\"low\":[160,100,80],\"high\":[180,255,255]}}"
'''
# ==============================================================================
