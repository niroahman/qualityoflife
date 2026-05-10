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
    return item.get("lahde_tyyppi") == "podcast" or bool(item.get("podcast_sivu") or item.get("podcast_mp3"))

def is_video(item: dict) -> bool:
    return item.get("lahde_tyyppi") == "video"

def is_release(item: dict) -> bool:
    return item.get("lahde_tyyppi") == "release"


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
    ("homelab",          "🏠 Homelab"),
    ("emulointi",        "🕹️ Emulointi & Retro"),
    ("lukulaite",        "📖 Lukulaitteet"),
    ("pelit",            "🎮 Pelit"),
    ("tv_elokuva",       "📺 TV & Elokuvat"),
    ("kirjat",           "📚 Kirjat"),
    ("sijoitukset_raha", "💰 Sijoitukset & Raha"),
    ("maailma_ilmiot",   "🌍 Maailma & Ilmiöt"),
]


def render_item(item: dict, checked_links: set[str]) -> list[str]:
    lines = []
    url = item.get("podcast_sivu") or item["linkki"] if is_podcast(item) else item["linkki"]
    tick = "x" if url in checked_links else " "
    lines += [
        f"- [{tick}] **[{item['otsikko']}]({item['linkki']})**",
        f"  *Lähde: {item['lahde']} | Pisteet: {item['pisteet']}/10*",
        f"  > {item['perustelu']}",
    ]
    if is_podcast(item):
        link_parts = []
        if item.get("podcast_sivu"):
            link_parts.append(f"[🔗 Avaa jakson sivu]({item['podcast_sivu']})")
        if item.get("podcast_mp3"):
            link_parts.append(f"[🎧 Kuuntele (MP3)]({item['podcast_mp3']})")
        if link_parts:
            lines.append("  " + " | ".join(link_parts))
    lines.append("")
    return lines


def build_markdown_personal(items: list[dict], checked_links: set[str], previously_checked: dict[str, str]) -> str:
    now = datetime.now()
    year, week, _ = now.isocalendar()
    generated = now.strftime("%Y-%m-%d %H:%M")
    items = sorted(items, key=lambda i: i.get("pisteet", 0), reverse=True)

    lines = [
        f"# 🎮 Viikkodigest — Viikko {week} / {year} (Personal)",
        "",
        f"*Generoitu: {generated} | Nostettu: {len(items)} artikkelia*",
        "",
        "---",
        "",
    ]

    categorized: set[str] = set()
    for cat_key, cat_label in PERSONAL_CATEGORIES:
        cat_items = [i for i in items if i.get("kategoria") == cat_key]
        if not cat_items:
            continue
        lines += [f"## {cat_label}", ""]
        for item in cat_items:
            lines += render_item(item, checked_links)
            categorized.add(item["linkki"])

    uncategorized = [i for i in items if i["linkki"] not in categorized]
    if uncategorized:
        lines += ["## 📌 Muut", ""]
        for item in uncategorized:
            lines += render_item(item, checked_links)

    new_urls = {item["linkki"] for item in items}
    orphaned = {url: line for url, line in previously_checked.items() if url not in new_urls}
    if orphaned:
        lines += ["", "---", "", "## ✅ Luettu aiemmin", ""]
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

    items = sorted(items, key=lambda i: i.get("pisteet", 0), reverse=True)
    articles = [i for i in items if not is_podcast(i) and not is_video(i) and not is_release(i)]
    podcasts = [i for i in items if is_podcast(i)]
    videos = [i for i in items if is_video(i)]
    releases = [i for i in items if is_release(i)]

    lines = [
        f"# 📰 Viikkodigest — Viikko {week} / {year} ({label})",
        "",
        f"*Generoitu: {generated} | Nostettu: {len(items)} artikkelia*",
        "",
        "---",
        "",
    ]

    if articles:
        lines += ["## 🔥 Tällä viikolla kannattaa lukea", ""]
        for item in articles:
            url = item["linkki"]
            tick = "x" if url in checked_links else " "
            lines += [
                f"- [{tick}] **[{item['otsikko']}]({url})**",
                f"  *Lähde: {item['lahde']} | Pisteet: {item['pisteet']}/10*",
                f"  > {item['perustelu']}",
                "",
            ]

    if podcasts:
        lines += ["## 🎧 Podcastit", ""]
        for item in podcasts:
            url = item.get("podcast_sivu") or item["linkki"]
            tick = "x" if url in checked_links else " "
            lines += [
                f"- [{tick}] **[{item['otsikko']}]({url})**",
                f"  *Podcast: {item['lahde']} | Pisteet: {item['pisteet']}/10*",
                f"  > {item['perustelu']}",
                "",
            ]
            link_parts = []
            if item.get("podcast_sivu"):
                link_parts.append(f"[🔗 Avaa jakson sivu]({item['podcast_sivu']})")
            if item.get("podcast_mp3"):
                link_parts.append(f"[🎧 Kuuntele (MP3)]({item['podcast_mp3']})")
            if link_parts:
                lines.append("  " + " | ".join(link_parts))
            lines.append("")

    if videos:
        lines += ["## ▶ YouTube", ""]
        for item in videos:
            url = item["linkki"]
            tick = "x" if url in checked_links else " "
            lines += [
                f"- [{tick}] **[{item['otsikko']}]({url})**",
                f"  *{item['lahde']} | Pisteet: {item['pisteet']}/10*",
                f"  > {item['perustelu']}",
                "",
            ]

    if releases:
        lines += ["## 🚀 GitHub Releases", ""]
        for item in releases:
            url = item["linkki"]
            tick = "x" if url in checked_links else " "
            lines += [
                f"- [{tick}] **[{item['otsikko']}]({url})**",
                f"  *{item['lahde']} | Pisteet: {item['pisteet']}/10*",
                f"  > {item['perustelu']}",
                "",
            ]

    # Items checked in a previous run but not in this digest → preserve as history
    new_urls = {item["linkki"] for item in items} | {item.get("podcast_sivu") or item["linkki"] for item in items}
    orphaned = {url: line for url, line in previously_checked.items() if url not in new_urls}
    if orphaned:
        lines += ["", "---", "", "## ✅ Luettu aiemmin", ""]
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

    # Gemini occasionally drops the colon in JSON keys, e.g. "lahde_tyyppi: "
    raw = re.sub(r'"([a-z_]+): "', r'"\1": "', raw)

    # Podcast link fields sometimes contain markdown instead of raw URLs — unwrap them
    raw = re.sub(r'"\[.*?\]\((https?://[^)]+)\)"', r'"\1"', raw)

    try:
        items = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

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
