#!/usr/bin/env python3
"""End-to-end self-test on a synthetic clip. Proves the whole pipeline works on THIS computer.

    python scripts/run_demo.py          (Windows)
    python3 scripts/run_demo.py         (macOS / Linux)

Makes a 75 s test video (ffmpeg testsrc2 picture + "wave-like" noise sound) and a fake field-recorder
WAV that started 3.5 s earlier, then runs: footage inventory + sync -> scan -> analyze -> pick ->
test clip -> loop -> seam -> build (3 min) -> verify -> Shorts (with hook text) -> patch-sound ->
thumbnail -> audioloop.
Everything goes to demo-work/ (git-ignored); it is deleted at the start of each run.
Takes about 1-3 minutes. Exit code 0 and "DEMO PASSED" = all good.
"""
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
W = ROOT / "demo-work"
PY = sys.executable
sys.path.insert(0, str(HERE))
from common import FF, duration, hevc_encoder, run, run_err  # noqa: E402

LOOP_D, XFADE, FPS = 20.0, 2.0, 30
results = []


def step(name, args, expect_ok=True):
    t = time.time()
    print(f"\n=== {name}\n$ {Path(PY).name} " + " ".join(str(x) for x in args), flush=True)
    p = subprocess.run([PY] + [str(x) for x in args], cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, encoding="utf-8", errors="replace")
    print(p.stdout.rstrip()[-2500:])
    good = (p.returncode == 0) == expect_ok
    results.append((name, good, time.time() - t))
    if not good:
        print(f"!!! step failed: {name} (exit {p.returncode})")
    return p.stdout


def check(name, cond, detail=""):
    results.append((name, bool(cond), 0))
    print(f"--- check {name}: {'ok' if cond else 'FAILED'} {detail}")


def ssim(a, b):
    err = run_err(["ffmpeg", "-hide_banner", "-nostdin", "-i", a, "-i", b, "-lavfi", "ssim", "-f", "null", "-"])
    m = re.findall(r"All:([\d.]+)", err)
    return float(m[-1]) if m else 0.0


def frame(src, t, out):
    run(FF + ["-v", "error", "-ss", f"{t:.3f}", "-i", src, "-frames:v", "1", out])
    return out


