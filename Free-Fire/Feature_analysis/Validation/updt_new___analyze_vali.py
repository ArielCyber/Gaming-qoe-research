r'''
# 1. מעבר לתיקייה שבה נמצא הקוד
cd C:\project_ping\ping_extractor\Feature_analysis

# 2. הפעלת הסביבה הווירטואלית (VENV)
# אם הוא נמצא בתיקייה אחת למעלה (כפי שזה נראה מהנתיב שלך):
..\venv_win\Scripts\activate

# 3. הרצת הקוד
python updt_new___analyze_vali.py

'''
# ==============================================================================
# File: updt_new___analyze.py
# Purpose: Professional Backend Engine for Game QoE Analysis
# ==============================================================================

# --- קומה 1: ייבוא ספריות ---
import os
import pandas as pd
import numpy as np
import re
import ast
import time
import multiprocessing
from datetime import datetime
from pathlib import Path
from nfstream import NFStreamer
from scapy.all import PcapReader, IP, IPv6, UDP, TCP
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
from sklearn.model_selection import train_test_split
from sklearn.inspection import permutation_importance
from joblib import Parallel, delayed

# ייבוא מודולים מקומיים (ודא שהם באותה תיקייה)
from PingLatency import PingLatency

try:
    from rank import rank_qoe_3_classes, rank_str_to_int_mapping_3_classes
    from modelse import make_models
except ImportError:
    print("⚠️ Warning: Local modules (rank.py/modelse.py) not found. Check your paths!")

# --- קומה 2: הגדרות גלובליות ונתיבים  ---
# כאן נשים את כל המשתנים (DATA_SUBFOLDER, RAW_DATA_PATH, PRODUCTS_DIR וכו')

CURRENT_DIR = Path(os.getcwd())
BASE_DIR = CURRENT_DIR.parent
DATA_SUBFOLDER = "P++200_first_5"  # שנה לפי הצורך
RAW_DATA_PATH = BASE_DIR.parent / "adb" / "sessions_screencap_pc_roi" / DATA_SUBFOLDER
PRODUCTS_DIR = CURRENT_DIR / f"Products_{DATA_SUBFOLDER}"
os.makedirs(PRODUCTS_DIR, exist_ok=True)

GAME_PORT_RANGE = "10010-10025"
BPF_FILTER = f"udp and (portrange {GAME_PORT_RANGE})"
WINDOW_SIZE = 10
DECAY_RATE = 0.5
SAMPLE_DURATION = 1
USE_PARALLEL = False
USE_PARALLEL_ML = True
CORES_TO_USE = max(1, multiprocessing.cpu_count() - 4)
INCLUDE_SVM = False

start_time = time.time()  # Michael: הגדרת זמן התחלה גלובלי לסיכום הסופי

# --- שמות קבצי התוצרים (File Name Configuration) ---
METADATA_FILENAME = "metadata_results_auto.csv"
NETWORK_ANALYSIS_FILENAME = "NetDiscovery_Michael_gm.xlsx"
FEATURES_FILENAME = "final_training_features.csv"
IMPORTANCE_FILENAME = "feature_importance_results.csv"
REPORT_FILENAME = f"Color_Coded_{DATA_SUBFOLDER}.xlsx" # דו"ח הקונצנזוס הסופי
NET_BACKUP_FILENAME = "network_analysis_backup.csv" # קובץ הגיבוי של ניתוח הרשת

# --- קומה 3: פונקציות העזר והעיבוד ---

r'''
בלוק זה מכיל פונקציות עזר קריטיות לעיבוד נתוני הזמן וה-QoE.
מטרתן להפוך את המידע הגולמי שנאסף משמות הקבצים לסדרות עיתיות (Time Series)
שניתן להציג בגרפים ולנתח סטטיסטית.
'''


