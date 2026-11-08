# dataset_merger_gm.py
import os
import shutil

# התיקיות שמהן אוספים
SOURCES = ['training_data', 'training_data_clean']
DEST = 'final_training_data'

def merge():
    # יצירת תיקיית היעד אם אינה קיימת
    if not os.path.exists(DEST):
        os.makedirs(DEST)
    
    total_moved = 0
    for i in range(10):
        # יצירת תתי-תיקיות לספרות 0-9
        digit_dest = os.path.join(DEST, str(i))
        os.makedirs(digit_dest, exist_ok=True)
        
        for src in SOURCES:
            src_path = os.path.join(src, str(i))
            if not os.path.exists(src_path):
                continue
                
            files = [f for f in os.listdir(src_path) if f.lower().endswith('.png')]
            for f in files:
                # הוספת שם התיקייה למניעת דריסת קבצים עם שם זהה
                new_name = f"{src}_{f}"
                shutil.copy2(os.path.join(src_path, f), os.path.join(digit_dest, new_name))
                total_moved += 1
                
    print(f"[SUCCESS] Merged {total_moved} clean templates into '{DEST}'")

if __name__ == "__main__":
    merge()