"""Shared SilverBullet auth helpers."""

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
