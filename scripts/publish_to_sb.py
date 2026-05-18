#!/usr/bin/env python3
"""Publish weekly digest to SilverBullet."""

import argparse
import json
import re
import sys
from datetime import datetime

from auth import SB_BASE_URL, get_session


def page_name(agent: str) -> str:
    now = datetime.now()
    year, week, _ = now.isocalendar()
    return f"Digest/{year}-W{week:02d}-{agent}"


def is_podcast(item: dict) -> bool:
    return item.get("source_type") == "podcast" or bool(item.get("podcast_page") or item.get("podcast_mp3"))

def is_video(item: dict) -> bool:
    return item.get("source_type") == "video"

def is_release(item: dict) -> bool:
    return item.get("source_type") == "release"


def get_existing_page(session, page_url: str) -> str:
    resp = session.get(page_url, timeout=15)
    if resp.status_code != 200:
        return ""
    resp.encoding = "utf-8"
    return resp.text


def extract_checked(page_content: str) -> dict[str, str]:
    """Return {url: full_line} for all checked items in the page."""
    checked = {}
    for m in re.finditer(r"(- \[x\][^\n]*\((https?://[^)]+)\)[^\n]*)", page_content):
        url = m.group(2)
        checked[url] = m.group(1)
    return checked


PERSONAL_CATEGORIES = [
    ("homelab",      "🏠 Homelab"),
    ("emulation",    "🕹️ Emulation & Retro"),
    ("ereader",      "📖 E-Readers"),
    ("games",        "🎮 Games"),
    ("tv_film",      "📺 TV & Films"),
    ("books",        "📚 Books"),
    ("investing",    "💰 Investing & Money"),
    ("world_trends", "🌍 World & Trends"),
]


def render_item(item: dict, checked_links: set[str]) -> list[str]:
    lines = []
    url = item.get("podcast_page") or item["url"]
    tick = "x" if url in checked_links else " "
    lines += [
        f"- [{tick}] **[{item['title']}]({item['url']})**",
        f"  *Source: {item['source']} | Score: {item['score']}/10*",
        f"  > {item['reasoning']}",
    ]
    if is_podcast(item):
        link_parts = []
        if item.get("podcast_page"):
            link_parts.append(f"[🔗 Episode page]({item['podcast_page']})")
        if item.get("podcast_mp3"):
            link_parts.append(f"[🎧 Listen (MP3)]({item['podcast_mp3']})")
        if link_parts:
            lines.append("  " + " | ".join(link_parts))
    lines.append("")
    return lines


def build_markdown_personal(items: list[dict], checked_links: set[str], previously_checked: dict[str, str]) -> str:
    now = datetime.now()
    year, week, _ = now.isocalendar()
    generated = now.strftime("%Y-%m-%d %H:%M")
    items = sorted(items, key=lambda i: i.get("score", 0), reverse=True)

    lines = [
        f"# 🎮 Weekly Digest — Week {week} / {year} (Personal)",
        "",
        f"*Generated: {generated} | Items: {len(items)}*",
        "",
        "---",
        "",
    ]

    categorized: set[str] = set()
    for cat_key, cat_label in PERSONAL_CATEGORIES:
        cat_items = [i for i in items if i.get("category") == cat_key]
        if not cat_items:
            continue
        lines += [f"## {cat_label}", ""]
        for item in cat_items:
            lines += render_item(item, checked_links)
            categorized.add(item["url"])

    uncategorized = [i for i in items if i["url"] not in categorized]
    if uncategorized:
        lines += ["## 📌 Other", ""]
        for item in uncategorized:
            lines += render_item(item, checked_links)

    new_urls = {item["url"] for item in items}
    orphaned = {url: line for url, line in previously_checked.items() if url not in new_urls}
    if orphaned:
        lines += ["", "---", "", "## ✅ Previously Read", ""]
        lines += list(orphaned.values())
        lines.append("")

    return "\n".join(lines)


