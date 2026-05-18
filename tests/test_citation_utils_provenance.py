"""Direct tests for citation_utils.add_discovery_provenance.

Until Phase 3 the helper was only exercised transitively via the opencite
pipeline tests. These tests pin its behavior so future refactors do not
silently change the schema-v2 contract.
"""

from __future__ import annotations

from unittest import TestCase

from dataset_citations.core.citation_utils import (
    SCHEMA_VERSION_V2,
    add_discovery_provenance,
)


class AddDiscoveryProvenanceTests(TestCase):
    def test_creates_metadata_when_missing(self) -> None:
        result = add_discovery_provenance({}, discovery_backend="opencite")
        self.assertEqual(result["metadata"]["schema_version"], SCHEMA_VERSION_V2)
        self.assertEqual(result["metadata"]["discovery_backend"], "opencite")

    def test_overwrites_existing_top_level_markers(self) -> None:
        """Helper is a 'stamp this output' operation; it overwrites by design.

        The docstring says so explicitly; this test pins that behavior so a
        future refactor to setdefault would fail loudly.
        """
        payload = {
            "metadata": {
                "schema_version": "1.0",
                "discovery_backend": "scholarly",
            }
        }
        out = add_discovery_provenance(payload, discovery_backend="opencite")
        self.assertEqual(out["metadata"]["schema_version"], "2.0")
        self.assertEqual(out["metadata"]["discovery_backend"], "opencite")

    def test_preserves_unrelated_metadata_keys(self) -> None:
        payload = {
            "metadata": {"fetch_date": "2026-01-01", "total_cumulative_citations": 99}
        }
        out = add_discovery_provenance(payload, discovery_backend="opencite")
        self.assertEqual(out["metadata"]["fetch_date"], "2026-01-01")
        self.assertEqual(out["metadata"]["total_cumulative_citations"], 99)

    def test_per_citation_backend_only_set_when_missing(self) -> None:
        """setdefault on per-citation discovery_backend so callers can
        pre-populate with finer-grained labels and not have them clobbered."""
        payload = {
            "citation_details": [
                {"title": "A", "discovery_backend": "scholarly"},
                {"title": "B"},
            ]
        }
        out = add_discovery_provenance(payload, discovery_backend="opencite")
        self.assertEqual(out["citation_details"][0]["discovery_backend"], "scholarly")
        self.assertEqual(out["citation_details"][1]["discovery_backend"], "opencite")

    def test_tolerates_none_citation_details(self) -> None:
        payload = {"citation_details": None}
        out = add_discovery_provenance(payload, discovery_backend="opencite")
        self.assertEqual(out["metadata"]["schema_version"], "2.0")

    def test_custom_schema_version(self) -> None:
        out = add_discovery_provenance(
            {}, discovery_backend="opencite", schema_version="2.1-preview"
        )
        self.assertEqual(out["metadata"]["schema_version"], "2.1-preview")

    def test_returns_same_dict_for_chaining(self) -> None:
        payload: dict = {}
        out = add_discovery_provenance(payload, discovery_backend="opencite")
        self.assertIs(out, payload)
