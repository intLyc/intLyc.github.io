#!/usr/bin/env python3
"""Fetch total GitHub stars for the user's repos and write _data/github.yml."""

import json
import os
import sys
import urllib.request
from datetime import datetime

import yaml

OWNER = "intLyc"


def main() -> None:
    url = f"https://api.github.com/users/{OWNER}/repos?per_page=100&type=owner"
    # Authenticate with GITHUB_TOKEN when available (CI): unauthenticated
    # requests from shared runner IPs hit the 60 req/h rate limit (HTTP 403).
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    data = json.load(urllib.request.urlopen(req, timeout=30))
    total = sum(r.get("stargazers_count", 0) for r in data)

    out = {
        "metadata": {"last_updated": datetime.now().strftime("%Y-%m-%d")},
        "total_stars": total,
    }
    with open("_data/github.yml", "w") as f:
        yaml.dump(out, f, width=1000, sort_keys=True)
    print(f"total stars: {total}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001 - report and exit non-zero for callers
        print(f"Error: {e}")
        sys.exit(1)
