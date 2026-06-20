#!/usr/bin/env python3
"""
Unit tests for citation_utils module.

Tests the surviving opencite citation helpers (content-idempotent writes and
the volatile-timestamp comparison) using real data without mocks. The legacy
pre-opencite write path (`create_citation_json_structure` / `save_citation_json`)
and the pickle->json `migrate` helper were removed in epic #180 phase 5.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dataset_citations.core import citation_utils


class TestStripVolatileTimestamps(unittest.TestCase):
    """strip_volatile_timestamps underpins content-idempotent writes (issue #165)."""

    def _payload(self, *, date: str, scoring: str) -> dict:
        return {
            "dataset_id": "ds000001",
            "num_citations": 1,
            "date_last_updated": date,
            "metadata": {"fetch_date": date, "fetch_status": "success"},
            "citation_details": [{"title": "A", "doi": "10.1/a"}],
            "confidence_scoring": {"model_used": "m", "scoring_date": scoring},
        }

    def test_payloads_differing_only_in_timestamps_compare_equal(self):
        a = self._payload(
            date="2026-06-14T10:00:00+00:00", scoring="2026-06-15T01:00:00+00:00"
        )
        b = self._payload(
            date="2026-06-18T10:00:00+00:00", scoring="2026-06-18T19:00:00+00:00"
        )
        self.assertEqual(
            citation_utils.strip_volatile_timestamps(a),
            citation_utils.strip_volatile_timestamps(b),
        )

    def test_substantive_change_compares_unequal(self):
        a = self._payload(
            date="2026-06-14T10:00:00+00:00", scoring="2026-06-15T01:00:00+00:00"
        )
        b = self._payload(
            date="2026-06-14T10:00:00+00:00", scoring="2026-06-15T01:00:00+00:00"
        )
        b["num_citations"] = 2
        self.assertNotEqual(
            citation_utils.strip_volatile_timestamps(a),
            citation_utils.strip_volatile_timestamps(b),
        )

    def test_does_not_mutate_input_and_tolerates_missing_keys(self):
        original = {"dataset_id": "x", "date_last_updated": "2026-01-01T00:00:00+00:00"}
        stripped = citation_utils.strip_volatile_timestamps(original)
        # Input untouched (deep copy), volatile key removed in the result.
        self.assertIn("date_last_updated", original)
        self.assertNotIn("date_last_updated", stripped)
        self.assertEqual(stripped, {"dataset_id": "x"})


class TestWriteCitationJsonIfChanged(unittest.TestCase):
    """write_citation_json_if_changed underpins the #165 idempotency guarantee."""

    def _payload(self, *, date: str, num: int = 1) -> dict:
        return {
            "dataset_id": "ds000001",
            "num_citations": num,
            "date_last_updated": date,
            "metadata": {"fetch_date": date, "fetch_status": "success"},
            "citation_details": [],
        }

    def test_creates_new_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ds000001_citations.json")
            wrote = citation_utils.write_citation_json_if_changed(
                path, self._payload(date="2026-06-18T00:00:00+00:00")
            )
            self.assertTrue(wrote)
            self.assertTrue(os.path.isfile(path))

    def test_no_op_when_only_timestamps_differ(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ds000001_citations.json")
            citation_utils.write_citation_json_if_changed(
                path, self._payload(date="2026-06-14T00:00:00+00:00")
            )
            before = Path(path).read_text()
            wrote = citation_utils.write_citation_json_if_changed(
                path, self._payload(date="2026-06-18T00:00:00+00:00")
            )
            self.assertFalse(wrote)
            self.assertEqual(Path(path).read_text(), before)  # old timestamp kept

    def test_rewrites_on_substantive_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ds000001_citations.json")
            citation_utils.write_citation_json_if_changed(
                path, self._payload(date="2026-06-14T00:00:00+00:00", num=1)
            )
            wrote = citation_utils.write_citation_json_if_changed(
                path, self._payload(date="2026-06-14T00:00:00+00:00", num=2)
            )
            self.assertTrue(wrote)
            self.assertEqual(json.loads(Path(path).read_text())["num_citations"], 2)

    def test_rewrites_when_existing_file_is_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ds000001_citations.json")
            Path(path).write_text("not json at all")
            wrote = citation_utils.write_citation_json_if_changed(
                path, self._payload(date="2026-06-18T00:00:00+00:00")
            )
            self.assertTrue(wrote)
            self.assertEqual(json.loads(Path(path).read_text())["num_citations"], 1)


if __name__ == "__main__":
    unittest.main()
