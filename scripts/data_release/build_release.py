"""Build the public raw-data release (Zenodo): captures + ping screenshots only.

Reads straight from the four source zips (no extraction) and writes:
  <out>/gaming_qoe_sample.zip          3 runs per game (low / mid / high ping)
  <out>/gaming_qoe_<game>.zip          every run used in the paper, per game
  <out>/manifest_<game>.csv            one row per capture file
  <out>/SHA256SUMS                     checksums of the output zips

What is shipped per run: the capture (.pcap / .pcapng), the cropped ping
screenshots (.png) and log.csv (screenshot index, timestamp, file name, status).
What is NOT shipped: OCR ping values, labels, features, metadata, results.
Free Fire screenshot names carry the OCR value (..._Ping_157.png, _W_/_N_ flags);
they are renamed back to the original capture name used in log.csv.

Usage:
  python scripts/data_release/build_release.py --out ~/gaming_qoe_release --sample-only
  python scripts/data_release/build_release.py --out ~/gaming_qoe_release
"""
import argparse
import ast
import csv
import hashlib
import os
import re
import statistics
import sys
import zipfile
from collections import defaultdict

csv.field_size_limit(10**9)

DEFAULT_SRC = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-<account>/My Drive/phd/research/major_revision/raw_pcaps")
DEFAULT_LABELS = os.path.join(os.path.dirname(__file__), "..", "..", "datasets")

# game -> (source zip, folder holding the run folders inside the zip)
GAMES = {
    "cod": ("Call_of_Duty_data.zip", "Call_of_Duty_data/recordings_cod/"),
    "freefire": ("michael_data.zip", "michael_data/recordings_ff/"),
    "pubg": ("menash_data.zip", "menash_data/recordings_pubg/"),
    "gob": ("asath_data.zip", "asath_data/recordings_gob/"),
}
CAPTURE_EXT = (".pcap", ".pcapng")
LOG_COLUMNS = {"i", "ts", "filename", "status", "elapsed_sec", "error"}
FF_PNG = re.compile(r"^(\d+)_(\d{8}_\d{6})_?(?:[A-Za-z]_?)?Ping_[^.]*\.png$")
LEAK = re.compile(r"ping", re.I)


def clean_name(game, fname, log_names=None):
    """Free Fire: drop the OCR value; use log.csv's name for the same frame index when known."""
    if game == "freefire":
        m = FF_PNG.match(fname)
        if m:
            if log_names and m.group(1) in log_names:
                return log_names[m.group(1)]
            return f"{m.group(1)}_{m.group(2)}.png"
    return fname


def read_log(zin, infos):
    for info in infos:
        if os.path.basename(info.filename) == "log.csv":
            return list(csv.DictReader(zin.read(info).decode("utf-8", "replace").splitlines()))
    return []