def hhmmss_to_seconds(hhmmss: int) -> int:
    r'''
    המרת פורמט זמן של שש ספרות (HHMMSS) למספר שניות כולל מתחילת היום.
    הלוגיקה: פירוק המספר השלם לשעות, דקות ושניות וסיכומם לשניות.
    למשל: 143005 (שתיים וחצי וחמש שניות) הופך ל-52,205 שניות.
    '''
    h = hhmmss // 10000  # חילוץ שתי הספרות השמאליות (שעות)
    m = (hhmmss // 100) % 100  # חילוץ שתי הספרות האמצעיות (דקות)
    s = hhmmss % 100  # חילוץ שתי הספרות האחרונות (שניות)
    return h * 3600 + m * 60 + s  # חישוב סך השניות הכולל מתחילת היממה


def to_qoe_class_zero(ping):
    r'''
    המרת ערך פינג גולמי (מספר או טקסט) למחלקת איכות חוויה (QoE Class).
    הפונקציה מחזירה 1, 2 או 3 לפי רמת האיכות, או 0 במקרים של שגיאה או נתון חסר.
    זהו ה-Ground Truth (האמת המוחלטת) שלפיו המודלים יתאמנו.
    '''
    # בדיקה האם הנתון חסר (NaN)
    if pd.isna(ping):
        return 0
    try:
        # ניסיון להפוך את הערך למספר עשרוני (למקרה שהגיע כטקסט)
        ping = float(ping)
    except Exception:
        # אם יש ערך לא תקין (כמו טקסט משובש), נסמן אותו כ-0
        return 0

    # שימוש בפונקציות הדירוג מהקובץ rank.py (למשל Good/Fair/Poor)
    label = rank_qoe_3_classes(ping)
    # המרת תווית הטקסט למספר מזהה (ID) מתוך המיפוי שהוגדר
    return rank_str_to_int_mapping_3_classes.get(label, 0)

r'''
תא זה מחליף את הסקריפט החיצוני Metadata_Creator.
הוא סורק את התיקיות ומייצר את המשתנה metadata בזיכרון.
כך אין יותר תלות בקריאת קובץ CSV חיצוני בכל תא מחדש.
'''


def extract_ping_from_filename(filename):
    r'''
    פונקציית עזר לחילוץ הפינג והזמן משם הקובץ בעזרת Regex.
    הלוגיקה: שם הקובץ מכיל את השעה ואת ערך הפינג שהופיע על המסך.
    '''
    # שימוש ב-r (Raw String) מאפשר לנו לכתוב \d פעם אחת בלבד עבור "ספרה"
    # דוגמה למבנה: _123456_...Ping_50.png
    match = re.search(r"_(\d{6})_.*Ping_(\d+)\.png", filename, re.IGNORECASE)
    if match:
        return match.group(1), int(match.group(2))

    # טיפול במקרים של פינג חסר (None) בשם הקובץ
    match_none = re.search(r"_(\d{6})_.*Ping_None\.png", filename, re.IGNORECASE)
    if match_none:
        return match_none.group(1), None

    return None, None

# פונקציה זו מכינה את הנתונים עבור הקובץ: metadata_results_auto.csv
def generate_metadata_live(source_path):
    r'''
    סורק את התיקיות ומייצר רשימת מילונים עבור כל סשן (Run).
    הפונקציה מקשרת בין קובץ ה-PCAP לצילומי המסך המתאימים לו.
    '''
    all_runs_data = []
    root = Path(source_path)

    # מעבר על כל תיקיות הניסוי בנתיב שהוגדר
    for folder in root.iterdir():
        if folder.is_dir():
            # זיהוי קובץ הרשת (PCAP) שבתוך תיקיית הסשן
            pcap_files = list(folder.glob("*.pcapng"))
            pcap_name = pcap_files[0].name if pcap_files else "MISSING"

            # בניית מילון של "שעה: פינג" עבור כל התמונות בתיקייה
            time_value_pairs = {}
            for img in folder.glob("*.png"):
                timestamp, ping_val = extract_ping_from_filename(img.name)
                if timestamp:
                    time_value_pairs[timestamp] = ping_val

            # ריכוז הנתונים לשורה אחת בטבלה
            all_runs_data.append({
                "folder": folder.name,
                "pcapng_file": pcap_name,
                # שמירת המילון כייצוג טקסטואלי (repr) לצורך עקביות
                "time_value_pairs": repr(time_value_pairs)
            })

    return pd.DataFrame(all_runs_data)

# Output File: NetDiscovery_Michael_gm.xlsx
r'''
    פונקציית העל לניתוח הרשת (Network Discovery).
        פונקציית העל לניתוח הרשת:
    משלבת NFStreamer (בשביל לקבל את ה-349 הישן) ו-Scapy (בשביל הדיוק של ה-1, ה-31 וה-35).
    כוללת מנגנון Resume (נקודות ביקורת) לחסכון בזמן.
    מפיקה קובץ Excel הכולל את העמודות הבאות:
    -------------------------------------------
    1. folder: שם הסשן המנותח (מזהה ייחודי).
    2. total_ip_convs: סך השיחות הדו-כיווניות (IP+Port) - מדד לרעש כללי.
    3. total_udp_convs: סך שיחות ה-UDP (ה-31 מ-Wireshark).
    4. game_convs: שיחות מזוקקות בטווח פורטי המשחק (ה-1 מ-Wireshark).
    5. identified_ports: רשימת הפורטים שבאמת נמצאו פעילים בתוך הטווח.
    6. game_purity_pct [%]: אחוז כמות הפקטות של המשחק מתוך כלל הפקטות.
    7. purity_ratio: יחס מספרי של פקטות משחק מול סך הכל (למשל 11000/12000).
    8. udp_pct [%]: אחוז נפח הבייטים של UDP מתוך סך התעבורה.
    9. tcp_pct [%]: אחוז נפח הבייטים של TCP מתוך סך התעבורה.
    10. avg_iat_ms [ms]: זמן הגעה ממוצע בין פקטות משחק (מדד ליציבות/Jitter).
    11. avg_pkt_size [Bytes]: גודל פקטה ממוצע בבייטים (חתימת המשחק).
    12. unique_ips: כמות כתובות IPv4 ייחודיות שנראו (ה-35 מה-Endpoints).
    13. total_flows: כמות הזרמים לפי NFStreamer (המדד הישן).
    '''
def run_network_exploration():
        # שמירת שעת תחילת הריצה הכללית
    start_time = datetime.now()

    # הגדרת נתיב לקובץ הגיבוי שמתעדכן "חי" שורה-שורה
    log_file = PRODUCTS_DIR / NET_BACKUP_FILENAME

    # --- Michael: הגדרת כפתור ה-Resume לניהול נקודות ביקורת ---
    RESUME_ANALYSIS = False  # שנה ל-False אם ברצונך למחוק את הגיבוי ולהתחיל הכל מחדש
    processed_folders = set()  # קבוצה לאחסון תיקיות שכבר נותחו
    results = []  # רשימה ריקה שתאגור את התוצאות הסופיות

    # Michael: משתנה לאיסוף נתונים גלובליים עבור גיליון Port Volume Summary
    global_port_stats = {}  # {port: {'bytes': 0, 'pkts': 0}}

    # בדיקה האם להמשיך מהמקום שבו עצרנו או להתחיל מחדש
    if log_file.exists():
        if RESUME_ANALYSIS:
            # טעינת נתונים קיימים מהגיבוי כדי לדלג על מה שבוצע
            try:
                temp_df = pd.read_csv(log_file)
                processed_folders = set(temp_df['folder'].astype(str).unique())
                # החזרת הנתונים שכבר חושבו לתוך רשימת ה-results כדי שהאקסל הסופי יהיה מלא
                results = temp_df.to_dict('records')
                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] Resume Mode: Found {len(processed_folders)} folders in backup. Skipping...")
            except Exception as e:
                print(f"⚠️ Warning: Could not read backup. Starting fresh ({e}).")
                os.remove(log_file)
        else:
            # אם Resume כבוי - מוחקים את קובץ הגיבוי הישן ומתחילים נקי
            os.remove(log_file)

    # הדפסת פתיח לטרמינל עם השעה המדויקת
    print(f"[{start_time.strftime('%H:%M:%S')}] Starting Analysis...")

    # יצירת רשימה של כל התיקיות שמתחילות ב-'run_' בתוך נתיב המקור
    folders = [f for f in os.listdir(RAW_DATA_PATH) if f.lower().startswith('run_')]

    # פירוק טווח הפורטים של המשחק (למשל '10010-10025') לשני מספרים שלמים
    p_start, p_end = map(int, GAME_PORT_RANGE.split('-'))

    # לולאה ראשית: עוברת תיקייה-תיקייה לפי הסדר
    for idx, folder in enumerate(folders):
        # חותמת זמן לרגע הנוכחי עבור הלוג
        curr_t = datetime.now().strftime('%H:%M:%S')

        # --- Michael: מנגנון הדילוג של ה-Resume ---
        if folder in processed_folders:
            # הדפסת דיווח על דילוג (כדי שתדע שהקוד אכן זוכר את התיקייה)
            print(f"   [{curr_t}] [{idx + 1}/{len(folders)}] Skipping: {folder} (Already in backup) ✅")
            continue

        # הדפסת סטטוס התקדמות: [שעה] [מונה] Processing: שם התיקייה
        print(f"   [{curr_t}] [{idx + 1}/{len(folders)}] Processing: {folder}...", end=" ", flush=True)

        # בניית הנתיב המלא לתיקייה הנוכחית
        f_path = RAW_DATA_PATH / folder

        # חיפוש כל קובץ בתוך התיקייה שמכיל את הסיומת pcap (קבצי הקלטת הרשת)
        pcap_files = list(f_path.glob("*.pcap*"))

        # אם לא נמצא קובץ PCAP בתיקייה - מדלגים וממשיכים הלאה
        if not pcap_files:
            print("Skipped ❌")
            continue

        try:
            # הפיכת נתיב הקובץ למחרוזת (סטרינג) עבור הספריות השונות
            pcap_path = str(pcap_files[0])

            # --- שלב 1: NFStreamer לטובת total_flows (המספר הישן והגבוה, למשל 349) ---
            # אנחנו משתמשים ב-timeouts של 1 שניה כדי לקבל חיתוך זרימות מהיר כמו קודם
            streamer = NFStreamer(source=pcap_path, statistical_analysis=True, idle_timeout=1, active_timeout=1)
            nfs_df = streamer.to_pandas()  # הפיכת נתוני הזרימות לטבלה
            legacy_total_flows = len(nfs_df)  # ספירת כמות השורות (הזרימות) שיצאו

            # --- שלב 2: Scapy לטובת דיוק מחקרי 100% (Packet-Level) ---
            # אתחול "קבוצות" (Sets) לאיסוף נתונים ייחודיים (מניעת כפילויות אוטומטית)
            all_ip_convs = set()  # (א) כל השיחות הדו-כיווניות (IP+Port)
            udp_convs = set()  # (ב) שיחות UDP בלבד (המקור ל-31)
            game_convs = set()  # (ג) שיחות ששייכות למשחק (המקור ל-1)
            game_ports = set()  # (ד) הפורטים הספציפיים שזוהו בתוך הטווח

            # אתחול מונים ורשימות לסטטיסטיקה
            total_pkts, game_pkts, total_bytes, udp_bytes, tcp_bytes = 0, 0, 0, 0, 0
            game_pkt_sizes = []  # רשימת גדלים של פקטות משחק (לצורך ממוצע)
            game_timestamps = []  # רשימת זמני הגעה של פקטות משחק (לצורך IAT)
            unique_ipv4 = set()  # רשימת כתובות IPv4 ייחודיות (המקור ל-35)

            # פתיחת קובץ ה-PCAP לקריאה פקטה אחרי פקטה
            with PcapReader(pcap_path) as reader:
                for pkt in reader:
                    total_pkts += 1  # עדכון מונה פקטות כללי
                    p_len = len(pkt)  # מדידת גודל הפקטה הנוכחית בבייטים
                    total_bytes += p_len  # עדכון סך הבייטים הכללי בקובץ

                    # א) ספירת IPv4 ייחודיים (לוגיקה של check_ips - מחזיר 35)
                    if pkt.haslayer(IP):  # אם הפקטה היא מסוג IPv4
                        for ip in [pkt[IP].src, pkt[IP].dst]:  # בדיקת המקור והיעד
                            if ip != "255.255.255.255":  # התעלמות מכתובת ה-Broadcast הכללית
                                unique_ipv4.add(ip)  # הוספה לסט (אם כבר קיים, לא ייווסף שוב)

                    # ב) זיהוי שיחות (Conversations): לוגיקה מקוד המקור (IPv4+IPv6 -> מחזיר 31)
                    if (pkt.haslayer(IP) or pkt.haslayer(IPv6)) and (pkt.haslayer(UDP) or pkt.haslayer(TCP)):
                        l = IP if pkt.haslayer(IP) else IPv6  # זיהוי שכבת ה-IP
                        pr = UDP if pkt.haslayer(UDP) else TCP  # זיהוי שכבת התעבורה

                        #  עדכון סטטיסטיקת פורטים עבור הדו"ח הסופי
                        for p in [pkt[pr].sport, pkt[pr].dport]:
                            if p not in global_port_stats:
                                global_port_stats[p] = {'bytes': 0, 'pkts': 1}
                            else:
                                global_port_stats[p]['pkts'] += 1
                            global_port_stats[p]['bytes'] += (p_len / 2)

                        # יצירת מזהה שיחה דו-כיווני: מיון הכתובות והפורטים בסדר קבוע (sorted)
                        # כך ששיחה מ-A ל-B ושיחה מ-B ל-A נחשבות כאותה שיחה בודדת
                        c_id = tuple(sorted([(pkt[l].src, pkt[pr].sport), (pkt[l].dst, pkt[pr].dport)]))
                        all_ip_convs.add(c_id)  # הוספה למאגר השיחות הכללי

                        if pkt.haslayer(UDP):  # אם מדובר בפרוטוקול UDP
                            udp_bytes += p_len  # הוספה למשקל הכולל של ה-UDP
                            udp_convs.add(c_id)  # הוספה למאגר שיחות ה-UDP

                            # ג) זיהוי שיחות משחק (המקור ל-1 המזוקק)
                            s_p, d_p = pkt[UDP].sport, pkt[UDP].dport  # שליפת פורט מקור ויעד
                            # בדיקה אם אחד מהם נמצא בטווח הפורטים של המחקר
                            if (p_start <= s_p <= p_end) or (p_start <= d_p <= p_end):
                                game_convs.add(c_id)  # הוספה למאגר שיחות המשחק
                                game_pkts += 1  # מונה פקטות משחק
                                game_pkt_sizes.append(p_len)  # שמירת הגודל לחישוב ממוצע
                                game_timestamps.append(float(pkt.time))  # שמירת זמן ההגעה המדויק
                                # שמירת הפורט הספציפי מהטווח שבאמת פעל
                                if p_start <= s_p <= p_end: game_ports.add(s_p)
                                if p_start <= d_p <= p_end: game_ports.add(d_p)

                        elif pkt.haslayer(TCP):  # אם מדובר ב-TCP
                            tcp_bytes += p_len  # הוספה למשקל הכולל של ה-TCP

            # חישוב ה-IAT (Inter-Arrival Time): הזמן הממוצע שעובר בין פקטה לפקטה
            avg_iat = 0
            if len(game_timestamps) > 1:
                # יצירת רשימה של המרווחים (זמן פקטה נוכחית פחות זמן פקטה קודמת)
                iats = [game_timestamps[i] - game_timestamps[i - 1] for i in range(1, len(game_timestamps))]
                # חישוב ממוצע והפיכה למילי-שניות (מכפילים ב-1000)
                avg_iat = (sum(iats) / len(iats)) * 1000

            # --- שלב 3: ריכוז כל הנתונים למילון סטטיסטי (stats) ---
            stats = {
                'folder': folder,  # שם התיקייה המנותחת
                'total_ip_convs': len(all_ip_convs),  # סה"כ שיחות IP דו-כיווניות (למשל 72)
                'total_udp_convs': len(udp_convs),  # סה"כ שיחות UDP (ה-31 המפורסם מ-Wireshark)
                'game_convs': len(game_convs),  # כמות שיחות המשחק (ה-1 המזוקק)
                'identified_ports': str(sorted(list(game_ports))),  # רשימת הפורטים שנמצאו בפועל
                'game_purity_pct': (game_pkts / total_pkts * 100) if total_pkts > 0 else 0,  # אחוז ה"טוהר"
                'purity_ratio': f"{game_pkts} / {total_pkts}",  # הצגה של "כמה מתוך כמה" פקטות
                'udp_pct': (udp_bytes / total_bytes * 100) if total_bytes > 0 else 0,  # אחוז ה-UDP מהנפח
                'tcp_pct': (tcp_bytes / total_bytes * 100) if total_bytes > 0 else 0,  # אחוז ה-TCP מהנפח
                'avg_iat_ms': avg_iat,  # זמן הגעה ממוצע (ה"דופק" של המשחק)
                'avg_pkt_size': (sum(game_pkt_sizes) / len(game_pkt_sizes)) if game_pkt_sizes else 0,  # גודל פקטה ממוצע
                'unique_ips': len(unique_ipv4),  # כמות כתובות IPv4 ייחודיות (ה-35 מה-Endpoints)
                'total_flows': legacy_total_flows  # המספר הישן והגבוה מה-NFStreamer (למשל 349)
            }

            # הוספת התוצאה של התיקייה הנוכחית לרשימת התוצאות הכללית
            results.append(stats)

            # --- כאן מתבצעת כתיבה חיה של הגיבוי לקובץ: network_analysis_backup.csv ---
            # המטרה: שמירת נתונים שורה-שורה כדי לאפשר המשכיות (Resume) אם הריצה תיעצר
            # header=not log_file.exists() מוודא שהכותרות ייכתבו רק פעם אחת בתחילת הקובץ
            pd.DataFrame([stats]).to_csv(log_file, mode='a', header=not log_file.exists(), index=False)

            # הדפסת אישור סיום מוצלח של התיקייה הנוכחית
            print("Done! ✅")

        except Exception as e:
            # במקרה של תקלה (קובץ פגום וכו') - מדפיסים את השגיאה וממשיכים הלאה
            print(f"Error: {e} ❌")

    # הפיכת כל רשימת התוצאות לטבלת Pandas סופית
    final_df = pd.DataFrame(results)

    # הגדרת נתיב לקובץ האקסל המעוצב והסופי
    xlsx_out = PRODUCTS_DIR / NETWORK_ANALYSIS_FILENAME

    # --- Michael: בניית דוח אקסל מרובה גיליונות (מבוסס על הגרסה המקורית) ---
    final_df = pd.DataFrame(results)

    # א. הכנת גיליון פורטים
    port_summary = pd.DataFrame([
        {'Port Number': k, 'Total Bytes': int(v['bytes']), 'Total Packets': v['pkts']}
        for k, v in global_port_stats.items()
    ]).sort_values('Total Packets', ascending=False)

    # ב. הכנת גיליון Insights (מזהה Anomalies לפי חוק ה-80% UDP)
    anomalies = final_df[final_df['udp_pct'] < 80]['folder'].tolist()
    dom_port = port_summary.iloc[0]['Port Number'] if not port_summary.empty else "N/A"

    insights_data = [
        ['Total Sessions', len(final_df), ".All recording sessions were processed and validated"],
        ['% Avg UDP', f"{final_df['udp_pct'].mean():.2f}%",
         ".High UDP percentage confirms primary game traffic capture"],
        ['Dominant Port', dom_port, ".The main communication channel for the game has been identified"],
        ['Avg Flows', round(final_df['total_flows'].mean(), 1),
         ".Flow density matches typical real-time game signatures"],
        ['Anomalies (<80% UDP)', len(anomalies), f"Flagged folders for exclusion: {', '.join(anomalies[:5])}..."]
    ]
    insights_df = pd.DataFrame(insights_data, columns=['Metric', 'Value', 'Researcher Insight'])

    # ג. כתיבה פיזית של כל הגיליונות (מחליף את השמירה הפשוטה שהייתה קודם)
    with pd.ExcelWriter(xlsx_out, engine='xlsxwriter') as writer:
        final_df.to_excel(writer, sheet_name='Detailed Data', index=False)
        writer.sheets['Detailed Data'].set_column('A:Z', 22)

        port_summary.to_excel(writer, sheet_name='Port Volume Summary', index=False)
        writer.sheets['Port Volume Summary'].set_column('A:C', 20)

        insights_df.to_excel(writer, sheet_name='Project Insights', index=False)
        writer.sheets['Project Insights'].set_column('A:C', 45)

    # --- Michael: ניקוי קובץ הגיבוי רק לאחר יצירת האקסל בהצלחה ---
    if log_file.exists():
        os.remove(log_file)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Cleanup: Backup file removed (Analysis Finalized).")

    # הדפסת סיכום סופי לטרמינל
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [SUCCESS] All Parity Requirements Met (Full Report Created).")
    return final_df