def build_markdown(items: list[dict], agent: str, checked_links: set[str] | None = None, previously_checked: dict[str, str] | None = None) -> str:
    checked_links = checked_links or set()
    previously_checked = previously_checked or {}
    if agent == "personal":
        return build_markdown_personal(items, checked_links, previously_checked)

    now = datetime.now()
    year, week, _ = now.isocalendar()
    label = "Pro" if agent == "pro" else "Personal"
    generated = now.strftime("%Y-%m-%d %H:%M")

    items = sorted(items, key=lambda i: i.get("score", 0), reverse=True)
    articles = [i for i in items if not is_podcast(i) and not is_video(i) and not is_release(i)]
    podcasts = [i for i in items if is_podcast(i)]
    videos = [i for i in items if is_video(i)]
    releases = [i for i in items if is_release(i)]

    lines = [
        f"# 📰 Weekly Digest — Week {week} / {year} ({label})",
        "",
        f"*Generated: {generated} | Items: {len(items)}*",
        "",
        "---",
        "",
    ]

    if articles:
        lines += ["## 🔥 This Week's Picks", ""]
        for item in articles:
            url = item["url"]
            tick = "x" if url in checked_links else " "
            lines += [
                f"- [{tick}] **[{item['title']}]({url})**",
                f"  *Source: {item['source']} | Score: {item['score']}/10*",
                f"  > {item['reasoning']}",
                "",
            ]

    if podcasts:
        lines += ["## 🎧 Podcasts", ""]
        for item in podcasts:
            url = item.get("podcast_page") or item["url"]
            tick = "x" if url in checked_links else " "
            lines += [
                f"- [{tick}] **[{item['title']}]({url})**",
                f"  *Podcast: {item['source']} | Score: {item['score']}/10*",
                f"  > {item['reasoning']}",
                "",
            ]
            link_parts = []
            if item.get("podcast_page"):
                link_parts.append(f"[🔗 Episode page]({item['podcast_page']})")
            if item.get("podcast_mp3"):
                link_parts.append(f"[🎧 Listen (MP3)]({item['podcast_mp3']})")
            if link_parts:
                lines.append("  " + " | ".join(link_parts))
            lines.append("")

    if videos:
        lines += ["## ▶ YouTube", ""]
        for item in videos:
            url = item["url"]
            tick = "x" if url in checked_links else " "
            lines += [
                f"- [{tick}] **[{item['title']}]({url})**",
                f"  *{item['source']} | Score: {item['score']}/10*",
                f"  > {item['reasoning']}",
                "",
            ]

    if releases:
        lines += ["## 🚀 GitHub Releases", ""]
        for item in releases:
            url = item["url"]
            tick = "x" if url in checked_links else " "
            lines += [
                f"- [{tick}] **[{item['title']}]({url})**",
                f"  *{item['source']} | Score: {item['score']}/10*",
                f"  > {item['reasoning']}",
                "",
            ]

    # Items checked in a previous run but not in this digest → preserve as history
    new_urls = {item["url"] for item in items} | {item.get("podcast_page") or item["url"] for item in items}
    orphaned = {url: line for url, line in previously_checked.items() if url not in new_urls}
    if orphaned:
        lines += ["", "---", "", "## ✅ Previously Read", ""]
        lines += list(orphaned.values())
        lines.append("")

    return "\n".join(lines)


def publish(session, page: str, content: str) -> None:
    url = f"{SB_BASE_URL}/.fs/{page}.md"
    resp = session.put(
        url,
        data=content.encode("utf-8"),
        headers={"Content-Type": "text/markdown"},
        timeout=15,
    )
    if resp.status_code not in (200, 201):
        print(f"ERROR: Publish failed: HTTP {resp.status_code} — {resp.text[:200]}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", required=True)
    parser.add_argument("--input", default=None, help="JSON file (default: stdin)")
    args = parser.parse_args()

    if args.input:
        with open(args.input) as f:
            raw = f.read()
    else:
        raw = sys.stdin.read()

    # Gemini sometimes wraps JSON output in markdown code fences — strip them
    raw = raw.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
    if raw.endswith("```"):
        raw = "\n".join(raw.split("\n")[:-1])

    # Gemini occasionally drops the colon in JSON keys, e.g. "source_type: "
    raw = re.sub(r'"([a-z_]+): "', r'"\1": "', raw)

    # Podcast link fields sometimes contain markdown instead of raw URLs — unwrap them
    raw = re.sub(r'"\[.*?\]\((https?://[^)]+)\)"', r'"\1"', raw)

    try:
        items = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    before = len(items)
    items = [i for i in items if i.get("url")]
    dropped = before - len(items)
    if dropped:
        print(f"WARNING: {dropped} item(s) dropped — missing 'url' field", file=sys.stderr)

    session = get_session()
    page = page_name(args.agent)
    page_url = f"{SB_BASE_URL}/.fs/{page}.md"
    old_content = get_existing_page(session, page_url)
    previously_checked = extract_checked(old_content)
    checked_links = set(previously_checked.keys())
    content = build_markdown(items, args.agent, checked_links, previously_checked)
    publish(session, page, content)
    print(f"Published: {page}")


if __name__ == "__main__":
    main()
