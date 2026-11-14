---
name: research
description: Competitor and niche research on YouTube with the YouTube Data API - search a topic, rank videos by views per day and by "outlier" score (views vs the channel's median), study a reference video or channel the user likes, and turn the findings into title, length and thumbnail ideas. Use when the user asks what works in their niche, shares a reference video/channel, or before writing titles.
---

# YouTube research (read-only)

The script never changes anything on YouTube. Windows: `python`, macOS/Linux: `python3`.

## Access (one-time)

Either of:
1. **API key** (simplest for research): Google Cloud Console → same project as in README →
   "APIs & Services → Credentials → Create credentials → API key" → restrict it to
   "YouTube Data API v3". Save it as one line in `.secrets/api_key.txt` (git-ignored).
   Never paste the key into chat or any committed file.
2. Or the OAuth sign-in already used for metadata: `python3 scripts/yt.py auth`.

Quota: 10,000 units/day free. A `search` = 100 units per 50 results + ~2 units per channel.
Don't run more than ~20 searches a day.

## Commands

```
python3 scripts/research.py search "ocean waves sleep" --duration long --min-length 60 --days 730 --out work/research/ocean-sleep.md
python3 scripts/research.py search "strawberry smoothie" --duration short --days 90 --out work/research/smoothie-shorts.md
python3 scripts/research.py channel @SomeHandle --n 50 --out work/research/somehandle.md
```
Options: `--order viewCount|relevance|date`, `--lang en`, `--region US`, `--sort outlier|views_day|views`.

## How to read it

- **Views/day** = views ÷ days since upload: what is working *now*.
- **Outlier** = views ÷ median views of that channel's recent uploads. **3x+** = the video beat the
  channel's normal level, so the topic/title/thumbnail did the work, not the channel size.
  A 50x outlier on a small channel is the strongest signal there is.
- Ignore videos under ~7 days old (numbers not settled yet).

## Turn it into decisions (tell the user in plain words, 5–8 bullets)

1. Which **topics/places/moods** repeat among the top outliers.
2. Which **lengths** win (e.g. 3 h vs 8 h vs 10 h; Shorts 15–30 s vs 45–60 s).
3. **Title patterns**: word order, numbers ("10 Hours"), use cases ("for Sleep", "for Studying"), promise
   ("No Music", "Real Sound").
4. **Thumbnail patterns**: open 3–5 top outliers' thumbnails `https://i.ytimg.com/vi/<ID>/maxresdefault.jpg`
   and describe: dark vs bright, text or not, how many words, colour.
5. **Gaps**: popular searches where the top results are old or low quality = an opportunity.
6. Propose 3 concrete video ideas that the user's **own footage** can make — never suggest
   using other people's footage or sounds.

Save the summary to `channel/research-notes.md` so later sessions can reuse it.
Respect copyright: describe what you see; do not copy other creators' titles or thumbnails 1:1.
