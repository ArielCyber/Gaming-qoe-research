import cv2
import numpy as np
import pytesseract
import re
from pathlib import Path
from typing import Dict, Tuple, Optional, List

DIGITS_DIR = r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\digits_font\0_9"



def process_image(
        

    image_path: str,
    x1: int = 1565, y1: int = 150, x2: int = 1907, y2: int = 240,
    dx: int = 350, dy: int = 200, y2_delta: int = -70,
    shrink: int = 150
):

    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(image_path)

    h, w = img.shape[:2]

    x1_s = x1 + shrink
    x2_s = x2 - shrink

    X1 = x1_s + dx
    Y1 = y1 + dy
    X2 = x2_s + dx
    Y2 = y2 + dy + y2_delta
    
    X1 = max(0, min(w-1, int(round(X1))))
    X2 = max(0, min(w,   int(round(X2))))
    Y1 = max(0, min(h-1, int(round(Y1))))
    Y2 = max(0, min(h,   int(round(Y2))))

    if X2 <= X1 or Y2 <= Y1:
        raise ValueError(f"Bad ROI after offsets: ({X1},{Y1})-({X2},{Y2})")

    crop = img[Y1:Y2, X1:X2].copy()
    return crop





def sharpen(image: np.ndarray, strength: float = 1.5, radius: float = 1.0) -> np.ndarray:

    if image is None or image.size == 0:
        raise ValueError("image is empty or None")

    blurred = cv2.GaussianBlur(image, ksize=(0, 0), sigmaX=radius, sigmaY=radius)
    sharp = cv2.addWeighted(image, 1 + strength, blurred, -strength, 0)

    return sharp






def upscale_image(img: np.ndarray, scale: int = 8) -> np.ndarray:
    if img is None:
        raise ValueError("img is None")

    if scale <= 0:
        raise ValueError("scale must be positive")

    up = cv2.resize(
        img,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_CUBIC 
    )
    return up






def enhance_roi_for_digits(img_bgr: np.ndarray,
                           sat_gain: float = 1.4,
                           val_gain: float = 1.2,
                           alpha: float = 1.2,
                           beta: int = 5) -> np.ndarray:


    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    h, s, v = cv2.split(hsv)

    s = np.clip(s * sat_gain, 0, 255)
    v = np.clip(v * val_gain, 0, 255)

    hsv_enh = cv2.merge([h, s, v]).astype(np.uint8)
    bgr_enh = cv2.cvtColor(hsv_enh, cv2.COLOR_HSV2BGR)

    bgr_enh = cv2.convertScaleAbs(bgr_enh, alpha=alpha, beta=beta)

    return bgr_enh





