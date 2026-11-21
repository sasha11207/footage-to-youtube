# Footage to YouTube

**English** · [Українська](README.uk.md)

> Turn your own footage into long YouTube videos (and Shorts) with Claude Code: ask, test with short previews, then render. Mac & Windows.

You talk to **Claude Code** in plain language. Claude asks you simple questions (you answer with a
number), looks through your footage folder, makes **short test clips with sound** for you to check,
and only after you say "ok" makes the full video, checks it, and writes the title and description.
You don't need to know how to program. You always upload and publish yourself.

Everything runs on your own computer (macOS or Windows; Linux works too). Your footage never
leaves your computer and never goes into git.

**We collect feedback: tell us what worked for your channel** — a video that took off, a thumbnail
that won, a format that held viewers. Post it in [Discussions → What worked](https://github.com/sasha11207/footage-to-youtube/discussions/categories/what-worked) (or let Claude
draft it for you — see [Share what worked](#share-what-worked)).

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
- **Finds problems in your recordings** before you use them: recorder beeps, barks, voices, knocks.
- **Dusk and dawn clips**: measures how fast the light changes and picks a steady window, so the loop
  doesn't "blink".
- **Fix a noise** (a bark, a car) at a given second in a finished video.
- **24/7 live stream file**: a looping 1080p or 4K file ready for a live stream.
- **Thumbnails** with big text.
- **Titles, descriptions, tags, translations, playlists, scheduling** — filled in on YouTube for you
  (after you upload as Private and say "yes").
- **Research**: what works in your niche, which videos beat their channel's normal level ("outliers"),
  a channel's upload rhythm, a month plan.

---

## Setup: Claude does it for you

You only need the **Claude desktop app** (an Anthropic account with Claude Code). No Terminal and
no installing programs by hand.

1. Install the Claude app from https://claude.com/download, sign in and open the **Code** tab.
2. Make an empty folder for the project (for example `Documents/footage-to-youtube`) and choose it
   as the working folder in the Code tab.
3. Send Claude this message:
   > Set up this project for me in this folder: https://github.com/sasha11207/footage-to-youtube — follow the "Setup steps for Claude" in its README.
4. Claude downloads the project, checks your computer and tells you what is still missing (often
   nothing). Answer **1** to say yes. Then it offers a short self-test and a 2-minute welcome quiz.

**Everything goes inside the project folder**: Python in `.venv`, ffmpeg in `.tools` (only if your
computer doesn't already have them). Nothing is installed on the rest of the computer and no
settings are changed, so nothing else can break. To remove it all, delete the folder.

On Windows, if the Claude app asks for **Git for Windows**, install it from https://git-scm.com —
that is the only thing you might need to install yourself.

Rendering is faster with an NVIDIA or Intel graphics card (used automatically) and on Apple-silicon
Macs. Keep 60+ GB free for a 10-hour 4K video. Write in any language — Claude answers in the
language you write in.

### Setup steps for Claude

*(Claude reads this part. You can skip it.)*

1. **Detect the system first** and use it for every command below: macOS / Linux (`uname -s`,
   `uname -m`; POSIX shell) or Windows (`$env:OS`, `$env:PROCESSOR_ARCHITECTURE`; PowerShell,
   `curl.exe` instead of `curl`). Tell the user in one line what you found
   ("Windows 11, Intel/AMD 64-bit").
2. Work in the folder the user opened. If it is empty and git works, run
   `git clone https://github.com/sasha11207/footage-to-youtube.git .` (on macOS check `xcode-select -p` first: without Command Line Tools,
   `git` opens an install dialog). Without git: download
   `https://github.com/sasha11207/footage-to-youtube/archive/refs/heads/main.zip` with `curl -L -o project.zip`, extract it with
   `tar -xf project.zip` (works on macOS and Windows 10+), move the contents of
   `footage-to-youtube-main/` into the folder and delete the ZIP. If the folder is not empty, use a
   subfolder `footage-to-youtube` and tell the user to open that folder in the app next time.
3. Read `CLAUDE.md` and follow it. Its section 1 is the setup: `setup.sh` (macOS/Linux) or
   `setup.ps1` (Windows) — show the plan, ask the user, then run it. Install nothing system-wide.
4. Then start the welcome quiz from `CLAUDE.md`.

<details>
<summary>Manual setup in a terminal (if you prefer)</summary>

```bash
git clone https://github.com/sasha11207/footage-to-youtube.git
cd footage-to-youtube
sh setup.sh --yes                                            # macOS / Linux
powershell -ExecutionPolicy Bypass -File setup.ps1 -Yes      # Windows (PowerShell)
```
Then open the `footage-to-youtube` folder in Claude Code (desktop app: choose the folder;
terminal: `claude`). Run `sh setup.sh` without `--yes` (or `setup.ps1` without `-Yes`) to only see
what it would download.
</details>

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
| `setup.sh`, `setup.ps1` | One-time setup: Python and ffmpeg inside this folder only |
| `scripts/doctor.py` | Checks your computer, says what is missing |
| `scripts/run_demo.py` | Self-test on a generated clip |
| `scripts/footage.py` | Lists your footage, finds duplicates, syncs recorder sound |
| `scripts/sound_events.py` | Finds beeps, barks, voices and knocks in a recording |
| `scripts/ambient.py` | Analyze, pick, test, loop, seam check, build, verify, Short, patch-sound, brightness, stream file |
| `scripts/audioloop.py` | Builds a clean sound bed from hand-picked pieces |
| `scripts/thumb.py` | Thumbnail with text |
| `scripts/keepawake.py` | Keeps the computer awake while a video renders (no settings changed) |
| `scripts/yt.py` | YouTube metadata (titles, descriptions, languages, thumbnail, playlists, schedule) |
| `scripts/research.py` | YouTube research (outliers, views per day, upload rhythm) |
| `scripts/share.py` | Posts your "what worked" note to Discussions (preview first, only when you say yes) |
| `templates/` | Templates for video metadata and your channel profile |
| `examples/night-ocean/` | A full example: a 10-hour night ocean video |

The folders `.venv/`, `.tools/`, `work/`, `output/`, `channel/`, `demo-work/` and `.secrets/` are created on your
computer and are never committed.

## Good to know (rules that protect your channel)

- **You upload by hand** in YouTube Studio (as Private). Claude never uploads through the API or any
  bot: API uploads from unverified projects stay locked to private, and automation can look like
  spam to YouTube. Claude fills in everything else after you upload.
- **Your own footage and sound only.** Colour, night look, noise cleanup and loops are fine;
  AI-generated video, sound, music or "AI-enhanced" pictures are not — YouTube's "inauthentic
  content" rules can take away monetization. Claude warns you if a request goes that way.
- **No "template channel".** Each video is a different place or scene, with 2–3 description lines
  true only for it (place, time, weather, how the sound was recorded).
- **Weekly check-up.** `yt.py stats --save` saves a snapshot; next time you see what grew and what
  dropped, plus one suggestion. Claude runs it by itself when the last one is a week old.
- **Thumbnail A/B test.** Claude makes 3 thumbnail variants for every video; upload them in
  Studio → the video → Thumbnail → **Test & compare**, and YouTube picks the winner.

## Long renders: keep the computer awake

A 10-hour video can take a few hours to render. Claude keeps your computer awake while it runs
(`scripts/keepawake.py`, no settings are changed). Please don't close the laptop lid, keep it
plugged in, and don't unplug the drive with your footage until Claude says it's done.

## Share what worked

This project gets better from real results. When something clearly works for you (a video beats your
usual numbers, a thumbnail wins Test & Compare, a new format holds viewers), Claude asks **once**
whether you'd like to share it. It's always your choice — nothing is ever sent automatically.

If you say yes, Claude writes a short note: what you did, the key numbers (CTR, average view
duration, views compared with your usual videos) and what you think made the difference — **without**
your channel name, links or personal data, unless you add them. You read and edit it, and only then
it's posted under your own GitHub account to [Discussions → What worked](https://github.com/sasha11207/footage-to-youtube/discussions/categories/what-worked) (via the GitHub CLI
`gh`, or you paste it into the form yourself). You can also post there any time without Claude.

## Updating

Claude checks for updates at the start of a conversation and offers to update. By hand:
```bash
git pull
```
Your own files (work, output, channel profile, secrets) are not touched.

## Credits and license

MIT License (see `LICENSE`). The Shorts skill links to two separate MIT projects by other authors:
[reel-skills](https://github.com/danilbogdan/reel-skills) by danilbogdan and
[youtube-agent-skill](https://github.com/Jakeschincariol/youtube-agent-skill) by Jake Schincariol.
Their code is not included here; install them from their own repositories if you want them.
Uses [ffmpeg](https://ffmpeg.org) (downloaded by setup if your computer doesn't have it) and,
if needed, [uv](https://github.com/astral-sh/uv) for a private Python.
