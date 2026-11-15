"""Shared helpers: running ffmpeg, probing files, picking encoders per platform.
Python 3.8+ standard library only. Works on macOS, Windows and Linux.

Windows note: paths inside ffmpeg *filter* arguments (vidstab result=, metadata file=, textfile=)
are hard to escape (C:\\...). We avoid that by running ffmpeg with cwd= the work folder and passing
only plain file names to filters. Input/output paths outside filters are passed normally.
"""
import functools
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECRETS = ROOT / ".secrets"
VIDEO_EXT = (".mov", ".mp4", ".m4v", ".mts", ".mkv", ".avi", ".hevc")
AUDIO_EXT = (".wav", ".flac", ".mp3", ".m4a", ".aif", ".aiff")
IMAGE_EXT = (".jpg", ".jpeg", ".heic", ".png", ".dng")

OS = {"Darwin": "mac", "Windows": "windows"}.get(platform.system(), "linux")

# A private ffmpeg downloaded by setup (scripts/get_ffmpeg.py) wins over a system one.
LOCAL_FFMPEG = ROOT / ".tools" / "ffmpeg"
if LOCAL_FFMPEG.is_dir():
    os.environ["PATH"] = str(LOCAL_FFMPEG) + os.pathsep + os.environ.get("PATH", "")


def run(cmd, cwd=None, check=True):
    """Run a command, return stdout. On failure print the tail of stderr and stop."""
    cmd = [str(c) for c in cmd]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                       encoding="utf-8", errors="replace", cwd=str(cwd) if cwd else None)
    if check and p.returncode != 0:
        sys.exit("command failed: " + " ".join(cmd[:14]) + " ...\n" + p.stderr[-3000:])
    return p.stdout


def run_err(cmd, cwd=None):
    """Run a command and return stderr (ffmpeg prints its analysis there)."""
    cmd = [str(c) for c in cmd]
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                          encoding="utf-8", errors="replace", cwd=str(cwd) if cwd else None).stderr


FF = ["ffmpeg", "-hide_banner", "-nostdin", "-y"]


def probe(path):
    out = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path], check=False)
    try:
        return json.loads(out)
    except ValueError:
        return None


def ratio(s):
    try:
        a, b = str(s).split("/")
        return float(a) / float(b) if float(b) else 0.0
    except (ValueError, ZeroDivisionError):
        return 0.0


def describe(path):
    """Key facts about a video file, or None if it has no video stream."""
    j = probe(path)
    if not j:
        return None
    v = next((s for s in j["streams"] if s["codec_type"] == "video"
              and not s.get("disposition", {}).get("attached_pic")), None)
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    if not v:
        return None
    rot = 0
    for sd in v.get("side_data_list", []):
        if "rotation" in sd:
            rot = int(sd["rotation"])
    dv = any("DOVI" in sd.get("side_data_type", "") or "Dolby" in sd.get("side_data_type", "")
             for sd in v.get("side_data_list", []))
    w, h = int(v["width"]), int(v["height"])
    if abs(rot) in (90, 270):
        w, h = h, w
    fps, rfps = ratio(v.get("avg_frame_rate", "0/1")), ratio(v.get("r_frame_rate", "0/1"))
    trc = v.get("color_transfer", "unknown")
    return {
        "path": str(Path(path).resolve()), "duration": float(j["format"].get("duration", 0) or 0),
        "width": w, "height": h, "landscape": w > h, "fps": round(fps, 3), "vfr": abs(fps - rfps) > 0.05,
        "codec": v["codec_name"], "pix_fmt": v.get("pix_fmt"), "transfer": trc,
        "hdr": trc in ("arib-std-b67", "smpte2084"), "dolby_vision": dv,
        "audio": bool(a), "audio_rate": int(a["sample_rate"]) if a else 0, "audio_ch": a.get("channels", 0) if a else 0,
    }


def duration(path):
    j = probe(path)
    return float(j["format"].get("duration", 0) or 0) if j else 0.0


@functools.lru_cache(None)
def ffmpeg_list(kind):
    """Names from `ffmpeg -encoders` / `-filters`."""
    out = run(["ffmpeg", "-hide_banner", f"-{kind}"], check=False)
    return {m.group(1) for m in re.finditer(r"^\s*[A-Z.]{2,6}\s+(\S+)", out, re.M)}