def make_bw_digit_mask(img_bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    
    cond_hsv = (
        (h >= 45) & (h <= 60) &   
        (s >= 90) &               
        (v >= 150)                
    )

    b, g, r = cv2.split(img_bgr)
    g16 = g.astype(np.int16)
    r16 = r.astype(np.int16)
    b16 = b.astype(np.int16)

    cond_gdom = (
        (g16 > r16 + 15) &
        (g16 > b16 + 15) &
        (g >= 140)
    )

    mask = np.where(cond_hsv | cond_gdom, 255, 0).astype(np.uint8)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

    bw = np.full(mask.shape, 255, dtype=np.uint8)  
    bw[mask > 0] = 0                             

    return bw





def make_orange_digit_mask(img_bgr: np.ndarray) -> np.ndarray:

    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    cond_orange_hsv = (
        (h >= 10) & (h <= 30) &   # כתום/צהוב
        (s >= 80) &
        (v >= 130)
    )

    b, g, r = cv2.split(img_bgr)
    b16 = b.astype(np.int16)
    g16 = g.astype(np.int16)
    r16 = r.astype(np.int16)

    # R דומיננטי – טיפוסי לכתום/אדום
    cond_rdom = (
        (r16 > g16 + 10) &
        (r16 > b16 + 10) &
        (r >= 140)
    )

    cond_any = cond_orange_hsv | cond_rdom

    mask = np.where(cond_any, 255, 0).astype(np.uint8)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

    bw = np.full(mask.shape, 255, dtype=np.uint8)
    bw[mask > 0] = 0

    return bw









DIGIT_SIZE = (40, 64)  


def img_to_bw_digit(img: np.ndarray) -> np.ndarray:

    if img is None:
        raise ValueError("img_to_bw_digit got None")

    if len(img.shape) == 3 and img.shape[2] == 4:
        bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    elif len(img.shape) == 3 and img.shape[2] == 3:
        bgr = img
    else:
        bgr = None 

    if bgr is not None:
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        unique_vals = np.unique(gray)

        if len(unique_vals) <= 4:
            bw = (gray > 128).astype(np.uint8) * 255
            if np.mean(bw) > 127:
                bw = 255 - bw  
        else:
           
            bw = make_bw_digit_mask(bgr)
    else:
    
        gray = img
        unique_vals = np.unique(gray)
        if len(unique_vals) <= 4:
            bw = (gray > 128).astype(np.uint8) * 255
            if np.mean(bw) > 127:
                bw = 255 - bw
        else:
            _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            if np.mean(bw) < 127:
                bw = 255 - bw

    return bw


def normalize_digit(bw: np.ndarray) -> np.ndarray:

    h, w = bw.shape[:2]
    if (w, h) != DIGIT_SIZE:
        bw = cv2.resize(bw, DIGIT_SIZE, interpolation=cv2.INTER_AREA)
    return bw


def load_digit_templates(base_dir: str) -> Dict[int, List[np.ndarray]]:

    base = Path(base_dir) / "0_9"
    templates: Dict[int, List[np.ndarray]] = {d: [] for d in range(10)}

    for d in range(10):
        digit_dir = base / str(d)
        if not digit_dir.exists():
            continue

        for img_path in digit_dir.iterdir():
            if not img_path.is_file():
                continue

            img = cv2.imread(str(img_path), cv2.IMREAD_UNCHANGED)
            if img is None:
                continue

            try:
                bw = img_to_bw_digit(img)
                bw = normalize_digit(bw)
                templates[d].append(bw)
            except Exception as e:
                pass   

        if not templates[d]:
            pass   

    return templates


def segment_bw_digits(bw_digits: np.ndarray,
                      min_area: int = 500,
                      min_height: int = 40,
                      min_width: int = 15) -> List[Tuple[np.ndarray, Tuple[int, int, int, int]]]:

    fg = (bw_digits < 128).astype(np.uint8) * 255

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kernel, iterations=1)

    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        fg, connectivity=8
    )

    h_img, w_img = bw_digits.shape[:2]
    img_area = h_img * w_img

    components = []
    if num_labels <= 1:
        return []

    for label in range(1, num_labels):
        x, y, w, h, area = stats[label]

        if (
            area > 0.9 * img_area and
            w > 0.9 * w_img and
            h > 0.9 * h_img
        ):
            continue

        if area < min_area:
            continue
        if h < min_height:
            continue
        if w < min_width:
            continue

        if w > 1.4 * h:  
            child_boxes = split_wide_component(bw_digits, int(x), int(y), int(w), int(h),
                                               min_child_width=min_width)
            components.extend(child_boxes)
        else:
            components.append((int(x), int(y), int(w), int(h)))

    if not components:
        return []

    components.sort(key=lambda bb: bb[0])

    crops = []
    for (x, y, w, h) in components:
        x0 = max(x - 1, 0)
        y0 = max(y - 1, 0)
        x1 = min(x + w + 1, bw_digits.shape[1])
        y1 = min(y + h + 1, bw_digits.shape[0])
        crop = bw_digits[y0:y1, x0:x1]
        crops.append((crop, (x0, y0, x1 - x0, y1 - y0)))

    return crops