r'''
בלוק זה מגדיר את "ארגז הכלים" של המודלים - רשימת כל הפיצ'רים (תכונות) שישמשו לאימון.
הרשימה כוללת מדדי רשת גולמיים לצד מדדים סטטיסטיים שחושבו על פני חלון הזמן של 10 שניות.
'''

FEATURE_COLUMNS = [
            # --- תכונות גודל פקטה: כיוון שליחה מהמכשיר לשרת (Upload / Src2Dst) ---
            'src2dst_avg_pkt_size',        # הערך הגולמי של גודל הפקטה הממוצע בשנייה הנוכחית
            'src2dst_avg_pkt_size_mean',   # ממוצע גודל פקטה משוקלל עם דעיכה (על פני 10 שניות)
            'src2dst_avg_pkt_size_median', # חציון גודל הפקטה בחלון הזמן
            'src2dst_avg_pkt_size_std',    # סטיית תקן - מדד לתנודתיות ושינויים בגודל החבילות הנשלחות
            'src2dst_avg_pkt_size_min',    # הגודל המינימלי שנמדד בחלון
            'src2dst_avg_pkt_size_max',    # הגודל המקסימלי שנמדד בחלון (מזהה חבילות מידע גדולות וחריגות)

            # --- תכונות PPS (חבילות לשנייה): כיוון שליחה (Upload / Src2Dst) ---
            'src2dst_pps',        # קצב שליחת חבילות גולמי בשנייה האחרונה
            'src2dst_pps_mean',   # ממוצע PPS משוקלל עם דעיכה (נותן עדיפות למידע העדכני ביותר)
            'src2dst_pps_median', # חציון קצב השליחה ב-10 השניות האחרונות
            'src2dst_pps_std',    # מדד ליציבות קצב השליחה (Jitter בשכבת היישום)
            'src2dst_pps_min',    # קצב מינימלי שנרשם בחלון הזמן
            'src2dst_pps_max',    # קצב מקסימלי שנרשם (מזהה קפיצות עומס/Burstiness)

            # --- תכונות גודל פקטה: כיוון קבלה מהשרת למכשיר (Download / Dst2Src) ---
            'dst2src_avg_pkt_size',        # הערך הגולמי של גודל הפקטה בשנייה הנוכחית
            'dst2src_avg_pkt_size_mean',   # ממוצע משוקלל עם דעיכה של גודל הפקטה הנכנס
            'dst2src_avg_pkt_size_median', # חציון גודל הפקטה הנכנס
            'dst2src_avg_pkt_size_std',    # תנודתיות בגודל חבילות המידע הנכנסות מהשרת
            'dst2src_avg_pkt_size_min',    # גודל מינימלי נכנס
            'dst2src_avg_pkt_size_max',    # גודל מקסימלי נכנס

            # --- תכונות PPS (חבילות לשנייה): כיוון קבלה (Download / Dst2Src) ---
            'dst2src_pps',        # קצב קבלת חבילות גולמי בשנייה הנוכחית
            'dst2src_pps_mean',   # ממוצע PPS נכנס משוקלל (קריטי לזיהוי רצף נתונים מהשרת)
            'dst2src_pps_median', # חציון קצב הקבלה
            'dst2src_pps_std',    # מדד ליציבות זרם הנתונים הנכנס מהשרת
            'dst2src_pps_min',    # קצב קבלה מינימלי
            'dst2src_pps_max',    # קצב קבלה מקסימלי

            # --- תכונות יחס כיווניות (Direction Ratio) ---
            # מדד זה בוחן את האיזון בין העלאה להורדה, נתון חשוב בזיהוי פרוטוקולי משחק.
            'pkt_dir_ratio',        # היחס בין חבילות יוצאות לנכנסות בשנייה הנוכחית
            'pkt_dir_ratio_mean',   # ממוצע יחס הכיווניות המשוקלל לאורך 10 שניות
            'pkt_dir_ratio_median', # חציון יחס הכיווניות
            'pkt_dir_ratio_std',    # מדד ליציבות היחס בין כיווני התנועה
            'pkt_dir_ratio_min',    # הערך המינימלי של היחס בחלון
            'pkt_dir_ratio_max'     # הערך המקסימלי של היחס בחלון
]

