#!/usr/bin/env python3
"""Inventory a footage folder (or a whole drive) and sync field-recorder sound to camera clips.
Standard library + ffmpeg/ffprobe only. Never changes, moves or deletes your files.

  python scripts/footage.py inventory "D:/My Footage"           --out work/inventory   (Windows)
  python3 scripts/footage.py inventory "/Volumes/Drive/Footage" --out work/inventory   (macOS)
      -> work/inventory/inventory.json and work/inventory/footage-map.md
      Finds every video, audio recording and photo; camera originals vs edited exports;
      duplicates; portrait vs landscape; HDR; which recorder file overlaps which video (by clock),
      then measures the exact sync offset from the sound itself.

  python scripts/footage.py sync VIDEO.MOV RECORDER.WAV [--guess 0 --search 120]
      -> prints the offset: RECORDER time = VIDEO time + offset (use it as --audio-offset)

Times: many recorders (Zoom, Tascam) write LOCAL start time; phones write UTC. --tz (hours) is
added to UTC times to compare them; default = this computer's current UTC offset. The sound sync
measures the true offset, so a wrong clock shows up as a large "clock error", not a wrong result.
"""
import argparse
import datetime as dt
import json
import math
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import AUDIO_EXT, IMAGE_EXT, VIDEO_EXT, hms, loudness, need, probe, ratio, run  # noqa: E402

SKIP_DIRS = {".Spotlight-V100", ".Trashes", ".fseventsd", ".TemporaryItems", "$RECYCLE.BIN",
             "System Volume Information", "node_modules", ".git"}
RECORDER_HINTS = ("ZOOM", "TASCAM", "SONY", "ROLAND", "RODE", "H1", "H4", "H5", "H6", "DR-", "PCM")


def local_tz_hours():
    off = -(time.altzone if time.localtime().tm_isdst > 0 else time.timezone)
    return off / 3600


def describe(path, tz):
    j = probe(path)
    if not j:
        return {"kind": "unreadable"}
    fmt = j.get("format", {})
    tags = {k.lower(): v for k, v in fmt.get("tags", {}).items()}
    d = {"duration": float(fmt.get("duration", 0) or 0)}
    v = next((s for s in j["streams"] if s["codec_type"] == "video"
              and not s.get("disposition", {}).get("attached_pic")), None)
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    handlers = " ".join(s.get("tags", {}).get("handler_name", "") for s in j["streams"])
    enc = (tags.get("encoder", "") + " " + tags.get("encoded_by", "") + " " + tags.get("originator", "")).strip()
    if Path(path).suffix.lower() in AUDIO_EXT:
        is_rec = any(h in enc.upper() for h in RECORDER_HINTS) or (
            Path(path).suffix.lower() == ".wav" and d["duration"] > 10)
        d["kind"] = "recorder" if is_rec else "audio"
        d["device"] = enc
        if tags.get("date") and tags.get("creation_time") and ":" in tags["creation_time"][:5]:
            d["start_local"] = f"{tags['date']}T{tags['creation_time'][:8]}"      # BWF origination date + time
        else:
            m = re.search(r"(\d\d)(\d\d)(\d\d)[-_](\d\d)(\d\d)(\d\d)", Path(path).name)   # e.g. 041125-183012
            if m:
                dd, mm, yy, H, M, S = m.groups()          # Zoom style DDMMYY
                if int(mm) > 12 or int(dd) > 31:           # otherwise YYMMDD
                    yy, mm, dd = dd, mm, yy
                d["start_local"] = f"20{yy}-{mm}-{dd}T{H}:{M}:{S}"
        if a:
            d["audio_fmt"] = f"{a.get('codec_name')} {a.get('sample_rate')}Hz {a.get('channels')}ch"
        return d
    if not v:
        d["kind"] = "other"
        return d
    rot = 0
    for sdl in v.get("side_data_list", []):
        if "rotation" in sdl:
            rot = int(sdl["rotation"])
    w, h = int(v["width"]), int(v["height"])
    if abs(rot) in (90, 270):
        w, h = h, w
    trc = v.get("color_transfer", "")
    d.update({"width": w, "height": h, "fps": round(ratio(v.get("avg_frame_rate", "0/1")), 3),
              "codec": v["codec_name"], "hdr": trc in ("arib-std-b67", "smpte2084"), "audio": bool(a),
              "bitrate_mbps": round(int(fmt.get("bit_rate", 0) or 0) / 1e6, 1)})
    model = tags.get("com.apple.quicktime.model", "") or tags.get("model", "")
    if "DaVinci" in enc or "Resolve" in enc or "Premiere" in enc or "Final Cut" in enc or "CapCut" in enc:
        d["kind"], d["made_by"] = "edit-export", enc
    elif "Lavf" in enc or "HandBrake" in enc:
        d["kind"], d["made_by"] = "processed", enc
    elif model or "Core Media" in handlers or "DJI" in (enc + handlers).upper() or "GoPro" in handlers:
        d["kind"], d["made_by"] = "camera", model or ("DJI" if "DJI" in (enc + handlers).upper() else handlers.strip()[:30])
    else:
        d["kind"], d["made_by"] = "video", enc or handlers.strip()[:30]
    if "com.apple.quicktime.creationdate" in tags:      # local time with offset, e.g. 2026-04-11T17:18:04+0200
        d["start_local"] = tags["com.apple.quicktime.creationdate"][:19]
    elif tags.get("creation_time"):
        try:
            t = dt.datetime.fromisoformat(tags["creation_time"].replace("Z", "")[:19])
            d["start_local"] = (t + dt.timedelta(hours=tz)).isoformat()
        except ValueError:
            pass
    return d