@functools.lru_cache(None)
def encoder_works(name):
    """A hardware encoder can be listed but have no GPU behind it: try one tiny encode."""
    if name not in ffmpeg_list("encoders"):
        return False
    p = subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=640x360:d=0.5",
                        "-c:v", name, "-f", "null", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.returncode == 0


def hevc_encoder():
    """Best H.265 encoder on this machine: Apple hardware, NVIDIA, Intel, else software x265."""
    order = {"mac": ["hevc_videotoolbox"], "windows": ["hevc_nvenc", "hevc_qsv", "hevc_amf"],
             "linux": ["hevc_nvenc", "hevc_qsv", "hevc_vaapi"]}[OS]
    for e in order:
        if e != "hevc_vaapi" and encoder_works(e):
            return e
    return "libx265"


def video_encoder_args(codec, fps, quality="high"):
    """Encoder arguments. codec: auto | hevc | x265 | x264; quality: high (loops) | short | preview (tests).
    GOP = 2 s, closed, so loops stream-copy cleanly."""
    g = str(int(fps) * 2)
    if codec in ("auto", "hevc"):
        codec = hevc_encoder()
    if codec in ("x264", "libx264"):
        preset, crf = {"high": ("slow", "17"), "short": ("medium", "18")}.get(quality, ("veryfast", "21"))
        return ["-c:v", "libx264", "-preset", preset, "-crf", crf,
                "-g", g, "-bf", "2", "-flags", "+cgop", "-pix_fmt", "yuv420p"]
    if codec in ("x265", "libx265"):
        return ["-c:v", "libx265", "-preset", "medium", "-crf", "18" if quality == "high" else "24", "-tag:v", "hvc1",
                "-x265-params", f"keyint={g}:open-gop=0:log-level=error", "-pix_fmt", "yuv420p"]
    if codec == "hevc_videotoolbox":
        return ["-c:v", codec, "-q:v", "65" if quality == "high" else "50", "-tag:v", "hvc1", "-g", g]
    if codec == "hevc_nvenc":
        return ["-c:v", codec, "-preset", "p6", "-rc", "vbr", "-cq", "21" if quality == "high" else "27", "-b:v", "0",
                "-tag:v", "hvc1", "-g", g, "-bf", "0", "-pix_fmt", "yuv420p"]
    if codec == "hevc_qsv":
        return ["-c:v", codec, "-global_quality", "21" if quality == "high" else "27", "-tag:v", "hvc1", "-g", g,
                "-pix_fmt", "nv12"]
    if codec == "hevc_amf":
        return ["-c:v", codec, "-quality", "quality", "-rc", "cqp", "-qp_i", "20", "-qp_p", "22",
                "-tag:v", "hvc1", "-g", g]
    sys.exit(f"unknown codec {codec}")


def aac_args(bitrate="256k"):
    """Apple's AAC encoder sounds better on a Mac; elsewhere ffmpeg's built-in aac."""
    enc = "aac_at" if "aac_at" in ffmpeg_list("encoders") else "aac"
    return ["-c:a", enc, "-b:a", bitrate, "-ar", "48000"]


def hwaccel_args():
    """Faster decode for analysis on a Mac; elsewhere plain software decode (always works)."""
    return ["-hwaccel", "videotoolbox"] if OS == "mac" else []


def loudness(path):
    """Integrated loudness (LUFS) and true peak (dBFS)."""
    err = run_err(["ffmpeg", "-hide_banner", "-nostdin", "-vn", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"])
    i = re.findall(r"I:\s+(-?[\d.]+|-inf) LUFS", err)
    p = re.findall(r"Peak:\s+(-?[\d.]+|-inf) dBFS", err)
    f = lambda s: None if s == "-inf" else float(s)
    return (f(i[-1]) if i else None), (f(p[-1]) if p else None)


def hms(s):
    s = int(round(s))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def find_font():
    """A bold-ish sans font that exists on this OS, for thumbnails and titles."""
    cands = {
        "mac": ["/System/Library/Fonts/Avenir Next.ttc", "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf"],
        "windows": ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"],
        "linux": ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"],
    }[OS]
    for c in cands:
        if Path(c).exists():
            return Path(c)
    return None


def filter_path(p):
    """Path for use inside an ffmpeg filter argument (fontfile=...), escaped for Windows drive colons."""
    return Path(p).as_posix().replace(":", "\\:")


def need(tool="ffmpeg"):
    if not shutil.which(tool):
        sys.exit(f"{tool} not found. Run:  python scripts/doctor.py   (it prints the install steps for your computer)")
