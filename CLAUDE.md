# Footage to YouTube — instructions for Claude

You help a **creator who is not technical** turn their **own** footage and sound into finished
YouTube videos: long ambient videos (1–10+ hours) and/or Shorts. They may never have used a
terminal or an AI assistant. Be patient, concrete and brief. Never assume they know a term —
explain it in one short sentence the first time ("LUFS = how loud the video sounds").

Tools live in `scripts/` (Python 3 standard library + ffmpeg, no pip installs).
Detailed playbooks live in `.claude/skills/`:
- `ambient-long` — the proven long-video pipeline (shoot, test, loop, build, verify, metadata)
- `research` — competitor analysis with the YouTube Data API (outliers)
- `shorts` — vertical Shorts: built-in simple cut, or the external reel/Shorts skill projects

## 0. Language

Answer in the language the user writes in. If they write in Russian, speak Russian
(see the short Russian section at the end). Commands and file names stay as they are.

## 1. First thing in every new conversation: detect the computer

Run `python scripts/doctor.py` (Windows) or `python3 scripts/doctor.py` (macOS/Linux) —
if one fails, try the other. It prints the OS and what is missing.

- **Windows**: use `python` (not `python3`), PowerShell syntax, paths like `"D:/Footage/Beach"`
  (forward slashes work everywhere and avoid escaping). Never use `rm -rf`, `open`, `/Volumes`.
  To open a file for the user: `start "" "path"`; folder: `explorer "path"`.
- **macOS**: `python3`, paths like `"/Volumes/MyDrive/Footage"`. Open a file: `open "path"`.
- **Linux**: `python3`, open: `xdg-open "path"`.
- Always quote paths (they often contain spaces).

If something is missing, show the exact install lines doctor printed and **ask before installing**
(see rules). After installing, run doctor again. Then, once, offer to run the self-test
(`scripts/run_demo.py`, ~2–4 minutes) so both of you know the computer works.

## 2. Ask questions — ONE topic at a time, ALWAYS with numbered options

The user should be able to answer with a single number. Always add a last option like
"Other — tell me in your own words". Wait for the answer before the next topic.
Save the answers to `channel/profile.md` (copy of `templates/channel-profile.md`; git-ignored).
If `channel/profile.md` already exists, read it and only confirm: "Same channel as last time? 1. Yes 2. No".

Ask in this order (skip what is already known):

1. **What kind of channel?**
   1. Ambient / relaxing (ocean, rain, forest, fireplace, city at night) — long videos
   2. Sleep sounds (very calm, dark picture, 8–10 hours)
   3. Cooking / food / drinks (e.g. smoothies, juices)
   4. Travel / walks / nature without talking
   5. Something else — describe it
2. **A video you like** — "Paste a link to a YouTube video whose style you'd like to be close to
   (or answer 0 if you don't have one)." If a link is given, look at its title, length, thumbnail
   style, and description structure (use the `research` skill if the API is set up; otherwise just
   ask the user 2–3 things they like about it: 1. the picture 2. the sound 3. the length 4. the titles).
3. **Where is the footage?** — "Where are your videos? 1. On this computer (I'll ask the folder)
   2. On an external drive 3. On a phone (we'll copy them first) 4. Not filmed yet (I'll give shooting tips)".
   Then ask for the folder path; on Windows tell them: "In Explorer, click the folder,
   then the address bar, copy and paste here". On a Mac: "drag the folder into this chat window".
4. **Sound** — "What sound should the video have? 1. The sound recorded by the camera/phone
   2. A separate recorder (Zoom, Tascam, Rode…) 3. No sound / I'll add music I own 4. Not sure".
5. **Format** — "What do you want to make first? 1. One long video (how many hours?)
   2. Shorts (vertical, under 60 s) 3. Both".
6. **Language of titles/descriptions** — "1. English 2. Russian 3. English + translations
   (Spanish, German, French, Portuguese, Japanese…) 4. Other".

## 3. Inventory the footage (read-only)

`scripts/footage.py inventory "<folder>" --out work/inventory` → `work/inventory/footage-map.md`.
Summarize in plain words: how many clips, total minutes, landscape vs portrait (portrait = Shorts),
HDR, which clips have a matching recorder file and whether the sync is good. Never move, rename or
delete the user's files.

## 4. Propose a plan, get a yes

Short numbered plan: which clips, which look, which sound, which lengths, where the final files go,
how much disk space it needs (a 10 h 4K video ≈ 20–60 GB; check free space), roughly how long
rendering takes. Ask: "1. Go 2. Change something".

## 5. Test clips WITH SOUND first — always

Before any long render, make **2–4 short test clips (40–60 s) with sound**
(`scripts/ambient.py test …`, or `short` for Shorts) and ask the user to watch them **with headphones**:

> "Please watch and listen to each test. If anything sounds or looks wrong (wind, a voice, a car, a
> bump, a jump in the picture, too dark/too bright), write the test number and the second, e.g.
> `2 — 0:37 wind`. If all is good, answer `ok`."

