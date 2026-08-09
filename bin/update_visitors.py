#!/usr/bin/env python3
"""Fetch cumulative visitor country stats and write _data/visitors.yml.

Requires the GOATCOUNTER_TOKEN environment variable (API token).
Endpoint: https://[site].goatcounter.com/api/v0/stats/locations
"""

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from data_utils import DataValidationError, atomic_dump_yaml, load_yaml_mapping, today_iso

SITE = "intlyc.goatcounter.com"
PER_PAGE = 100
MAX_PAGES = 10
# GoatCounter began collecting data for this site on 2026-08-08. Supplying an
# explicit start is essential: the API otherwise defaults to only the last week.
DEFAULT_START = "2026-08-08T00:00:00Z"
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = REPO_ROOT / "_data" / "visitors.yml"


def _get_json(url: str, token: str) -> object:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "User-Agent": "intlyc-homepage-data-refresh",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:500]}")
        raise


def fetch_countries(token: str, start: str) -> list[dict[str, object]]:
    """Fetch every country page for an explicit cumulative date range."""

    countries_by_code: dict[str, dict[str, object]] = {}
    offset = 0
    for _ in range(MAX_PAGES):
        query = urllib.parse.urlencode({"start": start, "limit": PER_PAGE, "offset": offset})
        url = f"https://{SITE}/api/v0/stats/locations?{query}"
        data = _get_json(url, token)
        if not isinstance(data, dict) or not isinstance(data.get("stats"), list):
            raise DataValidationError("GoatCounter response must contain a stats list")

        rows = data["stats"]
        for row in rows:
            if not isinstance(row, dict):
                raise DataValidationError("GoatCounter stats entries must be objects")
            raw_code = str(row.get("id") or "").upper()
            # The top-level locations endpoint should contain ISO country IDs.
            # Ignore unknown locations and region detail IDs such as US-CA.
            if not re.fullmatch(r"[A-Z]{2}", raw_code):
                continue
            count = row.get("count")
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise DataValidationError(f"invalid visitor count for {raw_code}: {count!r}")
            if raw_code in countries_by_code:
                raise DataValidationError(f"duplicate country in GoatCounter response: {raw_code}")
            countries_by_code[raw_code] = {
                "country": raw_code,
                "visitors": count,
                "display_country": str(row.get("name") or raw_code),
            }

        more = data.get("more", False)
        if not isinstance(more, bool):
            raise DataValidationError("GoatCounter more flag must be boolean")
        if not more:
            break
        if not rows:
            raise DataValidationError("GoatCounter pagination reported more data without returning rows")
        offset += len(rows)
    else:
        raise DataValidationError("GoatCounter pagination exceeded the safety limit")

    countries = list(countries_by_code.values())
    countries.sort(key=lambda x: -x["visitors"])
    return countries


def validate_cumulative(
    countries: list[dict[str, object]], existing_data: dict[str, object] | None
) -> None:
    """Reject empty or decreasing data before replacing known cumulative data."""

    if not countries:
        raise DataValidationError("GoatCounter returned no valid countries")
    if not existing_data:
        return
    existing_countries = existing_data.get("countries")
    if not isinstance(existing_countries, list):
        return
    new_counts = {str(item["country"]): int(item["visitors"]) for item in countries}
    for item in existing_countries:
        if not isinstance(item, dict):
            continue
        code = str(item.get("country") or "")
        previous = item.get("visitors")
        if isinstance(previous, int) and new_counts.get(code, -1) < previous:
            raise DataValidationError(
                f"cumulative visitors for {code} decreased from {previous} to {new_counts.get(code, 0)}"
            )


def main() -> None:
    token = os.environ.get("GOATCOUNTER_TOKEN", "").strip()
    if not token:
        raise DataValidationError("GOATCOUNTER_TOKEN is required")
    start = os.environ.get("GOATCOUNTER_START", DEFAULT_START).strip()
    if not start:
        raise DataValidationError("GOATCOUNTER_START must not be empty")

    existing_data = load_yaml_mapping(OUTPUT_FILE)
    countries = fetch_countries(token, start)
    validate_cumulative(countries, existing_data)

    out = {
        "metadata": {
            "last_updated": today_iso(),
            "period_start": start,
            "total_visitors": sum(int(country["visitors"]) for country in countries),
        },
        "countries": countries,
    }
    atomic_dump_yaml(OUTPUT_FILE, out)
    print(f"countries: {len(countries)}, cumulative visitors: {out['metadata']['total_visitors']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001 - report and exit non-zero for callers
        print(f"Error: {e}")
        sys.exit(1)
