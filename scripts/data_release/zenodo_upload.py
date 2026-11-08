"""Create a Zenodo DRAFT for the raw-data release and upload the files. Never publishes.

  export ZENODO_TOKEN=...            # scopes: deposit:write, deposit:actions
  python scripts/data_release/zenodo_upload.py --dir ~/gaming_qoe_release --sandbox
  python scripts/data_release/zenodo_upload.py --dir ~/gaming_qoe_release            # real zenodo.org
  python scripts/data_release/zenodo_upload.py --dir ... --deposition <id>           # resume: upload missing files

Review the draft on the website, then press Publish there. Files cannot be changed after publishing.
"""
import argparse
import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request

FILES = ["README.md", "SHA256SUMS", "gaming_qoe_sample.zip", "manifest_sample.csv",
         "gaming_qoe_gob.zip", "manifest_gob.csv", "gaming_qoe_pubg.zip", "manifest_pubg.csv",
         "gaming_qoe_freefire.zip", "manifest_freefire.csv", "gaming_qoe_cod.zip", "manifest_cod.csv"]

TITLE = ("Mobile Gaming QoE Dataset: Encrypted Network Traffic Captures and In-Game Ping Screenshots "
         "(Call of Duty: Mobile, Free Fire, PUBG Mobile, Guns of Boom)")
DESCRIPTION = """<p>Raw data for per-second Quality of Experience (QoE) estimation of mobile first-person shooter games
from encrypted network traffic. For every match: the network capture of the Android phone (.pcapng / .pcap),
cropped screenshots of the in-game ping indicator (about every 1.4 s), and the screenshot log.</p>
<p>Games and matches: Call of Duty: Mobile (615), Free Fire (407), PUBG Mobile (184), Guns of Boom (300).
Latency impairments of 0 to 500 ms were added with Clumsy on the access point.</p>
<p>Start with gaming_qoe_sample.zip (3 matches per game). See README.md for the layout and the collection setup.</p>"""
METADATA = {
    "title": TITLE,
    "upload_type": "dataset",
    "description": DESCRIPTION,
    "creators": [{"name": "Zion, Yehonatan", "affiliation": "Ariel University"}],  # full author list after acceptance
    "access_right": "open",
    "license": "cc-by-4.0",
    "keywords": ["quality of experience", "QoE", "mobile gaming", "first-person shooter", "encrypted traffic",
                 "network traffic", "pcap", "latency", "ping", "OCR", "Call of Duty Mobile", "Free Fire",
                 "PUBG Mobile", "Guns of Boom"],
    # Added later in the Zenodo UI (metadata stays editable after publishing):
    #   code repo, once public: {"identifier": "https://github.com/ArielCyber/Gaming-qoe-research",
    #                            "relation": "isSupplementedBy", "resource_type": "software"}
    #   paper, after acceptance: {"identifier": "<paper DOI>", "relation": "isSupplementTo",
    #                             "resource_type": "publication-article"}
    "prereserve_doi": True,
}


def api(base, token, method, path, body=None, data=None, headers=None):
    url = path if path.startswith("http") else base + path
    h = {"Authorization": f"Bearer {token}"}
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=None) as r:
            txt = r.read()
            return json.loads(txt) if txt else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {url} -> {e.code}: {e.read().decode()[:2000]}")


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 24):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--sandbox", action="store_true")
    ap.add_argument("--deposition", help="existing draft id to resume")
    ap.add_argument("--files", nargs="+", help="upload only these files (default: all of FILES)")
    a = ap.parse_args()
    tok_file = os.path.expanduser("~/.zenodo_token_sandbox" if a.sandbox else "~/.zenodo_token")
    token = os.environ.get("ZENODO_TOKEN") or (open(tok_file).read().strip() if os.path.exists(tok_file) else None)
    token or sys.exit(f"set ZENODO_TOKEN or create {tok_file}")
    base = "https://sandbox.zenodo.org/api" if a.sandbox else "https://zenodo.org/api"

    paths = [os.path.join(a.dir, f) for f in (a.files or FILES)]
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        sys.exit(f"missing files: {missing}")

    if a.deposition:
        dep = api(base, token, "GET", f"/deposit/depositions/{a.deposition}")
    else:
        dep = api(base, token, "POST", "/deposit/depositions", body={})
        dep = api(base, token, "PUT", f"/deposit/depositions/{dep['id']}", body={"metadata": METADATA})
    print("draft:", dep["links"]["html"])
    print("reserved DOI:", dep["metadata"].get("prereserve_doi", {}).get("doi"))

    have = {f["filename"]: f["checksum"] for f in
            api(base, token, "GET", f"/deposit/depositions/{dep['id']}/files")}
    bucket = dep["links"]["bucket"]
    for p in paths:
        name = os.path.basename(p)
        local = md5(p)
        if have.get(name) == local:
            print(f"skip {name} (already uploaded)")
            continue
        size = os.path.getsize(p)
        print(f"upload {name} ({size/1e9:.2f} GB)", flush=True)
        with open(p, "rb") as f:
            r = api(base, token, "PUT", f"{bucket}/{urllib.parse.quote(name)}", data=f,
                    headers={"Content-Type": "application/octet-stream", "Content-Length": str(size)})
        remote = r.get("checksum", "").replace("md5:", "")
        if remote != local:
            sys.exit(f"checksum mismatch for {name}: local {local}, zenodo {remote}")
        print(f"  ok md5 {local}")
    print("\nAll files uploaded. Review the draft and press Publish on the website:", dep["links"]["html"])


if __name__ == "__main__":
    main()
