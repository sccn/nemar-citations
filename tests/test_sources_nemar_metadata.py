"""Tests for nemar_metadata parsing.

Loads real .nemar/metadata.json snapshots from tests/test_data/sources/nemar/
and runs them through the pure parse_nemar_metadata function. No mocks, no
network.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import TestCase

from dataset_citations.sources.nemar_metadata import parse_nemar_metadata

FIXTURE_DIR = Path(__file__).parent / "test_data" / "sources" / "nemar"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text())


class ParseNm000103(TestCase):
    """nm000103 (Healthy Brain Network EEG) — has References, IsDerivedFrom,
    IsDescribedBy, IsIdenticalTo entries."""

    def setUp(self) -> None:
        self.payload = load_fixture("nm000103.metadata.json")
        self.refs = parse_nemar_metadata(self.payload)

    def test_emits_only_citation_relation_types(self) -> None:
        rel_types = {r.relation_type for r in self.refs}
        self.assertNotIn("IsDescribedBy", rel_types)
        self.assertNotIn("IsSupplementedBy", rel_types)
        self.assertTrue(
            rel_types.issubset(
                {"References", "IsDerivedFrom", "IsIdenticalTo", "IsVersionOf"}
            )
        )

    def test_skips_url_identifiers(self) -> None:
        # All emitted references must be DOI-typed; URL entries are dropped.
        for ref in self.refs:
            self.assertEqual(ref.identifier_type, "doi")

    def test_includes_known_references_dois(self) -> None:
        identifiers = {r.identifier for r in self.refs}
        self.assertIn("10.1038/sdata.2017.181", identifiers)
        self.assertIn("10.1038/sdata.2017.40", identifiers)

    def test_isidenticalto_zenodo_kept(self) -> None:
        ids = [r for r in self.refs if r.identifier == "10.5281/zenodo.17306881"]
        self.assertEqual(len(ids), 1)
        self.assertEqual(ids[0].relation_type, "IsIdenticalTo")

    def test_source_field(self) -> None:
        for ref in self.refs:
            self.assertEqual(ref.source, "nemar_metadata")
            self.assertEqual(ref.source_field, "related_identifiers")


class ParseNm000115(TestCase):
    """Second fixture for relation_type variety."""

    def setUp(self) -> None:
        self.payload = load_fixture("nm000115.metadata.json")
        self.refs = parse_nemar_metadata(self.payload)

    def test_emits_at_least_one_reference(self) -> None:
        self.assertGreater(len(self.refs), 0)
        # IsDescribedBy is excluded; we expect to see References or related.
        rel_types = {r.relation_type for r in self.refs}
        self.assertTrue(rel_types & {"References", "IsDerivedFrom", "IsIdenticalTo"})


class ParseSyntheticEdgeCases(TestCase):
    """Hand-crafted edge cases that aren't easy to find in the real fixtures."""

    def test_missing_related_identifiers(self) -> None:
        refs = parse_nemar_metadata({"version": "2.0"})
        self.assertEqual(refs, [])

    def test_empty_related_identifiers(self) -> None:
        refs = parse_nemar_metadata({"related_identifiers": []})
        self.assertEqual(refs, [])

    def test_filters_isdescribedby(self) -> None:
        refs = parse_nemar_metadata(
            {
                "related_identifiers": [
                    {
                        "identifier": "https://example.com",
                        "identifier_type": "URL",
                        "relation_type": "IsDescribedBy",
                    },
                    {
                        "identifier": "10.1038/foo.bar",
                        "identifier_type": "DOI",
                        "relation_type": "References",
                    },
                ]
            }
        )
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].identifier, "10.1038/foo.bar")

    def test_skips_openneuro_dataset_doi(self) -> None:
        refs = parse_nemar_metadata(
            {
                "related_identifiers": [
                    {
                        "identifier": "10.18112/openneuro.ds000117.v1.0.0",
                        "identifier_type": "DOI",
                        "relation_type": "IsIdenticalTo",
                    },
                ]
            }
        )
        self.assertEqual(refs, [])

    def test_skips_malformed_identifier(self) -> None:
        refs = parse_nemar_metadata(
            {
                "related_identifiers": [
                    {
                        "identifier": "10.1038/foo\nbar",
                        "identifier_type": "DOI",
                        "relation_type": "References",
                    },
                ]
            }
        )
        self.assertEqual(refs, [])

    def test_handles_non_dict_entry(self) -> None:
        refs = parse_nemar_metadata(
            {
                "related_identifiers": [
                    "not a dict",
                    None,
                    {
                        "identifier": "10.1038/sdata.2015.1",
                        "identifier_type": "DOI",
                        "relation_type": "References",
                    },
                ]
            }
        )
        self.assertEqual(len(refs), 1)
