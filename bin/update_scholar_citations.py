#!/usr/bin/env python3
"""Safely refresh Google Scholar citation data."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

from data_utils import DataValidationError, atomic_dump_yaml, load_yaml_mapping, today_iso

REPO_ROOT = Path(__file__).resolve().parents[1]
SOCIALS_FILE = REPO_ROOT / "_data" / "socials.yml"
BIBLIOGRAPHY_FILE = REPO_ROOT / "_bibliography" / "papers.bib"
OUTPUT_FILE = REPO_ROOT / "_data" / "citations.yml"


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
    """Validate and normalize every publication returned by scholarly."""

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
    existing_metadata = (existing_data or {}).get("metadata")
    if isinstance(existing_metadata, dict) and (
        existing_metadata.get("last_checked") == today
        or existing_metadata.get("last_updated") == today
    ):
        print(f"Citations were already checked on {today}; skipping fetch.")
        return False

    print(f"Fetching citations for Google Scholar ID: {scholar_user_id}")
    if client is None:
        from scholarly import scholarly as client  # Imported only for a real fetch.

    client.set_timeout(15)
    client.set_retries(3)
    author = client.search_author_id(scholar_user_id)
    author_data = client.fill(author)
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
