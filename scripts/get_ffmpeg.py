#!/usr/bin/env python3
"""Download ffmpeg + ffprobe into this project's .tools/ffmpeg/ folder (not system-wide).

    python scripts/get_ffmpeg.py          show what would be downloaded
    python scripts/get_ffmpeg.py --yes    download

Sources (official builds linked from ffmpeg.org/download.html):
  macOS   ffmpeg.martin-riedl.de  (signed static builds, Apple silicon and Intel)
  Windows gyan.dev                (essentials build: has zscale, xfade, x264, x265, vidstab)
  Linux   johnvansickle.com       (static build)
scripts/common.py puts .tools/ffmpeg first on PATH, so every script uses this copy.
To remove it: delete the .tools folder.
"""
import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / ".tools" / "ffmpeg"
SYSTEM = platform.system()
ARM = platform.machine().lower() in ("arm64", "aarch64")
EXE = ".exe" if SYSTEM == "Windows" else ""

if SYSTEM == "Darwin":
    a = "arm64" if ARM else "amd64"
    SOURCES = [f"https://ffmpeg.martin-riedl.de/redirect/latest/macos/{a}/release/{n}.zip" for n in ("ffmpeg", "ffprobe")]
    SIZE = "~60 MB"
elif SYSTEM == "Windows":
    SOURCES = ["https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"]
    SIZE = "~115 MB"
else:
    a = "arm64" if ARM else "amd64"
    SOURCES = [f"https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-{a}-static.tar.xz"]
    SIZE = "~45 MB"


def download(url, path):
    """curl is on every Mac, Windows 10+ and most Linux; it uses the system's certificates."""
    curl = shutil.which("curl")
    if curl:
        subprocess.run([curl, "-fL", "--progress-bar", "-o", str(path), url], check=True)
    else:
        urllib.request.urlretrieve(url, str(path))


def extract(archive, tmp):
    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as z:
            z.extractall(tmp)
    else:
        with tarfile.open(archive) as t:
            t.extractall(tmp)


def main():
    if (DEST / f"ffmpeg{EXE}").exists() and (DEST / f"ffprobe{EXE}").exists():
        print(f"ffmpeg is already in {DEST}")
        return 0
    print(f"Will download ffmpeg + ffprobe ({SIZE}) into {DEST}")
    for u in SOURCES:
        print("  from " + u)
    if "--yes" not in sys.argv:
        print("Nothing changed. Run again with --yes to download.")
        return 0
    DEST.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(ROOT / ".tools")) as td:
        tmp = Path(td)
        for i, u in enumerate(SOURCES):
            arc = tmp / (f"part{i}.zip" if ".zip" in u else f"part{i}.tar.xz")
            print("Downloading " + u)
            download(u, arc)
            extract(arc, tmp / "x")
        for name in ("ffmpeg", "ffprobe"):
            hits = [p for p in (tmp / "x").rglob(name + EXE) if p.is_file()]
            if not hits:
                sys.exit(f"{name}{EXE} not found in the download")
            target = DEST / (name + EXE)
            shutil.copy2(str(hits[0]), str(target))
            if not EXE:
                target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    ver = subprocess.run([str(DEST / f"ffmpeg{EXE}"), "-version"], stdout=subprocess.PIPE, text=True).stdout
    print("Installed: " + (ver.splitlines() or ["?"])[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
