"""Regression tests for publication BibTeX copy data and markup."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
BIBLIOGRAPHY_FILE = REPO_ROOT / "_bibliography" / "papers.bib"
BIBTEX_DATA_FILE = REPO_ROOT / "_data" / "publication_bibtex.yml"
BIB_LAYOUT_FILE = REPO_ROOT / "_layouts" / "bib.liquid"


class PublicationBibtexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.publication_bibtex = yaml.safe_load(
            BIBTEX_DATA_FILE.read_text(encoding="utf-8")
        )
        cls.website_keys = set(
            re.findall(
                r"^@\w+\{([^,]+),",
                BIBLIOGRAPHY_FILE.read_text(encoding="utf-8"),
                flags=re.MULTILINE,
            )
        )

    def test_every_website_publication_has_exactly_one_bibtex_entry(self) -> None:
        self.assertEqual(set(self.publication_bibtex), self.website_keys)
        self.assertEqual(len(self.publication_bibtex), 13)

    def test_citations_have_required_fields_and_no_private_reference_fields(self) -> None:
        citation_keys = []
        for website_key, citation in self.publication_bibtex.items():
            with self.subTest(publication=website_key):
                match = re.match(r"^@(article|inproceedings)\{([^,]+),", citation)
                self.assertIsNotNone(match)
                citation_keys.append(match.group(2))
                for field in ("author", "title", "year"):
                    self.assertRegex(citation, rf"(?m)^\s+{field}\s*=\s*\{{")
                for private_field in ("file", "groups", "readstatus"):
                    self.assertNotRegex(citation, rf"(?m)^\s+{private_field}\s*=")
                self.assertEqual(citation.count("{"), citation.count("}"))

        self.assertEqual(len(citation_keys), len(set(citation_keys)))

    def test_copy_button_is_rendered_immediately_after_code(self) -> None:
        layout = BIB_LAYOUT_FILE.read_text(encoding="utf-8")
        code_end = layout.index("{% endif %}", layout.index("{% if entry.code %}"))
        copy_button = layout.index("data-bibtex-copy", code_end)
        citation_badge = layout.index(
            "site.enable_publication_badges.google_scholar", copy_button
        )
        self.assertLess(code_end, copy_button)
        self.assertLess(copy_button, citation_badge)


if __name__ == "__main__":
    unittest.main()