def read_labels(labels_dir, game):
    """Paper runs: {run folder basename: (capture file, median OCR ping)}. Used only to select runs."""
    out = {}
    with open(os.path.join(labels_dir, game, f"labels_{game}.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            run = re.split(r"[\\/]", r["folder"])[-1]
            vals = [v for v in ast.literal_eval(r["time_value_pairs"]).values()
                    if isinstance(v, (int, float))]
            out[run] = (r["pcapng_file"], statistics.median(vals) if vals else None)
    return out


def scan(zf, prefix):
    """Group zip entries by leaf run folder (nested runs become their own run).

    Some runs are stored twice (top level and nested inside another run); identical
    copies (same name, size, CRC) are kept once, differing copies stop the build."""
    runs = defaultdict(dict)
    for info in zf.infolist():
        n = info.filename
        if not n.startswith(prefix) or n.endswith("/"):
            continue
        parts = n[len(prefix):].split("/")
        run, fname = (parts[-2] if len(parts) > 1 else ""), parts[-1]
        prev = runs[run].get(fname)
        if prev is None:
            runs[run][fname] = info
        elif (prev.CRC, prev.file_size) != (info.CRC, info.file_size):
            sys.exit(f"conflicting copies: {prev.filename} vs {n}")
    return {run: list(files.values()) for run, files in runs.items()}


def select_runs(game, labels, runs):
    """Paper runs: labelled capture present, screenshots present, at least one numeric OCR label."""
    keep, missing = [], []
    for run, (cap, med) in labels.items():
        files = {os.path.basename(i.filename) for i in runs.get(run, [])}
        if med is not None and cap in files and any(f.endswith(".png") for f in files):
            keep.append(run)
        else:
            missing.append(run)
    return sorted(keep), sorted(missing)


def pick_sample(keep, labels, runs, n):
    """n runs spread over the ping range (median-size capture of each band, >=100 screenshots)."""
    scored = []
    for run in keep:
        med = labels[run][1]
        infos = runs[run]
        n_png = sum(i.filename.endswith(".png") for i in infos)
        size = sum(i.file_size for i in infos if i.filename.endswith(CAPTURE_EXT))
        if med is not None and n_png >= 100:
            scored.append((med, size, run))
    scored.sort()
    picks = []
    for k in range(n):
        band = scored[k * len(scored) // n:(k + 1) * len(scored) // n]
        band = sorted(band, key=lambda t: t[1])
        picks.append(band[len(band) // 2][2])  # median-size capture of the band
    return picks


def copy_run(zin, zout, game, run, infos, root, rows, used_capture):
    log = read_log(zin, infos)
    log_names = {r["filename"].split("_")[0]: r["filename"] for r in log if r.get("filename")}
    names = set()
    for info in sorted(infos, key=lambda i: i.filename):
        fname = os.path.basename(info.filename)
        low = fname.lower()
        if low.endswith(CAPTURE_EXT):
            if fname != used_capture:
                continue  # only the labelled capture is shipped
            kind = "capture"
        elif low.endswith(".png"):
            kind = "png"
        elif fname == "log.csv":
            kind = "log"
        else:
            continue  # stray files (e.g. 102.5vw) are not shipped
        new = clean_name(game, fname, log_names)
        if new in names:
            sys.exit(f"name clash after rename: {game}/{run}/{new}")
        names.add(new)
        zi = zipfile.ZipInfo(f"{root}/{run}/{new}", date_time=info.date_time)
        zi.compress_type = zipfile.ZIP_STORED if kind == "png" else zipfile.ZIP_DEFLATED
        h = hashlib.sha256()
        with zin.open(info) as src, zout.open(zi, "w", force_zip64=info.file_size > 2**31) as dst:
            while chunk := src.read(1 << 20):
                h.update(chunk)
                dst.write(chunk)
        if kind == "capture":
            rows.append({"game": game, "run": run, "capture_file": new,
                         "capture_bytes": info.file_size, "capture_sha256": h.hexdigest()})
    n_png = sum(n.endswith(".png") for n in names)
    for r in rows:
        if r["run"] == run:
            r["n_screenshots"] = n_png
            r["has_log"] = int("log.csv" in names)
            r["n_logged_frames"] = sum(1 for x in log if x.get("status") == "ok")


def verify(path):
    """No OCR value in any name; log.csv only has the expected columns and refers to shipped PNGs."""
    errors, info = [], {"logged_frames_without_png": 0}
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        nameset = set(names)
        for n in names:
            if LEAK.search(os.path.basename(n)):
                errors.append(f"name contains 'ping': {n}")
            if n.endswith(".csv") and os.path.basename(n) == "log.csv":
                rows = list(csv.DictReader(z.read(n).decode("utf-8", "replace").splitlines()))
                cols = set(rows[0].keys()) if rows else set()
                if not cols <= LOG_COLUMNS:
                    errors.append(f"unexpected log.csv columns {cols - LOG_COLUMNS}: {n}")
                d = os.path.dirname(n)
                info["logged_frames_without_png"] += sum(
                    1 for r in rows if r.get("status") == "ok" and f"{d}/{r['filename']}" not in nameset)
            elif n.endswith(".csv") and not os.path.basename(n).startswith("manifest_"):
                errors.append(f"unexpected csv: {n}")
    return errors, info


def write_manifest(path, rows):
    cols = ["game", "run", "capture_file", "capture_bytes",
            "capture_sha256", "n_screenshots", "n_logged_frames", "has_log"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 24):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=DEFAULT_SRC)
    ap.add_argument("--labels", default=DEFAULT_LABELS)
    ap.add_argument("--out", required=True)
    ap.add_argument("--games", nargs="+", default=list(GAMES))
    ap.add_argument("--sample-n", type=int, default=3)
    ap.add_argument("--sample-only", action="store_true")
    ap.add_argument("--verify-only", action="store_true", help="check existing zips, rewrite SHA256SUMS")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.verify_only:
        names = ["gaming_qoe_sample.zip"] + [f"gaming_qoe_{g}.zip" for g in a.games]
        finish([os.path.join(a.out, n) for n in names], a.out)

    plan = {}
    for g in a.games:
        zname, prefix = GAMES[g]
        zin = zipfile.ZipFile(os.path.join(a.src, zname))
        labels = read_labels(a.labels, g)
        runs = scan(zin, prefix)
        keep, missing = select_runs(g, labels, runs)
        sample = pick_sample(keep, labels, runs, a.sample_n)
        print(f"{g}: paper runs={len(labels)} shipped={len(keep)} missing={len(missing)} sample={sample}")
        plan[g] = (zin, labels, runs, keep, sample)

    outputs = []
    sp = os.path.join(a.out, "gaming_qoe_sample.zip")
    rows = []
    with zipfile.ZipFile(sp, "w", allowZip64=True) as zout:
        for g, (zin, labels, runs, keep, sample) in plan.items():
            for run in sample:
                copy_run(zin, zout, g, run, runs[run], f"gaming_qoe_sample/{g}", rows, labels[run][0])
        mp = os.path.join(a.out, "manifest_sample.csv")
        write_manifest(mp, rows)
        zout.write(mp, "gaming_qoe_sample/manifest_sample.csv")
    outputs.append(sp)

    if not a.sample_only:
        for g, (zin, labels, runs, keep, sample) in plan.items():
            gp = os.path.join(a.out, f"gaming_qoe_{g}.zip")
            rows = []
            with zipfile.ZipFile(gp, "w", allowZip64=True) as zout:
                for i, run in enumerate(keep, 1):
                    copy_run(zin, zout, g, run, runs[run], f"gaming_qoe_{g}", rows, labels[run][0])
                    if i % 50 == 0:
                        print(f"  {g}: {i}/{len(keep)} runs", flush=True)
                mp = os.path.join(a.out, f"manifest_{g}.csv")
                write_manifest(mp, rows)
                zout.write(mp, f"gaming_qoe_{g}/manifest_{g}.csv")
            outputs.append(gp)
    finish(outputs, a.out)


def finish(outputs, out):
    bad = False
    with open(os.path.join(out, "SHA256SUMS"), "w") as f:
        for p in outputs:
            errs, info = verify(p)
            for e in errs[:20]:
                print("  CHECK FAIL", e)
            bad |= bool(errs)
            print(f"{os.path.basename(p)}: {os.path.getsize(p)/1e9:.2f} GB, checks {'FAILED' if errs else 'ok'}, {info}")
            f.write(f"{sha256_file(p)}  {os.path.basename(p)}\n")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
