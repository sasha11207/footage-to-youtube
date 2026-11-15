#!/bin/sh
# One-time setup for macOS and Linux. Everything goes INSIDE this project folder:
#   .venv/          Python environment used by the scripts
#   .tools/         uv + Python (only if this computer has no Python 3.9+), ffmpeg (only if needed)
# Nothing is installed system-wide, no settings are changed, no admin password is asked.
# To remove everything: delete the project folder.
#
#   sh setup.sh          show what would be downloaded (nothing is changed)
#   sh setup.sh --yes    do it
set -e
cd "$(dirname "$0")"
HERE="$(pwd)"
YES=0; [ "$1" = "--yes" ] && YES=1

OS="$(uname -s)"; ARCH="$(uname -m)"
case "$OS" in Darwin) os=mac ;; Linux) os=linux ;; *) echo "Unsupported system: $OS (on Windows use setup.ps1)"; exit 1 ;; esac
case "$ARCH" in arm64|aarch64) arch=aarch64 ;; x86_64|amd64) arch=x86_64 ;; *) echo "Unsupported CPU: $ARCH"; exit 1 ;; esac

# --- 1. Python: use one that is already here (read-only), else a private copy in .tools/ ---
pybase=""
# SETUP_FORCE_LOCAL=1 skips the computer's own Python and ffmpeg (used to test the downloads).
if [ "${SETUP_FORCE_LOCAL:-0}" = 1 ]; then :
elif [ -x .venv/bin/python ]; then
  pybase="(existing .venv)"
else
  for c in python3 python3.13 python3.12 python3.11 python3.10 python3.9; do
    p="$(command -v "$c" 2>/dev/null || true)"
    [ -z "$p" ] && continue
    # On a Mac without Command Line Tools, /usr/bin/python3 is a stub that opens an install dialog.
    if [ "$os" = mac ] && [ "$p" = /usr/bin/python3 ] && ! xcode-select -p >/dev/null 2>&1; then continue; fi
    if "$p" -c 'import sys, venv; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then pybase="$p"; break; fi
  done
fi

# --- 2. ffmpeg: the system one is fine if it has the filters we need, else a private copy ---
ff_ok=0
if [ -x .tools/ffmpeg/ffmpeg ] && [ -x .tools/ffmpeg/ffprobe ]; then ff_ok=1
elif [ "${SETUP_FORCE_LOCAL:-0}" = 1 ]; then :
elif command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1 \
     && ffmpeg -hide_banner -filters 2>/dev/null | grep -q " zscale " \
     && ffmpeg -hide_banner -filters 2>/dev/null | grep -q " xfade "; then ff_ok=1
fi

echo "Setup plan for this folder: $HERE"
if [ -n "$pybase" ]; then echo "  Python : use $pybase  (nothing to download)"
else echo "  Python : download uv (~20 MB, github.com/astral-sh/uv) and Python 3.12 (~40 MB) into .tools/"; fi
if [ "$ff_ok" = 1 ]; then echo "  ffmpeg : already OK  (nothing to download)"
elif [ "$os" = mac ]; then echo "  ffmpeg : download ffmpeg + ffprobe (~60 MB, ffmpeg.martin-riedl.de, signed builds) into .tools/ffmpeg/"
else echo "  ffmpeg : download static ffmpeg (~45 MB, johnvansickle.com) into .tools/ffmpeg/"; fi
echo "  Then   : create .venv and run the computer check (scripts/doctor.py)"
if [ "$YES" != 1 ]; then echo; echo "Nothing changed. Run 'sh setup.sh --yes' to do this."; exit 0; fi

mkdir -p .tools
if [ ! -x .venv/bin/python ]; then
  if [ -n "$pybase" ]; then
    "$pybase" -m venv .venv
  else
    if [ "$os" = mac ]; then t="uv-$arch-apple-darwin"; else t="uv-$arch-unknown-linux-gnu"; fi
    echo "Downloading uv ..."
    mkdir -p .tools/uv
    curl -fL --progress-bar "https://github.com/astral-sh/uv/releases/latest/download/$t.tar.gz" | tar -xz -C .tools/uv --strip-components 1
    export UV_PYTHON_INSTALL_DIR="$HERE/.tools/python" UV_CACHE_DIR="$HERE/.tools/uv-cache" UV_NO_CONFIG=1
    .tools/uv/uv python install 3.12
    .tools/uv/uv venv .venv --python 3.12
  fi
fi
PY="$HERE/.venv/bin/python"
"$PY" -c 'import sys; print("Python ready:", sys.version.split()[0], sys.executable)'

if [ "$ff_ok" != 1 ]; then "$PY" scripts/get_ffmpeg.py --yes; fi

echo
"$PY" scripts/doctor.py || true
echo
echo "Done. Run the scripts with: .venv/bin/python scripts/<name>.py"
