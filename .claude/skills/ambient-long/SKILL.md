---
name: ambient-long
description: Make a long (1-10+ hour) ambient / relaxing / sleep YouTube video from the user's own footage and field recordings - shooting advice, footage inventory, recorder sync, 40-60 s test clips with sound for approval, seamless loop, long build by stream copy, verification, thumbnail and metadata. Use for ocean, rain, forest, fireplace, city-at-night, "sleep sounds" and similar long videos.
---

# Long ambient video pipeline (proven)

Commands below use `python3` (macOS/Linux). On **Windows** write `python` and paths like
`"D:/Footage/Beach/IMG_0420.MOV"`. Work in `work/`, finished files in `output/` (or the user's drive).

## Overview

```
footage.py inventory  ->  ambient.py scan/analyze/pick  ->  TEST CLIPS (user listens)  ->
ambient.py loop  ->  seam (user checks)  ->  build --hours N  ->  verify  ->  thumb.py  ->  meta.json  ->  yt.py apply
```

Typical products: **3 h "day"** video (natural colours) and **10 h "night"** video for sleep
(the same daytime footage graded dark blue: "day for night", `--look night`). One good 5-minute
window of footage is enough for both.

## 0. If the user has not filmed yet — shooting advice (tell them in plain words)

- **Tripod or a stable support**, phone/camera locked, no zoom, no panning. 10–20 minutes per shot;
  we need at least 6–8 calm minutes in one piece.
- Landscape (horizontal) for long videos; vertical only for Shorts.
- iPhone: 4K 30 fps. HDR (Dolby Vision) is OK — the tools tone-map it. Turn off "Action mode".
  Lock exposure/focus (long-press on the screen). Avoid the sun in the frame (flicker in clouds).
- **Sound**: a separate recorder (Zoom H1/H4, Tascam, Rode…) with a wind cover (fur), placed
  low and out of the wind, 32-bit float if available. Start the recorder first, then the camera,
  and **clap once** in front of the camera (makes syncing certain). Phone sound is fine for calm days.
- No people, voices, music, dogs, engines in the window we'll use; watch for drops on the lens.
- Write down the place name — it goes into the description (honesty sells for real-sound channels).

## 1. Inventory and sync

```
python3 scripts/footage.py inventory "<footage folder>" --out work/inventory
```
Read `work/inventory/footage-map.md`. A recorder line with `@+12.3s (good)` means: recorder time =
video time + 12.3 s → use `--audio "<wav>" --audio-offset 12.3`. `(check by ear)` / `(no match)` →
run `footage.py sync VIDEO WAV --guess <clock offset> --search 300` and confirm with a test clip.

## 2. Find loop windows

```
python3 scripts/ambient.py scan "<folder or files>" --work work
python3 scripts/ambient.py analyze --work work            # minutes per clip; run in background for many clips
python3 scripts/ambient.py pick --work work --min 240 --max 420 --top 8
```
Each pick has a contact sheet `work/pickNN.jpg` — open it, check for people, birds, drops, tilted
horizon. Prefer: high `motion` (living water), low `shake95`, no `SCENE-JUMP`, low `wind`.
`SHAKY(--stab)` → add `--stab` (or `--tripod` for a slow drift) to test/loop.
Default loop length **300 s** with **4 s** crossfade — long enough that nobody notices the repeat.

## 3. Test clips WITH SOUND — the user approves by ear

For the 2–4 best windows, and for each look the user wants (e.g. `day` and `night`):
```
python3 scripts/ambient.py test "<clip>" <start> --dur 50 --look day   --audio "<wav>" --audio-offset <off> --out work/tests/t1-day.mp4
python3 scripts/ambient.py test "<clip>" <start> --dur 50 --look night --audio "<wav>" --audio-offset <off> --out work/tests/t1-night.mp4
```
(Without a recorder, leave out `--audio`/`--audio-offset` — the camera sound is used.)
Use `--timecode` if it helps the user name the second. A 50 s test takes ~1–3 min to render.
Open the files for the user and ask them to listen **with headphones** and report
`test number — second — problem`. Typical fixes:

| User hears / sees | Fix |
|---|---|
| wind rumble, low "booming" | `--highpass 90` (or 120), or a calmer window |
| hiss | `--denoise 12` (max ~15, higher sounds "underwater") |
| voice / car / dog at 0:37 | pick another window, or build the sound from clean pieces with `audioloop.py` |
| sound "jumps" or doubles | wrong `--audio-offset`: re-run `footage.py sync` |
| too dark / bright | `--npl 150` brighter (HDR), or `--vf "eq=brightness=0.03"`; night darker: `--vf "eq=brightness=-0.03"` |
| shaky | `--stab` or `--tripod` |

Re-test only what changed. Continue only after the user says **ok**.

## 4. Loop, seam check

```
python3 scripts/ambient.py loop "<clip>" <start> 300 --look day --size 3840x2160 --audio "<wav>" --audio-offset <off> --out work/loop-day
python3 scripts/ambient.py seam work/loop-day
```
`--size 3840x2160` for 4K sources, `1920x1080` otherwise. `--codec auto` picks the hardware H.265
encoder (Mac VideoToolbox, NVIDIA, Intel) or x265. Show the user `work/loop-day/seam_check.mp4`
(the seam is at 0:05 — nothing should happen there).

Sound from clean pieces instead (when the window's own sound has problems):
```
python3 scripts/audioloop.py work/loop-day/loop.wav --len 300 --k 2 "<wav>@120-290" "<wav>@600-760" --process
```
then `seam` again.

## 5. Build and verify

```
python3 scripts/ambient.py build work/loop-day   --hours 3  --out output/<name>-3h.mp4
python3 scripts/ambient.py build work/loop-night --hours 10 --out output/<name>-10h.mp4
python3 scripts/ambient.py verify output/<name>-10h.mp4 --hours 10 --lufs -20
```
Build is stream copy (minutes, not hours); the sound is encoded once over the full length with a
4 s fade-in and 10 s fade-out. Size: a 300 s 4K loop ≈ 0.4–1.2 GB → ×N. Check free disk space first.
`verify` must say **PASS**. Then delete `work/loop-*/concat.txt` leftovers and old tests you made
(only after the user is happy; keep one final per output).

Loudness targets: sleep / night **-20 LUFS** (-20 … -23), daytime relaxing -18 … -16, Shorts -14.

## 6. Thumbnail

```
python3 scripts/thumb.py work/loop-night/loop.mp4 42 --look night --big "10 HOURS" --sub "Night ocean for deep sleep" --out output/thumbs
```
Big short text (2–3 words), one sub-line, the `REAL SOUND · NO AI` badge only if true (`--badge ""` removes it).
Ask the user to choose the frame second (or show 3 options).

## 7. Metadata

Copy `templates/meta.template.json` → `output/<name>.meta.json`; see `examples/night-ocean/` for a
complete, good example. Proven structure:
- **Title** (≤ 100 chars): `What & where · Length for Use · Promise 4K`
  e.g. `Night Ocean Waves by the Harbour · 10 Hours for Deep Sleep · Real Sound, No AI 4K`
- **Description**: 1) two calm sentences of what you see/hear; 2) where/how it was filmed and recorded
  (real place, own recording); 3) "No music. No voices. No AI." (only if true); 4) "Put it on for:" 3–4 bullets;
  5) one line about the channel; 6) 📍 place, 🎥 4K · 🎙 natural sound; 7) 3 hashtags.
- **Tags**: 12–20, most specific first; total under ~480 characters.
- `categoryId`: 19 Travel & Events, 22 People & Blogs, 24 Entertainment, 26 Howto & Style.
- `localizations`: translate title + description for the languages the user chose.
- `publishAt` (UTC, ISO) only if the user wants scheduling. Night videos: publish in the evening
  of the main audience's time zone.

Then: user uploads as Private → `yt.py list` → `yt.py apply <ID> output/<name>.meta.json --dry-run`
→ show → on **yes** run without `--dry-run`. Never publish publicly without an explicit yes.

## Other "looks"

`--look none | day | storm | night | sleep`. `sleep` = warm, soft vignette. Extra filters: `--vf "..."`
(any ffmpeg video filters, applied after the look). For rain/forest/fireplace the same pipeline
works: choose `day` or `none`, a lower `--highpass` (50) for fire crackle, and `--denoise 0` for rain.