r'''
תא זה מבצע את חילוץ הפיצ'רים תוך שימוש בהגדרות הגלובליות.
הוא משתמש ב-BPF_FILTER, WINDOW_SIZE ו-DECAY_RATE שהוגדרו בראש המחברת.
המטרה: יצירת וקטורי תכונות (Features) המייצגים את התנהגות הרשת בכל שנייה ושנייה.
'''


def weighted_average_decay(arr, r=DECAY_RATE):
    r'''
    חישוב ממוצע משוקלל עם דעיכה (Michael's Weighted Decay).
    היגיון: הנתונים האחרונים בחלון הזמן חשובים יותר מהנתונים הישנים לצורך חיזוי הפינג הנוכחי.
    r=0.5 (DECAY_RATE) קובע שכל דגימה אחורה מקבלת חצי מהמשקל של הדגימה שאחריה.
    '''
    if not (0 < r < 1): # וולידציה: הבטחה שקצב הדעיכה הוא שבר הגיוני. אם r לא בטווח (0,1), החישוב הסטטיסטי יאבד משמעות.
        raise ValueError("r must be between 0 and 1")

    if not arr: return 0  # אם המערך ריק, החזר 0 כדי למנוע שגיאת חישוב
    w, s, w_sum = 1.0, 0.0, 0.0  # אתחול משקולת התחלתית (1.0), סכום ערכים משוקלל וסכום משקולות
    # הפיכת המערך כדי להתחיל מהדגימה העדכנית ביותר (הסוף הופך להתחלה)
    arr = arr[::-1]
    for x in arr:  # מעבר על כל איבר במערך (מהחדש לישן)
        # בדיקה שהערך תקין ואינו NaN (נתון חסר)
        if x is not None and not (isinstance(x, float) and np.isnan(x)):
            s += w * x  # הוספת הערך מוכפל במשקולת שלו לסכום המצטבר
            w_sum += w  # צבירת סכום המשקולות לצורך נרמול (חלוקה בסוף)
        w *= r  # הקטנת המשקל עבור הדגימה הבאה (הישנה יותר) לפי קצב הדעיכה
    return s / w_sum if w_sum > 0 else 0  # החזרת הממוצע המשוקלל הסופי


