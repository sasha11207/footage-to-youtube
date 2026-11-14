# Example: 10-hour night ocean video

Based on a real project from a "Real Sound · No AI" sleep channel; names, places, file names and
offsets are replaced with illustrative ones.

**Material:** one 14-minute iPhone clip (4K HDR, tripod) of a calm bay in daylight, plus a
32-bit float WAV from a small field recorder placed on the beach. The night look was made from
the daytime footage ("day for night"); a 3-hour daytime version was made from the same loop
with `--look day`.

## Commands that were run (macOS; on Windows use `python` and `D:/...` paths)

```bash
python3 scripts/footage.py inventory "/Volumes/Drive/Ocean" --out work/inventory
#   IMG_0420.MOV <-> ZOOM0007.WAV  @+18.4s (good)

python3 scripts/ambient.py scan "/Volumes/Drive/Ocean/IMG_0420.MOV" --work work
python3 scripts/ambient.py analyze --work work
python3 scripts/ambient.py pick --work work --min 240 --max 420

# tests with sound, approved by ear (first round: "2 — 0:31 wind" -> --highpass 90)
python3 scripts/ambient.py test "/Volumes/Drive/Ocean/IMG_0420.MOV" 95 --look night --highpass 90 \
    --audio "/Volumes/Drive/Ocean/ZOOM0007.WAV" --audio-offset 18.4 --out work/tests/t2-night.mp4

python3 scripts/ambient.py loop "/Volumes/Drive/Ocean/IMG_0420.MOV" 95 300 --look night --highpass 90 \
    --size 3840x2160 --audio "/Volumes/Drive/Ocean/ZOOM0007.WAV" --audio-offset 18.4 --out work/loop-night
python3 scripts/ambient.py seam  work/loop-night
python3 scripts/ambient.py build work/loop-night --hours 10 --out output/night-ocean-10h.mp4
python3 scripts/ambient.py verify output/night-ocean-10h.mp4 --hours 10 --lufs -20     # PASS

python3 scripts/thumb.py work/loop-night/loop.mp4 42 --look night --big "10 HOURS" \
    --sub "Night ocean & harbour lights" --out output/thumbs
```

## Metadata

[`night-ocean-10h.meta.json`](night-ocean-10h.meta.json): title pattern, honest description
structure, tags, two playlists, a scheduled evening publish time, and Spanish + German
translations. The user uploaded the file as Private in YouTube Studio, then:

```bash
python3 scripts/yt.py list
python3 scripts/yt.py apply <VIDEO_ID> output/night-ocean-10h.meta.json --dry-run
python3 scripts/yt.py apply <VIDEO_ID> output/night-ocean-10h.meta.json        # after the owner's yes
```
