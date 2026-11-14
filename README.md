# Footage to YouTube

**English** · [Українська](README.uk.md)

> Turn your own footage into long YouTube videos (and Shorts) with Claude Code: ask, test with short previews, then render. Mac & Windows.

You talk to **Claude Code** in plain language. Claude asks you simple questions (you answer with a
number), looks through your footage folder, makes **short test clips with sound** for you to check,
and only after you say "ok" makes the full video, checks it, and writes the title and description.
You don't need to know how to program. You always upload and publish yourself.

Everything runs on your own computer (macOS or Windows; Linux works too). Your footage never
leaves your computer and never goes into git.

---

## What it can do

- **Long relaxing videos (1–10+ hours)** from your own clips: ocean, rain, forest, fireplace, city at
  night, sleep sounds. A 5-minute calm piece becomes a seamless loop — no visible or audible "jump".
- **Real field sound**: syncs a separate recorder (Zoom, Tascam, Rode…) to your video automatically,
  gently removes wind rumble and hiss, sets a comfortable loudness for sleep.
- **"Day for night"**: a dark-blue night version made from your daytime footage.
- **iPhone / DJI HDR** footage is converted to normal colours automatically.
- **Short test clips first** (40–60 s, with sound): you listen and say what's wrong *before* hours of rendering.
- **Checks the finished file**: plays at start, middle and end, loudness on target, right length.
- **Shorts**: vertical 1080×1920 clips with a hook text on screen; links to two free skill packs for
  talking, cooking and tutorial Shorts.
- **Fix a noise** (a bark, a car) at a given second in a finished video.
- **Thumbnails** with big text.
- **Titles, descriptions, tags, translations, playlists, scheduling** — filled in on YouTube for you
  (after you upload as Private and say "yes").
- **Research**: what works in your niche, which videos beat their channel's normal level ("outliers"),
  a channel's upload rhythm, a month plan.

---

## 10-minute setup

You need: **Claude Code** (an Anthropic account), **Python 3**, **ffmpeg** and **git**.

### macOS

1. Open **Terminal** (⌘ + Space, type "Terminal", Enter).
2. Install Homebrew if you don't have it: copy the command from https://brew.sh and paste it into Terminal.
3. Install the tools:
   ```bash
   brew install python ffmpeg git
   ```
4. Install Claude Code: https://claude.com/claude-code (desktop app or terminal version).
5. Download this project and check your computer:
   ```bash
   cd ~
   git clone https://github.com/sasha11207/footage-to-youtube.git
   cd footage-to-youtube
   python3 scripts/doctor.py
   python3 scripts/run_demo.py
   ```
   The demo takes 3–5 minutes and must end with **DEMO PASSED**.

### Windows 10 / 11

1. Open **PowerShell** (Start → type "PowerShell" → Enter).
2. Install the tools, one line at a time (answer "Yes" if Windows asks):
   ```powershell
   winget install -e --id Python.Python.3.12
   winget install -e --id Gyan.FFmpeg
   winget install -e --id Git.Git
   ```
3. **Close PowerShell and open it again** (so it finds the new programs).
4. Install Claude Code: https://claude.com/claude-code
5. Download this project and check your computer:
   ```powershell
   cd $HOME
   git clone https://github.com/sasha11207/footage-to-youtube.git
   cd footage-to-youtube
   python scripts/doctor.py
   python scripts/run_demo.py
   ```
   Must end with **DEMO PASSED**. If `python` opens the Microsoft Store, close it, reopen PowerShell
   and try again (or install Python from https://www.python.org/downloads/ and tick
   "Add python.exe to PATH").

Rendering is faster with an NVIDIA or Intel graphics card (used automatically) and on Apple-silicon
Macs. Keep 60+ GB free for a 10-hour 4K video.

### Open it in Claude Code

Open the `footage-to-youtube` folder in Claude Code (desktop app: choose the folder; terminal:
`cd footage-to-youtube`, then `claude`). Claude reads `CLAUDE.md` and knows the whole workflow.
Write in any language — Claude answers in the language you write in.

---

## How to ask

Copy a prompt, change the parts in `<…>`, and paste it into Claude Code. Claude will ask a few
questions back — **one at a time, with numbered answers** — so you can just reply with a number.

