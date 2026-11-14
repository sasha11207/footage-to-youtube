#!/usr/bin/env python3
"""YouTube Data API v3 helper: YOU upload the video in YouTube Studio as Private,
this script fills in everything else (title, description, tags, languages, thumbnail,
playlists, scheduled publish time). Python standard library only.

One-time setup: see README.md, section "YouTube API". In short: Google Cloud project ->
enable "YouTube Data API v3" -> OAuth consent screen (External, Testing, your own Google
account as a test user) -> OAuth client ID of type "Desktop app" -> download the JSON to
    .secrets/client_secret.json        (the .secrets folder is never committed to git)

  python scripts/yt.py auth                       # opens Google sign-in once, stores .secrets/token.json
  python scripts/yt.py list [--n 10]              # your latest uploads: id, status, length, title
  python scripts/yt.py show VIDEO_ID              # current title, description, languages, status
  python scripts/yt.py apply VIDEO_ID meta.json --dry-run     # ALWAYS first: shows what would change
  python scripts/yt.py apply VIDEO_ID meta.json               # sends it (video stays private/scheduled)

meta.json: see templates/meta.template.json. "privacyStatus": "public" is refused unless you also
pass --confirm-public (publishing is the channel owner's decision). This script never deletes anything.
Quota: videos.update 50, thumbnails.set 50, playlistItems.insert 50 units; 10,000 units per day free.
"""
import argparse
import base64
import hashlib
import http.server
import json
import os
import secrets
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECRETS = ROOT / ".secrets"
CLIENT = SECRETS / "client_secret.json"
TOKEN = SECRETS / "token.json"
SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
API = "https://www.googleapis.com/youtube/v3"

# python.org Python on macOS may ship without a CA bundle: fall back to the system one
if sys.platform == "darwin" and not os.environ.get("SSL_CERT_FILE") and Path("/etc/ssl/cert.pem").exists():
    os.environ["SSL_CERT_FILE"] = "/etc/ssl/cert.pem"


def client():
    if not CLIENT.exists():
        sys.exit(f"missing {CLIENT}\nDownload the OAuth 'Desktop app' client JSON there first (README: YouTube API).")
    c = json.loads(CLIENT.read_text(encoding="utf-8"))
    return c.get("installed") or c.get("web")


