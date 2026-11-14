#!/usr/bin/env python3
"""Long ambient videos from your own footage: clip -> seamless loop -> 1-10+ hour video.
Python 3 standard library + ffmpeg/ffprobe only. Works on macOS, Windows and Linux.
(On Windows type `python` instead of `python3`.)

Steps (each writes into --work, default ./work):
  scan    <folder_or_files...>     probe every clip: length, size, fps, HDR, portrait, sound
  analyze                          per-second motion, shake, scene jumps, loudness, wind rumble
  pick    [--min 60 --max 420]     rank loop windows -> picks.json + a contact sheet per pick
  test    <clip> <start>           40-60 s TEST clip with sound, same look/sound chain as the loop
  loop    <clip> <start> <dur>     render ONE graded loop with a crossfaded seam (video + clean audio)
  seam    <loopdir>                10 s clip around the seam (loop end -> loop start) to check by eye and ear
  build   <loopdir> --hours 3      repeat the loop N times by stream copy + encode the audio once -> final MP4
  verify  <final.mp4>              decode start/middle/end, loudness, length -> PASS / FAIL
  short   <clip> <start>           vertical 9:16 Short (up to 60 s) with sound

Example (macOS paths; on Windows use e.g. "D:/Footage/IMG_0420.MOV"):
  python3 scripts/ambient.py scan "/Volumes/Drive/Ocean" --work work
  python3 scripts/ambient.py analyze --work work
  python3 scripts/ambient.py pick --work work --min 120 --max 420
  python3 scripts/ambient.py test "/Volumes/Drive/Ocean/IMG_0420.MOV" 95 --look day --out work/tests/t01.mp4
  python3 scripts/ambient.py loop "/Volumes/Drive/Ocean/IMG_0420.MOV" 95 300 --look day --out work/loop1
  python3 scripts/ambient.py seam work/loop1
  python3 scripts/ambient.py build work/loop1 --hours 3 --out output/ocean-3h.mp4
  python3 scripts/ambient.py verify output/ocean-3h.mp4
"""
import argparse
import json
import math
import re
import statistics as st
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (FF, VIDEO_EXT, aac_args, describe, duration, hwaccel_args, loudness, need,  # noqa: E402
                    run, run_err, video_encoder_args)