def build_second_vectors(pcap_path):
    r'''
    מטרת הפונקציה: הפיכת קובץ הקלטת רשת (PCAP) לטבלת נתונים סטטיסטית ברזולוציה של שניה אחת.
    הפונקציה מחלצת פיצ'רים גולמיים שישמשו מאוחר יותר לאימון מודל ה-QoE.
    '''
    # ייבוא ספריות בתוך הפונקציה כדי לשפר ביצועים בהרצה מקבילית (Multiprocessing)
    from PingLatency import PingLatency
    #import numpy as np  # ספריית חישובים מתמטיים

    try:
        # אתחול הסטרימר - המנוע שקורא את הפקטות ומקבץ אותן לזרימות (Flows)
        streamer = NFStreamer(
            source=str(pcap_path),  # נתיב לקובץ ה-PCAP הנוכחי
            udps=[PingLatency()],  # הפעלת הפלאגין המותאם אישית שלנו למדידת השהייה
            bpf_filter=BPF_FILTER,  # סינון תעבורת המשחק בלבד (לפי פורטים)
            active_timeout=SAMPLE_DURATION,  # SAMPLE_DURATION=1: חיתוך המידע בדיוק כל שניה
            idle_timeout=SAMPLE_DURATION  # סגירת זרימות לא פעילות במהירות לסנכרון זמן אמת
        )

        # המרת תוצרי הסטרימר לטבלת Pandas (DataFrame) לעבודה נוחה
        df = streamer.to_pandas()

        # בדיקה האם הקובץ ריק, חסר או שהסינון לא מצא פקטות של המשחק
        if df is None or df.empty or "bidirectional_first_seen_ms" not in df.columns:
            return pd.DataFrame()

        # מציאת רגע תחילת המשחק במילי-שניות (Absolute Time)
        t0 = df["bidirectional_first_seen_ms"].min()

        # הגנה למקרה שהפונקציה min החזירה ערך לא תקין
        if pd.isna(t0): return pd.DataFrame()

        # יצירת ציר זמן יחסי (0, 1, 2...): הפרש מההתחלה חלקי 1000 להפיכה לשניות
        # שימוש ב-"Int64" מאפשר לטבלה להכיל ערכי NaN בלי לקרוס (בטיחות מעל הכל)
        df["pktIdx"] = ((df["bidirectional_first_seen_ms"] - t0) / 1000).astype(int)

        # שלב הזיקוק: מיון לפי זמן ונפח תעבורה (src2dst_bytes)
        df = df.sort_values(["pktIdx", "src2dst_bytes"], ascending=[True, False])

        # שמירה של שורה אחת בלבד לכל שניה - זו שמייצגת את הזרם הראשי של המשחק
        df = df.groupby("pktIdx").head(1).copy()

        # קביעת השניה כמזהה השורה (Index) לצורך הצמדה מדויקת של העמודות
        df = df.set_index("pktIdx")

        # יצירת טבלת הפלט החדשה (out) שתכיל רק את הפיצ'רים שמעניינים אותנו
        out = pd.DataFrame(index=df.index)

        # הכנת משתני עזר מנוקים  -  מילוי אפסים במקום נתונים חסרים (NaN)
        s_pkts = df["src2dst_packets"].fillna(0)  # כמות חבילות יוצאות
        d_pkts = df["dst2src_packets"].fillna(0)  # כמות חבילות נכנסות
        s_bytes = df["src2dst_bytes"].fillna(0)  # נפח בייטים יוצא
        d_bytes = df["dst2src_bytes"].fillna(0)  # נפח בייטים נכנס

        # חישוב משך הזמן האמיתי של הפעילות בתוך אותה שניה (Duration)
        # שימוש ב-clip(lower=1.0) מונע חלוקה באפס אם הזמן שנמדד קצר מדי
        s_dur = (df["src2dst_last_seen_ms"] - df["src2dst_first_seen_ms"]).clip(lower=1.0)
        d_dur = (df["dst2src_last_seen_ms"] - df["dst2src_first_seen_ms"]).clip(lower=1.0)

        # --- חישוב פיצ'רים מחקריים ---

        # 1. גודל פקטה ממוצע (כמה מידע יש בכל "חבילה" שנשלחת או מתקבלת)
        out["src2dst_avg_pkt_size"] = (s_bytes / s_pkts.clip(lower=1.0)).fillna(0)
        out["dst2src_avg_pkt_size"] = (d_bytes / d_pkts.clip(lower=1.0)).fillna(0)

        # 2. יחס כיווניות (Direction Ratio) - האם המשחק מעלה יותר מידע ממה שהוא מוריד?
        out["pkt_dir_ratio"] = (s_pkts / d_pkts.clip(lower=1.0)).fillna(0)

        # 3. PPS (Packets Per Second) - ה"דופק" של הרשת.
        # מחלקים בכמות המילי-שניות ומכפילים ב-1000 כדי לקבל קצב לשניה שלימה.
        out["src2dst_pps"] = (s_pkts / s_dur * 1000.0).fillna(0)
        out["dst2src_pps"] = (d_pkts / d_dur * 1000.0).fillna(0)

        # החזרת הטבלה המוכנה, והפיכת ה-pktIdx חזרה לעמודה רגילה לשימוש ב-rolling window
        return out.reset_index()

    except Exception as e:
        # אם קובץ PCAP ספציפי פגום, נדפיס אזהרה ונדלג עליו כדי לא לעצור את כל הריצה.
        print(f"⚠️ Error processing {pcap_path}: {e}")
        return pd.DataFrame()

# --- Michael: פונקציית משימה לביצוע העיבוד על סשן בודד במקביל ---
def _process_run_task(row_tuple):
    # הפונקציה מקבלת טאפל של (index, row) ומחזירה DataFrame של סשן מעובד
    idx, row = row_tuple  # פירוק הטאפל לאינדקס ולשורת המטא-דאטה
    pcap_path = RAW_DATA_PATH / row["folder"] / row["pcapng_file"]  # בניית הנתיב לקובץ ה-PCAP של הסשן
    if not pcap_path.exists(): return None  # דילוג במקרה שהקובץ חסר פיזית בדיסק

    sec_df = build_second_vectors(pcap_path)  # חילוץ הפיצ'רים הגולמיים (שנייה אחר שנייה)
    if sec_df.empty: return None  # דילוג אם לא חולצו נתונים תקינים מהקובץ

    # סנכרון זמנים: המרת הפינגים לציר זמן שמתחיל ב-0 עבור כל סשן בנפרד
    time_pairs = ast.literal_eval(row["time_value_pairs"])  # המרת מחרוזת המילוי מה-CSV למילון פייתון אמיתי
    start_hhmmss = int(row["folder"].split("_")[-1])  # חילוץ זמן ההתחלה של הסשן מתוך שם התיקייה
    # יצירת מפת פינגים: המרת זמן השעון לשניות יחסיות מתחילת המשחק
    ping_map = {hhmmss_to_seconds(int(t_str)) - hhmmss_to_seconds(start_hhmmss): v
                for t_str, v in time_pairs.items()}

    # מילוי "חורים" בציר הזמן כדי להבטיח רציפות של השנייה בחישובי החלון הרץ
    max_idx = max(sec_df["pktIdx"].max(), max(ping_map.keys() if ping_map else [0]))  # מציאת השנייה האחרונה בסשן
    all_idx = pd.DataFrame({"pktIdx": list(range(0, max_idx + 1))})  # יצירת רצף שניות מלא (למשל 0 עד 120)
    sec_df = all_idx.merge(sec_df, on="pktIdx", how="left")  # הצמדת הנתונים לרצף המלא (יצירת NaN בשניות חסרות)

    # חישוב הפיצ'רים המתקדמים בעזרת חלון רץ (Rolling)
    base_cols = ["src2dst_avg_pkt_size", "dst2src_avg_pkt_size", "dst2src_pps", "src2dst_pps", "pkt_dir_ratio"]
    rolling_df = pd.DataFrame({"pktIdx": sec_df["pktIdx"]})  # יצירת טבלה חדשה עבור הפיצ'רים המשוכללים

    # --- Michael Fix: הוספת שם התיקייה לכל שורה (חיוני לאבחון!) ---
    rolling_df["folder"] = row["folder"]  # הצמדת שם הריצה לכל שורת נתונים לזיהוי עתידי

    for col in base_cols:  # לולאה שעוברת על כל אחד מפיצ'רי הבסיס של הרשת
        r = sec_df[col].rolling(window=WINDOW_SIZE, min_periods=1)  # הגדרת חלון רץ של 10 שניות
        rolling_df[f"{col}"] = sec_df[col]  # שמירת הערך הגולמי של השנייה הנוכחית
        # חישוב הממוצע המשוקלל עם דעיכה בתוך החלון
        rolling_df[f"{col}_mean"] = r.apply(lambda s: weighted_average_decay(s.tolist()), raw=False)
        rolling_df[f"{col}_median"] = r.median()  # חישוב חציון (חסין מפני קפיצות רעש רגעיות)
        rolling_df[f"{col}_min"] = r.min()  # מציאת ערך המינימום ב-10 השניות האחרונות
        rolling_df[f"{col}_max"] = r.max()  # מציאת ערך המקסימום (מזהה עומסי שיא)
        rolling_df[f"{col}_std"] = r.std(ddof=0)  # חישוב סטיית תקן למדידת יציבות התעבורה

    # הדבקת הפינג (הלייבל) לכל וקטור פיצ'רים של אותה שנייה
    rolling_df["ping"] = rolling_df["pktIdx"].map(ping_map)  # הצמדת ערך הפינג הוויזואלי המתאים לשנייה

    # סינון: שומרים רק שורות שיש להן חלון מלא (10 שניות) ושיש להן לייבל (פינג) תקין
    final_run_df = rolling_df[(rolling_df["pktIdx"] >= WINDOW_SIZE - 1) & (rolling_df["ping"].notna())].copy()

    # --- Michael: ניקוי משתנים כבדים מהזיכרון בסיום המשימה כדי למנוע הצטברות ---
    del sec_df
    del rolling_df

    return final_run_df


