#!/usr/bin/env python3
"""Competitor research with the YouTube Data API: which videos in your niche over-perform.
Standard library only. Read-only: it never changes anything on YouTube.

  python scripts/research.py search "ocean waves sleep 10 hours" --days 365 --duration long --out work/research/ocean.md
  python scripts/research.py channel @SomeChannelHandle --n 50 --out work/research/channel.md

For every video: views, views per day since publishing, and the OUTLIER score = views divided by the
median views of that channel's recent uploads. Outlier 5x means "this video did 5 times better than
this channel normally does": its title, thumbnail, length and topic are worth studying.

Access (either one):
  * an API key (simplest for research): put it in .secrets/api_key.txt, or set env YT_API_KEY
  * or the OAuth sign-in from yt.py (python scripts/yt.py auth)
Quota (10,000 units/day free): search = 100 units per 50 results; everything else 1 unit per call.
A typical search with 15 channels costs about 140 units.
"""
import argparse
import datetime as dt
import os
import re
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yt  # noqa: E402


def api_key():
    k = os.environ.get("YT_API_KEY", "").strip()
    f = yt.SECRETS / "api_key.txt"
    if not k and f.exists():
        k = f.read_text().strip()
    return k or None


KEY = None


def get(path, params):
    return yt.call("GET", path, params, key=KEY)


def iso_dur(s):
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    if not m:
        return 0
    d, h, mi, se = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + se


def chunks(xs, n=50):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


def videos(ids):
    out = []
    for c in chunks(list(ids)):
        out += get("/videos", {"part": "snippet,statistics,contentDetails", "id": ",".join(c)}).get("items", [])
    now = dt.datetime.now(dt.timezone.utc)
    rows = []
    for v in out:
        pub = dt.datetime.fromisoformat(v["snippet"]["publishedAt"].replace("Z", "+00:00"))
        days = max(1.0, (now - pub).total_seconds() / 86400)
        views = int(v.get("statistics", {}).get("viewCount", 0))
        rows.append({"id": v["id"], "title": v["snippet"]["title"], "channel": v["snippet"]["channelTitle"],
                     "channelId": v["snippet"]["channelId"], "published": pub.date().isoformat(), "days": round(days),
                     "views": views, "views_day": round(views / days, 1),
                     "likes": int(v.get("statistics", {}).get("likeCount", 0) or 0),
                     "comments": int(v.get("statistics", {}).get("commentCount", 0) or 0),
                     "length_s": iso_dur(v["contentDetails"].get("duration"))})
    return rows


def channel_info(ids):
    info = {}
    for c in chunks(list(ids)):
        for ch in get("/channels", {"part": "snippet,statistics,contentDetails", "id": ",".join(c)}).get("items", []):
            info[ch["id"]] = {"title": ch["snippet"]["title"],
                              "subs": int(ch["statistics"].get("subscriberCount", 0) or 0),
                              "videos": int(ch["statistics"].get("videoCount", 0) or 0),
                              "uploads": ch["contentDetails"]["relatedPlaylists"]["uploads"]}
    return info


def recent_uploads(uploads_playlist, n):
    items = get("/playlistItems", {"part": "contentDetails", "playlistId": uploads_playlist,
                                   "maxResults": min(50, n)}).get("items", [])
    return [i["contentDetails"]["videoId"] for i in items]


def add_outliers(rows, info, n_recent):
    med = {}
    for cid, ch in info.items():
        vids = videos(recent_uploads(ch["uploads"], n_recent))
        views = [v["views"] for v in vids if v["days"] >= 7] or [v["views"] for v in vids]   # skip brand-new ones
        med[cid] = st.median(views) if views else 0
        ch["median_views"] = round(med[cid])
    for r in rows:
        m = med.get(r["channelId"], 0)
        r["outlier"] = round(r["views"] / m, 1) if m else None
        r["subs"] = info.get(r["channelId"], {}).get("subs", 0)


