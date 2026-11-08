# filename: template_generator_V2_gm.py

import cv2
import numpy as np
import re
from pathlib import Path

# --- הגדרות ---
DIGIT_SIZE = (40, 64) 
OUTPUT_DIR = Path("digits_font")
FAILED_DIR = Path("failed_generation")
RE_PING_VALUE = re.compile(r"Ping_(\d+)")

def get_digit_masks(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # התאמת טווחים לרזולוציה 151x97
    mask_white = cv2.inRange(hsv, np.array([0, 0, 160]), np.array([180, 60, 255]))
    mask_yellow = cv2.inRange(hsv, np.array([15, 80, 80]), np.array([40, 255, 255]))
    mask_red1 = cv2.inRange(hsv, np.array([0, 100, 80]), np.array([10, 255, 255]))
    mask_red2 = cv2.inRange(hsv, np.array([160, 100, 80]), np.array([180, 255, 255]))
    
    combined = cv2.bitwise_or(mask_white, mask_yellow)
    combined = cv2.bitwise_or(combined, mask_red1)
    combined = cv2.bitwise_or(combined, mask_red2)
    
    kernel = np.ones((2,2), np.uint8)
    combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel)
    return combined

def segment_digits(img):
    mask = get_digit_masks(img)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    
    components = []
    for i in range(1, num_labels):
        x, y, w, h, area = stats[i]
        aspect_ratio = h / float(w)
        
        # התאמה למידות 151x97: ספרות בד"כ בגובה 30-70 פיקסלים
        if 0.8 < aspect_ratio < 4.0 and 15 < h < 90 and area > 20:
            components.append((x, y, w, h))
            
    components.sort(key=lambda c: c[0])
    
    digit_images = []
    for x, y, w, h in components:
        digit_crop = mask[y:y+h, x:x+w]
        digit_norm = cv2.resize(digit_crop, DIGIT_SIZE, interpolation=cv2.INTER_AREA)
        digit_images.append(digit_norm)
        
    return digit_images, mask

def process_labeled_folder(input_path):
    input_path = Path(input_path)
    if not input_path.exists(): return

    FAILED_DIR.mkdir(exist_ok=True)
    for i in range(10): (OUTPUT_DIR / str(i)).mkdir(parents=True, exist_ok=True)

    total_count = 0
    img_files = sorted(list(input_path.glob("*.png")))
    
    for img_path in img_files:
        match = RE_PING_VALUE.search(img_path.name)
        if not match: continue
            
        truth_value = match.group(1)
        img = cv2.imread(str(img_path))
        if img is None: continue
        
        digits, full_mask = segment_digits(img)
        
        if len(digits) == len(truth_value):
            for char, digit_img in zip(truth_value, digits):
                out_name = f"gen_{total_count}.png"
                cv2.imwrite(str(OUTPUT_DIR / char / out_name), digit_img)
                total_count += 1
        else:
            # שמירת תמונה שנכשלה לדיבאג ויזואלי
            cv2.imwrite(str(FAILED_DIR / f"fail_{len(digits)}_exp_{len(truth_value)}_{img_path.name}"), full_mask)

    print(f"Summary: Created {total_count} templates. Failures saved in '{FAILED_DIR}'")

if __name__ == "__main__":
    import sys
    process_labeled_folder(sys.argv[1] if len(sys.argv) > 1 else "./117_Relevant_Picture")

# דוגמת הרצה:
# python3 template_generator_V2_gm.py ./117_Relevant_Picture