def generate_training_data_main(meta_df, window_size=WINDOW_SIZE):
    r'''
    הפונקציה המרכזית: עוברת על כל הסשנים, מחלצת פיצ'רים ומצמידה להם את הפינג (Labels).
    מיישמת "חלון רץ" (Rolling Window) לחישוב מגמות וסטטיסטיקות.
    '''
    if USE_PARALLEL:  # אם המתג הוגדר כ-True בקומה 2
        print(f"⚡ Parallel Mode: Using {CORES_TO_USE} CPU workers (Joblib).")  # הודעה למשתמש על הרצה מקבילית
        # Michael: הרצה במקביל עם עדכון למסך בכל פעם שמשימות מסתיימות (verbose=10)
        results = Parallel(n_jobs=CORES_TO_USE, verbose=10)(
            delayed(_process_run_task)(item) for item in meta_df.iterrows()
        )
        all_dfs = [r for r in results if r is not None]
    else:  # Michael: מצב טורי יציב עם דיווח התקדמות חי
        print(f"🐢 Serial Mode: Processing folders one by one.")
        all_dfs = []
        # הפיכת ה-iterrows לרשימה כדי לדעת את האורך הכולל (לצורך ה-print)
        items = list(meta_df.iterrows())
        total_items = len(items)

        for idx, item in enumerate(items):
            folder_name = item[1]['folder']  # שליפת שם התיקייה מהשורת מטא-דאטה
            print(
                f"   [{datetime.now().strftime('%H:%M:%S')}] Feature extraction [{idx + 1}/{total_items}]: {folder_name}...",
                end=" ")

            res = _process_run_task(item)
            if res is not None:
                all_dfs.append(res)
                print("Done! ✅")
            else:
                print("Skipped/Empty ❌")

    # איחוד כל הטבלאות של כל הסשנים לטבלה אחת ענקית עבור אימון המודל
    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

r'''
התא הנוכחי מגדיר ומריץ תהליך של "חשיבות תכונות לפי תמורות" (Permutation Importance).
הוא משתמש במתג USE_PARALLEL_ML כדי להאיץ את החישובים ללא פגיעה בדיסק.

המטרה: להבין אילו מדדי רשת הם באמת הקריטיים ביותר עבור כל מודל.
השיטה: המערכת מערבבת בצורה אקראית עמודה מסוימת ובודקת כמה ביצועי המודל נפגעו. 
אם הפגיעה בביצועים גדולה - סימן שהפיצ'ר הזה קריטי למחקר.
'''

def top_features_per_model(
        df: pd.DataFrame,
        models_list,  # רשימה של צמדים: (שם המודל, אובייקט המודל)
        feature_cols,  # רשימת הפיצ'רים שיוזנו למודל
        target_col: str,  # שם עמודת המטרה (הלייבל)
        test_size: float = 0.2,  # אחוז הנתונים שיישמרו לבדיקה (20%)
        random_state: int = 42,  # הבטחת תוצאות עקביות בכל הרצה
        n_repeats: int = 10,  # כמה פעמים לערבב כל פיצ'ר לחישוב יציב
        top_k: int = 10  # כמה פיצ'רים מובילים להציג לכל מודל
):
    # הכנת הנתונים: המרת הפיצ'רים למספרי עשרוניים והמטרה למספרים שלמים
    X = df[feature_cols].astype("float32")
    y = df[target_col].astype(int)

    # שכבת הגנה: ביצוע Stratification (שמירה על יחס המחלקות) רק אם יש יותר ממחלקה אחת
    strat = y if y.nunique() > 1 else None

    # חלוקת בסיס הנתונים לסט אימון (80%) וסט בדיקה (20%)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=test_size,
        random_state=random_state,
        stratify=strat
    )

    # Michael: קביעת כמות הליבות לפי המתג הייעודי ל-ML
    current_n_jobs = CORES_TO_USE if USE_PARALLEL_ML else 1

    rows = []
    # מעבר על כל מודל ברשימה (למשל Random Forest, KNN וכו')
    for name, model in models_list:
        try:
            # Michael: הדפסה עם חיווי על מצב המקביליות
            print(
                f"   [{datetime.now().strftime('%H:%M:%S')}] Analyzing model: {name} (Parallel ML: {USE_PARALLEL_ML})...",
                end=" ")

            # שלב הלמידה: אימון המודל על נתוני האימון
            model.fit(X_train, y_train)

            # חישוב חשיבות התכונות: ערבוב אקראי של כל עמודה ובדיקת ההשפעה על הדיוק
            perm = permutation_importance(
                model,
                X_test,
                y_test,
                n_repeats=n_repeats,
                random_state=random_state,
                n_jobs=current_n_jobs  # שימוש במתג הדינמי
            )

            # ארגון התוצאות: יצירת סדרת נתונים המכילה את ממוצע החשיבות של כל פיצ'ר
            importances = pd.Series(perm.importances_mean, index=feature_cols)
            # בחירת הפיצ'רים המובילים לפי עוצמת ההשפעה שלהם
            top = importances.sort_values(ascending=False).head(top_k)

            for feat, val in top.items():
                rows.append({
                    "model": name,
                    "feature": feat,
                    "perm_importance_mean": float(val)
                })

            print("Done! ✅")

        except Exception as e:
            # טיפול בשגיאות במקרה ומודל מסוים לא הצליח לסיים את האימון
            rows.append({
                "model": name,
                "feature": "__ERROR__",
                "perm_importance_mean": np.nan
            })
            print(f"Failed! ❌ ({e})")

    out = pd.DataFrame(rows)
    # החזרת טבלה מסודרת המציגה לכל מודל את "עשרת הנבחרים" שלו
    return out.sort_values(["model", "perm_importance_mean"], ascending=[True, False])

r'''
תא זה מייצר את דו"ח ה-Consensus הצבעוני הסופי - גרסה מלאה.
התהליך כולל:
1. שקלול מודלים לפי קבוצות איכות (Tiers) - מתן משקל גבוה יותר למודלים חזקים.
2. יישום לוגיקת Consensus לזיהוי הפיצ'רים המשמעותיים ביותר באופן עקבי.
3. הפקת קובץ Excel הכולל טבלת זוכים (Winners) וטבלת משתתפים אחרים (Others).
'''
def calculate_scores_and_contributions(df):
    r'''
    חישוב הדירוג הפנימי והניקוד המשוקלל לכל פיצ'ר.
    כאן אנחנו הופכים את הדירוג (Rank) לנקודות: מקום ראשון מקבל 10 נקודות, מקום שני 9, וכן הלאה.
    '''
    df = df.copy()
    # דירוג הפיצ'רים בתוך כל מודל לפי עוצמת החשיבות שלהם
    df['rank'] = df.groupby('model')['perm_importance_mean'].rank(ascending=False, method='first').astype(int)
    # המרת הדירוג לניקוד (Points): רק ה-Top 10 מקבלים ניקוד
    df['points'] = df['rank'].apply(lambda r: max(0, 11 - r) if r <= 10 else 0)

    # הגדרת משקולות (Tiers): מודלים מתקדמים (Boosting) מקבלים משקל מלא (1.0),
    # בעוד מודלים פשוטים יותר כמו Random Forest מקבלים משקל מעט נמוך יותר (0.8).
    weights = {'XGBoost': 1.0, 'CatBoost': 1.0, 'LGBM': 1.0, 'RF': 0.8}
    # חישוב התרומה הסופית של כל מודל לציון של הפיצ'ר
    df['contribution'] = df.apply(lambda row: row['points'] * weights.get(row['model'], 0.6), axis=1)

    # סיכום כל התרומות מכל המודלים לכדי ציון סופי אחד לכל פיצ'ר
    final_scores = df.groupby('feature')['contribution'].sum().to_dict()
    return final_scores, df