def fmt_len(s):
    return f"{s // 3600}h{s % 3600 // 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def table(rows, title):
    L = [f"# {title}", "", f"_{dt.date.today().isoformat()}, {len(rows)} videos. Outlier = views / channel median._", "",
         "| # | Outlier | Views/day | Views | Length | Published | Channel (subs) | Title |",
         "|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        o = f"{r['outlier']}x" if r.get("outlier") is not None else "-"
        L.append(f"| {i} | {o} | {r['views_day']:,} | {r['views']:,} | {fmt_len(r['length_s'])} | {r['published']} | "
                 f"{r['channel']} ({r.get('subs', 0):,}) | [{r['title'].replace('|', '/')}](https://youtu.be/{r['id']}) |")
    return "\n".join(L) + "\n"


def rank(rows, by):
    key = {"outlier": lambda r: (r.get("outlier") or 0, r["views_day"]), "views_day": lambda r: r["views_day"],
           "views": lambda r: r["views"]}[by]
    return sorted(rows, key=key, reverse=True)


def emit(text, out):
    print(text)
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(text, encoding="utf-8")
        print("->", out)


def cmd_search(a):
    params = {"part": "id", "type": "video", "q": a.query, "maxResults": 50, "order": a.order}
    if a.days:
        since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=a.days)
        params["publishedAfter"] = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    if a.duration != "any":
        params["videoDuration"] = a.duration     # short <4 min, medium 4-20, long >20
    if a.lang:
        params["relevanceLanguage"] = a.lang
    if a.region:
        params["regionCode"] = a.region
    ids, token = [], None
    while len(ids) < a.n:
        if token:
            params["pageToken"] = token
        res = get("/search", params)
        ids += [i["id"]["videoId"] for i in res.get("items", []) if i["id"].get("videoId")]
        token = res.get("nextPageToken")
        if not token:
            break
    rows = videos(ids[: a.n])
    if a.min_length:
        rows = [r for r in rows if r["length_s"] >= a.min_length * 60]
    by_ch = {}
    for r in sorted(rows, key=lambda r: -r["views_day"]):
        by_ch.setdefault(r["channelId"], 0)
        by_ch[r["channelId"]] += 1
    top_channels = list(by_ch)[: a.channels]
    info = channel_info(top_channels)
    add_outliers(rows, info, a.recent)
    emit(table(rank(rows, a.sort), f'Search: "{a.query}"'), a.out)


def resolve_channel(s):
    if s.startswith("UC") and len(s) == 24:
        return s
    res = get("/channels", {"part": "id", "forHandle": s if s.startswith("@") else "@" + s})
    if res.get("items"):
        return res["items"][0]["id"]
    sys.exit("channel not found: " + s)


def cmd_channel(a):
    cid = resolve_channel(a.channel)
    info = channel_info([cid])
    rows = videos(recent_uploads(info[cid]["uploads"], a.n))
    add_outliers(rows, info, a.n)
    ch = info[cid]
    emit(table(rank(rows, a.sort), f"Channel: {ch['title']} ({ch['subs']:,} subscribers, {ch['videos']} videos, "
                                   f"median {ch['median_views']:,} views)"), a.out)


def main():
    global KEY
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("search"); p.add_argument("query")
    p.add_argument("--n", type=int, default=50, help="videos to look at (50 = 100 quota units)")
    p.add_argument("--days", type=int, default=0, help="only videos from the last N days")
    p.add_argument("--duration", choices=["any", "short", "medium", "long"], default="any")
    p.add_argument("--min-length", type=float, default=0, help="minutes; e.g. 60 for long ambient")
    p.add_argument("--order", default="relevance", choices=["relevance", "viewCount", "date", "rating"])
    p.add_argument("--lang", default=""); p.add_argument("--region", default="")
    p.add_argument("--channels", type=int, default=15, help="channels to compute medians for")
    p.add_argument("--recent", type=int, default=30, help="recent uploads per channel for the median")
    p.add_argument("--sort", choices=["outlier", "views_day", "views"], default="outlier")
    p.add_argument("--out", default="")
    p = sub.add_parser("channel"); p.add_argument("channel", help="@handle or UC... channel id")
    p.add_argument("--n", type=int, default=50)
    p.add_argument("--sort", choices=["outlier", "views_day", "views"], default="views_day")
    p.add_argument("--out", default="")
    a = ap.parse_args()
    KEY = api_key()
    {"search": cmd_search, "channel": cmd_channel}[a.cmd](a)


if __name__ == "__main__":
    main()
