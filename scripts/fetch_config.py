#!/usr/bin/env python3
"""Fetch agent config from SilverBullet and write runtime files to /tmp/."""

import argparse
import os
import sys

from auth import SB_BASE_URL, get_session


def fetch_page(session, path: str) -> str:
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

    if not os.path.exists(args.template):
        print(f"ERROR: Template not found: {args.template}", file=sys.stderr)
        sys.exit(1)

    session = get_session()
    agent = args.agent

    profile = fetch_page(session, f"config/curator-{agent}/profile.md")
    feeds = fetch_page(session, f"config/curator-{agent}/feeds.md")

    with open(args.template) as f:
        prompt = f.read().replace("{{PROFILE}}", profile)

    with open("/tmp/runtime-prompt.md", "w") as f:
        f.write(prompt)
    with open("/tmp/runtime-feeds.yaml", "w") as f:
        f.write(feeds)

    print(f"Config fetched for curator-{agent}. Runtime files written to /tmp/.")


if __name__ == "__main__":
    main()