# ---------------------------------------------------------------- sound sync
def envelope(path, cache, rate=10):
    """dB RMS envelope at `rate` Hz (mono), cached as JSON in `cache`."""
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    key = re.sub(r"[^A-Za-z0-9]+", "_", str(path))[-120:] + f"_{rate}"
    cp = cache / (key + ".json")
    if cp.exists():
        return json.loads(cp.read_text())
    n = 48000 // rate
    tmp = key + ".txt"          # plain name + cwd=cache: no Windows path escaping inside the filter
    run(["ffmpeg", "-hide_banner", "-nostdin", "-y", "-vn", "-i", Path(path).resolve(), "-af",
         f"aresample=48000,pan=mono|c0=0.5*c0+0.5*c1,highpass=f=150,asetnsamples=n={n}:p=0,"
         f"astats=metadata=1:reset=1,ametadata=mode=print:key=lavfi.astats.Overall.RMS_level:file={tmp}",
         "-f", "null", "-"], cwd=cache, check=False)
    env = []
    tp = cache / tmp
    if tp.exists():
        for line in tp.read_text(errors="ignore").splitlines():
            if line.startswith("lavfi.astats.Overall.RMS_level="):
                x = line.split("=", 1)[1].strip()
                env.append(-120.0 if x in ("-inf", "inf", "nan") else max(-120.0, float(x)))
        tp.unlink()
    cp.write_text(json.dumps(env))
    return env


def ncc(a, b, lag):
    """normalized correlation of a[i] with b[i+lag] over the overlap"""
    i0, i1 = max(0, -lag), min(len(a), len(b) - lag)
    if i1 - i0 < 20:
        return -1, 0
    xs, ys = a[i0:i1], b[i0 + lag:i1 + lag]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return (sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else -1), n


def find_offset(venv, wenv, guess_s, search_s, rate=10):
    """offset (s) such that RECORDER time = VIDEO time + offset; returns (offset, correlation)"""
    k = rate // 2
    va = [sum(venv[i:i + k]) / k for i in range(0, len(venv) - k + 1, k)]
    wa = [sum(wenv[i:i + k]) / k for i in range(0, len(wenv) - k + 1, k)]
    best = (-2, 0)
    g = int(round(guess_s * 2))
    for lag in range(g - int(search_s * 2), g + int(search_s * 2) + 1):
        c, _ = ncc(va, wa, lag)
        if c > best[0]:
            best = (c, lag)
    g2 = best[1] * k
    fine = (-2, g2)
    for lag in range(g2 - rate, g2 + rate + 1):
        c, _ = ncc(venv, wenv, lag)
        if c > fine[0]:
            fine = (c, lag)
    return fine[1] / rate, fine[0]


def verdict(corr):
    return "good" if corr >= 0.5 else ("check by ear" if corr >= 0.3 else "no match")


