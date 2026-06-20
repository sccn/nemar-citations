"""Direct tests for citation_utils.add_discovery_provenance.

Until Phase 3 the helper was only exercised transitively via the opencite
pipeline tests. These tests pin its behavior so future refactors do not
silently change the schema-v2 contract.
"""

from __future__ import annotations

from unittest import TestCase

from dataset_citations.core.citation_utils import (
    SCHEMA_VERSION_V2_1,
    add_discovery_provenance,
    stamp_dataset_metadata,
)


class AddDiscoveryProvenanceTests(TestCase):
    def test_creates_metadata_when_missing(self) -> None:
        result = add_discovery_provenance({}, discovery_backend="opencite")
        self.assertEqual(result["metadata"]["schema_version"], SCHEMA_VERSION_V2_1)
        self.assertEqual(result["metadata"]["discovery_backend"], "opencite")
        # Schema v2.1 provenance keys default to empty lists.
        self.assertEqual(result["metadata"]["anchors"], [])
        self.assertEqual(result["metadata"]["searched_dois"], [])

    def test_overwrites_existing_top_level_markers(self) -> None:
        """Helper is a 'stamp this output' operation; it overwrites by design.

        The docstring says so explicitly; this test pins that behavior so a
        future refactor to setdefault would fail loudly.
        """
        payload = {
            "metadata": {
                "schema_version": "1.0",
                "discovery_backend": "legacy",
            }
        }
        out = add_discovery_provenance(payload, discovery_backend="opencite")
        self.assertEqual(out["metadata"]["schema_version"], "2.1")
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
                {"title": "A", "discovery_backend": "legacy"},
                {"title": "B"},
            ]
        }
        out = add_discovery_provenance(payload, discovery_backend="opencite")
        self.assertEqual(out["citation_details"][0]["discovery_backend"], "legacy")
        self.assertEqual(out["citation_details"][1]["discovery_backend"], "opencite")

    def test_tolerates_none_citation_details(self) -> None:
        payload = {"citation_details": None}
        out = add_discovery_provenance(payload, discovery_backend="opencite")
        self.assertEqual(out["metadata"]["schema_version"], "2.1")

    def test_custom_schema_version(self) -> None:
        out = add_discovery_provenance(
            {}, discovery_backend="opencite", schema_version="2.1-preview"
        )
        self.assertEqual(out["metadata"]["schema_version"], "2.1-preview")

    def test_anchors_and_searched_dois_round_trip(self) -> None:
        anchors = [
            {"identifier": "10.1/a", "identifier_type": "doi", "kept": True},
            {"identifier": "10.2/b", "identifier_type": "doi", "kept": False},
        ]
        out = add_discovery_provenance(
            {},
            discovery_backend="opencite",
            anchors=anchors,
            searched_dois=["10.1/a"],
        )
        self.assertEqual(out["metadata"]["anchors"], anchors)
        self.assertEqual(out["metadata"]["searched_dois"], ["10.1/a"])
        # Stored as a copy, not the caller's list (mutation isolation).
        self.assertIsNot(out["metadata"]["anchors"], anchors)

    def test_returns_same_dict_for_chaining(self) -> None:
        payload: dict = {}
        out = add_discovery_provenance(payload, discovery_backend="opencite")
        self.assertIs(out, payload)


class StampDatasetMetadataTests(TestCase):
    def test_writes_all_three_keys(self) -> None:
        out = stamp_dataset_metadata(
            {},
            keywords=["EEG", "BIDS"],
            methods_description="collected during tasks",
            funding=[{"funder_name": "NIH", "award_number": "R01"}],
        )
        self.assertEqual(out["metadata"]["keywords"], ["EEG", "BIDS"])
        self.assertEqual(
            out["metadata"]["methods_description"], "collected during tasks"
        )
        self.assertEqual(
            out["metadata"]["funding"], [{"funder_name": "NIH", "award_number": "R01"}]
        )

    def test_empty_defaults(self) -> None:
        out = stamp_dataset_metadata({})
        self.assertEqual(out["metadata"]["keywords"], [])
        self.assertIsNone(out["metadata"]["methods_description"])
        self.assertEqual(out["metadata"]["funding"], [])

    def test_preserves_unrelated_metadata_and_is_idempotent(self) -> None:
        payload: dict = {"metadata": {"schema_version": "2.1", "anchor_count": 3}}
        first = stamp_dataset_metadata(
            payload, keywords=["EEG"], methods_description="m", funding=[]
        )
        # Unrelated keys untouched.
        self.assertEqual(first["metadata"]["schema_version"], "2.1")
        self.assertEqual(first["metadata"]["anchor_count"], 3)
        # Idempotent: a second identical call produces an equal dict.
        second = stamp_dataset_metadata(
            {"metadata": {"schema_version": "2.1", "anchor_count": 3}},
            keywords=["EEG"],
            methods_description="m",
            funding=[],
        )
        self.assertEqual(first, second)

    def test_returns_same_dict_for_chaining(self) -> None:
        payload: dict = {}
        out = stamp_dataset_metadata(payload)
        self.assertIs(out, payload)
