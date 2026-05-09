#!/usr/bin/env python3
"""Fetch agent config from SilverBullet and write runtime files to /tmp/."""

import argparse
import os
import sys

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


def fetch_page(session: requests.Session, path: str) -> str:
    url = f"{SB_BASE_URL}/.fs/{path}"
    resp = session.get(url, timeout=10)
    if resp.status_code != 200:
        print(f"ERROR: Failed to fetch '{path}': HTTP {resp.status_code}", file=sys.stderr)
        sys.exit(1)
    resp.encoding = "utf-8"
    return resp.text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", required=True, help="Agent name: pro or personal")
    parser.add_argument("--template", required=True, help="Path to system-prompt.template.md")
    args = parser.parse_args()

    agent = args.agent
    template_path = args.template

    if not os.path.exists(template_path):
        print(f"ERROR: Template not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    session = get_session()

    profile = fetch_page(session, f"config/curator-{agent}/profile.md")
    feeds = fetch_page(session, f"config/curator-{agent}/feeds.md")
    sources = fetch_page(session, f"config/curator-{agent}/sources.md")

    with open(template_path) as f:
        template = f.read()

    prompt = template.replace("{{PROFILE}}", profile)

    with open("/tmp/runtime-prompt.md", "w") as f:
        f.write(prompt)
    with open("/tmp/runtime-feeds.yaml", "w") as f:
        f.write(feeds)
    with open("/tmp/runtime-sources.yaml", "w") as f:
        f.write(sources)

    print(f"Config fetched for curator-{agent}. Runtime files written to /tmp/.")


if __name__ == "__main__":
    main()