def get_stats_with_logic(df, final_scores):
    r'''
    חישוב סטטיסטיקות הופעה וזיהוי זוכים לפי לוגיקת ה-Consensus המלאה.
    פיצ'ר נחשב "Winner" רק אם הוא הופיע במיקומים גבוהים אצל מספר מודלים שונים.
    '''
    stats_list = []
    features = df['feature'].unique()
    for feat in features:
        feat_data = df[df['feature'] == feat]
        ranks = feat_data['rank'].tolist()
        s = {
            'feature': feat,
            '1st': sum(1 for r in ranks if r == 1),  # כמה פעמים הגיע למקום ה-1
            '2nd': sum(1 for r in ranks if r == 2),  # כמה פעמים הגיע למקום ה-2
            '3rd': sum(1 for r in ranks if r == 3),  # כמה פעמים הגיע למקום ה-3
            'top3': sum(1 for r in ranks if r <= 3),  # סה"כ הופעות בשלישייה הפותחת
            'top5': sum(1 for r in ranks if r <= 5),  # סה"כ הופעות בחמישייה הפותחת
            'else': sum(1 for r in ranks if r > 3),  # הופעות מחוץ לטופ 3
            'total': len(ranks),  # סך כל המודלים שזיהו את הפיצ'ר
            'final_score': round(final_scores.get(feat, 0), 2)
        }

        # לוגיקת Winner (גרסה 2.1): שילוב של מיקומים גבוהים וכמות מודלים.
        # Winner הוא פיצ'ר שהופיע לפחות פעמיים בטופ 3, או פעם בטופ 3 ו-3 פעמים בטופ 5, וכו'.
        is_winner = (s['top3'] >= 2) or (s['top3'] >= 1 and s['top5'] >= 3) or (s['top3'] >= 1 and s['total'] >= 4)
        if not is_winner:
            # מבחן עקביות נוסף: האם הפיצ'ר הופיע בטופ N לפחות N פעמים
            for n in range(2, 9):
                if sum(1 for r in ranks if r <= n) >= n:
                    is_winner = True;
                    break
        s['is_winner'] = is_winner
        stats_list.append(s)
    return stats_list


def generate_full_color_coded_report():
# הפונקציה המרכזית - מייצרת את קובץ האקסל המלא הכולל עיצובים, צבעים וחלוקה לקטגוריות

    # שימוש בתוצרי השלב הקודם (CSV של חשיבות הפיצ'רים)
    input_csv = PRODUCTS_DIR / IMPORTANCE_FILENAME
    output_xlsx = PRODUCTS_DIR / REPORT_FILENAME

    if not input_csv.exists():
        return print(f"❌ Error: Could not find CSV at {input_csv}")

    # טעינה ועיבוד הנתונים
    raw_df = pd.read_csv(input_csv)
    final_scores, df_processed = calculate_scores_and_contributions(raw_df)
    all_stats = get_stats_with_logic(df_processed, final_scores)

    # פיצול הפיצ'רים לשתי קבוצות: "הזוכים הגדולים" וכל השאר
    winners = sorted([s for s in all_stats if s['is_winner']], key=lambda x: x['final_score'], reverse=True)
    others = sorted([s for s in all_stats if not s['is_winner']], key=lambda x: x['final_score'], reverse=True)

    # יצירת מפה של צבעים ואותיות (A, B, C...) עבור הזוכים כדי להקל על הזיהוי בגרפים עתידיים
    palette = ["FFFF00", "00FF00", "00FFFF", "FF00FF", "FFA500", "FFC0CB", "ADFF2F", "FFD700", "00BFFF", "F08080",
               "90EE90", "DDA0DD"]
    mapping = {s['feature']: {"letter": chr(65 + i), "color": palette[i % len(palette)]} for i, s in enumerate(winners)}

    # בניית קובץ ה-Excel בעזרת openpyxl
    wb = Workbook()
    ws = wb.active
    ws.title = "Consensus Analysis V5"

    # 1. יצירת הטבלה הראשית: מראה איך כל מודל דירג את הפיצ'רים שלו
    ws.append(["Model", "Pos", "Feature (Coded)", "Importance Score", "Score Contribution"])
    for cell in ws[1]: cell.font = Font(bold=True); cell.alignment = Alignment(horizontal="center")

    for _, row in df_processed.iterrows():
        feat = row['feature']
        # הצגת האות המקודדת עבור זוכים, או שם הפיצ'ר המלא לאחרים
        display = mapping[feat]['letter'] if feat in mapping else feat
        ws.append([row['model'], row['rank'], display, row['perm_importance_mean'], round(row['contribution'], 1)])
        curr = ws.max_row
        ws.cell(row=curr, column=2).alignment = Alignment(horizontal="center")
        ws.cell(row=curr, column=5).alignment = Alignment(horizontal="center")
        # צביעת התא במידה והפיצ'ר הוא Winner
        if feat in mapping:
            cell = ws.cell(row=curr, column=3)
            cell.fill = PatternFill(start_color=mapping[feat]['color'], end_color=mapping[feat]['color'],
                                    fill_type="solid")
            cell.font = Font(bold=True);
            cell.alignment = Alignment(horizontal="center")

    # 2. בניית המקרא (Legend) בצד ימין של הגיליון
    start_col = 7
    legend_headers = ["Letter", "Feature Name", "1st", "2nd", "3rd", "else", "Total", "FINAL SCORE"]
    for i, h in enumerate(legend_headers):
        cell = ws.cell(row=1, column=start_col + i, value=h);
        cell.font = Font(bold=True)

    cur_row = 2
    # כתיבת רשימת הזוכים (Winners) עם כל הסטטיסטיקות שלהם
    for s in winners:
        info = mapping[s['feature']]
        ws.cell(row=cur_row, column=start_col, value=info['letter']).fill = PatternFill(start_color=info['color'],
                                                                                        end_color=info['color'],
                                                                                        fill_type="solid")
        ws.cell(row=cur_row, column=start_col).alignment = Alignment(horizontal="center")
        ws.cell(row=cur_row, column=start_col + 1, value=s['feature'])
        for i, key in enumerate(['1st', '2nd', '3rd', 'else', 'total']):
            ws.cell(row=cur_row, column=start_col + 2 + i, value=s[key])
        ws.cell(row=cur_row, column=start_col + 7, value=s['final_score']).font = Font(bold=True)
        cur_row += 1

    # כתיבת רשימת המשתתפים האחרים (Other Participants) - פיצ'רים שלא עברו את סף ה-Consensus
    cur_row += 2
    ws.cell(row=cur_row, column=start_col + 1, value="Other Participants").font = Font(bold=True)
    cur_row += 1
    for s in others:
        ws.cell(row=cur_row, column=start_col + 1, value=s['feature'])
        for i, key in enumerate(['1st', '2nd', '3rd', 'else', 'total']):
            ws.cell(row=cur_row, column=start_col + 2 + i, value=s[key])
        ws.cell(row=cur_row, column=start_col + 7, value=s['final_score'])
        cur_row += 1

    # --- כאן נוצר דוח הקונצנזוס הצבעוני והסופי: Color_Coded_...xlsx ---
    # פונקציה זו קוראת את נתוני ה-IMPORTANCE_FILENAME ומעצבת אותם לפי לוגיקת ה-Consensus
    wb.save(output_xlsx)
    print(f"✅ Full color-coded report saved to: {output_xlsx}")

# ==============================================================================
# קומה 4: המנוע הראשי (Execution Loop)
# ==============================================================================