def post_form(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def save_token(tok):
    SECRETS.mkdir(exist_ok=True)
    tok["expires_at"] = time.time() + int(tok.get("expires_in", 3600)) - 60
    old = json.loads(TOKEN.read_text()) if TOKEN.exists() else {}
    if "refresh_token" not in tok and "refresh_token" in old:
        tok["refresh_token"] = old["refresh_token"]
    fd = os.open(str(TOKEN), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(tok, f)


def cmd_auth(a):
    c = client()
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    redirect = f"http://127.0.0.1:{port}"
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    url = c["auth_uri"] + "?" + urllib.parse.urlencode({
        "client_id": c["client_id"], "redirect_uri": redirect, "response_type": "code", "scope": SCOPE,
        "access_type": "offline", "prompt": "consent", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256"})
    got = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
            self.wfile.write("Done. You can close this window.".encode())

        def log_message(self, *x):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", port), H)
    print("Opening Google sign-in in your browser. If it does not open, copy this address into the browser:\n" + url,
          flush=True)
    webbrowser.open(url)
    while "code" not in got and "error" not in got:
        srv.handle_request()
    if got.get("state") != state or "code" not in got:
        sys.exit(f"sign-in failed: {got.get('error', 'state mismatch')}")
    tok = post_form(c["token_uri"], {"code": got["code"], "client_id": c["client_id"],
                                     "client_secret": c.get("client_secret", ""), "redirect_uri": redirect,
                                     "grant_type": "authorization_code", "code_verifier": verifier})
    save_token(tok)
    ch = call("GET", "/channels", {"part": "snippet", "mine": "true"})
    print("signed in; channel:", ", ".join(i["snippet"]["title"] for i in ch.get("items", [])) or "(none)")


def access_token():
    if not TOKEN.exists():
        sys.exit("not signed in: run  python scripts/yt.py auth")
    tok = json.loads(TOKEN.read_text())
    if time.time() > tok.get("expires_at", 0):
        c = client()
        new = post_form(c["token_uri"], {"client_id": c["client_id"], "client_secret": c.get("client_secret", ""),
                                         "refresh_token": tok["refresh_token"], "grant_type": "refresh_token"})
        save_token(new)
        tok = json.loads(TOKEN.read_text())
    return tok["access_token"]


def call(method, path, params=None, body=None, data=None, ctype=None, base=API, key=None):
    """One API call. With key= (an API key) public read-only calls work without OAuth (research.py)."""
    params = dict(params or {})
    headers = {}
    if key:
        params["key"] = key
    else:
        headers["Authorization"] = "Bearer " + access_token()
    url = base + path + ("?" + urllib.parse.urlencode(params) if params else "")
    if body is not None:
        data = json.dumps(body).encode(); headers["Content-Type"] = "application/json"
    elif ctype:
        headers["Content-Type"] = ctype
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            txt = r.read()
            return json.loads(txt) if txt else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} -> HTTP {e.code}: {e.read().decode()[:800]}")


def cmd_list(a):
    ch = call("GET", "/channels", {"part": "contentDetails", "mine": "true"})
    if not ch.get("items"):
        sys.exit("this Google account has no YouTube channel")
    up = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    items = call("GET", "/playlistItems", {"part": "contentDetails", "playlistId": up, "maxResults": a.n}).get("items", [])
    ids = ",".join(i["contentDetails"]["videoId"] for i in items)
    if not ids:
        print("no uploads yet"); return
    for v in call("GET", "/videos", {"part": "snippet,status,contentDetails", "id": ids})["items"]:
        extra = f" publishAt {v['status']['publishAt']}" if v["status"].get("publishAt") else ""
        print(f"{v['id']}  {v['status']['privacyStatus']:8s} {v['contentDetails']['duration']:>10s}  "
              f"{v['snippet']['title']}{extra}")


def cmd_show(a):
    v = call("GET", "/videos", {"part": "snippet,status,localizations", "id": a.video})["items"]
    print(json.dumps(v[0] if v else {}, ensure_ascii=False, indent=1))


_new_playlists = set()  # just created: listing its items can 404 for a while


def playlist_id(name, dry):
    pls = call("GET", "/playlists", {"part": "snippet", "mine": "true", "maxResults": 50}).get("items", [])
    for p in pls:
        if p["snippet"]["title"].strip().lower() == name.strip().lower():
            return p["id"]
    if dry:
        return None
    p = call("POST", "/playlists", {"part": "snippet,status"},
             {"snippet": {"title": name}, "status": {"privacyStatus": "public"}})
    print("  created playlist", name)
    _new_playlists.add(p["id"])
    return p["id"]


def cmd_apply(a):
    m = json.loads(Path(a.meta).read_text(encoding="utf-8"))
    m = {k: v for k, v in m.items() if not k.startswith("_")}       # "_comment" keys from the template
    base = Path(a.meta).resolve().parent
    if m.get("privacyStatus") == "public" and not a.confirm_public:
        sys.exit('meta.json says "privacyStatus": "public". Publishing is the owner\'s decision:\n'
                 "ask them, then re-run with --confirm-public (or use publishAt to schedule).")
    cur = call("GET", "/videos", {"part": "snippet,status,localizations", "id": a.video})["items"]
    if not cur:
        sys.exit("video not found on this channel: " + a.video)
    cur = cur[0]
    sn = cur["snippet"]
    snippet = {"title": m.get("title", sn["title"]), "description": m.get("description", sn.get("description", "")),
               "tags": m.get("tags", sn.get("tags", [])), "categoryId": str(m.get("categoryId", sn.get("categoryId", "22"))),
               "defaultLanguage": m.get("defaultLanguage", sn.get("defaultLanguage", "en"))}
    if len(snippet["title"]) > 100:
        sys.exit(f"title is {len(snippet['title'])} characters; YouTube allows 100")
    if len(snippet["description"].encode("utf-8")) > 5000:
        sys.exit("description over 5000 bytes")
    if len(",".join(snippet["tags"])) > 480:
        sys.exit("tags over ~500 characters in total")
    body = {"id": a.video, "snippet": snippet}
    parts = ["snippet"]
    # Studio's "video language" is defaultAudioLanguage (e.g. en-US). Keep them consistent, or Studio shows
    # an empty "English (United States)" row next to a separate "English" one.
    # a fresh upload may have no audio language yet; YouTube then fills en-US by itself, so set it ourselves
    aud = (m.get("defaultAudioLanguage") or sn.get("defaultAudioLanguage")
           or {"en": "en-US"}.get(snippet["defaultLanguage"]))
    if aud and aud.split("-")[0] == snippet["defaultLanguage"].split("-")[0]:
        snippet["defaultAudioLanguage"] = aud
        snippet["defaultLanguage"] = aud
    loc = dict(cur.get("localizations", {}))
    for k in list(loc):   # drop an older entry for the default language under another code ("en" vs "en-US")
        if k != snippet["defaultLanguage"] and k.split("-")[0] == snippet["defaultLanguage"].split("-")[0] \
                and k not in m.get("localizations", {}):
            del loc[k]
    if m.get("localizations"):
        loc[snippet["defaultLanguage"]] = {"title": snippet["title"], "description": snippet["description"]}
    for lang, t in m.get("localizations", {}).items():
        if len(t["title"]) > 100:
            sys.exit(f"{lang} title over 100 characters")
        loc[lang] = {"title": t["title"], "description": t["description"]}
    if loc:
        body["localizations"] = loc
        parts.append("localizations")
    stt = {k: cur["status"][k] for k in ("privacyStatus", "embeddable", "license", "publicStatsViewable")
           if k in cur["status"]}
    if "madeForKids" in m:
        stt["selfDeclaredMadeForKids"] = bool(m["madeForKids"])
    if "privacyStatus" in m:
        stt["privacyStatus"] = m["privacyStatus"]
    if m.get("publishAt"):
        stt["privacyStatus"] = "private"
        stt["publishAt"] = m["publishAt"]
    body["status"] = stt
    parts.append("status")
    print(f"video {a.video}: '{sn['title']}' -> '{snippet['title']}'")
    print(f"  languages: {', '.join(sorted(loc)) or '-'}; tags: {len(snippet['tags'])}; status: {stt.get('privacyStatus')}"
          + (f", publishAt {stt['publishAt']}" if "publishAt" in stt else ""))
    pls = m.get("playlist") or []
    pls = [pls] if isinstance(pls, str) else pls
    thumb = None
    if m.get("thumbnail"):
        thumb = Path(m["thumbnail"]) if Path(m["thumbnail"]).is_absolute() else base / m["thumbnail"]
        if not thumb.exists():
            sys.exit(f"thumbnail not found: {thumb}")
    if a.dry_run:
        print(f"  thumbnail: {thumb.name if thumb else '-'}; playlists: {', '.join(pls) or '-'}")
        print("  dry run: nothing sent"); return
    call("PUT", "/videos", {"part": ",".join(parts)}, body)
    print("  metadata updated")
    if thumb and not a.skip_thumb:
        ctype = "image/png" if thumb.suffix.lower() == ".png" else "image/jpeg"
        call("POST", "/thumbnails/set", {"videoId": a.video}, data=thumb.read_bytes(), ctype=ctype,
             base="https://www.googleapis.com/upload/youtube/v3")
        print("  thumbnail set:", thumb.name)
    for name in pls:
        pid = playlist_id(name, False)
        have = [] if pid in _new_playlists else \
            call("GET", "/playlistItems", {"part": "contentDetails", "playlistId": pid, "maxResults": 50}).get("items", [])
        if any(i["contentDetails"]["videoId"] == a.video for i in have):
            print("  already in playlist", name)
        else:
            call("POST", "/playlistItems", {"part": "snippet"},
                 {"snippet": {"playlistId": pid, "resourceId": {"kind": "youtube#video", "videoId": a.video}}})
            print("  added to playlist", name)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("auth")
    p = sub.add_parser("list"); p.add_argument("--n", type=int, default=10)
    p = sub.add_parser("show"); p.add_argument("video")
    p = sub.add_parser("apply"); p.add_argument("video"); p.add_argument("meta")
    p.add_argument("--dry-run", action="store_true"); p.add_argument("--skip-thumb", action="store_true")
    p.add_argument("--confirm-public", action="store_true", help="only after the owner said yes to publishing now")
    a = ap.parse_args()
    {"auth": cmd_auth, "list": cmd_list, "show": cmd_show, "apply": cmd_apply}[a.cmd](a)


if __name__ == "__main__":
    main()