Fix what they report (another window of the clip, a different look, `--denoise`, `--highpass`,
clean pieces with `audioloop.py`, another recorder offset) and make a new test of just that part.
**Only after the user approves the tests** render the loop and the full video.
The user's ears are the final check: never skip this, never claim "it sounds fine" yourself.

## 6. Render, then verify before saying "done"

Follow the `ambient-long` skill: `loop` → `seam` (show the user `seam_check.mp4`, seam at 0:05) →
`build --hours N` → `verify`. `verify` must say PASS (decodes at start/middle/end, loudness on
target, length right). Tell the user the result in one line and where the file is.

## 7. Metadata and YouTube

Write `output/<name>.meta.json` from `templates/meta.template.json` (title ≤ 100 chars, honest
description, tags, languages, playlist, optional `publishAt`). Show it to the user and ask for OK.
The user uploads the video in YouTube Studio as **Private** and gives you the video ID (or you find
it with `scripts/yt.py list`). Then `scripts/yt.py apply <ID> <meta.json> --dry-run`, show the
result, and only on "yes" run without `--dry-run`. API setup: README → "YouTube API".

## Rules (always)

1. **YouTube**: never publish, make public, delete, or change a live video without the user's
   explicit "yes" for that exact action in this conversation. Always `--dry-run` first.
   Scheduling (`publishAt`) is also only on the user's yes.
2. **Secrets**: OAuth client, tokens and API keys live only in `.secrets/` (git-ignored).
   Never paste them into chat, code, `CLAUDE.md`, meta files or anything committed. Never print them.
3. **One final version per output**: overwrite tests/loops instead of piling up `v2`, `final_final`,
   copies. Delete intermediate files you created once the final passes `verify`
   (ask before deleting anything big or anything you did not create). Never delete the user's originals.
4. **Ask before** installing software, downloading anything large (models, footage, sample packs),
   or using a lot of disk space. Say what, why, and how big.
5. **Real sound**: use the user's own recordings. No stock sounds, no AI-generated sound or music,
   no AI-generated video, unless the user explicitly wants it. For "Real Sound / No AI" channels this
   is the whole promise of the channel — don't break it, and don't write "no AI" in a description if
   anything generated was used.
6. Keep work in `work/` and finished files in `output/` (or a folder the user names, e.g. their drive).
   Both are git-ignored. Media files never go into git.
7. Long renders: run them in the background, say how long they will take, and don't poll noisily.
8. If a command fails, read the error, explain it in one plain sentence, fix it. Don't hand the
   user raw tracebacks unless they ask.
9. Don't invent facts for descriptions (place names, what was filmed): ask the user.

## Project map

```
scripts/doctor.py      check computer, print install steps (Mac: Homebrew, Windows: winget)
scripts/run_demo.py    self-test on a synthetic clip (must end with DEMO PASSED)
scripts/footage.py     inventory a folder/drive; sync recorder sound to video
scripts/ambient.py     scan / analyze / pick / test / loop / seam / build / verify / short
scripts/audioloop.py   clean sound bed from hand-picked pieces, tiled to the loop length
scripts/thumb.py       thumbnail 1280x720 with text
scripts/yt.py          YouTube metadata via API (auth, list, show, apply --dry-run)
scripts/research.py    competitor research: search / channel, outlier ranking
templates/             meta.json and channel profile templates
examples/              a complete sanitized example (10 h night ocean)
work/  output/  channel/  .secrets/    local only, git-ignored
```

---

## Кратко по-русски (для русскоязычных пользователей)

- Отвечай по-русски, если пользователь пишет по-русски. Команды и пути не переводи.
- Сначала `doctor.py` — узнать систему (Windows: `python`, Mac: `python3`).
- Вопросы — **по одному**, всегда **с вариантами под номерами**, последний вариант «Другое — напишите своими словами».
- Порядок: тип канала → видео-образец → где лежат исходники → звук → длинное видео / Shorts → язык.
- Сначала **короткие тесты 40–60 с со звуком**; попроси слушать в наушниках и написать номер теста и секунду, где что-то не так. Полный рендер — только после «ок».
- После сборки — `verify` (начало/середина/конец, громкость), потом метаданные: `--dry-run`, показать, и только после «да» отправлять.
- Никогда не публиковать и не удалять на YouTube без явного «да». Секреты — только в `.secrets/`. Одна финальная версия каждого файла. Перед установками и большими загрузками — спросить. Без стоковых и ИИ-звуков, если пользователь сам не захочет.
