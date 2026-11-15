#!/usr/bin/env python3
"""Check that this computer can run the project, and say exactly what to install if not.

    python scripts/doctor.py          (Windows)
    python3 scripts/doctor.py         (macOS / Linux)

Nothing is installed by this script. It only checks and prints instructions.
The easy fix for anything missing is the project setup, which puts Python and ffmpeg inside
this folder only:  sh setup.sh --yes  (macOS/Linux)  or
powershell -ExecutionPolicy Bypass -File setup.ps1 -Yes  (Windows).
"""
import platform
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OS, ROOT, encoder_works, ffmpeg_list, hevc_encoder  # noqa: E402

FILTERS = {
    "zscale": "HDR (iPhone/DJI) to normal video colour conversion",
    "xfade": "seamless video loop (crossfade at the seam)",
    "acrossfade": "seamless audio loop",
    "afftdn": "gentle noise reduction of field recordings",
    "ebur128": "loudness measurement (LUFS)",
    "loudnorm": "loudness for Shorts",
    "vidstabdetect": "stabilisation of shaky clips (optional)",
    "drawtext": "text on thumbnails",
    "signalstats": "motion / brightness analysis",
}
OPTIONAL = {"vidstabdetect", "drawtext"}

INSTALL = {
    "mac": {
        "python": "Install Homebrew (https://brew.sh), then in Terminal:\n    brew install python",
        "ffmpeg": "Install Homebrew (https://brew.sh) if you don't have it, then in Terminal:\n    brew install ffmpeg",
        "full": "Homebrew's ffmpeg includes everything needed:\n    brew reinstall ffmpeg",
        "git": "    xcode-select --install      (or: brew install git)",
    },
    "windows": {
        "python": "In PowerShell:\n    winget install -e --id Python.Python.3.12\n"
                  "Then close and reopen PowerShell. (Or download from https://www.python.org/downloads/ and tick 'Add to PATH'.)",
        "ffmpeg": "In PowerShell:\n    winget install -e --id Gyan.FFmpeg\nThen close and reopen PowerShell (and Claude Code) so 'ffmpeg' is found.",
        "full": "Your ffmpeg lacks some filters. Easiest: let setup put a complete copy in this folder\n"
                "(powershell -ExecutionPolicy Bypass -File setup.ps1 -Yes), or: winget install -e --id Gyan.FFmpeg",
        "git": "In PowerShell:\n    winget install -e --id Git.Git",
    },
    "linux": {
        "python": "    sudo apt install python3     (Debian/Ubuntu)",
        "ffmpeg": "    sudo apt install ffmpeg      (Debian/Ubuntu; Fedora: sudo dnf install ffmpeg)",
        "full": "Your distribution's ffmpeg lacks some filters; use a static build from https://johnvansickle.com/ffmpeg/",
        "git": "    sudo apt install git",
    },
}


def ok(msg):
    print("  [OK]   " + msg)


def bad(msg):
    print("  [MISSING] " + msg)


def warn(msg):
    print("  [note] " + msg)


def main():
    problems = []
    print(f"System: {platform.system()} {platform.release()} ({platform.machine()})  ->  '{OS}' instructions\n")

    print("Python")
    if sys.version_info >= (3, 8):
        venv = ROOT / ".venv" / ("Scripts/python.exe" if OS == "windows" else "bin/python")
        hint = str(venv.relative_to(ROOT)) if venv.exists() else ("python" if OS == "windows" else "python3")
        ok(f"Python {platform.python_version()}  (run scripts with: {hint})")
    else:
        bad(f"Python {platform.python_version()} is too old (need 3.8+)")
        problems.append("python")

    print("\nffmpeg / ffprobe")
    ff, fp = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ff or not fp:
        bad("ffmpeg and ffprobe must both be installed and on PATH")
        problems.append("ffmpeg")
    else:
        ver = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, text=True).stdout.splitlines()[0]
        ok(ver[:80])
        have = ffmpeg_list("filters")
        for f, why in FILTERS.items():
            if f in have:
                ok(f"filter {f:14s} {why}")
            elif f in OPTIONAL:
                warn(f"filter {f:14s} missing (optional: {why})")
            else:
                bad(f"filter {f:14s} {why}")
                if "full" not in problems:
                    problems.append("full")
        encs = ffmpeg_list("encoders")
        for e in ("libx264", "libx265"):
            (ok if e in encs else bad)(f"encoder {e}")
            if e not in encs and "full" not in problems:
                problems.append("full")
        hw = hevc_encoder()
        ok(f"H.265 encoder that will be used: {hw}" + ("  (hardware, fast)" if hw != "libx265" else "  (software: slower, same quality)"))
        if OS == "mac" and "aac_at" in encs:
            ok("Apple AAC encoder (aac_at)")

    print("\nOptional")
    if shutil.which("git"):
        ok("git (needed only to download/update this project)")
    else:
        warn("git not found:\n" + INSTALL[OS]["git"])
    sec = ROOT / ".secrets"
    if (sec / "client_secret.json").exists():
        ok("YouTube API client found in .secrets/ (see README: 'YouTube API')")
    else:
        warn("no .secrets/client_secret.json yet: only needed for automatic titles/descriptions on YouTube (README)")
    try:
        free = shutil.disk_usage(str(ROOT)).free / 1e9
        (ok if free > 60 else warn)(f"free disk space here: {free:.0f} GB  (a 10-hour 4K video needs ~20-60 GB)")
    except OSError:
        pass

    print()
    if not problems:
        print("All good. You can render videos on this computer.")
        return 0
    setup = ("powershell -ExecutionPolicy Bypass -File setup.ps1 -Yes" if OS == "windows" else "sh setup.sh --yes")
    print("Easiest fix: run the project setup. It downloads what is missing into this folder only\n"
          "(no system changes):\n    " + setup + "\n")
    print("Or install system-wide yourself (then run doctor again):\n")
    for p in problems:
        print(INSTALL[OS][p] + "\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
