# Footage to YouTube

Turn **your own** videos and sound recordings into finished YouTube videos — long relaxing videos
(1 to 10+ hours: ocean, rain, forest, city at night, sleep sounds) and short vertical **Shorts** —
by talking to **Claude Code** in plain language. You don't need to know how to program.

Claude asks you simple questions (you answer with a number), looks through your footage folder,
makes **short test clips with sound** for you to check, and only after you say "ok" makes the
full video, checks it, writes the title and description, and (if you want) fills them in on
YouTube for you. You always upload and publish yourself.

**What it is good at**
- Seamless loops: a 5-minute piece of calm footage becomes a 3- or 10-hour video with no visible
  or audible "jump".
- Real field sound: syncs a separate recorder (Zoom, Tascam, Rode…) to your video automatically,
  removes wind rumble gently, sets a comfortable loudness for sleep.
- "Day for night": a dark-blue night version from your daytime footage.
- Works with iPhone / DJI HDR footage.
- Shorts: simple vertical cuts built in, plus links to two free skill packs for talking, cooking and
  tutorial Shorts.
- Research: finds which videos in your niche do unusually well ("outliers").

Everything runs on your computer (macOS or Windows; Linux works too). Your footage never leaves
your computer and never goes into git.

---

## 10-minute setup

You need: **Claude Code** (an Anthropic account), **Python 3**, **ffmpeg**, and **git**.

### macOS

1. Open **Terminal** (press ⌘ + Space, type "Terminal", Enter).
2. Install Homebrew if you don't have it — copy the command from https://brew.sh and paste it in Terminal.
3. Install the tools:
   ```bash
   brew install python ffmpeg git
   ```
4. Install Claude Code: https://claude.com/claude-code (desktop app or the terminal version).
5. Download this project and check your computer:
   ```bash
   cd ~
   git clone <this-repository-link> footage-to-youtube
   cd footage-to-youtube
   python3 scripts/doctor.py
   python3 scripts/run_demo.py
   ```
   The demo takes 2–4 minutes and must end with **DEMO PASSED**.

### Windows 10 / 11

1. Open **PowerShell** (Start → type "PowerShell" → Enter).
2. Install the tools (each line, one at a time; say "Yes" if Windows asks):
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
   git clone <this-repository-link> footage-to-youtube
   cd footage-to-youtube
   python scripts/doctor.py
   python scripts/run_demo.py
   ```
   Must end with **DEMO PASSED**. If `python` opens the Microsoft Store, close it, reopen
   PowerShell, and try again (or install Python from https://www.python.org/downloads/ and tick
   "Add python.exe to PATH").

Rendering is faster with an NVIDIA or Intel graphics card (used automatically if present) and on
Apple-silicon Macs. Keep 60+ GB free for a 10-hour 4K video.

### Open it in Claude Code

Open the `footage-to-youtube` folder in Claude Code (desktop app: choose the folder;
terminal: `cd footage-to-youtube` then `claude`). Claude reads `CLAUDE.md` and knows the whole
workflow.

---

## First things to say to Claude (copy and paste)

> Hi! I want to make my first video. Please check my computer and ask me your questions.

> I have ocean footage from my phone and sound from a Zoom recorder on my external drive.
> I want a 3-hour daytime video and a 10-hour night version for sleep.

> Here is a video I like: https://www.youtube.com/watch?v=... — I want something in this style from my footage.

> I run a smoothie channel. Make me three 30-second vertical Shorts from the clips in my "Smoothies" folder.

> What works in my niche right now? Find outlier videos about "rain sounds for sleep".

> The video is uploaded as Private. Fill in the title, description, tags and thumbnail.

Claude always asks one question at a time with numbered answers. Answer with the number.

---

## YouTube API (optional — for filling in titles/descriptions automatically and for research)

You only need this once. It's free. It takes ~10 minutes.

1. Go to https://console.cloud.google.com/ and sign in with the Google account of your channel.
2. Top bar → project picker → **New project** → any name (e.g. "my-channel-tools") → Create.
3. Menu → **APIs & Services → Library** → search **YouTube Data API v3** → **Enable**.
4. **APIs & Services → OAuth consent screen** (or "Google Auth Platform"): User type **External**,
   app name anything, your email as support and developer contact. Leave it in **Testing** and add
   your own Google account under **Test users**.
5. **APIs & Services → Credentials → Create credentials → OAuth client ID** → Application type
   **Desktop app** → Create → **Download JSON**.
6. In the project folder create a folder named `.secrets` and save the file there as
   **`.secrets/client_secret.json`**.
7. Run once (a browser window opens — choose your channel's account and allow):
   ```bash
   python3 scripts/yt.py auth        # Windows: python scripts/yt.py auth
   ```
   It shows "signed in; channel: …". The sign-in is stored in `.secrets/token.json`.

For research you can also create an **API key** (Credentials → Create credentials → API key,
restrict it to YouTube Data API v3) and save it as one line in `.secrets/api_key.txt`.

**Safety:** the `.secrets/` folder is in `.gitignore` — it is never uploaded to GitHub. Don't send
these files to anyone and don't paste them into chats. If you think they leaked, delete the client
in Google Cloud Console and make a new one. While the app is in "Testing", Google asks you to sign
in again about once a week — just run `yt.py auth` again.

How it is used: you upload the video in YouTube Studio as **Private**; Claude runs
`yt.py apply VIDEO_ID meta.json --dry-run`, shows you what will change, and only after your "yes"
sends it. The tools never publish publicly or delete anything without your explicit OK.

---

## What's inside

| Path | What it is |
|---|---|
| `CLAUDE.md` | How Claude should work with you (questions, tests, safety rules) |
| `.claude/skills/ambient-long/` | The long-video playbook (shooting tips → final video → metadata) |
| `.claude/skills/research/` | Competitor research and outlier ranking |
| `.claude/skills/shorts/` | Shorts: built-in simple cuts + two free external skill packs |
| `scripts/doctor.py` | Checks your computer, prints exact install steps |
| `scripts/run_demo.py` | Self-test on a generated clip |
| `scripts/footage.py` | Lists your footage, finds duplicates, syncs recorder sound |
| `scripts/ambient.py` | Analyze, pick, test, loop, seam check, build, verify, Short |
| `scripts/audioloop.py` | Builds a clean sound bed from hand-picked pieces |
| `scripts/thumb.py` | Thumbnail with text |
| `scripts/yt.py` | YouTube metadata (titles, descriptions, languages, thumbnail, playlists) |
| `scripts/research.py` | YouTube research (outliers, views per day) |
| `templates/` | Templates for video metadata and your channel profile |
| `examples/night-ocean/` | A full example: 10-hour night ocean video |

Folders `work/`, `output/`, `channel/`, `demo-work/` and `.secrets/` are created on your computer
and are never committed.

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
Requires [ffmpeg](https://ffmpeg.org) (LGPL/GPL, installed separately).
