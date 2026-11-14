---
name: shorts
description: Make vertical YouTube Shorts (9:16, up to 60 s) from the user's own footage - a simple built-in cut with clean sound for ambient/no-talking channels, or, for talking, cooking, tutorial and story Shorts, the external MIT skill packs reel-skills and youtube-agent-skill (install instructions and attribution here; their code is not copied into this project).
---

# Shorts

Windows: `python`, macOS/Linux: `python3`. Always make **one test Short first** and let the user
watch it with sound before making a batch.

## Ask first (numbered, one at a time)

1. "What kind of Shorts? 1. Calm moment from my long video (no talking) 2. Cooking / recipe steps
   (e.g. a smoothie from start to glass) 3. Me talking to camera 4. Other"
2. "Where does the vertical picture come from? 1. I filmed vertically 2. Cut it out of my horizontal
   video 3. Not sure"
3. "How long? 1. 15–20 s 2. 30 s 3. 45–60 s" (YouTube allows up to 3 min, but ≤ 60 s is the safest
   for reach and for every country.)

## A. Built-in: calm / ambient / no-talking Shorts

```
python3 scripts/ambient.py short "<clip>" <start> --dur 30 --look day --out output/shorts/short01.mp4
```
- 1080x1920, H.264, sound cleaned (wind cut, gentle denoise), loudness **-14 LUFS**, soft 0.3 s fade-in, 1.5 s fade-out.
- From a horizontal clip it crops the middle; move the crop with `--xpos 0.2` (left) … `0.8` (right).
- With a recorder: `--audio "<wav>" --audio-offset <s>` (offset from `scripts/footage.py sync`).
- Hook text on screen: `--text "Wait for the big one\nreal sound"` (`\n` = new line), shown for
  `--text-dur 3` seconds (0 = whole Short), placed in the upper-middle safe area.
- From an existing long video: find 3–8 strong moments (ask the user, or look at `pick` contact
  sheets / the loudest wave hits), make ONE test Short, then the rest with the same settings.
- Good starts: the first second must already show the best thing (a wave breaking, juice pouring).
- Title ≤ 60 chars, hook first; add `#shorts` and 2 topic hashtags to the description.
  Link the long video in the description ("Full 10-hour version: …").

For a **cooking / smoothie** Short without voice: ask the user for the clips in order
(ingredients → blending → pouring → glass), make a test of each clip with `short` at the right
start, then join them:
```
# list.txt lines: file 'output/shorts/part1.mp4'   (one per part, same settings for all parts)
ffmpeg -f concat -safe 0 -i list.txt -c copy output/shorts/smoothie-01.mp4
```
Keep parts 2–6 s each; total 20–40 s. Only the user's own music or no music (or real kitchen sound).

## B. External skill packs (talking, edits, captions, hooks, packaging)

These are separate open-source projects by other authors, **MIT licensed**. We do not copy their
code into this repository; install them only if the user wants them, **ask first** (it downloads
code from GitHub). Requires `git`.

### reel-skills — by danilbogdan · https://github.com/danilbogdan/reel-skills · MIT
Vertical reels from your own footage: pause cutting, clean voice at -14 LUFS, captions, b-roll index,
video analysis from a link, hook checking.
```
git clone https://github.com/danilbogdan/reel-skills.git ../reel-skills
cd ../reel-skills
scripts/doctor.sh          # macOS/Linux; on Windows run it in "Git Bash" (comes with Git for Windows)
scripts/run_demo.sh        # should print "demo ok"
```
To make its skills available in this project, copy the skill folders you need from
`../reel-skills/skills/<name>` into this project's `.claude/skills/<name>` (or use its
`scripts/install.sh ~/.claude/skills` to install for all projects). Note: some of its skills
(`media-search`, `videogen`) use stock media or AI video — **do not use them for "real sound / no AI"
channels** unless the user explicitly wants it.

### youtube-agent-skill — by Jake Schincariol · https://github.com/Jakeschincariol/youtube-agent-skill · MIT
Eleven skills for running a channel: `/yt-script`, `/yt-package` (title + thumbnail together),
`/yt-shorts` (cut Shorts from long videos), `/yt-seo`, `/yt-chapters`, `/yt-retention`, `/yt-viral`,
`/yt-plan`, `/yt-edit`, `/yt-comment`, `/yt-audit`. It writes; it never uploads.
In Claude Code (any OS):
```
/plugin marketplace add Jakeschincariol/youtube-agent-skill
/plugin install youtube-agent
```
Or manually (macOS/Linux):
```
git clone https://github.com/Jakeschincariol/youtube-agent-skill.git ../youtube-agent-skill
cp -r ../youtube-agent-skill/skills/yt-* .claude/skills/
```
Windows PowerShell:
```
git clone https://github.com/Jakeschincariol/youtube-agent-skill.git ..\youtube-agent-skill
Copy-Item -Recurse ..\youtube-agent-skill\skills\yt-* .claude\skills\
```
Optional: its `templates/voice.md` describes the creator's voice; fill it in with the user.

Installed copies of these projects are third-party code: keep their LICENSE files, and do not commit
them into this repository (the copied `yt-*` / reel folders are git-ignored on purpose).

## Before posting (any Short)

- Plays fine on a phone, sound on: no clipping, nothing cut off by the YouTube buttons on the right
  and the caption area at the bottom (keep text in the middle 70 %).
- `python3 scripts/ambient.py verify output/shorts/short01.mp4 --lufs -14`
- The user uploads; never publish for them without an explicit yes.
