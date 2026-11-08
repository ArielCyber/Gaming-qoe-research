"""
Collect every input file of the paper figures into one folder.

Usage:
    export QOE_DRIVE_DIR=".../My Drive/phd/research/major_revision"   # once, e.g. in ~/.zshrc
    python figures/fetch_data.py [--drive-dir DIR] [--out-dir datasets/paper_figures]

Copies or extracts each file listed in SOURCES from the Google Drive folder
of the major revision into --out-dir, which is the default --data-dir of
figures/make_all.py. The Drive folder comes from --drive-dir or the
QOE_DRIVE_DIR environment variable. Files already present are skipped, so
it is safe to rerun. Only the needed files are extracted from the large zips.
"""

import argparse
import os
import shutil
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# file name in the data folder -> (path under the Drive folder, member inside a zip or None).
# Everything comes from the official data folder major_revision/datasets/<game>/ (see DATA.md).
SOURCES = {
    # the frozen paper datasets, 10-second windows (Fig. 9, Table 11)
    "features_cod_10s_paper.csv": ("datasets/cod/features_cod_10s_paper.csv", None),
    "features_freefire_10s_paper.csv": ("datasets/freefire/features_freefire_10s_paper.csv", None),
    "features_pubg_10s_paper.csv": ("datasets/pubg/features_pubg_10s_paper.csv", None),
    "features_gob_10s_paper.csv": ("datasets/gob/features_gob_10s_paper.csv", None),
    # per-match statistics (Fig. 8)
    "matches_cod.csv": ("datasets/cod/matches_cod.csv", None),
    "matches_freefire.csv": ("datasets/freefire/matches_freefire.csv", None),
    "matches_pubg.csv": ("datasets/pubg/matches_pubg.csv", None),
    "matches_gob.csv": ("datasets/gob/matches_gob.csv", None),
    # PUBG labels, for the 7 balancing runs of 2026-05-03 (Fig. 8)
    "labels_pubg.csv": ("datasets/pubg/labels_pubg.csv", None),
    # CoD experiments of the conference data, one row per second (Figs. 2 to 7)
    "conference_cod_experiments_10s.csv": ("datasets/cod/conference_cod_experiments_10s.csv", None),
}


def fetch(name, drive_dir, out_dir):
    target = os.path.join(out_dir, name)
    if os.path.exists(target):
        print(f"exists   {name}")
        return
    source, member = SOURCES[name]
    source = os.path.join(drive_dir, source)
    if member is None:
        shutil.copyfile(source, target)
    else:
        with zipfile.ZipFile(source) as z, z.open(member) as src, open(target, "wb") as dst:
            shutil.copyfileobj(src, dst)
    print(f"fetched  {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--drive-dir", default=os.environ.get("QOE_DRIVE_DIR"),
                        help="major_revision folder on Google Drive (default: $QOE_DRIVE_DIR)")
    parser.add_argument("--out-dir", default=os.path.join(ROOT, "datasets", "paper_figures"))
    args = parser.parse_args()
    if not args.drive_dir:
        parser.error("set the Drive folder with --drive-dir or the QOE_DRIVE_DIR environment variable")
    if not os.path.isdir(args.drive_dir):
        parser.error(f"Drive folder not found: {args.drive_dir}")
    os.makedirs(args.out_dir, exist_ok=True)
    for name in SOURCES:
        fetch(name, args.drive_dir, args.out_dir)


if __name__ == "__main__":
    main()
