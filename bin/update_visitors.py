#!/usr/bin/env python3
"""Fetch visitor country stats from GoatCounter and write _data/visitors.yml.

Requires the GOATCOUNTER_TOKEN environment variable (API token).
Endpoint: https://[site].goatcounter.com/api/v0/stats/locations
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime

import yaml

SITE = "intlyc.goatcounter.com"


def main() -> None:
    token = os.environ.get("GOATCOUNTER_TOKEN", "")
    url = f"https://{SITE}/api/v0/stats/locations?limit=100"
    req = urllib.request.Request(
        url,
        headers={"Authorization": "Bearer " + token, "User-Agent": "Mozilla/5.0"},
    )
    try:
        data = json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:500]}")
        raise

    rows = data.get("stats", data) if isinstance(data, dict) else data
    countries = []
    for c in rows:
        raw = c.get("id") or c.get("name") or ""
        code = raw.split("-")[0][:2].upper()
        if len(code) != 2:
            continue
        countries.append(
            {
                "country": code,
                "visitors": int(c.get("count", 0)),
                "display_country": c.get("name") or code,
            }
        )
    countries.sort(key=lambda x: -x["visitors"])

    out = {
        "metadata": {"last_updated": datetime.now().strftime("%Y-%m-%d")},
        "countries": countries,
    }
    with open("_data/visitors.yml", "w") as f:
        yaml.dump(out, f, width=1000, sort_keys=True)
    print(f"countries: {len(countries)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001 - report and exit non-zero for callers
        print(f"Error: {e}")
        sys.exit(1)
