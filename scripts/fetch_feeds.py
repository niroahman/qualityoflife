#!/usr/bin/env python3
"""Fetch RSS/Atom feeds and podcasts, output cleaned Markdown."""

import argparse
import os
import re
import sys
from datetime import datetime

import feedparser
import yaml
from dotenv import load_dotenv

load_dotenv()

MAX_ITEMS = int(os.getenv("FEED_MAX_ITEMS", 5))
MAX_DESC = int(os.getenv("FEED_MAX_DESC_CHARS", 400))
TIMEOUT = int(os.getenv("FEED_TIMEOUT_SECS", 10))


def strip_html(text: str) -> str:
    return re.sub(r"<[^<]+?>", "", text or "").strip()


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."


def format_date(entry) -> str:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6]).strftime("%Y-%m-%d")
            except Exception:
                pass
    return "?"


def fetch_feed(feed_cfg: dict, output) -> None:
    name = feed_cfg["name"]
    url = feed_cfg["url"]
    feed_type = feed_cfg.get("type", "feed")

    try:
        parsed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        print(f"WARNING: [{name}] fetch error: {e}", file=sys.stderr)
        return

    if parsed.bozo and not parsed.entries:
        print(f"WARNING: [{name}] empty or malformed feed", file=sys.stderr)
        return

    for entry in parsed.entries[:MAX_ITEMS]:
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
        else:
            if desc:
                output.write(f"{desc}\n")

        output.write("\n---\n\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feeds", default="/tmp/runtime-feeds.yaml")
    parser.add_argument("--output", default=None, help="Output file (default: stdout)")
    args = parser.parse_args()

    with open(args.feeds) as f:
        config = yaml.safe_load(f)

    if not config:
        print("WARNING: feeds config is empty", file=sys.stderr)
        return

    out = open(args.output, "w") if args.output else sys.stdout

    try:
        for section in ("newsletters", "podcasts", "tech_blogs"):
            feeds = config.get(section, [])
            if not feeds:
                continue
            section_label = {"newsletters": "Uutiskirjeet", "podcasts": "Podcastit", "tech_blogs": "Tech-blogit"}[section]
            out.write(f"## {section_label}\n\n")
            for feed_cfg in feeds:
                fetch_feed(feed_cfg, out)
    finally:
        if args.output:
            out.close()


if __name__ == "__main__":
    main()