### 1. A long ambient video from my footage
> Here is my folder `<D:/Footage/Ocean>`. Make a 10-hour night ocean video like this reference: `<YouTube link>`. Show me short test clips first.

Claude asks: which sound to use (camera or recorder), day or night look, where to save.
You get: 2–4 test clips to listen to → after your "ok", the 10-hour video, a seam check, a thumbnail and a ready title/description.

### 2. Shorts from my existing long video
> Cut 5 Shorts from my video `<D:/Videos/rain-3h.mp4>`. Write hooks and on-screen text, vertical 1080x1920.

Claude asks: how long each Short should be, which moments you like, the text language.
You get: one test Short first, then 5 vertical clips with hook text, plus a title and hashtags for each.

### 3. Analyze a channel
> Analyze the channel `<https://www.youtube.com/@SomeChannel>`: what works, titles, lengths, upload rhythm.

Claude asks: whether the YouTube connection is set up (if not, it walks you through it).
You get: the channel's top videos and outliers, which titles and lengths win, how often and on which days they upload.

### 4. Analyze a niche
> Find what works in the niche "sleep ocean sounds" and rank the outliers.

Claude asks: long videos or Shorts, how recent (last year? last 3 months?), which language/country.
You get: a ranked table of videos that did far better than their channel usually does, and 5–8 plain conclusions.

### 5. Compare my channel with competitors
> Compare my channel `<link>` with these competitors: `<link>`, `<link>`, `<link>`. Give me one main fix.

Claude asks: what your goal is (more views, more subscribers, longer watch time).
You get: a short side-by-side comparison and **one** most important change to make next, with the reason.

### 6. Titles, descriptions, tags, translations — and schedule it
> I uploaded my video as Private. Write the title, description, tags and translations into English, Spanish and German, set the thumbnail, and schedule it for Friday 20:00.

Claude asks: what and where you filmed (it never invents facts), your time zone, which playlist.
You get: a preview of every change ("dry run") → after your "yes", everything is filled in on YouTube. Nothing goes public without your yes.

### 7. Plan a month of uploads
> Plan my uploads for next month based on what works in my niche and the footage I have.

Claude asks: how many uploads a week you can really do, long videos, Shorts or both.
You get: a calendar table — date, topic, length, title draft and which of your clips to use.

### 8. Fix the sound in a finished video
> In `<D:/Videos/forest-8h.mp4>` there is a dog barking at 2:14:37. Remove it.

