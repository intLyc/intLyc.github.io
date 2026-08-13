#!/usr/bin/env python3
"""Safely refresh Google Scholar citation data."""

from __future__ import annotations

import os
import re
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from data_utils import DataValidationError, atomic_dump_yaml, load_yaml_mapping, today_iso

REPO_ROOT = Path(__file__).resolve().parents[1]
SOCIALS_FILE = REPO_ROOT / "_data" / "socials.yml"
BIBLIOGRAPHY_FILE = REPO_ROOT / "_bibliography" / "papers.bib"
OUTPUT_FILE = REPO_ROOT / "_data" / "citations.yml"


class ScholarProfileParser(HTMLParser):
    """Extract publication metadata from a public Scholar profile page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.publications: list[dict[str, object]] = []
        self._publication: dict[str, object] | None = None
        self._field: str | None = None
        self._field_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "tr" and "gsc_a_tr" in classes:
            self._publication = {}
            return
        if self._publication is None:
            return
        if tag == "a" and "gsc_a_at" in classes:
            query = urllib.parse.parse_qs(
                urllib.parse.urlparse(attributes.get("href") or "").query
            )
            publication_ids = query.get("citation_for_view") or []
            if publication_ids:
                self._publication["pub_id"] = publication_ids[0]
            self._start_field("title")
        elif tag == "a" and "gsc_a_ac" in classes:
            self._start_field("citations")
        elif tag == "td" and "gsc_a_y" in classes:
            self._start_field("year")

    def handle_data(self, data: str) -> None:
        if self._field is not None:
            self._field_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._publication is None:
            return
        if self._field == "title" and tag == "a":
            self._finish_field()
        elif self._field == "citations" and tag == "a":
            self._finish_field()
        elif self._field == "year" and tag == "td":
            self._finish_field()
        elif tag == "tr":
            title = str(self._publication.get("title") or "").strip()
            citation_text = str(self._publication.get("citations") or "").strip()
            self._publication["bib"] = {
                "title": title,
                "pub_year": str(self._publication.pop("year", "")).strip(),
            }
            self._publication["num_citations"] = int(citation_text or "0")
            self._publication.pop("title", None)
            self._publication.pop("citations", None)
            self.publications.append(self._publication)
            self._publication = None
            self._field = None

    def _start_field(self, field: str) -> None:
        self._field = field
        self._field_parts = []

    def _finish_field(self) -> None:
        if self._publication is not None and self._field is not None:
            self._publication[self._field] = "".join(self._field_parts).strip()
        self._field = None
        self._field_parts = []


def parse_public_profile(html: str) -> list[dict[str, object]]:
    """Parse one Scholar profile page and reject block/error responses."""

    parser = ScholarProfileParser()
    parser.feed(html)
    if not parser.publications:
        raise DataValidationError("public Google Scholar profile returned no publications")
    return parser.publications


def fetch_public_profile(scholar_user_id: str) -> dict[str, object]:
    """Fetch all publications directly from the public Scholar profile."""

    publications: list[dict[str, object]] = []
    page_size = 100
    for start in range(0, 1000, page_size):
        query = urllib.parse.urlencode(
            {
                "user": scholar_user_id,
                "hl": "en",
                "cstart": start,
                "pagesize": page_size,
            }
        )
        request = urllib.request.Request(
            f"https://scholar.google.com/citations?{query}",
            headers={
                "Accept-Language": "en-US,en;q=0.9",
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/127.0.0.0 Safari/537.36"
                ),
            },
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            page = parse_public_profile(response.read().decode("utf-8", errors="replace"))
        publications.extend(page)
        if len(page) < page_size:
            break
    return {"publications": publications}


def fetch_author_data(scholar_user_id: str, client: Any | None = None) -> dict[str, Any]:
    """Use the public profile first, with scholarly as a compatibility fallback."""

    if client is not None:
        client.set_timeout(15)
        client.set_retries(3)
        return client.fill(client.search_author_id(scholar_user_id))

    try:
        return fetch_public_profile(scholar_user_id)
    except Exception as direct_error:  # noqa: BLE001 - fallback boundary
        print(f"Direct Scholar profile fetch failed: {direct_error}; trying scholarly.")

    try:
        from scholarly import scholarly

        scholarly.set_timeout(15)
        scholarly.set_retries(3)
        return scholarly.fill(scholarly.search_author_id(scholar_user_id))
    except Exception as scholarly_error:  # noqa: BLE001 - fallback boundary
        raise DataValidationError(
            f"both Google Scholar fetch methods failed; scholarly: {scholarly_error}"
        ) from scholarly_error


def load_scholar_user_id() -> str:
    """Load the single canonical Google Scholar user ID."""

    config = load_yaml_mapping(SOCIALS_FILE)
    scholar_user_id = str((config or {}).get("scholar_userid") or "").strip()
    if not scholar_user_id:
        raise DataValidationError("scholar_userid is required in _data/socials.yml")
    return scholar_user_id


def load_expected_publication_ids() -> set[str]:
    """Read every Scholar publication ID displayed by the bibliography."""

    if not BIBLIOGRAPHY_FILE.exists():
        raise DataValidationError(f"bibliography not found: {BIBLIOGRAPHY_FILE}")
    text = BIBLIOGRAPHY_FILE.read_text(encoding="utf-8")
    expected = set(re.findall(r"google_scholar_id\s*=\s*\{([^}]+)\}", text))
    if not expected:
        raise DataValidationError("bibliography contains no google_scholar_id entries")
    return expected


def _publication_suffix(publication_id: str) -> str:
    return publication_id.rsplit(":", 1)[-1]


def build_citation_data(author_data: dict[str, Any]) -> dict[str, dict[str, object]]:
    """Validate and normalize every publication returned by Scholar."""

    publications = author_data.get("publications")
    if not isinstance(publications, list) or not publications:
        raise DataValidationError("Google Scholar returned no publications")

    papers: dict[str, dict[str, object]] = {}
    errors: list[str] = []
    for publication in publications:
        if not isinstance(publication, dict):
            errors.append("publication entry is not an object")
            continue
        bib = publication.get("bib")
        if not isinstance(bib, dict):
            errors.append("publication has no bibliography object")
            continue
        publication_id = publication.get("pub_id") or publication.get("author_pub_id")
        title = str(bib.get("title") or "").strip()
        year = str(bib.get("pub_year") or "").strip()
        citations = publication.get("num_citations")
        if not publication_id:
            errors.append(f"publication has no ID: {title or 'unknown title'}")
            continue
        publication_id = str(publication_id)
        if not title:
            errors.append(f"publication has no title: {publication_id}")
            continue
        if isinstance(citations, bool) or not isinstance(citations, int) or citations < 0:
            errors.append(f"invalid citation count for {publication_id}: {citations!r}")
            continue
        if publication_id in papers:
            errors.append(f"duplicate publication ID: {publication_id}")
            continue
        papers[publication_id] = {
            "citations": citations,
            "title": title,
            "year": year or "Unknown Year",
        }
        print(f"Found: {title} ({year or 'Unknown Year'}) - Citations: {citations}")

    if errors:
        raise DataValidationError("; ".join(errors))
    return papers


def validate_complete_result(
    papers: dict[str, dict[str, object]],
    expected_ids: set[str],
    existing_data: dict[str, Any] | None,
) -> None:
    """Reject partial or unexpectedly decreasing Scholar snapshots."""

    returned_suffixes = {_publication_suffix(publication_id) for publication_id in papers}
    missing = sorted(expected_ids - returned_suffixes)
    if missing:
        raise DataValidationError(f"Google Scholar result is missing bibliography IDs: {', '.join(missing)}")

    if not existing_data or os.environ.get("ALLOW_SCHOLAR_DECREASE") == "1":
        return
    existing_papers = existing_data.get("papers")
    if not isinstance(existing_papers, dict):
        return
    if len(papers) < len(existing_papers):
        raise DataValidationError(
            f"Google Scholar publication count decreased from {len(existing_papers)} to {len(papers)}; "
            "set ALLOW_SCHOLAR_DECREASE=1 only after verifying an intentional profile removal"
        )
    for publication_id, old_paper in existing_papers.items():
        if publication_id not in papers or not isinstance(old_paper, dict):
            continue
        old_count = old_paper.get("citations")
        new_count = papers[publication_id].get("citations")
        if isinstance(old_count, int) and isinstance(new_count, int) and new_count < old_count:
            raise DataValidationError(
                f"citations for {publication_id} decreased from {old_count} to {new_count}; "
                "set ALLOW_SCHOLAR_DECREASE=1 only after verifying the change"
            )


def get_scholar_citations(client: Any | None = None) -> bool:
    """Fetch, validate and update Scholar data; return whether a file was written."""

    scholar_user_id = load_scholar_user_id()
    today = today_iso()
    existing_data = load_yaml_mapping(OUTPUT_FILE)

    print(f"Fetching citations for Google Scholar ID: {scholar_user_id}")
    author_data = fetch_author_data(scholar_user_id, client)
    if not isinstance(author_data, dict):
        raise DataValidationError(f"Google Scholar returned invalid author data for {scholar_user_id}")

    papers = build_citation_data(author_data)
    validate_complete_result(papers, load_expected_publication_ids(), existing_data)
    previous_papers = (existing_data or {}).get("papers")
    previous_metadata = (existing_data or {}).get("metadata")
    papers_changed = previous_papers != papers
    last_changed = today if papers_changed else (
        previous_metadata.get("last_changed") or previous_metadata.get("last_updated")
        if isinstance(previous_metadata, dict)
        else today
    )
    citation_data = {
        "metadata": {
            "last_changed": last_changed,
            "last_checked": today,
            "last_updated": today,
            "paper_count": len(papers),
        },
        "papers": papers,
    }
    atomic_dump_yaml(OUTPUT_FILE, citation_data)
    print(f"Citation data checked and saved to {OUTPUT_FILE}")
    return True


def main() -> int:
    try:
        get_scholar_citations()
        return 0
    except Exception as error:  # noqa: BLE001 - command-line boundary
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
