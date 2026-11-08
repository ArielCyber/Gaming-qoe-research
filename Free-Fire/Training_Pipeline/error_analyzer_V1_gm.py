# error_analyzer_V1_gm.py
import re
import os
import sys

# נוספו הנקודתיים החסרות בסוף השורה
def analyze_errors(input_file):
    if not os.path.exists(input_file):
        print(f"[ERROR] File '{input_file}' not found.")
        return

    output_file = f"mismatches_of_{os.path.basename(input_file)}"
    
    # תבנית לחילוץ הפינג האמיתי (תומך בפורמט _Ping_120 או _Ping_120_)
    truth_pattern = re.compile(r"_Ping_(\d+)")
    
    mismatches = []
    total_lines = 0

    print(f"[INFO] Analyzing {input_file}...")

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if " -> " not in line:
                continue
            
            total_lines += 1
            
            # פירוק השורה: filename -> detection | Method: ...
            parts = line.split(" -> ")
            filename = parts[0].strip()
            
            # חילוץ הזיהוי (המספר שמשמאל ל-pipe)
            id_part = parts[1].split(" | ")[0].strip()
            
            # חילוץ הפינג האמיתי משם הקובץ (Ground Truth)
            truth_match = truth_pattern.search(filename)
            if not truth_match:
                continue
                
            actual_ping = truth_match.group(1)
            
            # אם הזיהוי שונה מהאמת, נשמור את השורה
            if id_part != actual_ping:
                mismatches.append(line)

    # כתיבת דו"ח הטעויות
    with open(output_file, 'w', encoding='utf-8') as out_f:
        out_f.write(f"=== Error Analysis for: {input_file} ===\n")
        out_f.write(f"Total processed: {total_lines} | Total mismatches: {len(mismatches)}\n")
        out_f.write("-" * 60 + "\n")
        for m in mismatches:
            out_f.write(m + "\n")

    print(f"[SUCCESS] Found {len(mismatches)} mismatches.")
    print(f"[RESULT] Errors saved to: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze_errors(sys.argv[1])
    else:
        target = input("Enter output filename (e.g., out_V31_all2641.txt): ")
        analyze_errors(target)
        
# דוגמת הרצה
# python error_analyzer_V1_gm.py out_V38_all2641.txt         