def split_wide_component(
    bw_digits: np.ndarray,
    x: int, y: int, w: int, h: int,
    min_child_width: int = 15
) -> List[Tuple[int, int, int, int]]:
   

    roi = (bw_digits[y:y+h, x:x+w] < 128).astype(np.uint8)  # 1=שחור,0=לבן
    col_sum = roi.sum(axis=0)   
    h_roi = roi.shape[0]
    max_sum = int(col_sum.max())
    if max_sum == 0:
        return [(x, y, w, h)]

    thresh = min(0.35 * max_sum, 0.25 * h_roi)
    gap_cols = np.where(col_sum < thresh)[0]
    if len(gap_cols) == 0:
        return [(x, y, w, h)]

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

    boundaries = [0]
    for s, e in splits:
        mid = (s + e) // 2
        boundaries.append(mid)
    boundaries.append(w)

    child_boxes: List[Tuple[int, int, int, int]] = []
    for i in range(len(boundaries) - 1):
        x0_c = boundaries[i]
        x1_c = boundaries[i + 1]
        cw = x1_c - x0_c
        if cw < min_child_width:
            continue
        child_boxes.append((x + x0_c, y, cw, h))

    if len(child_boxes) <= 1:
        return [(x, y, w, h)]
    return child_boxes

def digit_similarity(bw_query: np.ndarray, bw_template: np.ndarray) -> float:

    if bw_query.shape != bw_template.shape:
        bw_template = cv2.resize(
            bw_template,
            (bw_query.shape[1], bw_query.shape[0]),
            interpolation=cv2.INTER_AREA,
        )
    diff = cv2.absdiff(bw_query, bw_template)
    return float(np.mean(diff))


def recognize_single_digit(
    bw_digit: np.ndarray, templates: Dict[int, List[np.ndarray]]
) -> Tuple[int, Dict[int, float]]:

    bw_norm = normalize_digit(img_to_bw_digit(bw_digit))

    scores: Dict[int, float] = {}
    for d in range(10):
        tmpls = templates.get(d, [])
        if not tmpls:
            continue

        best = float("inf")
        for t in tmpls:
            s = digit_similarity(bw_norm, t)
            if s < best:
                best = s

        scores[d] = best

    if not scores:
        raise RuntimeError("no templates available for recognition")

    best_digit = min(scores, key=scores.get)
    return best_digit, scores




def recognize_number_from_bw_mask(
    bw_digits: np.ndarray,
    templates: Dict[int, List[np.ndarray]],
    max_mean_diff: float = 80.0,
    min_digits: int = 1,
) -> Tuple[Optional[int], List[int]]:


    segments = segment_bw_digits(bw_digits)

    if not segments:
        return None, []


    recognized_digits: List[int] = []

    for i, (digit_bw, bbox) in enumerate(segments):
        d, scores = recognize_single_digit(digit_bw, templates)
        best_score = scores[d]

      
        if best_score > max_mean_diff:
            return None, []

        recognized_digits.append(d)

    if len(recognized_digits) < min_digits:
        return None, []

    number = 0
    for d in recognized_digits:
        number = number * 10 + d

    return number, recognized_digits


def pad_left_bw(bw: np.ndarray, pad_px: int = 30, pad_value: int = 255) -> np.ndarray:
    """
    Padding משמאל למסכת BW.
    bw: 1-channel uint8, 0=ספרה, 255=רקע
    pad_value: 255 = רקע לבן (מומלץ), 0 = שחור
    """
    if bw is None or bw.size == 0:
        return bw
    if len(bw.shape) != 2:
        raise ValueError("pad_left_bw expects single-channel BW image")

    h, w = bw.shape
    if pad_px <= 0:
        return bw

    pad = np.full((h, pad_px), pad_value, dtype=bw.dtype)
    return np.concatenate([pad, bw], axis=1)