Claude asks: how long the noise lasts, and whether the video was made with this project (then it fixes the loop and rebuilds, so the noise doesn't repeat).
You get: a 20-second preview around the spot to listen to → after your "ok", the fixed file (the picture is untouched).

---

## Connect your YouTube channel

Needed only for automatic titles/descriptions/thumbnails and for research. Free. About 10 minutes,
once. Claude can walk you through it step by step — just say *"help me connect YouTube"*.

1. **Create a Google Cloud project.** Go to https://console.cloud.google.com/ and sign in with the
   Google account that owns your channel. In the top bar open the project picker → **New project** →
   any name (e.g. `my-channel-tools`) → **Create**. Make sure the new project is selected.
2. **Enable two YouTube APIs.** Menu ☰ → **APIs & Services → Library** → search
   **YouTube Data API v3** → open it → **Enable**. Go back to the Library, search
   **YouTube Analytics API** → **Enable**. (The first one manages your videos; the second lets
   Claude read your channel statistics: watch time, average view duration, where viewers come
   from, subscribers per video.)
3. **OAuth consent screen.** Menu ☰ → **APIs & Services → OAuth consent screen** (in newer
   consoles: **Google Auth Platform**) → **Get started**. App name: anything. User support email and
   developer contact: your email. Audience / user type: **External**. Leave the app in **Testing**.
   Under **Test users** (or **Audience → Test users**) → **Add users** → your own Google account.
4. **Create the OAuth client.** **APIs & Services → Credentials** (or **Google Auth Platform →
   Clients**) → **Create credentials → OAuth client ID** → Application type **Desktop app** → any
   name → **Create**.
5. **Download the JSON.** In the window that appears click **Download JSON**. In the
   `footage-to-youtube` folder create a folder named **`.secrets`** and save the file there as
   **`client_secret.json`** → `footage-to-youtube/.secrets/client_secret.json`.
   (On a Mac, folders starting with a dot are hidden in Finder: press ⌘ + Shift + . to show them.)
6. **Sign in once.** Run the command below (or ask Claude to run it). A browser window opens: choose
   your channel's account → if Google says the app isn't verified, click **Continue** (it's your own
   app) → tick **both** permissions (manage YouTube, view YouTube Analytics) → **Allow**.
   ```bash
   python3 scripts/yt.py auth        # Windows: python scripts/yt.py auth
   ```
   You'll see `signed in; channel: <your channel>`. The sign-in is saved in `.secrets/token.json`.

**Check your statistics:** `python3 scripts/yt.py stats --days 28` (Windows: `python …`) — or just
ask Claude "How is my channel doing this month?". Already signed in before statistics were added?
Enable **YouTube Analytics API** (step 2) and run `yt.py auth` once more.

**Optional, for research:** **Credentials → Create credentials → API key** → restrict it to
"YouTube Data API v3" → save the key as one line in `.secrets/api_key.txt`.

**Free quota:** 10,000 units per day, per project. What things cost:

| Action | Units |
|---|---|
| Update title/description/tags/translations of a video | ~50 |
| Set a thumbnail | ~50 |
| Add a video to a playlist | ~50 |
| One research search (50 videos) | ~100 (+ ~2 per channel analyzed) |
| Listing your videos, reading statistics | 1 each |

So you can fill in dozens of videos and run ~50 searches a day for free.

**Safety:**
- The `.secrets/` folder is in `.gitignore` — it is never uploaded to GitHub.
- Never paste these keys into a chat, an email, or any other file. Claude will never ask you to.
- If you think they leaked: delete the client/key in Google Cloud Console and make a new one.
- While the app is in "Testing", Google asks you to sign in again about once a week — just run
  `yt.py auth` again.
- How it's used: you upload in YouTube Studio as **Private**; Claude shows a dry run of every change,
  and only after your "yes" sends it. The tools never publish publicly or delete anything on their own.

---

## What's inside

| Path | What it is |
|---|---|
| `CLAUDE.md` | How Claude works with you: questions, tests, safety rules |
| `.claude/skills/ambient-long/` | The long-video playbook (shooting tips → final video → metadata) |
| `.claude/skills/research/` | Competitor research and outlier ranking |
| `.claude/skills/shorts/` | Shorts: built-in vertical cuts + two free external skill packs |
| `scripts/doctor.py` | Checks your computer, prints exact install steps |
| `scripts/run_demo.py` | Self-test on a generated clip |
| `scripts/footage.py` | Lists your footage, finds duplicates, syncs recorder sound |
| `scripts/ambient.py` | Analyze, pick, test, loop, seam check, build, verify, Short, patch-sound |
| `scripts/audioloop.py` | Builds a clean sound bed from hand-picked pieces |
| `scripts/thumb.py` | Thumbnail with text |
| `scripts/keepawake.py` | Keeps the computer awake while a video renders (no settings changed) |
| `scripts/yt.py` | YouTube metadata (titles, descriptions, languages, thumbnail, playlists, schedule) |
| `scripts/research.py` | YouTube research (outliers, views per day, upload rhythm) |
| `templates/` | Templates for video metadata and your channel profile |
| `examples/night-ocean/` | A full example: a 10-hour night ocean video |

The folders `work/`, `output/`, `channel/`, `demo-work/` and `.secrets/` are created on your
computer and are never committed.

## Long renders: keep the computer awake

A 10-hour video can take a few hours to render. Claude keeps your computer awake while it runs
(`scripts/keepawake.py`, no settings are changed). Please don't close the laptop lid, keep it
plugged in, and don't unplug the drive with your footage until Claude says it's done.

## Updating

```bash
git pull
```
Your own files (work, output, channel profile, secrets) are not touched.

## Credits and license

MIT License (see `LICENSE`). The Shorts skill links to two separate MIT projects by other authors:
[reel-skills](https://github.com/danilbogdan/reel-skills) by danilbogdan and
[youtube-agent-skill](https://github.com/Jakeschincariol/youtube-agent-skill) by Jake Schincariol.
Their code is not included here; install them from their own repositories if you want them.
Requires [ffmpeg](https://ffmpeg.org), installed separately.
