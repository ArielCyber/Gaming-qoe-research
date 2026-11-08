# build_templates_from_debug.py
# Purpose: Auto-generate digit templates from debug* crops into digits_font.
# Terminal output: English only
# Code comments: Hebrew

import os
import re
import shutil
from pathlib import Path

import cv2
import numpy as np


# =========================
# הגדרות ברירת מחדל
# =========================

# לאן לשמור טמפלייטים (ברירת מחדל כמו שביקשת)
DEFAULT_DIGITS_FONT_DIR = Path.home() / "Documents" / "ping_extractor" / "digits_font"

# תת-מבנה התיקיות אצלך הוא digits_font/0_9/0..9
SUBFOLDER_0_9 = "0_9"

# לאן לשמור קבצים שנכשלו (לבדיקה ידנית)
FAILED_DIR_NAME = "failed_for_review"

# סף לזיהוי "צבע" (אם ההבדל בין ערוצי RGB גדול מזה -> כנראה צבעוני)
# הערה: זה לא מושלם, אבל עובד טוב כדי לסנן תמונות “מהמשחק עם מלבן אדום”
COLOR_DIFF_THRESHOLD = 8

# גודל אחיד לטמפלייטים (כמו בקוד של דביר)
DIGIT_SIZE = (40, 64)  # (width, height)

# פילוח קומפוננטות – ספים (אפשר לכוונן אם צריך)
MIN_AREA = 80
MIN_H = 12
MIN_W = 4


# =========================
# עזר: פינג מתוך שם קובץ
# =========================

def extract_ping_from_filename(filename: str):
    """
    מחזיר int של פינג אם יש בדיוק מופע אחד של 2-3 ספרות בשם הקובץ.
    אחרת מחזיר None.
    """
    # מחפש מספר של 2 או 3 ספרות שהוא "מילה" בפני עצמה (לא חלק ממספר ארוך יותר)
    matches = re.findall(r"(?<!\d)(\d{2,3})(?!\d)", filename)
    if len(matches) != 1:
        return None
    return int(matches[0])


# =========================
# עזר: בדיקה אם תמונה צבעונית
# =========================

def is_grayscale_like(img: np.ndarray) -> bool:
    """
    מחזיר True אם התמונה נראית כמו גווני אפור / שחור לבן.
    מחזיר False אם יש סימנים ברורים לצבע.
    """
    if img is None or img.size == 0:
        return False

    # אם כבר grayscale אמיתי (ערוץ אחד) -> מעולה
    if len(img.shape) == 2:
        return True

    # אם יש 4 ערוצים (BGRA) נזרוק אלפא
    if len(img.shape) == 3 and img.shape[2] == 4:
        img = img[:, :, :3]

    if len(img.shape) != 3 or img.shape[2] != 3:
        return False

    b, g, r = cv2.split(img)
    # אם זו תמונת אפור שמאוחסנת כ-BGR, הערוצים כמעט זהים
    diff_bg = cv2.absdiff(b, g)
    diff_gr = cv2.absdiff(g, r)
    diff_br = cv2.absdiff(b, r)

    max_diff = max(
        int(np.max(diff_bg)),
        int(np.max(diff_gr)),
        int(np.max(diff_br))
    )

    return max_diff <= COLOR_DIFF_THRESHOLD


# =========================
# עזר: בינריזציה + נרמול (ספרה שחורה על רקע לבן)
# =========================