def recognize_number_from_screenshot(
    image, templates: Dict[int, List[np.ndarray]]
) -> Tuple[Optional[int], List[int]]:


    crop_big = upscale_image(sharpen(image))

    bw_green = make_bw_digit_mask(crop_big)
    cv2.imwrite("dbg_bw_green.png", bw_green)

    number, digits = recognize_number_from_bw_mask(
        bw_green,
        templates,
        max_mean_diff=90.0,  
        min_digits=1,
    )
    if number is not None:
        return number, digits

    bw_orange = make_orange_digit_mask(crop_big)
    cv2.imwrite("dbg_bw_orange.png", bw_orange)

    number2, digits2 = recognize_number_from_bw_mask(
        bw_orange,
        templates,
        max_mean_diff=60.0,  
        min_digits=3,       
    )
    if number2 is not None:
        return number2, digits2

        bw_orange2 = make_orange_digit_mask(crop_big) 
    bw_orange2 = pad_left_bw(bw_orange, pad_px=40, pad_value=0)
    cv2.imwrite("dbg_bw_orange_pad_left__.png", bw_orange2)

    number2, digits2 = recognize_number_from_bw_mask(
        bw_orange2,
        templates,
        max_mean_diff=60.0, 
        min_digits=3,  
    )
    if number2 is not None:

        return number2, digits2
    
    return None, []



# def run(image,templates=load_digit_templates(DIGITS_DIR)):
#     crop = process_image(image)
#     number, digits = recognize_number_from_screenshot(crop, templates)
#     if(number==None):
#         crop=enhance_roi_for_digits(crop)
#         number, digits = recognize_number_from_screenshot(crop, templates)
import cv2

def load_image_from_path(path: str):

    img = cv2.imread(path)
    return img



def run(image_path: str, templates: Dict[int, List[np.ndarray]]):
    # crop = process_image(str(image_path))
    crop = load_image_from_path(str(image_path))
    time=str(image_path).split("_")[-1].split(".")[0]
    number, digits = recognize_number_from_screenshot(crop, templates)
    if number is None:
        crop = enhance_roi_for_digits(crop)
        number, digits = recognize_number_from_screenshot(crop, templates)

    return digits, number,time

    

    return digits,number
def extracttime(img_path):
    img_path = str(img_path)
    ans=0
    j=1
    for i in range(len(img_path) - 5, -1, -1):
        if(img_path[i]=='_'):
            break
        c=img_path[i]
        ans+=j*(int(c))
        j*=10
    return ans
import numpy as np