def wdir(work):
    p = Path(work)
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def save_json(p, obj, indent=1):
    Path(p).write_text(json.dumps(obj, indent=indent, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------- scan
def cmd_scan(a):
    files = []
    for p in map(Path, a.inputs):
        if p.is_dir():
            files += sorted(f for f in p.rglob("*") if f.suffix.lower() in VIDEO_EXT and not f.name.startswith("._"))
        elif p.exists():
            files.append(p)
        else:
            print("not found:", p)
    clips = []
    for f in files:
        d = describe(f)
        if not d:
            continue
        clips.append(d)
        flags = []
        if not d["landscape"]:
            flags.append("PORTRAIT(Shorts, or skip for 16:9)")
        if d["hdr"]:
            flags.append("HDR-" + ("HLG" if d["transfer"] == "arib-std-b67" else "PQ"))
        if d["dolby_vision"]:
            flags.append("DolbyVision")
        if d["vfr"]:
            flags.append("VFR")
        if not d["audio"]:
            flags.append("NO-SOUND")
        print(f"{f.name:28s} {d['duration']:7.1f}s {d['width']}x{d['height']} {d['fps']:g}fps {d['codec']} {' '.join(flags)}")
    save_json(wdir(a.work) / "clips.json", clips)
    tot = sum(c["duration"] for c in clips)
    print(f"\n{len(clips)} clips, {tot / 60:.1f} min total, {sum(c['landscape'] for c in clips)} landscape "
          f"-> {Path(a.work) / 'clips.json'}")


# ---------------------------------------------------------------- analyze
def per_second(pairs, dur, how="mean"):
    buckets = [[] for _ in range(int(math.ceil(dur)) + 1)]
    for t, v in pairs:
        i = int(t)
        if 0 <= i < len(buckets) and v is not None and not math.isinf(v):
            buckets[i].append(v)
    out = []
    for b in buckets[: int(dur)]:
        if not b:
            out.append(None)
        elif how == "max":
            out.append(max(b))
        else:
            out.append(sum(b) / len(b))
    return out


def read_meta(path):
    """ffmpeg metadata=print file -> list of (pts_time, {key: value})."""
    frames, cur = [], None
    if not Path(path).exists():
        return frames
    for line in Path(path).read_text(errors="ignore").splitlines():
        m = re.match(r"frame:\s*\d+\s+pts:\s*\S+\s+pts_time:(\S+)", line)
        if m:
            cur = (float(m.group(1)), {})
            frames.append(cur)
        elif "=" in line and cur:
            k, v = line.strip().split("=", 1)
            try:
                cur[1][k] = float(v)
            except ValueError:
                pass
    return frames


def read_trf(path, fps):
    """vid.stab .trf -> list of (time, dx, dy): median local motion = camera motion per frame."""
    out = []
    if not Path(path).exists():
        return out
    raw = Path(path).read_bytes()
    if raw[:4] == b"TRF1":      # vid.stab >= 1.1 binary: 24-byte header, then per frame int32 num, int32 n, n x 26-byte LM
        pos = 24
        while pos + 8 <= len(raw):
            num, n = struct.unpack_from("<ii", raw, pos)
            pos += 8
            if n < 0 or pos + 26 * n > len(raw):
                break
            xs = [struct.unpack_from("<hh", raw, pos + 26 * k) for k in range(n)]
            pos += 26 * n
            if xs:
                out.append(((num - 1) / fps, st.median(x for x, _ in xs), st.median(y for _, y in xs)))
        return out
    for line in raw.decode(errors="ignore").splitlines():
        m = re.match(r"Frame (\d+) \(List \d+ \[(.*)\]\)", line)
        if not m:
            continue
        lm = re.findall(r"\(LM (-?\d+) (-?\d+) ", m.group(2))
        if lm:
            out.append(((int(m.group(1)) - 1) / fps, st.median(int(x) for x, _ in lm), st.median(int(y) for _, y in lm)))
    return out


def analyze_clip(c, work, rate=6):
    """All side files get plain names and ffmpeg runs with cwd=work: safe on Windows paths."""
    base = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(c["path"]).stem)
    vm, trf, am, lm = base + ".video.txt", base + ".trf", base + ".loud.txt", base + ".low.txt"
    vf = (f"fps={rate},scale=320:-2,format=yuv420p,signalstats,scdet=threshold=100,"
          f"vidstabdetect=shakiness=6:accuracy=9:show=0:result={trf},metadata=mode=print:file={vm}")
    run(FF + hwaccel_args() + ["-i", c["path"], "-an", "-vf", vf, "-f", "null", "-"], cwd=work)
    vframes = read_meta(work / vm)
    dur = c["duration"]
    res = {"motion": per_second([(t, d.get("lavfi.signalstats.YDIF")) for t, d in vframes], dur),
           "bright": per_second([(t, d.get("lavfi.signalstats.YAVG")) for t, d in vframes], dur),
           "jump": per_second([(t, d.get("lavfi.scd.score")) for t, d in vframes], dur, "max")}
    cam = read_trf(work / trf, rate)
    shake_pairs = []        # shake = camera motion minus its 2 s moving average (a slow pan is not shake)
    for i, (t, dx, dy) in enumerate(cam):
        w = cam[max(0, i - rate): i + rate + 1]
        mx, my = sum(x for _, x, _ in w) / len(w), sum(y for _, _, y in w) / len(w)
        shake_pairs.append((t, math.hypot(dx - mx, dy - my)))
    res["shake"] = per_second(shake_pairs, dur, "max")
    if c["audio"]:
        run(FF + ["-i", c["path"], "-vn", "-af",
                  f"aresample=48000,ebur128=metadata=1,ametadata=mode=print:key=lavfi.r128.M:file={am}",
                  "-f", "null", "-"], cwd=work)
        res["loud"] = per_second([(t, d.get("lavfi.r128.M")) for t, d in read_meta(work / am)], dur, "max")
        run(FF + ["-i", c["path"], "-vn", "-af",
                  "aresample=48000,asplit[f][l];[l]lowpass=f=100,lowpass=f=100,asetnsamples=n=48000,"
                  f"astats=metadata=1:reset=1,ametadata=mode=print:key=lavfi.astats.Overall.RMS_level:file={lm};"
                  "[f]anullsink", "-f", "null", "-"], cwd=work)
        low = per_second([(t, d.get("lavfi.astats.Overall.RMS_level")) for t, d in read_meta(work / lm)], dur)
        res["wind"] = [None if (lo is None or lu is None) else lo - lu for lo, lu in zip(low, res["loud"])]
    for f in (vm, trf, am, lm):      # keep only the summary
        (work / f).unlink(missing_ok=True)
    return res


def cmd_analyze(a):
    work = wdir(a.work)
    clips = load_json(work / "clips.json")
    out = {}
    for c in clips:
        if not c["landscape"] and not a.portrait:
            continue
        print("analyzing", Path(c["path"]).name, f"({c['duration']:.0f}s)", flush=True)
        out[c["path"]] = analyze_clip(c, work)
    save_json(work / "analysis.json", out, indent=None)
    print(f"-> {work / 'analysis.json'}")


# ---------------------------------------------------------------- pick
def fill(xs, default=0.0):
    good = [x for x in xs if x is not None]
    d = st.median(good) if good else default
    return [d if x is None else x for x in xs]


def cmd_pick(a):
    work = wdir(a.work)
    an = load_json(work / "analysis.json")
    cands = []
    for path, r in an.items():
        motion, shake, jump = fill(r["motion"]), fill(r["shake"]), fill(r["jump"])
        loud = fill(r.get("loud", [0] * len(motion)), -40)
        wind = fill(r.get("wind", [0] * len(motion)), -20)
        bright = fill(r["bright"])
        n = len(motion)
        lmed = st.median(loud) if loud else -30
        impact = [1 if (l > lmed + a.impact_db) else 0 for l in loud]   # wave hits stand out of the bed
        for L in sorted({min(n - 2, x) for x in (a.min, (a.min + a.max) // 2, a.max)}):
            if L < a.min * 0.5 or L < 20:
                continue
            step = max(5, L // 10)
            for s in range(1, n - L - 1, step):    # skip the first second (tap to start)
                w = slice(s, s + L)
                sh = sorted(shake[w])[int(0.95 * (L - 1))]
                cands.append({
                    "clip": path, "start": s, "dur": L,
                    "motion": round(st.mean(motion[w]), 2), "shake95": round(sh, 2),
                    "jump": round(max(jump[w]), 1), "impacts_min": round(sum(impact[w]) * 60 / L, 1),
                    "wind": round(st.mean(wind[w]), 1), "loud_peak": round(max(loud[w]), 1),
                    "seam_bright": round(abs(st.mean(bright[s:s + 3]) - st.mean(bright[s + L - 3:s + L])), 1),
                })
    if not cands:
        sys.exit("no window fits: clips are shorter than --min")

    def z(key):
        vals = [c[key] for c in cands]
        m, sd = st.mean(vals), (st.pstdev(vals) or 1)
        return lambda c: (c[key] - m) / sd

    zm, zs, zi, zw, zb = z("motion"), z("shake95"), z("impacts_min"), z("wind"), z("seam_bright")
    for c in cands:
        c["score"] = round(1.0 * zm(c) + 0.6 * zi(c) - 1.5 * zs(c) - 0.8 * zw(c) - 0.5 * zb(c)
                           - (3 if c["jump"] > a.jump else 0) - (2 if c["shake95"] > a.shake else 0)
                           + 0.3 * math.log(c["dur"] / a.min + 1), 2)
    cands.sort(key=lambda c: -c["score"])
    picks = []
    for c in cands:      # no overlapping windows in the list
        if any(u["clip"] == c["clip"] and c["start"] < u["start"] + u["dur"] and u["start"] < c["start"] + c["dur"]
               for u in picks):
            continue
        picks.append(c)
        if len(picks) >= a.top:
            break
    for i, p in enumerate(picks, 1):
        sheet = work / f"pick{i:02d}.jpg"
        every = max(1, p["dur"] // 12)
        run(FF + ["-ss", p["start"], "-t", p["dur"], "-i", p["clip"],
                  "-vf", f"fps=1/{every},scale=480:-2,tile=4x3:padding=4", "-frames:v", "1", "-update", "1", sheet])
        p["sheet"] = str(sheet)
        flag = (["SCENE-JUMP"] if p["jump"] > a.jump else []) + (["SHAKY(--stab)"] if p["shake95"] > a.shake else [])
        print(f"{i:2d}. {Path(p['clip']).name} {p['start']}s +{p['dur']}s  score {p['score']:+.2f}  motion {p['motion']} "
              f"shake {p['shake95']} impacts/min {p['impacts_min']} wind {p['wind']} {' '.join(flag)}")
    save_json(work / "picks.json", picks)
    print(f"-> {work / 'picks.json'} and pickNN.jpg contact sheets (check for people, drops on the lens, tilted horizon)")


# ---------------------------------------------------------------- looks and chains
LOOKS = {   # applied after tone mapping, in SDR BT.709; tuned on Atlantic coast phone footage
    "none": "",
    "day": "curves=master='0/0 0.25/0.22 0.75/0.79 1/1',vibrance=intensity=0.18,colortemperature=temperature=6900:mix=0.25",
    "storm": "curves=master='0/0 0.25/0.20 0.6/0.55 1/0.92',eq=saturation=0.9,colortemperature=temperature=7600:mix=0.35",
    # "day for night": dark blue sea from daytime footage; the sky is darkened further by a gradient (see video_chain)
    "night": "eq=saturation=0.25,curves=r='0/0 0.5/0.02 0.8/0.13 1/0.32':g='0/0 0.5/0.045 0.8/0.22 1/0.52':"
             "b='0/0.012 0.4/0.06 0.7/0.30 0.9/0.66 1/0.88',noise=alls=3:allf=t",
    "sleep": "curves=master='0/0 0.5/0.36 1/0.74',eq=saturation=0.85,colortemperature=temperature=5600:mix=0.45,vignette=angle=PI/6",
}


def video_chain(c, a, size, t0=0.0, tag="x"):
    f = [f"fps={a.fps}"]
    if c["hdr"]:
        f.append(f"zscale=tin={c['transfer']}:min=bt2020nc:pin=bt2020:rin=tv:t=linear:npl={a.npl},format=gbrpf32le,"
                 f"zscale=p=bt709,tonemap=tonemap={a.tonemap}:desat=0,zscale=t=bt709:m=bt709:r=tv")
    if getattr(a, "stab_trf", None):
        if getattr(a, "tripod", False):
            f.append(f"vidstabtransform=input={a.stab_trf}:tripod=1:optzoom=0:zoom=1.5:interpol=bicubic")
        else:
            f.append(f"vidstabtransform=input={a.stab_trf}:smoothing=30:optzoom=1:zoom=2:interpol=bicubic")
    w, h = size.split("x")
    if getattr(a, "drift", ""):   # follow a slow camera drift with a moving crop (output px over SECONDS)
        dx, dy, over = (float(v) for v in a.drift.split(","))
        k = c["width"] / float(w)
        rx, ry = dx * k / over, dy * k / over
        mx, my = abs(rx) * 330 + 4, abs(ry) * 330 + 4
        cw = int(c["width"] - 2 * max(mx, my * 16 / 9)) // 2 * 2
        ch = int(cw * 9 / 16) // 2 * 2
        ox, oy = (c["width"] - cw) / 2, (c["height"] - ch) / 2
        f.append(f"crop={cw}:{ch}:x='{ox:.1f}+{rx:.5f}*(t+{t0})':y='{oy:.1f}+{ry:.5f}*(t+{t0})':exact=1")
    xpos = getattr(a, "xpos", 0.5)
    f.append(f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,"
             f"crop={w}:{h}:x='(iw-ow)*{xpos}':y='(ih-oh)/2',setsar=1")
    if a.look == "night":      # darken the sky: multiply by a static top-down gradient (bright foam kept)
        f.append(f"format=gbrp[p{tag}];gradients=s={w}x{h}:r={a.fps}:c0=0x8a8a8a:c1=0xffffff:x0=0:y0=0:x1=0:"
                 f"y1={int(int(h) * 0.48)}:n=2:speed=0,format=gbrp[g{tag}];[p{tag}][g{tag}]blend=all_mode=multiply:shortest=1")
    if LOOKS[a.look]:
        f.append(LOOKS[a.look])
    if a.vf:
        f.append(a.vf)
    f.append("format=yuv420p")
    return ",".join(f)


def audio_chain(a):
    f = ["aresample=48000", "aformat=channel_layouts=stereo",
         f"highpass=f={a.highpass}:poles=2", f"highpass=f={a.highpass}:poles=2"]
    if a.denoise > 0:
        f.append(f"afftdn=nr={a.denoise}:nf={a.noise_floor}:tn=1")
    f.append("lowpass=f=16000")
    return ",".join(f)


def master(src, out, target, ceiling):
    """One fixed gain to the target loudness (no compression); a soft limiter only if peaks would pass the ceiling."""
    i, tp = loudness(src)
    if i is None:
        sys.exit(f"no sound measured in {src}")
    g = target - i
    lim = ""
    if tp is not None and tp + g > ceiling:
        lim = f",alimiter=limit={10 ** ((ceiling - 0.5) / 20):.4f}:attack=5:release=80:level=disabled"
    tmp = Path(str(out) + ".tmp.wav")
    run(FF + ["-i", src, "-af", f"volume={g:.2f}dB{lim}", "-c:a", "pcm_f32le", tmp])
    i2, _ = loudness(tmp)          # the limiter lowers loudness a little: one make-up step
    run(FF + ["-i", tmp, "-af",
              f"volume={target - i2:.2f}dB,alimiter=limit={10 ** (ceiling / 20):.4f}:attack=5:release=80:level=disabled",
              "-c:a", "pcm_s24le", out])
    tmp.unlink()
    i3, tp3 = loudness(out)
    print(f"audio: {i:.1f} LUFS -> {i3:.1f} LUFS, true peak {tp3:.1f} dBFS (gain {g:+.1f} dB{', limited' if lim else ''})")


def audio_inputs(a, c, start, length):
    """-ss/-t input args for the sound: camera clip, or an external recorder at start + offset."""
    if a.audio:
        w0 = start + a.audio_offset
        if w0 < 0:
            sys.exit(f"the recorder starts {-w0:.1f}s after this point: use a later start")
        return ["-ss", f"{w0:.3f}", "-t", f"{length:.3f}", "-i", a.audio], True
    return None, c["audio"]


# ---------------------------------------------------------------- test clip
def cmd_test(a):
    """Short preview with the SAME picture and sound chain as the loop, so the user can approve by eye and ear."""
    c = describe(a.clip)
    if not c:
        sys.exit("not a video: " + a.clip)
    D = min(a.dur, c["duration"] - a.start)
    if D < 5:
        sys.exit("start is too close to the end of the clip")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    vc = video_chain(c, a, a.size)
    if a.timecode:
        from common import filter_path, find_font
        font = find_font()
        ff = f"fontfile='{filter_path(font)}':" if font else ""
        vc = vc.replace(",format=yuv420p", "") + (
            f",drawtext={ff}text='%{{pts\\:hms}}':x=24:y=24:fontsize=36:fontcolor=white:box=1:boxcolor=black@0.5,format=yuv420p")
    ins = ["-ss", a.start, "-t", D, "-i", a.clip]
    ain, has_audio = audio_inputs(a, c, a.start, D)
    if ain:
        ins += ain
    cmd = FF + ins + ["-map", "0:v", "-vf", vc] + video_encoder_args("x264", a.fps, "preview")
    if has_audio:
        raw = out.with_suffix(".raw.wav")
        run(FF + ins + ["-map", f"{1 if ain else 0}:a", "-af", audio_chain(a), "-c:a", "pcm_s24le", raw])
        wav = out.with_suffix(".wav")
        master(raw, wav, a.lufs, a.tp)
        raw.unlink()
        cmd = FF + ins + ["-i", wav, "-map", "0:v", "-map", f"{2 if ain else 1}:a", "-vf", vc] + \
            video_encoder_args("x264", a.fps, "preview") + aac_args("192k")
    cmd += ["-t", D, "-movflags", "+faststart", out]
    print(f"rendering test {D:g}s from {Path(a.clip).name} @ {a.start:g}s, look '{a.look}'", flush=True)
    run(cmd)
    if has_audio:
        out.with_suffix(".wav").unlink()
    print(f"-> {out}\nWatch it WITH SOUND (headphones). Note the second where anything sounds or looks wrong.")


# ---------------------------------------------------------------- loop
def cmd_loop(a):
    c = describe(a.clip)
    if not c:
        sys.exit("not a video: " + a.clip)
    D, X = float(a.dur), float(a.xfade)
    if a.start + D + X > c["duration"] + 0.01:
        sys.exit(f"needs {a.start + D + X:.1f}s of source, clip has {c['duration']:.1f}s (lower start/dur/xfade)")
    out = wdir(a.out)
    src, s0 = str(Path(a.clip).resolve()), a.start
    a.stab_trf = None
    if a.tripod:
        a.stab = True
    if a.stab:      # stabilise the whole window once (two-pass vid.stab) so both loop pieces share one path
        a.stab_trf = "stab.trf"     # plain name, ffmpeg runs in the loop folder
        run(FF + ["-ss", s0, "-t", D + X, "-i", src, "-an", "-vf",
                  f"fps={a.fps},vidstabdetect=shakiness=6:accuracy=12:result={a.stab_trf}" + (":tripod=1" if a.tripod else ""),
                  "-f", "null", "-"], cwd=out)
        mid = out / "stab_window.mov"
        vc = video_chain(c, a, a.size)
        run(FF + ["-ss", s0, "-t", D + X, "-i", src, "-vf", vc, "-c:v", "prores_ks", "-profile:v", "3",
                  "-c:a", "pcm_s24le", mid.name], cwd=out)
        (out / "stab.trf").unlink(missing_ok=True)
        src, s0, a.stab_trf = str(mid), 0.0, None
        c = describe(mid)
        c["hdr"] = False
        a.look, a.vf, a.drift = "none", "", ""     # already applied

    vc, vcb, ac = video_chain(c, a, a.size, X, "a"), video_chain(c, a, a.size, 0.0, "b"), audio_chain(a)
    # piece A = window [X, X+D], piece B = window [0, X]; xfade A's tail into B -> loop of exactly D seconds
    fc = (f"[0:v]{vc},trim=duration={D},setpts=PTS-STARTPTS[va];"
          f"[1:v]{vcb},trim=duration={X},setpts=PTS-STARTPTS[vb];"
          f"[va][vb]xfade=transition=fade:duration={X}:offset={D - X}[v]")
    ins = ["-ss", s0 + X, "-t", D + 1, "-i", src, "-ss", s0, "-t", X + 1, "-i", src]
    ai = (0, 1)
    has_audio = c["audio"]
    if a.audio:     # external recorder: recorder time = video time + audio_offset (footage.py sync)
        w0 = a.start + a.audio_offset
        if w0 < 0:
            sys.exit(f"the recorder starts {-w0:.1f}s after this window: raise start")
        ins += ["-ss", f"{w0 + X:.3f}", "-t", D + 1, "-i", a.audio, "-ss", f"{w0:.3f}", "-t", X + 1, "-i", a.audio]
        ai, has_audio = (2, 3), True
    if has_audio:
        fc += (f";[{ai[0]}:a]{ac},atrim=duration={D},asetpts=PTS-STARTPTS[aa];"
               f"[{ai[1]}:a]{ac},atrim=duration={X},asetpts=PTS-STARTPTS[ab];"
               f"[aa][ab]acrossfade=d={X}:c1=qsin:c2=qsin[a]")
    raw_wav, wav, mp4 = out / "loop_raw.wav", out / "loop.wav", out / "loop.mp4"
    enc = video_encoder_args(a.codec, a.fps)
    cmd = FF + ins + ["-filter_complex", fc, "-map", "[v]"] + enc + [
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
        "-an", "-movflags", "+faststart", mp4]
    if has_audio:
        cmd += ["-map", "[a]", "-c:a", "pcm_s24le", raw_wav]
    print(f"rendering loop {D:g}s (seam crossfade {X:g}s) with {enc[1]}", flush=True)
    run(cmd)
    if has_audio:
        master(raw_wav, wav, a.lufs, a.tp)
        raw_wav.unlink()
    if a.stab:
        (out / "stab_window.mov").unlink(missing_ok=True)
    meta = {"clip": str(Path(a.clip).resolve()), "start": a.start, "dur": D, "xfade": X, "look": a.look,
            "size": a.size, "fps": a.fps, "codec": enc[1], "lufs": a.lufs, "audio": has_audio,
            "audio_src": a.audio or "camera", "audio_offset": a.audio_offset}
    save_json(out / "loop.json", meta)
    print(f"-> {mp4} ({duration(mp4):.2f}s)" + (" + loop.wav" if has_audio else "") +
          f"\nnext: check the seam:  ambient.py seam {out}")


# ---------------------------------------------------------------- seam / build / verify
def cmd_seam(a):
    d = Path(a.loopdir)
    mp4, wav = d / "loop.mp4", d / "loop.wav"
    D = duration(mp4)
    ins = ["-stream_loop", "1", "-i", mp4] + (["-stream_loop", "1", "-i", wav] if wav.exists() else [])
    out = d / "seam_check.mp4"
    run(FF + ins + ["-ss", D - 5, "-t", 10, "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p"]
        + (aac_args("192k") if wav.exists() else []) + ["-shortest", out])
    print(f"-> {out}: the seam is at 0:05. Watch and listen: you should not notice anything at 0:05.")


def concat_line(p):
    return "file '" + Path(p).resolve().as_posix().replace("'", "'\\''") + "'\n"


def cmd_build(a):
    d = Path(a.loopdir)
    meta = load_json(d / "loop.json")
    mp4, wav = d / "loop.mp4", d / "loop.wav"
    D = duration(mp4)
    n = max(1, math.ceil(a.hours * 3600 / D))
    total = n * D
    lst = d / "concat.txt"
    lst.write_text(concat_line(mp4) * n, encoding="utf-8")
    out = Path(a.out) if a.out else d / f"final_{a.hours:g}h.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = FF + ["-f", "concat", "-safe", "0", "-i", lst]
    if meta.get("audio") and wav.exists():
        # audio is encoded once over the whole length: no AAC gaps at the joins;
        # 4 s fade-in so the video never opens with a jolt, 10 s fade-out at the very end
        fo = min(10.0, total / 4)
        cmd += ["-stream_loop", n - 1, "-i", wav, "-map", "0:v", "-map", "1:a",
                "-af", f"afade=t=in:d={min(4.0, total / 4):g},afade=t=out:st={total - fo:.3f}:d={fo:g}"] + aac_args("256k")
    else:
        cmd += ["-map", "0:v"]
    cmd += ["-c:v", "copy", "-t", f"{total:.3f}", "-movflags", "+faststart", out]
    gb = mp4.stat().st_size * n / 1e9
    print(f"{n} x {D:.2f}s = {total / 3600:.2f} h, about {gb:.1f} GB -> {out}", flush=True)
    run(cmd)
    lst.unlink()
    print(f"-> {out} ({duration(out) / 3600:.3f} h, {out.stat().st_size / 1e9:.2f} GB)\nnext:  ambient.py verify {out}")


def decode_ok(path, t, length=8):
    err = run_err(["ffmpeg", "-hide_banner", "-nostdin", "-v", "error", "-ss", f"{max(0, t):.2f}", "-t", length,
                   "-i", path, "-f", "null", "-"])
    return not err.strip(), err.strip()[:300]


def cmd_verify(a):
    p = Path(a.file)
    if not p.exists():
        sys.exit("file not found: " + str(p))
    T = duration(p)
    v = describe(p)
    fails = []
    print(f"{p.name}: {T / 3600:.3f} h ({T:.1f} s), {v['width']}x{v['height']} {v['fps']:g} fps {v['codec']}, "
          f"sound: {'yes' if v['audio'] else 'NO'}, {p.stat().st_size / 1e9:.2f} GB")
    if a.hours and abs(T - a.hours * 3600) > max(60, a.hours * 3600 * 0.03):
        fails.append(f"length {T / 3600:.2f} h, expected about {a.hours:g} h")
    for name, t in (("start", 0), ("middle", T / 2), ("end", T - 12)):
        good, err = decode_ok(p, t)
        print(f"  decode {name:6s} @ {t:9.1f}s: {'ok' if good else 'ERROR ' + err}")
        if not good:
            fails.append(f"decode error at {name}")
    if v["audio"]:
        mid = Path(str(p) + ".mid.wav")
        seg = min(120, T / 3)
        run(FF + ["-ss", T / 2 - seg / 2, "-t", seg, "-i", p, "-vn", "-c:a", "pcm_s16le", mid])
        i, tp = loudness(mid)
        mid.unlink()
        print(f"  loudness (middle {seg:.0f} s): {i} LUFS, true peak {tp} dBFS (target {a.lufs:g} +-2)")
        if i is None or abs(i - a.lufs) > 2:
            fails.append(f"loudness {i} LUFS, target {a.lufs:g}")
        if tp is not None and tp > -0.5:
            fails.append(f"true peak {tp} dBFS is too hot")
        head = Path(str(p) + ".head.wav")
        run(FF + ["-t", 1, "-i", p, "-vn", "-c:a", "pcm_s16le", head])
        hi, _ = loudness(head) if duration(head) >= 0.4 else (None, None)
        head.unlink()
        print(f"  first second: {hi} LUFS (should be quiet: fade-in)")
    print("PASS" if not fails else "FAIL: " + "; ".join(fails))
    sys.exit(0 if not fails else 1)


# ---------------------------------------------------------------- short
def cmd_short(a):
    """Vertical 1080x1920 clip with sound, up to 60 s (YouTube Shorts limit is 3 min; 60 s is safest)."""
    c = describe(a.clip)
    if not c:
        sys.exit("not a video: " + a.clip)
    D = min(a.dur, c["duration"] - a.start, 180)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    vc = video_chain(c, a, "1080x1920")
    ins = ["-ss", a.start, "-t", D, "-i", a.clip]
    ain, has_audio = audio_inputs(a, c, a.start, D)
    if ain:
        ins += ain
    cmd = FF + ins + ["-map", "0:v", "-vf", vc] + video_encoder_args("x264", a.fps, "short")
    if has_audio:
        fo = min(1.5, D / 4)
        cmd += ["-map", f"{1 if ain else 0}:a", "-af",
                audio_chain(a) + f",loudnorm=I={a.lufs}:TP=-1.5:LRA=11,afade=t=in:d=0.3,afade=t=out:st={D - fo:.2f}:d={fo:g}"] \
            + aac_args("192k")
    cmd += ["-t", D, "-movflags", "+faststart", out]
    print(f"rendering Short {D:g}s 1080x1920", flush=True)
    run(cmd)
    print(f"-> {out}")


# ---------------------------------------------------------------- CLI
def add_look_args(p, lufs=-20.0):
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--look", choices=LOOKS, default="day")
    p.add_argument("--vf", default="", help="extra ffmpeg video filters after the look")
    p.add_argument("--tonemap", default="hable", help="HDR tone map: hable | mobius | reinhard")
    p.add_argument("--npl", type=float, default=100, help="tone-map nominal peak; higher = brighter result")
    p.add_argument("--xpos", type=float, default=0.5, help="crop position 0=left .. 1=right (Shorts)")
    p.add_argument("--drift", default="", help="DX,DY,SECONDS: cancel a slow camera drift with a moving crop")
    p.add_argument("--highpass", type=int, default=70, help="wind rumble cut, Hz")
    p.add_argument("--denoise", type=float, default=8, help="gentle noise reduction in dB, 0 = off")
    p.add_argument("--noise-floor", type=float, default=-40)
    p.add_argument("--audio", default="", help="external recorder file instead of the camera sound")
    p.add_argument("--audio-offset", type=float, default=0.0, help="recorder time = video time + this (footage.py sync)")
    p.add_argument("--lufs", type=float, default=lufs, help="sleep -20..-23, daytime -16..-18, Shorts -14")
    p.add_argument("--tp", type=float, default=-2, help="true-peak ceiling dBFS")


def main():
    need("ffmpeg")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("scan"); p.add_argument("inputs", nargs="+"); p.add_argument("--work", default="work")
    p = sub.add_parser("analyze"); p.add_argument("--work", default="work"); p.add_argument("--portrait", action="store_true")
    p = sub.add_parser("pick"); p.add_argument("--work", default="work")
    p.add_argument("--min", type=int, default=60); p.add_argument("--max", type=int, default=420)
    p.add_argument("--top", type=int, default=8)
    p.add_argument("--jump", type=float, default=12, help="scene-jump score that counts as a cut/bump")
    p.add_argument("--shake", type=float, default=1.5, help="95th pct shake (px at 320 wide) that needs --stab")
    p.add_argument("--impact-db", type=float, default=6, help="dB above the median loudness that counts as a wave hit")

    p = sub.add_parser("test"); p.add_argument("clip"); p.add_argument("start", type=float)
    p.add_argument("--dur", type=float, default=50, help="40-60 s is right for listening tests")
    p.add_argument("--out", default="work/tests/test.mp4"); p.add_argument("--size", default="1920x1080")
    p.add_argument("--timecode", action="store_true", help="burn the clip time into the corner")
    add_look_args(p)

    p = sub.add_parser("loop"); p.add_argument("clip"); p.add_argument("start", type=float); p.add_argument("dur", type=float)
    p.add_argument("--out", default="work/loop"); p.add_argument("--xfade", type=float, default=4)
    p.add_argument("--size", default="3840x2160", help="1920x1080, 2560x1440 or 3840x2160")
    p.add_argument("--stab", action="store_true", help="two-pass stabilisation before looping")
    p.add_argument("--tripod", action="store_true", help="lock to the window's first frame (slow drift)")
    p.add_argument("--codec", choices=["auto", "hevc", "x265", "x264"], default="auto",
                   help="auto = hardware H.265 if this computer has it, else x265")
    add_look_args(p)

    p = sub.add_parser("seam"); p.add_argument("loopdir")
    p = sub.add_parser("build"); p.add_argument("loopdir"); p.add_argument("--hours", type=float, default=3)
    p.add_argument("--out", default="")
    p = sub.add_parser("verify"); p.add_argument("file"); p.add_argument("--hours", type=float, default=0)
    p.add_argument("--lufs", type=float, default=-20)

    p = sub.add_parser("short"); p.add_argument("clip"); p.add_argument("start", type=float)
    p.add_argument("--dur", type=float, default=45); p.add_argument("--out", default="work/shorts/short.mp4")
    add_look_args(p, lufs=-14.0)

    a = ap.parse_args()
    {"scan": cmd_scan, "analyze": cmd_analyze, "pick": cmd_pick, "test": cmd_test, "loop": cmd_loop,
     "seam": cmd_seam, "build": cmd_build, "verify": cmd_verify, "short": cmd_short}[a.cmd](a)


if __name__ == "__main__":
    main()