def to_bw_digits_mask(gray: np.ndarray) -> np.ndarray:
    """
    מקבל תמונת גרייסקייל של אזור הפינג,
    מחזיר מסכה בינרית בפורמט:
    0 = ספרה (שחור), 255 = רקע (לבן)
    """
    # טשטוש קטן כדי להפחית רעש
    blur = cv2.GaussianBlur(gray, (3, 3), 0)

    # Otsu
    _, bw = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # נוודא שהספרות שחורות:
    # אם יש יותר מדי שחור (כלומר הרבה פיקסלים <128), ייתכן שהפכנו
    # נשתמש בממוצע: אם הממוצע נמוך => התמונה "כהה" מדי -> נהפוך
    if np.mean(bw) < 127:
        bw = 255 - bw

    # עכשיו bw הוא: לבן=255 לרקע בדרך כלל.
    # אבל אנחנו רוצים: 0 ספרה, 255 רקע.
    # אחרי הלוגיקה למעלה, לרוב הספרה תהיה שחורה (0) והרקע לבן (255) – שזה בדיוק מה שרצינו.
    return bw


def normalize_digit_crop(bw_digit: np.ndarray) -> np.ndarray:
    """
    מנרמל קרופ של ספרה לגודל קבוע.
    שומר פורמט 0=ספרה, 255=רקע.
    """
    return cv2.resize(bw_digit, DIGIT_SIZE, interpolation=cv2.INTER_AREA)


# =========================
# עזר: פיצול קומפוננטה רחבה (כמו בדביר)
# =========================

def split_wide_component(bw_digits: np.ndarray, x: int, y: int, w: int, h: int, min_child_width: int = 4):
    """
    מנסה לפצל קומפוננטה רחבה לשתי ספרות לפי "עמודות ריקות".
    מחזיר רשימת תיבות (x,y,w,h).
    """
    roi = (bw_digits[y:y+h, x:x+w] < 128).astype(np.uint8)  # 1=שחור (ספרה)
    col_sum = roi.sum(axis=0)
    h_roi = roi.shape[0]
    max_sum = int(col_sum.max())
    if max_sum == 0:
        return [(x, y, w, h)]

    # סף לזיהוי "עמודה כמעט ריקה"
    thresh = min(0.35 * max_sum, 0.25 * h_roi)
    gap_cols = np.where(col_sum < thresh)[0]
    if len(gap_cols) == 0:
        return [(x, y, w, h)]

    # מאחדים ריצפים
    splits = []
    start = gap_cols[0]
    prev = gap_cols[0]
    for c in gap_cols[1:]:
        if c == prev + 1:
            prev = c
        else:
            splits.append((start, prev))
            start = c
            prev = c
    splits.append((start, prev))

    # גבולות לפי אמצע הרווחים
    boundaries = [0]
    for s, e in splits:
        boundaries.append((s + e) // 2)
    boundaries.append(w)

    child_boxes = []
    for i in range(len(boundaries) - 1):
        x0 = boundaries[i]
        x1 = boundaries[i + 1]
        cw = x1 - x0
        if cw < min_child_width:
            continue
        child_boxes.append((x + x0, y, cw, h))

    if len(child_boxes) <= 1:
        return [(x, y, w, h)]
    return child_boxes


# =========================
# פילוח ספרות מתוך מסכה
# =========================

def segment_digits(bw_digits: np.ndarray):
    """
    מקבל מסכה bw של כל אזור הפינג.
    מחזיר רשימת קרופים של ספרות (ממוינים משמאל לימין) + התיבות שלהן.
    """
    # foreground של הספרות
    fg = (bw_digits < 128).astype(np.uint8) * 255

    # סוגרים חורים כדי לאחד חלקי ספרה
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kernel, iterations=1)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)

    if num_labels <= 1:
        return []

    comps = []
    h_img, w_img = bw_digits.shape[:2]
    img_area = h_img * w_img

    for label in range(1, num_labels):
        x, y, w, h, area = stats[label]

        # מדלגים על קומפוננטה ענקית שמכסה כמעט הכל (בד"כ זבל)
        if area > 0.9 * img_area and w > 0.9 * w_img and h > 0.9 * h_img:
            continue

        if area < MIN_AREA or h < MIN_H or w < MIN_W:
            continue

        # אם רחב מדי ביחס לגובה, ננסה לפצל (ספרות “מחוברות”)
        if w > 1.35 * h:
            comps.extend(split_wide_component(bw_digits, int(x), int(y), int(w), int(h), min_child_width=MIN_W))
        else:
            comps.append((int(x), int(y), int(w), int(h)))

    if not comps:
        return []

    comps.sort(key=lambda bb: bb[0])

    crops = []
    for (x, y, w, h) in comps:
        # מוסיפים פדינג קטן כדי לא לחתוך
        x0 = max(x - 1, 0)
        y0 = max(y - 1, 0)
        x1 = min(x + w + 1, bw_digits.shape[1])
        y1 = min(y + h + 1, bw_digits.shape[0])

        digit_crop = bw_digits[y0:y1, x0:x1]
        crops.append((digit_crop, (x0, y0, x1 - x0, y1 - y0)))

    return crops


