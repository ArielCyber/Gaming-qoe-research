'''
שם הקובץ: cnn_dataset_generator_V1_gm.py
---------------------------------
הסבר: יצירת Dataset לאימון רשת נוירונים מתוך 2,641 התמונות המתויגות.

מה הקוד עושה:
1. סורק את תיקיית all_new_pic.
2. מחלץ את הפינג האמיתי משם הקובץ (Ground Truth).
3. משתמש במסכות צבע כדי למצוא את מיקום הספרות.
4. גוזר כל ספרה בנפרד ושומר אותה בתיקייה המתאימה (0-9) תחת training_data.
'''

import cv2
import numpy as np
import re
import sys
from pathlib import Path

# הגדרות
DIGIT_SIZE = (40, 64)
BASE_DIR = Path(__file__).resolve().parent
SOURCE_DIR = BASE_DIR / "all_new_pic"
OUTPUT_DIR = BASE_DIR / "training_data"
RE_PING = re.compile(r"Ping_(\d+)")

def get_masks(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return {
        "white": cv2.inRange(hsv, np.array([0, 0, 180]), np.array([180, 50, 255])),
        "yellow": cv2.inRange(hsv, np.array([15, 100, 100]), np.array([35, 255, 255])),
        "red": cv2.bitwise_or(cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255])),
                              cv2.inRange(hsv, np.array([160, 100, 100]), np.array([180, 255, 255])))
    }

def generate_dataset():
    if not SOURCE_DIR.exists():
        print(f"Error: Source folder {SOURCE_DIR} not found.")
        return

    # יצירת תיקיות 0-9
    for i in range(10):
        (OUTPUT_DIR / str(i)).mkdir(parents=True, exist_ok=True)

    images = list(SOURCE_DIR.glob("*.png"))
    print(f"Starting to process {len(images)} images...")

    digit_counts = {i: 0 for i in range(10)}
    total_extracted = 0

    for img_p in images:
        # חילוץ הפינג משם הקובץ
        match = RE_PING.search(img_p.name)
        if not match: continue
        
        truth_ping = match.group(1)
        img = cv2.imread(str(img_p))
        if img is None: continue
        
        masks = get_masks(img)
        
        # אנחנו מחפשים באיזו מסכה כמות הספרות מתאימה לפינג המתויג
        for color, mask in masks.items():
            num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
            components = []
            for i in range(1, num_labels):
                if stats[i, cv2.CC_STAT_AREA] > 8: # סף נמוך כדי לתפוס הכל
                    components.append(stats[i])
            
            components = sorted(components, key=lambda x: x[cv2.CC_STAT_LEFT])
            
            # אם מצאנו בדיוק את כמות הספרות שבפינג - גוזרים ושומרים
            if len(components) == len(truth_ping):
                for i, char in enumerate(truth_ping):
                    c = components[i]
                    digit_crop = mask[c[1]:c[1]+c[3], c[0]:c[0]+c[2]]
                    digit_norm = cv2.resize(digit_crop, DIGIT_SIZE)
                    
                    save_path = OUTPUT_DIR / char / f"{img_p.stem}_d{i}.png"
                    cv2.imwrite(str(save_path), digit_norm)
                    digit_counts[int(char)] += 1
                    total_extracted += 1
                break # מצאנו את הצבע הנכון, עוברים לתמונה הבאה

    print("\n" + "="*40)
    print("      DATASET GENERATION SUMMARY      ")
    print("="*40)
    for d in range(10):
        print(f"Digit {d}: {digit_counts[d]} samples")
    print(f"\nTotal digits extracted: {total_extracted}")
    print(f"Data saved in: {OUTPUT_DIR}")
    print("="*40)

if __name__ == "__main__":
    generate_dataset()