# ---------------------------------------------------------------- commands
def cmd_sync(a):
    cache = Path(a.work) / "env"
    ve, we = envelope(a.video, cache), envelope(a.audio, cache)
    off, corr = find_offset(ve, we, a.guess, a.search)
    print(f"offset {off:+.2f} s  (recorder time = video time + offset), correlation {corr:.2f} -> {verdict(corr)}")
    print(f"use:  --audio \"{a.audio}\" --audio-offset {off:.2f}")


def cmd_inventory(a):
    root = Path(a.root)
    if not root.exists():
        sys.exit(f"folder not found: {root}")
    out = Path(a.out)
    (out / "env").mkdir(parents=True, exist_ok=True)
    inv_path = out / "inventory.json"
    old = {x["path"]: x for x in json.loads(inv_path.read_text(encoding="utf-8"))} if inv_path.exists() else {}
    tz = local_tz_hours() if a.tz is None else a.tz

    items = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        for n in sorted(files):
            if n.startswith("._") or n in (".DS_Store", "Thumbs.db", "desktop.ini"):
                continue
            p = Path(dirpath) / n
            rel = p.relative_to(root).as_posix()
            ext = p.suffix.lower()
            try:
                size = p.stat().st_size
            except OSError:
                continue
            key = str(p)
            if key in old and old[key].get("size") == size and "kind" in old[key]:
                items.append(old[key])
                continue
            it = {"path": key, "rel": rel, "folder": Path(rel).parent.as_posix(), "name": n, "size": size}
            if ext in VIDEO_EXT or ext in AUDIO_EXT:
                it.update(describe(p, tz))
            elif ext in IMAGE_EXT:
                it["kind"] = "photo"
            else:
                it["kind"] = "other"
            items.append(it)
            print(f"{it['kind']:12s} {rel}", flush=True)

    groups = defaultdict(list)          # duplicates: same size and duration in another place
    for it in items:
        if it["kind"] in ("camera", "edit-export", "processed", "video", "recorder", "audio"):
            groups[(it["size"], round(it.get("duration", 0), 2))].append(it)
    for g in groups.values():
        g.sort(key=lambda x: x["rel"])
        for x in g[1:]:
            x["duplicate_of"] = g[0]["rel"]

    def span(it):
        t = dt.datetime.fromisoformat(it["start_local"][:19])
        return t, t + dt.timedelta(seconds=it["duration"])

    vids = [x for x in items if x["kind"] in ("camera", "video") and "start_local" in x and not x.get("duplicate_of")]
    recs = [x for x in items if x["kind"] == "recorder" and "start_local" in x and not x.get("duplicate_of")]
    for c in vids:
        try:
            c0, c1 = span(c)
        except ValueError:
            continue
        for r in recs:
            try:
                r0, r1 = span(r)
            except ValueError:
                continue
            ov = (min(c1, r1) - max(c0, r0)).total_seconds()
            if ov <= min(5, c["duration"] * 0.5):
                continue
            guess = (c0 - r0).total_seconds()
            rec = next((m for m in c.get("recorder", []) if m["wav"] == r["rel"] and "sync_offset_s" in m), None)
            if not rec:
                rec = {"wav": r["rel"], "clock_offset_s": round(guess, 1), "overlap_s": round(ov, 1)}
                if not a.no_sync and c.get("audio"):
                    print(f"sync {c['rel']}  <->  {r['rel']}", flush=True)
                    off, corr = find_offset(envelope(c["path"], out / "env"), envelope(r["path"], out / "env"),
                                            guess, search_s=90)
                    rec.update({"sync_offset_s": round(off, 2), "sync_corr": round(corr, 2),
                                "clock_error_s": round(off - guess, 1)})
            c["recorder"] = [m for m in c.get("recorder", []) if m["wav"] != rec["wav"]] + [rec]
            r.setdefault("videos", [])
            if c["rel"] not in r["videos"]:
                r["videos"].append(c["rel"])

    for it in items:
        if (it["kind"] == "recorder" and not it.get("duplicate_of")) or it.get("recorder"):
            if "lufs" not in it and it.get("duration", 0) > 3:
                it["lufs"], it["peak_db"] = loudness(it["path"])

    inv_path.write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
    write_md(items, out / "footage-map.md", root)
    print(f"-> {inv_path}\n-> {out / 'footage-map.md'}")


