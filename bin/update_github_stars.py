#!/usr/bin/env python3
"""Fetch total stars for the user's original repositories."""

import json
import os
import sys
import urllib.request
from pathlib import Path

from data_utils import DataValidationError, atomic_dump_yaml, load_yaml_mapping, today_iso

PER_PAGE = 100
MAX_PAGES = 100
REPO_ROOT = Path(__file__).resolve().parents[1]
SOCIALS_FILE = REPO_ROOT / "_data" / "socials.yml"
OUTPUT_FILE = REPO_ROOT / "_data" / "github.yml"


def load_owner() -> str:
    socials = load_yaml_mapping(SOCIALS_FILE)
    owner = str((socials or {}).get("github_username") or "").strip()
    if not owner:
        raise DataValidationError("github_username is required in _data/socials.yml")
    return owner


def _get_json(url: str, token: str) -> object:
    # Authenticate with GITHUB_TOKEN when available (CI): unauthenticated
    # requests from shared runner IPs hit the 60 req/h rate limit (HTTP 403).
    headers = {
        "User-Agent": "intlyc-homepage-data-refresh",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def fetch_repositories(owner: str, token: str) -> list[dict[str, object]]:
    repositories: list[dict[str, object]] = []
    for page in range(1, MAX_PAGES + 1):
        url = (
            f"https://api.github.com/users/{owner}/repos"
            f"?per_page={PER_PAGE}&page={page}&type=owner&sort=full_name"
        )
        data = _get_json(url, token)
        if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
            raise DataValidationError("GitHub repositories response must be a list of objects")
        repositories.extend(data)
        if len(data) < PER_PAGE:
            return repositories
    raise DataValidationError("GitHub repository pagination exceeded the safety limit")


def main() -> None:
    owner = load_owner()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    repositories = fetch_repositories(owner, token)
    original_repositories = [repo for repo in repositories if repo.get("fork") is not True]
    if not original_repositories:
        raise DataValidationError(f"GitHub returned no original repositories for {owner}")

    stars: list[int] = []
    for repository in original_repositories:
        count = repository.get("stargazers_count")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise DataValidationError(f"invalid stargazers_count: {count!r}")
        stars.append(count)
    total = sum(stars)

    out = {
        "metadata": {
            "excluded_forks": len(repositories) - len(original_repositories),
            "last_updated": today_iso(),
            "owner": owner,
            "repository_count": len(original_repositories),
        },
        "total_stars": total,
    }
    atomic_dump_yaml(OUTPUT_FILE, out)
    print(
        f"total stars: {total} across {len(original_repositories)} original repositories "
        f"({out['metadata']['excluded_forks']} forks excluded)"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001 - report and exit non-zero for callers
        print(f"Error: {e}")
        sys.exit(1)
