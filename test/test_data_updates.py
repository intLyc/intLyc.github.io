"""Regression tests for dynamic homepage data refreshers."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "bin"))

import data_utils  # noqa: E402
import update_github_stars  # noqa: E402
import update_scholar_citations  # noqa: E402
import update_visitors  # noqa: E402


class DataUpdateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_visitors_use_explicit_cumulative_start_and_pagination(self) -> None:
        output = self.root / "visitors.yml"
        responses = [
            {
                "stats": [{"id": "SG", "name": "Singapore", "count": 14}],
                "more": True,
            },
            {
                "stats": [{"id": "US", "name": "United States", "count": 3}],
                "more": False,
            },
        ]
        with (
            mock.patch.object(update_visitors, "OUTPUT_FILE", output),
            mock.patch.object(update_visitors, "_get_json", side_effect=responses) as get_json,
            mock.patch.dict(os.environ, {"GOATCOUNTER_TOKEN": "token"}, clear=False),
        ):
            update_visitors.main()

        result = yaml.safe_load(output.read_text(encoding="utf-8"))
        self.assertEqual(result["metadata"]["period_start"], update_visitors.DEFAULT_START)
        self.assertEqual(result["metadata"]["total_visitors"], 17)
        self.assertEqual([item["country"] for item in result["countries"]], ["SG", "US"])
        self.assertIn("start=2026-08-08T00%3A00%3A00Z", get_json.call_args_list[0].args[0])
        self.assertIn("offset=1", get_json.call_args_list[1].args[0])

    def test_visitors_reject_decrease_without_overwriting_last_good_data(self) -> None:
        output = self.root / "visitors.yml"
        original = {
            "countries": [{"country": "SG", "display_country": "Singapore", "visitors": 10}],
            "metadata": {"last_updated": "2026-08-08"},
        }
        data_utils.atomic_dump_yaml(output, original)
        response = {
            "stats": [{"id": "SG", "name": "Singapore", "count": 9}],
            "more": False,
        }
        before = output.read_bytes()
        with (
            mock.patch.object(update_visitors, "OUTPUT_FILE", output),
            mock.patch.object(update_visitors, "_get_json", return_value=response),
            mock.patch.dict(os.environ, {"GOATCOUNTER_TOKEN": "token"}, clear=False),
            self.assertRaises(data_utils.DataValidationError),
        ):
            update_visitors.main()
        self.assertEqual(output.read_bytes(), before)

    def test_github_paginates_and_excludes_forks(self) -> None:
        output = self.root / "github.yml"
        socials = self.root / "socials.yml"
        socials.write_text("github_username: intLyc\n", encoding="utf-8")
        first_page = [
            {"fork": False, "stargazers_count": 1, "name": f"repo-{index}"}
            for index in range(100)
        ]
        second_page = [{"fork": True, "stargazers_count": 50, "name": "fork"}]
        with (
            mock.patch.object(update_github_stars, "OUTPUT_FILE", output),
            mock.patch.object(update_github_stars, "SOCIALS_FILE", socials),
            mock.patch.object(
                update_github_stars, "_get_json", side_effect=[first_page, second_page]
            ) as get_json,
        ):
            update_github_stars.main()

        result = yaml.safe_load(output.read_text(encoding="utf-8"))
        self.assertEqual(result["total_stars"], 100)
        self.assertEqual(result["metadata"]["repository_count"], 100)
        self.assertEqual(result["metadata"]["excluded_forks"], 1)
        self.assertEqual(get_json.call_count, 2)

    def test_scholar_can_initialize_a_missing_output_file(self) -> None:
        output = self.root / "citations.yml"
        socials = self.root / "socials.yml"
        bibliography = self.root / "papers.bib"
        socials.write_text("scholar_userid: user-id\n", encoding="utf-8")
        bibliography.write_text("@article{x, google_scholar_id={paper-id}}\n", encoding="utf-8")
        author_data = {
            "publications": [
                {
                    "pub_id": "user-id:paper-id",
                    "bib": {"title": "Paper", "pub_year": "2026"},
                    "num_citations": 1,
                }
            ]
        }
        client = mock.Mock()
        client.search_author_id.return_value = {}
        client.fill.return_value = author_data
        with (
            mock.patch.object(update_scholar_citations, "OUTPUT_FILE", output),
            mock.patch.object(update_scholar_citations, "SOCIALS_FILE", socials),
            mock.patch.object(update_scholar_citations, "BIBLIOGRAPHY_FILE", bibliography),
        ):
            self.assertTrue(update_scholar_citations.get_scholar_citations(client))

        result = yaml.safe_load(output.read_text(encoding="utf-8"))
        self.assertEqual(result["papers"]["user-id:paper-id"]["citations"], 1)
        self.assertEqual(result["metadata"]["paper_count"], 1)

    def test_scholar_rejects_partial_response_without_overwriting(self) -> None:
        output = self.root / "citations.yml"
        socials = self.root / "socials.yml"
        bibliography = self.root / "papers.bib"
        socials.write_text("scholar_userid: user-id\n", encoding="utf-8")
        bibliography.write_text(
            "@article{x, google_scholar_id={required-id}}\n", encoding="utf-8"
        )
        original = {
            "metadata": {"last_updated": "2026-08-01"},
            "papers": {"user-id:required-id": {"citations": 5, "title": "Old", "year": "2025"}},
        }
        data_utils.atomic_dump_yaml(output, original)
        before = output.read_bytes()
        partial = {
            "publications": [
                {
                    "pub_id": "user-id:different-id",
                    "bib": {"title": "Different", "pub_year": "2026"},
                    "num_citations": 1,
                }
            ]
        }
        client = mock.Mock()
        client.search_author_id.return_value = {}
        client.fill.return_value = partial
        with (
            mock.patch.object(update_scholar_citations, "OUTPUT_FILE", output),
            mock.patch.object(update_scholar_citations, "SOCIALS_FILE", socials),
            mock.patch.object(update_scholar_citations, "BIBLIOGRAPHY_FILE", bibliography),
            self.assertRaises(data_utils.DataValidationError),
        ):
            update_scholar_citations.get_scholar_citations(client)
        self.assertEqual(output.read_bytes(), before)

    def test_atomic_yaml_write_preserves_original_on_serialization_failure(self) -> None:
        output = self.root / "data.yml"
        output.write_text("value: original\n", encoding="utf-8")
        with (
            mock.patch.object(data_utils.yaml, "safe_dump", side_effect=OSError("disk error")),
            self.assertRaises(OSError),
        ):
            data_utils.atomic_dump_yaml(output, {"value": "replacement"})
        self.assertEqual(output.read_text(encoding="utf-8"), "value: original\n")
        self.assertEqual(list(self.root.glob(".data.yml.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
