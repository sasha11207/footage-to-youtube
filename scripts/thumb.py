#!/usr/bin/env python3
"""Make a YouTube thumbnail (1280x720 JPG) from one frame of your video.

  python scripts/thumb.py work/loop1/loop.mp4 42 --look day --big "3 HOURS" --sub "Ocean waves at sunrise" --out output/thumbs

Writes OUT/thumb_<look>_text.jpg (with text and a small badge) and OUT/thumb_<look>_clean.jpg (no text).
For YouTube Studio "Test & Compare" make 2-3 variants with --suffix _a / _b (another frame, other words),
and use the clean one as the third variant: thumb_<look>_text_a.jpg, thumb_<look>_text_b.jpg, ...
--badge "" removes the badge. Pick the frame second by looking at the video or the pick contact sheets.
Works on macOS, Windows and Linux (finds a system font automatically, or pass --font).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FF, filter_path, find_font, need, run  # noqa: E402

LIFT = {"day": "eq=saturation=1.15:contrast=1.04,unsharp=5:5:0.5",
        "night": "curves=master='0/0 0.15/0.26 0.5/0.72 1/1',eq=saturation=1.3,unsharp=5:5:0.6",
        "none": "null"}


def main():
    need("ffmpeg")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("src"); p.add_argument("t", type=float, help="second of the frame")
    p.add_argument("--look", choices=list(LIFT), default="day")
    p.add_argument("--big", required=True, help="big line, e.g. '10 HOURS'"); p.add_argument("--sub", default="")
    p.add_argument("--align", choices=["left", "right"], default="left")
    p.add_argument("--badge", default="REAL SOUND · NO AI")
    p.add_argument("--font", default="", help="path to a .ttf/.ttc font")
    p.add_argument("--suffix", default="", help="variant name for A/B tests, e.g. _a, _b")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    font = Path(a.font) if a.font else find_font()
    ff = f"fontfile='{filter_path(font)}':" if font else ""
    hit = out / "frame.png"
    run(FF + ["-v", "error", "-ss", a.t, "-i", a.src, "-frames:v", "1", hit])
    # text goes through small files (textfile=) so quotes, colons and accents need no escaping
    for name, txt in (("big.txt", a.big), ("sub.txt", a.sub), ("badge.txt", a.badge)):
        (out / name).write_text(txt, encoding="utf-8")
    night = a.look == "night"
    bx = (lambda m: f"w-tw-{m}") if a.align == "right" else (lambda m: str(m))
    parts = [f"drawtext={ff}textfile=big.txt:fontsize=112:fontcolor=white:x={bx(56)}:y=34:"
             f"shadowcolor=black@0.7:shadowx=4:shadowy=4"]
    if a.sub:
        parts.append(f"drawtext={ff}textfile=sub.txt:fontsize=42:fontcolor={'0xcfe0ff' if night else 'white'}:"
                     f"x={bx(62)}:y=162:shadowcolor=black@0.7:shadowx=3:shadowy=3")
    if a.badge:
        parts.append(f"drawtext={ff}textfile=badge.txt:fontsize=30:fontcolor=white:x={bx(44)}:y=h-th-40:"
                     f"box=1:boxcolor=black@0.55:boxborderw=14")
    base = f"{LIFT[a.look]},scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720"
    for name, vf in (("text", ",".join([base] + parts)), ("clean", base)):
        run(FF + ["-v", "error", "-i", hit.name, "-vf", vf, "-q:v", "2", f"thumb_{a.look}_{name}{a.suffix}.jpg"], cwd=out)
    for n in ("frame.png", "big.txt", "sub.txt", "badge.txt"):
        (out / n).unlink(missing_ok=True)
    print("->", out / f"thumb_{a.look}_text{a.suffix}.jpg", "and", out / f"thumb_{a.look}_clean{a.suffix}.jpg")


if __name__ == "__main__":
    main()
