'''
שם הקובץ: ping_diagnostic_V2_gm.py
---------------------------------
הסבר: סקריפט לאבחון תיקייה שלמה. הוא סורק את כל התמונות ומציג דו"ח
של כל הספרות שקיבלו ציון נמוך מהסף (0.75).

מה הקוד עושה:
1. עובר על כל קבצי ה-PNG בתיקייה שניתנה.
2. מחשב את ציון ההתאמה (Confidence) לכל ספרה בכל תמונה.
3. מדפיס דו"ח של "המקרים הקשים" - אלו שקיבלו ציון בין 0.50 ל-0.78.

איך משתמשים:
python3 ping_diagnostic_V2_gm.py ./117_Relevant_Picture

דוגמת הרצה:
michael@michael-VirtualBox:~/Documents/ping_extractor$ python3 ping_diagnostic_V2_gm.py ./117_Relevant_Picture
'''

import cv2
import numpy as np
import sys
from pathlib import Path

DIGIT_SIZE = (40, 64)
TEMPLATES_DIR = Path("digits_font/0_9")

def load_all_templates():
    templates = {i: [] for i in range(10)}
    if not TEMPLATES_DIR.exists(): return templates
    for i in range(10):
        folder = TEMPLATES_DIR / str(i)
        if folder.exists():
            for p in folder.glob("*.png"):
                t = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
                if t is not None:
                    templates[i].append(cv2.resize(t, DIGIT_SIZE))
    return templates

def run_diagnostic_batch(folder_path):
    templates = load_all_templates()
    images = sorted(list(Path(folder_path).glob("*.png")))
    
    print(f"\n{'Image Name':<40} | {'Pos':<3} | {'Best':<4} | {'Score':<6} | {'Status'}")
    print("-" * 80)

    for img_p in images:
        img = cv2.imread(str(img_p))
        if img is None: continue
        
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        # בודק את כל המסכות כדי למצוא את הספרות
        mask_w = cv2.inRange(hsv, np.array([0, 0, 180]), np.array([180, 50, 255]))
        mask_y = cv2.inRange(hsv, np.array([15, 80, 80]), np.array([40, 255, 255]))
        mask_r = cv2.bitwise_or(cv2.inRange(hsv, np.array([0, 100, 80]), np.array([10, 255, 255])),
                                cv2.inRange(hsv, np.array([160, 100, 80]), np.array([180, 255, 255])))
        
        full_mask = cv2.bitwise_or(mask_w, cv2.bitwise_or(mask_y, mask_r))
        num_labels, _, stats, _ = cv2.connectedComponentsWithStats(full_mask)
        components = sorted([stats[i] for i in range(1, num_labels) if stats[i, cv2.CC_STAT_AREA] > 10], 
                            key=lambda x: x[cv2.CC_STAT_LEFT])

        for idx, c in enumerate(components):
            digit_crop = cv2.resize(full_mask[c[1]:c[1]+c[3], c[0]:c[0]+c[2]], DIGIT_SIZE)
            best_val, max_score = -1, -1
            
            for d, t_list in templates.items():
                for t in t_list:
                    res = cv2.matchTemplate(digit_crop, t, cv2.TM_CCOEFF_NORMED)
                    score = cv2.minMaxLoc(res)[1]
                    if score > max_score:
                        max_score, best_val = score, d
            
            # אנחנו מדפיסים רק מקרים "מעניינים" (גבוליים או נכשלים)
            if max_score < 0.80:
                status = "FAIL" if max_score < 0.75 else "MARGINAL"
                print(f"{img_p.name[:40]:<40} | {idx+1:<3} | {best_val:<4} | {max_score:.3f} | {status}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_diagnostic_batch(sys.argv[1])
    else:
        print("Usage: python3 ping_diagnostic_V2_gm.py <folder_path>")