# =========================
# שמירה לתיקיית digits_font
# =========================

def ensure_digits_folders(digits_font_dir: Path):
    """
    יוצר digits_font/0_9/0..9 אם חסר.
    """
    base = digits_font_dir / SUBFOLDER_0_9
    base.mkdir(parents=True, exist_ok=True)
    for d in range(10):
        (base / str(d)).mkdir(parents=True, exist_ok=True)
    # נשאיר גם "none" אם קיים אצלך, אבל לא נשתמש בו פה
    (base / "none").mkdir(parents=True, exist_ok=True)


def save_digit_template(digits_font_dir: Path, digit: str, img_bw: np.ndarray, out_name: str):
    """
    שומר טמפלייט ספרה לתיקייה המתאימה.
    """
    out_dir = digits_font_dir / SUBFOLDER_0_9 / digit
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / out_name
    cv2.imwrite(str(out_path), img_bw)


# =========================
# טיפול בקובץ אחד
# =========================

def process_one_image(img_path: Path, digits_font_dir: Path, failed_dir: Path):
    """
    מנסה:
    - לוודא שם עם פינג (2-3 ספרות פעם אחת)
    - לוודא grayscale
    - לפלח ספרות ולהשוות לכמות הספרות בפינג
    - לשמור טמפלייטים
    """
    ping = extract_ping_from_filename(img_path.name)
    if ping is None:
        # לא מתאים לפי הדרישה שלך -> “נכשל” (לבדיקה), אבל בלי רעש
        return ("SKIP_BAD_NAME", 0)

    img = cv2.imread(str(img_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        copy_to_failed(img_path, failed_dir, reason="cannot_read")
        return ("FAILED_READ", 0)

    # מסנן צבע
    if not is_grayscale_like(img):
        # זה בד"כ “תמונה מהמשחק עם מלבן אדום” -> לא רלוונטי
        return ("SKIP_COLOR", 0)

    # המרה לגרייסקייל
    if len(img.shape) == 3 and img.shape[2] == 4:
        img = img[:, :, :3]

    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    bw = to_bw_digits_mask(gray)

    # פילוח
    segments = segment_digits(bw)
    if not segments:
        copy_to_failed(img_path, failed_dir, reason="no_segments")
        return ("FAILED_NO_SEGMENTS", 0)

    expected_len = len(str(ping))

    # רוצים בדיוק 2 או 3 ספרות (כמו שאמרת)
    if expected_len not in (2, 3):
        return ("SKIP_NOT_2_3_DIGITS", 0)

    # אם כמות הספרות לא תואמת – לא מכניסים טמפלייטים, כדי לא לזהם את המאגר
    if len(segments) != expected_len:
        copy_to_failed(img_path, failed_dir, reason=f"digit_count_{len(segments)}_expected_{expected_len}")
        return ("FAILED_COUNT_MISMATCH", 0)

    # שמירה: הספרות לפי הסדר משמאל לימין מול הפינג משמאל לימין
    ping_str = str(ping)
    saved = 0
    stem_safe = re.sub(r"[^a-zA-Z0-9_\-]+", "_", img_path.stem)

    for i, (digit_crop, bbox) in enumerate(segments):
        digit_char = ping_str[i]

        # מנרמלים לגודל קבוע
        norm = normalize_digit_crop(digit_crop)

        # שם קובץ ייחודי כדי שלא ידרוס
        out_name = f"{stem_safe}__d{i}_{digit_char}.png"
        save_digit_template(digits_font_dir, digit_char, norm, out_name)
        saved += 1

    return ("OK", saved)


def copy_to_failed(img_path: Path, failed_dir: Path, reason: str):
    """
    מעתיק את הקובץ שנכשל לתיקיית failed_for_review,
    עם סאב-תיקייה לפי reason.
    """
    out_dir = failed_dir / reason
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(img_path), str(out_dir / img_path.name))


# =========================
# חיפוש תיקיות debug*
# =========================

def find_debug_dirs(root: Path):
    """
    מחזיר רשימת תיקיות שהשם שלהן מתחיל ב-debug (בכל עומק).
    """
    debug_dirs = []
    for p in root.rglob("*"):
        if p.is_dir() and p.name.startswith("debug"):
            debug_dirs.append(p)
    return sorted(debug_dirs)


def iter_images_in_dir(d: Path):
    """
    מחזיר כל תמונה חוקית בתיקייה.
    """
    exts = {".png", ".jpg", ".jpeg"}
    for p in sorted(d.iterdir()):
        if p.is_file() and p.suffix.lower() in exts:
            yield p


# =========================
# main
# =========================

def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 build_templates_from_debug.py <root_folder_to_scan> [digits_font_dir]")
        print("Example: python3 build_templates_from_debug.py ~/Documents/ping_extractor/LotOfScreenshot")
        sys.exit(1)

    root = Path(sys.argv[1]).expanduser().resolve()
    digits_font_dir = Path(sys.argv[2]).expanduser().resolve() if len(sys.argv) >= 3 else DEFAULT_DIGITS_FONT_DIR

    if not root.exists():
        print(f"[ERROR] Root folder does not exist: {root}")
        sys.exit(1)

    ensure_digits_folders(digits_font_dir)

    failed_dir = root / FAILED_DIR_NAME
    failed_dir.mkdir(parents=True, exist_ok=True)

    debug_dirs = find_debug_dirs(root)
    print(f"[INFO] Found {len(debug_dirs)} debug* folder(s) under: {root}")

    total_ok = 0
    total_saved = 0
    total_skipped_color = 0
    total_skipped_bad_name = 0
    total_failed = 0

    for dd in debug_dirs:
        print(f"[INFO] Scanning: {dd}")

        for img_path in iter_images_in_dir(dd):
            try:
                status, saved = process_one_image(img_path, digits_font_dir, failed_dir)

                if status == "OK":
                    total_ok += 1
                    total_saved += saved
                elif status == "SKIP_COLOR":
                    total_skipped_color += 1
                elif status == "SKIP_BAD_NAME":
                    total_skipped_bad_name += 1
                elif status.startswith("SKIP_"):
                    # שאר סוגי SKIP – לא נספור ככשל, זה פשוט לא רלוונטי לפי הכללים שלך
                    pass
                else:
                    total_failed += 1

            except Exception as e:
                # לא עוצרים על תמונה אחת
                total_failed += 1
                copy_to_failed(img_path, failed_dir, reason="exception")
                # הדפסה מינימלית באנגלית בלבד
                print(f"[WARN] Failed on {img_path.name}: {e}")

    print("\n[SUMMARY]")
    print(f"  OK images (templates created): {total_ok}")
    print(f"  Total digit templates saved:  {total_saved}")
    print(f"  Skipped (color images):       {total_skipped_color}")
    print(f"  Skipped (bad filename):       {total_skipped_bad_name}")
    print(f"  Failed (sent to review):      {total_failed}")
    print(f"  Review folder:                {failed_dir}")
    print(f"  Digits font folder:           {digits_font_dir}")


if __name__ == "__main__":
    main()