def hhmmss_to_seconds(t: int) -> int:
    t = int(t)
    s = t % 100
    m = (t // 100) % 100
    h = t // 10000
    return h * 3600 + m * 60 + s

def mean_std_time(hhmmss_list):
    # ממיר לרשימת שניות
    times_sec = np.array([hhmmss_to_seconds(t) for t in hhmmss_list], dtype=int)

    # הפרשים בין כל שתי תמונות עוקבות
    diffs = np.diff(times_sec)

    if diffs.size == 0:
        return 0.0, 0.0, []

    mean_diff = float(diffs.mean())
    std_diff  = float(diffs.std())  # ddof=0
    return mean_diff, std_diff, diffs.tolist()


def mean_std_time(arr):
    ans=[]
    times_sec = [hhmmss_to_seconds(t) for t in arr]
    ans.append(0)
    for i in range(1,len(times_sec)):
        b=times_sec[i]
        n=times_sec[i-1]
        z=(b-n)
        ans.append(z)
    diffs = np.diff(times_sec)          # arr[1:] - arr[:-1]
    m = np.mean(diffs)
    s = np.std(diffs)    

    return m,s,diffs.tolist()
def extract_numbers_with_gaps_marked(results):
    # שליפה ראשונית של רק המספרים
    nums = [num for (_, num, _) in results]
    n = len(nums)

    # מציאת first real index
    left = 0
    while left < n and nums[left] is None:
        left += 1

    # מציאת last real index
    right = n - 1
    while right >= 0 and nums[right] is None:
        right -= 1

    # אם אין ערכים אמיתיים – פשוט להחזיר את המערך
    if left >= right:
        return nums

    # סימון None באמצע כ־-1
    for i in range(left + 1, right):
        if nums[i] is None:
            nums[i] = -1

    return nums
def get_stats(time_stemps_witaot_nan,time_stemps,results):

    mean,std,ans=mean_std_time(time_stemps_witaot_nan)

    print("reale valuse:",extract_numbers_with_gaps_marked(results))


    print("time stemps witaot nan:",ans)


    print("size:",len(time_stemps_witaot_nan))


    print("mean:",mean)

    print("std:",std)


    mean,std,ans=mean_std_time(time_stemps)

    print("time stemps:",ans)


    print("size:",len(time_stemps))

    print("mean:",mean)

    print("std:",std)

    print("total Nans:",len(time_stemps)-len(time_stemps_witaot_nan))
    print("\n")
    print("\n")
    print("\n")
    print("\n")



import re
from datetime import datetime
from pathlib import Path
import numpy as np

# TS_RE = re.compile(r"internal_(\d{8})_(\d{6})")

# def extract_dt(p: Path) -> datetime:
#     m = TS_RE.search(p.name)
#     if not m:
#         raise ValueError(f"bad filename: {p.name}")
#     ymd, hms = m.group(1), m.group(2)
#     return datetime.strptime(ymd + hms, "%Y%m%d%H%M%S")

from datetime import datetime
import re
from pathlib import Path

TS_RE = re.compile(r"(?:internal_)?(\d{8})_(\d{6})")  # internal_ is optional

def extract_dt(p: Path) -> datetime:
    m = TS_RE.search(p.stem)  # use stem (no .png)
    if not m:
        raise ValueError(f"bad filename: {p.name}")
    ymd, hms = m.group(1), m.group(2)
    return datetime.strptime(ymd + hms, "%Y%m%d%H%M%S")


import csv

def create_csv(data, output_path="metadata.csv"):
    with open(output_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # כותרות
        writer.writerow(["folder", "pcapng_file", "time_value_pairs"])

        for folder, (pcapng, results) in data.items():
            result_str = str(results)
            writer.writerow([folder, pcapng, result_str])

    print("CSV created:", output_path)

if __name__ == "__main__":
    # תיקיית התמונות שלך

    root = Path(r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\pictgers\test1")

    # טוענים טמפלייטים פעם אחת
    templates = load_digit_templates(DIGITS_DIR)
    to_csv = {}
    # print("Starting to processing ", folder.name)
    m=0
    size=len(list(root.iterdir()))
    for folder in root.iterdir():
        if not folder.is_dir():
            continue  # מדלג על קבצים אם יש
        m+=1
        print("Processing folder:", folder.name,"         ",m,"/",size)

        images_dir = folder  # זה כבר Path

        results = {}
        time_stemps = []
        time_stemps_witaot_nan = []
        pcaps = list(images_dir.glob("*.pcapng"))
        if not pcaps:
            print("Skipping folder (no pcapng):", folder.name)
            continue
        pcapng = pcaps[0].name 
        for img_path in images_dir.glob("*.png"):
            try:
                extract_dt(img_path)  
            except:
                continue
            digits, number,time = run(img_path, templates)
            # results.append((time, number))
            results[time]=number

            extraxt = extracttime(img_path)
            time_stemps.append(extraxt)

            if digits != [] or number is not None:
                time_stemps_witaot_nan.append(extraxt)
        mean_diff, std_diff, diffs = mean_std_time(time_stemps)

        # print("times:", time_stemps)
        # print("diffs (sec):", diffs)
        # print("mean diff (sec):", mean_diff)
        # print("std diff (sec):", std_diff)

        # to_csv.append((pcapng,results))
        to_csv[folder.name] = (pcapng,results)
        # get_stats(time_stemps_witaot_nan, time_stemps, results)
    create_csv(to_csv)

    print("Done processing all folders.")


# def time_stats():
#     root = Path(r"C:\Users\<user>\Downloads\school\Final project\Gaming-qoe-research\pictgers\test1")

#     for folder in root.iterdir():
#         if not folder.is_dir():
#             continue  # מדלג על קבצים אם יש

#         print("Processing folder:", folder.name)
#         images_dir = folder  # זה כבר Path

#         results = {}
#         time_stemps = []
#         time_stemps_witaot_nan = []
#         for img_path in sorted(images_dir.glob("*.png"), key=extract_dt):

#             extraxt = extracttime(img_path)
#             time_stemps.append(extraxt)


#         mean_diff, std_diff, diffs = mean_std_time(time_stemps)

#         print("times:", time_stemps)
#         print("diffs (sec):", diffs)
#         print("mean diff (sec):", mean_diff)
#         print("std diff (sec):", std_diff)
# time_stats()