def write_md(items, path, root):
    by = defaultdict(list)
    for it in items:
        by[it["folder"]].append(it)
    L = [f"# Footage map: {Path(root).name}", "",
         "Kinds: **camera** = original from a phone/drone/camera; **edit-export** = exported from an editor; "
         "**processed** = re-saved by ffmpeg/HandBrake; **recorder** = field recorder WAV; "
         "duplicate = same size and length elsewhere.", ""]
    tot = defaultdict(float)
    for it in items:
        if it.get("duration") and not it.get("duplicate_of"):
            key = it["kind"] + (" portrait" if it.get("height", 0) > it.get("width", 1) else "")
            tot[key] += it["duration"]
    L += ["Total without duplicates: " + ", ".join(f"{k} {hms(v)}" for k, v in sorted(tot.items())), ""]
    for folder in sorted(by):
        xs = [x for x in by[folder] if x["kind"] not in ("photo", "other")]
        others = [x["name"] for x in by[folder] if x["kind"] in ("photo", "other")]
        if not xs and not others:
            continue
        L += [f"## {folder}", ""]
        if xs:
            L += ["| File | Kind | Length | Format | Start (local) | Sound / recorder | Notes |",
                  "|---|---|---|---|---|---|---|"]
        for it in sorted(xs, key=lambda x: (x.get("start_local", "9"), x["name"])):
            k = it["kind"]
            fmt = ""
            if "width" in it:
                fmt = f"{it['width']}x{it['height']} {it['fps']:g}fps {it['codec']}"
                fmt += " PORTRAIT" if it["height"] > it["width"] else ""
                fmt += " HDR" if it.get("hdr") else ""
            elif "audio_fmt" in it:
                fmt = it["audio_fmt"]
            snd = ""
            if "width" in it:
                snd = "camera sound" if it.get("audio") else "no sound"
                for m in it.get("recorder", []):
                    if "sync_offset_s" in m:
                        snd += f"; {Path(m['wav']).name} @{m['sync_offset_s']:+.1f}s ({verdict(m['sync_corr'])})"
                    else:
                        snd += f"; {Path(m['wav']).name} (by clock {m['clock_offset_s']:+.0f}s)"
            elif k == "recorder":
                if it.get("lufs") is not None:
                    snd = f"{it['lufs']:.0f} LUFS, peak {it['peak_db']:.0f} dBFS" + (" **quiet**" if it["lufs"] < -35 else "")
                if it.get("videos"):
                    snd += "; for: " + ", ".join(Path(v).name for v in it["videos"])
            notes = []
            if it.get("duplicate_of"):
                notes.append(f"duplicate of {it['duplicate_of']}")
            if it.get("made_by"):
                notes.append(str(it["made_by"])[:30])
            L.append(f"| {it['name']} | {k} | {hms(it.get('duration', 0))} | {fmt} | "
                     f"{it.get('start_local', '')[5:16].replace('T', ' ')} | {snd} | {'; '.join(notes)} |")
        if others:
            L += ["", f"Other files ({len(others)}): " + ", ".join(others[:12]) + (" ..." if len(others) > 12 else "")]
        L.append("")
    Path(path).write_text("\n".join(L), encoding="utf-8")


def main():
    need("ffprobe")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("inventory", help="map a folder or drive")
    p.add_argument("root"); p.add_argument("--out", default="work/inventory")
    p.add_argument("--tz", type=float, default=None, help="hours to add to UTC camera times (default: this computer's)")
    p.add_argument("--no-sync", action="store_true", help="skip the sound-based sync (faster)")
    p = sub.add_parser("sync", help="offset between one video and one recorder file")
    p.add_argument("video"); p.add_argument("audio")
    p.add_argument("--guess", type=float, default=0.0, help="expected offset in seconds, if known")
    p.add_argument("--search", type=float, default=120.0, help="search +- this many seconds around the guess")
    p.add_argument("--work", default="work")
    a = ap.parse_args()
    {"inventory": cmd_inventory, "sync": cmd_sync}[a.cmd](a)


if __name__ == "__main__":
    main()
