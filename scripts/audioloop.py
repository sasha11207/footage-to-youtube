#!/usr/bin/env python3
"""Seamless audio loop from hand-picked clean pieces of recording, tiled to fit a video loop.
Use it when the sound under the chosen video window has a problem (a voice, a car, a bump):
pick clean pieces by ear (from the same place!), and this builds a sound bed of exactly the loop length.

  python scripts/audioloop.py work/loop1/loop.wav --len 300 --k 2 "D:/rec/ZOOM0001.WAV@120-260" "D:/rec/ZOOM0001.WAV@400-520"

PIECE = path@start-end (seconds). Pieces are joined with --xfade crossfades, the end crossfades
back into the start, the result is cut to LEN/K and repeated K times, so the video loop and the
sound loop wrap together. --process applies the same cleaning as ambient.py (wind cut, gentle denoise).
Replace work/loopN/loop.wav with the result, then run  ambient.py seam  and  build  as usual.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FF, duration, loudness, need, run  # noqa: E402


def main():
    need("ffmpeg")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out"); ap.add_argument("pieces", nargs="+")
    ap.add_argument("--len", type=float, required=True, help="video loop length, seconds")
    ap.add_argument("--k", type=int, default=1, help="how many sound loops per video loop")
    ap.add_argument("--xfade", type=float, default=3); ap.add_argument("--lufs", type=float, default=-20)
    ap.add_argument("--process", action="store_true", help="wind cut + gentle denoise, as in ambient.py")
    a = ap.parse_args()
    L, X = a.len / a.k, a.xfade
    ins, fl = [], []
    pre = "highpass=f=70:poles=2,highpass=f=70:poles=2,afftdn=nr=8:nf=-40:tn=1,lowpass=f=16000," if a.process else ""
    for i, p in enumerate(a.pieces):
        path, rng = p.rsplit("@", 1)
        s, e = map(float, rng.split("-"))
        ins += ["-i", path]
        fl.append(f"[{i}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,{pre}"
                  f"atrim={s}:{e},asetpts=PTS-STARTPTS[p{i}]")
    cur = "p0"
    for i in range(1, len(a.pieces)):
        fl.append(f"[{cur}][p{i}]acrossfade=d={X}:c1=tri:c2=tri[j{i}]")
        cur = f"j{i}"
    # need L + X seconds: body = [X, L+X), head [0, X) crossfaded onto the body's end
    fl.append(f"[{cur}]atrim=0:{L + X},asetpts=PTS-STARTPTS,asplit=2[a][b]")
    fl.append(f"[a]atrim={X}:{L + X},asetpts=PTS-STARTPTS[body];[b]atrim=0:{X},asetpts=PTS-STARTPTS[head]")
    fl.append(f"[body][head]acrossfade=d={X}:c1=tri:c2=tri,aloop=loop={a.k - 1}:size={int(round(L * 48000))},"
              f"atrim=0:{a.len}[o]")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(out) + ".tmp.wav")
    run(FF + ins + ["-filter_complex", ";".join(fl), "-map", "[o]", "-c:a", "pcm_s24le", tmp])
    i, _ = loudness(tmp)
    run(FF + ["-i", tmp, "-af", f"volume={a.lufs - i:.2f}dB,alimiter=limit=0.7079:attack=5:release=80:level=disabled",
              "-c:a", "pcm_s24le", out])
    tmp.unlink()
    d = duration(out)
    print(f"{out}: {d:.2f}s = {a.k} x {L:.2f}s loop, {i:.1f} -> {a.lufs} LUFS")
    if abs(d - a.len) > 0.05:
        sys.exit(f"length mismatch: {d:.2f}s, expected {a.len:.2f}s (pieces too short for LEN/K + xfade?)")


if __name__ == "__main__":
    main()