def main():
    print(f"🚀 [BACKEND] Starting Full Pipeline for {DATA_SUBFOLDER}")
    print("-" * 50)

    # 1. יצירת מטא-דאטה (05)
    print("\n[Step 1/5] Extracting Metadata...")
    metadata = generate_metadata_live(RAW_DATA_PATH)
    ########################################### Start add for validation
    # ==========================================================================
    # --- Michael's Validation Phase ---
    # ==========================================================================
    # הגדרת הנתיב לתיקיית הדוחות החדשה בתוך תיקיית התוצרים הקיימת
    VALIDATION_DIR = PRODUCTS_DIR / "Validation_Reports"

    # יצירה פיזית של התיקייה על הדיסק (exist_ok=True מונע שגיאה אם היא כבר קיימת)
    os.makedirs(VALIDATION_DIR, exist_ok=True)

    # ספירת כמות השורות בטבלת המטא-דאטה כדי לדעת על כמה סשנים אנחנו רצים
    total_sessions = len(metadata)

    # הדפסת פתיח למסך עם כמות הסשנים הכוללת שנמצאה בתיקייה
    print(f"\n🧪 [Validation] Running integrity check on {total_sessions} sessions...")

    # לולאה שעוברת שורה-שורה על הטבלה (i הוא המונה, row מכיל את נתוני הסשן)
    for i, row in metadata.iterrows():

        # שליפת שם התיקייה הנוכחית (למשל run_1) מתוך עמודת folder
        f_name = row['folder']

        # בניית הנתיב המלא לקובץ ה-PCAP (הפיכה לסטרינג לצורך ספריית הסטרימר)
        pcap_p = str(RAW_DATA_PATH / f_name / row['pcapng_file'])

        # הגדרת שם קובץ האקסל שייווצר עבור הסשן הזה בתוך תיקיית הדוחות
        excel_out = VALIDATION_DIR / f"Validation_{f_name}.xlsx"

        # הדפסת סטטוס התקדמות חי למסך: [מספר נוכחי / סך הכל] ושם התיקייה
        print(f"   [{i + 1}/{total_sessions}] Generating Excel Report: {f_name}...", end=" ", flush=True)

        # ניסיון הרצה בתוך בלוק הגנה (try) כדי שתקלה בקובץ אחד לא תעצור את הכל
        try:
            # פתיחת מנוע כתיבה לאקסל שמאפשר לשמור כמה טבלאות (גיליונות) בקובץ אחד
            with pd.ExcelWriter(excel_out, engine='xlsxwriter') as writer:

                # --- מצב 1: Full_Pipeline (הכול פעיל - בדיוק כמו בקוד הראשי) ---
                s1 = NFStreamer(source=pcap_p,
                                udps=[PingLatency()],
                                bpf_filter=BPF_FILTER,
                                active_timeout=SAMPLE_DURATION,
                                idle_timeout=SAMPLE_DURATION)
                s1.to_pandas().to_excel(writer, sheet_name='Full_Pipeline_Seconds', index=False)

                # --- מצב 2: Raw_No_Filter (הצגת הכל מהכל - ללא סינון וללא חיתוך זמן) ---
                s2 = NFStreamer(source=pcap_p,
                                udps=[PingLatency()],
                                # bpf_filter=BPF_FILTER,
                                # active_timeout=SAMPLE_DURATION,
                                # idle_timeout=SAMPLE_DURATION
                                )
                s2.to_pandas().to_excel(writer, sheet_name='Raw_No_Filter', index=False)

                # --- מצב 3: Filter_Only (רק פילטר הפורטים - ללא חיתוך זמן) ---
                s3 = NFStreamer(source=pcap_p,
                                udps=[PingLatency()],
                                bpf_filter=BPF_FILTER,
                                # active_timeout=SAMPLE_DURATION,
                                # idle_timeout=SAMPLE_DURATION
                                )
                s3.to_pandas().to_excel(writer, sheet_name='Filter_Only_Total', index=False)

            # הדפסת אישור סיום מוצלח עבור המשחק הנוכחי
            print("Done! ✅")

        # תפיסת שגיאות (כמו קובץ PCAP פגום או חסר) והדפסת הודעת אזהרה
        except Exception as e:
            print(f"Failed! ❌ (Error: {e})")

    # הדפסת סיכום סופי המציין שהפקת כל הדוחות הושלמה והיכן הם נמצאים
    print(f"\n✨ [Validation Success] All {total_sessions} reports created in: {VALIDATION_DIR.name}")

    # הדפסת קו מפריד ויזואלי לסיום הבלוק בטרמינל
    print("-" * 50)

    ########################################### End add for validation

    # --- כאן נוצר הקובץ: metadata_results_auto.csv ---
    # הנתונים עבורו מגיעים מהפונקציה generate_metadata_live
    metadata.to_csv(PRODUCTS_DIR / METADATA_FILENAME, index=False)

    # 2. ניתוח רשת ודיוק Wireshark (10)
    print("\n[Step 2/5] Running Network Analysis (Ironclad)...")
    run_network_exploration()

    # 3. חילוץ פיצ'רים וחלון רץ (18)
    print("\n[Step 3/5] Extracting Feature Vectors...")
    training_df = generate_training_data_main(metadata)
    # ניקוי PPS וסינון
    training_df = training_df[(training_df["dst2src_pps"] < 1000) & (training_df["src2dst_pps"] < 1000)]
    # --- כאן נוצר הקובץ: final_training_features.csv ---
    # הנתונים עבורו חולצו, עובדו ואוחדו על ידי הפונקציה generate_training_data_main
    training_df.to_csv(PRODUCTS_DIR / FEATURES_FILENAME, index=False)

    # 4. הרצת חשיבות פיצ'רים
    print("\n[Step 4/5] Running Machine Learning Importance...")
    # הכנת הלייבלים
    # שימוש ב-.get(..., 0) כדי שאם הדירוג יחזיר ערך לא צפוי, נקבל 0 והשורה תסונן מיד אחר כך
    training_df['y'] = training_df['ping'].apply(to_qoe_class_zero)
    training_df = training_df[training_df['y'] > 0].copy() # סינון שורות לא תקינות (שבהן הדירוג נכשל והחזיר 0) כדי למנוע מחלקות שליליות
    training_df['y0'] = training_df['y'] - 1

    models_list = make_models(n_classes=3, knn_k=3, knn_weights='uniform', knn_metric='minkowski')
    if not INCLUDE_SVM: models_list = [m for m in models_list if m[0] != 'SVM']

    imp_df = top_features_per_model(df=training_df, models_list=models_list, feature_cols=FEATURE_COLUMNS, target_col="y0")
    # --- כאן נוצר הקובץ: feature_importance_results.csv ---
    # הנתונים עבורו חושבו על ידי הפונקציה top_features_per_model
    imp_df.to_csv(PRODUCTS_DIR / IMPORTANCE_FILENAME, index=False)

    # 5. יצירת דו"ח קונצנזוס צבעוני (36)
    print("\n[Step 5/5] Generating Color-Coded Consensus Report...")
    generate_full_color_coded_report()

    # --- Michael: Final Archiving Strategy ---
    # לאחר שכל הריצות הסתיימו בהצלחה, אנחנו משנים את שם קובץ הפיצ'רים לשם סופי עם חותמת זמן.
    timestamp_id = int(time.time())
    final_archive_name = f"window_{WINDOW_SIZE}_{timestamp_id}.csv"

    old_path = PRODUCTS_DIR / FEATURES_FILENAME
    new_path = PRODUCTS_DIR / final_archive_name

    if old_path.exists():
        try:
            os.rename(old_path, new_path)
            print(f"\n📦 Archive Complete: '{old_path.name}' renamed to '{new_path.name}'")
        except Exception as e:
            print(f"⚠️ Warning: Could not archive file: {e}")

    # --- Michael: Global Execution Timer End & Summary ---
    end_time = time.time()
    total_duration_seconds = end_time - start_time

    # חישוב שעות, דקות ושניות מהתוצאה הכוללת
    hours, rem = divmod(total_duration_seconds, 3600)
    minutes, seconds = divmod(rem, 60)

    print("-" * 40)
    print(f"🏁 Overall Execution Finished at: {datetime.now().strftime('%H:%M:%S')}")
    print(f"⏱️ Total Runtime: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")
    print("-" * 40)

    print("\n" + "=" * 50)
    print(f"✅ [SUCCESS] Backend Pipeline Completed at {datetime.now().strftime('%H:%M:%S')}")
    print(f"📂 All products are waiting in: {PRODUCTS_DIR}")
    print("=" * 50)

if __name__ == "__main__":
    main()
