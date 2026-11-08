'''
שם הקובץ: cloud_labeler_V1_gm.py
---------------------------------
הסבר: שימוש ב-Google Cloud Vision API לתיוג אוטומטי.

מה הקוד עושה:
1. סורק את תיקיית New_Pic.
2. שולח תמונות לזיהוי טקסט בענן של גוגל.
3. מחלץ את הפינג (מספר בן 1-3 ספרות) ומשנה את שם הקובץ.
4. עוצר אחרי 1000 תמונות כדי לשמור על המכסה החינמית.

איך משתמשים:
python3 cloud_labeler_V1_gm.py ./New_Pic
'''

import os
import re
import sys
import io
import time
from pathlib import Path
from google.cloud import vision

# --- הגדרות נתיבים ---
# וודא שקובץ ה-JSON נמצא באותה תיקייה וזה שמו
KEY_FILE = "google_key.json" 
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = KEY_FILE

def extract_ping_value(text):
    """מאתר מספר שמתאים לפינג בתוך הטקסט שחזר מה-AI"""
    # ניקוי תווים מיוחדים והשארת רק ספרות ורווחים
    clean_text = re.sub(r'[^0-9\s]', '', text)
    nums = re.findall(r'\d+', clean_text)
    
    # בדרך כלל הפינג הוא המספר הברור ביותר בפינה, נחפש מספר הגיוני (1-999)
    for n in nums:
        val = int(n)
        if 1 <= val <= 999:
            return val
    return None

def run_labeler(folder_path, limit=363):
    client = vision.ImageAnnotatorClient()
    folder = Path(folder_path)
    
    if not folder.exists():
        print(f"Error: Folder {folder_path} not found.")
        return

    # רשימת קבצים שטרם תויגו (אין להם את המילה 'Ping' בשם)
    images = [p for p in folder.glob("*.png") if "ping" not in p.name.lower()]
    images = sorted(images)
    
    print(f"--- Cloud Labeler V1 Start ---")
    print(f"Found {len(images)} images to process. Limit set to: {limit}")
    
    success_count = 0
    fail_count = 0

    for i, img_p in enumerate(images):
        if i >= limit:
            print(f"\n[STOP] Reached the quota limit of {limit} images.")
            break

        try:
            with io.open(str(img_p), 'rb') as image_file:
                content = image_file.read()

            image = vision.Image(content=content)
            response = client.text_detection(image=image)
            texts = response.text_annotations

            if texts:
                # texts[0] מכיל את כל הטקסט שזוהה בתמונה
                full_text = texts[0].description
                ping_val = extract_ping_value(full_text)
                
                if ping_val is not None:
                    new_name = f"{img_p.stem}_Ping_{ping_val}_{img_p.suffix}"
                    img_p.rename(img_p.parent / new_name)
                    success_count += 1
                    print(f"[{i+1}] {img_p.name} -> Ping_{ping_val}_")
                else:
                    print(f"[{i+1}] {img_p.name} -> SKIP (No valid number found in: '{full_text.strip()}')")
                    fail_count += 1
            else:
                print(f"[{i+1}] {img_p.name} -> FAIL (No text detected)")
                fail_count += 1
            
            # המתנה קלה בין בקשות כדי לא להעמיס
            time.sleep(0.1)

        except Exception as e:
            print(f"\n[ERROR] Problem with {img_p.name}: {e}")
            break

    print(f"\n--- Finish Summary ---")
    print(f"Successfully labeled: {success_count}")
    print(f"Failed/Skipped: {fail_count}")

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "./New_Pic"
    run_labeler(path)
