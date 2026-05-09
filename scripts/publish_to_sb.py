#!/usr/bin/env python3
"""Publish weekly digest to SilverBullet."""

import json
import os
import sys
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

SB_BASE_URL = os.environ["SB_BASE_URL"].rstrip("/")
CF_CLIENT_ID = os.environ["CF_ACCESS_CLIENT_ID"]
CF_CLIENT_SECRET = os.environ["CF_ACCESS_CLIENT_SECRET"]
SB_USER = os.environ["SB_USER"]
SB_PASSWORD = os.environ["SB_PASSWORD"]

CF_HEADERS = {
    "CF-Access-Client-Id": CF_CLIENT_ID,
    "CF-Access-Client-Secret": CF_CLIENT_SECRET,
}


def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(CF_HEADERS)
    resp = session.post(
        f"{SB_BASE_URL}/.auth",
        data={"username": SB_USER, "password": SB_PASSWORD},
        timeout=10,
    )
    if resp.status_code != 200:
        print(f"ERROR: SilverBullet auth failed: {resp.status_code}", file=sys.stderr)
        sys.exit(1)
    return session


def page_name(agent: str) -> str:
    now = datetime.now()
    year, week, _ = now.isocalendar()
    return f"Digest/{year}-W{week:02d}-{agent}"


def build_markdown(items: list[dict], agent: str) -> str:
    now = datetime.now()
    year, week, _ = now.isocalendar()
    label = "Pro" if agent == "pro" else "Personal"
    generated = now.strftime("%Y-%m-%d %H:%M")

    articles = [i for i in items if not i.get("podcast_sivu") and not i.get("podcast_mp3")]
    podcasts = [i for i in items if i.get("podcast_sivu") or i.get("podcast_mp3")]
    releases = []  # GitHub releases come in via separate step (future)

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
            lines += [
                f"### [{item['otsikko']}]({item['linkki']})",
                f"*Lähde: {item['lahde']} | Pisteet: {item['pisteet']}/10*",
                f"> {item['perustelu']}",
                "",
                "---",
                "",
            ]

    if podcasts:
        lines += ["## 🎧 Podcastit", ""]
        for item in podcasts:
            lines += [
                f"### [{item['otsikko']}]({item.get('podcast_sivu') or item['linkki']})",
                f"*Podcast: {item['lahde']} | Pisteet: {item['pisteet']}/10*",
                f"> {item['perustelu']}",
                "",
            ]
            link_parts = []
            if item.get("podcast_sivu"):
                link_parts.append(f"[🔗 Avaa jakson sivu]({item['podcast_sivu']})")
            if item.get("podcast_mp3"):
                link_parts.append(f"[🎧 Kuuntele (MP3)]({item['podcast_mp3']})")
            if link_parts:
                lines.append(" | ".join(link_parts))
            lines += ["", "---", ""]

    return "\n".join(lines)


def publish(session: requests.Session, page: str, content: str) -> None:
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
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", required=True)
    parser.add_argument("--input", default=None, help="JSON file (default: stdin)")
    args = parser.parse_args()

    if args.input:
        with open(args.input) as f:
            raw = f.read()
    else:
        raw = sys.stdin.read()

    # Strip markdown code fences if Gemini wrapped the JSON
    raw = raw.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
    if raw.endswith("```"):
        raw = "\n".join(raw.split("\n")[:-1])

    try:
        items = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    session = get_session()
    page = page_name(args.agent)
    content = build_markdown(items, args.agent)
    publish(session, page, content)
    print(f"Published: {page}")


if __name__ == "__main__":
    main()
