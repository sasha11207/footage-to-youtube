#!/usr/bin/env python3
"""Find short sounds that stand out from steady ambient noise (surf, rain, wind):
beeps, barks, voices, knocks, handling noise. A first pass before the user listens.

  python scripts/sound_events.py "D:/Recorder/ZOOM0007.WAV" [--start S] [--dur D] [--db 9]

Splits the sound into 50 ms frames in two bands (voice/bark 300-3000 Hz, beep 1.5-5 kHz) and reports
moments where a band rises more than --db above its running median (10 s window), plus a tonality score
(1 = pure tone) so electronic beeps (narrow, tonal) can be told from water splashes (broadband).
Events in the first/last 30 s of the file are marked EDGE: recorders beep and get handled there,
and that part is never used for loops anyway.

Then cut a short clip around each hit for the user to hear, e.g.
  ffmpeg -ss 754 -t 6 -i FILE.WAV hit1.wav
Nothing here is perfect: the user's ears are the final check.
"""
import argparse
import array
import math
import statistics
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import duration, hms, need  # noqa: E402  (also puts the project's own ffmpeg first on PATH)

SR, FR = 16000, 800                       # 16 kHz, 50 ms frames
EDGE = 30.0


def band(path, start, dur, af):
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-ss", str(start)] + (["-t", str(dur)] if dur else []) + \
          ["-i", str(path), "-vn", "-af", f"aresample={SR},pan=mono|c0=0.5*c0+0.5*c1,{af}", "-f", "s16le", "-"]
    x = array.array("h")
    x.frombytes(subprocess.run(cmd, stdout=subprocess.PIPE).stdout)
    if sys.byteorder == "big":
        x.byteswap()
    out = []
    for i in range(0, len(x) - FR, FR):
        seg = x[i:i + FR]
        out.append(10 * math.log10(sum(v * v for v in seg) / FR + 1e-9))
    return out, x


def tonality(x, i0):
    """Autocorrelation peak over 1.5-5 kHz periods in one frame (1 = pure tone, ~0 = noise)."""
    seg = x[i0:i0 + FR]
    e = sum(v * v for v in seg) or 1
    return max(sum(seg[j] * seg[j + lag] for j in range(len(seg) - lag)) / e for lag in range(3, 11))


def main():
    need("ffmpeg")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file"); p.add_argument("--start", type=float, default=0); p.add_argument("--dur", type=float, default=0)
    p.add_argument("--db", type=float, default=9, help="how far above the steady background counts as an event")
    a = p.parse_args()
    total = duration(a.file)
    if not total:
        sys.exit("cannot read: " + a.file)
    print(f"{Path(a.file).name}: {hms(total)}; looking for sounds that stand out by more than {a.db:g} dB ...", flush=True)
    found = 0
    for name, af in (("voice/bark 300-3k", "highpass=f=300,lowpass=f=3000"),
                     ("beep 1.5-5k", "highpass=f=1500,lowpass=f=5000")):
        lv, raw = band(a.file, a.start, a.dur, af)
        W = 200                               # 10 s median window
        events, cur = [], None
        for i, v in enumerate(lv):
            if i % 4 == 0:     # the median moves slowly: refresh it every 200 ms
                med = statistics.median(lv[max(0, i - W // 2):i + W // 2])
            rise = v - med
            if rise > a.db:
                if cur and i - cur[1] <= 2:
                    cur[1], cur[2] = i, max(cur[2], rise)
                else:
                    cur = [i, i, rise]
                    events.append(cur)
            elif cur and i - cur[1] > 2:
                cur = None
        for s, e, r in events:
            t = a.start + s * FR / SR
            edge = "  EDGE (start/stop zone)" if t < EDGE or t > total - EDGE else ""
            ton = max(tonality(raw, k * FR) for k in range(s, min(e, s + 80) + 1))   # strongest tone in the event
            kind = "  tonal: likely a beep/electronic" if ton > 0.6 and "beep" in name else ""
            print(f"{hms(t):>8s} ({t:8.2f}s) {(e - s + 1) * 50:5d} ms  {name:18s} +{r:4.1f} dB  tonal {ton:.2f}{kind}{edge}")
            found += 1
    print(f"done: {found} event(s). Make a short clip around each one and let the user listen." if found
          else "done: nothing stands out. Still listen to a few minutes before using it.")


if __name__ == "__main__":
    main()
