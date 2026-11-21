#!/usr/bin/env python3
"""Share what worked for your channel with the author and other creators (GitHub Discussions).
Opt-in only: nothing is sent unless YOU decide to send it.

  python scripts/share.py post channel/share/what-worked.md --title "Clean night thumbnail doubled CTR"
        -> shows exactly what would be posted, and where. Nothing is sent.
  python scripts/share.py post channel/share/what-worked.md --title "..." --yes
        -> posts it with the GitHub CLI (gh) under YOUR GitHub account, prints the link.

The note is a plain Markdown file you can read and edit first (see templates/what-worked.md).
Needs the GitHub CLI: https://cli.github.com  (then once: gh auth login). Without gh, the script
prints the web address of the form and you paste the note there yourself.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = "sasha11207/footage-to-youtube"
CATEGORY = "what-worked"


def gh(args, check=True):
    p = subprocess.run(["gh"] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                       encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        sys.exit("gh failed: " + p.stderr.strip()[:600])
    return p


def web_url(repo):
    return f"https://github.com/{repo}/discussions/new?category={CATEGORY}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("post"); p.add_argument("file"); p.add_argument("--title", required=True)
    p.add_argument("--repo", default=REPO); p.add_argument("--yes", action="store_true", help="really post it")
    a = ap.parse_args()

    body = Path(a.file).read_text(encoding="utf-8").strip()
    if len(a.title) > 120:
        sys.exit("title is too long (keep it under ~100 characters)")
    print(f"Where: GitHub Discussions of {a.repo}, category '{CATEGORY}' (public, visible to everyone)")
    print(f"Title: {a.title}\n" + "-" * 60 + f"\n{body}\n" + "-" * 60)
    if not a.yes:
        print("Preview only: nothing was sent. Read it; to post it, run the same command with --yes.")
        return
    if not shutil.which("gh") or gh(["auth", "status"], check=False).returncode != 0:
        print("The GitHub CLI (gh) is not installed or not signed in. Post it in the browser instead:\n"
              f"  {web_url(a.repo)}\nand paste the title and the text above.")
        return
    owner, name = a.repo.split("/", 1)
    q = gh(["api", "graphql", "-f", "query=query($o:String!,$n:String!){repository(owner:$o,name:$n){id "
            "hasDiscussionsEnabled discussionCategories(first:50){nodes{id slug name}}}}", "-f", f"o={owner}", "-f", f"n={name}"])
    repo = json.loads(q.stdout)["data"]["repository"]
    cat = next((c for c in repo["discussionCategories"]["nodes"] if c["slug"] == CATEGORY), None)
    if not repo["hasDiscussionsEnabled"] or not cat:
        sys.exit(f"Discussions or the '{CATEGORY}' category are not set up in {a.repo} yet. "
                 f"Post it in the browser instead: {web_url(a.repo)}")
    m = gh(["api", "graphql", "-f", "query=mutation($r:ID!,$c:ID!,$t:String!,$b:String!){createDiscussion(input:"
            "{repositoryId:$r,categoryId:$c,title:$t,body:$b}){discussion{url}}}",
            "-f", f"r={repo['id']}", "-f", f"c={cat['id']}", "-f", f"t={a.title}", "-F", f"b=@{Path(a.file).resolve()}"])
    print("posted:", json.loads(m.stdout)["data"]["createDiscussion"]["discussion"]["url"])


if __name__ == "__main__":
    main()
