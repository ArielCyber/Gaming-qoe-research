'''
שם הקובץ: template_refiner_V5_gm.py
---------------------------------
הסבר: גרסת הלמידה המתקדמת ביותר הכוללת דוח סינון מפורט.

מה חדש ב-V5:
1. ניהול יומן דחיות: כל תמונה שנדחית נרשמת עם סיבת הדחייה הספציפית.
2. דוח סיום מפורט: מציג בדיוק אילו תמונות לא נכנסו למאגר ולמה.
3. מבחני איכות V4: Solidity, Density ו-Aspect Ratio למניעת "333/999".

דוגמת הרצה:
michael@michael-VirtualBox:~/Documents/ping_extractor$ python3 template_refiner_V5_gm.py
'''

import cv2
import numpy as np
import re
from pathlib import Path

DIGIT_SIZE = (40, 64)
BASE_DIR = Path(__file__).resolve().parent
UNKNOWN_DIR = BASE_DIR / "unknown_candidates"
OUTPUT_BASE = BASE_DIR / "digits_font" / "0_9"
RE_PING = re.compile(r"Ping_(\d+)")

def check_digit_quality(crop):
    """בודק איכות ומחזיר (True/False, סיבה)"""
    h, w = crop.shape
    white_pixels = cv2.countNonZero(crop)
    density = white_pixels / (h * w)
    aspect_ratio = h / w

    if density < 0.20: return False, "Low Density (Too empty)"
    if density > 0.65: return False, "High Density (Too solid/Block)"
    if aspect_ratio < 1.1 or aspect_ratio > 3.2: return False, "Invalid Shape (Not a vertical digit)"

    contours, _ = cv2.findContours(crop, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours: return False, "No Contours"
    
    cnt = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(cnt)
    hull = cv2.convexHull(cnt)
    hull_area = cv2.contourArea(hull)
    
    if hull_area == 0: return False, "Zero Hull Area"
    solidity = float(area) / hull_area
    
    if solidity < 0.45: return False, f"Low Solidity ({solidity:.2f}) - Likely Noise"

    return True, "OK"

def refine():
    if not UNKNOWN_DIR.exists():
        print("unknown_candidates folder not found.")
        return

    stats = {"added": 0, "rejected": []}
    
    for img_path in UNKNOWN_DIR.glob("*.png"):
        match = RE_PING.search(img_path.name)
        if not match: continue
        
        truth_value = match.group(1)
        img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)
        _, mask = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # ניקוי רעשים פיזי
        kernel = np.ones((2,2), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        num_labels, labels, cc_stats, _ = cv2.connectedComponentsWithStats(mask)
        components = []
        for i in range(1, num_labels):
            if cc_stats[i, cv2.CC_STAT_HEIGHT] > 12:
                components.append(cc_stats[i])
        
        components = sorted(components, key=lambda c: c[cv2.CC_STAT_LEFT])
        
        # בדיקה 1: כמות ספרות תואמת לשם הקובץ
        if len(components) != len(truth_value):
            stats["rejected"].append((img_path.name, f"Count mismatch: found {len(components)}, expected {len(truth_value)}"))
            continue

        temp_storage = []
        is_file_ok = True
        
        for i, char in enumerate(truth_value):
            c = components[i]
            digit_crop = mask[c[1]:c[1]+c[3], c[0]:c[0]+c[2]]
            
            is_ok, reason = check_digit_quality(digit_crop)
            if is_ok:
                digit_norm = cv2.resize(digit_crop, DIGIT_SIZE)
                temp_storage.append((char, digit_norm))
            else:
                is_file_ok = False
                stats["rejected"].append((img_path.name, f"Digit {char} failed: {reason}"))
                break
        
        if is_file_ok and len(temp_storage) == len(truth_value):
            for char, digit_norm in temp_storage:
                out_dir = OUTPUT_BASE / char
                out_dir.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(out_dir / f"v5_refined_{img_path.stem}_{i}.png"), digit_norm)
                stats["added"] += 1
            img_path.unlink() # מוחק רק אם הכל עבר בהצלחה

    # הדפסת דוח סיום
    print("\n" + "="*50)
    print("      REFINER V5 - QUALITY REPORT      ")
    print("="*50)
    print(f"Successfully added: {stats['added']} templates")
    print(f"Rejected images:    {len(stats['rejected'])}")
    
    if stats["rejected"]:
        print("\nDetails of rejected images:")
        for name, reason in stats["rejected"]:
            print(f"  - {name}: {reason}")
    print("="*50 + "\n")

if __name__ == "__main__":
    refine()