def main():
    if W.exists():
        shutil.rmtree(W)
    src_dir = W / "footage"
    src_dir.mkdir(parents=True)
    clip, rec = src_dir / "DEMO_0001.MOV", src_dir / "REC_0001.WAV"
    print("making a synthetic 75 s clip with wave-like sound ...", flush=True)
    swell = "volume='0.12+0.88*pow(abs(sin(PI*t/5.3+0.7*sin(t/3.1))),6)':eval=frame"
    run(FF + ["-f", "lavfi", "-i", f"testsrc2=s=1280x720:r={FPS}:d=75",
              "-f", "lavfi", "-i", "anoisesrc=color=pink:amplitude=0.5:seed=7:d=75:r=48000",
              "-af", swell + ",pan=stereo|c0=c0|c1=c0", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
              "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", clip])
    # recorder: same sound, started 3.5 s BEFORE the camera, plus its own hiss -> offset must be +3.5 s
    run(FF + ["-i", clip, "-f", "lavfi", "-i", "anoisesrc=color=white:amplitude=0.01:seed=3:d=85:r=48000",
              "-filter_complex", "[0:a]adelay=3500|3500,apad=pad_dur=6[x];[1:a]pan=stereo|c0=c0|c1=c0[n];"
              "[x][n]amix=inputs=2:duration=shortest:normalize=0",
              "-c:a", "pcm_s24le", rec])

    s = HERE
    out = step("footage inventory + sound sync", [s / "footage.py", "inventory", src_dir, "--out", W / "inventory"])
    inv = json.loads((W / "inventory" / "inventory.json").read_text(encoding="utf-8")) if (W / "inventory" / "inventory.json").exists() else []
    check("inventory found the clip and the recorder",
          {x["name"] for x in inv} >= {clip.name, rec.name}, str([(x["name"], x["kind"]) for x in inv]))
    sync = step("footage sync (one pair)", [s / "footage.py", "sync", clip, rec, "--work", W])
    m = re.search(r"offset ([+-][\d.]+) s", sync)
    off = float(m.group(1)) if m else 99
    check("sync offset is +3.5 s", abs(off - 3.5) <= 0.15, f"measured {off:+.2f}")

    step("scan", [s / "ambient.py", "scan", src_dir, "--work", W])
    step("analyze", [s / "ambient.py", "analyze", "--work", W])
    step("pick", [s / "ambient.py", "pick", "--work", W, "--min", 20, "--max", 40, "--top", 3])
    check("pick wrote picks.json", (W / "picks.json").exists())

    t = W / "tests" / "test01.mp4"
    step("test clip with sound (recorder, night look)", [s / "ambient.py", "test", clip, 10, "--dur", 40, "--look", "night",
                                                        "--audio", rec, "--audio-offset", off, "--timecode", "--out", t])
    check("test clip is 40 s with sound", t.exists() and abs(duration(t) - 40) < 0.2)

    loop = W / "loop1"
    step(f"loop (codec auto = {hevc_encoder()})", [s / "ambient.py", "loop", clip, 5, LOOP_D, "--xfade", XFADE,
                                                  "--size", "1280x720", "--look", "day", "--audio", rec,
                                                  "--audio-offset", off, "--out", loop])
    mp4 = loop / "loop.mp4"
    check("loop video is exactly LOOP_D", mp4.exists() and abs(duration(mp4) - LOOP_D) < 0.05, f"{duration(mp4):.3f}s")
    check("loop sound is exactly LOOP_D", (loop / "loop.wav").exists() and abs(duration(loop / "loop.wav") - LOOP_D) < 0.02)
    if mp4.exists():
        # the seam (last frame -> first frame) must look like any normal frame-to-frame step
        a = W / "seam_a.png"      # very last frame of the loop
        run(FF + ["-v", "error", "-sseof", "-0.5", "-i", mp4, "-update", "1", a])
        b = frame(mp4, 0, W / "seam_b.png")
        c, d = frame(mp4, LOOP_D / 2, W / "mid_a.png"), frame(mp4, LOOP_D / 2 + 1.0 / FPS, W / "mid_b.png")
        seam, mid = ssim(a, b), ssim(c, d)
        check("seam is as smooth as a normal frame step", seam >= mid - 0.05, f"seam SSIM {seam:.3f} vs normal {mid:.3f}")

    step("seam check clip", [s / "ambient.py", "seam", loop])
    check("seam_check.mp4 is 10 s", (loop / "seam_check.mp4").exists() and abs(duration(loop / "seam_check.mp4") - 10) < 0.3)

    final = W / "output" / "demo-3min.mp4"
    step("build 0.05 h (3 min) by stream copy", [s / "ambient.py", "build", loop, "--hours", 0.05, "--out", final])
    check("final video is 3 min", final.exists() and abs(duration(final) - 180) < 1, f"{duration(final):.2f}s")
    step("verify (decode start/middle/end, loudness)", [s / "ambient.py", "verify", final, "--hours", 0.05, "--lufs", -20])

    sh = W / "shorts" / "short01.mp4"
    step("vertical Short", [s / "ambient.py", "short", clip, 20, "--dur", 30, "--out", sh])
    if sh.exists():
        v = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                            "-of", "json", sh]))["streams"][0]
        check("Short is 1080x1920", (v["width"], v["height"]) == (1080, 1920))
    else:
        check("Short exists", False)

    sh2 = W / "shorts" / "short02-text.mp4"
    step("Short with hook text", [s / "ambient.py", "short", clip, 30, "--dur", 15, "--text", "Wait for it...\\nit's working",
                                  "--out", sh2])
    check("Short with text exists", sh2.exists() and abs(duration(sh2) - 15) < 0.2)

    pv = W / "output" / "demo-3min_fixed_preview.mp4"
    step("patch-sound preview", [s / "ambient.py", "patch-sound", final, "--at", 95, "--len", 1.5, "--preview"])
    check("patch-sound preview is 20 s", pv.exists() and abs(duration(pv) - 20) < 0.3)
    fx = W / "output" / "demo-3min_fixed.mp4"
    step("patch-sound full", [s / "ambient.py", "patch-sound", final, "--at", 95, "--len", 1.5])
    check("patched video keeps its length", fx.exists() and abs(duration(fx) - duration(final)) < 0.2)

    step("thumbnail", [s / "thumb.py", mp4, 5, "--look", "day", "--big", "3 HOURS", "--sub", "Demo: it's working",
                       "--out", W / "thumbs"])
    check("thumbnail exists", (W / "thumbs" / "thumb_day_text.jpg").exists())

    step("audioloop from two clean pieces", [s / "audioloop.py", W / "bed.wav", "--len", LOOP_D, "--k", 2,
                                            f"{rec}@10-25", f"{rec}@40-55", "--process"])
    check("audioloop length", (W / "bed.wav").exists() and abs(duration(W / "bed.wav") - LOOP_D) < 0.05)

    print("\n" + "=" * 60)
    for name, good, secs in results:
        print(f"{'PASS' if good else 'FAIL'}  {name}" + (f"  ({secs:.0f}s)" if secs >= 1 else ""))
    bad = [n for n, g, _ in results if not g]
    print("=" * 60)
    print("DEMO PASSED" if not bad else f"DEMO FAILED: {len(bad)} problem(s)")
    print(f"Files to look at: {final}  and  {loop / 'seam_check.mp4'}  (delete demo-work/ when done)")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
