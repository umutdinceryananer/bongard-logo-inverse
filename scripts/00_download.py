"""Download the Bongard-LOGO dataset and extract it under data/.

Question: Can the dataset be downloaded in full from the link in the official repository?
Input:    The Google Drive link in the NVlabs/Bongard-LOGO README (a single zip file).
Output:   data/raw/ShapeBongard_V2.zip, the zip contents extracted under data/
          without macOS metadata (__MACOSX/, .DS_Store), and the zip size and
          SHA-256 printed to stdout.
Decision: None directly. Prerequisite for every later script.

Usage: python scripts/00_download.py
"""

import hashlib
import sys
import zipfile
from pathlib import Path

import gdown

# https://github.com/NVlabs/Bongard-LOGO README, "The Bongard-LOGO Dataset"
GDRIVE_ID = "1-1j7EBriRpxI-xIVqE6UEXt-SzoWvwLx"

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ZIP_PATH = DATA / "raw" / "ShapeBongard_V2.zip"


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def is_macos_metadata(name):
    """True for macOS archive metadata: the __MACOSX/ tree and .DS_Store files."""
    return name.startswith("__MACOSX/") or name.rsplit("/", 1)[-1] == ".DS_Store"


def safe_extract(zip_path, target):
    """Extract the zip without macOS metadata, after checking that no member
    writes outside target. Returns the top-level entries and the skip count."""
    target = target.resolve()
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        members = [n for n in names if not is_macos_metadata(n)]
        for name in members:
            dest = (target / name).resolve()
            if not dest.is_relative_to(target):
                sys.exit(f"Zip member points outside the target directory: {name}")
        tops = sorted({n.split("/")[0] for n in members})
        z.extractall(target, members=members)
    return tops, len(names) - len(members)


def main():
    ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)
    if ZIP_PATH.exists():
        print(f"Zip already present, skipping download: {ZIP_PATH}")
    else:
        gdown.download(id=GDRIVE_ID, output=str(ZIP_PATH), quiet=False)

    print(f"Size:    {ZIP_PATH.stat().st_size / 2**20:.1f} MiB")
    print(f"SHA-256: {sha256(ZIP_PATH)}")

    tops, skipped = safe_extract(ZIP_PATH, DATA)
    print(f"Extracted under data/, top-level entries: {tops}")
    print(f"Skipped {skipped} macOS metadata entries")


if __name__ == "__main__":
    main()
