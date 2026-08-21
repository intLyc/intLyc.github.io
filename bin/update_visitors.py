#!/usr/bin/env python3
"""Fetch cumulative visitor country stats and write _data/visitors.yml.

Requires the GOATCOUNTER_TOKEN environment variable (API token).
Endpoint: https://[site].goatcounter.com/api/v0/stats/locations
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from data_utils import DataValidationError, atomic_dump_yaml, load_yaml_mapping, today_iso

SITE = "intlyc.goatcounter.com"
PER_PAGE = 100
MAX_PAGES = 10
MAX_ATTEMPTS = 4
RETRYABLE_HTTP_CODES = {404, 408, 425, 429}
# GoatCounter began collecting data for this site on 2026-08-08. Supplying an
# explicit start is essential: the API otherwise defaults to only the last week.
DEFAULT_START = "2026-08-08T00:00:00Z"
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = REPO_ROOT / "_data" / "visitors.yml"
DISPLAY_COUNTRY_OVERRIDES = {"CN": "Mainland China"}


def _get_json(url: str, token: str) -> object:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "User-Agent": "intlyc-homepage-data-refresh",
        },
    )
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", "replace")[:500]
            retryable = error.code in RETRYABLE_HTTP_CODES or 500 <= error.code <= 599
            if retryable and attempt < MAX_ATTEMPTS:
                retry_after = error.headers.get("Retry-After") if error.headers else None
                delay = int(retry_after) if retry_after and retry_after.isdigit() else 2 ** (attempt - 1)
                delay = min(delay, 30)
                print(
                    f"HTTP {error.code}: {body}; retrying in {delay}s "
                    f"({attempt}/{MAX_ATTEMPTS})"
                )
                time.sleep(delay)
                continue
            print(f"HTTP {error.code}: {body}")
            raise
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt < MAX_ATTEMPTS:
                delay = 2 ** (attempt - 1)
                print(f"Network error: {error}; retrying in {delay}s ({attempt}/{MAX_ATTEMPTS})")
                time.sleep(delay)
                continue
            raise
    raise RuntimeError("unreachable GoatCounter retry state")


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
                "display_country": DISPLAY_COUNTRY_OVERRIDES.get(
                    raw_code, str(row.get("name") or raw_code)
                ),
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


def validate_snapshot(data: dict[str, object] | None) -> int:
    """Validate that a stored snapshot is safe to use as a deployment fallback."""

    if not data:
        raise DataValidationError("visitor fallback snapshot is missing or empty")
    metadata = data.get("metadata")
    countries = data.get("countries")
    if not isinstance(metadata, dict) or not isinstance(countries, list) or not countries:
        raise DataValidationError("visitor fallback snapshot must contain metadata and countries")
    period_start = metadata.get("period_start")
    if not isinstance(period_start, str) or not period_start.strip():
        raise DataValidationError("visitor fallback snapshot has no cumulative period_start")

    seen: set[str] = set()
    total = 0
    for item in countries:
        if not isinstance(item, dict):
            raise DataValidationError("visitor fallback countries must be objects")
        code = str(item.get("country") or "").upper()
        count = item.get("visitors")
        if not re.fullmatch(r"[A-Z]{2}", code) or code in seen:
            raise DataValidationError(f"invalid or duplicate fallback country: {code!r}")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise DataValidationError(f"invalid fallback visitor count for {code}: {count!r}")
        seen.add(code)
        total += count

    recorded_total = metadata.get("total_visitors")
    if isinstance(recorded_total, bool) or not isinstance(recorded_total, int):
        raise DataValidationError("visitor fallback snapshot has no valid total_visitors")
    if recorded_total != total:
        raise DataValidationError(
            f"visitor fallback total mismatch: metadata={recorded_total}, countries={total}"
        )
    return total


def validate_output_snapshot() -> None:
    """Validate and report the snapshot that a failed refresh would deploy."""

    data = load_yaml_mapping(OUTPUT_FILE)
    total = validate_snapshot(data)
    print(f"validated visitor fallback: {total} cumulative visitors")


def main(validate_only: bool = False) -> None:
    if validate_only:
        validate_output_snapshot()
        return

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
    validate_snapshot(out)
    atomic_dump_yaml(OUTPUT_FILE, out)
    print(f"countries: {len(countries)}, cumulative visitors: {out['metadata']['total_visitors']}")


if __name__ == "__main__":
    try:
        main(validate_only="--validate-snapshot" in sys.argv[1:])
    except Exception as e:  # noqa: BLE001 - report and exit non-zero for callers
        print(f"Error: {e}")
        sys.exit(1)
