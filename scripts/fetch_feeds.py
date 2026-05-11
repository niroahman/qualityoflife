#!/usr/bin/env python3
"""Fetch RSS/Atom feeds and podcasts, output cleaned Markdown."""

import argparse
import os
import re
import socket
import ssl
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import certifi
import feedparser
import yaml
from dotenv import load_dotenv

load_dotenv(Path.home() / ".secrets" / "qualityoflife" / ".env")

ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())

MAX_ITEMS = int(os.getenv("FEED_MAX_ITEMS", 20))
MAX_DESC = int(os.getenv("FEED_MAX_DESC_CHARS", 400))
TIMEOUT = int(os.getenv("FEED_TIMEOUT_SECS", 10))

socket.setdefaulttimeout(TIMEOUT)

# (feed_type, display_label) — insertion order defines digest section order
_SECTIONS: dict[str, tuple[str, str]] = {
    "newsletters":     ("newsletter", "Uutiskirjeet"),
    "podcasts":        ("podcast",    "Podcastit"),
    "tech_blogs":      ("blog",       "Tech-blogit"),
    "youtube_channels": ("youtube",   "YouTube"),
    "reddit_forums":   ("reddit",     "Reddit"),
    "github_releases": ("release",    "GitHub Releases"),
}


def this_monday() -> datetime:
    """This week's Monday 00:00 UTC."""
    today = datetime.now(timezone.utc)
    return (today - timedelta(days=today.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


def default_since() -> datetime:
    """Last Monday 00:00 UTC — covers previous week + current week to today."""
    return this_monday() - timedelta(weeks=1)


def read_since(state_file: str) -> datetime:
    """
    Always fetch from last Monday — so same-week re-runs accumulate the full week.
    If last run was before last Monday (missed a week+), catch up from last run instead.
    """
    last_monday = default_since()
    if os.path.exists(state_file):
        try:
            with open(state_file) as f:
                ts = f.read().strip()
            last_run = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
            if last_run < last_monday:
                return last_run  # been away > 1 week, catch up from last run
        except Exception:
            pass
    return last_monday


def entry_datetime(entry) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def strip_html(text: str) -> str:
    return re.sub(r"<[^<]+?>", "", text or "").strip()


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."


def format_date(entry) -> str:
    dt = entry_datetime(entry)
    return dt.strftime("%Y-%m-%d") if dt else "?"


def fetch_feed(feed_cfg: dict, output, since: datetime, section: str = "tech_blogs") -> None:
    name = feed_cfg["name"]
    url = feed_cfg["url"]
    feed_type = feed_cfg.get("type") or _SECTIONS.get(section, ("blog", ""))[0]

    ua = "qualityoflife-bot/1.0 (personal digest)" if "reddit.com" in url else "Mozilla/5.0"
    try:
        parsed = feedparser.parse(url, request_headers={"User-Agent": ua})
    except Exception as e:
        print(f"WARNING: [{name}] fetch error: {e}", file=sys.stderr)
        return

    if parsed.bozo and not parsed.entries:
        print(f"WARNING: [{name}] empty or malformed feed", file=sys.stderr)
        return

    count = 0
    for entry in parsed.entries:
        if count >= MAX_ITEMS:
            break

        dt = entry_datetime(entry)
        if dt is None or dt < since:
            continue

        count += 1
        title = strip_html(entry.get("title", "(no title)"))
        link = entry.get("link", "")
        date = format_date(entry)
        desc = strip_html(entry.get("summary", entry.get("description", "")))
        desc = truncate(desc, MAX_DESC)

        output.write(f"### [{title}]({link})\n")
        output.write(f"*Lähde: {name} | Julkaistu: {date}*\n")

        if feed_type == "podcast":
            podcast_link = entry.get("link", "")
            mp3 = ""
            enclosures = entry.get("enclosures", [])
            if enclosures:
                mp3 = enclosures[0].get("href", "")
            if desc:
                output.write(f"{desc}\n\n")
            links_line = f"[🔗 Avaa jakson sivu]({podcast_link})"
            if mp3:
                links_line += f" | [🎧 Kuuntele (MP3)]({mp3})"
            output.write(links_line + "\n")
        elif feed_type == "youtube":
            if desc:
                output.write(f"{desc}\n\n")
            output.write(f"[▶ Katso video]({link})\n")
        else:
            if desc:
                output.write(f"{desc}\n")

        output.write("\n---\n\n")


def write_feeds(config: dict, output, since: datetime) -> None:
    for section, (_, label) in _SECTIONS.items():
        feeds = config.get(section, [])
        if not feeds:
            continue
        output.write(f"## {label}\n\n")
        for feed_cfg in feeds:
            fetch_feed(feed_cfg, output, since, section)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feeds", default="/tmp/runtime-feeds.yaml")
    parser.add_argument("--output", default=None, help="Output file (default: stdout)")
    parser.add_argument("--since-file", default=None, help="Path to last-run state file")
    args = parser.parse_args()

    since = read_since(args.since_file) if args.since_file else default_since()
    print(f"Fetching entries since: {since.strftime('%Y-%m-%d %H:%M')} UTC", file=sys.stderr)

    with open(args.feeds) as f:
        config = yaml.safe_load(f)

    if not config:
        print("WARNING: feeds config is empty", file=sys.stderr)
        return

    if args.output:
        with open(args.output, "w") as out:
            write_feeds(config, out, since)
    else:
        write_feeds(config, sys.stdout, since)


if __name__ == "__main__":
    main()
